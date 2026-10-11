# Lightweight Planner Context Gate v1

2026-10-11，分支 `lightweight-planner-competence-v1`。**Context 子项通过，Gate 1 整体仍为 NO-GO：原始 function-call schema 校验失败。** 本轮运行了真实模型测试，18-cell 正式实验执行数为 0；历史 Phase II 保持终止。

## 截断原因与配置

现有 Ollama 0.34.0 的 `qwen-vl8b-resident-32k-v1` 已部署为 32K：`/api/ps.context_length=32768`、resident runner `/props.n_ctx=32768`，进程参数 `-c 32768 -np 1 --context-shift --keep 4`。服务环境为 `OLLAMA_NUM_PARALLEL=1`、`OLLAMA_MAX_LOADED_MODELS=1`、q8_0 KV cache、flash attention，GPU1。server PID 1129016、runner PID 1130540、runner port 43715；收尾时进程命令行保持一致。

旧请求的 42,272 → 16,386 不是部署窗口只有 16K。超过 32K 后，context-shift 路径预留约半个窗口：`32768 - floor((32768 - 4) / 2) = 16386`，与旧服务日志完全对应。另有 chat-history truncation 路径；OpenAI compatibility 转换未提供可靠的 `truncate=false` 请求透传，因此不能仅靠客户端请求参数避免丢失。公式和路径参见 Ollama v0.34.0 的 [llama_server.go](https://raw.githubusercontent.com/ollama/ollama/v0.34.0/llm/llama_server.go)、[prompt.go](https://raw.githubusercontent.com/ollama/ollama/v0.34.0/server/prompt.go)、[openai.go](https://raw.githubusercontent.com/ollama/ollama/v0.34.0/openai/openai.go)。这是版本源码、现场参数和日志的联合判断，未声称已识别二进制的构建 commit。

已有 32K 部署符合本次要求，未创建新 tag、重启服务或修改 Executor。`MAX_LOADED_MODELS=1` 下新增 tag 反而可能替换现有 resident 实例。固定参数：

| 项目 | 值 |
|---|---|
| Model digest | `8af2c13de2205715e2088787387b9a7d29d63f4c628a270ea66d56c41a7c4936` |
| Weight blob | `sha256-1329cd5ab37e5ef6faef37cd8ff8660ffc96ed5b47b34fddf8eb0912e6c82466` |
| Template SHA256 | `b507b9c2f6ca642bffcd06665ea7c91f235fd32daeefdf875a0f938db05fb315` |
| Context / output reservation | 32,768 / 2,048 tokens |
| Effective input budget | 30,720 tokens，包含 messages、tools、template overhead |
| Inference wire | `/v1/chat/completions`，`max_tokens=2048`，非流式 |

tag 的 show 参数为 temperature=1、top_k=20、top_p=0.95；OpenAI adapter 在 wire 未给值时使用自己的默认值，不能把 tag 的 top_p=0.95 宣称为实际 OpenAI 请求采样参数。本轮未修改采样配置。

## Manager preflight

新增 `src/infra_joint/experiments/manager_context.py`，仅在本次隔离的 Manager HTTP client 接入 request/response hooks。通用 runtime、operator registry、Physical Scheduler 和原 Executor app 均未修改。

每次发出最终序列化请求前，校验 resident model digest、context、weight blob、template 和 renderer/parser。将 OpenAI 文本消息按 provider 转换规则送入 native `/api/chat`，使用 **`_debug_render_only=true`、`truncate=false`** 完整渲染，再调用同一 resident runner 的 `/tokenize` 精确计数。检查 `prompt_tokens + 2048 <= 32768`。超限抛出 `context_limit_exceeded`；无法证明计数、出现不支持的字段/模态或 residency 漂移时拒绝请求。

合法 inference wire 原样发送；不摘要、不删消息、不改工具参数。响应 usage 必须与 preflight 完整计数一致，并重新校验 residency，否则响应不会交给 SDK。此实现依赖已核验的 provider debug-render 接口和 pinned runner；不声称支持其他 Ollama 版本、流式或图像 Manager 输入。它没有部署到所有生产 Manager 客户端。

## 实测

运行前冻结 protocol、Skills hash、原源码副本和有限请求预算。以下数字是包含全部 schema/template 的 prompt token 数；所有请求均预留 2,048 输出。

| 输入 tokens | Provider prompt tokens | 首/中/尾 sentinel | Inference 次数 | 结果 |
|---:|---:|---|---:|---|
| 8,192 | 8,192 | 全部正确 | 1 | PASS |
| 16,384 | 16,384 | 全部正确 | 1 | PASS |
| 24,576 | 24,576 | 全部正确 | 1 | PASS |
| 30,720 | 30,720 | 全部正确 | 1 | PASS |
| 30,721 | 未发送 | 不适用 | 0 | 明确拒绝 |
| 42,272 | 未发送 | 不适用 | 0 | 明确拒绝 |

另有一次 8K 无 guard 对照；与启用 guard 的请求字节完全一致。七个获准请求（四档容量 + 三轮 SDK）的 provider prompt usage 均匹配 preflight，日志没有实际 truncation/context-shift 事件。

真实 SDK（openai-agents 0.20.0）三轮完成 `read_artifact` typed failure → `invoke_model` → final `A`，但不能据此认定 schema 合格。对原始模型响应重新按实际请求 schema 校验：

| Tool | 原始 JSON schema 校验 | 原因 |
|---|---|---|
| `read_artifact` | FAIL | 缺少 required `arguments` 字段 |
| `invoke_model` | PASS | 满足请求 schema |

现有 native runtime 使用 `payload.get("arguments", {})`，掩盖了第一条响应的 wire schema 问题。本轮未修改默认值行为、工具 schema、Skills 或模型输出来制造通过结果。原有严格 read-retry 判据也仍为 false；模型选择了另一工具后结束。新预冻结协议将精确 reread 作为独立诊断，旧判据与旧 receipt 均保留原值。即使接受替代工具链路，原始 schema 失败依然阻止 Gate 1 通过。

Planner 仅使用本地 8B；Specialist/Verifier 分别构造为原 `qwen3.8-max`，Verifier 保持 temperature=0、tool_choice=required。强角色没有被替换、截断或实际调用；云 transport 被显式阻断，attempts=0。因此这里只验证构造隔离，未声称验证强角色 live E2E。

真实 SDK 的独立 scripted HTTP 并发测试达到两项 action 同时执行，2 次 scripted response、0 次真实模型推理；没有要求 live 8B 必须选择并行调用。

## 审计与资源

remote owner：`/home/super/xiaoming/lightweight-planner-competence-v1/context-repair-001`。原始请求、响应、trace、server log delta、执行源码 archive、原始 receipt 保留在 owner；本地只保存 metadata、hash、protocol 和结论。

首次执行的日志分类器把正常 `truncated=0` 误判成 warning。原始 `run-001/receipt.json` 未覆盖，执行 archive 和 source freeze 保留。修复仅用于离线复核，无模型重跑；首次严格 schema auditor 遇到缺字段后异常退出，第二版将错误记录为 blocking 结果。`audited-gate1-002.json` 是当前结论，Gate 1=false。提交中的 runner 同时保留正确日志分类及原始 schema 校验，避免未来漏检；它与首次执行脚本的差异明确记录在 source manifest。

本轮 **9 次真实推理**：4 档容量 + 1 次 paired baseline + 3 次 SDK + 1 次诊断。诊断请求一度误用不带下划线的 debug key，实际生成 24 tokens；该请求计入总数，raw `render-probe.json` 保留。之后使用正确 `_debug_render_only`。Gate run 有 126 次 helper HTTP 请求；诊断阶段 helper 未单独计量，未伪报为零。GPU-seconds、金额均未知。云推理=0、正式 benchmark=0。

controller 原 worker app 的 114 个源码文件 hash、两个 resident model digest 以及 Manager 服务进程保持一致。Jetson 本轮 SSH 收尾读回遭 key-auth 拒绝，metadata 保留错误；不把旧盘点当成本轮 attestation。没有向 Jetson 发起写入或部署动作。

Skills SHA256 仍为 `d8b75f3ce6e76ab19fa16328acc7f4ffce56988ab5d6abd794c95866d9b1f422`；Phase II journal SHA256 仍为 `e8e796e0b9bb2e3ebf1c2492c96138a20e05fca246bcb029c205f799339fa3a9`。benchmark、Skills、Physical Scheduler 和历史结果保持原状。

本地验证：51 项针对 context guard、schema auditor、角色隔离及 native SDK runtime 的测试通过；新 core 的 Pyright 为 0 errors；新增 Python 文件通过 Ruff 检查和格式检查。

当前阻塞转为 **8B 原始工具调用的 schema 合规性**。此次 Gate 检查完成，正式执行权限继续为 false；没有启动 18-cell 或恢复 Phase II。
