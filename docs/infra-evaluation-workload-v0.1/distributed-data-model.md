# Versioned evaluation data model

[`evaluation-schema.json`](evaluation-schema.json) separates immutable task references, source residency, infrastructure profile, private evaluation definition and trial execution. A [schema-valid instance example](../../configs/experiments/infra-evaluation-instance-v01.json) references manifests instead of duplicating task data. One task row is reused across network conditions; it is never copied with a different answer or support label. The [candidate register](manifests/task-candidates.jsonl) is a researcher audit view, whereas the [Planner view](manifests/planner-view.jsonl) is the only task projection eligible for runtime. [Public evaluation definitions](manifests/evaluation-definitions.jsonl) contain private metadata references only; `evaluator-private.jsonl` remains outside Git on the experiment controller and is never installed in a Worker artifact store.

| Logical concept | Existing InfraMAS contract or store |
|---|---|
| Question/output contract | `TaskContract`, `OutputContract`; public task ID and objective |
| Source artifact/version/owner | `ArtifactSpec` and `ArtifactRuntimeState`; `FileArtifactStore` plus `source-residency.jsonl` SHA256, size and resident Agent |
| Agent, deployment and link | `EnvironmentSpec`, `InfrastructureState`, Worker `/state`; configured network profile is a separate reference |
| Semantic operation and placement | `SemanticAction`, `PhysicalDecision`, `OperatorRegistry`, `RuntimeExecutor` |
| Action status, output and dependency | `ActionReceipt`, `ExecutionResult`, `ArtifactTransferTelemetry`; probe's redacted producer/consumer/hash/representation receipt |
| Independent quality evaluation | `PrivateMultiHopEvaluation` / `PrivateMultiModalQAEvaluation` and original evaluator references; private labels excluded from Worker and Planner projection |

The logical source is a publisher or modality service; the physical host is a current placement, not a benchmark property. A full original article and a BM25 retrieved top-three record set have different artifact IDs and representations; neither is treated as semantically equivalent to the other. The schema permits `setup_policy` (`cold`, `resident`, `incremental`) and an explicit `result_namespace`. Cloud USD or local GPU money should remain `null` when not measured.
