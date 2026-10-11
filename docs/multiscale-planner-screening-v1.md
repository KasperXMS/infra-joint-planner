# Multi-scale Planner screening v1

三任务 screening 已全部完成并计入正式矩阵，无重复执行。4B/9B/Ministral 3B/实际 Qwen3.8-27B 的 TSR 为 1/3、0/3、0/3、2/3；所有候选随后都完成剩余三个正式 cells，未按 screening 成绩淘汰或重跑。筛选仅提供描述性结果，完整结论见[六任务报告](multiscale-planner-results-v1.md)。

Execution state: **complete**; analyzed 42 cells. Missing cells below are not run, never zero-score observations.

Sanitized input SHA256: `6100b61692500ee46b86f050a287c7ee22f71b47fe16a9ddbfae6d065d96ea69`. Base commit `70a75ae`. Raw prompts, answers, task payloads and credential evidence remain on the experiment machines.

Six frozen, previously examined tasks; one attempt per model/task/Skills condition. Results are descriptive: no significance, noninferiority, held-out validation, or universal scale threshold. Schema failures and legitimate budget exhaustion remain evaluation outcomes; no selective score reruns.

The original external-GPU-contention stop remains historical evidence. Current export state is **complete**; preserved stop receipts: 4. A completed authorized continuation can be complete while retaining that stop.

Placement amendment: the first three 4B cells (task indices 1/3/5) used GPU1; the remaining 4B cells use an independent A28 Planner service. The third 4B cell's actual score is retained with its external-contention flag; its Planner service/runner work remains unknown. The 4B six-task cohort mixes placement and contention conditions, so its aggregate cost is not a pure matched hardware comparison. 9B and Ministral use A28; the resident 27B remains on GPU0. Foreign processes are outside experiment ownership.

The continuation Skills allocation is 9B plus resident 27B, six matched tasks each. Timing verification that selection preceded the first 9B benchmark: yes. The old 4B allocation is preserved in the original freeze but is not executed as an extra ablation. Weights, semantic prompts, frozen Skills, evaluator, Scheduler and Executor are unchanged; retained benchmark cells are not rerun.

Tasks 1/3/5 are the preregistered first task in MultiHop-RAG, LongBench and Video-MME. These cells are retained as the first half of the six-task matrix; any placement amendment and contention strata are recorded above. screening is not an independent validation set and its costs must not be counted twice.

All four preselected candidates proceed unless context integrity, safety or budget protection fails. Observed model errors do not create another ability Gate or a score-based selection rule.

The frozen slot `qwen35-27b` is reported as **Qwen3.8-27B [qwen35-27b]**. When the provenance correction receipt is present, its resident weight and projector match the official Qwen3.8-27B registry descriptors, rather than Qwen3.5-27B. The slot, weights and deployment were preserved. Only 4B and 9B provide a same-release Qwen3.5 size comparison; 27B also changes model generation, hardware and MTP/runtime configuration. None of these observational differences isolates a size-only causal effect.

| Condition | Observed/planned | Completion | TSR | Mean original score | Valid/schema attempts | Schema failures | Outcomes |
|---|---|---|---|---|---|---|---|
| Qwen3.5-4B | 3/3 | 1/3 | 1/3 | 1.000 (1 evaluated) | 42/54 | 12 | context_budget_exceeded:1; success:1; turn_budget_exhausted:1 |
| Qwen3.5-9B | 3/3 | 1/3 | 0/3 | 0.000 (1 evaluated) | 14/20 | 6 | control_plane_failed:2; incorrect_answer:1 |
| Ministral 3 3B | 3/3 | 1/3 | 0/3 | 0.000 (1 evaluated) | 4/9 | 5 | control_plane_failed:1; incorrect_answer:1; terminal_contract_failed:1 |
| Qwen3.8-27B [qwen35-27b] | 3/3 | 3/3 | 2/3 | 0.667 (3 evaluated) | 34/34 | 0 | incorrect_answer:1; success:2 |

## Placement and contention strata

| Condition | Manager placement | External contention | Task indices | Completion | TSR | Schema failures | Task E2E s | Independent Planner runner s |
|---|---|---|---|---|---|---|---|---|
| B0 qwen3.8-max | cloud | no | 1,2,3,4,5,6 | 5/6 | 4/6 | 0 | 717.074 | 0.000 |
| Ministral 3 3B | A28 | no | 1,2,3,4,5,6 | 1/6 | 0/6 | 8 | 548.613 | 309.579 |
| Qwen3.8-27B [qwen35-27b] | strong-4090-gpu0 | no | 1,2,3,4,5,6 | 6/6 | 4/6 | 1 | 614.159 | 0.000 |
| Qwen3.8-27B [qwen35-27b] +Skills | strong-4090-gpu0 | no | 1,2,3,4,5,6 | 6/6 | 4/6 | 1 | 650.607 | 0.000 |
| Qwen3.5-4B | A28 | no | 2,4,6 | 0/3 | 0/3 | 7 | 1592.774 | 1202.562 |
| Qwen3.5-4B | strong-4090-gpu1 | no | 1,3 | 0/2 | 0/2 | 8 | 272.526 | 82.754 |
| Qwen3.5-4B | strong-4090-gpu1 | yes | 5 | 1/1 | 1/1 | 4 | 255.311 | unknown |
| Qwen3.5-9B | A28 | no | 2,3,4,5,6 | 2/5 | 1/5 | 12 | 2967.347 | 2522.610 |
| Qwen3.5-9B | A28 | yes | 1 | 1/1 | 0/1 | 3 | 535.647 | unknown |
| Qwen3.5-9B +Skills | A28 | no | 1,2,3,4,5,6 | 2/6 | 1/6 | 34 | 3365.246 | 2925.983 |

| Placement cohort | Cells | Resource samples | Controller GPU min free MiB | A28 min available shared RAM KiB |
|---|---|---|---|---|
| cloud-manager | 6 | 46 | 0:3936; 1:5206 | 22850280 |
| continued-a28 | 21 | 235 | 0:733; 1:2793 | 18876628 |
| existing-resident-gpu0 | 12 | 92 | 0:3936; 1:5206 | 18816144 |
| original-gpu1 | 3 | 0 | none | unknown |

Sampled memory headroom is neither peak model memory nor continuous OOM surveillance. Missing Planner work for the contended third 4B cell remains unknown; its completion, score, API receipts and physical evidence are retained. Mixed-placement cohort resource sums are descriptive only.

| Task index | Condition | Outcome | Original score | Nodes | Artifact edges | Owners | Operators | Schema failures | Later-valid/invalid owners | Identical repeated calls |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.5-4B | context_budget_exceeded | unknown | 11 | 9 | manager:11 | aggregate_artifacts:1; bm25_retrieve:4; invoke_model:1; read_artifact:2; select_fields:3 | 5 | 1/1 | 1 |
| 1 | Qwen3.5-9B | incorrect_answer | 0.000 | 8 | 9 | manager:8 | aggregate_artifacts:2; bm25_retrieve:4; invoke_model:2 | 3 | 1/1 | 0 |
| 1 | Ministral 3 3B | control_plane_failed | unknown | 0 | 0 | none | none | 2 | 0/1 | 0 |
| 1 | Qwen3.8-27B [qwen35-27b] | incorrect_answer | 0.000 | 21 | 18 | manager:21 | bm25_retrieve:18; invoke_model:3 | 0 | 0/0 | 0 |
| 3 | Qwen3.5-4B | turn_budget_exhausted | unknown | 13 | 13 | manager:13 | bm25_retrieve:4; invoke_model:5; select_fields:1; top_k_records:3 | 3 | 1/1 | 0 |
| 3 | Qwen3.5-9B | control_plane_failed | unknown | 2 | 0 | manager:2 | bm25_retrieve:2 | 2 | 1/1 | 0 |
| 3 | Ministral 3 3B | terminal_contract_failed | unknown | 0 | 0 | none | none | 0 | 0/0 | 0 |
| 3 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 6 | 4 | manager:6 | bm25_retrieve:4; invoke_model:2 | 0 | 0/0 | 0 |
| 5 | Qwen3.5-4B | success | 1.000 | 7 | 16 | manager:7 | invoke_model:6; sample_frames:1 | 4 | 1/1 | 0 |
| 5 | Qwen3.5-9B | control_plane_failed | unknown | 1 | 0 | manager:1 | sample_frames:1 | 1 | 0/1 | 0 |
| 5 | Ministral 3 3B | incorrect_answer | 0.000 | 3 | 0 | manager:3 | extract_clip:2; invoke_model:1 | 3 | 1/1 | 0 |
| 5 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 3 | 20 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
