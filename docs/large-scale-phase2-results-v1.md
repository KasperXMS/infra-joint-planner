# Resident Phase II results — in progress

Checkpoint: 2026-10-06T19:52:03Z / 2026-10-07 03:52 HKT. Ten of 192 nominal
held-out cells settled; no reservation was pending at this snapshot. These are
actual original evaluator results, not final
method estimates. Same frozen 18-task manifest, execution004, resident diversified
pool, B0/B1/A/E methods, deterministic schedule and n1 discipline. Old42 and
Phase I results are not pooled into this held-out table.

The first four cells are the same frozen LongBench-v2 position6 task hash
`612be14c898ffdda`, attempt1. Canonical choice came from successful terminal model
output; evaluator ran without a semantic finalizer. Original admissions were
independently reproduced exactly and matched journal settlements. Empty initial
stores, Worker exit, five-instance residency and tc restoration passed. Existing
actual SDK recipient scans found no issues; complete post-block semantic/adoption
audits remain pending. Cells five through eight are frozen Video-MME position5
task hash `332db0bfa03dd109`, also attempt1, with valid completion and original
scores 0, 0, 1 and 1 respectively. Neither wrong-answer cell was retried.

| Task | Planner / network / method | Completion / format / score | Manager / Verifier | Physical / returned inference | Context rejects | E2E s | Initial bytes / s | Artifact movement bytes | API list-price USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LongBench6 | DeepSeek / Fast / E | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 61.338 | 2,032,683 / 0.215 | 0 | 0.076829 |
| LongBench6 | Qwen / Slow / B0 | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 57.405 | 2,032,683 / 5.737 | 0 | 0.066510 |
| LongBench6 | DeepSeek / Slow / B1 | true / valid / 1 | 17 / 17 | 24 / 11 | 2 | 392.753 | 2,032,683 / 5.739 | 0 | 0.468597 |
| LongBench6 | Qwen / Fast / A | true / valid / 1 | 6 / 6 | 4 / 1 | 1 | 53.779 | 2,032,683 / 0.204 | 0 | 0.065860 |
| Video5 | Qwen / Fast / E | true / valid / 0 | 8 / 8 | 7 / 1 | 1 | 136.761 | 2,076,341 / 0.209 | 0 | 0.486185 |
| Video5 | DeepSeek / Slow / A | true / valid / 0 | 7 / 7 | 4 / 1 | 1 | 140.020 | 2,076,341 / 5.906 | 0 | 0.180513 |
| Video5 | Qwen / Slow / B1 | true / valid / 1 | 3 / 3 | 2 / 1 | 0 | 101.103 | 2,076,341 / 5.863 | 0 | 0.120313 |
| Video5 | DeepSeek / Fast / B0 | true / valid / 1 | 3 / 3 | 2 / 1 | 0 | 91.785 | 2,076,341 / 0.211 | 0 | 0.108085 |
| Video6 | DeepSeek / Fast / B1 | true / valid / 1 | 3 / 3 | 2 / 1 | 0 | 121.284 | 233,097,342 / 20.753 | 0 | 0.071510 |
| Video6 | Qwen / Slow / A | true / valid / 1 | 5 / 5 | 3 / 1 | 1 | 753.030 | 233,097,342 / 650.833 | 0 | 0.220815 |

Fast100Mbps/configured5ms and Slow3Mbps/configured50ms retain the existing
Jetson HTB/no-netem caveat: configured delay is not measured symmetric RTT.
Initial materialization is separate from Agent-controlled registered artifact
transfers. Zero artifact movement does not mean zero HTTP prompt/control traffic.
The price estimate is based on frozen usage/pricing, not the provider invoice.
Worker operator receipts include invoke_model and must not be added again to
backend service work as an E2E decomposition.

Observed paths:

- E, B0 and A: two BM25 attempts, two model requests, one context preflight rejection
  followed by successful smaller-input inference. Six Manager/Verifier turns,
  four graph nodes. No specialists; single-agent completion is valid.
- B1: ten BM25 actions, one aggregate_artifacts action and thirteen model requests,
  with eleven returned inference telemetry receipts and two context rejections.
  24 graph nodes/14 edges, 73 snapshots, zero specialists. Physical model input/
  output totals42,324/729; all eleven finish reasons stop. Backend service work
 260.379s. Most successful model selections were A4; the terminal prompt-only
  choice synthesis selected the4090GPU0Qwen3.5-27B instance,290input/2output tokens.
 34actual SDK contexts (17Manager/17Verifier) scanned without findings.
- Video5/E: sample_frames, an infeasible model request, four make_contact_sheet
  actions, then successful visual model invocation consuming all four sheets.
  A4VL4B returned4,620input/2output tokens, finish stop; service25.118s. Seven
  graph nodes/64 artifact-flow edges/22snapshots; max actual concurrency1,
  no specialists. The terminal model choice was format-valid but wrong under
  the original evaluator. Actual original admission/settlement, four empty stores,
  unchanged five resident identities, tc restoration, Worker exit and16SDK
  recipient contexts passed. This is retained without retry/tuning; visual
  reasoning versus evidence selection/coverage remains unidentified pending
  post-block private audit. Source-bound first-video audit SHA256
  `07edea55b8d8a80ae3e5927d943c95c5197bf6a656b755b0f9cb2e924c2d322b`.
- Video5/A: sample_frames, a context-rejected model request, another sample_frames
  action with fewer frames, then successful A4 visual inference on seven artifacts.
  Model input/output7,819/2, finish stop, backend service44.262s; four graph
  nodes/23 edges/13 snapshots, no specialists and max action concurrency1.
  The resulting canonical choice was wrong, not a runtime/format failure.
  Exact original admission reproduction and journal receipt, four empty stores,
  unchanged five runner/server identities, tc restoration, Worker exit and14
  actual SDK contexts passed. Source-bound audit SHA256
  `ebe5f45c93bda035cc9df9d97458657e2600b2c5ea82765588a2f81bbc04824f`.
- Video5/B1: sample_frames then successful A4 visual model inference on seven
  artifacts, with no context rejection. Model input/output7,760/2, finish stop,
  service44.144s; two graph nodes/seven edges/seven snapshots, no specialists
  and max action concurrency1. Exact original admission/journal, empty stores,
  unchanged five resident identities, cleanup, Worker exit and six actual SDK
  contexts passed. Source-bound audit SHA256
  `4ddbed36cdcfd0ee4ed3796748c786e348ffb4aa459f4ec8edfc98521230e377`.
- Video5/B0: sample_frames then successful A4 visual inference on seven artifacts,
  no context rejection,7,905input/2output tokens, finish stop, service44.610s.
  Two nodes/seven edges/seven snapshots, no specialists, max concurrency1.
  Original admission/journal, four empty stores, five stable resident identities,
  tc restoration, Worker exit and six actual SDK contexts passed. Source-bound
  audit SHA256 `6c40c24de1d5b4b2935fa4d11b31498048240d00065f07048e6d710f424e2100`.
- Video6/B1, task hasha530f885312b82f6: sample_frames then successful A4 visual
  model inference on six artifacts, no context rejection,6,707input/2output tokens,
  stop, service37.782s. Sampling operator work25.903s; two nodes/six edges/seven
  snapshots, no specialists and max concurrency1. The larger fixed video payload
  took20.753s to materialize, separate from zero Agent artifact movement. Original
  admission/journal, empty stores, five stable resident identities, Worker exit,
  cleanup, terminal provenance and six SDK contexts passed. Audit SHA256
  `639b8718d11b114f7a98980d717c1cbad7a2b7218164d6de8c6266c22c2499a3`.
- Video6/A: sample_frames, a context-rejected model request, then a successful
  A4 visual model invocation using three already materialized artifacts. Model
  input/output3,411/2, stop, service19.035s; three nodes/35 edges/ten snapshots,
  no specialists and max concurrency1. Manager continued after typed preflight
  and schema/phase observations without hidden repair or retry. The initial
 233,097,342B video materialization took650.833s of753.030s E2E, separate from
  zero Agent artifact movement. This setup-dominated result is not an Agent
  communication-saving claim or a causal comparison with the different Planner/
  method/network ninth cell. Original admission/journal, four empty stores,
  five stable resident identities, cleanup, Worker exit, terminal provenance and
  ten actual SDK contexts passed. Audit SHA256
  `26e77b78caa1b341ebfeb82e29135e1a70dde2cfdad0d470c8de48d5e229b4f9`.

Actual feedback-wire review of all ten settled cells matched persisted provider
requests, not just trace declarations: 64 Manager plus64 Verifier contexts,
23 exact B1 pre-decision profiles,32 exact A/E ledgers and14 exact E rule payloads.
All Verifier requests used the fixed frozen model and contained none of the
profile/ledger/rules message prefixes. B0 had none of these feedback messages.
The existing full recipient scans had no findings. Advisory rules were the same
canonical payload throughout; visibility is not internal adoption or causal
optimization. Owner-local feedback audit005 SHA256:
`2cca663e95ea0c5964308fd7c434cc79f74cf0dea11df28788ca443b986aca3b`.
The nine-cell audit004 is preserved with SHA256:
`0223640e8c48c4a67d7a01015b0bcf72ff9bdce37a0a73d908e5a92931c82a60`.
The eight-cell audit003 is preserved with SHA256:
`16a68ee56c944055ff0f2278086403e9b96db6f6abb1a3850e8d066acd552dbf`.
The seven-cell audit002 is preserved with SHA256:
`7d1ee33a2d8846f0914de6f36fe38add6637c21ca7a937625fa8de04ad7733de`.
The six-cell audit001 is preserved with SHA256
`a35c518dda67f761937608cf87661d44c12f3d85536b9c6d4c1253ea2aa2f7e8`.
No support/corpus/store-body or gold scans were performed while the queue was live.

These unmatched Planner/method/network cells cannot establish an E or B1 causal
effect, a matched speedup, stable infrastructure adaptation or statistical
significance. B1's longer successful trajectory is retained unchanged, not
treated as a bug to tune away. Evidence coverage/semantic sufficiency and causal
profile adoption remain separate questions for the full audit.

Authoritative owner-local snapshot009 SHA256:
`cee444fe3a3cd800f16bf0f334e8071cb829c07224ff3030a23fbff847881ac9`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`154a1768f12316ddf6650fc89ea3e0de564f28a320a7f158ed16fc118ec0e7d3`.
Ten admitted cells, ten preserved attempts, zero pending; no confounded or
operational-excluded attempts. Earlier snapshot008 SHA256:
`7f63d2ab27420269f8db1005e01905c0b87c78e3c3202a9d8f0a8c0bf896433b`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`7089a591c244a1a01bb8d085c7446e6a9786e3a109c915b9c4a577e9d9e582c6`.
Nine admitted cells, nine preserved attempts, zero pending; no confounded or
operational-excluded attempts. Earlier snapshot007 SHA256:
`48dfed8298f46726df7534e3656428b0f5ff522d8940b390f4788ef7e01e2f98`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`6c0da78fc0ed3ab39924638a5adef52fc925a89bbcfc4ce268d165e0f82f787f`.
Eight admitted cells, eight preserved attempts, zero pending; no confounded or
operational-excluded attempts in this held-out block. Earlier snapshot006 SHA256:
`b18abcb244ce89cd6f6d40254667b809cb1b1080673a2db4a21f6408b662fb76`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at the seven-cell checkpoint:
`c95be495615079c6eddda3ffc8ee376a6d636c32a42ba220a0bf535f40fd20c5`.
Its eighth reservation was pending, not completion. Earlier snapshot005 (six
settled cells) remains preserved:
`3df2cca139d9fae2e99c7eb1f7ef6f7b9ddfd4464881de62ef4729101beb6555`.
Earlier snapshot004 SHA256:
`cbfc4ee0a97a7d1c8cb11c172140e14cb2b01d7816a17362fef4daf68adde2e5`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`4cfc30a5cb72954293d5670ceb1cc5677d6e56adabe3a237972095bc959cd8e7`.
Earlier snapshot002, covering the first three cells, remains preserved:
`0cb9a56a44ed0707482c237958a8ef9a760d2c27e85ab06a42ad01b54230bc9c`.
At snapshot003, the fifth cell was pending; its reservation is not completion.
Snapshot003 SHA256 remains preserved:
`7b9bdfa4d7d3f0b969cea7eec7a0324be366a513e605386123aa54366e82db8e`.
No complete-table aggregation, private-body scan, new method, retry, prompt
tuning or replacement was performed. The remaining frozen schedule continues.
See [first-cell audit](large-scale-resident-phase2-first-cell-v1.md) and
[collector validation](large-scale-resident-phase2-projection-v1.md).
