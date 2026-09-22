from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import Field, model_validator

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel

MIB = 1024 * 1024
DEFAULT_PAYLOAD_TARGETS: dict[str, int] = {
    "S": 8 * MIB,
    "M": 32 * MIB,
    "L": 128 * MIB,
}
DERIVED_LABEL = "derived_deterministic_semantic_replication_v1"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(raw, dict):
        raise ValueError(f"expected a JSON object: {path}")
    value = cast(dict[object, object], raw)
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"expected string JSON object keys: {path}")
    return cast(dict[str, Any], value)


def _required_string(value: Mapping[str, Any], field: str, *, source: Path) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item:
        raise ValueError(f"{source} requires a non-empty string field: {field}")
    return item


def _string_tuple(value: object, field: str, *, source: Path) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{source} requires a string array field: {field}")
    items = cast(list[object], value)
    if any(not isinstance(item, str) for item in items):
        raise ValueError(f"{source} requires a string array field: {field}")
    return tuple(cast(list[str], items))


class FrozenTaskIdentity(ContractModel):
    task_id: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    query: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    evaluator_type: str = Field(min_length=1)


class SourceFileDigest(ContractModel):
    path: str = Field(min_length=1)
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrozenShard(ContractModel):
    artifact_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    placement_agent: Literal["A4", "A5"]
    media_type: Literal["application/json"] = "application/json"
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(gt=0)


class FrozenPayload(ContractModel):
    label: str = Field(min_length=1)
    target_bytes: int = Field(gt=0)
    actual_bytes: int = Field(gt=0)
    record_count: int = Field(gt=0)
    derived_label: Literal["derived_deterministic_semantic_replication_v1"] = DERIVED_LABEL
    shards: tuple[FrozenShard, FrozenShard]

    @model_validator(mode="after")
    def totals_match_shards(self) -> FrozenPayload:
        if sum(shard.bytes for shard in self.shards) != self.actual_bytes:
            raise ValueError("payload byte total does not match shards")
        if sum(shard.record_count for shard in self.shards) != self.record_count:
            raise ValueError("payload record total does not match shards")
        if {shard.placement_agent for shard in self.shards} != {"A4", "A5"}:
            raise ValueError("payload must contain one A4 shard and one A5 shard")
        return self


class PrivateEvaluationReference(ContractModel):
    path: str = Field(min_length=1)
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    planner_visible: Literal[False] = False


class ContextPreflightConstraint(ContractModel):
    algorithm: Literal["utf8_bytes_token_upper_bound_v1"] = (
        "utf8_bytes_token_upper_bound_v1"
    )
    context_window_tokens: int = Field(gt=0)
    reserved_output_tokens: int = Field(gt=0)
    prompt_token_upper_bound: int = Field(gt=0)
    max_reduced_artifact_bytes: int = Field(gt=0)
    final_bm25_top_k: int = Field(gt=0)
    fail_closed: Literal[True] = True
    silent_truncation: Literal[False] = False

    @model_validator(mode="after")
    def budget_is_exact(self) -> ContextPreflightConstraint:
        expected = (
            self.context_window_tokens
            - self.reserved_output_tokens
            - self.prompt_token_upper_bound
        )
        if expected <= 0:
            raise ValueError("model context budget leaves no room for reduced artifacts")
        if self.max_reduced_artifact_bytes != expected:
            raise ValueError("max_reduced_artifact_bytes must equal the conservative budget")
        return self


class ScriptedWorkflowNode(ContractModel):
    node_id: str = Field(min_length=1)
    placement_agent: Literal["A4", "A5", "A28"]
    operator: str = Field(min_length=1)
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    arguments: dict[str, Any] = Field(default_factory=dict)

    def semantic_action(self) -> SemanticAction:
        return SemanticAction(
            operator=self.operator,
            inputs=self.inputs,
            arguments=self.arguments,
        )


class ScriptedWorkflowEdge(ContractModel):
    producer_node: str = Field(min_length=1)
    consumer_node: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)


class ScriptedWorkflowTemplate(ContractModel):
    template_id: Literal["heterogeneous_multihop_fixed_dag_v1"] = (
        "heterogeneous_multihop_fixed_dag_v1"
    )
    synthesis_model_instance_id: str = Field(min_length=1)
    same_synthesis_model_for_all_payloads: Literal[True] = True
    nodes: tuple[ScriptedWorkflowNode, ...]
    edges: tuple[ScriptedWorkflowEdge, ...]
    context_preflight: ContextPreflightConstraint


class SemanticWorkloadManifest(ContractModel):
    schema_version: Literal["heterogeneous-semantic-workload-freeze-v1"] = (
        "heterogeneous-semantic-workload-freeze-v1"
    )
    task: FrozenTaskIdentity
    representation: Literal["derived_semantic_replication_json"] = (
        "derived_semantic_replication_json"
    )
    representation_notes: str = Field(min_length=1)
    source_candidate_document_count: int = Field(gt=0)
    materialized_source_document_count: int = Field(gt=0)
    source_files: tuple[SourceFileDigest, ...]
    payloads: tuple[FrozenPayload, ...]
    private_evaluation: PrivateEvaluationReference
    workflow_template: ScriptedWorkflowTemplate
    planner_visible: Literal[False] = False


class _SourceDocument(ContractModel):
    source_document_id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record: dict[str, Any]


def _source_documents(
    data_dir: Path,
    candidate_ids: tuple[str, ...],
    supporting_ids: tuple[str, ...],
) -> tuple[_SourceDocument, ...]:
    candidate_order = {document_id: index for index, document_id in enumerate(candidate_ids)}
    documents: list[_SourceDocument] = []
    for path in data_dir.glob("mhr-doc-*.json"):
        document_id = path.stem
        if document_id not in candidate_order:
            raise ValueError(f"local document is not a task candidate: {document_id}")
        record = _load_object(path)
        for field in ("title", "body", "author", "source", "published_at", "category", "url"):
            _required_string(record, field, source=path)
        documents.append(
            _SourceDocument(
                source_document_id=document_id,
                source_sha256=_sha256_file(path),
                record=record,
            )
        )
    documents.sort(key=lambda document: candidate_order[document.source_document_id])
    available = {document.source_document_id for document in documents}
    missing_support = sorted(set(supporting_ids) - available)
    if missing_support:
        raise ValueError(f"materialization omits supporting documents: {missing_support}")
    if len(documents) < 2:
        raise ValueError("at least two real source documents are required for A4/A5 sharding")
    return tuple(documents)


def _derived_record(
    payload_label: str,
    ordinal: int,
    replica_index: int,
    document: _SourceDocument,
) -> dict[str, Any]:
    identity = _canonical_json(
        {
            "derived_label": DERIVED_LABEL,
            "payload_label": payload_label,
            "ordinal": ordinal,
            "source_document_id": document.source_document_id,
            "source_sha256": document.source_sha256,
        }
    )
    derived_id = f"mhr-derived-{_sha256_bytes(identity)[:32]}"
    return {
        **document.record,
        "derived_document_id": derived_id,
        "derived_label": DERIVED_LABEL,
        "replica_index": replica_index,
        "source_document_id": document.source_document_id,
        "source_document_sha256": document.source_sha256,
    }


def _record_bytes(
    payload_label: str,
    ordinal: int,
    documents: Sequence[_SourceDocument],
) -> bytes:
    document = documents[ordinal % len(documents)]
    record = _derived_record(
        payload_label,
        ordinal,
        ordinal // len(documents),
        document,
    )
    return _canonical_json(record)


def _nearest_record_count(
    payload_label: str,
    target_bytes: int,
    documents: Sequence[_SourceDocument],
) -> tuple[int, int]:
    if target_bytes <= 0:
        raise ValueError("payload targets must be positive")
    count = 0
    total = 4  # Two empty JSON arrays: [] + [].
    shard_counts = [0, 0]
    while total < target_bytes or count < 2:
        shard_index = count % 2
        record_size = len(_record_bytes(payload_label, count, documents))
        separator_size = 1 if shard_counts[shard_index] else 0
        candidate_total = total + record_size + separator_size
        if count >= 2 and abs(total - target_bytes) <= abs(candidate_total - target_bytes):
            break
        total = candidate_total
        shard_counts[shard_index] += 1
        count += 1
    return count, total


def _write_payload(
    output_dir: Path,
    label: str,
    target_bytes: int,
    documents: Sequence[_SourceDocument],
) -> FrozenPayload:
    record_count, expected_bytes = _nearest_record_count(label, target_bytes, documents)
    paths = {
        "A4": output_dir / f"payload-{label.lower()}-a4.json",
        "A5": output_dir / f"payload-{label.lower()}-a5.json",
    }
    streams = {agent: path.open("wb") for agent, path in paths.items()}
    try:
        for stream in streams.values():
            stream.write(b"[")
        shard_counts = {"A4": 0, "A5": 0}
        for ordinal in range(record_count):
            agent = "A4" if ordinal % 2 == 0 else "A5"
            if shard_counts[agent]:
                streams[agent].write(b",")
            streams[agent].write(_record_bytes(label, ordinal, documents))
            shard_counts[agent] += 1
        for stream in streams.values():
            stream.write(b"]")
    finally:
        for stream in streams.values():
            stream.close()

    shards = tuple(
        FrozenShard(
            artifact_id=f"heterogeneous-{label.lower()}-{agent.lower()}",
            path=path.name,
            placement_agent=cast(Literal["A4", "A5"], agent),
            bytes=path.stat().st_size,
            sha256=_sha256_file(path),
            record_count=(record_count + (1 if agent == "A4" else 0)) // 2,
        )
        for agent, path in paths.items()
    )
    actual_bytes = sum(shard.bytes for shard in shards)
    if actual_bytes != expected_bytes:
        raise RuntimeError("written payload size differs from deterministic sizing pass")
    return FrozenPayload(
        label=label,
        target_bytes=target_bytes,
        actual_bytes=actual_bytes,
        record_count=record_count,
        shards=cast(tuple[FrozenShard, FrozenShard], shards),
    )


def _workflow_template(
    *,
    model_instance_id: str,
    context_window_tokens: int,
    reserved_output_tokens: int,
    prompt_token_upper_bound: int,
    local_top_k: int,
    final_top_k: int,
) -> ScriptedWorkflowTemplate:
    preflight = ContextPreflightConstraint(
        context_window_tokens=context_window_tokens,
        reserved_output_tokens=reserved_output_tokens,
        prompt_token_upper_bound=prompt_token_upper_bound,
        max_reduced_artifact_bytes=(
            context_window_tokens - reserved_output_tokens - prompt_token_upper_bound
        ),
        final_bm25_top_k=final_top_k,
    )
    nodes = (
        ScriptedWorkflowNode(
            node_id="a4-local-retrieve-reduce",
            placement_agent="A4",
            operator="bm25_retrieve",
            inputs=("{payload}.A4",),
            outputs=("{payload}.A4.local-top-k",),
            arguments={
                "query": "{task.query}",
                "text_field": "body",
                "top_k": local_top_k,
                "output_artifact_id": "{payload}.A4.local-top-k",
            },
        ),
        ScriptedWorkflowNode(
            node_id="a5-local-retrieve-reduce",
            placement_agent="A5",
            operator="bm25_retrieve",
            inputs=("{payload}.A5",),
            outputs=("{payload}.A5.local-top-k",),
            arguments={
                "query": "{task.query}",
                "text_field": "body",
                "top_k": local_top_k,
                "output_artifact_id": "{payload}.A5.local-top-k",
            },
        ),
        ScriptedWorkflowNode(
            node_id="a28-merge-package",
            placement_agent="A28",
            operator="aggregate_artifacts",
            inputs=("{payload}.A4.local-top-k", "{payload}.A5.local-top-k"),
            outputs=("{payload}.placement-group-package",),
            arguments={"output_artifact_id": "{payload}.placement-group-package"},
        ),
        ScriptedWorkflowNode(
            node_id="a28-placement-group-bm25-reduce",
            placement_agent="A28",
            operator="bm25_retrieve",
            inputs=("{payload}.placement-group-package",),
            outputs=("{payload}.context-ready",),
            arguments={
                "query": "{task.query}",
                "text_field": "body",
                "top_k": final_top_k,
                "output_artifact_id": "{payload}.context-ready",
            },
        ),
        ScriptedWorkflowNode(
            node_id="a28-same-model-synthesis",
            placement_agent="A28",
            operator="invoke_model",
            inputs=("{payload}.context-ready",),
            outputs=(),
            arguments={
                "prompt": (
                    "{task.query}\nUse only the context artifact. Return a concise answer. "
                    "Context admission is governed by the frozen fail-closed preflight."
                ),
            },
        ),
    )
    edges = (
        ScriptedWorkflowEdge(
            producer_node="a4-local-retrieve-reduce",
            consumer_node="a28-merge-package",
            artifact_id="{payload}.A4.local-top-k",
        ),
        ScriptedWorkflowEdge(
            producer_node="a5-local-retrieve-reduce",
            consumer_node="a28-merge-package",
            artifact_id="{payload}.A5.local-top-k",
        ),
        ScriptedWorkflowEdge(
            producer_node="a28-merge-package",
            consumer_node="a28-placement-group-bm25-reduce",
            artifact_id="{payload}.placement-group-package",
        ),
        ScriptedWorkflowEdge(
            producer_node="a28-placement-group-bm25-reduce",
            consumer_node="a28-same-model-synthesis",
            artifact_id="{payload}.context-ready",
        ),
    )
    return ScriptedWorkflowTemplate(
        synthesis_model_instance_id=model_instance_id,
        nodes=nodes,
        edges=edges,
        context_preflight=preflight,
    )


def freeze_semantic_workload(
    *,
    data_dir: Path,
    output_dir: Path,
    payload_targets: Mapping[str, int] = DEFAULT_PAYLOAD_TARGETS,
    model_instance_id: str = "a28-deepseek-chat",
    context_window_tokens: int = 64_000,
    reserved_output_tokens: int = 1_024,
    prompt_token_upper_bound: int = 2_048,
    local_top_k: int = 1,
    final_top_k: int = 4,
    overwrite: bool = False,
) -> SemanticWorkloadManifest:
    """Freeze deterministic semantic payloads without exposing private evaluation data."""

    task_path = data_dir / "task.json"
    candidates_path = data_dir / "candidates.json"
    task = _load_object(task_path)
    candidates = _load_object(candidates_path)
    task_id = _required_string(task, "task_id", source=task_path)
    query = _required_string(task, "query", source=task_path)
    candidate_values_raw = cast(object, candidates.get("candidates"))
    if not isinstance(candidate_values_raw, list):
        raise ValueError("candidates.json requires a candidates array")
    candidate_values = cast(list[object], candidate_values_raw)
    selected: list[dict[str, Any]] = []
    for value in candidate_values:
        if not isinstance(value, dict):
            continue
        candidate_record = cast(dict[str, Any], value)
        if candidate_record.get("task_id") == task_id:
            selected.append(candidate_record)
    if len(selected) != 1:
        raise ValueError(f"expected exactly one candidate record for task: {task_id}")
    candidate = selected[0]
    if _required_string(candidate, "query", source=candidates_path) != query:
        raise ValueError("task and candidate query differ")
    candidate_ids = _string_tuple(
        candidate.get("candidate_document_ids"),
        "candidate_document_ids",
        source=candidates_path,
    )
    task_ids = _string_tuple(task.get("artifact_ids"), "artifact_ids", source=task_path)
    if candidate_ids != task_ids:
        raise ValueError("candidate and task artifact ordering differ")
    evaluator = candidate.get("evaluator_only")
    if not isinstance(evaluator, dict):
        raise ValueError("candidate requires private evaluator data")
    evaluator = cast(dict[str, Any], evaluator)
    supporting_ids = _string_tuple(
        evaluator.get("supporting_document_ids"),
        "supporting_document_ids",
        source=candidates_path,
    )
    gold_answer = _required_string(evaluator, "answer", source=candidates_path)
    documents = _source_documents(data_dir, candidate_ids, supporting_ids)

    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    private_payload = {
        "schema_version": "heterogeneous-private-evaluation-v1",
        "task_id": task_id,
        "evaluator_type": _required_string(task, "evaluator_type", source=task_path),
        "gold_answer": gold_answer,
        "supporting_document_ids": supporting_ids,
        "planner_visible": False,
    }
    private_path = output_dir / "private-evaluation.json"
    private_content = _canonical_json(private_payload) + b"\n"
    private_path.write_bytes(private_content)

    payloads = tuple(
        _write_payload(output_dir, label, target, documents)
        for label, target in payload_targets.items()
    )
    source_paths = (task_path, candidates_path) + tuple(
        data_dir / f"{document.source_document_id}.json" for document in documents
    )
    source_files = tuple(
        SourceFileDigest(
            path=path.name,
            bytes=path.stat().st_size,
            sha256=_sha256_file(path),
        )
        for path in source_paths
    )
    manifest = SemanticWorkloadManifest(
        task=FrozenTaskIdentity(
            task_id=task_id,
            dataset=_required_string(task, "dataset", source=task_path),
            query=query,
            instruction=_required_string(task, "instruction", source=task_path),
            evaluator_type=_required_string(task, "evaluator_type", source=task_path),
        ),
        representation_notes=(
            "Derived, deterministic canonical JSON replication of every real document present "
            "in the pre-existing local M4 materialization. No random or synthetic padding is used; "
            "replicas receive unique IDs and retain source hashes. The local materialization "
            "contains the supporting evidence but may be a subset of the 30-candidate task. "
            "Physical placement is harness-only and must not enter TaskContract or planner input."
        ),
        source_candidate_document_count=len(candidate_ids),
        materialized_source_document_count=len(documents),
        source_files=source_files,
        payloads=payloads,
        private_evaluation=PrivateEvaluationReference(
            path=private_path.name,
            bytes=len(private_content),
            sha256=_sha256_bytes(private_content),
        ),
        workflow_template=_workflow_template(
            model_instance_id=model_instance_id,
            context_window_tokens=context_window_tokens,
            reserved_output_tokens=reserved_output_tokens,
            prompt_token_upper_bound=prompt_token_upper_bound,
            local_top_k=local_top_k,
            final_top_k=final_top_k,
        ),
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_bytes(_canonical_json(manifest.model_dump(mode="json")) + b"\n")
    return manifest
