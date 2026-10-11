# Avoidable Work Characterization v1

2026-10-11，回顾性描述分析。**尚未证实可安全删除的 Planner/model work，
也未证实任何正的净节省。** 发现的是 618 个可追溯信号：577 个需要
counterfactual validation，41 个 Unknown；Exact Candidate 为 0。
这不是“真实冗余为零”的证明。

## 分析总体和复现

按 [Evidence Inventory](avoidable-work-evidence-inventory-v1.md) 的顺序完成
来源核查、cost decomposition、候选识别和分类。原始 ZIP 仅只读、在内存解析；
278 次尝试均核验 manifest 中的 trace hash、字节数和事件数，再按有效 admission
视图选取 257 个 trace：Phase I 168，Phase II 旧快照子集 89。
未将 18 个 confounded、2 个 operational exclusions 和 Phase II 原始71混入总体。
没有恢复 Phase II；未为 cell136 创建 admission。

| 总体 | Benchmark | 有效 cells | score1 | score0 | 未评估 |
| --- | --- | ---: | ---: | ---: | ---: |
| Phase I | LongBench-v2 | 56 | 22 | 28 | 6 |
| Phase I | MultiHop-RAG | 56 | 32 | 15 | 9 |
| Phase I | Video-MME | 56 | 51 | 5 | 0 |
| Phase II 本地子集 | LongBench-v2 | 32 | 16 | 16 | 0 |
| Phase II 本地子集 | MultiHop-RAG | 25 | 14 | 11 | 0 |
| Phase II 本地子集 | Video-MME | 32 | 24 | 8 | 0 |

Phase I 计数与已审阅历史报告一致。Phase II 此表不代表终止时的 135 admissions；
缺少 cells90–135，其中105和117是未完成 Agent failures。此处的任务、cell、attempt、
admission 和 trace 不互换；每个条件 n=1，重复条件不是独立任务。
没有计算跨 benchmark 的统一准确率。

资源逐 run 记录于 `analysis/avoidable-work-resources-v1.jsonl`；按
experiment/benchmark/Planner/method/outcome 的完整分布、known/unknown coverage
及同 task/Planner/network 的 B0 contrasts 位于
`analysis/avoidable-work-summary-v1.json`。候选见
`analysis/avoidable-work-opportunities-v1.jsonl`。全部只包含元数据及 hashes。

```powershell
.venv/Scripts/python.exe -m scripts.avoidable_work_analysis_v1 `
  --archive ../phase1-traces-2026-10-08-cells001-168.zip `
  --archive ../phase2-traces-2026-10-08-cells001-089.zip `
  --output-dir results/avoidable-work-reproduction-001
```

输出目录必须不存在；已有输出拒绝覆盖。summary 记录输入 ZIP/manifest/journal
以及分析脚本和复用 helpers 的 hashes。运行不调用 Agent、API、GPU、网络 shaping
或 admission creator。原始 provider usage 缺失，SDK usage 不能替代 provider billing。

## R1：控制、推理和数据成本

下表为 measured receipt subtotals；有失败缺失的总体总成本保持 unknown。
所有 work sums 都不是 E2E 的可相加分项，model wrapper 不再与 model service 重复计费。

| 指标 | Phase I，168 runs | Phase II 本地子集，89 runs |
| --- | ---: | ---: |
| Manager starts / completed work subtotal | 1,449 / 9,662.679 s | 631 / 4,856.032 s |
| Verifier starts / completed work subtotal | 975 / 3,146.280 s | 631 / 2,209.957 s |
| Specialist starts / completed work subtotal | 239 / 1,410.142 s | 137 / 806.672 s |
| Manager / Verifier / Specialist latency 完整 runs | 167 / 163 / 166 | 89 / 89 / 89 |
| Prepared model actions | 398 | 264 |
| Successful inference receipts | 226 | 136 |
| Model service receipt subtotal | 13,048.788 s | 7,737.373 s |
| Model service 完整 runs | 166/168 | 85/89 |
| Action movement 完整 runs | 131/168 | 68/89 |
| 完整 movement runs 的已知字节和 | 95,624,601 B | 31,427,529 B |
| Tool/operator work 完整 runs | 132/168 | 70/89 |
| 完整 tool-work runs 的已知 work 和 | 1,248.234 s | 280.037 s |
| 完整 control API USD / GPU-seconds | unknown / unknown | unknown / unknown |

这些是不同 coverage 的列，不能把已知子集的成本推断到所有 runs，也不能把
prepared actions 当作成功推理数。模型 token receipts 按 run 保留，未测失败不填零。
初始 materialization 独立列在 resource vector 的 Network 分量；action bytes 不包含
cloud prompt、tool-result RPC 和 HTTP wire traffic。零 action movement 不等于零通信。

| 总体 / Benchmark | Manager / Verifier / Specialist starts 中位数 | 已知完整 model-service work 中位数 |
| --- | --- | ---: |
| Phase I / LongBench | 10 / 8 / 0 | 11.567 s |
| Phase I / MultiHop | 6 / 5 / 0 | 123.291 s |
| Phase I / Video | 5.5 / 4 / 0 | 31.421 s |
| Phase II 子集 / LongBench | 7 / 7 / 0 | 14.756 s |
| Phase II 子集 / MultiHop | 8 / 8 / 0 | 129.421 s |
| Phase II 子集 / Video | 4 / 4 / 0 | 31.201 s |

Manager 是最大的已记录控制 work 来源。Phase I 各方法均24cells，其 Manager starts：
B0=165、B1=147、A=168、B=173、C=327、D=315、E=154。
C/D 的额外交互和20-turn上限值得检查，但不能把 C−B0 的 turns 全称为可删除开销：
语义轨迹、Verifier cadence、token/cache和 specialist 使用均可能不同。
P1=DeepSeek，P2=Qwen；Verifier 固定 Blind Qwen。

按单 run 的已记录 Manager work，Phase I cell85（MultiHop/P1/B/score0）为157.232s，
其后 cell78、140（LongBench/P1/D/未评估）为149.114s、148.288s。
Phase II 子集最大的是 cell14（MultiHop/P1/A/score1）146.805s。
这只能比较 measured work，不能推出最高 provider USD 的 Planner。
历史 [cross-Planner table](large-scale-crossplanner-analysis-v1.md) 的 API USD 是冻结
list-price usage estimate，且表内中位数限定 score1 子总体，不能与这里的全总体混排。

## R2：候选频率与潜在规模

| Pattern | Phase I 点数 / 涉及 runs | Phase II 子集 点数 / 涉及 runs | 分类 |
| --- | --- | --- | --- |
| A：相同规范化确定性请求及输入身份 | 0 / 0 | 0 / 0 | 无符合当前窄检测器的匹配 |
| B：重复 evidence identity / 非终端无显式消费者 | 63 / 21 | 42 / 14 | Counterfactual-required |
| C：Quote protocol control-only batch | 472 / 49 | 0 / 0 | Counterfactual-required |
| D：传输完整 aggregation 后做 retrieval | 33 / 31 | 8 / 7 | Unknown |

C 的49runs包括有 protocol 痕迹的 B 变体；不能假设只有最终 C/D 标签才可能有相关事件。
点数不是独立实验单元。Pattern间和同一 decision 上的候选会重叠，不可直接累加成收益。
Phase II 没有 C/D 方法，不能把 C=0 解读为控制机制已经被优化。
重复完全相同 context rejection 的窄检测器未发现匹配；参数变化的合法恢复不计为重复。

A 的 fingerprint 保留有序输入、内容hash/媒体类型/版本信息（若存在）、参数与
contract；只有明确 output rebinding contract 才能忽略输出ID。
历史配置/defaults/实现/determinism closure 不完整，初始输入也常缺少内容hash。
所以相似 retrieval、同一 artifact ID、不同 query/top-k 都不被升级为 Exact。
没有支持 Exact 的历史点，**可验证 exact 节省规模目前无法确定**。

B 的105个点中99个有 model-service receipt，总计9,353.180s；其余6个未知。
Phase I 已知 subtotal为5,607.331s，Phase II子集为3,745.848s。
这只是“如果删掉这些操作，原先执行了多少已测 service work”的局部毛上界，
不是预计净节省；新 fallback/replan/inference 和干预自身成本可能抵消全部毛收益。
没有正的节省下界。单 operation 最大是 Phase II cell15/P2/B1/score1 的796.637s；
cell16/P1/B0/score0 的候选为670.771s。成功和错误轨迹都含昂贵工作。

无显式消费者不表示信息未使用。扫描后续实际 reasoning/verifier input，105个B点中
33个出现其原始输出文本的完整 substring；短输出可能偶然命中，长输出也可能仅被展示。
因此这是弱 exposure signal，不是语义贡献证明；其余72个也不能排除转述、截断、
prompt-carried evidence 或内部决策影响。每点记录真实图消费者的hash和后续输入数。
删除候选只能保留**干预前** observations，不能把被删调用的历史输出重新注入。

C 的472个 control-only batches 都有可定位的输入边界；控制请求 work 在 metadata 中
记录为 enclosing reasoning work，不归入可节省毛上界。Quote构建本地时长不等于额外
Manager/Verifier云调用成本。压缩交互是否保留反馈和语义机会必须实验判断。

D 的41个点有完整对应成功 operator receipts，operator work合计仅8.242s；
关联 action-transfer payload subtotal：Phase I 95,300,555B，Phase II子集31,287,083B。
这些字节是原操作的观测 footprint，尚无证明它们可全部避免。
global BM25 的全局文档频率、平均长度、稳定排序/tie和top-k必须保持；简单
“各 shard 本地top-k再拼接”不具有一般等价性。不能把 lossy pruning 标成 Exact。

## R3：成功、错误与未完成轨迹

| 总体 / outcome | runs | Manager starts中位数 | Verifier starts中位数 |
| --- | ---: | ---: | ---: |
| Phase I / score1 | 105 | 6 | 5 |
| Phase I / score0 | 48 | 9 | 7 |
| Phase I / 未评估 | 15 | 20 | 3 |
| Phase II 子集 / score1 | 54 | 6 | 6 |
| Phase II 子集 / score0 | 35 | 7 | 7 |

这些是成本的描述性条件分布，不是跨benchmark TSR。没有将未完成变成score0。
Phase I 八个 Manager budget exhaustion 为 cells71/76/78/91/125/133/140/164，
均是原 admission 中的合法失败，而不是应删除的低质样本。
在失败样本中花费更多不能证明这些计算全部无用，也可能反映难度和必要恢复。

Phase I 同 task/Planner/network 的各方法对 B0 共每benchmark48个 contrasts。
双方score1的 LongBench/MultiHop/Video 分别18/22/43对；Manager turns 较B0
更少/相同/更多分别7/3/8、7/5/10、14/6/23。
这些 pairs 共享任务且共享B0基线，不能作为独立重复来计算显著性。
summary 同时保留非双方成功的 contrasts，避免成功筛选替代完整质量总体。

两个重要历史反例仅引用既有审阅结论，不从 private gold 制作未来 Agent 规则：

- [minimal replanning](minimal-replanning-v1-audit.md)：补充四个retrieval和两个
  evidence-note节点后，原失败案例恢复score1；已完成prefix不重跑。
  说明更多 retrieval/inference 可能是修复信息缺口的必要工作。
- [A/C final](cost-guidance-final-results-v1.md) 和
  [B/D/E](cost-guidance-bde-results-v1.md)：MultiHop 的较低 movement 可以同时伴随
  已取回证据未进入终端输入和score0；不能把减小输入或去掉分支作为通用安全规则。
  [budget diagnostic](blind-budget-diagnostic-v1-report.md) 的Video2→7→8次推理
  都未终止，显示 over-expansion，但没有评估质量，因此不足以证明可安全删哪一次。

## R4：基础设施依赖和研究决策

所有自动候选的 infra 标签保留 Unknown。Generic exact memoization 若有证明，原则上
属于 infrastructure-independent；它的收益大小仍可随 placement 和网络变化。
全局等价 retrieval pushdown/reuse 的传输净收益可能 infrastructure-conditioned，
必须扣除分布式stats、局部计算、合并和额外消息；相同Physical Scheduler作为基线。
只改变placement而现有Scheduler已能实现的机会不得归功于新的logical optimizer。
同任务Fast/Slow中的5,204,596B footprint是payload观察，不是带宽因果效应。
历史没有动态model join/leave的已验证实验事件；这里只允许提出后续假设。

最终决策（Q1–Q8）：

1. **Q1，成本来源。** 已测控制work主要来自Manager，C/D的额外交互和LongBench
   20-turn exhaustion突出；昂贵physical inference既有Video，也有MultiHop evidence
   reasoning。当前Phase II子集cell16全run model-service subtotal为1,283.773s，
   Phase I cell84/Video/P2/C为898.705s。美元/GPU排名未知。
2. **Q2，exact规模。** 0个已证实Exact；真实exact机会和净收益unknown，不能填零。
3. **Q3，必要工作。** 证据覆盖修复、context合法恢复、Verifier发现约束和prompt-carried
   信息都可能必要；历史的增量replanning恢复与证据遗漏失败反对盲目少调用。
4. **Q4，必须replay。** 所有Planner turn压缩、model skip/merge、specialist collapse、
   lossy evidence reduction，及operator exact替换对后续Agent决策的影响都需Level2。
5. **Q5，infra候选。** 最明确的待验证方向是保持全局retrieval语义的数据移动改写，
   其次是同device争用下的推理安排；后者须先与现有scheduler比较。
   join/leave只有理论相关性，尚无历史验证。
6. **Q6，若只选择一种最小机制。** 优先验证同一decision内Quote/Commit交互压缩，
   保留同样的cost feedback、合法动作检查和预算定义；不增加独立optimizer模型调用。
   理由是472个真实control-only batches，机会比当前未检出的exact memoization更具体。
   每次成功压缩最多可能避免一个相关云reasoning交互，但token/API和净收益仍未知；
   风险是减少语义思考机会、改变Verifier时机或吞掉合法恢复。先做failure/success配对
   pilot，若状态/反馈无法等价保留则停止，不把压缩机制当作已验证方法。
7. **Q7，runtime分叉。** 当前没有公开的完整checkpoint/fork/restore入口；详见协议。
   trace输入和graph足以定位边界，不足以恢复SDK及应用/Worker完整状态。
8. **Q8，下一阶段投入。** 有理由做小规模、另行授权的机制pilot；没有理由启动新matrix
   或恢复Phase II。先补最小quiescent checkpoint，再做协议的C成功/失败两点和B昂贵
   成功/错误两点；8点完整候选覆盖更多风险。若自然续跑的recovery吞掉收益或质量下降，
   转向semantic decision policy / conditional computation，而非扩大独立Optimizer。

证据等级：成本receipts和计数为已实测；成本/quality差异仅为相关性；exact算子替换
可在完整contract下形式化证明但此处未获历史闭包；TSR影响需受控实验；完整Phase II
成本、正净收益和动态infra效果目前无法判断。
