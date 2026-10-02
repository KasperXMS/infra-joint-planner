import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from run_predecision_matrix_v1 import validate_cell  # noqa: E402


def fixture(directory: Path, *, aware: bool = False, failure: str | None = None) -> None:
    run = directory / "runs/test"
    (run / "private").mkdir(parents=True)
    profile = {"network_class": "constrained"} if aware else None
    events = ([{"event_type": "logical.profile.predecision", "payload": {
        "decision_id": "manager:1", "profile": profile,
    }}] if aware else []) + [
        {"event_type": "logical.reasoning.input", "payload": {
            "logical_agent_id": "manager", "decision_id": "manager:1",
            "current_anonymous_profile": profile,
        }},
        {"event_type": "run.failed" if failure else "run.end", "payload": {}},
    ]
    values = {
        run / "result.json": {"execution_completed": not failure,
                              "final_answer": None if failure else "Yes",
                              "evaluation": None if failure else {"benchmark_score": 0},
                              "failure": None if not failure else {
                                  "exception_type": "AgentLoopError", "message": failure,
                              }},
        directory / "summary.json": {"trace_summary": {"logical_privacy_pass": True}},
        directory / "tc-attestation.json": {"cleanup_error": None,
                                            "original_qdisc": {"host": "clean"},
                                            "restored_qdisc": {"host": "clean"}},
    }
    for path, value in values.items():
        path.write_text(json.dumps(value), encoding="utf-8")
    (run / "trace.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    (run / "private/observer-diagnostics.jsonl").write_text(json.dumps({
        "probes": [{"probe_success": True}],
    }))


@pytest.mark.parametrize("aware", [True, False])
def test_queue_gate_keeps_wrong_answers_and_budget_failures(tmp_path: Path, aware: bool) -> None:
    fixture(tmp_path, aware=aware, failure="manager turn budget exhausted")
    assert validate_cell(tmp_path, "test", "aware" if aware else "blind")["problems"] == []


def test_queue_gate_rejects_missing_predecision_profile(tmp_path: Path) -> None:
    fixture(tmp_path)
    assert validate_cell(tmp_path, "test", "aware")["problems"] == [
        "profile mismatch: manager:1"
    ]


def test_queue_gate_stops_on_provider_incident(tmp_path: Path) -> None:
    fixture(tmp_path, failure="Blind verifier failed: ReadTimeout")
    assert "provider/runtime failure; requires audit" in validate_cell(
        tmp_path, "test", "blind"
    )["problems"]


def test_queue_gate_stops_on_observer_incident(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "runs/test/private/observer-diagnostics.jsonl"
    path.write_text(json.dumps({"probes": [{"probe_success": False,
                                          "probe_error_type": "ReadTimeout"}]}))
    assert "observer probe incident; requires audit" in validate_cell(
        tmp_path, "test", "blind"
    )["problems"]


def test_queue_gate_stops_on_tc_leakage(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "tc-attestation.json"
    tc = json.loads(path.read_text())
    tc["restored_qdisc"] = {"host": "shaped"}
    path.write_text(json.dumps(tc))
    assert "tc restoration failure" in validate_cell(tmp_path, "test", "blind")["problems"]
