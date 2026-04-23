# AIMiner Improvement Plan

本计划基于 4 个 `gpt-5.4 xhigh` 子代理对后端/API、Agent/核心计算、前端/TUI、测试/CI/部署/文档的只读 review 汇总而成。安全性问题已明确排除，不纳入本计划。

## 目标

- 修复会影响研究结果真实性的问题。
- 修复会导致运行资源泄漏、历史覆盖、状态不一致的问题。
- 收敛运行目录、测试矩阵、部署默认行为。
- 改善 Web/TUI 的可用性与状态一致性。

## 本轮落地状态

本轮已按分工调用 5 个 `gpt-5.4 xhigh` 子代理并行修复，主线程补齐了遗漏的 Rank IC、SummaryAgent 图表链路和 API 重启回归测试。当前状态如下：

- Agent A：已修复 EvalAgent/workflow/sub_agent 的真实回测保护、最佳因子快照、IC 方向、plot_paths 传递、策略阶段失败隔离。
- Agent B：已修复 strategy/cache/manager/local_data 的 run-scoped 策略持久化、cache key、权重上限、rebalance mask、负 IC 反向交易、策略后去相关、并行全局超时、本地 panel 多文件语义。
- Agent C：已修复 API manifest 原子写入、shutdown 清理、活跃 PID 探测、stop/delete/status/list 状态一致性、请求模型校验、stale starting 恢复、分页 envelope。
- Agent D：已修复 WebSocket token、Run Detail socket 状态、前端 Stop 按钮状态、历史详情 stale data、Wiki dirty guard/GFM/wikilink、TUI subprocess/editor/stop/quit 可用性。
- Agent E：已修复 Compose profile、reset runs scope、pytest marker/CI matrix、packaging test gate、Docker build context、相关文档同步。
- 主线程补丁：`RiceQuantEval` 现在按日期计算横截面 Spearman Rank IC；`SummaryAgent`/`main.py`/`manager.py`/`core/wiki.py`/`tui.py` 已继续收敛 runtime path；新增 API 重启后 active run 删除/计数/filter 回归测试。

已通过验证：

- `pytest -q tests/unit`：102 passed
- `pytest -q tests/test_summary_agent.py tests/integration/test_manual_strategy_runner.py`：3 passed
- `pytest -q tests/unit/test_api_contract.py`：24 passed
- `cd frontend && npm run build`：通过，保留 Monaco 大 chunk 警告
- `python -m py_compile ...`：核心 Python 文件通过
- `git diff --check ...`：通过
- `docker compose config --services`：默认仅 `api`
- `docker compose --profile research --profile tui config --services`：`api/tui/worker`
- `bash -n start_web.sh`：通过

仍需在真实环境验证：

- Web/TUI 真实启动后端后，执行 start/stop/delete run 与日志 WebSocket 实时流。
- Supervisor 若直接 `SIGKILL` uvicorn，FastAPI shutdown hook 仍无法执行；需要由进程管理器提供 graceful timeout。
- Monaco Editor 引入后仍有较大 chunk，当前只是构建警告，后续可做按语言裁剪或更细粒度 code splitting。

## P0：结果正确性与运行稳定性

### P0-1 本地/QLib 后端不得被 robustness 失败降级为模拟结果

涉及文件：

- `agents/eval_agent.py`
- `core/alphaeval/local_eval.py`
- `core/alphaeval/rq_eval.py`
- `core/alphaeval/modeltester.py`

问题：

- `EvalAgent` 对所有 evaluator 无条件调用 `run_robustness_test()`。
- `LocalDataEval` 继承到的 robustness 路径会强行创建 `RiceQuantEval`。
- 主回测成功后，robustness 失败会让真实结果进入异常分支并返回随机模拟指标。

改进：

- 主回测异常与 robustness 异常分开处理。
- 非 RiceQuant 后端没有可用 robustness 时返回 `rre=None`，不得覆盖真实主回测结果。
- 增加 local/qlib 后端“不应模拟化”的回归测试。

落地状态：

- `agents/eval_agent.py` 已保留主回测 metrics/returns/plot_paths，robustness 失败只记录 `robustness_error`。
- `tests/unit/test_agent_workflow_regressions.py` 已覆盖 robustness 失败不模拟化。

### P0-2 多轮迭代必须返回最佳完整因子，而不是最后一轮

涉及文件：

- `app_workflow/state.py`
- `app_workflow/graph.py`
- `agents/eval_agent.py`
- `sub_agent.py`

问题：

- `best_ic`/`best_code_expression` 只用于早停。
- `AlphaResearcher.run()` 仍返回 `final_state` 的最后一轮字段。
- `increment_iteration` 会清掉上一轮输出，最佳因子可能丢失。

改进：

- 在 workflow state 中维护 `best_factor_snapshot`。
- snapshot 包含 hypothesis/code/metrics/returns/plot_paths/strategy 语义字段。
- `AlphaResearcher.run()` 返回最佳快照。
- 增加多轮返回最佳的回归测试。

落地状态：

- `app_workflow/state.py`、`app_workflow/graph.py` 已加入 `best_factor_snapshot` 和 `best_ic_abs`。
- `sub_agent.py` 已优先返回最佳快照而不是最后状态。
- 回归测试已覆盖多轮最佳因子返回。

### P0-3 Web/API 退出必须清理 Swarm 子进程

涉及文件：

- `api.py`
- `start_web.sh`

问题：

- API 只注册 startup，没有 shutdown 清理。
- Swarm worker 是 `daemon=False`，关闭 Web 后可能继续写 DB/log。
- `start_web.sh` 只 kill 直接记录的后端/前端 PID。

改进：

- FastAPI shutdown 时遍历 active run，调用 `_stop_process_tree()`。
- `start_web.sh` 使用进程组清理，避免只杀 uvicorn 父进程。
- 增加 shutdown 清理行为的最小测试或可观测日志。

落地状态：

- `api.py` 已增加 shutdown hook，退出时把 active run 写为 `stopping -> stopped` 并清理进程树。
- `start_web.sh` 已增加 graceful shutdown 宽限。
- `tests/unit/test_api_contract.py` 已覆盖 shutdown 清理。

### P0-4 策略持久化不能跨 run 覆盖历史结果

涉及文件：

- `core/manual_runner.py`
- `core/strategy.py`
- `manager.py`

问题：

- `strategy_id` 不包含 `run_id/source_factor_id/candidate_rank`。
- `strategy_backtests.strategy_id` 是主键，并使用 `INSERT OR REPLACE`。
- 同表达式/配置在新 run 中复用会覆盖旧 run 的策略行。

改进：

- 区分 cache key 与 run-scoped 持久化 ID。
- Swarm 派生策略使用 run-scoped strategy id 或复合唯一键。
- 手工策略回测仍可保持缓存语义，但不得覆盖 Swarm 历史。
- 增加跨 run 策略不覆盖的回归测试。

落地状态：

- `core/manual_runner.py` 已拆分 `strategy_cache_*` 与 run-scoped `strategy_*`。
- `core/strategy.py` 已增加 `cache_key` 列和索引。
- `manager.py` 已规范化 Swarm 策略结果为 run-scoped `strategy_id`。

### P0-5 Compose 默认不得循环运行有限挖掘任务

涉及文件：

- `docker-compose.yml`
- `Dockerfile`
- `README.md`

问题：

- `docker compose up -d` 默认执行有限运行任务。
- 配合 `restart: unless-stopped` 会反复运行并写产物。

改进：

- Compose 默认启动 API 服务。
- 研究 worker/TUI 放入 profile 或使用 `docker compose run --rm`。
- 有限任务不配置 restart。

Agent E 落地状态：

- `api` 是唯一默认 Compose 服务。
- `worker` 放入 `research` profile，默认 `AIMINER_ITERATIONS=5` 且 `restart: "no"`。
- `tui` 放入 `tui` profile，使用交互式 run 启动且 `restart: "no"`。

## P1：核心计算正确性

### P1-1 并行 Agent 必须有全局超时

涉及文件：

- `manager.py`

改进：

- 不依赖 `future.result(timeout=...)`。
- 使用 `as_completed(..., timeout=...)` 或 `wait(..., timeout=...)` 和全局 deadline。
- 超时后取消未完成任务并记录跳过 agent。

落地状态：

- `manager.py` 已加入 `swarm_global_timeout`，并对 pending agent 做 best-effort cancel/terminate。

### P1-2 RiceQuant Rank IC 不应恒为 0

涉及文件：

- `core/alphaeval/rq_eval.py`
- `agents/eval_agent.py`

改进：

- 在 RiceQuant evaluator 中按日期计算 rank correlation。
- 覆盖全 NaN、小截面、单日样本不足情况。
- 增加 rank IC 非零测试。

落地状态：

- `core/alphaeval/rq_eval.py` 已按日期计算横截面 Spearman Rank IC。
- `tests/unit/test_rq_eval_metrics.py` 已覆盖正/负 Rank IC。

### P1-3 策略阶段失败不得丢弃已通过的因子

涉及文件：

- `app_workflow/graph.py`
- `sub_agent.py`
- `manager.py`

改进：

- 策略阶段异常写入 `strategy_failure_reason`。
- 保留 factor 主链结果，不设置顶层 fatal `error`。

落地状态：

- workflow/sub_agent/manager 已把策略阶段失败降级为因子附加信息，保留通过评估的 factor 结果。

### P1-4 策略权重上限与 rebalance 语义修复

涉及文件：

- `core/strategy.py`
- `tests/`

改进：

- `_normalize_positions` 同时满足 gross exposure 与 `max_weight_per_position`。
- `_rebalance_mask` 使用相邻行 period 比较，而不是移动 period 值。
- 增加 daily/weekly/monthly rebalance 和单票权重上限测试。

落地状态：

- `core/strategy.py` 已修复 clip 后二次归一化导致的单票权重超限。
- weekly/monthly rebalance mask 已按相邻 period 变化触发。

### P1-5 backtest cache key 必须包含全部影响结果的参数

涉及文件：

- `core/manual_runner.py`

改进：

- 手工因子 cache key 增加 `market_mode`、`market_profiles`、`local_data_layout`、`run_robustness`。
- 策略 cache key 增加 `market_profiles`、`local_data_layout`。
- 保持旧 job 可读取，但新 job key 不再冲突。

落地状态：

- `core/manual_runner.py` 已补齐 strategy/factor cache key 的数据后端、市场模式、市场 profiles、本地布局、signal multiplier 等影响结果参数。

### P1-6 run manifest 写入必须原子化

涉及文件：

- `api.py`

改进：

- manifest 写入使用临时文件 + `os.replace()`。
- 对同一 run 的 manifest 写入使用锁。
- 避免 listener/waiter/stop/list/get 并发读改写导致 JSON 损坏或状态丢失。

落地状态：

- `api.py` 已使用 per-run 线程锁、`fcntl` 文件锁和临时文件原子替换。
- 并发写 manifest 的回归测试已通过。

## P2：运行一致性与接口契约

### P2-1 统一 runtime path 到 `AiminerSettings`

涉及文件：

- `agents/summary_agent.py`
- `main.py`
- `manager.py`
- `core/wiki.py`
- `core/settings.py`

改进：

- 所有 `data/`、`results/`、`logs/` 产物路径从 settings 派生。
- `SummaryAgent`、`LLMWiki`、`main.setup_logging/save_results` 接收 settings/path 参数。

落地状态：

- `SummaryAgent`、`main.py`、`manager.py`、`core/wiki.py`、`tui.py` 已使用 `AiminerSettings` 派生报告、图表、日志、DB、Wiki 路径。
- `tests/unit/test_runtime_paths.py` 已覆盖 CLI `save_results` 使用 settings 结果目录。

### P2-2 reset runs scope 必须清理真实 Swarm 产物

涉及文件：

- `scripts/reset_workspace.py`
- `tests/`

改进：

- `runs` scope 指向 `results/swarm_runs`。
- 增加 reset 覆盖真实 swarm run 目录的测试。

Agent E 落地状态：

- `scripts/reset_workspace.py` 的 `runs` scope 已改为 `results/swarm_runs`。
- `tests/unit/test_reset_workspace.py` 覆盖真实目录移动，并确认不会误清理仓库根 `swarm_runs`。

### P2-3 API 请求模型应校验枚举并兼容别名

涉及文件：

- `api.py`
- `core/settings.py`

改进：

- `SwarmConfig` / `BacktestRequest` / `StrategyRunRequest` 使用共享枚举或 `Literal`。
- 提供兼容 alias，例如 `multi -> batch/mixed`。
- 无效值在 API 边界返回 400/422，不先创建 run。

落地状态：

- `api.py` 请求模型已统一枚举/alias 校验，无效 swarm payload 会在 422 阶段失败且不创建 run。

### P2-4 stale starting run 自动恢复

涉及文件：

- `api.py`

改进：

- 对没有 pid 的 `starting` manifest 增加超时恢复逻辑。
- 超时后归一化为 `stopped` 或 `failed`，避免永久卡住。

落地状态：

- `api.py` 已把超时 `starting/pending` run 恢复为 `failed` 并记录 `failure_reason`。

### P2-5 分页 envelope 固定返回 `limit`

涉及文件：

- `api.py`
- `frontend/src/types.ts`

改进：

- 所有分页响应固定返回 `items,total,offset,limit,next_offset`。
- API contract 测试覆盖 run/log/results/strategy/wiki 分页。

落地状态：

- `api.py` 分页 envelope 已固定包含 `limit`。
- `tests/unit/test_api_contract.py` 已覆盖主要分页接口。

### P2-6 WebSocket token 连通性

涉及文件：

- `frontend/src/lib/ws.ts`
- `frontend/src/lib/api.ts`

改进：

- WebSocket URL 从当前 token 派生 `?token=...`。
- token 改变时重连。
- 页面显示 socket 状态。

落地状态：

- `frontend/src/lib/ws.ts` 已从 local token 派生 `?token=`，token 变化会重连。
- Run Detail 已显示 socket 状态。

### P2-7 TUI 关键可用性修复

涉及文件：

- `tui.py`

改进：

- 补 `subprocess` import。
- TUI 策略配置统一单一事实源：默认使用表单，只有显式高级 JSON 模式使用 JSON。
- Stop 后保持轮询直到 terminal 状态。
- quit 时等待 stop 或明确不负责停止后端 run。

落地状态：

- `tui.py` 已补 `subprocess` import。
- 策略配置默认使用表单，只有勾选高级 JSON 才读取 JSON。
- Stop 后保留轮询直到 `completed/failed/stopped`，Quit 会先尝试发送 stop。

## P3：增强与维护性

### P3-1 负 IC 支持反向交易

涉及文件：

- `app_workflow/graph.py`
- `sub_agent.py`
- `manager.py`

改进：

- 发现强度使用 `abs(IC)`。
- 记录方向。
- 自动生成 inverted/short-biased 策略候选。

落地状态：

- Eval/workflow/manager 已记录 IC 方向并按 `abs(IC)` 做强度判断。
- `manager.py` 对负 IC 因子写入 `signal_direction=-1`，并通过 `signal_multiplier` 反向策略信号。

### P3-2 策略后去相关

涉及文件：

- `manager.py`

改进：

- factor-level 与 strategy-level 去相关分开记录。
- 最终组合使用 strategy returns 再做一次相关性裁剪。

落地状态：

- `manager.py` 已在策略评估后使用策略收益再做相关性裁剪。

### P3-3 本地 panel 多文件语义明确

涉及文件：

- `core/local_data.py`

改进：

- panel 目录多文件时全部 concat，或报错要求显式布局。
- 增加多文件 panel 测试。

落地状态：

- `core/local_data.py` 已明确 `layout="panel"` 多 shard concat 语义。
- `auto` 会根据是否存在 instrument 列区分 panel vs instrument files。

### P3-4 报告图表链路补齐

涉及文件：

- `agents/eval_agent.py`
- `sub_agent.py`
- `agents/summary_agent.py`

改进：

- SubAgent 返回 `plot_paths`。
- SummaryAgent 对 dict returns 转 `pd.Series` 后生成 equity curve。

落地状态：

- `sub_agent.py` 已返回 `plot_paths`。
- `SummaryAgent` 已将 dict/list/Series returns 统一转为 `pd.Series` 并生成 equity curve。
- `tests/test_summary_agent.py` 已覆盖 dict returns 图表生成。

### P3-5 Web 历史详情与 Wiki 编辑体验

涉及文件：

- `frontend/src/pages/ManualBacktestPage.tsx`
- `frontend/src/pages/StrategyBacktestPage.tsx`
- `frontend/src/pages/WikiPage.tsx`
- `frontend/src/styles.css`

改进：

- 历史项切换时清空旧 detail，避免显示上一条结果。
- Wiki 编辑加 dirty guard。
- 补响应式布局。
- Wiki 支持 GFM 和 `[[wikilink]]` 导航。

落地状态：

- Manual/Strategy 历史详情切换已避免 stale detail。
- Wiki 已支持 dirty guard、GFM、`[[wikilink]]`。
- 移动端响应式布局已补强。

### P3-6 测试、CI、Docker、发布治理

涉及文件：

- `.github/workflows/ci.yml`
- `.github/workflows/packaging.yml`
- `.dockerignore`
- `pytest.ini`
- `tests/`
- `requirements.txt`
- `environment.yml`
- `README.md`
- `instruction.md`

改进：

- 引入 `unit/integration/external/native` markers。
- 默认 CI 跑全部 hermetic unit。
- RiceQuant/native/external 测试拆成独立 job。
- packaging workflow 依赖测试或内置最小测试闸门。
- `.dockerignore` 排除生成数据目录。
- 统一 Python 版本与依赖锁定策略。

Agent E 落地状态：

- `pytest.ini` 启用严格 marker，并声明 `unit`、`integration`、`external`、`native`。
- `tests/conftest.py` 按 `tests/unit` 和 `tests/integration` 自动补 marker。
- RiceQuant 依赖测试使用 `external` marker 和 `pytest.importorskip`，Polars/Rust 原生路径使用 `native` marker。
- CI 默认执行 `pytest tests/unit -m "unit and not external and not native" -q`。
- external/native CI job 仅手动触发，native job 会先构建 `polars_plugins` wheel。
- packaging workflow 增加 `test-gate`，前端和后端打包 job 均依赖该测试闸门。
- `.dockerignore` 排除 generated data/cache/model 目录，避免 Docker build context 膨胀。

## 并行修复分工

- Agent A：评估/Agent workflow 正确性。
- Agent B：策略、cache、持久化正确性。
- Agent C：API runtime、manifest、进程生命周期。
- Agent D：前端/TUI 可用性。
- Agent E：测试、CI、Docker、文档、reset。

## 验收建议

- `pytest -q tests/unit/test_api_contract.py tests/unit/test_manager_strategy_eval.py`
- `pytest -q` 的 hermetic unit 子集
- `cd frontend && npm run build`
- Web 启动后验证：start/stop/delete run、日志实时流、manual/strategy history、wiki edit。
- Docker 验证：`docker compose up` 默认只启动 API，不循环执行有限任务。

## 自改进执行协议

本节用于约束 Codex 后续“自己测试、自己改进”的工作方式。目标不是无限制重写，而是形成可回放、可验证、可停止的工程闭环。

### 固定循环

每一轮只处理一个明确问题，必须按下面顺序执行：

| 步骤 | 动作 | 输出物 | 不允许的做法 |
| --- | --- | --- | --- |
| 1 | 从本文件选择一个未完成或需复核的问题 | 轮次标题、涉及模块、预期行为 | 同时处理多个无关模块 |
| 2 | 阅读相关代码和既有测试 | 问题定位、影响边界 | 先改代码再定位 |
| 3 | 写最小复现或失败测试 | 新测试、现有测试调整、或明确的手工复现脚本 | 只靠人工观察判断修复成功 |
| 4 | 做最小实现修改 | 小范围 patch | 顺手重构无关代码 |
| 5 | 跑目标测试 | 具体命令和结果 | 只说“应该可以” |
| 6 | 跑必要的回归测试 | 按 `verification_matrix.md` 选择层级 | 跳过共享模块回归 |
| 7 | 更新文档 | `regression_log.md` 记录本轮；必要时更新本文件状态 | 修完不记录 |
| 8 | 标注剩余风险 | 外部依赖、手工验证、未覆盖路径 | 把未验证项描述成已完成 |

### 验证层级

后续每轮自改进必须选择至少一个验证层级。共享代码、API 契约、策略计算、运行生命周期改动必须使用多层级验证。

| 层级 | 名称 | 用途 | 典型命令 |
| --- | --- | --- | --- |
| L0 | 静态检查 | 文档、配置、轻量语法检查 | `git diff --check` |
| L1 | Python 编译检查 | 快速发现语法和导入级问题 | `python -m py_compile api.py manager.py main.py tui.py` |
| L2 | 目标单测 | 复现一个具体问题 | `pytest -q tests/unit/test_api_contract.py -k stop` |
| L3 | 模块单测 | 覆盖一个子系统 | `pytest -q tests/unit/test_strategy_correctness.py` |
| L4 | 全量 hermetic unit | 回归核心行为 | `pytest -q tests/unit` |
| L5 | 集成/前端/打包 | 验证跨边界行为 | `pytest -q tests/integration`、`cd frontend && npm run build` |
| L6 | 手工真实环境 | 验证外部服务和 UI 实时行为 | Web/TUI start、stop、delete、日志流、RiceQuant smoke |

### 停止条件

遇到下面情况必须停止并记录，不应继续自行猜测：

| 停止条件 | 原因 | 正确动作 |
| --- | --- | --- |
| 业务语义不明确 | 例如策略评分、负 IC 方向、组合权重取舍存在多种合理实现 | 写出选项和影响，等待决策 |
| 可能破坏历史数据 | 例如删除、迁移、覆盖 DB/schema/manifest | 先写 dry-run、backup、migration plan |
| 外部依赖不可用 | RiceQuant、LLM provider、Qlib 下载失败 | 标记为外部阻塞，保留 hermetic 测试 |
| 测试失败来源不明 | 改动范围外的失败可能是环境或历史脏状态 | 记录命令、错误、隔离假设 |
| 修改范围失控 | 一个问题牵出多个架构层变更 | 拆分新任务，不在同一轮混改 |

### 优先级队列

当前后续自改进建议按下面顺序推进。已完成项仍保留在上文，下面队列只记录下一阶段需要复核、补测或增强的事项。

| 优先级 | 项目 | 当前风险 | 建议第一步 | 验证入口 |
| --- | --- | --- | --- | --- |
| P0 | Swarm run lifecycle 真实环境复核 | 单测已覆盖大部分 API 重启和状态恢复，但真实进程树、uvicorn shutdown、WebSocket 日志仍需端到端验证 | 写一个本地 smoke 脚本或手工 runbook，覆盖 start/stop/delete/status/logs | `verification_matrix.md` 的 `runtime-api`、`frontend-run-control` |
| P0 | Stop run 前端到后端链路复核 | 用户曾反馈 stop 无效，需要确认当前 UI、API、worker 三层状态是否一致 | 从 Web 点击 Stop，记录网络请求、manifest 状态、进程状态、日志 terminal event | `regression_log.md` 新增真实环境记录 |
| P1 | 策略回测 golden sample | 策略核心已有单测，但需要固定一组小型 panel 作为跨语言/Rust 化基准 | 构造 3 天 x 4 标的信号和标签，固定 positions/turnover/net_returns 预期值 | `tests/unit/test_strategy_correctness.py` |
| P1 | Manual factor chart 前端验收 | 文档和前端已有图表改动，但需要确认空 returns、dict returns、长序列渲染都稳定 | 增加或补充前端层的 chart data contract 测试/手工验收 | `frontend` build + Web manual smoke |
| P1 | Wiki lint/migrate 操作闭环 | API 和前端操作存在，但应验证 dirty guard 与迁移 dry-run 不会误写 | 用测试 vault 执行 lint/migrate dry-run | `tests/unit` + 手工 Wiki 页 |
| P2 | Rust 化边界设计 | 已有 `polars_plugins` 和 Tauri sidecar，但缺少正式迁移边界 | 写 Rust migration RFC，先锁定 Python/Rust 数据协议 | 单独文档，不直接改运行代码 |
| P2 | CI 与 packaging 长期稳定性 | 当前 CI 策略已改善，但外部/native job 仍依赖环境 | 定期跑 native/external 手工 job，记录失败原因 | `verification_matrix.md` 的 `ci-packaging` |

### 文档联动规则

三个文件的职责必须保持清晰：

| 文件 | 职责 | 更新时机 |
| --- | --- | --- |
| `improvement_plan.md` | 记录问题、优先级、决策、落地状态、下一阶段队列 | 新增改进项、改变优先级、完成或废弃任务 |
| `verification_matrix.md` | 记录模块到测试命令的映射，以及改动触发哪些验证 | 新增模块、测试命令变化、CI 策略变化 |
| `regression_log.md` | 记录每轮执行、测试结果、失败、剩余风险 | 每一轮自改进结束时必须更新 |

### 每轮记录格式

每轮结束时必须在 `regression_log.md` 追加一条记录，至少包含：

| 字段 | 要求 |
| --- | --- |
| 日期/轮次 | 使用本地日期，必要时写时间 |
| 目标 | 一句话说明本轮修什么 |
| 复现 | 写明失败测试、手工步骤或为何只能做文档/静态验证 |
| 修改 | 只列用户需要理解的关键文件和行为 |
| 验证 | 写完整命令和结果 |
| 剩余风险 | 外部依赖、手工未验、性能风险、迁移风险 |
| 下一步 | 如果还有后续，明确下一轮入口 |
