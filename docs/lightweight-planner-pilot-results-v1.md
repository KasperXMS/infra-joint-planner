# Lightweight Planner Pilot Results v1

**正式结果：未产生。Gate 1 NO-GO，18 个 nominal cells 全部未执行。**
本地 Manager 服务在 synthetic 超限输入上静默截断并返回 HTTP 200。已有一次小输入合法
SDK 终端链路，不能据此声称其能完整完成真实 MAS 任务。没有评估 scores、Skills effect、
成本优势、TSR 优势或 non-inferiority。

机器可读结果：[pilot-results-v1.json](../analysis/lightweight-planner-competence-v1/pilot-results-v1.json)；
判定：[gate-decision-v1.json](../analysis/lightweight-planner-competence-v1/gate-decision-v1.json)。
`—` 表示缺失/未执行，不表示已评估的 score0。

## 18-cell execution table

| Cell | Family / position | Group | Status | Legal terminal | Evaluated | Original score | E2E success |
|---|---|---|---|---|---|---|---|
| LPC-01 | MultiHop-RAG / 1 | B0 | not_run_gate1 | — | — | — | — |
| LPC-02 | MultiHop-RAG / 1 | B1 | not_run_gate1 | — | — | — | — |
| LPC-03 | MultiHop-RAG / 1 | B2 | not_run_gate1 | — | — | — | — |
| LPC-04 | MultiHop-RAG / 2 | B1 | not_run_gate1 | — | — | — | — |
| LPC-05 | MultiHop-RAG / 2 | B2 | not_run_gate1 | — | — | — | — |
| LPC-06 | MultiHop-RAG / 2 | B0 | not_run_gate1 | — | — | — | — |
| LPC-07 | LongBench-v2 / 1 | B2 | not_run_gate1 | — | — | — | — |
| LPC-08 | LongBench-v2 / 1 | B0 | not_run_gate1 | — | — | — | — |
| LPC-09 | LongBench-v2 / 1 | B1 | not_run_gate1 | — | — | — | — |
| LPC-10 | LongBench-v2 / 2 | B0 | not_run_gate1 | — | — | — | — |
| LPC-11 | LongBench-v2 / 2 | B2 | not_run_gate1 | — | — | — | — |
| LPC-12 | LongBench-v2 / 2 | B1 | not_run_gate1 | — | — | — | — |
| LPC-13 | Video-MME / 1 | B2 | not_run_gate1 | — | — | — | — |
| LPC-14 | Video-MME / 1 | B1 | not_run_gate1 | — | — | — | — |
| LPC-15 | Video-MME / 1 | B0 | not_run_gate1 | — | — | — | — |
| LPC-16 | Video-MME / 2 | B1 | not_run_gate1 | — | — | — | — |
| LPC-17 | Video-MME / 2 | B0 | not_run_gate1 | — | — | — | — |
| LPC-18 | Video-MME / 2 | B2 | not_run_gate1 | — | — | — | — |

## 分母与质量指标

| Benchmark | 每组 planned | 每组 executed / evaluated | Completion | Evaluated accuracy | E2E TSR |
|---|---:|---|---|---|---|
| MultiHop-RAG | 2 | 0 / 0 | 未测 | 未测 | 未测 |
| LongBench-v2 | 2 | 0 / 0 | 未测 | 未测 | 未测 |
| Video-MME | 2 | 0 / 0 | 未测 | 未测 | 未测 |

三组各 planned 6，总 planned 18。Gate 停止意味着没有正式试验观测，不能将“0 次执行”
写成“8B TSR=0%”。原 evaluator score、terminal validity 与 E2E success 均为 null。
synthetic 返回 `A` 既没有原 evaluator，也没有真实 Worker，不混入表中。

## 本轮实际资源账

只核算七次 synthetic 本地 HTTP 请求；不是 B0/B1/B2 的任务成本对比。
来源：[gate-resource-accounting-001.json](../analysis/lightweight-planner-competence-v1/gate-resource-accounting-001.json)。

| Probe | Requests | Provider input | Provider output | Cached input | 计时 |
|---|---:|---:|---:|---:|---|
| gate-001 | 3 | 16,205 | 130 | 10,773 | HTTP latency sum 2,454.001 ms；wall 3.110 s |
| gate-002 | 3 | 16,262 | 108 | 16,090 | HTTP latency sum 995.467 ms；wall 1.644 s |
| context-probe-001 | 1 | 16,386 | 1 | 4 | probe elapsed 3,388.196 ms |
| 合计 | 7 | 48,853 | 239 | 26,867 | 三种时间区间不用于推断 GPU compute |

context probe 的 input usage 是**截断后**计数，不包含服务丢掉的 25,886 tokens。
两次 smoke cached tokens 差异很大，且第二次有 harness repair；不能把速度差异归因于
Planner 改进。Provider cached-token 声明不等于可靠 GPU busy time 或可兑现的货币折扣。

| 资源维度 | 实际记录 / 可知范围 |
|---|---|
| 强 Manager / Specialist / Verifier API | 均无请求；本轮 cloud API charge 为 0，不代表正式任务成本为 0 |
| 本地 Planner | 7 requests；48,853 input / 239 output；计时如上；GPU-seconds、energy、货币均 unknown |
| 真实 physical model inference | 0；synthetic Gateway 的 invoke_model 返回固定测试文本，不是执行器推理 |
| 工具 / operator work | 仅 synthetic observations；没有正式 operator service cost |
| HTTP JSON bytes | requests 259,451；responses 3,767；是 application payload，不是 wire network bytes |
| 初始 materialization | synthetic 0 bytes；正式任务缺失，不冒充任务节省 |
| 模型初始化 / residency | 未新初始化；复用已有常驻模型，容量仍占用，不作“本地免费”结论 |
| GPU1 容量 / 争用 | 8B size_vram 7,962,330,398 bytes；设备整体 10,538 MiB；没有任务期 contention 测量 |
| Artifact movement / E2E task wall | 无正式任务，均缺失；SSH 审计开销未并入 HTTP payload |

所有正式 cell 的 control-plane tokens/turns/cost、physical action counts/tokens/service time、
total resource vector 和 workflow 均为 null。没有将缺失 usage 填零，没有统一加总秒与 bytes。

## Workflow 与错误归因

没有真实任务 ExecutionGrownGraph，因此不能报告 B0/B1/B2 nodes、owners、handoffs、
重复 retrieval、evidence omission、Verifier correction、Specialist decomposition 或并行
区间的组间差异。synthetic 序列只说明协议观察：

- gate-001：read_artifact typed failure → read_artifact success → invoke_model harness exception。
- gate-002：read_artifact typed failure → invoke_model synthetic success → native terminal `A`。
- context probe：provider 截断后返回一个 token；这不是可评分的 workflow。

| Taxonomy | 本轮观察 | 不能得出的结论 |
|---|---|---|
| Harness implementation defect | `.operator` AttributeError，原记录保留，通用修复与回归完成 | 不能记为 8B 推理失败 |
| Context/provider transport | 输入截断且 HTTP 200；**正式 blocker** | 不能记为 benchmark score0 |
| Recovery instruction deviation | repaired smoke 未重新 read，严格 predicate=false | 不等于工具协议不兼容；不能概括真实任务语义能力 |
| Schema / argument invalidity | repaired smoke 两次工具调用被 native schema 接受 | 不是全部 operators 的合法调用率估计 |
| Dependency/readiness | synthetic read failure 是人为注入 | 不是实际系统 readiness failure rate |
| Agent selection / semantic planning | 无正式任务样本 | 未知 |
| Worker / physical execution failure | 未启动正式 Worker | 未测 |
| Benchmark answer incorrect | 无 evaluator 调用 | 未测，不能填写 score0 |

保留错误答案和负结果的规则没有被绕开：没有正式结果可排除，synthetic 首次故障也未被覆盖。

## Skills effect 与证据限制

Skills 已固定，但 B1/B2 均未运行真实任务；没有 Skills competence 或成本 improvement
证据。B0/B1 的模型规模效应、B1/B2 的 Skills effect、B0/B2 的组合效果全部未知。
没有实现 Infra Adapter，不能把任何结果归因于 Infra-aware Optimization。

六任务已由研究者分析过。即使后续执行，18 cells / n=1 也只能作 feasibility pilot；
不能声称 held-out 泛化、统计显著或 non-inferiority。本轮 snapshot 证明模型驻留，
不能替代任务执行期 GPU/排队 telemetry。下一步依据见
[next-step](lightweight-planner-next-step-v1.md)。
