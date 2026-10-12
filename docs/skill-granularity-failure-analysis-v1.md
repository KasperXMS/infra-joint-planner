# Skill Granularity Pilot v1：失败与工作流分析

30 个正式 cells 均已执行一次，没有补跑。12 个合法完成，其中 4 个被 benchmark evaluator 判为正确；另外 18 个未完成。以下分析来自实验机器保留的原始事件、请求计量和脱敏结果，只公布匿名任务编号、操作类型和计数。t1、t2、t3 分别对应本轮新冻结的 MultiHop-RAG、LongBench-v2、Video-MME 样本。

## 失败分类

| 最终结果 | 4B（12 cells） | 9B（12 cells） | 实际 Qwen3.8-27B（6 cells） | 合计 |
| --- | ---: | ---: | ---: | ---: |
| 正确完成 | 2 | 0 | 2 | 4 |
| 合法完成但答案错误 | 1 | 3 | 4 | 8 |
| `APITimeoutError` | 4 | 7 | 0 | 11 |
| Manager turn budget 耗尽 | 4 | 1 | 0 | 5 |
| 终结 choice contract 不合法 | 1 | 0 | 0 | 1 |
| Manager context preflight 拒绝 | 0 | 1 | 0 | 1 |

六个 `AgentLoopError` 可进一步区分：4B 的 t1 四个条件，以及 9B 的 t1 S1，均耗尽 20 个 Manager turns；剩余一个是 4B t3 S2 的终结 choice contract 失败。后者此前已经得到两次成功的 `invoke_model` 观察，但直接终结的答案没有满足终结格式约束，不能归为 turn budget 耗尽。

9B t1 S2 外层异常为 `APIConnectionError`，实际是合法的 context preflight 拒绝：最终请求 rendered input 为 31,318 tokens，加预留输出 2,048 超过 32,768，且 `inference_forwarded=false`。此前一次输入 30,564 的请求被允许并通过完整性检查。这不是静默截断，也不是已证实的独立连接故障。

11 个超时是共享部署、固定请求时限下实际交付的失败，不能全部归因于模型规划能力。9B t1 S0、t1 S3、t3 S1、t3 S2 在首次 Manager 请求即超时，尚未执行工具；9B S0 三个任务最终均超时。因此，不能把其他条件更高的 Completion 直接解释为 Skills 的能力提升。现有证据也没有确认另一个独立的 parser 故障类别。最终实验完整性通过与这些请求级失败可以同时成立。

后续[只读超时诊断](skill-granularity-timeout-diagnosis-v1.md)核对了全部 11 个客户端与服务端取消事件：三路 cell 流水共用 Orin 单槽服务，180 秒等待包含排队，已有明确排队案例。该补充保留所有原结果，不进行选择性补跑。

## 同任务结果与工作流

表中“对”为合法完成且 evaluator 正确，“错”为合法完成但 evaluator 错误，“未”为未完成。27B 只预注册了 S0/S3。

| Manager / 任务 | S0 | S1 | S2 | S3 |
| --- | --- | --- | --- | --- |
| 4B / t1 | 未：turn budget | 未：turn budget | 未：turn budget | 未：turn budget |
| 4B / t2 | 未：timeout | 错 | 未：timeout | 未：timeout |
| 4B / t3 | 未：timeout | 对 | 未：choice contract | 对 |
| 9B / t1 | 未：timeout | 未：turn budget | 未：context budget | 未：timeout |
| 9B / t2 | 未：timeout | 错 | 错 | 错 |
| 9B / t3 | 未：timeout | 未：timeout | 未：timeout | 未：timeout |
| 27B / t1 | 错 | 未设置 | 未设置 | 错 |
| 27B / t2 | 错 | 未设置 | 未设置 | 错 |
| 27B / t3 | 对 | 未设置 | 未设置 | 对 |

4B t1 四种条件均持续检索、读取或尝试合成，却全部耗尽预算。S0/S1/S2/S3 分别出现 7/2/3/2 次 schema validation failure；减少 schema 错误没有转化为该任务的完成。轨迹还包含阶段限制、未物化或过大的 artifact，以及 Physical 模型请求的上下文保护拒绝。Physical resolver 的 `estimated_input` 是保守的字节/图像成本代理，不是真实 tokenizer token 数，不能与 Manager rendered tokens 混用。

4B t3 的两个正确工作流不同。S1 在取帧后将图像整理成 contact sheet，再成功调用模型；S3 先提取 clip，遇到不支持的视频输入后转向取帧，并继续恢复到合法模型调用。S2 虽然有成功的模型观察，最后仍因终结 contract 失败。这里能确认的是工具执行与终结控制的差异，不能据此证明更细 SOP 必然产生更好的语义推理。

9B t2 的 S1/S2/S3 均完成但错误。S3 有四个 `bm25` 检索节点，最后成功的 `invoke_model` 却使用 `inputs: []`，整个已记录 artifact 图为零条边：检索输出没有通过 artifact inputs 接到最终合成。这是可见的证据交接缺口；prompt 可能内联携带部分信息，不能由空 inputs 单独推断完全没有证据或认定幻觉。原始答案及实体不公开，检索是否覆盖全部 gold 证据、哪一步语义判断错误，不能由这些计数精确归因。

| 27B 同任务 S0 → S3 | Manager / Verifier turns | DAG 节点 | `bm25` 节点 | `invoke_model` 节点 | 其他变化 | evaluator |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | 7/7 → 4/4 | 8 → 14 | 6 → 12 | 2 → 2 | 更少轮次承载更多检索节点 | 错 → 错 |
| t2 | 6/6 → 5/5 | 11 → 4 | 8 → 2 | 3 → 2 | Specialist requests 8 → 0 | 错 → 错 |
| t3 | 7/7 → 4/4 | 4 → 3 | 0 → 0 | 3 → 2 | 两者均包含取帧 | 对 → 对 |

S3 在 27B t2/t3 上减少了部分交互和委派，但没有提高该组三个任务的 TSR。t1 也说明“轮次更少”不等于“物理工作更少”：检索节点反而翻倍。合法终结和 Verifier 允许完成，不保证 evaluator 正确。27B 的实际来源是 Qwen3.8，不能把名义候选键解释为 Qwen3.5-27B 的同系列容量对照。

## Schema 恢复与 Verifier 工作量

Schema failure 是被拒绝并返回给 Agent 的观察，不必然是最终失败。4B t3 S1 的三次拒绝依次涉及 `sample_frames` 缺少 `arguments`/`inputs`、一个不合法 `invoke_model`、以及 `invoke_model` 缺少 `arguments`；随后同类操作有合法调用，最终正确完成。4B t3 S3 的一次 `read_artifact` 缺少 `arguments` 后被放弃，Agent 改用其他合法操作最终成功，不能写成该 `read_artifact` 本身被修复。

相反，27B t1 S0 的 `invoke_model` 缺少 `inputs` 和 t2 S3 的不合法 `bm25`，都出现后续合法同类调用，但最终答案仍错误。9B t2 S3 的九次 schema 拒绝中，一部分 `invoke_model` 后续恢复合法，五次缺少 `arguments` 的 `read_artifact` 没有后续合法同类调用；最终空 artifact inputs 的合成仍可通过 schema。Schema 合法性、证据连接、答案正确性是不同层次。

| Manager | 正式 cells | Manager 计量请求数 | Verifier 请求数 | 已知 Verifier input tokens | Specialist 请求数 | Schema failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4B | 12 | 146 | 141 | 882,626 | 0 | 28 |
| 9B | 12 | 82 | 75 | 512,127 | 0 | 28 |
| 27B | 6 | 33 | 33 | 246,026 | 8 | 2 |

Verifier 共调用 249 次，已知 input tokens 合计 1,640,779。4B t1 四个条件全部失败，却消耗 80 次 Manager 请求、80 次 Verifier 请求和 465,370 个 Verifier input tokens。这说明反复失败或恢复也会放大 Verifier 工作量，不能据此断言 Verifier 导致失败。计量请求数与 reasoning turns 并非完全相同：9B 最终一次 context preflight 在转发前拒绝。超时的 Manager 响应存在未知 usage，不能把已知 token 小计称为完整成本；缓存计费及 GPU/CPU 价格也不能从上述 tokens 推导。

## 解释边界与判断

本轮不支持“SOP 越细，TSR 越高”，也不足以确定通用的最佳粒度。4B 的 S1 与 S3 答对同一个视频任务，S2 没有成功；9B 四条件均没有正确答案，且大量超时限制能力归因；27B S0/S3 的正确任务相同。S3 的若干工作流缩减值得保留为观察，但不是已验证的质量或完整成本收益。

前三类任务各只有一个新样本、每条件一次执行。前两个 cells 串行，其余 28 个按用户授权共享资源、最多三个 cells 并发；模型服务请求并行度仍为 1。并发排队、缓存历史、数值差异、S2/S3 的长度与显式工具知识、模型代际及部署硬件均限制比较。E2E 和服务工作量仅作执行诊断，不能当作独占资源成本或纯模型能力指标。

因此，对直接扩大“细 SOP 可提高小模型正确率及完整成本效率”的主张为 **No-Go**。所有失败保留，不因能力差、合法预算耗尽或 provider 超时补跑；本分析不启动新实验、Infra-aware Workflow Adapter 或历史 Phase II。
