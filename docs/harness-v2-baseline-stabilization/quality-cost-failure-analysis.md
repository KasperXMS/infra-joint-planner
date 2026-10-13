# Quality, cost and failure censoring

The frozen [H1 receipts](../../results/harness-v2-baseline-requalification/final-sanitized-analysis.json) and [per-cell structural export](../../results/harness-v2-baseline-stabilization/workflow-variation.json) distinguish score 1, completed score 0, incomplete, and physical context rejection. Cost is a vector: E2E, known cloud USD, physical model-service work, transfer, and Manager/Verifier/Specialist requests and tokens. Local GPU monetary cost is **unknown**. Failed cells remain in all denominators and consume actual cost.

| Method | Completion | TSR | Sum E2E s | Cloud USD | Physical work s | Transfer MB | Manager / Verifier calls | Physical inference calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Blind | 7/12 | 3/12 | 3690.1 | 1.7127 | 622.5 | 1166.8 | 123 / 123 | 11 |
| Raw Aware | 8/12 | 2/12 | 3248.8 | 1.4476 | 555.1 | 1165.0 | 88 / 88 | 11 |
| Cost Ledger | 7/12 | 1/12 | 2803.0 | 1.1364 | 401.4 | 1164.9 | 74 / 74 | 10 |

**Trace-supported observation.** Ledger's lower cloud bill accompanies fewer Manager/Verifier calls (74 each versus Blind's 123), less physical work, and lower TSR. The slow MultiHop Ledger cells are especially clear early-stop cases: both used 6 `bm25_retrieve` plus one logical `invoke_model` but had no physical inference and no nonempty Manager model output before Verifier failure; they spent $0.0274/$0.0288. Other Ledger failures, especially LongBench, did use physical inference and stopped late, so “all savings came from short failures” is unsupported. In completed MultiHop Ledger fast cells, longer retrieval/model trajectories still scored 0. This points to protocol censoring **and** unresolved planning/evidence/synthesis quality, not one exclusive cause.

The 10 Aware cells without score 1 consumed 2170.6 s and $1.2626; the 11 Ledger cells without score 1 consumed 2736.1 s and $1.0745. These are observed subset costs, not matched estimates. Of 24 Aware/Ledger-vs-Blind pairs, only Slow Video trial 2 has both sides score 1: Aware versus Blind has E2E 866.6/969.7 s, physical work 25.4/38.0 s, cloud $0.0787/$0.0838, and identical 282.442 MB transfer. In Slow Video trial 1 Aware scores 0 while Blind scores 1. No method has two-trial replicated quality-preserving cost improvement. Fast Video trial results reverse success across trials, further weakening a stable cost strategy inference.

Manager prompt/output tokens were Blind 1,592,816/59,397, Aware 1,042,108/45,633, Ledger 827,295/37,648; Verifier tokens were 1,330,495/20,696, 974,843/14,684 and 766,096/12,609 respectively. Specialist was not invoked in Stage 2. Known cloud USD comes from the Verifier; local Manager and Executor monetary cost cannot be priced. Physical work is measured model-service time, not API latency or waiting. The Video source transfer alone is about 282 MB per cell under both networks, so network speed changes E2E without demonstrating a logical-workflow transfer reduction.

There were 63 explicit physical context rejections across 36 cells, with no silent truncation. Those rejections and the 12 Verifier protocol failures are distinct from wrong completed answers. Thus the aggregate cost ranking is not a quality-preserving efficiency ranking, and neither Aware nor Ledger can claim a full-resource monetary saving from these receipts.
