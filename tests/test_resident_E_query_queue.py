import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
controller = importlib.import_module("large_scale_resident_E_query_queue_v1")


def fixture(root: Path) -> tuple[Path, list[dict]]:
    directory = root / "evidence"
    api = directory / "private/api"
    api.mkdir(parents=True)
    for call, recipient, tools in [("first", "manager", ["invoke_model", "bm25_retrieve"]),
                                    ("second", "manager", ["invoke_model"]),
                                    ("third", "verifier", ["submit_verification"])]:
        (api / (call + "-usage.json")).write_text(json.dumps({
            "recipient": recipient, "call_id": call}), encoding="utf-8")
        (api / (call + "-request.json")).write_text(json.dumps({
            "tools": [{"function": {"name": t}} for t in tools]}), encoding="utf-8")
    events = [{"event_type": "method.variant.start", "payload": {
        "variant": "route-e-v0", "optional_cost_queries": False}}]
    return directory, events


def test_actual_E_request_tools_are_audited_without_reading_or_exporting_bodies(tmp_path) -> None:
    directory, events = fixture(tmp_path)
    original = {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    controller.assert_E_tool_isolation(directory, events)
    assert original == {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


@pytest.mark.parametrize("extra", ["estimate_bm25_retrieve", "estimate_invoke_model",
                                   "compare_ready_actions", "commit_quote", "discard_quote"])
def test_unused_forbidden_E_tool_still_invalidates_comparison(tmp_path, extra: str) -> None:
    directory, events = fixture(tmp_path)
    request = directory / "private/api/second-request.json"
    value = json.loads(request.read_text())
    value["tools"].append({"function": {"name": extra}})
    request.write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="must not expose"):
        controller.assert_E_tool_isolation(directory, events)


@pytest.mark.parametrize("damage", ["flag", "other-route", "duplicate-start", "missing-start",
                                     "identity"])
def test_E_surface_receipt_cannot_waive_wrong_flag_or_wrong_call_identity(tmp_path, damage) -> None:
    directory, events = fixture(tmp_path)
    if damage == "flag":
        events[0]["payload"]["optional_cost_queries"] = True
    elif damage == "other-route":
        events[0]["payload"]["variant"] = "route-b-v0"
    elif damage == "duplicate-start":
        events.append(events[0])
    elif damage == "missing-start":
        events.clear()
    else:
        usage = directory / "private/api/first-usage.json"
        value = json.loads(usage.read_text())
        value["call_id"] = "../escaped"
        usage.write_text(json.dumps(value))
    with pytest.raises(RuntimeError):
        controller.assert_E_tool_isolation(directory, events)


def test_historical_repairs_remain_bound_to_their_separate_frozen_epochs(tmp_path) -> None:
    (tmp_path / "quote-repair-authorization-001.json").write_text(json.dumps({
        "new_execution_sha256": "2" * 64, "affected_original_runs": ["quote4", "quote84"]}))
    (tmp_path / "input-cardinality-repair-authorization-001.json").write_text(json.dumps({
        "new_execution_sha256": "3" * 64, "original_run_id": "cardinality110"}))
    assert controller.historical_repairs(tmp_path) == {
        "quote4": "2" * 64, "quote84": "2" * 64, "cardinality110": "3" * 64}


def test_controller_cannot_prepare_execution_on_development_pc() -> None:
    with pytest.raises(RuntimeError):
        controller.prepare()
