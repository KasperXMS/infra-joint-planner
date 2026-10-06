# Resident checkpoint148: Optional-Card interface visible, unused

2026-10-06. Cell `phase1-multihop_rag-2-2d3129ed85c03f62-p2-fast-B`,
attempt1, completed normally with the original evaluator score1.0 and valid
terminal format. No retry/replacement, prompt tuning or manual recovery.

## Actual execution and interface adoption

The single Manager naturally composed:

`three source shards -> aggregate_artifacts -> bm25_retrieve -> invoke_model`

All three physical actions selected A28. Aggregation moved the original A4
shard (2,772,674bytes/2.132796s) and A5 shard (2,431,922bytes/0.411654s) to A28;
the third shard was already local. Retrieval and model consumption then stayed
local. The terminal model action consumed the retrieved artifact, materialized
its answer and supplied the successful terminal candidate. Its actual deployment
was `resident-a28-qwen35-27b-v1`, not the cloud Manager model.

The complete actual root provider responses contain exactly one aggregate,
one BM25 and one invoke_model call. All3Manager requests exposed the optional
`estimate_*` tool interface; actual query attempts/cards/matches are0. The
3observed ready-action decision opportunities therefore have0query adoption.
This is verified exposure plus non-adoption in one trajectory, not a claim
about B's performance across both Planners/workloads or grounds for pruning.
No candidate comparison or quote was used.

## Measured outcome

| Metric | Observed |
|---|---:|
| Completion / format / evaluator score | true / true / 1.0 |
| Manager / Verifier calls | 3 / 3 |
| Created specialists / specialist turns | 0 / 0 |
| Physical actions / successful tools / inference | 3 / 2 / 1 |
| Failed observations / context rejections | 0 / 0 |
| Actual model input/output tokens | 7,925 / 3 |
| Graph | 3nodes / 2edges / 10snapshots |
| E2E | 161.537422s |
| Complete action traffic | 5,204,596bytes / 2.544449s |
| Fixed initial placement | 7,696,522bytes / 0.800086s |
| Tool work / model service work | 1.207797s / 136.860806s |
| Manager / Verifier work | 10.926477s / 8.376254s |
| Frozen list-price API estimate | USD0.051154821350 |

API cost uses all6known usage receipts, separately3Manager/3Blind Verifier.
The estimate is not an invoice. Service/work sums are overlapping/non-additive,
not an exact E2E decomposition. Setup movement remains separate from Agent
movement. Model/service work dominates this trajectory, but no general workload
or method claim follows from one run. Correctness does not prove that every
supporting fact was retrieved, preserved or selected; semantic retention still
requires the gated private post-block audit.

## Independent validity and immutable evidence

The original admission was independently reconstructed and matched its durable
settlement hash. Four initially empty stores, fresh Worker processes, all6actual
SDK recipient contexts, Worker exits, five unchanged resident model instances
and successful tc cleanup passed. The live process's actual environment was
execution004/revision `0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`; its Pythonpath
contained only004src/scripts. Its config exactly matches the frozen schedule.
The previous malformed-JSON cell147was not retried.

Evidence stays under `/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

| Append-only proof | SHA256 |
|---|---|
| `analysis/resident-source004-cell148-live-audit-001.json` | `5f64d52e1c48917c6602ca645c0c7b19f9cbdcacc9064eff2ee11c2f89dddda2` |
| `analysis/resident-source004-cell148-settlement-audit-001.json` | `3d21c82f39ba8045fc3e79ed586a6c246d2f228f5ac2e77b043913d0ecc28d08` |
| `analysis/resident-source004-cell148-information-path-audit-002.json` | `ec7edfb653f96168178e2076c2f9b13dbf3ec50a28ac25f22112df299f0ff7f9` |
| Original trace | `e7ba9c0b82818dd69ff8d3dd1b7be110675219c3a99ee75dae1ac5cd985d87a1` |

Information-path001is preserved. An ad-hoc export initially looked for wrong
TransferReceipt field names `size_bytes/latency_ms`, producing nulls in that
supplemental metadata only.002corrects the projection to actual
`bytes_transferred/duration_ms`, binds001's hash and verifies its sums against
the already correct complete settlement telemetry. The original trace/result
and measurements did not change; this is not a run confounder or rerun reason.

Snapshot050was captured at147valid/166attempts/0pending before this new cell.
This independently audited settlement brings the admitted total to148/168;
it does not retroactively change snapshot050. At14:03:42Z, Queue021 PID1114748
was owned/live on the next original cell, Video representative2/DeepSeek/Fast/D,
attempt1 (atomic1135060), with four Worker starts and actual SDK-loop events.
That run was still pending, not a completed149th sample. Old42remain unpooled;
full168private/failure/recipient/adoption audits, frozen pruning, actual held-out
PhaseII and finalQ1–Q10are still outstanding. No new method or semantic tuning.
