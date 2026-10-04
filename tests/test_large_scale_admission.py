import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_sdk_api_meter import build_meter, usage

from infra_joint.control.provenance import provenance_sha256
from infra_joint.experiments.api_cost import APICostReceipt, estimate_api_cost

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
admission = importlib.import_module("large_scale_admission_v1")


def raw_fixture(tmp_path: Path, *, role: str, status: int = 200,
                messages: list[dict] | None = None) -> tuple[dict, object]:
    meter, _ = build_meter()
    model = "qwen3.8-max" if role == "verifier" else "deepseek-v4-pro"
    response = {"model": model, "usage": usage(123)} if status == 200 else {"error": "synthetic"}
    raw = response.get("usage")
    cost = estimate_api_cost(
        raw, meter.prices[model], meter.fx, provider=meter.provider, region=meter.region,
        requested_model=model, response_model=response.get("model"))
    identifier = role + "-001"
    request = {"model": model, "messages": messages or [{"role": "user", "content": "synthetic"}]}
    receipt = APICostReceipt(call_id=identifier, recipient=role, cost=cost)
    values = {"request": request, "response": response, "usage": {
        "call_id": identifier, "recipient": role, "intended_model": model, "requested_model": model,
        "response_model": response.get("model"), "status": status, "usage": raw,
        "cost_receipt": receipt.model_dump(mode="json"), "error_type": None}}
    for kind, value in values.items():
        (tmp_path / f"{identifier}-{kind}.json").write_text(json.dumps(value))
    return meter.prices, meter.fx


def test_original_freeform_answer_and_wrong_quality_are_valid_not_binary_rewritten() -> None:
    for answer, score in (("original named entities", 1), ("wrong named entity", 0)):
        problems, incidents = admission.classify_terminal({
            "execution_completed": True, "final_answer": answer,
            "evaluation": {"benchmark_score": score, "format_valid": True}, "failure": None})
        assert not problems and not incidents


@pytest.mark.parametrize("exception", ["AgentLoopError", "MaxTurnsExceeded", "ModelBehaviorError"])
def test_explainable_agent_failure_is_retained_without_operational_replacement(
    exception: str,
) -> None:
    assert admission.classify_terminal({
        "execution_completed": False, "failure": {
            "exception_type": exception,
            "message": "Budget exhausted or invalid terminal synthesis"},
    }) == ([], [])


def test_missing_evaluation_runtime_and_service_failures_are_not_semantic_failures() -> None:
    assert admission.classify_terminal({
        "execution_completed": True, "final_answer": "A", "evaluation": None,
    })[0]
    assert admission.classify_terminal({
        "execution_completed": False, "failure": {
            "exception_type": "ValueError", "message": "observer surface mismatch"},
    })[0]
    assert admission.classify_terminal({
        "execution_completed": False, "failure": {
            "exception_type": "ReadTimeout", "message": "model service timeout"},
    }) == ([], ["external_model_service_failure"])


def test_every_actual_request_is_scanned_and_raw_usage_is_recomputed(tmp_path: Path) -> None:
    prices, fx = raw_fixture(tmp_path, role="manager")
    raw_fixture(tmp_path, role="specialist", messages=[{
        "role": "tool", "content": '{"physical_profile":{"network_class":"slow"}}'}])
    raw_fixture(tmp_path, role="verifier")
    result = admission.raw_api_audit(
        tmp_path, method="B1", planner="deepseek-v4-pro", prices=prices, fx=fx,
        physical_identifiers=())
    assert result["HTTP_calls"] == 3
    assert result["roles"]["all"]["calls"] == 3
    assert result["roles"]["all"]["complete_usd_total"] is not None
    assert result["problems"] == ["actual_recipient_privacy_or_method_leakage"]
    specialist = next(row for row in result["contexts"] if row["recipient"] == "specialist")
    assert specialist["findings"] and "slow" not in json.dumps(specialist)


@pytest.mark.parametrize(("status", "expected"), [
    (503, "operational"), (429, "operational"), (400, "confounder"),
])
def test_API_outage_and_protocol_failure_are_distinguished(
    tmp_path: Path, status: int, expected: str,
) -> None:
    prices, fx = raw_fixture(tmp_path, role="manager", status=status)
    result = admission.raw_api_audit(
        tmp_path, method="B0", planner="deepseek-v4-pro", prices=prices, fx=fx,
        physical_identifiers=())
    assert bool(result["operational_incidents"]) == (expected == "operational")
    assert bool(result["problems"]) == (expected == "confounder")
    assert result["roles"]["all"]["complete_usd_total"] is None


@pytest.mark.parametrize("damage", ["request", "response", "cost", "unclosed"])
def test_raw_payload_or_cost_drift_and_unclosed_requests_stop_admission(
    tmp_path: Path, damage: str,
) -> None:
    prices, fx = raw_fixture(tmp_path, role="manager")
    if damage == "request":
        path = tmp_path / "manager-001-request.json"
        value = json.loads(path.read_text())
        value["model"] = "substituted-model"
    elif damage == "response":
        path = tmp_path / "manager-001-response.json"
        value = json.loads(path.read_text())
        value["usage"]["prompt_tokens"] = 9999
    elif damage == "cost":
        path = tmp_path / "manager-001-usage.json"
        value = json.loads(path.read_text())
        value["cost_receipt"]["cost"]["usd_amount"] = "999"
    else:
        path = tmp_path / "unclosed-request.json"
        value = {"model": "deepseek-v4-pro", "messages": []}
    path.write_text(json.dumps(value))
    assert admission.raw_api_audit(
        tmp_path, method="B0", planner="deepseek-v4-pro", prices=prices, fx=fx,
        physical_identifiers=())["problems"]


def event(index: int, kind: str, parent: str | None) -> dict:
    return {"run_id": "run", "step_id": f"{index:06d}-{kind}", "parent_id": parent,
            "event_type": kind, "timestamp": datetime.now(UTC).isoformat(), "payload": {}}


def test_trace_chain_uses_real_JSONL_record_boundaries_and_exact_terminal() -> None:
    first = event(0, "run.start", None)
    last = event(1, "run.failed", first["step_id"])
    assert not admission.trace_audit([first, last], "run")
    assert admission.trace_audit([first, last], "other-run")
    assert admission.trace_audit([first, last, last], "run")
    last["parent_id"] = "missing-parent"
    assert admission.trace_audit([first, last], "run")


def test_full_admission_keeps_original_freeform_wrong_answer_and_separate_API_cost(
    tmp_path: Path,
) -> None:
    api_root = tmp_path / "private/api"
    api_root.mkdir(parents=True)
    prices, fx = raw_fixture(api_root, role="manager")
    raw_fixture(api_root, role="verifier")
    price_path = tmp_path / "prices.json"
    price_path.write_text(json.dumps({
        "prices": {key: value.model_dump(mode="json") for key, value in prices.items()},
        "fx": fx.model_dump(mode="json")}))
    first = event(0, "run.start", None)
    call = event(1, "logical.reasoning.input", first["step_id"])
    call["payload"] = {"logical_agent_id": "manager", "decision_id": "d1",
                       "input_items": [], "input_sha256": provenance_sha256([]),
                       "current_anonymous_profile": None}
    verification = event(2, "logical.verification.input", call["step_id"])
    verification["payload"] = {"context": {}, "context_sha256": provenance_sha256({})}
    last = event(3, "run.end", verification["step_id"])
    folder = tmp_path / "runs/run"
    folder.mkdir(parents=True)
    (folder / "result.json").write_text(json.dumps({
        "run_id": "run", "execution_completed": True, "final_answer": "wrong original free text",
        "evaluation": {"benchmark_score": 0, "format_valid": True}, "failure": None}))
    (folder / "trace.jsonl").write_text(
        "\n".join(json.dumps(item) for item in (first, call, verification, last)) + "\n")
    diagnostic = folder / "private/observer-diagnostics.jsonl"
    diagnostic.parent.mkdir()
    diagnostic.write_text('{"probes":[{"probe_success":true}]}\n')
    receipts = {
        "private/worker-state-before.json": {"synthetic-worker": {"deployments": []}},
        "tc-attestation.json": {"cleanup_error": None, "original_qdisc": {"node": "unchanged"},
                               "restored_qdisc": {"node": "unchanged"},
                               "applied_qdisc": {"node": "shaped"}},
        "worker-shutdown.json": {"errors": [], "verified_exited": True},
        "private/artifact-persistence.json": {"pass": True},
    }
    api = admission.raw_api_audit(api_root, method="B0", planner="deepseek-v4-pro",
                                  prices=prices, fx=fx, physical_identifiers=())
    receipts["api-accounting.json"] = {"roles": api["roles"], "logical_feedback": False}
    for name, payload in receipts.items():
        (tmp_path / name).write_text(json.dumps(payload))
    config = {"run_id": "run", "method": "B0", "planner": "deepseek-v4-pro",
              "worker_urls": {"synthetic-worker": "http://127.0.0.1:9000"}}
    result = admission.admit(tmp_path, config, price_path)
    assert result["disposition"] == "valid" and not result["problems"]
    assert result["original_evaluation"]["benchmark_score"] == 0
    assert result["api_audit"]["roles"]["all"]["calls"] == 2
    assert result["api_audit"]["roles"]["specialist"]["calls"] == 0
    assert result["api_audit"]["roles"]["all"]["complete_usd_total"] is not None
