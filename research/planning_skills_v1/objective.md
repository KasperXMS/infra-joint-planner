# Autonomous Research Objective
## LLM Planning Capacity × Procedural Skills

### Mission

Conduct an autonomous, literature-grounded, experimentally rigorous exploration of the relationship between LLM planning capabilities and procedural skills.

**Primary research question:**

How can procedural skills compensate for limited planning capabilities in smaller language models, and what mechanisms provide reliable, cost-effective improvements beyond existing research?

本任务不是完成固定实验矩阵，而是自主发现有研究价值的问题、建立假设、进行受控实验、分析失败，并持续推进有证据支持的研究方向。

你被授权自主执行整个研究过程，**不需要在中间节点请求人工确认**。

---

## 1. Research Objectives

重点探索以下相互关联的问题，但不要求平均分配资源：

**RQ1 — Capacity Compensation**

哪些 Planning 能力可以通过 Skills 补偿？包括任务分解、依赖管理、工具组合、状态转移、失败恢复、证据传递和终结控制。

**RQ2 — Skill Representation**

为什么相同的程序性知识使用不同抽象粒度、表示方式或执行接口后，会产生不同效果？怎样区分真正的程序性帮助与单纯增加 Prompt Tokens？

**RQ3 — Planning Externalization**

哪些在线规划决策可以预先外部化为可复用程序、条件规则或执行单元？哪些决策仍然必须依赖 LLM 的语义推理？

**RQ4 — Model–Skill Interaction**

Skill 的收益是否与模型容量、基础能力、任务复杂度和 Harness 支持能力有关？是否存在模型能力与 Skill 表示形式的匹配关系？

**RQ5 — Cost and Reliability**

Skill 能否减少实际完成任务所需的推理调用、无效操作、Verifier 开销和执行延迟，而不损害最终正确性？

这些研究问题是起点，不是固定搜索空间。可以根据文献与实验证据提出更精确的新问题，或放弃已被否定、已有充分研究的假设。

---

## 2. Reading List — Directly Accessible Documents

优先访问以下正式论文页面及 PDF。可以下载到研究工作区、提取 Method、Experiments、Ablations 和 Limitations。

### Core empirical evidence

**[R1] SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks**

- Paper: https://arxiv.org/abs/2602.12670
- PDF: https://arxiv.org/pdf/2602.12670
- Project: https://www.skillsbench.ai/

研究 Skill 对不同模型、任务和 Harness 的正负效果，关注小模型补偿与负迁移。

**[R2] Skill Availability and Presentation Granularity in Large-Language-Model Agents: A Controlled SkillsBench Study**

- Paper: https://arxiv.org/abs/2605.31408
- PDF: https://arxiv.org/pdf/2605.31408

重点检查抽象粒度实验的控制变量和效果估计。不要重复简单的 High/Medium/Low Prompt 对比。

**[R3] Demystifying Agent Skills: Why They Work—Until They Don't**

- Paper: https://arxiv.org/abs/2608.14036
- PDF: https://arxiv.org/pdf/2608.14036

重点研究 Procedural Anchoring、Skill 使用方式、失败模式与跨 Harness 泛化。

**[R4] Agent Skills Can Be Harmful: An Empirical Study of Skill-Induced Failures in LLM Agents**

- Paper: https://arxiv.org/abs/2608.11888
- PDF: https://arxiv.org/pdf/2608.11888

重点研究 Skill 为什么增加无效验证、冗余程序和执行成本。避免只关注正收益。

### Skill representation and execution mechanisms

**[R5] SkillCraft: Can LLM Agents Learn to Use Tools Skillfully?**

- Paper: https://arxiv.org/abs/2603.00718
- PDF: https://arxiv.org/pdf/2603.00718

关注工具组合复杂度、程序抽象以及跨任务 Skill 复用。

**[R6] SkillReducer: Optimizing LLM Agent Skills for Token Efficiency**

- Paper: https://arxiv.org/abs/2603.29919
- PDF: https://arxiv.org/pdf/2603.29919

关注 Token Overhead、Progressive Disclosure 和非必要 Skill 内容。

**[R7] SkillLens: Adaptive Multi-Granularity Skill Reuse for Cost-Efficient LLM Agents**

- Paper: https://arxiv.org/abs/2605.08386
- PDF: https://arxiv.org/pdf/2605.08386

关注层级粒度和动态 Skill 复用。注意不要与微软同名项目混淆。

**[R8] SkVM: Revisiting Language VM for Skills across Heterogenous LLMs and Harnesses**

- Paper: https://arxiv.org/abs/2604.03088
- PDF: https://arxiv.org/pdf/2604.03088

重点研究模型/Harness 能力刻画、Skill 编译、运行时优化。直接涉及本研究的新颖性边界。

**[R9] SkillSmith: Compiling Agent Skills into Boundary-Guided Runtime Interfaces**

- Paper: https://arxiv.org/abs/2605.15215
- PDF: https://arxiv.org/pdf/2605.15215

关注将 Skills 编译为细粒度执行接口、减少重复规划和面向小模型的 Skill 消费。

### Skill learning, transfer and workflow memory

**[R10] From Raw Experience to Skill Consumption: A Systematic Study of Model-Generated Agent Skills**

- Paper: https://arxiv.org/abs/2605.23899
- PDF: https://arxiv.org/pdf/2605.23899
- Project: https://microsoft.github.io/SkillLens/
- Code: https://github.com/microsoft/SkillLens

关注 Skill Extractor 与 Consumer 的能力差异、跨模型迁移和 Negative Transfer。

**[R11] Skill-Pro: Learning Reusable Skills from Experience via Non-Parametric PPO for LLM Agents**

- Paper: https://proceedings.mlr.press/v306/mi26d.html
- PDF: https://raw.githubusercontent.com/mlresearch/v306/main/assets/mi26d/mi26d.pdf

关注 Skill-MDP、启动/执行/终止条件及可复用 Skill 的优化方法。

**[R12] Agent Workflow Memory**

- Paper: https://proceedings.mlr.press/v267/wang25bx.html

关注 Workflow Memory 与 Procedural Skills 的关系，避免将已有 workflow reuse 机制重新命名。

### Reading Rules

- 优先阅读 R1–R4、R8–R10，再根据实际研究方向选择其他论文。
- 不要求所有论文逐页精读。
- 必须记录所使用的具体版本、Method、Ablation 和来源 URL。
- 如果 PDF 无法访问，尝试论文 HTML、作者主页或官方仓库，不能虚构阅读结果。
- 允许自主检索更多相关研究，特别是 2026 年的最新工作。
- 对任何候选创新，都要寻找最接近的 2–3 篇已有工作，并明确相同点与差异。

建立动态的 `literature-novelty-ledger.md`，记录哪些问题已经解决、哪些尚未被充分研究。

**不要把“没看到相关论文”直接当作 Novelty 证据。**

---

## 3. Existing Experimental Evidence

首先复用本项目已经产生的真实证据，而不是从零开始猜测。

相关材料：

- Lightweight Planner 18-cell Pilot
- Multi-Scale Planner 42-cell Evaluation
- Skill Granularity 30-cell Pilot
- Skill Granularity Failure Analysis
- Timeout Diagnosis
- 已导出的原始 Traces
- S0/S1/S2/S3 Skill 文件

已知观察：

- Qwen3-VL 8B 的 SDK-native tool protocol 不可靠。
- Qwen3.5 4B/9B 的规划能力受协议、Workflow State 和 Serving 条件共同制约。
- Generic Skill 与静态 Atomic SOP 均未表现出稳定的 TSR 改善。
- 部分 Skill 能改变控制轮次和委派行为，但未必提高答案正确性。
- Physical Executor Context Rejection 与 Evidence Continuity 是独立问题。
- 过去 A28 的 180 秒超时受到单槽排队影响，不能简单归因于模型能力。

这些结果属于研究动机与诊断材料，不是新机制的 held-out 测试集。

不必重复历史 30-cell 矩阵，也不得覆盖原有证据。

---

## 4. Autonomous Research Strategy

采用 **Evidence-Driven Research Loop**：

**Read → Identify Gap → Form Hypothesis → Design Controlled Experiment → Execute → Analyze → Decide Next Action**

每轮自主判断：

1. 当前假设是否已有研究充分覆盖？
2. 哪种实验能够以最低成本排除最关键的不确定性？
3. 当前结果是支持、否定还是无法识别该假设？
4. 是否需要增加对照、检查原始 Trace 或修改机制？
5. 继续研究这一方向，还是转换到更有潜力的问题？

允许动态选择研究路线、实验规模、模型和技术方法。

### 初始候选机制

优先考虑但不局限于：

**A. Capacity-conditioned Skill Representation**

同一程序性知识对不同能力模型是否需要不同程度的显式化、拆解或抽象？

**B. State-conditioned Procedural Support**

完整静态 SOP 与当前状态相关的局部程序指导，是否对模型施加不同的决策负担？

**C. Procedural Planning Externalization**

哪些 Tool Selection、Dependency Tracking、State Transition、Recovery 决策可以转移到可复用程序中？

**D. Skill–Harness Boundary**

Skill 不能解决的问题，是否应由确定性 Harness 处理？两种机制之间是否存在可量化的分工边界？

**E. Skill-induced Failure and Cost Regression**

为什么看似正确的 Skill 反而导致更多执行步骤、无效验证或证据交接失败？

这些方向不需要全部实现。优先选择文献尚未充分解决、又有明确可测试假设的方向。

---

## 5. Experimental Methodology

可以自主创建小型 Planning Microbenchmarks，也可以利用已有研究的公开任务和工具。

Microbenchmarks 应能独立测量：

- Task decomposition
- Tool composition
- Dependency planning
- State tracking
- Error recovery
- Evidence transfer
- Terminal control

优先设计可参数化的依赖深度、分支数量、状态数量和错误类型，使用确定性工具与可检验的目标条件。

模型优先级：

- Qwen3.5-4B
- Qwen3.5-9B
- 必要时使用 Qwen3.8-27B 作为参考

模型代际、量化和部署差异必须明确披露，不得直接解释为纯参数规模效应。

实验规则：

1. 区分 development 和 held-out 任务。
2. 对每项核心假设设置必要的匹配对照。
3. 保持同一比较内的模型、工具、采样和 Harness 契约一致。
4. 区分 Skill 提示、动态 Skill Delivery 和可执行 Harness 支持。
5. 记录合法工具调用、Workflow Completion、Task Success 和完整可测成本。
6. 不根据测试集答案反复调整 Skill。
7. 必要时重复随机实验并保留全部样本。
8. 严格区分推理失败、协议失败、部署超时和真实任务错误。

允许探索性 Prompt 或 Skill 修改，但必须保存版本和关联实验，不能通过选择性展示制造提升。

### Experiment Selection

不要求执行所有组合。

优先采用 Sequential Experimental Design：

- 少量诊断实验发现机制；
- 针对可能的混杂因素做受控消融；
- 冻结最有希望的机制；
- 使用独立任务或模板进行验证；
- 根据结果决定继续深入还是切换方向。

如果很快得到明确结果，不需要等到预设时间结束才继续下一步。

如果连续实验没有新增信息，应及时停止该方向，而不是靠扩大矩阵消耗 GPU。

---

## 6. Full Autonomy and Problem Resolution

这是无人值守的自主目标任务。

**授权你自主处理研究过程中出现的技术与实验问题，不需要逐步询问。**

在已提供的研究实例及独立工作区内，允许：

- 安装和修复依赖；
- 部署、重启或重新配置自有 vLLM/Ollama 服务；
- 修改实验代码、工具、配置和 Microbenchmark；
- 修复解析、超时、并发、GPU OOM 等工程问题；
- 根据证据调整研究假设和实验顺序；
- 创建新 Skill 表示或执行机制；
- 执行必要的消融、回归与独立验证；
- 调查和修正分析程序；
- 下载公开论文、模型及必要研究资料；
- 提交、push 代码和研究报告。

**无需每次实验结束后审计、暂停或请求确认。**

但需要满足以下边界：

- 使用独立实验分支与 namespace。
- 不覆盖历史结果或原始 traces。
- 不修改实验室现有 InfraMAS 部署和 Physical Executor。
- 不触碰其他用户、外部进程或非本任务资源。
- 不向公开仓库上传 API Keys、SSH Credentials、私人任务数据或敏感原始轨迹。
- 不自动购买额外云资源、变更付费套餐或创建新的付费实例。
- 不能跳过安全验证或通过静默修改 evaluator 制造成功结果。
- 不在未声明的情况下通过 constrained decoding、Oracle 信息或额外强模型调用替代被测 Planner 的能力。

如原计划失效，可以自主制定替代方案并继续执行。所有实质性方法或环境变化必须记录。

---

## 7. Adaptive Time and Resource Policy

**10 小时是预期研究投入，不是硬停止时间。**

不要将研究机械拆成固定的一小时或两小时阶段。

### 提前出现结果

如果几小时内就完成最初的探索：

- 自动深入已经发现的机制；
- 增加有价值的消融或 held-out 验证；
- 检查跨模型迁移；
- 研究失败边界；
- 必要时探索下一项有潜力的假设。

不要因为原定阶段已完成就停止。

### 到达 10 小时

自主检查当前进展：

- 是否存在具有明确效果、但尚缺关键验证的机制？
- 是否有尚未排除的替代解释？
- 增加少量实验是否能够明显提高结论可信度？
- 是否仍有值得尝试、且不重复已有工作的研究方向？

如果存在明确价值，可以继续执行，不需要人工批准。

但不能仅以“可能继续提高成绩”为理由无限搜索。

### Resource Protection

AutoDL 现有实例：

- 2 × RTX 5090 32GB
- 180GB RAM
- ¥6.06/hour

持续记录资源使用、运行时长和估算租金。

默认采取 **10 小时软目标、20 小时总运行安全上限**。超过 10 小时可以根据实际发现自主延长；20 小时用于防止无人值守时无限运行或持续计费。

不以到达时间点作为否定研究方向的理由。若达到安全上限而仍有重要结果未完成，应保留 checkpoint、明确后续实验与预算需求，不丢失证据。

不得擅自增加其他付费云资源。

可以在自有实验资源上进行合理并发，但不能牺牲结果可识别性。优先利用双 GPU 提高吞吐，避免之前的单槽排队超时。

---

## 8. Checkpointing and Research Accountability

维护持续更新的 Research Journal，至少记录：

- 当前研究假设；
- 相关文献及 Novelty 判断；
- 选择实验的原因；
- 实验配置；
- Raw Results 与统计结果；
- 主要失败模式；
- 已排除的解释；
- 下一步决策及其依据；
- 累计运行时间和资源使用。

通过周期性 checkpoint 保证可恢复性，但不要因为 checkpoint 暂停推理或生成冗长进度报告。

每项主要实验必须有明确的比较条件和评价规则。

**不要把探索过程中表现最好的单次运行直接当作最终科学结论。**

---

## 9. Desired Final Deliverables

最终应交付可独立阅读、可复现实验的研究成果。

### A. Research Landscape

梳理已有研究，包括：

- 已经解决的问题；
- 目前各方法的实际假设；
- 相互重叠的贡献；
- 对小模型 Planning 尚未充分解释的现象；
- 可验证的研究空白。

### B. Experimental Findings

每项实际执行的探索必须有真实结果。

包括模型、任务、Skill、执行配置、成功率、失败分类、Token、Latency 和成本。

不得用推测数据填补缺失结果。

### C. Mechanism-level Analysis

重点回答：

- Skill 实际补偿了什么能力？
- 为什么某些 Skill 有效、另一些无效？
- 受益是否源于内容、表示、执行接口还是 Harness？
- 效果是否与模型规模或 Planning Complexity 相关？
- 额外的 Skill 管理成本是否抵消收益？

### D. Candidate Research Contributions

最多推荐两个优先方向。

每个方向必须包括：

1. Problem Statement
2. Closest Related Work
3. Unresolved Gap
4. Proposed Mechanism
5. Supporting Experimental Evidence
6. Alternative Explanations
7. Expected Novelty
8. Required Next Experiments
9. Risks and Failure Cases

### E. Artifacts

提交：

- Literature/N​ovelty Ledger
- Research Journal
- Microbenchmark Generator
- Skill Definitions
- Experiment Configurations
- Raw Trace Index
- Result Tables
- Mechanism Ablations
- Final Research Report
- Reproducibility Instructions

保存原始实验和失败记录；GitHub 仅推送适合公开的代码与脱敏证据。

---

## 10. Success Criteria

任务的成功不取决于是否获得正面的 TSR 提升。

真正的目标是产生以下至少一种成果：

**Type I — Mechanism Discovery**

找到一种此前缺少充分研究、能够在控制变量后提高小模型规划可靠性或降低实际决策成本的机制。

**Type II — Scientific Characterization**

建立 Skill 表示、模型能力与 Planning Complexity 之间可复验的关系，包括非单调性、能力阈值或负迁移。

**Type III — Negative Finding**

在排除部署错误和明显混杂因素后，明确证实某种看似有前景的 Skill 机制不具备稳定收益，并解释原因。

**Type IV — Research Gap Identification**

发现已有研究的关键假设不适用于当前 Open-ended Planning 场景，提出能被实验检验的新研究问题。

不要追求机械完成阅读清单或最大化调用次数。

**持续探索直到新增实验的预期研究信息价值明显降低，或者到达资源安全上限。**

全程自主决策，无需中间确认。完成后提交、push 并输出最终研究总结；不要自动启动无关的 InfraMAS 项目。