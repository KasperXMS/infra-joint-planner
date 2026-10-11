# Multi-scale Planner six-task results v1

42/42 正式 cells 已完成，无选择性重跑。实际 Qwen3.8-27B plain 完成 6/6、TSR 4/6；新 B0 完成 5/6、TSR 4/6，成功任务均为 t2/t3/t5/t6。4B、9B、Ministral 3B 的 TSR 分别为 1/6、1/6、0/6；这些是部署栈结果，部分 control-plane failures 包含 provider/SDK 错误，不能全部归因为模型能力。

27B plain 相对 B0 的已知云 API 成本降低 30.56%（$0.428588306 vs $0.617211977），任务 E2E 总和降低 14.35%（614.159s vs 717.074s）。Resident runner work 却为 410.083s vs 383.679s，前者包含本地 Manager；GPU 价格、能耗及失败调用的完整 service work 未测，因此完整资源成本仍为 unknown。全矩阵已知云 API 成本为 **$3.915528308**，按冻结价格估算，不等同于最终账单。

本轮只清理自有新 Planner 服务和转发，42 个 cells 的 Worker 均已退出。原五个 Executor、外部 RoboTwin、历史实验和固定 Skills 保留。原始敏感 traces 留在实验机器；仓库保存[脱敏结果](../analysis/multiscale-planner-evaluation-v1/multiscale-results.json)、[完整性摘要](../analysis/multiscale-planner-evaluation-v1/final-integrity.json)、[清理摘要](../analysis/multiscale-planner-evaluation-v1/owned-service-cleanup-summary.json)及[证据哈希](../analysis/multiscale-planner-evaluation-v1/raw-evidence-hashes.json)。

配套交付：[模型调查](multiscale-planner-model-survey-v1.md)、[兼容性记录](multiscale-planner-compatibility-v1.md)、[筛选结果](multiscale-planner-screening-v1.md)、[Skills 消融](multiscale-planner-skills-ablation-v1.md)、[研究判断](multiscale-planner-research-conclusions-v1.md)。

Execution state: **complete**; analyzed 42 cells. Missing cells below are not run, never zero-score observations.

Sanitized input SHA256: `6100b61692500ee46b86f050a287c7ee22f71b47fe16a9ddbfae6d065d96ea69`. Base commit `70a75ae`. Raw prompts, answers, task payloads and credential evidence remain on the experiment machines.

Six frozen, previously examined tasks; one attempt per model/task/Skills condition. Results are descriptive: no significance, noninferiority, held-out validation, or universal scale threshold. Schema failures and legitimate budget exhaustion remain evaluation outcomes; no selective score reruns.

The original external-GPU-contention stop remains historical evidence. Current export state is **complete**; preserved stop receipts: 4. A completed authorized continuation can be complete while retaining that stop.

Placement amendment: the first three 4B cells (task indices 1/3/5) used GPU1; the remaining 4B cells use an independent A28 Planner service. The third 4B cell's actual score is retained with its external-contention flag; its Planner service/runner work remains unknown. The 4B six-task cohort mixes placement and contention conditions, so its aggregate cost is not a pure matched hardware comparison. 9B and Ministral use A28; the resident 27B remains on GPU0. Foreign processes are outside experiment ownership.

The continuation Skills allocation is 9B plus resident 27B, six matched tasks each. Timing verification that selection preceded the first 9B benchmark: yes. The old 4B allocation is preserved in the original freeze but is not executed as an extra ablation. Weights, semantic prompts, frozen Skills, evaluator, Scheduler and Executor are unchanged; retained benchmark cells are not rerun.

The frozen slot `qwen35-27b` is reported as **Qwen3.8-27B [qwen35-27b]**. When the provenance correction receipt is present, its resident weight and projector match the official Qwen3.8-27B registry descriptors, rather than Qwen3.5-27B. The slot, weights and deployment were preserved. Only 4B and 9B provide a same-release Qwen3.5 size comparison; 27B also changes model generation, hardware and MTP/runtime configuration. None of these observational differences isolates a size-only causal effect.

B0 is the new matched qwen3.8-max Manager condition. Specialist, Verifier, physical pool, Scheduler, evaluator and semantic prompts stay fixed. Historical B0 4/6 is descriptive context only and is not pooled with the new baseline.

| Condition | Observed/planned | Completion | TSR | Mean original score | Valid/schema attempts | Schema failures | Outcomes |
|---|---|---|---|---|---|---|---|
| B0 qwen3.8-max | 6/6 | 5/6 | 4/6 | 0.800 (5 evaluated) | 43/43 | 0 | incorrect_answer:1; success:4; verification_failed:1 |
| Qwen3.5-4B | 6/6 | 1/6 | 1/6 | 1.000 (1 evaluated) | 80/99 | 19 | context_budget_exceeded:1; success:1; terminal_contract_failed:1; turn_budget_exhausted:3 |
| Qwen3.5-9B | 6/6 | 3/6 | 1/6 | 0.333 (3 evaluated) | 41/56 | 15 | control_plane_failed:3; incorrect_answer:2; success:1 |
| Ministral 3 3B | 6/6 | 1/6 | 0/6 | 0.000 (1 evaluated) | 13/21 | 8 | control_plane_failed:2; incorrect_answer:1; terminal_contract_failed:3 |
| Qwen3.8-27B [qwen35-27b] | 6/6 | 6/6 | 4/6 | 0.667 (6 evaluated) | 57/58 | 1 | incorrect_answer:2; success:4 |
| Qwen3.5-9B +Skills | 6/6 | 2/6 | 1/6 | 0.500 (2 evaluated) | 36/70 | 34 | control_plane_failed:2; incorrect_answer:1; success:1; turn_budget_exhausted:2 |
| Qwen3.8-27B [qwen35-27b] +Skills | 6/6 | 6/6 | 4/6 | 0.667 (6 evaluated) | 76/77 | 1 | incorrect_answer:2; success:4 |

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

## Matched task comparison minus B0

| Reference | Comparison | Pairs | Completion delta | TSR numerator delta | Schema delta | Manager turns delta | Manager input delta | Known cloud USD delta | Physical successes delta | Known model-service s delta | Task E2E s delta | Full cost delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 qwen3.8-max | Ministral 3 3B | 6/6 | -4 | -4 | 8 | -19 | unknown | -0.4943391023000571360235985065 | -4 | -279.488 | -168.461 | unknown |
| B0 qwen3.8-max | Qwen3.8-27B [qwen35-27b] | 6/6 | 1 | 0 | 1 | 0 | -31869 | -0.1886236715874513347240861559 | 0 | -105.713 | -102.915 | unknown |
| B0 qwen3.8-max | Qwen3.5-4B | 6/6 | -4 | -3 | 19 | 66 | 1057625 | 0.6150462961240516084455015339 | 1 | -262.456 | 1403.536 | unknown |
| B0 qwen3.8-max | Qwen3.5-9B | 6/6 | -2 | -3 | 15 | 24 | unknown | -0.0600895985862156021206765969 | -3 | -237.278 | 2785.920 | unknown |

Deltas use only the shared task indices shown in the pair count. Fewer than six pairs is a partial comparison. Cloud deltas compare known subtotals; if costs are missing, a subtotal difference is not a bound on the true cost difference.

## Control-plane resources

| Condition | Role | Requests | Turns | Input tokens | Output tokens | Cached input | Provider latency s | Cloud USD known subtotal | Complete cloud USD | Unknown-cost calls |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 qwen3.8-max | manager | 35 | 35 | 373088 | 10293 | 318080 | 124.617 | 0.2248854077253218884120171674 | 0.2248854077253218884120171674 | 0 |
| B0 qwen3.8-max | specialist | 7 | 7 | 60177 | 1947 | 49920 | 24.445 | 0.03998098034786537158346510052 | 0.03998098034786537158346510052 | 0 |
| B0 qwen3.8-max | verifier | 35 | 35 | 232701 | 5600 | 60160 | 82.356 | 0.3523455892318526687837999442 | 0.3523455892318526687837999442 | 0 |
| Qwen3.5-4B | manager | 100 | 101 | 1430713 | 25309 | 1316746 | 1378.053 | 0 | 0 | 0 |
| Qwen3.5-4B | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.5-4B | verifier | 99 | 99 | 1003369 | 18051 | 421760 | 312.200 | 1.232258273429091537224783746 | 1.232258273429091537224783746 | 0 |
| Qwen3.5-9B | manager | 59 | 59 | unknown (known subtotal 625509; 3 requests unknown) | unknown (known subtotal 14729; 3 requests unknown) | unknown (known subtotal 559954; 3 requests unknown) | 2936.457 | 0 | 0 | 0 |
| Qwen3.5-9B | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.5-9B | verifier | 56 | 56 | 431330 | 8925 | 167808 | 171.884 | 0.5571223787188243266586056152 | 0.5571223787188243266586056152 | 0 |
| Ministral 3 3B | manager | 16 | 16 | unknown (known subtotal 85977; 2 requests unknown) | unknown (known subtotal 2625; 2 requests unknown) | unknown (known subtotal 66582; 2 requests unknown) | 332.592 | 0 | 0 | 0 |
| Ministral 3 3B | specialist | 7 | 7 | 64982 | 1993 | 41856 | 24.102 | 0.06145702042280657462894803279 | 0.06145702042280657462894803279 | 0 |
| Ministral 3 3B | verifier | 11 | 11 | 35817 | 1963 | 8448 | 31.660 | 0.06141585458217621812673567281 | 0.06141585458217621812673567281 | 0 |
| Qwen3.8-27B [qwen35-27b] | manager | 35 | 35 | 341219 | 14874 | 294504 | 134.492 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] | verifier | 35 | 35 | 301155 | 5232 | 88448 | 91.177 | 0.4285883057175885940551960562 | 0.4285883057175885940551960562 | 0 |
| Qwen3.5-9B +Skills | manager | 72 | 72 | unknown (known subtotal 749500; 2 requests unknown) | unknown (known subtotal 15961; 2 requests unknown) | unknown (known subtotal 687137; 2 requests unknown) | 2939.836 | 0 | 0 | 0 |
| Qwen3.5-9B +Skills | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.5-9B +Skills | verifier | 70 | 70 | 353384 | 11790 | 168192 | 185.353 | 0.4323952510663176497163129991 | 0.4323952510663176497163129991 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | manager | 40 | 40 | 419614 | 16446 | 362217 | 151.423 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | verifier | 40 | 40 | 361558 | 6092 | 98816 | 97.460 | 0.5250792463359863936539151465 | 0.5250792463359863936539151465 | 0 |

Known token/cache subtotals are lower bounds when any request lacks usage. Unknown provider failures are not filled with zero tokens or zero cost. Cloud subtotals use the frozen price accounting; local GPU monetary cost and full resource monetary cost remain unknown.

## Physical and wall-clock resources

| Condition | Physical admissions | Inference successes | Failed actions | Physical input tokens | Physical output tokens | Known model-service s | Failed service unmeasured | Operator s | Task E2E s | Controller execution s | Initial bytes | Action bytes | Resident runner s | Resident starts | Independent Planner runner s | Independent starts known | Independent work unobserved cells |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 qwen3.8-max | 6 | 6 | 7 | 38618 | 86 | 389.858 | yes | 436.499 | 717.074 | 717.196 | 238804668 | 10626750 | 383.679 | 6 | 0.000 | 0 | 0 |
| Qwen3.5-4B | 14 | 7 | 20 | 23558 | 137 | 127.402 | yes | 149.509 | 2120.611 | 2120.733 | 238804668 | 4636886 | 297.175 | 14 | unknown | 84 | 1 |
| Qwen3.5-9B | 7 | 3 | 8 | 5718 | 247 | 152.580 | yes | 176.611 | 3502.994 | 3503.120 | 238804668 | 10409192 | 280.535 | 7 | 2925.359 | 59 | 0 |
| Ministral 3 3B | 2 | 2 | 1 | 1410 | 1110 | 110.370 | yes | 133.672 | 548.613 | 548.734 | 238804668 | 0 | 109.349 | 2 | 309.579 | 16 | 0 |
| Qwen3.8-27B [qwen35-27b] | 6 | 6 | 7 | 33587 | 62 | 284.145 | yes | 357.972 | 614.159 | 614.287 | 238804668 | 36861 | 410.083 | 41 | 0.000 | 0 | 0 |
| Qwen3.5-9B +Skills | 3 | 3 | 6 | 6869 | 132 | 121.968 | yes | 147.829 | 3365.246 | 3365.369 | 238804668 | 10626750 | 119.308 | 3 | 2925.983 | 72 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | 6 | 6 | 8 | 30915 | 65 | 297.454 | yes | 373.467 | 650.607 | 650.741 | 238804668 | 247754 | 440.006 | 46 | 0.000 | 0 | 0 |

Matrix journal wall: 16510.296 s, including setup/cleanup and recorded pauses. Task E2E is summed separately. Operator/model service, API latency and runner durations can overlap; do not add them to infer E2E or GPU busy seconds. Resident work covers all five existing runners and includes Manager work only for a reused resident endpoint; independent Planner work is reported separately. Runner decode runs under MTP are not interchangeable with output tokens. An independent endpoint does not apply to B0 or the resident 27B; its unobserved independent-work counter does not imply missing resident work. Failed-action service work can be unmeasured. Persisted API JSON sizes are storage, not measured network transfer.

Early failures may consume fewer resources because work was never completed. Lower observed cost on a failed task is not evidence of useful inference efficiency. GPU prices, energy, peak VRAM and complete GPU compute time are unknown.

## Same-task workflows

| Task index | Condition | Outcome | Original score | Nodes | Artifact edges | Owners | Operators | Schema failures | Later-valid/invalid owners | Identical repeated calls |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | B0 qwen3.8-max | incorrect_answer | 0.000 | 4 | 4 | manager:4 | aggregate_artifacts:1; bm25_retrieve:2; invoke_model:1 | 0 | 0/0 | 0 |
| 1 | Qwen3.5-4B | context_budget_exceeded | unknown | 11 | 9 | manager:11 | aggregate_artifacts:1; bm25_retrieve:4; invoke_model:1; read_artifact:2; select_fields:3 | 5 | 1/1 | 1 |
| 1 | Qwen3.5-9B | incorrect_answer | 0.000 | 8 | 9 | manager:8 | aggregate_artifacts:2; bm25_retrieve:4; invoke_model:2 | 3 | 1/1 | 0 |
| 1 | Ministral 3 3B | control_plane_failed | unknown | 0 | 0 | none | none | 2 | 0/1 | 0 |
| 1 | Qwen3.8-27B [qwen35-27b] | incorrect_answer | 0.000 | 21 | 18 | manager:21 | bm25_retrieve:18; invoke_model:3 | 0 | 0/0 | 0 |
| 1 | Qwen3.5-9B +Skills | control_plane_failed | unknown | 3 | 2 | manager:3 | aggregate_artifacts:1; bm25_retrieve:2 | 3 | 1/1 | 0 |
| 1 | Qwen3.8-27B [qwen35-27b] +Skills | incorrect_answer | 0.000 | 21 | 18 | manager:21 | bm25_retrieve:18; invoke_model:3 | 1 | 1/1 | 0 |
| 2 | B0 qwen3.8-max | success | 1.000 | 3 | 2 | manager:3 | aggregate_artifacts:1; bm25_retrieve:1; invoke_model:1 | 0 | 0/0 | 0 |
| 2 | Qwen3.5-4B | turn_budget_exhausted | unknown | 12 | 9 | manager:12 | bm25_retrieve:5; invoke_model:5; read_artifact:1; select_fields:1 | 1 | 1/1 | 0 |
| 2 | Qwen3.5-9B | incorrect_answer | 0.000 | 8 | 7 | manager:8 | aggregate_artifacts:1; bm25_retrieve:3; invoke_model:3; select_fields:1 | 0 | 0/0 | 0 |
| 2 | Ministral 3 3B | control_plane_failed | unknown | 0 | 0 | none | none | 3 | 1/1 | 0 |
| 2 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 8 | 6 | manager:8 | bm25_retrieve:6; invoke_model:2 | 1 | 1/1 | 0 |
| 2 | Qwen3.5-9B +Skills | incorrect_answer | 0.000 | 5 | 4 | manager:5 | aggregate_artifacts:1; bm25_retrieve:2; invoke_model:2 | 3 | 1/1 | 0 |
| 2 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 8 | 6 | manager:8 | bm25_retrieve:6; invoke_model:2 | 0 | 0/0 | 0 |
| 3 | B0 qwen3.8-max | success | 1.000 | 6 | 5 | manager:6 | aggregate_artifacts:1; bm25_retrieve:2; invoke_model:3 | 0 | 0/0 | 0 |
| 3 | Qwen3.5-4B | turn_budget_exhausted | unknown | 13 | 13 | manager:13 | bm25_retrieve:4; invoke_model:5; select_fields:1; top_k_records:3 | 3 | 1/1 | 0 |
| 3 | Qwen3.5-9B | control_plane_failed | unknown | 2 | 0 | manager:2 | bm25_retrieve:2 | 2 | 1/1 | 0 |
| 3 | Ministral 3 3B | terminal_contract_failed | unknown | 0 | 0 | none | none | 0 | 0/0 | 0 |
| 3 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 6 | 4 | manager:6 | bm25_retrieve:4; invoke_model:2 | 0 | 0/0 | 0 |
| 3 | Qwen3.5-9B +Skills | turn_budget_exhausted | unknown | 3 | 2 | manager:3 | aggregate_artifacts:1; bm25_retrieve:1; invoke_model:1 | 9 | 1/1 | 0 |
| 3 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 16 | 24 | manager:16 | aggregate_artifacts:1; bm25_retrieve:12; invoke_model:3 | 0 | 0/0 | 0 |
| 4 | B0 qwen3.8-max | verification_failed | unknown | 13 | 11 | manager:8; specialist_1:5 | aggregate_artifacts:1; bm25_retrieve:6; invoke_model:4; read_artifact:1; select_fields:1 | 0 | 0/0 | 0 |
| 4 | Qwen3.5-4B | turn_budget_exhausted | unknown | 15 | 15 | manager:15 | aggregate_artifacts:2; bm25_retrieve:1; filter_records:7; invoke_model:4; select_fields:1 | 4 | 1/1 | 1 |
| 4 | Qwen3.5-9B | control_plane_failed | unknown | 2 | 0 | manager:2 | bm25_retrieve:2 | 5 | 1/1 | 0 |
| 4 | Ministral 3 3B | terminal_contract_failed | unknown | 1 | 0 | manager:1 | aggregate_artifacts:1 | 0 | 0/0 | 0 |
| 4 | Qwen3.8-27B [qwen35-27b] | incorrect_answer | 0.000 | 6 | 4 | manager:6 | bm25_retrieve:4; invoke_model:2 | 0 | 0/0 | 0 |
| 4 | Qwen3.5-9B +Skills | turn_budget_exhausted | unknown | 9 | 7 | manager:9 | aggregate_artifacts:1; bm25_retrieve:2; filter_records:2; invoke_model:3; select_fields:1 | 11 | 1/1 | 0 |
| 4 | Qwen3.8-27B [qwen35-27b] +Skills | incorrect_answer | 0.000 | 6 | 4 | manager:6 | bm25_retrieve:4; invoke_model:2 | 0 | 0/0 | 0 |
| 5 | B0 qwen3.8-max | success | 1.000 | 3 | 12 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
| 5 | Qwen3.5-4B | success | 1.000 | 7 | 16 | manager:7 | invoke_model:6; sample_frames:1 | 4 | 1/1 | 0 |
| 5 | Qwen3.5-9B | control_plane_failed | unknown | 1 | 0 | manager:1 | sample_frames:1 | 1 | 0/1 | 0 |
| 5 | Ministral 3 3B | incorrect_answer | 0.000 | 3 | 0 | manager:3 | extract_clip:2; invoke_model:1 | 3 | 1/1 | 0 |
| 5 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 3 | 20 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
| 5 | Qwen3.5-9B +Skills | control_plane_failed | unknown | 2 | 0 | manager:2 | sample_frames:2 | 6 | 1/1 | 0 |
| 5 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 3 | 20 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
| 6 | B0 qwen3.8-max | success | 1.000 | 2 | 6 | manager:2 | invoke_model:1; sample_frames:1 | 0 | 0/0 | 0 |
| 6 | Qwen3.5-4B | terminal_contract_failed | unknown | 1 | 0 | manager:1 | sample_frames:1 | 2 | 1/1 | 0 |
| 6 | Qwen3.5-9B | success | 1.000 | 9 | 13 | manager:9 | aggregate_artifacts:1; extract_clip:1; invoke_model:4; sample_frames:3 | 4 | 1/1 | 0 |
| 6 | Ministral 3 3B | terminal_contract_failed | unknown | 4 | 16 | specialist_1:4 | invoke_model:1; make_contact_sheet:1; read_artifact:1; sample_frames:1 | 0 | 0/0 | 0 |
| 6 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 3 | 21 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
| 6 | Qwen3.5-9B +Skills | success | 1.000 | 4 | 25 | manager:4 | invoke_model:3; sample_frames:1 | 2 | 1/1 | 0 |
| 6 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 3 | 18 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |

Edges are artifact dependencies, including multiple edges between operator nodes. Owner labels are anonymized. A later valid call after a schema error establishes protocol recovery, not task completion or correctness. Counts describe topology and operator choices; they do not establish semantic decomposition quality or whether all necessary information reached synthesis.

## Deployment and preparation work

| Candidate | Downloaded tag | Download s | Quantization | Manifest SHA256 |
|---|---|---|---|---|
| Ministral 3 3B | ministral-3:3b | 32.764 | Q4_K_M | f04aa1c738f64e13c625b82ae92504fc0260fa6723b509ed1ece0fa188179b1d |
| Qwen3.5-4B | qwen3.5:4b | 37.945 | Q4_K_M | d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04 |
| Qwen3.5-9B | qwen3.5:9b | 6.401 | Q4_K_M | 56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90 |

| Candidate | Phase | Load/attestation s | Resident VRAM bytes | GPU snapshots used/free MiB | Executor runners unchanged |
|---|---|---|---|---|---|
| Ministral 3 3B | compatibility | 6.986 | 4319462030 | GPU0:20146/3936; GPU1:15877/8204 | yes |
| Qwen3.8-27B [qwen35-27b] | compatibility | 1.934 | 17399734598 | GPU0:20146/3936; GPU1:15895/8186 | yes |
| Qwen3.5-4B | compatibility | 10.230 | 3801392085 | GPU0:20146/3936; GPU1:15259/8822 | yes |
| Qwen3.5-9B | compatibility | 12.573 | 6248359525 | GPU0:20146/3936; GPU1:17829/6252 | yes |
| Qwen3.5-9B | 003-screening | 13.301 | 6248359525 | GPU0:20643/3439; GPU1:20559/3523 | yes |
| Ministral 3 3B | 004-matrix-extension | 10.861 | 4319462030 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.8-27B [qwen35-27b] | continued-004-matrix-extension | 1.449 | 17399734598 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.5-4B | 004-matrix-extension | 19.763 | 3801392085 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.5-9B | 004-matrix-extension | 14.016 | 6248359525 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Ministral 3 3B | 004-screening | 24.424 | 4319462030 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.8-27B [qwen35-27b] | continued-004-screening | 1.422 | 17399734598 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.5-9B | 004-screening | 13.337 | 6248359525 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.8-27B [qwen35-27b] | continued-004-skills | 1.412 | 17399734598 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.5-9B | 004-skills | 14.363 | 6248359525 | GPU0:20146/3936; GPU1:18875/5206 | yes |
| Qwen3.5-9B | screening | 27.528 | 6248359525 | GPU0:20146/3936; GPU1:19113/4968 | yes |
| Qwen3.5-4B | screening | 7.912 | 3801392085 | GPU0:20146/3936; GPU1:15259/8822 | yes |

Load/attestation elapsed time is preparation outside task E2E; a resident endpoint's attestation time is not a new weight-load measurement. VRAM values are snapshots, not peaks. Independent local Planner services share GPU resources with the protected physical pool; contention can affect timings. No resident Executor model was substituted for another model.

Frozen Manager sampling: `{"context_window": 32768, "manager_max_tokens": 2048, "manager_temperature": 1, "manager_top_p": 0.95, "qwen_reasoning_effort": "none"}`.

| Candidate | Context/output | Thinking | Renderer | Parser | Model blob SHA256 | Template SHA256 |
|---|---|---|---|---|---|---|
| Ministral 3 3B | 32768/2048 | unknown | unknown | ministral | sha256-910e4bf4e2338f181e99796d7452404e85c1b6bbbf8cd0bb094672cf9b6f2f22 | 24c6226aca35b16350187fb9125e7cb4e746795c78edd3cb1de45654c7e77181 |
| Qwen3.8-27B [qwen35-27b] | 32768/2048 | no | qwen3.8 | qwen3.5 | sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d | b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315 |
| Qwen3.5-4B | 32768/2048 | no | qwen3.5 | qwen3.5 | sha256-a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50 | b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315 |
| Qwen3.5-9B | 32768/2048 | no | qwen3.5 | qwen3.5 | sha256-02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d | b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315 |

A null thinking field means the sanitized metadata does not establish that switch; it does not assert that thinking was enabled. Backend versions and architecture details are retained in sanitized model metadata. Parser differences are deployment differences, not evidence that model scale alone caused an observed outcome.

## Execution integrity

| Check | Observed |
|---|---|
| source_unchanged | yes |
| protected_history_and_skills_unchanged | yes |
| all_executed_workers_drained_and_exited | yes |
| system_problems |  |
| semantic_retries | 0 |
| private_raw_evidence_exported | no |
| source_files_checked | 511 |
| protected_files_checked | 26 |
