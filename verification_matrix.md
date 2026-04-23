# AIMiner Verification Matrix

本文件定义 AIMiner 自改进过程中的验证入口。每次修改都应先根据“触发条件”选择最小必要验证，再根据影响范围追加回归验证。目标是让 Codex 在自行修复时知道该跑什么、为什么跑、什么结果才算通过。

## 使用规则

| 规则 | 要求 |
| --- | --- |
| 先窄后宽 | 先跑能复现问题的目标测试，再跑受影响模块的回归测试 |
| 共享代码加宽验证 | 修改 `api.py`、`manager.py`、`core/strategy.py`、`core/manual_runner.py`、`app_workflow/*` 时不得只跑单个测试 |
| 文档也要检查 | 文档改动至少跑 `git diff --check`，涉及命令时尽量验证命令存在 |
| 外部依赖隔离 | RiceQuant、Qlib、LLM provider、native Rust build 不得阻塞 hermetic unit 的结论 |
| 失败必须记录 | 无论失败是否由本轮引起，都要在 `regression_log.md` 写明命令、失败摘要、隔离判断 |

## 验证层级

| 层级 | 适用场景 | 命令 | 通过标准 |
| --- | --- | --- | --- |
| L0 Markdown/diff | 只改文档、配置、注释、计划文件 | `git diff --check -- .` | 无 whitespace error |
| L1 Python syntax | 改 Python 入口、API、TUI、manager | `python -m py_compile api.py manager.py main.py tui.py` | 命令退出码为 0 |
| L1 Target Python syntax | 只改少量 Python 文件 | `python -m py_compile <changed-files>` | 命令退出码为 0 |
| L2 Target pytest | 修复一个具体 bug | `pytest -q <test-file> -k <case>` | 目标测试通过，失败测试变绿 |
| L3 Module pytest | 改一个子系统 | `pytest -q tests/unit/<module-test>.py` | 模块测试全通过 |
| L4 Hermetic unit | 改共享核心或多个模块 | `pytest -q tests/unit` | unit 全通过 |
| L5 Integration | 改跨模块执行链路 | `pytest -q tests/integration` | integration 全通过或明确外部阻塞 |
| L5 Frontend build | 改 `frontend/src` 或 API 契约影响前端 | `cd frontend && npm run build` | 构建通过；chunk warning 可记录但不阻塞 |
| L5 Compose config | 改 Docker/compose/env/default entrypoint | `docker compose config --services` | 默认服务符合预期 |
| L5 Profile compose | 改 research/tui profile | `docker compose --profile research --profile tui config --services` | profile 服务符合预期 |
| L6 Manual Web smoke | 改 run lifecycle、WebSocket、history、wiki editor | 手工启动 Web，执行指定路径 | 记录步骤、结果、截图或日志摘要 |
| L6 External smoke | 改 RiceQuant/Qlib/LLM provider | 使用真实凭证执行最小 run | 成功或记录外部错误，不污染 hermetic 结论 |

## 模块矩阵

| 模块标签 | 触发条件 | 必跑验证 | 建议追加验证 | 关注点 |
| --- | --- | --- | --- | --- |
| `runtime-api` | 修改 `api.py`、run manifest、stop/delete/status/logs、auth、pagination | `pytest -q tests/unit/test_api_contract.py` | `pytest -q tests/unit`；Web manual start/stop/delete | API 重启后状态恢复、活跃进程识别、manifest 原子写入、DELETE 不误删活跃 run |
| `swarm-manager` | 修改 `manager.py`、并行执行、全局 timeout、portfolio aggregation | `pytest -q tests/unit/test_manager_strategy_eval.py` | `pytest -q tests/unit/test_agent_workflow_regressions.py tests/unit/test_strategy_correctness.py` | 并发上限、超时取消、负 IC、策略去相关、最佳结果选择 |
| `agent-workflow` | 修改 `app_workflow/*`、`sub_agent.py`、`agents/eval_agent.py`、`agents/factor_agent.py` | `pytest -q tests/unit/test_agent_workflow_regressions.py` | `pytest -q tests/test_agent_validation.py tests/test_early_stopping.py` | 最佳因子快照、robustness 不覆盖主结果、策略失败隔离 |
| `strategy-core` | 修改 `core/strategy.py`、策略模板、成本、仓位、rebalance | `pytest -q tests/unit/test_strategy_correctness.py` | `pytest -q tests/integration/test_manual_strategy_runner.py tests/unit/test_manager_strategy_eval.py` | 权重上限、turnover、cost、rebalance、cache/persist ID |
| `manual-runner` | 修改 `core/manual_runner.py`、manual factor/strategy run、cache key、charts | `pytest -q tests/integration/test_manual_strategy_runner.py` | `pytest -q tests/unit/test_api_contract.py tests/test_summary_agent.py` | cache key 完整性、chart paths、history detail、manual API response |
| `evaluator-rq` | 修改 `core/alphaeval/rq_eval.py`、RiceQuant evaluator、Rank IC | `pytest -q tests/unit/test_rq_eval_metrics.py` | 外部 RiceQuant smoke；`pytest -q tests/test_rq_connection.py -m external` | 日期分组 Rank IC、NaN、小截面、外部认证失败降级 |
| `local-data` | 修改 `core/local_data.py`、本地 CSV/Parquet layout、market profile | `pytest -q tests/unit/test_local_data.py` | `pytest -q tests/integration/test_manual_strategy_runner.py` | panel 多文件 concat、instrument layout、字段标准化、日期对齐 |
| `portfolio` | 修改 `core/portfolio.py`、`agents/portfolio_agent.py` | `pytest -q tests/unit/test_portfolio.py tests/unit/test_portfolio_agent.py` | `pytest -q tests/unit/test_manager_strategy_eval.py` | 权重归一、协方差异常、空 returns、组合选择 |
| `wiki-rag` | 修改 `core/wiki.py`、`core/rag.py`、`core/hybrid_knowledge.py`、Wiki API | `pytest -q tests/test_rag.py` | Wiki manual lint/edit/migrate dry-run | wikilink、backlink、dirty guard、batch compile、RAG 去重 |
| `summary-report` | 修改 `agents/summary_agent.py`、报告图表、plot paths | `pytest -q tests/test_summary_agent.py` | 手工检查 `results/reports` 输出 | dict/list/Series returns、equity curve、缺图降级 |
| `frontend-run-control` | 修改 `frontend/src/pages/SwarmRunsPage.tsx`、`SwarmRunDetailPage.tsx`、`frontend/src/lib/api.ts`、`frontend/src/lib/ws.ts` | `cd frontend && npm run build` | Web manual start/stop/delete/logs；`pytest -q tests/unit/test_api_contract.py` | Stop 按钮是否发请求、socket token、状态文案、inactive/running 显示 |
| `frontend-backtest` | 修改 `ManualBacktestPage.tsx`、`StrategyBacktestPage.tsx`、图表组件、Monaco editor | `cd frontend && npm run build` | 手工执行 manual factor/strategy backtest | stale detail、图表空数据、模板加载、editor payload |
| `frontend-wiki-admin` | 修改 `WikiPage.tsx`、`AdminPage.tsx`、reset/lint/migrate UI | `cd frontend && npm run build` | 手工 Wiki dirty guard、admin reset dry-run | 误写、未保存提示、dry-run 可见性 |
| `tui` | 修改 `tui.py`、TUI start/stop/editor/manual/strategy | `python -m py_compile tui.py` | 手工 TUI run；API contract tests | stop 后继续轮询、quit 清理、editor fallback、表单/JSON 单一事实源 |
| `settings-runtime-path` | 修改 `core/settings.py`、runtime path、reset workspace、env | `pytest -q tests/unit/test_settings.py tests/unit/test_runtime_paths.py tests/unit/test_reset_workspace.py` | `python scripts/reset_workspace.py --dry-run` | 路径统一、dry-run、backup、不得误删 tracked docs |
| `docker-ci-packaging` | 修改 Dockerfile、compose、workflows、pytest markers、packaging | `docker compose config --services` | `docker compose --profile research --profile tui config --services`；CI dry review | 默认不循环运行、profile 隔离、build context、test gate |
| `rust-polars` | 修改 `polars_plugins/*`、Rust expression plugin | `pytest -q tests/test_polars_refactor.py tests/test_polars_ops_extensive.py -m "not external"` | `cd polars_plugins && cargo test`；native wheel build | pandas/polars 数值一致、窗口函数、NaN、表达式解析 |
| `tauri` | 修改 `src-tauri/*`、sidecar、desktop packaging | `cd src-tauri && cargo check` | Tauri app 手工启动 | sidecar 启动、进程退出、前后端端口、日志 |
| `docs` | 修改 `README.md`、`instruction.md`、`docs/*`、计划文件 | `git diff --check -- <changed-docs>` | 链接/命令抽样验证 | 文档与真实命令一致，不记录过期路径 |

## 常用命令清单

| 目的 | 命令 |
| --- | --- |
| 查看改动 | `git status --short` |
| 查看当前差异 | `git diff -- <path>` |
| whitespace 检查 | `git diff --check -- .` |
| 核心 Python 编译 | `python -m py_compile main.py manager.py api.py tui.py core/wiki.py agents/summary_agent.py` |
| API contract | `pytest -q tests/unit/test_api_contract.py` |
| 核心 unit | `pytest -q tests/unit` |
| 策略相关 | `pytest -q tests/unit/test_strategy_correctness.py tests/integration/test_manual_strategy_runner.py tests/unit/test_manager_strategy_eval.py` |
| Agent workflow | `pytest -q tests/unit/test_agent_workflow_regressions.py tests/test_agent_validation.py tests/test_early_stopping.py` |
| 本地数据 | `pytest -q tests/unit/test_local_data.py` |
| 前端构建 | `cd frontend && npm run build` |
| Compose 默认服务 | `docker compose config --services` |
| Compose profiles | `docker compose --profile research --profile tui config --services` |
| Rust plugin | `cd polars_plugins && cargo test` |
| Tauri check | `cd src-tauri && cargo check` |

## 手工验证 Runbook

### Web Run Lifecycle

| 步骤 | 操作 | 期望结果 |
| --- | --- | --- |
| 1 | 启动后端和前端 | API health 正常，前端可访问 |
| 2 | 在 Run Launcher 点击 Start Run | 返回 `run_id`，列表出现 run，日志开始追加 |
| 3 | 打开 Run Detail | WebSocket 状态显示 connected 或可恢复状态 |
| 4 | 点击 Stop | Network 中出现 `POST /api/swarm/runs/{run_id}/stop` |
| 5 | 等待终态 | run 状态变为 `stopped` 或 `failed`，不再显示 active |
| 6 | 点击 Delete | inactive run 删除成功，manifest/log 文件不存在或被正确移除 |
| 7 | 刷新页面 | 删除后的 run 不再出现，status running count 不回弹 |

### Manual Factor Backtest

| 步骤 | 操作 | 期望结果 |
| --- | --- | --- |
| 1 | 输入一个最小合法表达式 | API 返回 job id |
| 2 | 查看结果卡片 | IC、Rank IC、returns、chart 区域不报错 |
| 3 | 切换历史项 | 详情不会短暂显示上一条 stale result |
| 4 | 删除历史项 | 列表刷新，选中项清空 |

### Strategy Backtest

| 步骤 | 操作 | 期望结果 |
| --- | --- | --- |
| 1 | 选择模板或填写 `strategy_config` | payload 包含完整策略字段 |
| 2 | 执行 strategy run | 返回 strategy id、metrics、positions summary |
| 3 | 查看图表和 JSON | returns/chart 不为空时正常展示，空值时有降级文案 |
| 4 | 删除历史项 | 不影响其他 run 的同表达式策略历史 |

### Wiki/Admin

| 步骤 | 操作 | 期望结果 |
| --- | --- | --- |
| 1 | 编辑 Wiki 页面但不保存 | 离开页面出现 dirty guard |
| 2 | 执行 lint dry-run | 显示 lint 结果，不写入 vault |
| 3 | 执行 migrate dry-run | 显示将变更内容，不直接改文件 |
| 4 | 执行 reset dry-run | 显示 scopes 和 candidate paths，不删除真实数据 |

## 结果记录规则

每次执行验证后，必须把关键结果写入 `regression_log.md`。记录粒度遵循下面规则：

| 场景 | 记录要求 |
| --- | --- |
| 全部通过 | 写命令、耗时或摘要、通过数量 |
| 部分失败 | 写失败测试、首个错误、是否与本轮相关 |
| 跳过测试 | 写跳过原因，例如外部凭证缺失、native toolchain 不可用 |
| 手工验证 | 写操作步骤、观察结果、遗留风险 |
| 只改文档 | 写 `git diff --check` 结果 |
