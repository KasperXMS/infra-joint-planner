# Lightweight Planner + Fixed Skills Competence Pilot v1

2026-10-11；分支 `lightweight-planner-competence-v1`；基线提交
`5474d67ba8aec7e501f1db4610cb57bc5340fdef`。

**当前决定：NO-GO / Gate 1。正式执行 0/18，未启动正式 Worker 或网络整形。**
本协议冻结后续比较设计，不代表已完成正式运行的 readiness。单次上下文探针证实
本地 Manager 服务静默截断超限输入；尚无经验证的 Manager fail-closed context
preflight。原始证据保留，不以 compatibility failure 推断 benchmark competence。

机器可读配置：[lightweight-planner-competence-v1.json](../configs/experiments/lightweight-planner-competence-v1.json)。
本轮仅实施 SDK synthetic 检查、只读部署审计和角色构造 facade；没有正式执行入口。
配置中的 `formal_execution_allowed=false` 与 `execution_entrypoint=null` 必须保留。

## 比较及不变量

| Group | Manager | Skills | Specialist / Verifier |
|---|---|---|---|
| B0 | `qwen3.8-max`，现有阿里云强 Manager | 无 | 原有 `qwen3.8-max` |
| B1 | 本地 `qwen-vl8b-resident-32k-v1` | 无 | 原有 `qwen3.8-max` |
| B2 | 与 B1 完全相同 | 整份 procedural v1 | 原有 `qwen3.8-max` |

强模型 provider 为 Alibaba Cloud Model Studio，endpoint 为
`https://llm-6tbxas81ayf65rd1.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`；
`enable_thinking=false`、provider-default temperature、180 秒 timeout、SDK retries=0。
不更换已选云模型。Specialist 保留原生 bounded instructions、settings 和工具集合。
Verifier 保留原有 blind instructions、temperature=0、required function、每次验证
max_turns=1。Verifier 单独构造，不经过 Manager 模型替换。

审计发现 `OpenAIAgentsNativeRuntime._agent()` 原本对 Manager 和
`bounded_specialist` 都使用 `self._model`。因此不能直接替换全局 SDK model。
[角色 facade](../scripts/lightweight_planner_roles_v1.py) 仅在 SDK Agent 构造时按名称
选择 model；其余 SDK 对象保持原对象，包括 Runner。Manager 与 Specialist 分别
用对应 provider 的 meter，并记录真实 requested model ID。旧 `metered_sdk()` 会把
Specialist requested ID 也写成 Manager ID，不能直接用于两种模型的比较。

全部组保留现有 persistent SDK-native loop、blind profile visibility、12 个 operators、
ActionGateway、Scheduler、Executor、Worker API、artifact semantics、五个物理 deployments、
原始 evaluator 和 terminal contract。没有预定义 DAG、固定 Agent 数量、workflow adapter、
隐藏强模型修复、cost guidance、RL、skill retrieval、model join/leave。

## 本地 Manager 与硬件

候选是在 controller strong-4090 GPU1 已常驻的 Qwen3-VL 8B Instruct，实际参数数
8,767,123,696（8.8B）、GGUF Q4_K_M；不是另一个已安装的 Thinking tag。

- endpoint：`http://127.0.0.1:11437/v1`；Ollama 0.34.0。
- digest：`8af2c13de2205715e2088787387b9a7d29d63f4c628a270ea66d56c41a7c4936`。
- template SHA：`b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315`。
- 部署 context=32,768；架构元数据的 262,144 不是实际可用部署窗口。
- B1/B2 同为 temperature=1、top_k=20、top_p=.95、不覆盖 seed；Manager
  `max_tokens=2048`、parallel_tool_calls=true、timeout=180 秒、retries=0。
- 服务报告 size_vram=7,962,330,398 bytes；GPU1 总占用 10,538 MiB 是设备整体读数，
  不能全部归入 Planner。GPU0 总占用 20,146 MiB。快照时两卡利用率均为 0%。

本次发现的既有 8B 实例中，没有独立 Planner 实例；A5 和 controller 上的 8B 都属于既有物理池。
选定 controller 实例，避免改变模型池。它同时承担 physical executor，不能宣称资源隔离。
全部组应保持五模型常驻；B1/B2 增加 GPU1 请求，须分别记录排队、推理延迟和与执行器
重叠的时间区间。没有可靠测量的 GPU-seconds、电力和 GPU 货币成本保持 null。
没有下载、训练、重新部署或终止 resident 服务。

## 固定 Skills

[planner-procedural-v1.md](../configs/skills/planner-procedural-v1.md)，1,555 UTF-8 bytes；
SHA-256：`d8b75f3ce6e76ab19fa16328acc7f4ffce56988ab5d6abd794c95866d9b1f422`。

B2 将整份文件以两个 LF 追加到原 Manager instructions 后，不选择片段、不匹配任务类别。
B0/B1 保留原基础 instructions 的完整字符串。Specialist 与 Verifier 不收到 skills。
四类内容仅为 task decomposition、evidence management、tool/context discipline、typed
feedback/recovery；不含 task ID、gold、topology、routing、模型调用序列或资源优化 policy。
正式结果后不得修改；本轮没有 B2 live inference。Skills 增量进入 Manager provider input
usage；字节数不是 token 数，准确增量须用固定 tokenizer/paired request 核算，不填零。

## 六个任务与执行顺序

选择原 freeze 的各 family 第 1、2 项，不按本轮答案或成绩筛选。它们曾被研究者分析过，
是既有任务上的 feasibility screening，不是新 held-out generalization test。

| Index | Family / position | 原 source task ID | Group 顺序 |
|---|---|---|---|
| 1 | MultiHop-RAG / 1 | `multihop-rag-train-4b6de4acbde051fee1f727f3` | B0, B1, B2 |
| 2 | MultiHop-RAG / 2 | `multihop-rag-train-fe71f374676e35359d12c83e` | B1, B2, B0 |
| 3 | LongBench-v2 / 1 | `66f2c44e821e116aacb2b826` | B2, B0, B1 |
| 4 | LongBench-v2 / 2 | `66f94f9ebb02136c067c4fde` | B0, B2, B1 |
| 5 | Video-MME / 1 | `602-2` | B2, B1, B0 |
| 6 | Video-MME / 2 | `131-3` | B1, B0, B2 |

每组在第一/第二/第三位置各出现两次。该顺序不能消除所有 cache 效应，特别是 synthetic
探针已经改变了模型 KV cache；必须记录每个 cell 的 residency/cached tokens。

原 freeze：`/home/super/xiaoming/large-scale-cost-guidance-v1/preparation/task-freeze-002`；
manifest SHA：`25e65b22b452bc164efe61ad895d20e5fcf3c8d407e4e9c7380a204bbec9b3ad`。
六个任务均在远端通过 `frozen_task()` 重新核验原 public bundle、Agent view、prepared
bytes、private evaluator 与 evaluator implementation。逐任务 bundle / Agent view 哈希
见配置和 [metadata](../analysis/lightweight-planner-competence-v1/remote-metadata-001.json)。
私有输入、gold、模型请求正文和答案不下载到 PC。

## 固定环境与源码

后续只用原 fast regime：100 Mbps、added RTT 5 ms；无 Slow 条件，无 join/leave。
本轮没有应用该 regime，不能把 gate 的 loopback latency 当成正式 Fast cell latency。
正式运行前须对四节点执行 tc before/apply/after attestation 与还原验证。
每 cell 使用独立空 artifact stores，原始 initial placement 不变；空 stores 不代表模型冷启动。

原物理池：A4 4B、A5 8B、A28 27B、controller GPU0 27B / GPU1 8B，均为原有
Q4_K_M、32K / reserved output 2048 / image token cost 4096。
源码 inventory 覆盖四个原 Worker app 各 114 个 Python 源文件；这是只读 source inventory，
尚不是新正式 Worker 启动/配置 admission。

关键 frozen source：native runtime `81d9e80233f24ccbf115999799e438a52d3151e119f67f7e8e95d7ddc6b66af8`；
Verifier `6c7813735ceec02136008d74da99ae3e773ec93b95b5a50d8a8dd1fd992699e8`；
其余 component hashes 见配置、[source inventory](../analysis/lightweight-planner-competence-v1/source-and-residency-001.json)
与本轮 `source-freeze-v1.json`。原执行组件没有修改。

## 预算与停止规则

| 范围 | 上限 / 状态 |
|---|---|
| 正式 nominal cells | 18；每 cell 一次；无 semantic retry / repetitions / task replacement |
| Manager / Specialist turns | 20 / 每个 8 |
| Physical actions / created specialists / active specialists | 64 / 4 / 2 |
| Verifier calls | 20 |
| 计划 control HTTP requests | 每 cell 72（20 + 4×8 + 20），无 API retry |
| Physical model requests | 每 cell 最多 64，属于原 physical action 总预算 |
| 计划 task deadline / cleanup allowance | 每 cell 3600 / 1260 秒 |
| 计划整轮 task / cleanup ceiling | 64800 / 22680 秒；不可后台自动扩展 |
| 已执行 synthetic budget | 两次 native smoke，各最多 8 requests / 600 秒；一次 context probe，1 request / 180 秒 |
| 本轮实际消耗 | 7 次本地请求；0 cloud requests；0 正式 cells；不再追加 live calls |

正式 administrative ceilings 是设计，**本轮没有实现或启用相应正式 dispatch guard**。
强 Specialist/Verifier 保留原 settings，没有擅自增加 output cap；可信全角色 token/货币
上限、timeout 后远端 in-flight inference 的处理、总请求 quota 原子性，仍需在启动前验证。
没有可声称的 dollar ceiling。无法证实受控上限时不允许正式执行。

现有 Phase II 保持用户终止状态；journal SHA 仍为
`e8e796e0b9bb2e3ebf1c2492c96138a20e05fca246bcb029c205f799339fa3a9`。
新证据仅写入 `/home/super/xiaoming/lightweight-planner-competence-v1`，不调用旧 queue。

遇到 provider/schema incompatibility、context 静默截断、source/evaluator drift、artifact
污染、网络 regime 失效、预算或任务状态不可信，停止 dispatch 并保留原记录。
本轮不允许补跑正式 cells。未来若确认独立 operational confounder，先冻结独立 replacement
规则和新证据目录，再讨论补做；错误答案、非法规划和预算耗尽不属于补做理由。

## 指标、归因与 admission

正式 cell 保存 config/manifest/source hashes、result、原 evaluator、JSONL trace、raw provider
usage、physical telemetry、Worker/cleanup、tc/residency 与 admission；任一失败不能覆盖。
每个 family 分别报告 completion、evaluated accuracy、E2E success；不能直接混合原评分。

- Completion：预注册任务中达到合法 terminal 的比例。
- Evaluated accuracy：已到原 evaluator 的任务中原 score=1 的比例，分母单列。
- E2E TSR：预注册任务中合法完成且原 score=1 的比例。已尝试但未完成者可记未成功，
  original score 仍为 null；本轮全未开始，因此不存在实测 TSR，不填 0%。
- Competence：合法 tool calls / 尝试数、schema/argument/context/dependency failures、recovery、
  Manager turns、Verifier/Specialist calls、completion。
- 控制面：按 Manager / Specialist / Verifier 分开 raw input/output/cached tokens、requests、
  latency、provider usage / pricing completeness。SDK 缺失字段为 null，不冒充账单。
- 物理面：prepared / success / rejected model actions、tokens、service time、deployment identity、
  context/preflight failures；GPU 可用性及 Planner/Executor 时间重叠单列。
- 总资源：API 货币、local Planner compute、physical inference、operator work、artifact movement、
  E2E wall、initial materialization、初始化/常驻容量，保持各自单位；不把秒、GPU-seconds、
  bytes 直接相加。未知 GPU 货币成本为 null。

从 ExecutionGrownGraph / trace 提取 nodes/edges、owners、tool/model 序列、并行区间、
information objects/handoffs、重复 retrieval、context recovery、evidence processing 和 terminal
synthesis。图小不自动等于好；无显式 artifact edge 不代表 prompt/context 中没用证据。
只在同任务 B1 vs B2 分析 Skills effect；B0 vs B2 同时改变模型与 Skills。
最多 18 cells / n=1，不声明显著优越或 non-inferiority，更不归因于未加入的 Infra Adapter。
