# Multi-scale Planner frozen Skills ablation v1

两组均未观察到 TSR 提升。实际 Qwen3.8-27B 加 Skills 后逐任务 score 不变，Manager turns 35→40，输入增加 78,395 tokens，云 API 成本增加 $0.096490941（22.51%），任务 E2E 增加 36.448s。t3 的 workflow 从 6 个节点、4 次检索扩至 16 个节点、12 次检索，两次均成功；额外检索是后续研究的可测优化对象，不能仅凭计数判定每次检索都无效。

Qwen3.5-9B 加 Skills 后 Completion 3/6→2/6，TSR 仍为 1/6，schema failures 15→34，Manager turns 59→72。t6 从 9 节点、17 turns 缩为 4 节点、7 turns且仍成功，但 t1 从完成的错误答案转为 control_plane_failed。已知云 API 成本下降 22.39%、任务 E2E 减少 137.748s，不能作为效率提升：失败路径、provider 错误与缺失 usage 会影响解释。

Skills 文本未修改。消融模型在首次 9B 正式 cell 前冻结为 9B/27B；其 Manager placement 在配对中保持相同，时间阶段和外部资源争用仍不完全相同。本轮不支持普遍正向 Skills 效应，也不估计统计显著性。

Execution state: **complete**; analyzed 42 cells. Missing cells below are not run, never zero-score observations.

Sanitized input SHA256: `6100b61692500ee46b86f050a287c7ee22f71b47fe16a9ddbfae6d065d96ea69`. Base commit `70a75ae`. Raw prompts, answers, task payloads and credential evidence remain on the experiment machines.

Six frozen, previously examined tasks; one attempt per model/task/Skills condition. Results are descriptive: no significance, noninferiority, held-out validation, or universal scale threshold. Schema failures and legitimate budget exhaustion remain evaluation outcomes; no selective score reruns.

The original external-GPU-contention stop remains historical evidence. Current export state is **complete**; preserved stop receipts: 4. A completed authorized continuation can be complete while retaining that stop.

Placement amendment: the first three 4B cells (task indices 1/3/5) used GPU1; the remaining 4B cells use an independent A28 Planner service. The third 4B cell's actual score is retained with its external-contention flag; its Planner service/runner work remains unknown. The 4B six-task cohort mixes placement and contention conditions, so its aggregate cost is not a pure matched hardware comparison. 9B and Ministral use A28; the resident 27B remains on GPU0. Foreign processes are outside experiment ownership.

The continuation Skills allocation is 9B plus resident 27B, six matched tasks each. Timing verification that selection preceded the first 9B benchmark: yes. The old 4B allocation is preserved in the original freeze but is not executed as an extra ablation. Weights, semantic prompts, frozen Skills, evaluator, Scheduler and Executor are unchanged; retained benchmark cells are not rerun.

The preregistered ablation uses the unchanged `configs/skills/planner-procedural-v1.md` for Qwen3.5-9B, Qwen3.8-27B [qwen35-27b]. No-Skills matrix cells are reused as matched comparisons; they are not extra benchmark attempts. Model/task/runtime/budgets/strong roles remain matched.

The frozen slot `qwen35-27b` is reported as **Qwen3.8-27B [qwen35-27b]**. When the provenance correction receipt is present, its resident weight and projector match the official Qwen3.8-27B registry descriptors, rather than Qwen3.5-27B. The slot, weights and deployment were preserved. Only 4B and 9B provide a same-release Qwen3.5 size comparison; 27B also changes model generation, hardware and MTP/runtime configuration. None of these observational differences isolates a size-only causal effect.

| Model | Paired tasks | Coverage | Completion delta | TSR numerator delta | Manager input delta | Manager output delta | Known input subtotal delta |
|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | 6/6 | complete six-task pairs | -1 | 0 | unknown | unknown | 123991 |
| Qwen3.8-27B [qwen35-27b] | 6/6 | complete six-task pairs | 0 | 0 | 78395 | 1572 | 78395 |

All deltas are with-Skills minus without-Skills on the same observed paired tasks. A partial pair count is not a six-task Skills effect. Total Manager input differences include Skills text repeated in requests, changed turn counts, tool results and recovery history; they are not a tokenizer-only estimate of the static Skills overhead. Cached usage and unknown provider requests must be considered separately.

| Reference | Comparison | Pairs | Completion delta | TSR numerator delta | Schema delta | Manager turns delta | Manager input delta | Known cloud USD delta | Physical successes delta | Known model-service s delta | Task E2E s delta | Full cost delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B [qwen35-27b] | Qwen3.8-27B [qwen35-27b] +Skills | 6/6 | 0 | 0 | 0 | 5 | 78395 | 0.0964909406183977995987190903 | 0 | 13.309 | 36.448 | unknown |
| Qwen3.5-9B | Qwen3.5-9B +Skills | 6/6 | -1 | 0 | 19 | 13 | unknown | -0.1247271276525066769422926161 | 0 | -30.613 | -137.748 | unknown |

## Qwen3.5-9B

| Condition | Observed/planned | Completion | TSR | Mean original score | Valid/schema attempts | Schema failures | Outcomes |
|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | 6/6 | 3/6 | 1/6 | 0.333 (3 evaluated) | 41/56 | 15 | control_plane_failed:3; incorrect_answer:2; success:1 |
| Qwen3.5-9B +Skills | 6/6 | 2/6 | 1/6 | 0.500 (2 evaluated) | 36/70 | 34 | control_plane_failed:2; incorrect_answer:1; success:1; turn_budget_exhausted:2 |

| Condition | Role | Requests | Turns | Input tokens | Output tokens | Cached input | Provider latency s | Cloud USD known subtotal | Complete cloud USD | Unknown-cost calls |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | manager | 59 | 59 | unknown (known subtotal 625509; 3 requests unknown) | unknown (known subtotal 14729; 3 requests unknown) | unknown (known subtotal 559954; 3 requests unknown) | 2936.457 | 0 | 0 | 0 |
| Qwen3.5-9B | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.5-9B | verifier | 56 | 56 | 431330 | 8925 | 167808 | 171.884 | 0.5571223787188243266586056152 | 0.5571223787188243266586056152 | 0 |
| Qwen3.5-9B +Skills | manager | 72 | 72 | unknown (known subtotal 749500; 2 requests unknown) | unknown (known subtotal 15961; 2 requests unknown) | unknown (known subtotal 687137; 2 requests unknown) | 2939.836 | 0 | 0 | 0 |
| Qwen3.5-9B +Skills | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.5-9B +Skills | verifier | 70 | 70 | 353384 | 11790 | 168192 | 185.353 | 0.4323952510663176497163129991 | 0.4323952510663176497163129991 | 0 |

| Condition | Physical admissions | Inference successes | Failed actions | Physical input tokens | Physical output tokens | Known model-service s | Failed service unmeasured | Operator s | Task E2E s | Controller execution s | Initial bytes | Action bytes | Resident runner s | Resident starts | Independent Planner runner s | Independent starts known | Independent work unobserved cells |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.5-9B | 7 | 3 | 8 | 5718 | 247 | 152.580 | yes | 176.611 | 3502.994 | 3503.120 | 238804668 | 10409192 | 280.535 | 7 | 2925.359 | 59 | 0 |
| Qwen3.5-9B +Skills | 3 | 3 | 6 | 6869 | 132 | 121.968 | yes | 147.829 | 3365.246 | 3365.369 | 238804668 | 10626750 | 119.308 | 3 | 2925.983 | 72 | 0 |

| Task index | Condition | Outcome | Original score | Nodes | Artifact edges | Owners | Operators | Schema failures | Later-valid/invalid owners | Identical repeated calls |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.5-9B | incorrect_answer | 0.000 | 8 | 9 | manager:8 | aggregate_artifacts:2; bm25_retrieve:4; invoke_model:2 | 3 | 1/1 | 0 |
| 1 | Qwen3.5-9B +Skills | control_plane_failed | unknown | 3 | 2 | manager:3 | aggregate_artifacts:1; bm25_retrieve:2 | 3 | 1/1 | 0 |
| 2 | Qwen3.5-9B | incorrect_answer | 0.000 | 8 | 7 | manager:8 | aggregate_artifacts:1; bm25_retrieve:3; invoke_model:3; select_fields:1 | 0 | 0/0 | 0 |
| 2 | Qwen3.5-9B +Skills | incorrect_answer | 0.000 | 5 | 4 | manager:5 | aggregate_artifacts:1; bm25_retrieve:2; invoke_model:2 | 3 | 1/1 | 0 |
| 3 | Qwen3.5-9B | control_plane_failed | unknown | 2 | 0 | manager:2 | bm25_retrieve:2 | 2 | 1/1 | 0 |
| 3 | Qwen3.5-9B +Skills | turn_budget_exhausted | unknown | 3 | 2 | manager:3 | aggregate_artifacts:1; bm25_retrieve:1; invoke_model:1 | 9 | 1/1 | 0 |
| 4 | Qwen3.5-9B | control_plane_failed | unknown | 2 | 0 | manager:2 | bm25_retrieve:2 | 5 | 1/1 | 0 |
| 4 | Qwen3.5-9B +Skills | turn_budget_exhausted | unknown | 9 | 7 | manager:9 | aggregate_artifacts:1; bm25_retrieve:2; filter_records:2; invoke_model:3; select_fields:1 | 11 | 1/1 | 0 |
| 5 | Qwen3.5-9B | control_plane_failed | unknown | 1 | 0 | manager:1 | sample_frames:1 | 1 | 0/1 | 0 |
| 5 | Qwen3.5-9B +Skills | control_plane_failed | unknown | 2 | 0 | manager:2 | sample_frames:2 | 6 | 1/1 | 0 |
| 6 | Qwen3.5-9B | success | 1.000 | 9 | 13 | manager:9 | aggregate_artifacts:1; extract_clip:1; invoke_model:4; sample_frames:3 | 4 | 1/1 | 0 |
| 6 | Qwen3.5-9B +Skills | success | 1.000 | 4 | 25 | manager:4 | invoke_model:3; sample_frames:1 | 2 | 1/1 | 0 |

## Qwen3.8-27B [qwen35-27b]

| Condition | Observed/planned | Completion | TSR | Mean original score | Valid/schema attempts | Schema failures | Outcomes |
|---|---|---|---|---|---|---|---|
| Qwen3.8-27B [qwen35-27b] | 6/6 | 6/6 | 4/6 | 0.667 (6 evaluated) | 57/58 | 1 | incorrect_answer:2; success:4 |
| Qwen3.8-27B [qwen35-27b] +Skills | 6/6 | 6/6 | 4/6 | 0.667 (6 evaluated) | 76/77 | 1 | incorrect_answer:2; success:4 |

| Condition | Role | Requests | Turns | Input tokens | Output tokens | Cached input | Provider latency s | Cloud USD known subtotal | Complete cloud USD | Unknown-cost calls |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B [qwen35-27b] | manager | 35 | 35 | 341219 | 14874 | 294504 | 134.492 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] | verifier | 35 | 35 | 301155 | 5232 | 88448 | 91.177 | 0.4285883057175885940551960562 | 0.4285883057175885940551960562 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | manager | 40 | 40 | 419614 | 16446 | 362217 | 151.423 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | specialist | 0 | 0 | 0 | 0 | 0 | 0.000 | 0 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | verifier | 40 | 40 | 361558 | 6092 | 98816 | 97.460 | 0.5250792463359863936539151465 | 0.5250792463359863936539151465 | 0 |

| Condition | Physical admissions | Inference successes | Failed actions | Physical input tokens | Physical output tokens | Known model-service s | Failed service unmeasured | Operator s | Task E2E s | Controller execution s | Initial bytes | Action bytes | Resident runner s | Resident starts | Independent Planner runner s | Independent starts known | Independent work unobserved cells |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B [qwen35-27b] | 6 | 6 | 7 | 33587 | 62 | 284.145 | yes | 357.972 | 614.159 | 614.287 | 238804668 | 36861 | 410.083 | 41 | 0.000 | 0 | 0 |
| Qwen3.8-27B [qwen35-27b] +Skills | 6 | 6 | 8 | 30915 | 65 | 297.454 | yes | 373.467 | 650.607 | 650.741 | 238804668 | 247754 | 440.006 | 46 | 0.000 | 0 | 0 |

| Task index | Condition | Outcome | Original score | Nodes | Artifact edges | Owners | Operators | Schema failures | Later-valid/invalid owners | Identical repeated calls |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.8-27B [qwen35-27b] | incorrect_answer | 0.000 | 21 | 18 | manager:21 | bm25_retrieve:18; invoke_model:3 | 0 | 0/0 | 0 |
| 1 | Qwen3.8-27B [qwen35-27b] +Skills | incorrect_answer | 0.000 | 21 | 18 | manager:21 | bm25_retrieve:18; invoke_model:3 | 1 | 1/1 | 0 |
| 2 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 8 | 6 | manager:8 | bm25_retrieve:6; invoke_model:2 | 1 | 1/1 | 0 |
| 2 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 8 | 6 | manager:8 | bm25_retrieve:6; invoke_model:2 | 0 | 0/0 | 0 |
| 3 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 6 | 4 | manager:6 | bm25_retrieve:4; invoke_model:2 | 0 | 0/0 | 0 |
| 3 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 16 | 24 | manager:16 | aggregate_artifacts:1; bm25_retrieve:12; invoke_model:3 | 0 | 0/0 | 0 |
| 4 | Qwen3.8-27B [qwen35-27b] | incorrect_answer | 0.000 | 6 | 4 | manager:6 | bm25_retrieve:4; invoke_model:2 | 0 | 0/0 | 0 |
| 4 | Qwen3.8-27B [qwen35-27b] +Skills | incorrect_answer | 0.000 | 6 | 4 | manager:6 | bm25_retrieve:4; invoke_model:2 | 0 | 0/0 | 0 |
| 5 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 3 | 20 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
| 5 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 3 | 20 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
| 6 | Qwen3.8-27B [qwen35-27b] | success | 1.000 | 3 | 21 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |
| 6 | Qwen3.8-27B [qwen35-27b] +Skills | success | 1.000 | 3 | 18 | manager:3 | invoke_model:2; sample_frames:1 | 0 | 0/0 | 0 |

No statistical significance, general Skills efficacy claim, or size interaction is established by two models and six previously examined tasks. The resident 27B is Qwen3.8, so comparison against the smaller Skills model also changes model generation. If the ablation was not run, this report records the missing evidence rather than treating missing cells as failed trials.
