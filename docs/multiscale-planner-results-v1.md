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

## Failure case analysis

42 cells 中有 15 次成功、27 次非成功；其中 9 次已完成但答案错误，18 次未完成。下表是互斥的最终结果，schema 错误是过程中发生的事件，不另计为一类最终失败。t1（MultiHop-RAG 第一题）和 t4（LongBench 第二题）在全部七个条件下均未成功，共占 14/27 次非成功，说明这两个任务是本轮的共同难点，不能单凭共同失败认定 evaluator 有问题。

| 最终失败类型 | Cells | 位置 |
|---|---:|---|
| incorrect_answer | 9 | B0 t1；27B plain/Skills t1、t4；9B plain t1、t2；9B Skills t2；Ministral t5 |
| control_plane_failed / HTTP 500 | 7 | 9B plain t3、t4、t5；9B Skills t1、t5；Ministral t1、t2 |
| turn_budget_exhausted | 5 | 4B t2、t3、t4；9B Skills t3、t4 |
| terminal_contract_failed | 4 | 4B t6；Ministral t3、t4、t6 |
| context_budget_exceeded | 1 | 4B t1，Manager preflight 拒绝 |
| verification_failed | 1 | B0 t4，Verifier complete 与 Manager 候选所有权契约冲突 |

以下归因依据既有私有 traces、API error receipts 和服务日志的只读检查，没有新增 inference、恢复服务或重跑 cell。[脱敏 trace 时间线](../analysis/multiscale-planner-evaluation-v1/failure-case-trace-summary-v1.json)记录 42 cells 的错误代码、阶段变化、schema 类别及原始 trace/result SHA256；[provider 解析故障摘要](../analysis/multiscale-planner-evaluation-v1/failure-provider-findings-v1.json)补充七次 HTTP 500 的定位。题目、实体、候选答案和原始模型响应不写入本节。

### 27B t1 和 t4：完成合成仍然答错

实际 Qwen3.8-27B plain/Skills 在 t1 都进行了六路分片检索，两次 physical context 检查拒绝后降低 top_k、重新检索，最终成功调用 Executor 合成，但 evaluator 判错。两组都记录 18 个 BM25 节点。plain 有 1 次输出命名碰撞；Skills 有 1 次 schema 错误和 7 次命名碰撞（1 次合成、6 次检索），最终正确性未变。B0 t1 则经过两路主题检索、2 次阶段限制拒绝后成功合成，格式合法但同样判错。t4 两个 27B 条件均经过两主题检索、一次 physical context 拒绝、降低 top_k 后成功合成同一错误选项；Skills 消除了 plain 的 1 次合成输出命名碰撞，却没有修复错误答案。

这里可证实的是：工具调用最终完成、格式合法和 Verifier complete 并不能保证答案正确。相关 Verifier 判断依据非空候选和合法输出格式，并未建立 ground-truth 正确性。原 Worker store 已为空，现存 trace 主要保存检索产物元数据，无法核实最终合成输入是否覆盖全部 gold 证据。因此不能进一步断言是漏检关键证据、压缩丢失关系、错误证据连接还是 Executor 合成推理错误；对这几种语义根因保留 unknown，不能直接称为 hallucination。增加检索次数没有在本轮修复 t1。

### 9B Skills t3：已获准合成，却在阶段和参数错误中耗尽轮次

第 1 次 aggregate_artifacts 后，Verifier 将流程切入 synthesis；当前 runtime 在该阶段只允许 invoke_model 或最终回答。接下来发生 8 次 phase_restricted 和 9 次 schema_validation_failed。Verifier 共 13 次返回 ready_for_synthesis，但 Manager 没有及时形成合法、可执行且输入适配的合成调用。第 14 次验证前的 invoke_model 又被 physical context 检查拒绝，流程退回取证阶段，最终用完 20 个 Manager turns，只形成 3 个 action nodes。

Schema 错误包括省略 arguments、将 top_k 放错层级，以及空 inputs。此例的直接瓶颈是阶段规则、参数结构和反馈恢复，不能解释为单纯“还缺更多推理轮次”。注意：phase_restricted 和 schema 错误是不同检查点，其计数不能简单相加当作互斥失败轮次。

### 4B t2/t3/t4 与 9B Skills t4：修复动作没有稳定收束

4B t2/t3 在 evidence_collection 与 synthesis 间反复切换；Verifier 分别有 6/5 次 ready_for_synthesis，但后续出现未 materialize 的 artifact、过大 Executor 输入、参数及语义校验错误，最终各耗尽 20 轮。4B t4 做了 7 次 filter_records、3 次 physical context 拒绝，Verifier 20 次均为 continue。9B Skills t4 则有 11 次 schema 错误，包括缺 arguments、将嵌套参数摊平以及把应为 object 的 arguments 生成为字符串；即便局部调用修复成功，仍没有在预算内完成。

这五个 turn-budget failures 合计消耗 100 个 Manager turns 和 100 个 Verifier turns。模型可以在某次错误后恢复一个合法调用，却仍不能完成任务；因此“出现 later-valid call”不等于有效的整体恢复。这也解释了弱 Planner 为什么会放大强 Verifier 的成本。

### 七次 HTTP 500：发生在应用层 Schema 校验之前的解析故障

五个 9B cells 的日志明确定位到 Ollama 原生工具调用 XML parser（qwen3coder.go → qwen35.go）。plain t3/t4/t5 和 Skills t5 的 function 标签被 parameter 结束标签关闭；Skills t1 则相反。它们没有形成可交付应用层 validator 的 Function Call，故没有被计作 schema_validation_failed，不能据此认为应用层静默执行了非法调用。

Ministral t1/t2 的错误 body 分别为 object key 后出现非法右花括号、string literal 内出现非法换行，已定位到 JSON 语法解析失败；服务日志没有足够调用栈进一步确认具体 parser/renderer 组件。七次失败请求均通过 Manager context preflight，相关日志未见 OOM、timeout 或非零 truncation 标志。它们是有效的部署栈协议失败，与任务答案错误分开报告；不能全部归为纯推理能力差，也不能仅凭日志未见某标志证明其绝对不存在。

### 提前结束和终结契约失败

Ministral t3 尚未执行工具就返回文本，未获 Verifier 合成授权；t4 在一次 aggregate_artifacts 后返回空文本；t6 虽委派强 Specialist 并完成部分视频分析，Manager 在 Verifier 仍要求继续取证时结束。4B t6 进入 synthesis 后经历非法 invoke_model 参数、未 materialize artifact 和阶段违规，最后返回 752 字符、7 行文本，被选择题输出契约拒绝。这四例属于未完成，不能拿其中看似合理的文本当作已提交答案评分。

B0 t4 是另一种契约问题：三次 physical context 拒绝后，Specialist 有一次成功合成并 handoff；最终 Verifier 返回 complete，但 Manager 没有自己的成功 model candidate。Runtime 因 `verifier returned complete without a successful manager model candidate` 拒绝终结。该例还包含输出命名碰撞、phase_restricted 和 artifact_too_large。它说明强 Specialist 的局部成功不会自动形成合法 Manager 最终产物；不能把 B0 t4 简化为错误答案或一般预算耗尽。

### Context 和 Skills 的解释边界

只有 4B t1 命中了本地 Manager 的 tokenizer preflight：rendered prompt 为 30,723 tokens，超过 32,768 减去 2,048 输出预留后的 30,720 预算，因此 fail-closed，禁止发送并静默截断。其他多次 context_limit_exceeded 来自被冻结的 Physical resolver：其 estimated_input 对文本使用 UTF-8/文件字节数、对图像使用 image_token_cost，是保守输入大小 proxy，不能写成实际 tokenizer tokens。比如 4B t4 的一次估计值为 2,120,902，表示其输入打包规模过大，并不证明模型实际收到两百万 tokens。

全矩阵有 78 次 schema-invalid calls，其中 25 次缺少 arguments。一个调用可能违反多条 schema 规则；脱敏摘要另记录 30 条额外/错层字段错误和 10 条类型错误，不能与 78 次调用直接相加。当前 Frozen Skills 只提供抽象的“检查 schema、遵守预算、根据反馈恢复”，没有提供每个 operator 的嵌套参数实例、阶段转换操作步骤或超大 artifact 的压缩方案。本轮证据支持“这份固定指导不足以稳定解决这些错误”，不支持“所有 Skills 无效”。

下一轮的建议是先针对这些已观察到的路径设计具体 SOP：合法 inputs/arguments 示例、按当前 phase 选择动作、Executor 输入缩减及证据保留、Manager 最终候选与输出格式检查。对 27B plain 的 Adapter 研究仍是有条件 Go，但应区分输入路由/资源优化与语义正确性；不能预先声称调度或减少节点会修复 t1/t4 的答案。以上均为未来方案，本轮未改 Skills、Prompt、Evaluator、Scheduler 或结果。
