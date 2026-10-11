# Lightweight Planner Competence Pilot 正式结果

2026-10-11，原冻结的 6 个任务 × B0/B1/B2 共 **18 cells 已完成**。每 cell 保留一次实际任务执行，没有因低分、非法调用或预算耗尽选择性重跑。历史 Gate No-Go 保留；本轮依据独立准入变更直接评测，没有新增能力探针。实验已停止，不启动下一阶段或历史 Phase II。

完整的逐 cell、逐角色资源账与同任务三组 workflow 对照见 [详细报告](../analysis/lightweight-planner-formal-pilot-v1/report.md)；机器可读数据和原始证据 SHA-256 索引见 [pilot-results.json](../analysis/lightweight-planner-formal-pilot-v1/pilot-results.json)。原始 traces、API payload、artifact、evaluator 私有数据和服务日志仍保留在实验机器。

| Group | Completion | TSR | Raw-call schema failures | 已知 Cloud API USD |
|---|---:|---:|---:|---:|
| B0：强 Manager，无 Skills | 6/6 | 4/6 | 0 | 0.677008 |
| B1：本地 8B，无 Skills | 1/6 | 1/6 | 40 | 0.585375 |
| B2：同一 8B，Frozen Skills | 0/6 | 0/6 | 20 | 0.147515 |

Completion 要求合法 terminal；TSR 要求同时完成且原 evaluator score=1。失败而未评估的 score 保持 unknown，不改写为 evaluator score0。B0 的两个错误答案照常计入分母。

B1 的失败为两次 turn budget 耗尽、两次 provider JSON parse error、一次 terminal contract failure。B2 为五次 provider JSON parse error、一次 turn budget 耗尽。Provider parse error 独立计数，不能冒充 callback 已收到且完成 JSON Schema 验证的调用，也不能仅凭 HTTP 错误确定责任在模型或 parser。B1 的视频任务 `131-3` 在一次 schema failure 后恢复并成功，说明严格拒绝非法调用仍允许原预算内恢复。

| 资源，六任务合计 | B0 | B1 | B2 |
|---|---:|---:|---:|
| Manager / Specialist / Verifier turns | 29 / 2 / 29 | 60 / 19 / 57 | 27 / 8 / 22 |
| 成功 physical inference calls | 6 | 2 | 0 |
| 已知 physical model-service 秒 | 369.996 | 13.939 | 0 |
| 五个 resident 的报告 service 秒，含本地 Planner | 364.487 | 132.249 | 38.797 |
| Task E2E 秒合计 | 700.599 | 464.818 | 160.676 |
| Initial artifact bytes | 238,804,668 | 238,804,668 | 238,804,668 |
| Action artifact transfer bytes | 10,626,750 | 10,409,192 | 5,204,596 |

整个正式矩阵 wall time 为 **2,915.404 秒**，含 setup、cleanup 和已记录的修复停顿；不是上述 task E2E 的简单相加。Service 时间之间存在重叠，runner timing 也不包含所有 vision/CPU/网络工作，不能当作 GPU busy time。Resident starts 与本地 Planner 请求及成功 physical calls 一致：B0 6=0+6，B1 62=60+2，B2 27=27+0。

逐角色完整 tokens、已知 token subtotal、缺失 usage 的请求数和缓存计数见详细报告。七次本地 provider parse error 缺少 provider usage，完整 token 总量保留 unknown；没有填零。本地 Planner、Executor 的 GPU 价格、能耗及完整货币成本均为 unknown，Cloud USD 使用冻结价卡与 FX 估算，不是实际账单。

行为上，B0 六次都走到 Manager-owned synthesis；两项 MultiHop-RAG 采用 retrieval/aggregation，LongBench 会在 physical context rejection 后继续调整，视频任务采用 frame sampling。B1 的 MultiHop 两次都委托强 Specialist，但 Manager 重复缺少必填 `arguments`，最终耗尽预算；视频第一项增加了 Specialist/contact sheet 等步骤，仍未满足 terminal contract，第二项以短 workflow 成功。B2 四项在建立 graph node 前失败，第二项 MultiHop 有 Specialist 子图但未完成；最后一项视频完成 sampling 后仍失败。Graph edge 按 artifact 记录，不等于独立 action 数或冗余工作量。

**B1 vs B2：本 pilot 没有观察到 Skills 的质量收益。** Completion 和 TSR 都从 1/6 到 0/6；schema failure 数减少伴随更多早期 provider parse failures，不能据此宣称工具能力或效率改善。**B0 vs B2：TSR 从 4/6 到 0/6。** B2 的较低 Cloud API、physical work 和 E2E 主要伴随未完成任务，不能作为成功任务的成本优势；完整资源货币成本也没有被识别。

**Infra-aware Workflow Adapter：No-Go。** 当前主导问题是 Planner stack 的协议可靠性与完成能力，尚无证据表明基础设施适配能解决这些失败。该判断是在跑完 18 cells 后作出的描述性分析，不新增准入 Gate。六个已被研究者查看过的任务、每组每任务一次执行，不能支持显著性、non-inferiority、held-out 泛化或 Skills 必然无效的结论。

[最终完整性记录](../analysis/lightweight-planner-formal-pilot-v1/final-integrity.json)确认：所有 Worker drain 并退出、source 与历史/Skills 未漂移、无静默截断或其它未解决的系统问题。87 次本地 Manager 请求均通过 context preflight，其中 80 次 HTTP 200 的 prompt usage 完整性检查通过，7 次 provider error 保留 unknown usage；没有 Manager context overflow。Physical 工具的合法 context rejection 保留在 trace 中。

启动和汇总修正单独保留：两轮零模型初始化、首个 B0 score0 的后处理字段修正，以及第 15 个 cell 的零模型 Worker bind 修正；没有重新执行已产生的模型结果。具体边界见 [准入与修正记录](lightweight-planner-pilot-admission-v2.md)。验证为 59 项 focused pytest、相关 core Pyright 0 errors，加一项零模型 Linux TCP TIME_WAIT regression。Frozen Skills、语义 prompts、Benchmark、Evaluator、Physical Scheduler 和 Executor 未修改。
