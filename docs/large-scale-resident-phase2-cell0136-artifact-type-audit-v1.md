# Phase II original136: model-output media-type gate

Queue021 stopped after the original attempt, not because of an observation
timeout. Its controller exit receipt records exit1 at
2026-10-08T13:56:54.870181UTC; independent14:00:43UTC /proc inspection confirms
the exact supervisor3875600/start198979764 and controller3875601/start198979767
are absent. Strict inactive and Strata-stopped checks pass14:06:22UTC.
There are135 admitted cells,137 preserved attempts, no pending action, one
unresolved original136, the sole original71 exclusion and56 unstarted cells.

Original136 is `phase2-video_mme-3-be0078ffc09fde77-p1-fast-B0`, attempt1.
Its original execution completed with evaluation present and no terminal failure.
No answer or evaluator score is reviewed here. Process3935767 exited0, all four
Workers were verified exited with no errors, tc cleanup was successful and
restored the exact previous qdisc, and the five resident instances passed.
Runtime0ff, fixed Blind Qwen Verifier,20/64/20 budget and1200s physical service
timeout remain unchanged.

| Immutable artifact | SHA-256 |
| --- | --- |
| Journal | `e8e796e0b9bb2e3ebf1c2492c96138a20e05fca246bcb029c205f799339fa3a9` |
| Original admission bytes | `1f9b682fcf42b59d879ea3065d9af07eee03683eeee70961de4152d976f76669` |
| Original result canonical provenance | `004b74e143adad14618e6a3f7b4738dbb71dab710b2dfb50219e12a15d61e798` |
| Trace bytes,225 events | `77a809eb8c16a3f8d83126dba2d7d31a25ab6e5104c96f961797ce1548258c14` |
| Run config bytes | `cf370e686a465fa5918f10a1aef712c9cce45016e8db5160e632af44e3d85b72` |

## Narrow diagnostic evidence

| Action | Metadata-only finding |
| --- | --- |
| Manager model call | Ten JPEGs;592 UTF-8 prompt bytes +10*4096 declared image context cost =41552; reserved2048/window32768. Exact context-limit rejection at selection, no inference or transfer. |
| Specialist model producers | Three successful invoke_model actions materialized text/plain outputs of4612,1249 and6011B. Logical information metadata, physical output metadata and saved replicas agree. |
| Specialist aggregate call | aggregate_artifacts consumes those three text/plain outputs; frozen load_json accepts application/json or application/jsonl only. Exact `artifact is not JSON: <first input>` failure at execution, before content parsing. No output artifact is materialized. |

The raw gate is exactly
`typed_action_failure_requires_audit:validation_failed`. This observation is
consistent with a legal-tool/bad-input-type composition mistake, but narrow
inspection does not grant effective admission. Existing record-field reviewers
do not prove this different media-type error. An additive offline proof and its
source-bound adapter/tests are in progress. They must bind all lifecycle/graph,
actual SDK selected-tool wires, immutable original admission/evidence, frozen
Worker/execution sources and image-context settings before any sidecar is created.

No new benchmark attempt, replacement, operator/type alias, runtime fix,
prompt/budget tuning, body/store scan or semantic-quality claim is made.
Existing admission/result/trace/journal and historical review authorities remain
unchanged. Successful creators must never be repeated. A validated complete
proof, exclusive sidecar and successor authority, independent bootstrap and
gated continuation remain outstanding. Full144/160/176/192, all192/all193 and
final actual-recipient/private/manual analyses and Q1–Q10 reports remain due.
