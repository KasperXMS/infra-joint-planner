# Resident cell 052: exact Verifier input-policy audit

2026-10-06. MultiHop representative 1 / P1 / Fast / A, task
`multihop-rag-train-4b6de4acbde051fee1f727f3`, original three nonsemantic hash
shards, same native runtime/tools/model pool/scheduler and frozen budgets.
Run `large-scale-cost-guidance-resident-v1-phase1-multihop_rag-1-29e45040dce39dae-p1-fast-A-attempt1`.
No retry, replacement, input censorship, prompt tuning or semantic repair.

## Original failure and exact classification

Original sequence 104 settled confounder at `2026-10-05T21:12:11.337293Z`:
single `unclassified_API_failure_requires_audit` gate. Original admission SHA
`c02db9c0b0008e6816b072611bc3308bb4c8ed18375a25de96c0f3f1e4d5166b`;
original settlement SHA
`eaf1587c2298f76653d53f459a05959912c4a919da80f77b185e9a7a38fa2842`.
Queue 006 and atomic process `2390501` actually exited; Workers exited and all
five resident-instance checks passed. Original journal/admission are unchanged.

Actual SDK HTTP receipts: nine Manager successes, eight Verifier successes,
then the ninth fixed Blind Qwen Verifier call returned HTTP 400
`data_inspection_failed` (both code/type and exact policy message match the
unchanged reviewer). Failed call `8a66818a38624289b3799206e52f43b2-1`, usage absent.
Terminal code `logical_loop_failed` / `AgentLoopError`, no operational incident,
no terminal answer or original evaluation. Missing score/format are not zero.

The existing exact single-gate reviewer independently reproduced the original
full admission and bound 102 original evidence files, actual recipient/method
privacy, exit/residency and execution/source checks. Exactly one provider
input-policy refusal, zero parse/record-field failures. New append-only sidecar
in remote `provider-policy-adjudications/`, canonical SHA
`c4be7f8b386f9453c2ba7fbd7a74c4330c974e9eaff5cfd8cabe6d85d1c4e17f`,
file SHA `d797c075bb9ae375e64fba2a91552364fd667a8b3c4f6713e88c1ea840df0708`.
Effective admission SHA
`0607009030817c32da8556ef6ca87882f09bdebfa07211ce147e416cce709b7a`:
valid **nominal provider-input-policy failure**, replacement forbidden.
No broad HTTP allowlist, reviewer/source change or original-receipt rewrite.

Append-only remote `analysis/resident-cell-052-summary-001.json` file SHA
`219fbc3650cb051db34579aea643a46e53a8cbb7fd029ac2704065975b2e4a14`.
The individual projection reproduces the exact sidecar proof against the
original journal attempt, original versus effective receipts, all eighteen
actual SDK contexts, exit/residency, and trace/result/source hashes. It is not
a comprehensive Phase I semantic audit or a newer complete-block snapshot.
No task body, raw prompt, gold/private evaluator or model payload is exported
through the local PC; private-audit/pruning flags remain false.

## Actual execution before the refusal

| Measurement | Observed value |
| --- | --- |
| Manager / Verifier calls | 9 / 9, including one refused Verifier call |
| Specialists created / specialist turns | 0 / 0 |
| Physical actions | 11: ten succeeded, one context preflight rejection |
| Successful tool executions | six BM25 + three bounded reads |
| Model actions / actual inference | 2 / 1 |
| Physical model input / output / finish | 366 / 68 / stop |
| E2E until explicit run.failed | 98.863 s |
| Fixed initial placement | 7,696,522 bytes / 1.475 s |
| Complete action artifact movement | 0 bytes / 0 s |
| Complete tool-only work | 2.481 s |
| Complete backend inference work | 1.035 s |
| Manager / measured Verifier work | 66.476 / 26.339 s |
| API known subtotal | USD 0.1802288231, seventeen known calls |
| Complete API cost | unknown, failed call usage missing |
| Graph nodes / declared artifact edges / snapshots | 11 / 9 / 34 |
| Actual concurrency / overlapping action wall time | maximum 3 / 1.362 s |

Two rounds of three shard-local retrieval actions used A4/A5/A28. After a
submitted context rejection, the Manager performed three bounded reads and
one successful strong GPU0 resident 27B model action. Continuation is observed,
not an automatic retry, new recovery heuristic or proof of ledger causality.
Two semantic-validation and two phase-restricted SDK failures are retained but
are not extra physical calls. The failed preflight did not reach inference.

Model input without declared artifact edges does not establish absence of
evidence: bounded reads may inform Manager context and the later prompt. Do not
infer evidence loss, hallucination or final answer quality without the private
post-hoc audit. The run's primary terminal failure is the proven cloud input
policy refusal. Context recovery is a trajectory feature, not its terminal
cause. Neither the twenty-turn nor sixty-four-physical-call ceiling was reached.

Complete transfer/backend totals are supported by persisted receipts, not
imputed from absent output. Inclusive Worker work already contains model
execution; do not add it to backend work. Overlapping work/path timings are not
an E2E decomposition. A short aborted run with missing quality is not a
quality-preserving optimization success. Known API estimates are frozen
regional list prices, not invoice totals or estimates for the missing call.

## Unchanged-source control continuation

Before control freeze 006: full pytest **1077 passed in 37.83 s**, Ruff passed,
strict Pyright **0 errors / 0 warnings**, `git diff --check` passed. No logical,
physical, method, model, prompt, tool, evaluator or budget source changed.

`queue-control-freeze-006.json` canonical SHA
`0b68d16f2f3ee8dd7e0e41065cff0c3383023ba9d214c13b624536e6588c088d`,
file SHA `3e7d173df35cd472c22cd260b78a02c4bb9fff4c8f918287e676977f534533d8`.
Measured execution remains revision `90fd30c531f3ad879dcaf5394b7633bcf7b07c3b`,
freeze `4090d46e5f3e7c3b25ae56355c830160c6688b1ca1c9e61ed5ca3ad93ba43e2c`.
New control binds the new exact sidecar and unchanged controller/reviewers.

Queue 007 PID `2437975` started `2026-10-05T21:22:58.720076Z`, actual cmdline
verified at launch. Only never-started remaining cells may proceed. Cell 052
is not replaced; original six rejected admissions and all exact sidecars remain
immutable. Re-read live process/journal state before claiming cell 53 execution.

The effective new nominal boundary is 52, not 52 completed/evaluated runs.
Old 42 remain closed/unpooled and separately count toward the global cap.
Finish all 168 Phase I outcomes and full private semantic/recipient/failure/
adoption audit before frozen pruning, preregistered Phase II and final Q1–Q10
reports. No early winner, new method or completed-goal claim.
