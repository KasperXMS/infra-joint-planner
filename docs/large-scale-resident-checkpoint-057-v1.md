# Resident-block checkpoint 057–058

2026-10-06. Original cell 57 settled valid at sequence 114,
`2026-10-05T21:40:41.901517Z`. New nominal-outcome boundary is 57/168,
including preserved earlier exact-reviewed failures, not 57 successful runs.
No retry, replacement, semantic tuning or early pruning; historical 42 remain
closed and unpooled. The measured app and control freeze are unchanged.

## MultiHop representative 2 / P1 / Fast / B

Task `multihop-rag-train-fe71f374676e35359d12c83e`, same three hash-nonsemantic
shards with union representing the complete corpus. Manager/specialists use
`deepseek-v4-pro`; independent fixed Blind Verifier uses `qwen3.8-max`. Fresh
Worker processes/stores, five already-resident model instances, 32K/2048
contracts, finite tools, scheduler and original evaluator are unchanged.
Fast is 100 Mbps / configured 5 ms, not measured symmetric RTT.

| Measurement | Observed value |
| --- | --- |
| Completed / canonical terminal / original score | yes / valid / 1.0 |
| Manager / Verifier turns | 7 / 7 |
| Specialists / specialist turns | 0 / 0 |
| Physical actions / actual inference / context rejects | 8 / 1 / 1 |
| Executed graph | 3 BM25 → rejected model → 3 BM25 → successful model |
| E2E | 188.770 s |
| Fixed initial placement | 7,696,522 bytes / 0.882 s |
| Complete action transfers | 18,072 bytes / 0.063 s, two receipts |
| Complete tool-only work | 2.413 s |
| Complete backend work | 123.182 s |
| Actual model input / output / finish | 7,072 / 3 / stop |
| Manager / Verifier work | 43.358 / 19.316 s |
| Frozen-list-price API USD estimate | 0.1014922920, all fourteen usages known |
| Actual SDK recipient contexts audited | 14 |
| Graph nodes / declared artifact edges / snapshots | 8 / 6 / 25 |
| Node states | 7 succeeded, 1 failed |
| Actual maximum action concurrency / overlap | 3 / 1.287 s |

Each three-action retrieval round executed on A4/A5/A28. The successful
model action selected A28's resident 27B deployment. Both abstract model
requirements are classified statically feasible; first actual context preflight
rejected the full request. It did not reach inference. The subsequent retrieval
round and legal inference are natural continuation, not a hidden automatic
repair or operational replacement. No unmeasured failed execution/inference
appears in these receipts. Inclusive Worker/model-wrapper work contains backend
time and must not be added to it; overlapping work is not an E2E decomposition.

Two semantic-validation and three phase-restricted SDK failures remain visible
but are not extra physical inferences. Actual raw Manager responses include
seven BM25, three read-artifact and three invoke-model requests; only six BM25
and two model actions entered the physical graph. No successful bounded read is
claimed simply because the Manager attempted one. Dependency frontier width six
does not mean six simultaneous actions: observed concurrency is three, all owned
by the Manager, with no cross-owner overlap or forced multi-agent requirement.

B's optional interface was visible in all seven actual Manager requests;
zero optional query attempts/cards, four observed ready schema-valid root-action
opportunities. Correct completion therefore does not prove use of the optional
cost mechanism or its optimization benefit. Private evidence retrieval,
preservation and terminal selection still require full post-Phase-I audit;
score 1.0 does not establish every intermediate reduction was semantically sound.

Original admission checks passed all fourteen effective SDK recipient contexts,
method/privacy boundaries, evaluator/artifact integrity, Worker exits/residency
and tc cleanup. Complete model work is much larger than this cell's measured
action-transfer work, but this is one descriptive trajectory, not a cross-task
or causal claim. No aggregate accuracy, winner or survivor set is selected.

## Cell 58 / same task / P2 / Slow / C

Original cell 58 settled valid at sequence 116, `21:43:05.225902Z`;
the nominal boundary advanced to 58/168. Completed/validterminal/originalscore1.0;
8 Manager / 3 Verifier, zero specialists, 4 physical actions / 1 actual
inference / 0 context rejects. Three BM25 actions ran on A4/A5/A28; model
execution selected A4 resident VL4B. Maximum actual concurrency 3 / overlap
0.910 s; graph 4 nodes / 1 declared artifact edge / 13 snapshots, all succeeded.

E2E 87.200 s; fixed initial 7,696,522 bytes / 22.235 s; complete action transfer
0 bytes / 0 s; complete tool-only work 1.218 s; complete backend work 20.868 s.
Actual model tokens 7,192 input / 3 output, `stop`; Manager / Verifier work
34.432 / 6.697 s; API USD 0.0750721748, all eleven usages known. All eleven
actual SDK contexts passed original admission/privacy checks; Worker exit,
residency, evaluator/artifact integrity and tc cleanup passed.

C produced five quotes: four consumed, one pending, none discarded/stale;
quote-control work 1.809 s. A phase-restricted quote rejection and two
deduplicated SDK phase-restricted failures are overlapping scopes, not three
extra physical executions. Attempted aggregation/specialist calls do not prove
an executed aggregate or created specialist. One final model artifact edge does
not prove missing other evidence: prompt and accumulated semantic observations
must be privately audited before any evidence-discard classification. Compared
with cell 57, Planner, network and method all differ, as does selected model;
the lower work/bytes cannot be causally attributed to C. No winner or pruning.

Append-only remote `analysis/resident-cell-058-summary-001.json` file SHA-256:
`1be46a367c1aba54cf62c940f6ecbb112f58a769a25d3f2bc324de8bf2c94960`.
Original admission canonical SHA-256:
`278c95e1a05eb5b32c42f3b0e48485ebe6cd6025642a77ecb70128ad0b16bd5e`.
Settlement SHA-256:
`f579db8baafd3a71b5486227794ae48971dd844026af5c6929987c3620d4301e`.
All original evidence remains immutable; full-private-audit/pruning flags false.

## Provenance and actual continuation

Original admission canonical SHA-256:
`a0fddae99033cb8e39a0ccdec8739d6a136fa8ce0173d0f6bfcc93d8e29dde81`.
Original settlement entry SHA-256:
`72bd92452f170eab761cc690fe04bde582358f97e26e0c4568387e436ba2f133`.
Append-only remote `analysis/resident-cell-057-summary-001.json` file SHA-256:
`9eccf865a572cad7c02125ac4b6908a50c357c5731a6bd3368889820d28d8ed9`.
Projection verifies the original hash-linked journal, admission/result agreement,
Worker exit/residency and trace/result/source bindings. Only bounded metadata
leave the owning remote nodes, never dataset/model payload, raw prompts or gold
through the PC. Comprehensive-private-audit and pruning flags remain false.

Queue 007 PID `2437975` and cell 59 atomic PID `2520418` were verified live at
`2026-10-05T21:43:31.848732Z`: MultiHop representative 2 / P1 / Slow / D,
original attempt1, reserved sequence 117 at `21:43:07.637912Z`. This observation
expires and does not authorize restarting a live or completed cell.

Execution freeze 001 / control freeze 006 remain unchanged. This documentation
does not create a new execution freeze; latest full tests before that actual
control freeze were 1077 pytest passes, Ruff/strict Pyright/diff passes. Complete
all 168 new primary outcomes and comprehensive private/recipient/failure/adoption
audit before screening/pruning and legitimate Phase II within
`42 + 168 + 48m <= 420`, then all final reports/Q1–Q10. Full objective remains
unfinished and active; no pause/block/completion is asserted.
