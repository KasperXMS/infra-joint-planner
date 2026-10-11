# Multi-scale Planner research conclusions v1

**下一阶段：有条件 Go，仅建议实际 Qwen3.8-27B plain 作为有界 Adapter 研究基线。本轮到此结束，不启动 Adapter 实验。** 该配置与 B0 成功任务相同，完成率更完整；固定 Skills 未增加成功任务，当前不推荐将 Skills 作为默认基线。

研究问题的具体答案：

- **硬件与规模：** 4B/9B/Ministral 3B 已在 A28 Jetson AGX Orin 的 CUDA/统一内存服务运行，27B 使用原 GPU0 resident 服务；均保留 32K preflight。未部署的调查模型和峰值显存仍无实测。实际 27B 属 Qwen3.8，只有 4B/9B 是同代 Qwen3.5 比较，无法推导统一参数规模阈值。
- **可靠性与质量：** plain 条件下 4B/9B/Ministral/27B 分别有 19/15/8/1 次 schema failures，TSR 为 1/6、1/6、0/6、4/6。27B 的两个错误答案没有被成功 schema 掩盖。Provider/SDK failures 仍是有效部署栈结果，但不等于模型固有能力差。
- **完整资源成本：** 27B plain 的云 API 和任务 E2E 较 B0 分别下降 30.56% 和 14.35%，resident runner work 上升约 6.88%。4B 的 Verifier 成本 $1.232258273 已超过 B0 全部云 API；9B plain/Skills 的独立 Planner runner work 分别为 2,925.359/2,925.983s。本地 Manager 的零云 API 费用不代表免费计算。全成本仍为 unknown。
- **Skills 与行为：** 9B/27B 的 TSR 均不变；9B Completion 下降，27B 云 API 增加 22.51%。27B plain/Skills 的 BM25 节点由 32→40，t3 由 4→12 次检索；9B 的 t6 则缩短且仍成功。效果随任务变化，未观察到总体收益。
- **信息流与 Adapter：** B0 有 7 个 Specialist turns，27B plain/Skills 均为 0；27B 主要由 Manager 直接规划。B0/27B plain/Skills 的 workflow 节点分别为 31/47/57，已记录 action payload transfer 分别为 10,626,750/36,861/247,754 bytes，各组另有同样的初始输入传输。后续可研究检索次数、artifact 复用和数据移动的权衡，须同时保持质量并记录规划/验证开销；当前数据尚不能认定所有额外节点冗余。
- **判断范围：** 六个此前已知任务、每条件一次运行，不支持显著性、普遍质量等价或质量—全成本 Pareto frontier。4B 混合 placement、外部争用、27B 跨代和不同 parser/runtime 均限制因果解释。4B/9B/Ministral 暂不作为 Adapter 基线；本轮没有自动增加任务或重跑。

Execution state: **complete**; analyzed 42 cells. Missing cells below are not run, never zero-score observations.

Sanitized input SHA256: `6100b61692500ee46b86f050a287c7ee22f71b47fe16a9ddbfae6d065d96ea69`. Base commit `70a75ae`. Raw prompts, answers, task payloads and credential evidence remain on the experiment machines.

Six frozen, previously examined tasks; one attempt per model/task/Skills condition. Results are descriptive: no significance, noninferiority, held-out validation, or universal scale threshold. Schema failures and legitimate budget exhaustion remain evaluation outcomes; no selective score reruns.

The original external-GPU-contention stop remains historical evidence. Current export state is **complete**; preserved stop receipts: 4. A completed authorized continuation can be complete while retaining that stop.

Placement amendment: the first three 4B cells (task indices 1/3/5) used GPU1; the remaining 4B cells use an independent A28 Planner service. The third 4B cell's actual score is retained with its external-contention flag; its Planner service/runner work remains unknown. The 4B six-task cohort mixes placement and contention conditions, so its aggregate cost is not a pure matched hardware comparison. 9B and Ministral use A28; the resident 27B remains on GPU0. Foreign processes are outside experiment ownership.

The continuation Skills allocation is 9B plus resident 27B, six matched tasks each. Timing verification that selection preceded the first 9B benchmark: yes. The old 4B allocation is preserved in the original freeze but is not executed as an extra ablation. Weights, semantic prompts, frozen Skills, evaluator, Scheduler and Executor are unchanged; retained benchmark cells are not rerun.

Infra-aware Workflow Adapter decision: **GO**. Conditional Go only for a bounded future Adapter study using actual Qwen3.8-27B plain: all six tasks completed and the same four tasks succeeded as B0, while redundant retrieval and data-movement differences provide concrete optimization targets. Frozen Skills did not improve TSR; 4B/9B/Ministral stacks are not recommended as the base. Full monetary advantage and statistical equivalence remain unestablished. No Adapter experiment is launched by this decision.

This decision is supplied by the researcher after reviewing evidence; the report generator does not invent an acceptance threshold. No Adapter, retrieval/sharing mechanism, join/leave logic, or additional experiment is started by this report.

The frozen slot `qwen35-27b` is reported as **Qwen3.8-27B [qwen35-27b]**. When the provenance correction receipt is present, its resident weight and projector match the official Qwen3.8-27B registry descriptors, rather than Qwen3.5-27B. The slot, weights and deployment were preserved. Only 4B and 9B provide a same-release Qwen3.5 size comparison; 27B also changes model generation, hardware and MTP/runtime configuration. None of these observational differences isolates a size-only causal effect.

| Condition | Observed/planned | Completion | TSR | Mean original score | Valid/schema attempts | Schema failures | Outcomes |
|---|---|---|---|---|---|---|---|
| B0 qwen3.8-max | 6/6 | 5/6 | 4/6 | 0.800 (5 evaluated) | 43/43 | 0 | incorrect_answer:1; success:4; verification_failed:1 |
| Qwen3.5-4B | 6/6 | 1/6 | 1/6 | 1.000 (1 evaluated) | 80/99 | 19 | context_budget_exceeded:1; success:1; terminal_contract_failed:1; turn_budget_exhausted:3 |
| Qwen3.5-9B | 6/6 | 3/6 | 1/6 | 0.333 (3 evaluated) | 41/56 | 15 | control_plane_failed:3; incorrect_answer:2; success:1 |
| Ministral 3 3B | 6/6 | 1/6 | 0/6 | 0.000 (1 evaluated) | 13/21 | 8 | control_plane_failed:2; incorrect_answer:1; terminal_contract_failed:3 |
| Qwen3.8-27B [qwen35-27b] | 6/6 | 6/6 | 4/6 | 0.667 (6 evaluated) | 57/58 | 1 | incorrect_answer:2; success:4 |

1. **RQ1 — hardware support.** Successful deployment receipts establish only the listed model/context/quantization configurations and point-in-time memory headroom on this setup. The independent Planner and protected Executor pool share GPU resources. Survey-only models, untried Orin placements and larger context windows remain unmeasured; peak memory is unknown.

2. **RQ2 — scale and protocol reliability.** Raw valid/schema-attempt counts, failure types and Completion above are the observed operating points. Safety admission is not an ability pass. No preregistered numerical reliability threshold or minimum acceptable parameter scale can be inferred from six tasks. Only Qwen3.5-4B/9B form a same-release size comparison.

3. **RQ3 — reliability versus TSR.** Compare schema validity, recovery and TSR jointly. A legal workflow can still produce an incorrect answer; later-valid recovery is not success. The matrix describes co-occurrence, not a causal effect or statistically established correlation.

4. **RQ4 — local versus strong quality.** The matched B0 and local six-task numerators above are directly descriptive under their recorded conditions. Equality or a small observed gap does not establish noninferiority or general parity. Partial conditions cannot support a six-task comparison. Historical B0 is kept separate.

5. **RQ5 — complete resources.** Manager savings must be assessed together with Specialist/Verifier recovery, physical service, runner work, transfer and E2E. API prices are only one component. GPU busy time, energy and GPU prices remain unknown, so complete monetary savings cannot be claimed. Early-failure resource reduction is not efficiency.

6. **RQ6 — Skills effect.** The ablation report gives paired with-minus- without deltas and explicit six-task coverage. Input-token differences include both instruction overhead and behavior changes. Two model sizes cannot establish a general size-by-Skills interaction; the 27B slot also changes checkpoint generation.

7. **RQ7 — workflows and information flow.** The same-task tables expose owner/operator choices, artifact edges, repetitions, schema failures and protocol recovery. Raw traces remain available privately for semantic assessment. Structural counts alone cannot establish whether decomposition or information aggregation was correct.

8. **RQ8 — future Adapter base.** The researcher's decision is GO: Conditional Go only for a bounded future Adapter study using actual Qwen3.8-27B plain: all six tasks completed and the same four tasks succeeded as B0, while redundant retrieval and data-movement differences provide concrete optimization targets. Frozen Skills did not improve TSR; 4B/9B/Ministral stacks are not recommended as the base. Full monetary advantage and statistical equivalence remain unestablished. No Adapter experiment is launched by this decision. Any future base must be named by actual checkpoint and runtime, preserve a quality baseline and permit measurement of recovery/physical costs. This run does not implement an Adapter.

9. **RQ9 — threshold/frontier.** These observations can identify candidate operating points for a later preregistered study, not a universal threshold or established quality-cost Pareto frontier. Missing full costs, six known tasks, one attempt, parser/runtime differences and the 27B generation correction limit such claims. No extra repeats or tasks were added.
