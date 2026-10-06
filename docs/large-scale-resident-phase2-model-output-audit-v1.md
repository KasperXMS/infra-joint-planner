# Held-out failed model-output accounting audit

2026-10-07, Asia/Hong_Kong. This is an action-level metadata/source audit while
cell16 remains in flight, not final admission, task failure classification or
private semantic review. No experiment, runtime, prompt, budget or method changed.

Cell: `phase2-multihop_rag-5-a60f56ec789bf3ae-p1-fast-B0`, attempt1.
The bounded specialist requested a materialized `application/json` model output.
Its logical observation carries `validation_failed` with the exact known failure
message `model output is not valid JSON`. The original model-outcome event reports
`physical_selection_succeeded=true` and `reached_model_inference=false`.
That negative flag must not be used to claim this request never reached inference.

The authoritative frozen Worker003 source and its execution-freeze source map
were independently rehashed. The handler first awaits the real deployment backend,
then performs `json.loads(completion.text)` for JSON materialization. The observed
error is emitted only after that backend completion. The model telemetry is not
returned on this error path. Therefore this is not a context-preflight rejection;
it is a model-output JSON compliance failure after backend completion. Neither
the generated text nor benchmark gold/supporting bodies were read/exported in
this audit. It does not establish whether the malformed output was prose, fenced
JSON, syntactically invalid JSON or an output-limit event.

Accounting distinction:

| Quantity | Evidence / interpretation |
| --- | --- |
| Backend completion before JSON check | Proven by exact failure and frozen Worker source ordering |
| Successful returned model telemetry for this action | Absent, not a successful receipt |
| Input/output tokens, finish reason and backend service work | Unknown; do not insert0 |
| Physical action elapsed time | Not a replacement for model service latency |
| Original `reached_model_inference=false` flag | Preserved, but insufficient to conclude zero inference |
| Existing spent Ledger | Such execution failures use unknown inference/work, not false/zero |
| Specialist continuation | A distinct later action followed the typed failure; not automatic backend retry |
| Final task/evaluator outcome | Still pending at this audit; no quality claim |

The frozen Ledger source is independently hash-bound too: execution failures with
incomplete telemetry remain `inference=None`, increment unknown inference calls,
and keep incomplete model service totals unknown. The separate successful-receipt
counts used in the results table are not asserted to be all actual backend calls.
No online accounting or failure message was rewritten to rescue this trajectory.

Immutable owner-local diagnostic, under
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis/`:
`resident-phase2-cell016-json-materialization-audit-001.json`, SHA256
`e18b16fde2b21de7feb48394afa5d0d53ec2ae61859af034e954ee318b4a9a7f`.
It binds the partial trace at capture and the exact Worker003 server, Ledger and
execution freeze. Partial trace hashes are capture-specific, not final trace
digests; the original trace continues growing. Planner/model calls made by this
audit:0. It does not authorize a replacement, tuning, hidden repair, private-body
scan or inference-cost/quality comparison. Final original admission and actual SDK
recipient checks must still run after the atomic settles; full192-cell private
semantic/failure/adoption audit remains gated on global inactivity.

## Subsequent terminal checkpoint (21:37Z)

The same atomic completed normally, valid terminal/evaluator score0, and exited0.
Original controller exited1 because its admission conservatively gated the exact
known JSON error. The rejection is preserved; it is not grounds for semantic
retry. Original admission and journal independently reproduce exactly; fresh
stores/Worker exit/residency/tc/direct terminal and34actual SDK contexts pass.
Independent settled audit SHA256:
`d8500a885a00584c46ce9a63f36a0a13b040610edcbf5248cadab6cb54d11ba4`.

Actual counts:13Manager/13Verifier,8specialist turns,48physical actions,
5successful inference telemetry receipts and at least one additional backend
completion established by the JSON failure. Missing failed-call telemetry remains
unknown. Three read-size failures and three context rejects returned to the
Agents, which continued. E2E1884.311s; graph48nodes/37edges/145snapshots/peak6.
Complete transfer/model-work totals remain unknown, even though successful
transfer receipts total43,046B/.881s. Initial7,696,522B/1.511s is separate.

The specialist returned an SDK agents-as-tools answer and handed off five
InformationObjects. That answer is not byte-identical to its last physical model
output; this follows existing wrapper semantics and alone does not prove a new
hidden benchmark finalizer. No later physical action used those five artifact IDs
as inputs. The parent still received the specialist answer in SDK tool context;
do not infer semantic non-use or causal failure from artifact-input absence.
The root terminal comes directly from a separate successful prompt-only model
action. Actual supporting-evidence adequacy and wrong-answer cause remain unknown
until the complete private post-block audit.

Exact append-only admission review and unchanged-schedule continuation are being
prepared separately. This terminal checkpoint does not claim a written sidecar,
admitted16th cell or restarted queue. See
[preparation](large-scale-resident-phase2-json-review-preparation-v1.md).
