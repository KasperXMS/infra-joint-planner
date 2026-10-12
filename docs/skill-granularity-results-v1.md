# Skill Granularity Pilot v1：30-cell 结果

30/30 正式 cells 已完成，每个 cell 仅执行一次，无选择性重跑。总体 Completion 为 12/30，TSR 为 4/30。首次正式执行至最后执行结束约 3 小时。前两个 cells 串行，其余 28 个按用户授权以最多三个 cells 并发执行；模型服务请求并行度仍为 1。

| Manager | Skill | Completion | TSR |
| --- | --- | --- | --- |
| Qwen3.5-4B | S0 无 Skill | 0/3 | 0/3 |
| Qwen3.5-4B | S1 Abstract | 2/3 | 1/3 |
| Qwen3.5-4B | S2 Procedure | 0/3 | 0/3 |
| Qwen3.5-4B | S3 Atomic SOP | 1/3 | 1/3 |
| Qwen3.5-9B | S0 无 Skill | 0/3 | 0/3 |
| Qwen3.5-9B | S1 Abstract | 1/3 | 0/3 |
| Qwen3.5-9B | S2 Procedure | 1/3 | 0/3 |
| Qwen3.5-9B | S3 Atomic SOP | 1/3 | 0/3 |
| Qwen3.8-27B | S0 无 Skill | 3/3 | 1/3 |
| Qwen3.8-27B | S3 Atomic SOP | 3/3 | 1/3 |

## 两个研究问题

**更细的程序性 Skills 能否显著改善 4B–9B Planner 的完成、正确率和成本效率？本轮不支持这一结论。** 4B 的 S1、S3 各答对同一个 Video-MME 任务，S2 没有成功；S1 的完成数还高于 S3。9B 的四个条件均未答对任务。粒度加细没有产生单调收益，S3 也没有超过 S1 的 TSR。完整 GPU/CPU 货币成本未知，不能据云 API 小计宣称完整成本效率改善。

**最优粒度是否取决于模型容量？本轮无法确定。** 4B 的观察结果偏向较短的 S1，9B 所有条件 TSR 均为零，27B 的 S0、S3 结果相同；27B 没有 S1/S2 条件，不能识别其四档最优粒度。27B 同时更换了模型代际和部署硬件，也不能据此建立纯容量因果解释。

每个条件只有三个不同任务的一次随机执行。S2/S3 比 S1 更长、知识表达更显式；前两个串行 cells 与后续并发 cells 的执行条件也不同。全部结果仅为探索性观察，不支持 TSR 显著性或通用 benchmark 结论。

## 失败与执行条件

18 个未完成 cells 中，11 个为 `APITimeoutError`，5 个耗尽 Manager turn budget，1 个违反终结 choice contract，1 个触发 Manager context preflight 合法拒绝。最后一个虽被 SDK 包装为 `APIConnectionError`，实际输入 31,318 tokens 加预留输出 2,048 超过 32,768，`inference_forwarded=false`；不能解释为独立连接故障或静默截断。

11 个超时单独记录，不全部解释为模型能力不足。9B 的 S0 三个 cells 均为超时，尤其不宜把其他条件较高的 Completion 直接归因于 Skills。共享服务排队与固定请求超时可能影响 TSR，当前证据不能分离排队时间与推理时间的贡献。所有正式结果保留，不补跑。

27B 在两个条件下都完成全部任务，但 MultiHop-RAG、LongBench 答案均错误，仅 Video-MME 正确。合法终结及 Verifier 检查通过并不保证 benchmark evaluator 判对。

## 成本与行为

全矩阵已知云 API 成本按冻结价格估算为 **$2.417197308**，不是最终账单或完整资源货币成本。Manager 超时请求的 token usage 缺失时保持 unknown。Verifier 共调用 249 次，输入 1,640,779 tokens；仅 4B 的四个 MultiHop-RAG 失败 cells 就消耗 80 次 Verifier 调用和 465,370 个输入 tokens。

27B 的 S0 → S3 在同样完成 3/3、成功 1/3 的同时，Manager/Verifier turns 从 20/20 降为 13/13，Specialist turns 从 8 降为 0，已知云 API 估算从 $0.252148 降至 $0.156792，减少 37.8%。4B 的 S1、S3 都成功 1/3，S3 的云 API 估算较低（$0.209778 vs $0.508756），但 Completion 也较低（1/3 vs 2/3）。这些是局部工作流与云费用观察，不能建立完整成本效率优势或稳定的最优粒度。

三路流水共享模型服务，跨 cell 的 service log 时间区间可能重叠；这些日志计数保留为诊断代理，不加总解释为独占 GPU 工作量。原始 trace 归属的 physical inference calls、已测模型 action 时间、E2E 和数据传输逐 cell 保留在统一报告中。GPU/CPU 价格、失败调用的完整 service work 和完整货币成本均为 unknown；E2E 不作为本轮 TSR 判断标准。

最终检查确认冻结源文件、Skills、任务和历史结果未变，原五个 Executor 实例未变，网络设置恢复，所有实验 Worker 已排空退出，自有新增 Planner 服务和转发已关闭。外部进程保持原状。模型切换时的一次端口绑定行政中断及原样续跑保留在证据中，没有重跑任何已执行 cell。原始敏感 traces 留在实验机器。

## 下一阶段判断

**No-Go：直接扩大“小模型加更细 SOP 即可提升正确率和完整成本效率”的实验。** 当前没有观察到相对 S1 的额外 TSR 收益，9B 的部署失败还限制了能力归因。进入更大规模研究前需要另行设计能区分部署超时、程序执行与语义答题失败的实验；本轮不启动该工作，也不启动 Infra-aware Workflow Adapter 或历史 Phase II。

完整交付：

- [逐 cell 与资源成本报告](../analysis/skill-granularity-pilot-v1/skill-granularity-report.md)
- [机器可读结果](../analysis/skill-granularity-pilot-v1/skill-granularity-results.json)
- [失败与同任务工作流分析](skill-granularity-failure-analysis-v1.md)
- [最终完整性](../analysis/skill-granularity-pilot-v1/final-integrity.json)、[并发检查](../analysis/skill-granularity-pilot-v1/concurrency-audit.json)、[续跑记录](../analysis/skill-granularity-pilot-v1/resume-metadata.json)
- [自有服务清理](../analysis/skill-granularity-pilot-v1/owned-service-cleanup-summary.json)、[匿名证据哈希](../analysis/skill-granularity-pilot-v1/raw-evidence-hashes.json)
