"""Pure synthetic contracts and companion proofs; no artifact body reads."""

from __future__ import annotations

import copy
import importlib
import json
from typing import Any

import pytest
from test_resident_derived_field_review import add_guard, case, event
from test_resident_derived_field_review_v2 import (
    add_filtered_descendant,
    filtered_case,
    set_filter_metadata,
)
from test_resident_derived_field_review_v3 import add_collision, add_read

reviewer = importlib.import_module("large_scale_resident_derived_field_review_v4")
_v1 = importlib.import_module("test_resident_derived_field_review")
_v2 = importlib.import_module("test_resident_derived_field_review_v2")
_v3 = importlib.import_module("test_resident_derived_field_review_v3")
EMPTY_SHA256 = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"


def bind_input(inputs: tuple[Any, ...], action: dict[str, Any], source: str) -> None:
    """Rebind a synthetic consumer to an exact earlier producer and metadata."""
    trace, result, _, _, _ = inputs
    action["inputs"] = [source]
    graph = result["loop"]["graph_snapshots"][-1]
    next(node for node in graph["nodes"] if node["action_id"] == action["action_id"])["inputs"] = [
        source
    ]
    producer = next(
        item["payload"]["action"]
        for item in trace
        if item["event_type"] == "logical.action.prepared"
        and any(output["artifact_id"] == source for output in item["payload"]["action"]["outputs"])
    )
    graph["edges"][:] = [
        edge for edge in graph["edges"] if edge["consumer_action_id"] != action["action_id"]
    ]
    graph["edges"].append(
        {
            "producer_action_id": producer["action_id"],
            "consumer_action_id": action["action_id"],
            "information_id": source,
        }
    )
    if action["action_type"] == "model":
        meta = event(trace, "logical.observation", producer["action_id"])["output"]
        estimated = len(action["prompt"].encode("utf-8")) + meta["size_bytes"]
        obs = event(trace, "logical.observation", action["action_id"])
        budget = obs["failure_message"].split(", reserved_output=", 1)[1]
        message = f"context limit exceeded before transfer: estimated_input={estimated}, "
        message += "reserved_output=" + budget
        obs["failure_message"] = message
        event(trace, "physical.execution", action["action_id"])["failure"]["failure_message"] = (
            message
        )
        for item in trace:
            if (
                item["event_type"] == "logical.action.selected"
                and item["payload"]["action_id"] == action["action_id"]
            ):
                item["payload"]["selected_tool_arguments"]["inputs"] = [source]
            if item["event_type"] == "logical.batch.validation" and item["payload"][
                "action_ids"
            ] == [action["action_id"]]:
                item["payload"]["input_artifact_ids"] = [source]


def test_all_companions_accept_filter_descendants_without_claiming_field_ancestry() -> None:
    inputs = filtered_case()
    trace, _, _, _, _ = inputs
    read, obs, physical = add_read(inputs)
    set_filter_metadata(inputs, 70_001, "e" * 64)
    bind_input(inputs, read, "filtered")
    obs["failure_message"] = "artifact has 70001 bytes; read limit is 65536"
    physical["failure"]["failure_message"] = obs["failure_message"]
    add_collision(inputs)
    context = event(trace, "logical.action.prepared", "manager:call_context")
    bind_input(inputs, context, "filtered")
    bind_input(inputs, event(trace, "logical.action.prepared", "bad"), "merged")
    add_guard(trace)
    before = copy.deepcopy(inputs)
    proof = reviewer.review(*inputs)
    assert inputs == before
    assert proof["version"] == "metadata-bound-derived-record-field-proof-v4"
    assert proof["covered_original_findings"] == [reviewer.GATE]
    assert proof["derived_field_proof"][0]["source_preserving_filter_ancestors"] == []
    filtered = proof["inferred_record_contracts"]["filtered"]
    assert filtered["record_count"] is None
    assert (filtered["record_count_lower_bound"], filtered["record_count_upper_bound"]) == (1, 2)
    assert filtered["possible_fields"] == ["_bm25_score", "body"]
    assert proof["read_artifact_limit_proof"][0]["input_artifact_id"] == "filtered"
    for key in (
        "context_preflight_proof",
        "prephysical_guard_proof",
        "read_artifact_limit_proof",
        "output_collision_proof",
    ):
        assert len(proof[key]) == 1
        assert not proof[key][0]["covers_original_audit_finding"]
        assert not proof[key][0]["reached_model_inference"]
    assert any(step["operator"] == "filter_records" for step in proof["propagation_proof"])
    assert "PRIVATE" not in json.dumps(proof)
    assert not proof["replacement_authorized"]
    assert not proof["new_store_or_corpus_body_decoded"]


def test_empty_filter_can_bind_context_companion_without_field_nonempty_claim() -> None:
    inputs = filtered_case()
    trace, result, _, _, _ = inputs
    set_filter_metadata(inputs, 2, EMPTY_SHA256)
    bind_input(inputs, event(trace, "logical.action.prepared", "bad"), "merged")
    context = _v1.add_context_companion(trace, result)
    bind_input(inputs, context, "filtered")
    proof = reviewer.review(*inputs)
    assert proof["inferred_record_contracts"]["filtered"]["record_count"] == 0
    assert proof["derived_field_proof"][0]["source_preserving_filter_ancestors"] == []
    assert len(proof["context_preflight_proof"]) == 1


@pytest.mark.parametrize(
    "damage",
    [
        "wrong-op",
        "unknown-source",
        "extra-count",
        "extra-field",
        "fake-metadata-count",
        "nonempty-empty-digest",
        "wrong-source-shape",
        "wrong-input-dependency",
        "failed-upstream",
        "mismatched-producer-operator",
    ],
)
def test_filtered_provenance_rejects_arguments_sources_and_fake_counts(damage: str) -> None:
    inputs = filtered_case()
    trace, result, _, shapes, _ = inputs
    action = event(trace, "logical.action.prepared", "filter")
    if damage == "wrong-op":
        action["arguments"]["op"] = "regex"
    elif damage == "unknown-source":
        action["inputs"] = ["unknown"]
        next(
            node
            for node in result["loop"]["graph_snapshots"][-1]["nodes"]
            if node["action_id"] == "filter"
        )["inputs"] = ["unknown"]
        result["loop"]["graph_snapshots"][-1]["edges"][:] = [
            edge
            for edge in result["loop"]["graph_snapshots"][-1]["edges"]
            if edge["consumer_action_id"] != "filter"
        ]
    elif damage in {"extra-count", "extra-field"}:
        action["arguments"]["record_count" if damage == "extra-count" else "new_field"] = 2
    elif damage == "fake-metadata-count":
        event(trace, "physical.execution", "filter")["execution"]["output"] = {
            **event(trace, "logical.observation", "filter")["output"],
            "record_count": 2,
        }
    elif damage == "nonempty-empty-digest":
        set_filter_metadata(inputs, 50, EMPTY_SHA256)
    elif damage == "wrong-source-shape":
        shapes["source1"]["actual_union_fields"].append("text")
    elif damage == "wrong-input-dependency":
        action["inputs"] = ["retrieved1"]
    elif damage == "failed-upstream":
        event(trace, "action.completed", "aggregate")["succeeded"] = False
    elif damage == "mismatched-producer-operator":
        event(trace, "physical.execution", "filter")["execution"]["operator"] = "select_fields"
    with pytest.raises(RuntimeError):
        reviewer.review(*inputs)


def test_supported_transform_set_and_complete_reservation_source_binding() -> None:
    assert "src/infra_joint/operators/structured.py" in reviewer.SOURCE_PATHS
    assert "src/infra_joint/control/gateway.py" in reviewer.SOURCE_PATHS
    inputs = filtered_case()
    add_filtered_descendant(inputs, "bm25_retrieve", ["filtered"], top_k=1)
    proof = reviewer.review(*inputs)
    assert {step["operator"] for step in proof["propagation_proof"]} == {
        "bm25_retrieve",
        "filter_records",
        "aggregate_artifacts",
    }
    assert proof["derived_field_proof"][0]["source_preserving_filter_ancestors"] == ["filter"]
    for version in ("v1", "v3"):
        old = importlib.import_module("large_scale_resident_derived_field_review_" + version)
        with pytest.raises(RuntimeError, match="unknown record transformation"):
            old.review(*inputs)


_retained_positive_tests = [
    "test_filter_is_source_preserving_but_count_remains_conservative",
    "test_source_contains_filter_preserves_body_without_creating_text",
    "test_uncertain_filtered_count_propagates_through_retrieval_and_aggregate",
    "test_old_only_failure_has_no_filter_ancestor_even_when_proof_supports_filters",
    "test_context_only_filter_cannot_be_mistaken_for_field_failure_ancestry",
    "test_bounded_retrieval_can_restore_exact_count_without_inventing_filter_count",
    "test_empty_filter_can_be_bound_without_claiming_its_failure_was_absent_text",
]


@pytest.mark.parametrize("name", _retained_positive_tests)
def test_v4_preserves_conservative_filter_proofs(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    monkeypatch.setattr(_v2, "reviewer", reviewer)
    getattr(_v2, name)()


_retained_rejection_tests = [
    (_v1, "test_no_unproven_case_can_be_a_validation_waiver"),
    (_v1, "test_only_exact_unprepared_guard_is_accepted"),
    (_v1, "test_context_companion_is_exact_preflight_evidence_only"),
    (_v2, "test_filtered_proof_rejects_unproved_shape_or_nonempty_claim"),
    (_v2, "test_descendant_canonical_size_must_agree_with_count_bounds"),
    (_v3, "test_read_companion_requires_exact_closed_metadata_failure"),
    (_v3, "test_output_collision_is_exact_prior_reservation_not_a_waiver"),
]
_retained_rejection_cases: list[tuple[str, str, str]] = [
    (module.__name__, name, damage)
    for module, name in _retained_rejection_tests
    for damage in getattr(module, name).pytestmark[0].args[1]
]


@pytest.mark.parametrize("module_name,name,damage", _retained_rejection_cases)
def test_v4_preserves_strict_shape_lifecycle_replica_and_companion_rejections(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    name: str,
    damage: str,
) -> None:
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "reviewer", reviewer)
    getattr(module, name)(damage)


def test_unchanged_bm25_aggregate_proof_still_requires_original_field_failure() -> None:
    inputs = case()
    proof = reviewer.review(*inputs)
    assert proof["inferred_record_contracts"]["merged"]["record_count"] == 2
    assert proof["derived_field_proof"][0]["source_preserving_filter_ancestors"] == []
    trace, result, _, _, _ = inputs
    trace[:] = [
        item
        for item in trace
        if item["payload"].get("action", item["payload"]).get("action_id") != "bad"
    ]
    graph = result["loop"]["graph_snapshots"][-1]
    graph["nodes"][:] = [node for node in graph["nodes"] if node["action_id"] != "bad"]
    graph["edges"][:] = [edge for edge in graph["edges"] if edge["consumer_action_id"] != "bad"]
    with pytest.raises(RuntimeError):
        reviewer.review(*inputs)
