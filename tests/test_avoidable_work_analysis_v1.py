import copy
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts import avoidable_work_analysis_v1 as analysis


def event(kind, **payload):
    return {"event_type": kind, "payload": payload}


def action(identifier="a", operator="bm25_retrieve", **changes):
    result = {
        "action_id": identifier,
        "operator": operator,
        "action_type": "tool",
        "owner_agent_id": "manager",
        "inputs": ["PRIVATE-input"],
        "outputs": [],
        "arguments": {"query": "PRIVATE-query", "output_artifact_id": "PRIVATE-output"},
    }
    result.update(changes)
    return result


def test_unknown_costs_are_never_zero_and_empty_execution_is_zero():
    values = [None, False, float("nan"), -1, 4]
    assert analysis.distribution(values)["known_n"] == 1
    assert analysis.distribution(values)["complete_sum"] is None
    assert analysis.distribution([])["complete_sum"] == 0


def test_fingerprint_requires_content_and_full_historical_contract():
    contract = {
        "deterministic": True,
        "output_rebinding_safe": True,
        "defaults_complete": True,
        "implementation_sha256": "1" * 64,
        "config_sha256": "2" * 64,
        "proof_sha256": "3" * 64,
    }
    identities = {"PRIVATE-input": {"sha256": "4" * 64, "media_type": "application/json"}}
    key, exact = analysis.fingerprint(action(), identities, contract)
    assert exact
    assert not analysis.fingerprint(action(), {}, contract)[1]
    assert not analysis.fingerprint(action(), identities)[1]
    changed = copy.deepcopy(identities)
    changed["PRIVATE-input"]["sha256"] = "5" * 64
    assert key != analysis.fingerprint(action(), changed, contract)[0]
    contract["implementation_sha256"] = "6" * 64
    assert key != analysis.fingerprint(action(), identities, contract)[0]


def test_fingerprint_normalizes_output_binding_but_preserves_arguments_and_input_order():
    first = action(inputs=["a", "b"])
    second = copy.deepcopy(first)
    second["arguments"]["output_artifact_id"] = "another-output"
    assert analysis.fingerprint(first, {}) == analysis.fingerprint(second, {})
    second["arguments"]["query"] = "different-query"
    assert analysis.fingerprint(first, {})[0] != analysis.fingerprint(second, {})[0]
    second = copy.deepcopy(first)
    second["inputs"].reverse()
    assert analysis.fingerprint(first, {})[0] != analysis.fingerprint(second, {})[0]


def model_events():
    a = action("PRIVATE-model", "invoke_model", action_type="model", prompt="PRIVATE-prompt")
    return [
        event("logical.action.prepared", action=a),
        event(
            "physical.execution",
            action_id="PRIVATE-model",
            execution={
                "operator": "invoke_model",
                "operator_latency_ms": 30,
                "model_telemetry": {
                    "service_latency_ms": 25,
                    "input_tokens": 3,
                    "output_tokens": 2,
                },
                "output": {"text": "PRIVATE-model-text", "artifacts": []},
                "transfers": [],
            },
        ),
        event(
            "logical.reasoning.input",
            decision_id="PRIVATE-decision",
            logical_agent_id="manager",
            input_items=[{"text": "PRIVATE-model-text"}],
        ),
    ]


def test_model_without_graph_consumer_can_have_prompt_carried_information():
    opportunities = analysis.mine(
        {"source": {"trace_sha256": "0" * 64}, "events": model_events()}, {"outcome": "score0"}
    )
    assert len(opportunities) == 1
    candidate = opportunities[0]
    assert candidate["classification"] == analysis.CF
    assert candidate["explicit_consumers_sha256"] == []
    assert candidate["later_control_inputs_containing_exact_output_text"] == 1
    assert candidate["potential_saved_cost"]["net_saving"] is None
    assert "PRIVATE" not in json.dumps(candidate)


def test_failed_prior_operator_is_not_a_reusable_success():
    events = [
        event("logical.action.prepared", action=action("a")),
        event("physical.execution", action_id="a", failure={"stage": "execution"}),
        event("logical.action.prepared", action=action("b")),
    ]
    assert analysis.mine({"source": {}, "events": events}, {"outcome": "unevaluated"}) == []


def test_duplicate_operator_signal_is_unknown_without_contract():
    events = [
        event("logical.action.prepared", action=action("a")),
        event("physical.execution", action_id="a", execution={"output": {}}),
        event("logical.action.prepared", action=action("b")),
    ]
    candidates = analysis.mine(
        {"source": {"trace_sha256": "0" * 64}, "events": events}, {"outcome": "score1"}
    )
    assert candidates[0]["pattern"] == "A"
    assert candidates[0]["classification"] == analysis.UNKNOWN


def test_missing_failed_model_work_and_incomplete_control_latency_remain_unknown():
    events = [
        event("logical.reasoning.started", decision_id="manager:1", logical_agent_id="manager"),
        event("logical.action.prepared", action=action("m", "invoke_model", action_type="model")),
        event("physical.execution", action_id="m", failure={"stage": "execution"}),
        event(
            "logical.model.outcome",
            action_id="m",
            succeeded=False,
            physical_selection_succeeded=True,
            reached_model_inference=False,
            failure_code="validation_failed",
        ),
        event("run.failed", failure="unfinished", e2e_latency_ms=100),
    ]
    row = analysis.project({"source": {}, "events": events})
    assert row["outcome"] == "unevaluated"
    assert row["original_score"] is None
    assert row["resource_vector"]["inference"]["service_complete_work_ms"] is None
    assert row["resource_vector"]["manager"]["latency_complete_work_ms"] is None
    assert row["resource_vector"]["network"]["action_transfer_complete_bytes"] is None
    assert row["resource_vector"]["inference"]["gpu_seconds"] is None


def archive_fixture(path: Path, *, corrupt=False):
    raw = json.dumps(event("task.start", task_id="PRIVATE-task")).encode()
    entries = []
    for index, disposition in [(1, "confounder"), (2, "valid")]:
        entries.append(
            {
                "cell_id": "phase1-longbench_v2-1-0123456789abcdef-p1-fast-B0",
                "cell_index": 1,
                "run_id": f"PRIVATE-run-{index}",
                "attempt_index": index,
                "trace_archive_path": f"trace{index}.jsonl",
                "trace_bytes": len(raw),
                "trace_sha256": "bad" if corrupt else hashlib.sha256(raw).hexdigest(),
                "event_count": 1,
                "effective_disposition": disposition,
            }
        )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"entries": entries}))
        for entry in entries:
            archive.writestr(entry["trace_archive_path"], raw)


def test_export_membership_excludes_confounded_attempt_and_deduplicates_overlap(tmp_path):
    path = tmp_path / "archive.zip"
    archive_fixture(path)
    rows, _ = analysis.load_archives([path, path])
    assert len(rows) == 1
    assert rows[0]["source"]["attempt_index"] == 2
    assert "PRIVATE" not in json.dumps(rows[0]["source"])


def test_hash_mismatch_even_on_excluded_attempt_fails_closed(tmp_path):
    path = tmp_path / "archive.zip"
    archive_fixture(path, corrupt=True)
    with pytest.raises(ValueError, match="hash"):
        analysis.load_archives([path])


def test_existing_output_is_rejected_before_inputs_are_read(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["analysis", "--archive", "nonexistent.zip", "--output-dir", str(tmp_path)]
    )
    with pytest.raises(FileExistsError):
        analysis.main()
