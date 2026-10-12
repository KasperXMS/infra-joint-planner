# Planning Capacity × Procedural Skills：最终研究报告

**结论：程序知识的呈现和当前事实的组织可以明显改变小模型的 workflow completion 与工作量，但本研究未建立可靠、普遍的 task-success 补偿机制。** 目标明确的单步 card 很有效，却不能替代自主调度、依赖绑定和多步 policy 执行。更大的 9B 在迁移测试中获益更多，primary 则没有同样方向的容量交互；证据不支持通用最优 Skill 粒度规律。

全部选定推理、统一回放和交付校验已完成：1,000 个有效 workflows、2,316 个单步决策查询，另保留 404 个工程无效请求的原始证据和费用。本轮成果定位为 **Type II 可复验的有限范围刻画 / Type III 有边界的负面发现**，不主张 Type I 新算法。结果只适用于下述 synthetic 分布、checkpoint、推理与工具契约。

逐组完整数据见 [实验总表](results/experimental-inventory.md)、[workflow CSV](results/workflow-condition-results.csv)、[physical model-stage 工作量](results/model-stage-work.csv)。Primary 的 [详细发现](heldout-findings.md)、[逐 episode 结果](results/heldout-binding-v1/results.csv) 和 transfer 的 [逐 episode 结果](results/structural-transfer-v1/results.csv) 包含全部失败，而非挑选的成功轨迹。

## 研究问题与证据边界

问题是程序性 Skills 能否补偿小模型的规划能力，以及收益究竟来自程序知识、信息组织还是 Harness 代劳。历史 18/42/30-cell 结果只用于定位问题：静态 Skills 的成绩不稳定，SDK/serving 问题与语义错误混杂，完成率提升不必然转化为任务正确率。历史结果没有覆盖、重跑或重新定级，原 Skill Granularity v2 保持暂停。

新的独立研究使用真实 Qwen3.5-4B/9B 推理和真实执行的确定性工具，**不是历史 InfraMAS 多 Agent benchmark**。图结构已提供给模型，因此主要测量依赖执行、条件操作选择、源更新后的重建、工具错误恢复及终结控制；不测量开放式任务分解，也不测量 LLM Specialist/Verifier 的生成质量。Verifier 只认证 provenance/freshness，明确不认证算术或 policy 正确性。

环境是双 RTX 5090、180 GiB cgroup 内存、Python 3.12.3、PyTorch 2.8.0+cu128、Transformers 5.19.0。两个官方 BF16 模型分别独占 GPU0/GPU1，直接 Transformers/SDPA 推理，greedy、thinking disabled、16,384-token 实际上下文预算、最多 256 output tokens、300 秒 cooperative request deadline。正式 workflow 使用 batch 2、64 turns、3,600 秒 task deadline；开发阶段 batch 4、48 turns。没有 constrained decoding、JSON 修补、隐式工具调用或强模型替代。上下文 preflight 先计算实际 token，超预算不转发，tokenizer 禁止 truncation。

这里使用原始文本 JSON action 协议，由独立 JSON Schema validator 决定是否合法，不是 provider-native SDK function calling。高 schema validity 只适用于本轮明确的 action/schema 合约，不能据此宣布历史 SDK 协议兼容性已经解决。

模型经 ModelScope 官方 Qwen 仓库下载，依赖使用清华 PyPI 镜像；运行阶段完全离线。Mutable master 不是上游 commit pin，26 个 checkpoint/config/tokenizer 文件的实际 SHA256 定义身份。缺失 causal_conv1d/fla 时保留正确的 PyTorch fallback，不在比较中途切换 backend。历史 Ollama Q4 与本轮 BF16 的分数不作受控量化/serving 对比。

## 研究如何从失败转向受控机制

| 阶段 | 样本与用途 | 状态 |
| --- | --- | --- |
| diagnostic-v1 | 首轮工程运行；chat-EOS framing 错误使合法输出被误报解析失败 | 整体排除能力分析；404 个已记录请求、101 个 batches 及原始失败保留并计成本 |
| diagnostic-v2 | 8 个开发任务 × 4 条件 × 2 模型；完整修正重跑 | 64/64；1,077 个请求精确校验通过 |
| role-placement-v1 | 同样 8 个开发任务 × 3 位置 × 2 模型 | 48/48；776 个请求精确校验通过；不是额外独立任务 |
| decision-context-probe-v1 | 48 个真实观察到的决策 × 3 上下文 × 2 模型 | 288/288；无工具执行；不是 workflow TSR |
| heldout-binding-v1 | 12 个新图、36 个更新变体 × 7 条件 × 2 模型 | 504/504；12,802 个请求完整校验通过 |
| structural-transfer-v1 | 16 个新图、48 变体 × 4 条件 × 2 模型 | 384/384；12,733 个请求精确校验通过；全部最终 ancestry 诊断完成 |
| decision-generalization-v1 | 338 个观察决策 × 3 上下文 × 2 模型 | 2,028/2,028；精确 prompt、token、raw schema 与独立 policy scoring 校验通过；诊断而非独立验证 |

开发阶段最清楚的混杂因素是 Skill 的放置位置。同样的静态 bank，从 latest user 移到 system 后，4B completion 从 4/8 回到 8/8，prompt tokens 从 690,264 降到 185,884；TSR 只是从 1/8 回到 baseline 的 2/8。9B 三个位置条件都是 2/8。Role、位置与 salience 一起变化，不能归因为 system authority 单独的因果作用。

开发决策 probe 在每个条件都给定 target 和 ordered handles。4B 的 operator accuracy 从 full-target 的 28/48 提高到 full-card 的 45/48；9B 从 26/48 到 44/48，但其中两次 target 错误，joint accuracy 为 42/48。Isolated-card 两模型都是 39/48。完整历史加 card 并不差于删去历史；然而 full-card 增加相关事实重复及 tokens，isolated-card 同时删除其他任务上下文。它们不能孤立识别 history interference，也不能估计 autonomous TSR。

据此冻结的机制不是更长的静态 SOP，而是 **observation-only value–policy organization**：把已经观察到的有效父 artifact、数值及顺序显示在每个公开 policy 旁边。Adapter 不选择下一 node、不求正确 operation、不执行或修复动作、不读取参考答案。最关键 control 是 unjoined rendering：保持相同事实、重复次数、ordered parent 信息、current output、receipt contract，以及每状态相同的 standalone support token 长度，仅改变组织方式。实际轨迹和总 token 仍可分叉。

本 synthetic task 的公开条件 policy 本身也可由确定性程序求值，离线 scorer 正是如此评分。因此本轮没有证明 operation selection 是不可外部化、必须依赖 LLM 的语义能力；只是有意把决策留给被测模型，以测量它消费程序知识的能力。更强 controller 直接选 operation 会改变贡献归属，应当作为 Harness externalization 单独评价，不能把它的正确性归为小模型 Skills 能力。

## 已完成 primary：完成率、正确率与有效工作分离

| 条件 | 4B Completion / Numeric success | 9B Completion / Numeric success |
| --- | --- | --- |
| None | 36/36；0/36 | 33/36；2/36 |
| Static / system | 36/36；1/36 | 36/36；0/36 |
| Same static / latest user | 6/36；0/36 | 29/36；1/36 |
| Local rule | 26/36；1/36 | 29/36；2/36 |
| Static / system + ledger | 29/36；0/36 | 29/36；0/36 |
| Static / system + joined facts | 36/36；5/36 | 36/36；5/36 |
| Static / system + unjoined facts | 33/36；2/36 | 36/36；3/36 |

Joined 对 static/system 的 numeric TSR 差为 +11.11 pp、+13.89 pp；对知识与支持长度匹配的 unjoined 差缩小为 +8.33 pp、+5.56 pp。后者 graph-cluster bootstrap 区间分别为 [0,22.22]、[0,13.89] pp；9B 减 4B 的交互为 -2.78 pp，区间 [-16.67,11.11] pp。这里只有 12 个选定的 synthetic graph clusters，不能把 504 episodes 当作 504 个独立自然任务或宣称一般显著性/容量规律。

504 episodes 中有 430 个合法终结、22 个 numeric success、74 个合法 turn exhaustion；12,802 次原始动作全部 JSON/schema-valid，没有 context rejection、request/task timeout、phase violation 或 terminal-contract failure。所有动作、工具观察与 evaluator 均已逐条精确回放。错误不能再简单归咎于历史 SDK 解析或服务端排队。

| 可观察结果/历史 | Episodes | 解释 |
| --- | --- | --- |
| 错答案，无 unexpected tool error | 333 | 工具契约与终结正常不代表 policy 正确 |
| 错答案，同时有 unexpected tool error | 75 | 语义错误与调用/恢复错误可以共存 |
| Turn exhaustion，已有接受的错误 policy 计算 | 52 | 不能仅按最后错误给单一因果标签 |
| Turn exhaustion，没有一次被接受的 compute | 22 | 空决策集合不是正确 branch competence |
| Numeric success，整个已执行 policy 历史正确 | 14 | 合法、正确的完整执行 |
| Numeric success，最终 ancestry 正确、此前历史有错误 policy | 6 | 可能是更新使旧路径作废，不能证明有意识错纠错 |
| Numeric success，最终 ancestry 保留错误 policy | 2 | 算术碰撞；保留原 evaluator 分数，不追溯改分 |

22 个零计算任务的 1,342 次依赖错误全部已经取到了正确的源 artifact 集合，只是与声明的 parent order 不同。1,320 个相邻 retry 全部重复相同参数。它们不缺输入、不提前请求 root，也不需要尚未构建的中间 parent，局部瓶颈是 ordered-handle binding 与不响应 rejection。严格顺序契约即使对某些交换律 operation 也会执行；因此它是本 Harness 的 contract competence 观察，不等于数学运算必然错误，不应外推为普遍规划缺陷。

两个 joined arm 都完成 36/36，却各有 31 个错答案。验证次数接近所需下界（4B 60/60；9B 62/60），证明 freshness/provenance 与语义 branch 正确性是不同属性。两个模型都存在“新输入、新 handle，却沿用旧正确 operation”的事件：满足旧选择正确、实际值改变及新 gold operation 改变的严格描述条件，分别有 12、14 次。这个行为与 anchoring 相容，不识别内部心理原因，也不证明历史动作导致新错误。

Depth 1 的 numeric success 为 20/252，depth 3 为 2/252；后两次恰好都是 retained-policy collisions。Depth 3 没有一个 policy-compliant submitted ancestry。这支持本分布上的组合执行困难，而不是一个由两个模型确定的通用规模阈值。

Primary 生成跨度 5,548.171 秒，6,423 个 physical batches，12,802 logical requests，36,332,362 prompt tokens、378,039 output tokens。Batch service wall 相加为 10,783.491 秒，不能称为 GPU kernel time。Joined 相比 unjoined：4B prompt work 降 28.8%、turns 降 18.2%；9B 仅降 1.3%、0.6%。相对 static/system，joined 的 prompt tokens 反而增加。Primary 未单独记录 renderer 时间，保持 unknown，不根据 transfer 回填。

## 独立 structural transfer

384/384 workflows 全部执行一次，12,733 个请求和 5,063 个 matched-fact states 通过统一精确校验。296 个 completion、19 个 numeric success、88 个合法 turn exhaustion。所有 12,733 个 action 都通过 raw JSON/schema；没有 context rejection 或 request/task timeout。独立目录的 versioned ancestry 分析完成，所有非修正字段与原始输出完全相同，原 numeric evaluator 未改动。

| 条件 | 4B Completion / Numeric success | 9B Completion / Numeric success |
| --- | --- | --- |
| None | 24/48；0/48 | 29/48；1/48 |
| Static / system | 30/48；1/48 | 38/48；3/48 |
| Joined facts | 42/48；2/48 | 48/48；7/48 |
| Unjoined facts | 38/48；2/48 | 47/48；3/48 |

Joined-minus-unjoined 为 4B 0 pp（两次 rescue、两次 regression），区间 [-8.33,10.42] pp；9B +8.33 pp（七次 rescue、三次 regression），区间 [-10.42,27.08] pp。跨模型交互为 +8.33 pp，区间 [-8.33,27.08] pp。相较 static/system，joined completion 提高 25 pp、20.83 pp，但 numeric success 只增加 2.08 pp、8.33 pp。独立迁移因此支持工作流完成改善，未支持一个稳定、普遍的 matched organization TSR 优势，也不能建立模型容量规律。

工具错误包括 3,092 次 dependency mismatch、434 次 unknown node、304 次 unknown source、49 次 stale/invalid artifact、119 次 terminal-contract failure。最后 119 次发生在六个 4B unjoined episodes；primary 没有 terminal failure，因此不能把“终结协议已解决”外推到迁移分布。9B joined 虽然 48/48 完成、没有 unexpected tool error，却仍有 41 个错答案，再次把契约/状态正确与语义 policy 正确分开。

**19 个 numeric success 中只有 7 个最终 ancestry policy-compliant，另外 12 个包含错误 operation 的数值碰撞。** 4B none/static/joined/unjoined 的 compliant counts 分别为 0/1/0/0，9B 为 0/0/5/1。4B joined 的两次 numeric success 均为碰撞；9B joined 七次中两次为碰撞。诊断的是已提交 ancestry 的 policy compliance，不追溯修改冻结的 numeric TSR。

Depth 2 numeric success 为 12/192，其中 6 个 policy-compliant；depth 4 为 7/192，其中只有 1 个 policy-compliant。Joined 的 stable/flip pre-update exact prefixes 仅 12/16（两个模型相同）；paired graph 不等同于始终一致的 counterfactual trajectory。没有把 prefix 不一致的例子强制修成一致或重跑。

迁移生成跨度为 5,764.402 秒；6,392 个 physical batches、12,733 logical requests、41,377,721 prompt tokens、348,470 output tokens，合计 batch service wall 10,704.411 秒。Joined 相比 matched unjoined，4B prompt work 降 23.1%、turns 降 17.1%，9B 分别降 7.3%、4.8%。Renderer wall 平均每次约 6.1–6.4 ms，包含同时构建 matched renderings 与 tokenizer/padding；不是纯 join 的最小部署开销或 CPU 货币价格，不包括 shared full-prompt tokenization。当前材料未支持用价格给 mixed-condition physical batches 强制分摊条件成本。

迁移机制、任务与顺序在 primary score inspection 前冻结：移除 layer-name/topological presentation cues，使用 opaque IDs 与打乱的公开 node 顺序，保留私有 evaluator 的原 topological order。12 个 primary 图上的预先冻结信息价值阈值触发了两模型整个 384-episode design；没有按成绩挑选 cells。迁移结果只在完整模型/研究结束后分析。

本迁移分布同时改变了呈现、标识、图深度和 seeds；它是独立 structural stress transfer，跨阶段变化不能只归因于打乱 public node order。Within-study 同任务的四条件比较保持这些因素一致。

完整的互斥 [failure partition](results/structural-transfer-v1/failure-analysis/failure-decomposition.md)：151 个错答案且无 unexpected tool error，126 个错答案伴随工具错误，63 个 turn exhaustion 已执行错误 policy，7 个耗尽前没有合法 compute，18 个已有合法 compute 但未观察到 policy 错误的耗尽，12 个成功但 retained-policy collision，6 个成功且整个执行 policy 历史正确，1 个成功且最终 ancestry 正确但此前发生错误。最后一种不能证明主动识别和修复错误。

## 最后的条件决策诊断

全部 2,028 个真实请求完成并通过统一校验。每组 338/338 schema-valid、target-correct，因而 operator accuracy 与 joint accuracy 相等；没有模型定向工具执行。逐请求延迟和安全元数据见 [decision-results.csv](results/decision-generalization-v1/decision-results.csv)，完整汇总与 coverage 见 [summary.json](results/decision-generalization-v1/summary.json)。

| 模型 / context | Joint accuracy | Pre /207 | Post /131 | 原错 rescue / 原对 regression | Prompt / Output tokens |
| --- | --- | --- | --- | --- | --- |
| 4B Full target | 159/338，47.04% | 95 | 64 | 13 / 30 | 680,652 / 10,528 |
| 4B Full card | 250/338，73.96% | 156 | 94 | 97 / 23 | 712,996 / 10,528 |
| 4B Isolated card | 185/338，54.73% | 117 | 68 | 47 / 38 | 219,778 / 12,688 |
| 9B Full target | 169/338，50.00% | 106 | 63 | 11 / 18 | 680,652 / 10,528 |
| 9B Full card | 271/338，80.18% | 170 | 101 | 123 / 28 | 712,996 / 10,528 |
| 9B Isolated card | 202/338，59.76% | 125 | 77 | 64 / 38 | 219,778 / 9,646 |

Full card 相比 full target 的 query-weighted gain 为 +26.92 pp（4B）和 +30.18 pp（9B），prompt tokens 增加 4.75%。以 11 个 observed graphs 等权的 macro gain 分别为 +25.18 pp，bootstrap interval [17.07,32.34]，以及 +31.67 pp，[22.04,40.57]。这两种 weighting 不是同一个 estimand。Full-card-minus-isolated 的 macro gain 为 +19.10 pp，[3.33,34.80]，和 +19.97 pp，[7.33,31.82]。区间只描述选定 observed states 的探索性 cluster uncertainty，不支持自然任务 TSR 或人口范围显著性声明。

Full card 仍留下 88/338 和 67/338 个错误，尽管 target、ordered handles 和当前 policy 已明确提供。重复相关事实的作用没有与额外长度完全拆开；删去历史也同时删去了其他上下文，不能把 isolated 对比解读为纯 history interference。两模型各 507 个 physical batches，batch service wall 691.392 秒和 691.076 秒，总 generation span 1,179.227 秒；两个阶段的 GPU handoff 有重叠，不能将每请求 latency 累加为 GPU 工作。

从全部 36 条 primary 9B baseline 轨迹选择 first actually executed conditional decision per node/update phase，包含原对与原错，使用实际观察中间值而非参考中间值。338 个 eligible decisions 全部保留；3 条 source trajectories 没有可提取决策，因此 observed queries 只覆盖 11/12 source graph clusters。未执行的状态不插值。它是 primary 后选择问题的机制诊断，不是 independent held-out workflow validation；三个 context 条件都给定 target，不能当作 TSR。

该 query pool 来自 9B 的实际访问状态，不是两个模型各自自然产生的状态分布；未被访问的困难状态被条件化排除。卡片 prompt 也不是原 autonomous workflow 的完整干预：它额外指定 target，且沿用无 skill-bank 的 baseline 历史。Primary joined workflow 则有相同静态 system bank 并自己调度 action。故一跳 joint decision gain 与 workflow TSR gap 只能并列解释，不能相乘推导完整任务成功率或作为独立模型容量效应。

## 对五个 RQ 的最终回答

| RQ | 本轮可支持的回答 | 未被识别的部分 |
| --- | --- | --- |
| RQ1 Capacity compensation | 放置正确的程序 bank 与当前事实组织能改善依赖执行/终结的完成率；9B joined transfer 达到 48/48 completion，但只有 7/48 numeric 和 5/48 ancestry-compliant success。它不能可靠补偿多步条件 operation 选择。 | 图已给定；没有开放式任务分解、真实 Specialist 委派或自然领域迁移证据。 |
| RQ2 Representation | 相同 bank 的位置影响很大；matched joined/unjoined 将知识覆盖、重复和 per-state support 长度控制住后，TSR 优势变小且跨分布不稳定。 | Local/full 改变 delivery 与内容量；card/target 不是长度匹配；不能把全部收益称为纯粒度效应。 |
| RQ3 Externalization | 有效 artifact、顺序、失效与 receipt bookkeeping 可以由程序投影；模型仍可能在拥有新鲜输入后选错 operation。 | 所有 synthetic policy 也可确定性求值；没有证明哪类语义决策必须保留给 LLM。强 controller 的正确性必须归属于 Harness。 |
| RQ4 Interaction | 4B 工作量减少更稳定，9B 在 transfer 的 joined numeric/compliant success 更高；primary/transfer 的跨模型 interaction 方向不同且区间宽。更深依赖主要放大组合失败。 | 两个 checkpoint 和少量选定图不足以建立最优粒度、通用容量阈值或 scaling law。 |
| RQ5 Cost/reliability | Joined 相对 matched unjoined 在两个 study 均减少失败-inclusive turns/prompt work，尤其 4B；相对 static 却不保证少 tokens。Verifier 最小化也不保证语义正确。 | 未测 primary renderer 时间、条件 GPU 货币成本和混合 batch 的精确价格分摊，不能证明统一 cost-per-success 优势。 |

因此，对“更细程序 Skills 能否显著改善 4B–9B 的真实规划完成、成功与成本效率”的回答是：**完成和工作量可以改善；可靠任务成功的补偿尚未成立。** 对“最优粒度是否依赖容量”的回答是：**现有证据不足以确定；效果取决于 delivery、具体任务和 Harness，不能简化为小模型一律需要更细 SOP。** 这不是对所有 Skills 的无效性证明。

## 文献位置与最多两个研究建议

通用“更细 Skills 更好”“容量感知 Skill compiler”“structured state 更好”均已有直接邻近研究，不能通过换名主张创新。SkillsBench 与 controlled granularity study 已覆盖 availability/granularity；Demystifying 与 Harmful Skills 已覆盖 anchoring/负迁移/额外验证。最接近当前机制的是：

- StateMem v1：https://arxiv.org/html/2608.19652v1 —— structured current state、dependency rechecking 与 matched answer wrapper 已覆盖广泛的 state externalization，也含 standing-rule inputs；本轮反复自主 action selection/rebuilding 的评价边界不是算法 novelty 证明。
- SkillSmith v1：https://arxiv.org/html/2605.15215v1 —— 编译 runtime interface、typed operators/boundary guards/fallback；本轮 adapter 更弱，只展示事实，全部决策留给被测模型。
- SkVM v3：https://arxiv.org/html/2604.03088v3 —— model/harness profiles 与 compile/runtime optimization 已覆盖广义 capacity-conditioned execution；其 software environment dependency binding 与观察值绑定不同，但术语差异不建立 novelty。

文献的实际版本、阅读范围、Method/Ablation 与 abstract-only 限制见 [ledger](literature-novelty-ledger.md) 和 [landscape](research-landscape.md)。只保留一个优先方向：**从合法完成到 policy-compliant autonomous workflow 的测量与支持边界**。

1. **Problem Statement：** 当前输入已新鲜、工具调用合法、Verifier 已通过时，小模型仍会在反复自主执行中违反公开操作规则。单步高正确率和 numeric TSR 容易掩盖这一缺口。
2. **Closest Related Work：** [StateMem v1](https://arxiv.org/html/2608.19652v1) 已覆盖 structured state/rechecker/answer wrapper；[SkillSmith v1](https://arxiv.org/html/2605.15215v1) 已覆盖 typed runtime operators、guards 和 fallback；[SkVM v3](https://arxiv.org/html/2604.03088v3) 已覆盖 model/harness-aware compilation。差异是本轮保留反复自主 action/rebuilding，并逐 ancestry 归因；不据此声称新算法。
3. **Unresolved Gap：** 在 observation-only 帮助与 executable semantic controller 之间，哪些决策外部化能在真实自主任务中提高 policy-compliant success，且计入验证、编译及恢复成本后仍值得采用？本轮只给出 synthetic 实证问题，不证明既有工作普遍失效。
4. **Proposed Mechanism：** 首先采用分层测量契约，分别报告 raw schema、合法终结、freshness、最终 ancestry policy compliance 与 numeric success；后续如研究执行机制，应将事实展示、typed action binding、semantic validation/controller 列为独立干预。此次只实际实现并评估前两类测量及 observation rendering，没有偷偷启用 semantic action guard。
5. **Supporting Experimental Evidence：** Primary 430 completions/22 numeric success，transfer 296/19；transfer 19 次 numeric success 中 12 次 retained-policy collision。9B joined transfer 48/48 completion、41 个错答案，而显式 target full-card 单步为 271/338。Matched join 对 4B transfer TSR 净效应为零，却减少 23.1% prompt work；结果说明完成、正确性与效率需要拆开。
6. **Alternative Explanations：** Greedy/batching、公开顺序契约、选定 flip-sensitive 合成图、深度与名称变化、operation 语言歧义、query pool 来自 9B observed states、card 的事实重复和长度、统计功效不足，均限制外推。没有证明因果 anchoring、纯 history interference 或模型内在容量极限。
7. **Expected Novelty：** Type II/III 的受控失效边界、逐 policy ancestry 计量和匹配对照数据可以构成可复验贡献。通用 state externalization、Skill compiler、typed guards 不是新的；尚不满足 Type I 算法创新证据。
8. **Required Next Experiments：** 若未来单独立项，使用新自然领域任务，冻结 node-selection/handle-binding/operator 三种支持边界并与 StateMem/SkillSmith 类强基线进行等总预算比较；使用不易数值碰撞的目标或独立语义验证；增加独立模型/graph clusters 检验 interaction。必须单独计入 controller/compiler/verifier 成本。这些是后续验证条件，本轮不自动启动。
9. **Risks and Failure Cases：** Controller 可能变成直接求解器；语义 checker 可能与生成器共享错误；新接口改善 schema 却不改善答案；严格顺序导致人工失败；小样本成功偶然、预算转移及更多验证抵消收益。若强基线已覆盖该测量缺口，研究应收缩为负面复现材料，而不是再命名一个框架。

## 成本、证据、停止决策

所有 13 个 model-stage 计 30,108 个已记录 logical requests、14,498 个 physical batches、86,048,955 prompt tokens、865,696 output tokens。剔除工程无效能力结果后，29,704 个有效 requests、85,183,030 prompt tokens、857,212 output tokens；其中 27,388 次 workflow 模型调用和 2,316 次无工具决策查询。工程阶段 404 个请求、101 batches、865,925 prompt/8,484 output tokens 均计入总资源，不丢弃失败成本；中断时没有记录的 in-flight work 保持 unknown。

总 batch service wall 24,186.127 秒是双 GPU 各批次服务 wall 的和，不是总 E2E、request wait 总和或 GPU kernel time。整个目标从 2026-10-13 01:05:05 HKT 开始，最后 telemetry sample 为约 06:02:10 HKT，对应 4.9515 小时、CNY30.0061 的租金估计。备份和清理后，关机连接观测在 06:18:37 HKT，若以该时刻作为计费边界，5.2256 小时对应 **CNY31.6669**；这不是最终账单，也未独立确认停费时刻。粗粒度 NVML sampling 得到 GPU0 约 1,206.8 Wh、GPU1 约 1,417.2 Wh 的 board-energy proxy，不是电表或价格。

原始敏感证据已保存在实验机和持久共享目录，另在一级工作区交付 `D:\Codes\infra-aware-mas-new\planning-skills-research-v1-traces.tar.gz`：7,645,542 bytes，SHA256 `c80856a584718b9652bed9921fca7b509e9db0d394771773ab99ac8ea0b90aeb`，全部 3,411 个成员逐长度/SHA 校验通过。Git 中仅提交 [公共原始证据索引](evidence/final-evidence-index.json)、脱敏结果、代码/配置和 [完整冻结 inference source snapshot](evidence/final-frozen-inference-source.tar.gz)。后者 242 个 source members、340,882 bytes，SHA256 `a6799c0a84c70be740812fb814e02df60cdee1372744ff05bba030c6a0fb9408`。当前 Git 的后处理工具不假称已包含于此前冻结 snapshot。模型全部 26 个文件在推理后重新校验一致。

最终 transfer 原始 publication receipt 意外包含自身空文件 hash；原 receipt 保留。单独的 [publication-verification-v2](results/structural-transfer-v1/publication-verification-v2.json) 排除该不成立的 self-entry，核对所有实际 data/figure 文件；两张 PNG 已人工视觉核查可读。没有修改任何模型结果或图数据。

清理前所有自有 GPU workers 和 supervisors 已退出，CUDA compute apps 为空；只保留 guard 到关机请求。持久备份和本地交付 SHA 均已核对。AutoDL `/usr/bin/shutdown` 缺 shebang，首次直接调用在执行前报 ENOEXEC；随后通过 `/bin/bash /usr/bin/shutdown` 调用时 SSH 被远端关闭，后续连接超时，**与关机一致，但 API 返回和平台计费状态 unknown**。没有为确认账单重启实例。当前 guard 增加仅 ENOEXEC 的 Bash fallback，三个 mock 回归通过；这是推理完成后的 portability 修复，不追溯替换执行时冻结 guard，也没有宣称真实 20-hour 路径已端到端验证。详见 [关机观测](evidence/final-shutdown-observation.json)、[备份/清理检查](evidence/final-backup-and-cleanup-precheck.json) 和 [交付检查](evidence/final-private-delivery-verification.json)。

本实例租金由用户给定为 CNY6.06/hour，不虚构 GPU USD 或把本地价格填零。Cloud API calls 实际不存在，费用可记为 0；request latency 重叠不当作物理工作，mixed-condition batch wall 不强行分摊成条件价格。60 秒 NVML power sampling 仅为粗略 board-energy proxy，非电表或货币成本。

**边际信息价值决定：本轮停止。** 研究已从工程诊断转到位置控制、条件单步诊断、事实/长度匹配 primary、独立结构迁移，再到新 policy 的完整观察状态诊断。迁移解决了“收益是否只来自简单呈现线索”的主要不确定性，最后 probe 解决了“新 policy 下提供 target/current card 后是否仍选错”的问题。结果共同支持 completion/work 改善比 correctness 更稳定，而不支持 observation-only Skills 已可靠补偿自主规划。

继续仅增加 static SOP 长度、更多相似 seeds 或 27B 参考点，主要提高分数或精度，难以区分剩余解释，也不能修复算法 novelty 边界。更有信息的下一步需要换研究契约：自然领域、独立语义判据或 executable controller 的成本匹配对照；这些与最接近文献高度重叠，需另行立项。本轮没有耗尽 10/20-hour 额度，停止理由是所选问题的新增信息价值下降，不是时间上限、低分或第一个矩阵完成。仍未排除的解释在上表和九项建议中明确保留，不把有限负面发现扩张为普遍不可能性。

复现入口见 [reproducibility.md](reproducibility.md)，逐要求的最终检查见 [completion-evidence-map.md](completion-evidence-map.md)。独立分支 `planning-skills-research-v1` 的变更限于本 namespace 和 `.gitattributes` 的对应路径规则；历史 results、Skills、Physical Executor 和暂停的 v2 不变。报告随最终交付 commit/push 发布，提交 SHA 以仓库 history 和最终回复为准，避免报告自引用其尚未生成的 commit hash。后续研究与历史实验都不自动启动。
