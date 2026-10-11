# Lightweight Planner 正式执行准入变更 v2

2026-10-11，基于 `41d034d`，按用户新指示执行原冻结 18-cell 矩阵。此前 Gate 1 的 No-Go、原始日志及报告保持原样。本变更不把历史结果改成通过。

本轮取消模型能力准入：schema 错误、失败恢复、错误答案、合法预算耗尽均为能力评测结果。模型原始 operator/delegation function call 按实际 JSON Schema 严格验证；缺字段不补齐、不执行，返回 `schema_validation_failed`，允许原 turn budget 内恢复。三组相同规则；Verifier 源码、prompt 和 settings 保持原样，通用接入层验证原始 verdict schema。

唯一停止后续 cells 的条件为系统安全或完整性失败：配额失控、静默截断、source/history/evaluator 漂移、数据污染、namespace/进程隔离失败、无法 drain 推理、tc 无法还原、认证失败等。合法 preflight 超限为单 cell 结果；不能据此重跑或换任务。每 cell 一次，无选择性重跑。

原 6 个任务、B0/B1/B2 次序、模型、完整 Skills、语义 prompt、原 evaluator、Physical Scheduler 和 Executor 均冻结。B1/B2 使用同一已验证 32K resident，预留 2,048；请求显式 temperature=1、top_p=.95，与原模型配置一致。Specialist/Verifier 保持强模型。首次三 cells 后检查执行安全，自动继续剩余 15 cells。

实际保护：共享控制 HTTP 配额 72/cell、physical inference 配额 64/cell、context helper 4096/cell、序列化控制输入总量 128 MiB/cell；原 loop budget 不变。请求 180 秒、physical service 1200 秒、执行 3600 秒、cleanup 1260 秒，额外 setup/attestation 上限 240 秒，单 cell 外层 5100 秒、整轮 91800 秒，不自动延长。请求数和 wall-time 是资源上限；强角色不新增 output cap，GPU 价格和 dollar ceiling 为 unknown。已有 provider usage 和冻结价卡用于成本统计，不冒充实际账单。

新 owner：`/home/super/xiaoming/lightweight-planner-competence-v1/formal-pilot-003`。独立 Worker 端口 62004/62005/62028/62112；每 cell 四节点独立新 artifact stores。复用原 Worker app，不改 resident 部署。每 cell 结束检查 Worker in-flight 与五个 resident runner `/slots` 均 idle，之后仅终止该 cell 新建的 Worker PID；验证进程退出并还原 tc。原始敏感数据仅保留在实验机。

STOP 文件和 SIGTERM/SIGINT 停止后续请求与 cells，并进入 cleanup。固定矩阵不后台扩展、不恢复历史 Phase II。Focused regression：59 项通过，相关 core Pyright 为 0 errors，新增代码 Ruff 通过；无额外模型能力探针。

启动修正单独保留：`formal-pilot-001` 误选旧 Worker app，在 task.start 前发生 surface mismatch，两次初始化的模型请求均为 0；`formal-pilot-002` 在 Worker 启动前因控制机逐条 sudo 的 DNS 延迟触发 tc 配置超时，模型请求也为 0。两个 namespace 和停止证据均保留，网络配置已还原，不计入能力结果。正式 owner 使用已有 `app-input-cardinality-repair-003`，不修改 Executor；相同冻结 tc 命令以一次获授权的 `sudo tc -batch -` 执行。只有 task.start 前且零模型请求的初始化故障可作此修正，模型开始后的能力结果不得选择性重跑。

正式 LPC-01 的原始执行已完成且 benchmark_score=0，汇总器误读 `score` 引发 KeyError 后停止。修复仅替换两个后处理字段访问；保留原始结果、原始 source freeze 和停止记录，追加 source amendment 后从 LPC-02 继续。LPC-01 不重跑、不剔除、不改分，Evaluator 无修改；继续脚本在执行下一 cell 前验证上述边界。
