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
