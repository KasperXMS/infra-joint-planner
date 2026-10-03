import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from cost_guidance_exploration_v1 import (  # noqa: E402
    CONDITIONS,
    TASKS,
    base_config,
    cell_config,
    ensure_remote,
    method_trace_audit,
    protocol,
    reserve_cell,
    verify_reference_tasks,
)

from infra_joint.control.ledger import LEDGER_MESSAGE_PREFIX
from infra_joint.control.provenance import provenance_sha256


def test_exploration_reuses_frozen_tasks_models_budget_and_64_fresh_stores() -> None:
    value = protocol()
    assert tuple(row["label"] for row in value["tasks"]) == TASKS
    assert value["execution"] == {"scheduler": "auto_physical_locality_aware",
                                 "repetitions": 1, "retry": False, "replacement": False}
    assert value["model_service_timeout_seconds"] == 1200
    assert value["primary_cells"] == 16 and value["maximum_substantive_cells"] == 36
    assert value["network_regimes"]["fast"]["bandwidth_mbps"] == 100
    assert value["network_regimes"]["slow"]["bandwidth_mbps"] == 3
    assert value["quote"] == {"ttl_seconds": 120, "max_proposals": 128, "minimum_support": 3}
    root = Path("/home/super/xiaoming/cost-guidance-exploration-v1-test")
    configs = [cell_config(value, root, row, condition)
               for row in value["tasks"] for condition in CONDITIONS]
    assert len({c["run_id"] for c in configs}) == 16
    assert len({p for c in configs for p in c["fresh_worker_stores"].values()}) == 64
    assert all(c["profile_visibility"] == "blind" for c in configs)
    assert [r["initial_placement"] for r in value["tasks"]] == [
        ["A4", "A5", "A28"], ["A4", "A5"], ["A4", "A5", "A28", "A5"], ["A4"],
    ]
    assert tuple(base_config(value)["planner"]["available_operations"]) == (
        "aggregate_artifacts", "aggregate_records", "bm25_retrieve", "derive_fields",
        "extract_clip", "filter_records", "invoke_model", "make_contact_sheet",
        "read_artifact", "sample_frames", "select_fields", "top_k_records",
    )


def test_exploration_cannot_access_datasets_on_development_pc(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="4090-owned"):
        ensure_remote(tmp_path)
    with pytest.raises(ValueError, match="unknown"):
        cell_config(protocol(), tmp_path, protocol()["tasks"][0], "fast-aware")


def events(*, quote: bool = False) -> list[dict[str, Any]]:
    ledger = {"role": "user", "content": LEDGER_MESSAGE_PREFIX + "{}"}
    output = {"type": "function_call_output", "output": json.dumps({
        "quote_id": "q", "action_sha256": "hash", "consequence": {},
    })}
    items = [ledger, *([output] if quote else [])]
    result = [{"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "manager", "input_items": items,
        "input_sha256": provenance_sha256(items),
    }}, {"event_type": "logical.method.reasoning_usage", "payload": {}}]
    if quote:
        result.extend([{"event_type": "logical.cost_quote.run.end", "payload": {}},
                       {"event_type": "logical.cost_quote.created", "payload": {
                           "quote": {"quote_id": "q"}}}])
    return result


@pytest.mark.parametrize("method", ["ledger", "quote"])
def test_method_audit_accepts_exact_actual_recipient_inputs(method: str) -> None:
    assert not method_trace_audit(events(quote=method == "quote"), method)["problems"]


@pytest.mark.parametrize("payload", [
    {"role": "user", "content": LEDGER_MESSAGE_PREFIX + "{}"},
    {"type": "function_call_output", "output": json.dumps({
        "quote_id": "q", "action_sha256": "h", "consequence": {},
    })},
])
def test_method_audit_rejects_specialist_cost_feedback(payload: dict[str, Any]) -> None:
    value = events()
    value.append({"event_type": "logical.reasoning.input", "payload": {
        "logical_agent_id": "specialist", "input_items": [payload],
        "input_sha256": provenance_sha256([payload]),
    }})
    assert "Blind specialist received ledger/quote" in method_trace_audit(
        value, "ledger",
    )["problems"]


def test_method_audit_rejects_missing_or_duplicate_ledger_and_input_hash_drift() -> None:
    value = events()
    value[0]["payload"]["input_items"] *= 2
    assert set(method_trace_audit(value, "ledger")["problems"]) == {
        "effective reasoning input hash mismatch", "Manager must receive exactly one fresh ledger",
    }
    assert "Ledger-only Manager received quote" in method_trace_audit(
        events(quote=True), "ledger",
    )["problems"]


def test_reference_comparison_rejects_representation_and_placement_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cost_guidance_exploration_v1 as driver

    task = {"label": TASKS[1], "task_bundle_sha256": "task",
            "static_capability_sha256": "cap", "initial_placement": {"a": "A4"}}
    row = {"task_label": task["label"], "task_bundle_sha256": "task",
           "capability_sha256": "cap", "initial_placement": {"a": "A4"}}
    path = tmp_path / "audit.json"
    path.write_text(json.dumps({"effective_records": [row] * 4}))
    monkeypatch.setattr(driver, "REFERENCE_AUDIT", path)
    monkeypatch.setattr(driver, "REFERENCE_AUDIT_SHA256", driver._sha256(path))
    verify_reference_tasks([task])
    changed = copy.deepcopy(task)
    changed["initial_placement"] = {"a": "A5"}
    with pytest.raises(RuntimeError, match="placement drift"):
        verify_reference_tasks([changed])
    changed = copy.deepcopy(task)
    changed["task_bundle_sha256"] = "wrong"
    with pytest.raises(RuntimeError, match="task/capability"):
        verify_reference_tasks([changed])


def test_global_cell_cap_counts_affected_runs_and_never_reuses_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cost_guidance_exploration_v1 as driver

    monkeypatch.setattr(driver, "_revision", lambda: "0" * 40)
    path = tmp_path / "budget.jsonl"
    reserve_cell("primary", budget_file=path)
    with pytest.raises(RuntimeError, match="already reserved"):
        reserve_cell("primary", budget_file=path)
    for index in range(35):
        reserve_cell(f"affected-{index}", budget_file=path)
    before = path.read_bytes()
    with pytest.raises(RuntimeError, match="cap reached"):
        reserve_cell("37th", budget_file=path)
    assert before == path.read_bytes()
    assert len(before.splitlines()) == 36


def test_verifier_context_cannot_receive_cost_feedback() -> None:
    value = events(quote=True)
    context = {"evidence": LEDGER_MESSAGE_PREFIX + "{}"}
    value.append({"event_type": "logical.verification.input", "payload": {
        "context": context, "context_sha256": provenance_sha256(context),
    }})
    assert "Blind Verifier cost isolation/provenance failure" in method_trace_audit(
        value, "quote",
    )["problems"]
