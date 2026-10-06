# Resident Phase II results — in progress

Live continuation at2026-10-06T22:47Z: cell17,
`phase2-multihop_rag-4-fffab28c23fbdeaf-p1-fast-E`, attempt1,
atomic2188408 is owned/live. This is a pending reservation, not another result:
the settled table below remains16. Its initial four Worker stores were empty,
five resident instances were attested before execution, and the atomic process
uses only archived execution004src/scripts with revision
`0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`. External controller/private-audit
namespaces are absent from the atomic PYTHONPATH. Start receipt SHA256:
`dd29530e68dcc36230b3f07ad6ea2875f60d2b012aa1fa604efc3c0c7028d669`.
Completion, quality, final residency, tc cleanup and recipient audits for this
cell are not yet claimed. No completed sample was repeated.

Checkpoint: 2026-10-06T22:20:09Z / 2026-10-07 06:20 HKT. Sixteen of 192 nominal
held-out cells are effective valid samples; no reservation was pending at this
snapshot. Cell16's raw JSON audit rejection is preserved and source-bound reviewed,
not silently rewritten or rerun. These are
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
| Video6 | DeepSeek / Slow / E | true / valid / 1 | 6 / 6 | 5 / 3 | 1 | 802.365 | 233,097,342 / 650.722 | 0 | 0.285777 |
| Video6 | Qwen / Fast / B0 | true / valid / 1 | 5 / 5 | 3 / 1 | 1 | 101.233 | 233,097,342 / 20.537 | 0 | 0.184910 |
| MultiHop5 | Qwen / Fast / E | true / valid / 0 | 10 / 10 | 13 / 1 | 2 | 318.009 | 7,696,522 / 1.339 | 5,204,596 | 0.234685 |
| MultiHop5 | DeepSeek / Slow / A | true / valid / 1 | 14 / 14 | 22 / 10 | 3 | 682.445 | 7,696,522 / 22.219 | 0 | 0.394572 |
| MultiHop5 | Qwen / Slow / B1 | true / valid / 1 | 10 / 10 | 13 / 2 | 1 | 1034.529 | 7,696,522 / 22.042 | 5,204,596 | 0.202958 |
| MultiHop5 | DeepSeek / Fast / B0 | true / valid / 0 | 13 / 13 | 48 / 5 | 3 | 1884.311 | 7,696,522 / 1.511 | unknown; returned subtotal 43,046 | 0.838502 |

Cell16 completed with original score0,13Manager/13Verifier,8specialist turns,
1created specialist,48physical actions,5successful inference telemetry receipts.
It also has one source-proven backend completion followed by invalid JSON
materialization; five returned receipts are not asserted to be all backend calls.
Three context and three read-size rejects returned to the Agents, which continued.
The48-node/37-edge graph has145snapshots and peak concurrency6. Terminal answer
comes directly from a separate successful prompt-only physical model action;
the original evaluator ran, without a new semantic finalizer.

Five returned model receipts record18,102input/3,468output tokens, all stop, and
1283.773s service work. Complete model work/tokens/finish distribution remain
unknown because the JSON-failed action has no returned telemetry. Successful tool
work9.055s and inclusive model-action Worker work1284.028s are not an E2E
decomposition and must not be added again to backend work. Successful registered
transfers total43,046B/.881s; full transfer totals are unknown because four
execution-stage failures lack complete execution receipts. Initial7,696,522B/
1.511s remains separate. Do not rank observed subtotals as complete costs.

Raw original admission is confounder only for the exact known post-backend JSON
error. Its full admission/journal, stores/exit/residency/tc/direct terminal and
34SDKcontexts independently reproduce; audit SHA256
`d8500a885a00584c46ce9a63f36a0a13b040610edcbf5248cadab6cb54d11ba4`.
Exact offline sidecar SHA256
`916192e8cc7aaf97ad5e789acf6ce8a684ce29a14e11e675855f1180b2338015`
supplies effective valid disposition, preserves score0 and explicitly forbids
replacement. Original journal/admission/trace/result remain unchanged.

Snapshot015 SHA256
`1c62622eab48ad7354d0de9529feba052c3206a66c34a7f2fda1af28ed727ea9`,
journal `4e5d6d964a7a8fa8001a9d8da7760de7130b16d88319efedca8a0817e5d4672c`:
16effective valid/16attempts/0pending/0effective confounders/1preserved original
confounder/0operational exclusions. Exact reviewer and read-once projection
adapter source/freeze are explicitly bound. No score pooling, retry or tuning.
Feedback011 audits252actual contexts,122Manager/122Verifier/8specialist; the
fixed Verifier and bounded specialist remain Blind. Visibility/evidence path is
not a semantic sufficiency or causal adoption oracle.

The first resumed external controller was self-rejected at startup before any
new reservation/Worker/tc/model call. Its exit/console are preserved as a setup
diagnostic, not a benchmark replacement. Narrow controller identity repair is
documented in [preparation](large-scale-resident-phase2-json-review-preparation-v1.md).
Actual continued queue execution must be verified separately. Remaining176cells
and complete post-block semantic/failure/adoption/Q1–Q10 audits are outstanding.
Historical checkpoint descriptions below retain their captured populations.

The fifteenth cell completed with valid direct terminal-model output and original
MultiHop score1. Ten Manager/Verifier turns and13physical actions: one aggregate,
six BM25, three select_fields and three model requests. One model request failed
context preflight; two A28Qwen3.5-27B requests returned actual inference. Separate
phase_restricted and semantic_validation_failed observations returned to the
Manager and did not become physical executions or hidden fixes. No specialists.

The first returned model receipt was6,767input/2,048output tokens, finish_reason
length, service796.637s. This explicit output-limit receipt is retained, not
called a normal stop or silent input truncation. The Manager then submitted a
distinct model action against the three evidence artifacts; its6,723input/2output
tokens, finish_reason stop and116.151s service produced the terminal answer.
This is recorded agent continuation, not an automatic backend retry. Combined
model service work912.788s, tool work9.323s and inclusive model-action Worker
work913.191s must not be double-counted. E2E1034.529s includes initial7,696,522B/
22.042s; registered Agent artifact movement is5,204,596B/14.944s. The graph has
13nodes/18edges/40snapshots, peak concurrency3. Score1 remains the original weak
evaluator result, not proof of evidence sufficiency or optimal cost reasoning.

Original admission independently reproduced exactly and matched the journal.
Four empty initial stores, Worker exit, five unchanged resident identities, tc
restoration, direct terminal-model text and20actual SDK contexts passed. Audit:
`e250fcf465f295562da2bf199badbeb14c23cda5916eea92459aafbec9b34b0f`.
Ten actual B1 feedback deliveries match their corresponding anonymous profile
payloads; visibility does not establish causal adoption or system benefit. No
retry, model reload, prompt tuning or private supporting-body audit occurred.

Snapshot014 SHA256 `1d11e7e3611572ce7c8f4c5876c28aa124d1945025739548d4ac733d335180de`,
journal at capture `658bda5ebee5c52d901334dbd3b959a2fb038effdab67c16c69587391dd80eaf`:
15admitted/15attempts/0pending/0confounded/0operational-excluded. The controller
continues the remaining177frozen cells. Full held-out private/manual semantic,
adoption, failure and Q1–Q10 analysis remain outstanding. Historical checkpoint
descriptions below retain their own capture times and populations.

The fourteenth cell completed with valid direct terminal-model output and original
MultiHop score1. Fourteen Manager/Verifier turns,22physical actions: nine BM25
actions and thirteen model requests, of which three were pre-inference context
rejects and ten returned successful inference telemetry. Actual successful model
selections span A4VL4B, A5VL8B and A28Qwen3.5-27B, three receipts each, followed
by one explicit prompt-only terminal model on4090GPU0. This is real execution on
fourWorkers, not forced routing or an assumption that every resident instance was
selected. GPU1 was not selected in this cell. No specialists were created.

The ten returned receipts record68,285input/446output tokens, all normal stop;
backend service work634.638s. Tool work6.304s and model-action Worker work635.955s
are exclusive receipt categories, not quantities to add again to backend work.
E2E682.445s includes initial7,696,522B/22.219s; registered action artifact movement
is complete0B. Zero movement does not imply no prompts/control traffic. The action
graph has22nodes/21edges/67snapshots and peak concurrency6; overlap/work sums are
not an E2E decomposition. Privacy and semantic evidence sufficiency are distinct.

Original admission reproduced exactly and matched journal settlement. Four empty
stores, five stable resident identities, tc restoration, Worker exit, direct
terminal-model text and28actual SDK contexts independently passed. The recorded
phase/readiness/semantic failures were returned to the Manager, which continued;
none is silently repaired or counted as inference. Independent audit SHA256
`27544644886bfed56e57ec227609319c66ad7b1f6453cde23e3cf274676945a0`.
Fourteen actual Ledger deliveries match trace payloads; visibility does not prove
useful cost reasoning. Repeated inference work is retained, not tuned away.
This is not a matched comparison with cell13: Planner, network and method differ.
Original score1 is not a private semantic-retention oracle or optimizer success.

Snapshot013 SHA256 `68059249e5a3372f48ba101768f2d7c60ce74bb3d482a2590058b3af7c75818e`,
journal at capture `965de01f812c802e262133738926b4de3f58e1f102929f4cc2eb509a6ce55bbf`:
14admitted/14attempts/0pending/0confounders/0exclusions; full block incomplete.
Earlier live proof SHA256
`71047fa18526c7dca344c7ede032cb2c58e93dff6200c02518157a30b0841cac`
verified original atomic1914655/source004/fresh stores/stable residency. One ad-hoc
read-only poll preceded trace creation and raised FileNotFoundError; the next poll
correctly reported an absent trace during preparation. No experiment was restarted
or modified, and this diagnostic race is not a cell failure.

The thirteenth cell, frozen MultiHop-RAG position5 task hash `a60f56ec789bf3ae`,
completed normally with valid direct terminal-model text and original evaluator
score0. It is a valid quality failure, not a system confounder or a retry target.
Actual sequence: aggregate_artifacts; three BM25 actions; a context-rejected
model request; three select_fields actions; another rejected model request;
three further BM25 actions; then successful A28 model inference consuming three
artifacts. Ten Manager/Verifier turns, thirteen physical actions, thirteen nodes,
eighteen edges, forty snapshots, max actual concurrency three, no specialists.
The two context rejects did not reach inference. The sole returned model receipt
records5,145input/461output tokens, finish stop,228.881s backend service work.
Tool work9.669s and model-action Worker work228.959s are separate exclusive kinds;
backend service is included in the latter, not additional E2E time.

Initial three-shard materialization7,696,522B/1.339s is separate from subsequent
registered artifact movement5,204,596B/1.526s. Terminal text equals the successful
model output directly, without hidden finalization. Original admission and journal
settlement, four empty initial stores, five resident identities, tc restoration,
Worker exit and twenty actual SDK recipient contexts independently passed.
Audit SHA256 `74967cfc330b24e9f1a5e4b03e7cd16040d02c8ecd45c4bc377378ecdea33a1e`.
E's ten exact rule deliveries do not demonstrate rule adoption or benefit.
Required-evidence retention and retrieval-versus-synthesis primary cause remain
unknown until the unchanged post-block private audit guard permits investigation.
No supporting/gold/corpus/store-body reads or exported raw API/model output.

Snapshot012 SHA256 `4576c7eae7d368dcc7ab53d68b266a2f4ab3624ade891d5feaa6be4c1b4c9425`,
journal at capture `e074fd3e180a24aa5c750945919e5ea11ff27c395568cef471ea6b5bdc645dae`:
13admitted/13attempts/0pending/0confounders/0exclusions, block still incomplete.
Its earlier live proof, SHA256
`8bbfa4ade78f94f2ad70f4f6a577e1e89ef18103007bbc1e9dfdd0803c965ac3`,
verified actual atomic1894444, execution004-only imports, four empty stores and
stable five-instance identities before completion. Read-only /state at20:23:40Z
confirmed A28in_flight1 and all fourWorkers available; no failover/restart was used.

The twelfth cell used sample_frames, one context-rejected model request, then
successful A4 visual inference consuming three already materialized artifacts.
The returned receipt records 3,450 input tokens, two output tokens, finish stop
and 19.031s backend service work. Five Manager and five Verifier turns, three
graph nodes, eleven edges, ten snapshots, no specialists and max concurrency one.
Original admission was independently reproduced and matched settlement; four
empty stores, five resident identities, Worker exit, tc restoration, successful
terminal model provenance and ten actual SDK recipient contexts passed. No retry
or semantic tuning. A context reject followed by smaller-input continuation is
observable recovery, not proof of an infrastructure-guided optimization.

Append-only snapshot011 SHA256:
`d83b7fe0bec6b78cf4297feb0fb5e78900535064ffeaefef1a8fb9635b6ac2e5`;
journal SHA256 at capture:
`870e698752088f0a70428598a1f6e86808ae900f05c91117b457bc05f6e700c0`.
Twelve admitted attempts, no pending reservation or confounder at this capture;
the live controller remains active, so this is not completion of the block.
Independent twelfth-cell audit SHA256:
`90b2703c7869bf63c8ab144e335802e7b1af057fde80f3b36ee1f671c22a549a`.
All receipts remain owner-local under the existing analysis root. Historical
snapshots below retain their original populations and timestamps.

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
- Video6/E: sample_frames and four model requests: one context rejection,
  two successful A4 visual inferences, then an explicitly selected prompt-only
  terminal synthesis on4090GPU0Qwen3.5-27B. Three returned inference receipts,
 9,253input/6output tokens, all finish stop, total backend work49.627s. The
  successful terminal model supplies the canonical choice; it is not an extra
  hidden finalizer. Five nodes/24 edges/16 snapshots, no specialists and max
  concurrency1. Initial materialization650.722s remains separate from zero
  registered Agent artifact movement and802.365s E2E. Extra visual/model work is
  retained, not tuned away or called a cost saving because quality passed.
  Exact original admission/journal, empty stores, stable resident identities,
  cleanup, Worker exit, terminal provenance and12actual SDK contexts passed.
  Audit SHA256 `536848a75cc0dc5693ad9a5355d2cc5098a6b637d840bb204bfd7aba48ac6c1e`.

Actual feedback-wire review of all eleven settled cells matched persisted provider
requests, not just trace declarations: 70 Manager plus70 Verifier contexts,
23 exact B1 pre-decision profiles,38 exact A/E ledgers and20 exact E rule payloads.
All Verifier requests used the fixed frozen model and contained none of the
profile/ledger/rules message prefixes. B0 had none of these feedback messages.
The existing full recipient scans had no findings. Advisory rules were the same
canonical payload throughout; visibility is not internal adoption or causal
optimization. Owner-local feedback audit006 SHA256:
`f2f75e4ba4f8f21d26e7ae061e570c1b7b7788a693061b4cead709e70639efd7`.
The ten-cell audit005 is preserved with SHA256:
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

Authoritative owner-local snapshot010 SHA256:
`6a50144c235831e74cf6380c81fbe03e504c2bfb689e76e512285e8324e9b552`,
under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`.
Journal SHA256 at that checkpoint:
`abe096a80f48c11c5ca9c77edfa1e8cea7d947638f76733ec3576d3af3243fd8`.
Eleven admitted cells, eleven preserved attempts, zero pending; no confounded or
operational-excluded attempts. Earlier snapshot009 SHA256:
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
