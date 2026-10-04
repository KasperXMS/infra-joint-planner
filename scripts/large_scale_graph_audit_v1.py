"""Offline execution-grown graph audit; never an Agent input or execution policy.

Ordinal descriptors omit physical identities, artifact IDs, prompts and arguments.
They describe observed structure, not graph isomorphism or semantic equivalence.
Artifact/control dependency paths are not full Manager/Verifier critical paths.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from infra_joint.control.contracts import WorkflowGraphSnapshot
from infra_joint.control.provenance import provenance_sha256
from infra_joint.evaluation.trace_audit import action_intervals, summarize_concurrency
from infra_joint.operators.catalog import build_operator_catalog


def graph_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    snapshots = [WorkflowGraphSnapshot.model_validate(e["payload"]) for e in events
                 if e["event_type"] == "workflow.graph.snapshot"]
    if not snapshots:
        return {"metric_version": "execution-grown-structure-v1", "graph_available": False,
                "structure_growth_events": None, "dependency_critical_path_ms": None}
    operators = set(build_operator_catalog().specs()) | {"invoke_model"}
    prior_nodes: dict[str, tuple[Any, ...]] = {}
    prior_edges: set[tuple[str, str, str]] = set()
    growth = []
    previous_version = -1
    for snapshot in snapshots:
        if snapshot.version <= previous_version:
            raise ValueError("graph versions are not strictly increasing")
        previous_version = snapshot.version
        nodes = {n.action_id: (n.owner_agent_id, n.action_type, n.operator, n.inputs, n.outputs)
                 for n in snapshot.nodes}
        edges = {(e.producer_action_id, e.consumer_action_id, e.information_id)
                 for e in snapshot.edges}
        if len(nodes) != len(snapshot.nodes) or len(edges) != len(snapshot.edges):
            raise ValueError("duplicate graph node or information-flow edge")
        if any(n.operator not in operators for n in snapshot.nodes):
            raise ValueError("graph contains an operator outside the system vocabulary")
        if any(left not in nodes or right not in nodes for left, right, _ in edges):
            raise ValueError("graph edge references a missing action")
        if not prior_edges <= edges or not prior_nodes.keys() <= nodes.keys():
            raise ValueError("execution-grown graph removes completed history")
        if any(nodes[key] != value for key, value in prior_nodes.items()):
            raise ValueError("execution-grown graph mutates an existing action")
        added = set(nodes) - set(prior_nodes)
        added_edges = edges - prior_edges
        if added or added_edges:
            growth.append({"snapshot_version": snapshot.version,
                           "added_nodes": len(added), "added_edges": len(added_edges),
                           "added_operator_counts": dict(Counter(nodes[k][2] for k in added))})
        prior_nodes, prior_edges = nodes, edges

    final = snapshots[-1]
    ordinal = {n.action_id: index for index, n in enumerate(final.nodes)}
    owners: dict[str, int] = {}
    descriptors = []
    for node in final.nodes:
        owners.setdefault(node.owner_agent_id, len(owners))
        descriptors.append({"owner_ordinal": owners[node.owner_agent_id],
                            "is_manager": node.owner_agent_id == "manager",
                            "action_type": node.action_type, "operator": node.operator,
                            "input_count": len(node.inputs), "output_count": len(node.outputs)})
    # Multiple information edges between one producer/consumer pair stay distinct
    # in the descriptor, but are one prerequisite for topological ordering.
    normalized_edges = sorted([ordinal[e.producer_action_id], ordinal[e.consumer_action_id],
                               e.information_id == "control-dependency"] for e in final.edges)
    predecessors: dict[str, set[str]] = {key: set() for key in ordinal}
    successors: dict[str, set[str]] = {key: set() for key in ordinal}
    for edge in final.edges:
        predecessors[edge.consumer_action_id].add(edge.producer_action_id)
        successors[edge.producer_action_id].add(edge.consumer_action_id)
    degrees = {key: len(value) for key, value in predecessors.items()}
    frontier = sorted(key for key, value in degrees.items() if not value)
    order = []
    frontier_width = 0
    while frontier:
        frontier_width = max(frontier_width, len(frontier))
        next_frontier = []
        for key in frontier:
            order.append(key)
            for successor in sorted(successors[key]):
                degrees[successor] -= 1
                if degrees[successor] == 0:
                    next_frontier.append(successor)
        frontier = sorted(next_frontier)
    if len(order) != len(ordinal):
        raise ValueError("execution-grown graph has a dependency cycle")

    intervals, invalid = action_intervals(events)
    durations = {item.action_id: (item.end - item.start) * 1000 for item in intervals}
    missing_intervals = set(ordinal) - set(durations)
    known_timing = not invalid and not missing_intervals
    depth: dict[str, int] = {}
    path_ms: dict[str, float] = {}
    dependency_order_violations = 0
    interval_by_id = {item.action_id: item for item in intervals}
    for key in order:
        depth[key] = 1 + max((depth[p] for p in predecessors[key]), default=0)
        if known_timing:
            path_ms[key] = durations[key] + max((path_ms[p] for p in predecessors[key]),
                                               default=0.0)
        for parent in predecessors[key]:
            if parent in interval_by_id and key in interval_by_id:
                dependency_order_violations += (
                    interval_by_id[parent].end > interval_by_id[key].start)
    concurrency = summarize_concurrency(events)
    return {
        "metric_version": "execution-grown-structure-v1", "graph_available": True,
        "snapshot_count": len(snapshots), "structure_growth_events": len(growth),
        "growth": growth, "node_count": len(final.nodes), "edge_count": len(final.edges),
        "final_node_states": dict(Counter(n.status for n in final.nodes)),
        "logical_owners_with_actions": len(owners),
        "operator_counts": dict(Counter(n.operator for n in final.nodes)),
        "ordinal_structure_sha256": provenance_sha256(
            {"nodes": descriptors, "edges": normalized_edges}),
        "signature_semantics": "creation-order descriptor, not isomorphism or task semantics",
        "max_fan_out": max((len(x) for x in successors.values()), default=0),
        "max_fan_in": max((len(x) for x in predecessors.values()), default=0),
        "dependency_frontier_max_width": frontier_width,
        "dependency_path_nodes": max(depth.values(), default=0),
        "dependency_critical_path_ms": max(path_ms.values(), default=0.0)
        if known_timing and not dependency_order_violations else None,
        "dependency_order_violations": dependency_order_violations,
        "unknown_graph_action_intervals": len(missing_intervals),
        "invalid_action_intervals": len(invalid),
        "max_concurrent_actions": concurrency["max_concurrent_actions"]
        if known_timing else None,
        "overlap_wall_ms": concurrency["overlap_wall_ms"] if known_timing else None,
        "action_wall_union_ms": concurrency["action_wall_union_ms"] if known_timing else None,
        "cross_owner_overlapping_pairs": concurrency["cross_owner_overlapping_pairs"],
        "timing_scope": "observed action lifetimes including transfer/preflight/wrapper; "
        "dependency path excludes Manager, Verifier, SDK information flow and scheduling waits",
        "structural_width_implies_executed_parallelism": False,
        "semantic_revision_or_infrastructure_causality_proven": False,
    }
