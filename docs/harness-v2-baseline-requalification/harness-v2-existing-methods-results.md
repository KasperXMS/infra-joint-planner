# Existing methods under Harness v2 H1

The frozen 36-cell Stage 2 matrix completed once, with no selective reruns. It
used the same local Qwen3.8-27B Planner, H1 terminal contract, cloud Verifier,
Executor pool, Physical Scheduler and evaluator for Blind, Raw Aware and Cost
Ledger. The three previously studied anchors were MultiHop-RAG
`multihop-rag-train-9bae0079038050a37a1ae583`, LongBench-v2
`66f7c780bb02136c067c35e8`, and Video-MME `video_mme:795`. Each method ran
twice per anchor and network. The two trials are model samples, not independent
task samples.

| Network | Method | Cells | Completed | TSR (score 1) | Verifier raw-schema failures | Known cloud USD | Sum E2E, s | Physical work, s | Transfer, MB |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Slow | Blind | 6 | 3 | 2 | 2 | 0.7797 | 2630.3 | 341.2 | 583.400 |
| Slow | Raw Aware | 6 | 4 | 1 | 2 | 0.7681 | 2392.0 | 315.1 | 582.484 |
| Slow | Cost Ledger | 6 | 3 | 0 | 2 | 0.5033 | 2077.1 | 106.3 | 582.452 |
| Fast | Blind | 6 | 4 | 1 | 1 | 0.9330 | 1059.8 | 281.2 | 583.400 |
| Fast | Raw Aware | 6 | 4 | 1 | 2 | 0.6795 | 856.8 | 240.0 | 582.476 |
| Fast | Cost Ledger | 6 | 4 | 1 | 2 | 0.6331 | 725.9 | 295.2 | 582.474 |

Across both networks, Blind completed 7/12 and scored 3/12; Raw Aware
completed 8/12 and scored 2/12; Cost Ledger completed 7/12 and scored 1/12.
Thus the lower aggregate time or known API spend of the two aware methods is
not a quality-preserving efficiency gain. In particular, Slow Ledger's low
physical work accompanies zero correct answers. Unknown local GPU monetary
cost is not counted as zero.

The paired score outcomes below use `X` for a run stopped before a valid
evaluator score and `0`/`1` for the unchanged evaluator result. Every entry is
one real cell; full per-cell receipts are in the redacted analysis export.

| Anchor | Network | Trial | Blind | Raw Aware | Cost Ledger |
| --- | --- | ---: | ---: | ---: | ---: |
| MultiHop | Slow | 1 | X | 0 | X |
| MultiHop | Slow | 2 | 0 | 0 | X |
| MultiHop | Fast | 1 | 0 | X | 0 |
| MultiHop | Fast | 2 | 0 | 0 | 0 |
| LongBench | Slow | 1 | X | X | 0 |
| LongBench | Slow | 2 | X | X | X |
| LongBench | Fast | 1 | X | X | X |
| LongBench | Fast | 2 | X | 0 | X |
| Video-MME | Slow | 1 | 1 | 0 | 0 |
| Video-MME | Slow | 2 | 1 | 1 | 0 |
| Video-MME | Fast | 1 | 1 | 0 | 0 |
| Video-MME | Fast | 2 | 0 | 1 | 1 |

The 14 non-completed cells comprise 11 malformed original Verifier function
calls, one Verifier result failing semantic validation, one Manager turn-budget
exhaustion and one terminal choice-format violation. All remain in the
denominator. One Manager raw-schema failure was observed and handled within the
original turn budget. Physical action preflight rejected 63 over-context
requests explicitly (`context_limit_exceeded`); there were no silent context
integrity failures. The last issue is a real workflow/capability limit, not a
reason to erase or rerun a cell.

Integrity checks passed for all 36 cells: unique result receipts, no incomplete
claims, all Workers drained and exited, no recorded system-level problem, and
both traffic-control regimes restored their original qdisc. Calibration
measured 2.760–2.796 Mbps for Slow and 91.761–95.388 Mbps for Fast across
controller–edge directions. The network's configured added RTT was 50 ms and
5 ms respectively; the TCP calibration's mean RTT is not an exact independent
RTT measurement. The Stage 2 batch spanned about 2 h 48 min from first claim
to completion, including network shaping and cleanup. Raw traces remain on
the controller; committed exports contain only redacted counts, workflow
structure, hashes and receipts.
