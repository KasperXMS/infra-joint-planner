# Lightweight Planner Compatibility Audit v1

**决定：NO-GO。** 8B 的小输入 SDK-native 协议链路可运行，但本地 provider 会静默截断
超限上下文，现有 Manager 路径没有经验证的 fail-closed 防护。因此正式 benchmark 未执行。
这不是“8B 不能使用 tools”或“8B benchmark competence 为零”的结论。

证据来自 2026-10-11 controller 的既有 Ollama 服务。raw synthetic 请求、响应、服务日志
只在 `/home/super/xiaoming/lightweight-planner-competence-v1`；提交的 metadata 不含凭据、
benchmark 输入或 gold。远端 SDK：openai-agents 0.20.0、openai 2.54.0、httpx 0.28.1。

## 部署与接口

复用 `qwen-vl8b-resident-32k-v1`，Qwen3-VL 8B Instruct、8.8B、Q4_K_M、GPU1。
digest `8af2c13de2205715e2088787387b9a7d29d63f4c628a270ea66d56c41a7c4936`；
capabilities 为 completion / vision / tools。`/api/ps` 报告 context_length=32768；
权重 architecture 的 context_length=262144 不能替代部署 attestation。
B1/B2 固定同权重、template、sampling、tool schema 和 output reservation。

## 有界测试及保留记录

| Evidence | 本地请求 | 结果 | 解释 |
|---|---:|---|---|
| `gate-001` | 3 | `UserError`，final=null | synthetic Gateway 错把 model action 当作带 `.operator` 的 tool action |
| `gate-002` | 3 | read failure → invoke_model → final `A` | 修复 harness 后真实 SDK 多轮终端链路完成；严格 read-retry 判据未满足 |
| `context-probe-001` | 1 | HTTP 200 + truncation warning | over-limit prompt 被静默截断；context transport 不安全 |

第一次故障属于测试 harness：`LogicalModelAction` 本来就没有 `.operator`。修复仅为
`getattr(action, "operator", "invoke_model")`，不更改 prompt、模型、sampling、schema、
任务或恢复决策。保留两份远端脚本、两份 receipt 和 raw wire；回归覆盖 typed read failure、
第二次读取与 model action。第二次是一次因明确 implementation defect 进行的复验，
不是为取得更好模型结果进行的 semantic retry。

第一次 source SHA：`d6f4b816daa658c63f08e0f5350864f4dd2899f6603014af4fc1b3b7e3594841`；
修复 source SHA：`6c337c319cb3df6c5c32fc503f1121449d5648d84c0154812d3b76197db2e6fc`。
receipts：

- gate-001：`f46bb658cb7a8eb20eecc7da449ad4eb24ef5aea14944b91fd8995eb399fdbd9`。
- gate-002：`77d24ee1fd0e1537ae1c4d4b16061634042b9eb82b5d80eb1edd53f383e7ad6e`。
- context-probe-001：`aa0f5e58f177586e81a01d81e530fae7b14a437045ce1aed27dea73736481c04`。

`passed_native_smoke=false` 保留原值。原 smoke 要求失败后重新读取，但第二次模型选择了
另一项合法工具再返回 `A`。该验收比最小协议兼容性更严格；它既不能证明 provider 不兼容，
也不能单独证明语义能力不足。不能在看到结果后把旧 receipt 改成通过。
即使独立审计接受这一替代链路，下面的 context blocker 仍然成立。

## 上下文探针：实际 blocker

仅一次、最多 1 request / 180 秒 / 1 output token。保留 gate-002 第一个请求的 SDK
function-tool schemas 和消息；追加纯 synthetic `" x" * 40000`，不使用 benchmark 数据。
将 max_tokens 从 2048 改为 1 仅为这一 boundary probe 控制生成量，不是模型调参搜索。
请求 JSON 106,117 bytes；SHA
`8e5a779a76f7d834f97bd97ca72ddb6c0f385206a5cbecc46bc45241d941552d`。

服务日志原文：

```text
msg="truncating input prompt" limit=16386 prompt=42272 keep=4 new=16386
```

HTTP 返回 200，provider usage 的 prompt_tokens=16386、completion_tokens=1。
日志 delta SHA：`176473d6286e38a9da64fcccce6fc5edc13ecd4324540f4529c695208d270553`。
42,272 是服务日志中的截断前 token 数，不是用字符串长度猜出的值。
16,386 是**这次请求**的 truncation limit；不能推断所有请求的有效窗口均为 16K，
也不能把该值当作模型架构窗口。问题是 provider 丢弃输入后仍将响应标为成功。

现有 native Manager 是 persistent conversation，历史消息和合法 tool results 会增长。
native Manager 请求没有对应 physical invoke_model 的 context preflight。初始六任务 Agent
view 仅 624–2,982 UTF-8 bytes，不代表整个后续轨迹都能装入 32K。物理层已有的 preflight
不能自动保护这个新增本地控制面。没有在 Planner 输入中静默截断、摘要或强模型修复来掩盖问题。

## Gate coverage

| 要求 | 已有证据 | 限制 / 状态 |
|---|---|---|
| Native tools / JSON / arguments | 真 SDK 接受 read_artifact 和 invoke_model | 不是全部 12 operators 的模型能力验证 |
| Tool-result serialization / state | gate-002 连续 3 次 HTTP 200，含 typed failure | 仅小 synthetic 输入 |
| Terminal contract | 模型基于 synthetic model result 返回合法 `A` | 无真实 Worker / benchmark evaluator；不记正式 completion |
| Output reservation | SDK wire 的 max_tokens=2048；probe=1 | 小输出未实测到达 2048 上限 |
| Context boundary | 观察到真实 silent truncation | **FAIL，正式 admission 被阻止** |
| Parallel semantics | 原 runtime 并发/依赖回归通过 | live 模型未选择并行；不要求它一定选择并行 |
| Role isolation | facade 路由/计费 ID 回归通过 | 未执行强 Specialist/Verifier live calls；不能声称云端 paired E2E 已验证 |
| Residency | 四节点五实例仍常驻 | Planner 与 physical 8B 共用实例，未测 GPU-seconds / contention 曲线 |

没有要求必须完整 32K stress 或模型主动并行才能过关。阻止正式执行的是观察到的
silently lossy transport，以及尚未闭合的正式预算/启动 admission，而不是这两项未观察行为。

## 最小修复需求与边界

下一步应单独冻结通用 **Manager context preflight**：对最终 serialized messages + tools +
template overhead 做可信 token 核算，保留 output budget；超限在请求前报 typed
`context_limit_exceeded`，不调用 provider、不选择新工具、不截断/摘要/补全计划。
需确定当前 provider 的实际截断/预留规则，而不是只信 tag 中的 `32k`。

进行一次预先冻结的 paired regression：小合法请求 wire、model、tools、observations 与
adapter 前一致；超限 synthetic 请求被本地拒绝，provider request count 为零。
若缺乏可信 tokenizer，可评估经证实安全的保守上界，并披露拒绝范围；不得把一个未验证
heuristic 宣称为精确 context capacity。保护不得修改 physical execution semantics。

本轮未实现/上线该 adapter，也不在 gate 失败后追加搜索。原 18 cells 保持未开始；
后续先关闭 context、角色端到端和预算 admission，再决定是否执行这一已设计的 matrix。
