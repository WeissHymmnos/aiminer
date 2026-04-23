# AIMiner Regression Log

本文件记录每轮自改进的复现、修改、验证和剩余风险。它不是 changelog，而是工程回归账本：后续 Codex 必须能根据这里判断哪些行为已经验证过、哪些只是推断、哪些仍需真实环境复核。

## 记录规则

| 规则 | 要求 |
| --- | --- |
| 每轮必记 | 只要做了代码、配置、测试、文档修改，都要追加一条记录 |
| 命令完整 | 验证命令必须可复制执行，不能只写“测试通过” |
| 区分事实和推断 | 真实执行结果写为事实；未跑的测试必须写成未验证 |
| 记录剩余风险 | 外部依赖、手工环境、性能、数据迁移、UI 真实交互都要明确 |
| 不覆盖历史 | 新轮次追加到“执行记录”顶部或底部均可，但不得改写旧记录的事实结果 |

## 记录模板

```md
### YYYY-MM-DD HH:MM - <short title>

| 字段 | 内容 |
| --- | --- |
| 目标 | <本轮要修复或验证的问题> |
| 触发来源 | <用户反馈、测试失败、计划项、review 发现> |
| 涉及模块 | `<module-tag>`，`<files>` |
| 复现方式 | <失败测试、手工步骤、或无法复现的原因> |
| 修改摘要 | <关键行为变化，不写低价值文件清单> |
| 验证命令 | `<command>` |
| 验证结果 | <通过/失败/跳过，附简要输出> |
| 剩余风险 | <未覆盖路径、外部依赖、手工验证事项> |
| 下一步 | <下一轮入口；没有则写“无”> |
```

## 当前基线

| 日期 | 基线 | 结果 | 说明 |
| --- | --- | --- | --- |
| 2026-04-21 | `pytest -q tests/unit` | 102 passed | 结构清理和主功能修复后的 unit 基线 |
| 2026-04-21 | `pytest -q tests/test_summary_agent.py tests/integration/test_manual_strategy_runner.py` | 3 passed | SummaryAgent 图表链路和 manual strategy integration 基线 |
| 2026-04-21 | `pytest -q tests/unit/test_api_contract.py` | 24 passed | API contract、run lifecycle、pagination 基线 |
| 2026-04-21 | `cd frontend && npm run build` | passed with Monaco chunk warning | 前端构建可用，chunk size 是已知非阻塞警告 |
| 2026-04-21 | `python -m py_compile main.py manager.py api.py tui.py core/wiki.py agents/summary_agent.py` | passed | 核心 Python 入口语法基线 |
| 2026-04-21 | `docker compose config --services` | `api` | 默认 Compose 不启动有限研究任务 |
| 2026-04-21 | `docker compose --profile research --profile tui config --services` | `api/tui/worker` | profile 服务可见 |
| 2026-04-21 | `bash -n start_web.sh` | passed | Web 启动脚本语法基线 |

## 待真实环境复核

| 项目 | 当前状态 | 需要的验证 | 风险 |
| --- | --- | --- | --- |
| Web Stop Run | 单测和代码路径已修，但用户曾报告 stop 无效 | Web UI 点击 Stop，确认 API 请求、manifest、进程树、日志终态一致 | 前端状态、API 状态和 worker 实际存活可能不一致 |
| WebSocket 日志流 | token 和状态显示已修 | Start run 后确认日志实时追加，断线后能恢复或显示状态 | 代理、端口、token 变化可能影响连接 |
| API shutdown hook | 单测覆盖 shutdown 清理 | 真实 uvicorn/SIGTERM graceful shutdown | `SIGKILL` 场景无法执行 shutdown hook |
| Manual Factor 图表 | 前端已有图表展示 | 使用真实/本地数据执行 manual backtest，看 chart、returns、empty state | 空 returns、长序列、异常 response 可能需要 UI 降级 |
| Strategy 历史删除 | API/frontend 已接入 | 删除一条 strategy history，确认不影响其他 run 同表达式记录 | 历史记录 ID 和 cache key 混用会导致误删风险 |
| Wiki lint/migrate | API/frontend 已接入 | 对测试 vault 执行 dry-run 和真实写入前备份 | 迁移工具可能误写用户笔记 |

## 执行记录

### 2026-04-22 - TUI Swarm API 自动探测与超时诊断

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复 TUI 固定请求 `127.0.0.1:8000` 导致 `Failed to start Swarm` 难以诊断的问题 |
| 触发来源 | 用户反馈 TUI 显示 `fail to start swarm: Swarm API POST http://127.0.0.1...` |
| 涉及模块 | `tui.py` |
| 复现方式 | 本机 `127.0.0.1:8000` 连接后超时，且存在多个旧 `uvicorn api:app` 进程占用 8000-8003；默认 TUI POST 到 8000 会超时 |
| 修改摘要 | TUI 未显式设置 `AIMINER_API_BASE_URL` 时自动探测 `127.0.0.1:8000-8020` 的健康 API；探测到其他端口时显示切换提示；探测不到时立即给出启动/设置端口的错误提示，不再盲目等待 POST 超时 |
| 验证命令 | `python -m py_compile tui.py` |
| 验证结果 | 通过 |
| 验证命令 | `python - <<'PY'\nimport os\nos.environ.pop('AIMINER_API_BASE_URL', None)\nfrom tui import TUIApp\napp = TUIApp()\ntry:\n    app._swarm_api_request_sync('GET','/api/swarm/status',None,None)\nexcept Exception as e:\n    print(type(e).__name__, str(e))\nPY` |
| 验证结果 | 返回 `RuntimeError No responsive AIMiner API found...`，错误信息可操作 |
| 验证命令 | `git diff --check -- tui.py` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 当前机器上仍有旧 uvicorn 进程占用 8000-8003；未自动 kill，需用户确认后清理或重启后端 |
| 下一步 | 清理旧 API 进程并重新运行 `./start_web.sh`，或用 `AIMINER_API_BASE_URL=http://127.0.0.1:<port> python tui.py` 显式指定健康后端 |

### 2026-04-22 - Codex provider 增加思考强度选项

| 字段 | 内容 |
| --- | --- |
| 目标 | 为本地 Codex LLM provider 增加 `low/medium/high/xhigh` 思考强度配置，并贯穿 CLI、API、Web、TUI 和 Agent 调用链 |
| 触发来源 | 用户询问调用级别后要求“加入思考强度选项” |
| 涉及模块 | `core/codex_llm.py`，`core/settings.py`，`core/llm.py`，`api.py`，`main.py`，`manager.py`，`sub_agent.py`，`app_workflow/graph.py`，`frontend/src/pages/SwarmRunsPage.tsx`，`tui.py` |
| 复现方式 | 新增/扩展 fake Codex CLI 单测，验证 `model_reasoning_effort` 参数、环境变量默认值、settings/API 校验和非法值拒绝 |
| 修改摘要 | 新增 `llm_reasoning_effort` 配置；Codex wrapper 调用 `codex exec -c model_reasoning_effort="..."`；Web/TUI 增加 Reasoning Effort 字段；CLI 增加 `--llm-reasoning-effort`；文档同步 |
| 验证命令 | `python -m py_compile core/codex_llm.py core/llm.py core/settings.py api.py main.py manager.py sub_agent.py app_workflow/graph.py app_workflow/state.py agents/idea_agent.py agents/factor_agent.py agents/eval_agent.py agents/strategy_agent.py agents/strategy_critic.py agents/summary_agent.py agents/portfolio_agent.py core/hybrid_knowledge.py core/wiki_bootstrapper.py tui.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_codex_llm.py tests/unit/test_settings.py tests/unit/test_api_contract.py` |
| 验证结果 | 45 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 118 passed |
| 验证命令 | `cd frontend && npm run build` |
| 验证结果 | 通过，保留既有 Monaco 大 chunk warning |
| 验证命令 | `git diff --check -- core/codex_llm.py core/llm.py core/settings.py api.py main.py manager.py sub_agent.py app_workflow/graph.py app_workflow/state.py agents core/hybrid_knowledge.py core/wiki_bootstrapper.py tui.py frontend/src/pages/SwarmRunsPage.tsx README.md instruction.md tests/unit/test_codex_llm.py tests/unit/test_settings.py tests/unit/test_api_contract.py` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 仍未真实启动多路 Codex Swarm 压测；`PortfolioAgent.with_structured_output` 对自定义 Codex wrapper 的兼容性后续需要单独实测 |
| 下一步 | 真实运行 `llm_provider=codex,llm_reasoning_effort=xhigh` 的单 agent smoke，确认 Codex CLI 输出结构化 JSON 的稳定性 |

### 2026-04-22 - 接入本地 Codex LLM provider

| 字段 | 内容 |
| --- | --- |
| 目标 | 新增 `llm_provider=codex`，通过本地 `codex exec` 替代现有文本生成 LLM API |
| 触发来源 | 用户要求接入本地 Codex 调用能力作为 LLM API 替代选项 |
| 涉及模块 | `core/llm.py`，`core/codex_llm.py`，`core/settings.py`，`api.py`，`main.py`，`README.md`，`instruction.md` |
| 复现方式 | 新增 fake Codex CLI 单测，验证 LangChain wrapper、provider 显式选择、API 请求校验和 embedding 拒绝逻辑 |
| 修改摘要 | 新增 `CodexChatModel`；`get_llm(provider="codex")` 返回本地 Codex wrapper；settings/API 接受 Codex 作为 LLM provider 但拒绝作为 embedding provider；CLI choices 和文档同步 |
| 验证命令 | `python -m py_compile core/codex_llm.py core/llm.py core/settings.py api.py main.py tui.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_codex_llm.py tests/unit/test_settings.py tests/unit/test_api_contract.py` |
| 验证结果 | 39 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 112 passed |
| 验证命令 | `git diff --check -- core/codex_llm.py core/llm.py core/settings.py api.py main.py README.md instruction.md tests/unit/test_settings.py tests/unit/test_api_contract.py tests/unit/test_codex_llm.py` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 未真实调用线上 Codex 模型，只用 fake CLI 验证命令边界；Swarm 并发启动多个 Codex CLI 的资源占用仍需真实环境观察 |
| 下一步 | 如真实运行出现资源争用，再增加 `AIMINER_CODEX_MAX_CONCURRENT` 或改为串行锁 |

### 2026-04-21 - 建立自改进文档闭环

| 字段 | 内容 |
| --- | --- |
| 目标 | 落实 `improvement_plan.md`、`verification_matrix.md`、`regression_log.md` 三个自改进支撑文件 |
| 触发来源 | 用户要求先落实三个文件，用于后续 Codex 自测和自改进 |
| 涉及模块 | `docs`，`improvement_plan.md`，`verification_matrix.md`，`regression_log.md` |
| 复现方式 | 文档治理任务，不涉及运行时 bug 复现 |
| 修改摘要 | 在改进计划中新增自改进执行协议、验证层级、停止条件、优先级队列和文档联动规则；新增验证矩阵；新增回归日志模板、基线和待复核项 |
| 验证命令 | `git diff --check -- improvement_plan.md verification_matrix.md regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 三个文件只建立流程，不代表真实环境 stop run、WebSocket、Wiki migrate 已完成复核 |
| 下一步 | 执行 diff check 后，把结果回填本条记录 |
