# Lightweight Planner Next-step Recommendation v1

**当前 Go / No-Go：正式 competence pilot、4B 扩展及 Infra Adapter 实验均 No-Go；
仅建议先做有界的通用 Manager context preflight 修复与 paired regression。**
依据是实际静默截断，并非已经证明 8B 语义能力差。原 18 cells 未执行，Skills 未实测。

| 问题 | 当前答案 | 支持程度与下一步 |
|---|---|---|
| Q1：8B 能合法、完整驱动 MAS 吗？ | 小 synthetic SDK 链路可以；完整 MAS competence 未证实 | 真 SDK 接受工具、typed failure、后续模型调用和终端 `A`。超限输入静默截断阻止正式 admission。不能回答真实任务成功率。 |
| Q2：Fixed Skills 改善 competence 吗？ | 未知 | Skills 已固定，无 B2 live task。必须用同任务 B1 vs B2；不能用 B0 vs B2 代替。 |
| Q3：Small + Skills 降低控制/总 inference cost 吗？ | 未知 | 本轮 7 次本地请求有真实 token/time 记录，但无同任务强 baseline、执行器成本、GPU 定价。不能把本地 API 无收费等同于计算免费。 |
| Q4：相对强 Planner 的质量缺口？ | 尚未测出语义质量缺口 | 观察的是 context transport 缺口，以及一次超出最低协议要求的 read-retry instruction deviation。没有三组质量比较。 |
| Q5：哪些失败适合 semantic adaptation / 强 Planner？ | 目前不能作实证分类 | 静默截断须由通用协议防护解决。未来 dependency/readiness/context-budget typed failures 可由 Agent 利用已有合法行动恢复；证据已覆盖却持续推理/分解错误才可能支持强 Planner escalation，仍须对照验证。 |
| Q6：继续 4B？ | 本阶段 No-Go | 先关闭 8B 协议与预算 admission，再取得最低真实任务 competence 证据；不在失败后换模型寻找好结果。 |
| Q7：Small + Infra-aware Workflow Adapter？ | 本阶段 No-Go | 应先完成合法且不丢输入的 Small ± Skills 对照。尚无法区分语义规划瓶颈与 transport 问题，不增加 Adapter 混淆归因。 |
| Q8：conditional escalation 的可观察触发？ | 仅能提出待验证规则，不能宣布已验证 | 使用 preflight 超限、预算剩余、重复 typed failures、重复 schema/argument rejects、Verifier 返回的证据覆盖/一致性问题、provider timeout。不得用 gold/最终 benchmark score 触发。 |

最小后续工作有明确顺序：先冻结通用 context adapter 的作用边界、token/模板核算和 output
reservation；证明合法小请求 wire 不变、超限请求发出前 typed reject 且 provider 请求数为零。
不自动摘要、不替换证据、不选动作、不改变物理执行、不使用强模型修复小模型计划。
若 provider 的有效窗口与预留行为仍不可信，则继续 No-Go。

之后用独立冻结的兼容性 acceptance 审计 read-retry 判据：替代合法恢复路径可作为协议
证据，但旧 smoke=false 不回写。无需要求模型主动并行；现有 runtime 并发回归已经通过。
仍须验证真实 SDK 下强 Specialist / Verifier 的 role identity、settings 和计费分离，完成
全角色 request/资源上限、超时后 inference drain、fresh Worker/tc/source admission。

全部 admission 关闭后，才考虑执行既有六任务 × 三组、每 cell 一次的最多 18-cell pilot。
保留原任务、技能、模型、组顺序和所有失败证据。不得根据本轮或后续 score 调 Skills，
不得追加 repetitions、模型搜索或恢复被用户终止的 Phase II。

对 Q8 中的候选信号还需区分处置：provider/context transport 问题应停止或 typed reject；
工具 readiness 问题先用合法反馈恢复；只有预先冻结并经对照证实的语义困难信号才适合
conditional escalation。任何 escalation 都将是新干预，不能混入本轮 B0/B1/B2 定义。
