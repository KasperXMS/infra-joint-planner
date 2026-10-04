import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
audit = importlib.import_module("large_scale_graph_audit_v1").graph_audit


def node(identifier: str, *, owner: str = "manager", status: str = "pending") -> dict:
    return {"action_id": identifier, "owner_agent_id": owner, "action_type": "tool",
            "operator": "bm25_retrieve", "status": status, "inputs": [], "outputs": []}


def graph(version: int, nodes: list[dict], edges: list[dict] | None = None) -> dict:
    return {"event_type": "workflow.graph.snapshot",
            "payload": {"version": version, "nodes": nodes, "edges": edges or []}}


def edge(left: str, right: str) -> dict:
    return {"producer_action_id": left, "consumer_action_id": right,
            "information_id": "PRIVATE-ARTIFACT-ID"}


def interval(identifier: str, start: int, end: int) -> list[dict]:
    return [{"event_type": kind, "timestamp": f"2026-10-05T00:00:{second:02d}Z",
             "payload": {"action_id": identifier, "decision_id": "PRIVATE-DECISION",
                         "logical_agent_id": "manager"}}
            for kind, second in (("action.started", start), ("action.completed", end))]


def test_state_snapshots_are_not_new_structures_and_ids_do_not_escape() -> None:
    events = [graph(0, []), graph(1, [node("PRIVATE-ACTION")]),
              graph(2, [node("PRIVATE-ACTION", status="running")]),
              graph(3, [node("PRIVATE-ACTION", status="succeeded")])]
    result = audit(events)
    assert result["snapshot_count"] == 4
    assert result["structure_growth_events"] == 1
    assert result["final_node_states"] == {"succeeded": 1}
    assert result["dependency_critical_path_ms"] is None
    assert "PRIVATE" not in json.dumps(result)


def test_parallel_actions_and_dependency_path_are_not_e2e() -> None:
    events = [graph(0, []), graph(1, [node("a"), node("b"), node("c")], [edge("a", "c")])]
    events += interval("a", 0, 2) + interval("b", 0, 3) + interval("c", 2, 6)
    result = audit(events)
    assert result["dependency_critical_path_ms"] == 6000
    assert result["max_concurrent_actions"] == 2
    assert result["overlap_wall_ms"] == 3000
    assert result["dependency_frontier_max_width"] == 2
    assert result["dependency_path_nodes"] == 2
    assert result["action_wall_union_ms"] == 6000
    assert not result["structural_width_implies_executed_parallelism"]


def test_missing_intervals_are_unknown_and_no_snapshot_is_not_an_empty_graph() -> None:
    assert audit([])["structure_growth_events"] is None
    events = [graph(0, [node("a"), node("b")])] + interval("a", 0, 2)
    result = audit(events)
    assert result["unknown_graph_action_intervals"] == 1
    assert result["dependency_critical_path_ms"] is None
    assert result["max_concurrent_actions"] is None


@pytest.mark.parametrize("events, message", [
    ([graph(0, [node("a")]), graph(1, [])], "removes"),
    ([graph(0, [node("a")]), graph(1, [node("a", owner="other")])], "mutates"),
    ([graph(0, [node("a"), node("a")])], "duplicate"),
    ([graph(0, [node("a")], [edge("a", "b")])], "missing"),
    ([graph(0, [node("a"), node("b")], [edge("a", "b"), edge("b", "a")])], "cycle"),
    ([graph(0, []), graph(0, [])], "increasing"),
])
def test_graph_integrity_fails_closed(events: list[dict], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        audit(events)


def test_dependency_overlap_does_not_create_a_valid_critical_path() -> None:
    events = [graph(0, [node("a"), node("b")], [edge("a", "b")])]
    events += interval("a", 0, 3) + interval("b", 2, 5)
    result = audit(events)
    assert result["dependency_order_violations"] == 1
    assert result["dependency_critical_path_ms"] is None


def test_shape_hash_ignores_opaque_identity_but_preserves_operator_owner_structure() -> None:
    first = audit([graph(0, [node("a"), node("b", owner="child-1")], [edge("a", "b")])])
    second = audit([graph(0, [node("x"), node("y", owner="renamed")], [edge("x", "y")])])
    assert first["ordinal_structure_sha256"] == second["ordinal_structure_sha256"]
    assert first["logical_owners_with_actions"] == 2
    different = audit([graph(0, [node("x"), node("y")], [edge("x", "y")])])
    assert first["ordinal_structure_sha256"] != different["ordinal_structure_sha256"]


def test_unknown_operator_is_not_exported_as_arbitrary_private_text() -> None:
    value = node("a")
    value["operator"] = "PRIVATE-OPERATOR"
    with pytest.raises(ValueError, match="vocabulary"):
        audit([graph(0, [value])])
