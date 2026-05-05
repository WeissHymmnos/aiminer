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

### 2026-04-29 12:10 - Factor 动态窗口修复

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 生成动态窗口参数时进入 `evaluation_failed=True`，并减少 dry-run 标量输入导致的无效重试 |
| 触发来源 | 300 轮本地期货 swarm 运行到动量专家第 29 轮时，因 `Operator 'Ref' window must be a positive constant integer` 评估失败 |
| 涉及模块 | `factor-agent`，`dry-run`，`agents/factor_agent.py`，`core/alphaeval/rq_eval.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 构造 `Mean($close, Sub($volume, 1))`、`Ref($close, Mean($volume, 20))`、`Corr(..., Mean(...))`、`Ts_Percentile(..., dynamic_window, dynamic_percentile)` 等动态窗口表达式 |
| 修改摘要 | FactorAgent 修复器将动态滚动窗口替换为安全常量默认值：`Ref/Delta=1`，常规滚动/相关窗口=20，`Ts_Percentile` 动态 percentile=50；RiceQuant dry-run 的 `Log` 先广播标量，避免 `'int' object has no attribute 'replace'` |
| 验证命令 | `python -m py_compile agents/factor_agent.py core/alphaeval/rq_eval.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，27 passed |
| 验证命令 | `pytest -q tests/unit/test_manager_strategy_eval.py tests/unit/test_strategy_agent_normalization.py tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，89 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | 动态窗口会被降级成默认窗口，语义可能不完全等同于 LLM 原意；但能避免本地长跑被无效表达式污染为失败评估 |
| 下一步 | 重新启动 300 轮本地期货 swarm，继续监控 `evaluation_failed=True`、`simulated=True`、内存和内核日志 |

### 2026-04-29 11:05 - 禁用 Chroma 词法降级

| 字段 | 内容 |
| --- | --- |
| 目标 | 在当前环境 Chroma Rust binding 会原生崩溃时，提供完全绕开 Chroma 的稳定长跑路径 |
| 触发来源 | process 与 thread 两种并行后端均出现 `chromadb_rust_bindings.abi3.so` / `tokio-runtime` segfault |
| 涉及模块 | `rag`，`wiki`，`core/rag.py`，`core/wiki.py` |
| 复现方式 | 使用 `--parallel --swarm-executor thread` 运行，启动阶段 Chroma 初始化/检索触发内核 segfault，进程 code 1 退出 |
| 修改摘要 | 新增 `AIMINER_DISABLE_CHROMA=1` 路径；RAG 使用本地 markdown/rst/txt chunk 的词法检索和内存经验缓存；Wiki 继续写 markdown，检索改用 vault 文件词法搜索并跳过 Chroma shadow index |
| 验证命令 | `python -m py_compile core/rag.py core/wiki.py manager.py agents/summary_agent.py core/alphaeval/rq_eval.py`；`pytest -q tests/test_rag.py tests/unit/test_wiki_resilience.py tests/unit/test_rag_readiness.py tests/unit/test_manager_strategy_eval.py`；`AIMINER_DISABLE_CHROMA=1 python - <<'PY'\nfrom core.rag import RAGModule\nfrom core.wiki import LLMWiki\nr = RAGModule(docs_dir='data/rag_docs', embedding_provider='glm')\nw = LLMWiki(embedding_provider='glm')\nprint(type(r.retrieve('momentum', 1)).__name__)\nprint(w.retrieve('momentum', 1)[:20])\nPY`；`pytest -q tests/unit`；`git diff --check` |
| 验证结果 | 通过；相关测试 22 passed，禁用 Chroma smoke 输出 `str` 和 Wiki 内容，完整 unit 2754 passed，diff check 无输出 |
| 剩余风险 | 词法检索质量弱于向量检索；但能规避当前 Chroma 原生崩溃，适合作为本次 300 轮稳定运行配置 |
| 下一步 | 以 `AIMINER_DISABLE_CHROMA=1 --swarm-executor thread` 重启完整 300 轮 |

### 2026-04-29 10:55 - Matplotlib headless 后端

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 thread executor 下 matplotlib 使用 Tk 后端导致 `main thread is not in main loop` |
| 触发来源 | thread 并行长跑中出现 `tkinter Image.__del__` 和 `Variable.__del__` ignored exception |
| 涉及模块 | `plotting`，`manager.py`，`agents/summary_agent.py`，`core/alphaeval/rq_eval.py` |
| 复现方式 | `--swarm-executor thread` 运行到回测图表/策略图表生成阶段，Tk 对象在非主线程析构 |
| 修改摘要 | 在入口设置 `MPLBACKEND=Agg`；SummaryAgent 和 RiceQuantEval 在导入 pyplot 前强制 `matplotlib.use("Agg", force=True)` |
| 验证命令 | `python -m py_compile manager.py agents/summary_agent.py core/alphaeval/rq_eval.py`；`pytest -q tests/unit/test_manager_strategy_eval.py tests/test_summary_agent.py tests/integration/test_manual_strategy_runner.py`；`python - <<'PY'\nimport matplotlib\nimport manager\nprint(matplotlib.get_backend())\nPY`；`pytest -q tests/unit`；`git diff --check` |
| 验证结果 | 通过；相关测试 18 passed，后端输出 `Agg`，完整 unit 2754 passed，diff check 无输出 |
| 剩余风险 | 只覆盖项目内 matplotlib 入口；若第三方库内部自行切换 GUI 后端，需要继续观察运行日志 |
| 下一步 | 重新启动 thread 并行 300 轮，并确认不再出现 Tk ignored exception |

### 2026-04-29 10:45 - Swarm thread 并行后端

| 字段 | 内容 |
| --- | --- |
| 目标 | 在 Chroma Rust binding 多进程不稳定时，仍保留 swarm 并行能力并避免 `ProcessPool` worker 原生崩溃 |
| 触发来源 | 加全局 Chroma 锁后仍出现 `tokio-runtime` 线程 segfault，说明 Chroma 后台线程跨进程共享持久库仍不安全 |
| 涉及模块 | `manager`，`manager.py`，`tests/unit/test_manager_strategy_eval.py` |
| 复现方式 | 使用原 4 角色 `--parallel` 命令，内核日志继续出现 `chromadb_rust_bindings.abi3.so` segfault，主流程恢复为 0 结果 |
| 修改摘要 | 新增 `--swarm-executor {process,thread}` / `AIMINER_SWARM_EXECUTOR`；thread 模式使用 `ThreadPoolExecutor` 并行运行 agent，避免多进程 Chroma；保留 process 模式和破损恢复 |
| 验证命令 | `python -m py_compile manager.py tests/unit/test_manager_strategy_eval.py core/chroma_lock.py core/rag.py core/wiki.py`；`pytest -q tests/unit/test_manager_strategy_eval.py`；`pytest -q tests/unit`；`git diff --check` |
| 验证结果 | 通过；manager 相关 15 passed，完整 unit 2754 passed，diff check 无输出 |
| 剩余风险 | thread 模式下 CPU 密集段并行度弱于 process 模式，但 LLM/API 等 I/O 阶段仍并行；真实 300 轮需要继续观察 qlib/thread 安全性 |
| 下一步 | 用 `--parallel --swarm-executor thread --disable-early-stop --swarm-global-timeout-seconds 0` 重跑完整 300 轮 |

### 2026-04-29 10:35 - ChromaDB 跨进程互斥

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免并行 worker 同时访问 Chroma/RAG/Wiki 持久库时触发 `chromadb_rust_bindings.abi3.so` segfault |
| 触发来源 | 重启 300 轮 swarm 后，内核日志出现 `tokio-runtime-w ... segfault ... chromadb_rust_bindings.abi3.so`，主流程捕获为 `BrokenProcessPool` |
| 涉及模块 | `rag`，`wiki`，`core/chroma_lock.py`，`core/rag.py`，`core/wiki.py` |
| 复现方式 | 4 个并行子进程几乎同时初始化 RAG/Wiki ChromaDB，2 个 tokio runtime worker 在线程级崩溃 |
| 修改摘要 | 新增全局 advisory file lock；RAG/Wiki 的 Chroma init/query/upsert/add/get 全部串行化，保留 LLM 和回测并行 |
| 验证命令 | `python -m py_compile core/chroma_lock.py core/rag.py core/wiki.py manager.py`；`pytest -q tests/test_rag.py tests/unit/test_wiki_resilience.py tests/unit/test_rag_readiness.py tests/unit/test_manager_strategy_eval.py`；`pytest -q tests/unit`；`git diff --check` |
| 验证结果 | 通过；相关测试 21 passed，完整 unit 2753 passed，diff check 无输出 |
| 剩余风险 | Chroma 调用被串行化会降低 RAG/Wiki 检索吞吐；真实 300 轮仍需观察是否有单进程 Chroma 原生崩溃 |
| 下一步 | 重新启动完整 300 轮本地期货 swarm，并监控内核日志、worker RSS 和 checkpoint 恢复路径 |

### 2026-04-29 10:27 - 并行进程池破损恢复

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 `ProcessPoolExecutor` 中 worker 被异常终止后，主流程只打印普通异常并以异常码退出 |
| 触发来源 | 300 轮本地期货 swarm 运行中出现 `A process in the process pool was terminated abruptly while the future was running or pending.`，随后主进程退出 |
| 涉及模块 | `manager`，`manager.py`，`tests/unit/test_manager_strategy_eval.py` |
| 复现方式 | 单测模拟 `future.result()` 抛出 `BrokenProcessPool`，并预写 agent checkpoint |
| 修改摘要 | 增加进程池破损识别；破损时取消剩余 future、终止进程池、用 checkpoint 恢复已完成 agent 结果；checkpoint 恢复日志区分 timeout 和 worker failure |
| 验证命令 | `python -m py_compile manager.py tests/unit/test_manager_strategy_eval.py`；`pytest -q tests/unit/test_manager_strategy_eval.py`；`pytest -q tests/unit`；`git diff --check` |
| 验证结果 | 通过；manager 相关 14 passed，完整 unit 2753 passed，diff check 无输出 |
| 剩余风险 | 如果 worker 被系统级信号杀掉，代码能有序恢复和释放池，但真实 300 轮是否还有资源峰值仍需继续跑实测 |
| 下一步 | 重启 300 轮 swarm，继续观察 worker RSS、swap 和是否再次出现进程池破损 |

### 2026-04-29 10:05 - StrategyAgent mixed/hybrid 模式归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 生成 `strategy_mode="mixed"` 或 hybrid 类别时被 `StrategyConfig` 枚举校验跳过 |
| 触发来源 | 300 轮本地期货 swarm 运行中出现 `[StrategyAgent] Skipping LLM candidate 'futures_hybrid_factor'` |
| 涉及模块 | `strategy-agent`，`agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 日志中 `strategy_mode` 为 `mixed`，但 `StrategyConfig.strategy_mode` 只允许 `cross_sectional` 或 `time_series` |
| 修改摘要 | 将 `mixed/hybrid/hybrid_factor/futures_hybrid_factor/combined` 等模式作为市场默认策略模式别名；期货归一为 `time_series`，股票归一为 `cross_sectional` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py`；`pytest -q tests/unit/test_strategy_agent_normalization.py`；`pytest -q tests/unit`；`git diff --check` |
| 验证结果 | 通过；策略归一化 47 passed，完整 unit 2752 passed，diff check 无输出 |
| 剩余风险 | LLM 仍可能发明新的策略模式别名，需要运行中继续按校验日志捕获并补充 |
| 下一步 | 重启 300 轮 swarm，继续观察是否还有新的候选参数组合被跳过 |

### 2026-04-29 09:23 - FactorAgent LLM JSON 解析失败重试

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 偶发输出坏 JSON 时，`factor_agent` 节点直接返回 `error` 并中断子代理 |
| 触发来源 | 300 轮无早停长跑中，波动率专家在实现 `Volume-Price Divergence Reversal Factor` 时出现 `Unparseable LLM JSON response` |
| 涉及模块 | `agents/factor_agent.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 构造形式化成功、第一次 implementation JSON 缺少冒号、第二次 implementation 成功的 LLM 响应序列 |
| 修改摘要 | 形式化 JSON 解析/校验失败最多重试 2 次；实现阶段 JSON 解析/校验失败进入原有 self-correction retry；形式化连续失败时返回受控 invalid factor 而不是节点 `error` |
| 验证命令 | `python -m py_compile agents/factor_agent.py tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，22 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2751 passed |
| 剩余风险 | LLM 仍可能连续多次返回不可解析 JSON；这种情况会作为 invalid factor 进入评估失败路径，长跑继续按实际日志判断是否需要更强 JSON repair |
| 下一步 | 重启 300 轮无早停长跑，继续监控 `FactorAgent` node error、`evaluation_failed`、simulated fallback 和内存 |

### 2026-04-29 09:08 - Strategy mode threshold/MA cross 归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 将入场规则或均线规则写入 `strategy_mode` 时，策略候选全部校验失败并回落模板 |
| 触发来源 | 300 轮无早停长跑中，动量专家候选因 `strategy_mode='signal_threshold'/'quantile_threshold'/'ma_cross'` 不是合法枚举而被跳过 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `signal_threshold`、`quantile_threshold`、`ma_cross` 三类 futures 候选，旧逻辑不能归一到 `time_series` |
| 修改摘要 | 将 threshold/quantile threshold/MA cross/crossover 类策略模式别名加入上下文依赖归一化；futures 默认归一到 `time_series`，股票默认归一到 `cross_sectional` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，46 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2749 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | LLM 仍可能发明新的 strategy_mode 标签；长跑继续按实际日志补别名 |
| 下一步 | 重启 300 轮无早停长跑，继续监控 strategy candidate skip、simulated fallback、evaluation_failed 和内存 |

### 2026-04-29 08:48 - Strategy mode breakout 归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode="breakout"` 时策略候选被 `StrategyConfig` 校验跳过 |
| 触发来源 | 300 轮无早停长跑中 `volume_confirmed_breakout` 候选因 `strategy_mode='breakout'` 不是合法枚举而被跳过 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode="breakout"` 的 futures/stock 候选，旧逻辑不能归一到 `time_series`/`cross_sectional` |
| 修改摘要 | 将 `breakout/breakout_strategy/breakout_signal/breakout_momentum/volume_breakout/volume_confirmed_breakout` 加入上下文依赖别名；futures 默认归一到 `time_series`，股票默认归一到 `cross_sectional` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，45 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2748 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | LLM 仍可能发明新的 strategy_mode 标签；后续长跑继续按实际日志补别名 |
| 下一步 | 重启 300 轮无早停长跑，继续监控 strategy candidate skip、simulated fallback、evaluation_failed 和内存 |

### 2026-04-29 08:39 - 多参数二元因子算子归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 生成 `Add/Sub/Mul/Div/Max/Min` 等二元算子的 3+ 参数形式时通过静态校验、却在 RiceQuant dry-run 中失败 |
| 触发来源 | 300 轮无早停长跑中统计套利因子最终 `evaluation_failed=True`，错误为 `RiceQuantEval.dry_run.<locals>.<lambda>() takes 2 positional arguments but 3 were given` |
| 涉及模块 | `agents/factor_agent.py`，`core/alphaeval/rq_eval.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 新增 `Div($close, $open, $volume)` 静态校验回归；新增多参数算术表达式自动折叠测试；新增 `Count($close, 20)` dry-run 回归 |
| 修改摘要 | FactorAgent 将常见多参数二元算子左折叠为嵌套二元调用，并对未修复二元算子严格要求 2 个位置参数；`Count` 的真实评估和 dry-run 支持 `Count(df, n)` |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，20 passed |
| 验证命令 | `python -m py_compile agents/factor_agent.py core/alphaeval/rq_eval.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2747 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | 比较算子 3+ 参数仍选择拒绝而不是猜测链式语义；如果 LLM 反复输出该类比较表达式，需再增加有明确语义的归一化 |
| 下一步 | 重启 300 轮无早停长跑，继续监控 `evaluation_failed=True`、simulated fallback 和内存 |

### 2026-04-29 08:14 - Strategy mode simple/composite 归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode="simple"` 或 `strategy_mode="composite"` 时策略候选全部被跳过 |
| 触发来源 | 300 轮无早停长跑中出现 3 个 LLM strategy candidate 因 `strategy_mode` 为 `simple/composite` 未映射到合法枚举而被跳过，随后回退模板 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造模板名含 `_ts_`/`_cs_` 且 `strategy_mode` 为 `simple/composite` 的候选，旧逻辑不能从模板名推断 time_series/cross_sectional |
| 修改摘要 | `_strategy_mode_hint` 支持 `_ts_/_cs_` 和 `*_ts/*_cs` 模板名提示；`simple/composite/generated/generic` 模式按模板提示或市场默认归一 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，44 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2744 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | LLM 仍可能发明新的 strategy_mode 标签；后续长跑继续按确定日志补映射 |
| 下一步 | 重启 300 轮无早停长跑，继续监控 skip/fallback/simulated/evaluation_failed 和内存 |

### 2026-04-29 08:00 - 结构化 selection_rule 归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 将 `selection_rule` 返回为 dict 时 StrategyAgent 直接回退模板策略 |
| 触发来源 | 300 轮无早停长跑中出现 `[StrategyAgent] Falling back to templates`，原因是 `selection_rule` 收到 `{method: rolling_rank, long_threshold: ..., short_threshold: ...}` 这类结构化对象 |
| 涉及模块 | `schemas/messages.py`，`agents/strategy_agent.py`，`tests/unit/test_strategy_output_schema.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造结构化 `selection_rule`，旧 schema 期望 string 并在进入 StrategyAgent 归一化前失败 |
| 修改摘要 | schema 允许 `selection_rule` 为字符串或 dict；StrategyAgent 将结构化规则中的 method、阈值和 top/bottom 数量拆解并合并到标准字段；新增 rolling rank 相关别名映射 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_output_schema.py` |
| 验证结果 | 通过，50 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py schemas/messages.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2743 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | LLM 仍可能输出未知结构化键；后续长跑如出现新的确定形态继续补映射 |
| 下一步 | 重新启动 300 轮无早停长跑并监控是否仍有模板回退、skip、模拟指标或真实评估失败 |

### 2026-04-29 07:50 - cross-sectional rank percentile 规则归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `selection_rule="cross-sectional rank percentile"` 时策略候选被枚举校验跳过 |
| 触发来源 | 300 轮无早停长跑中出现 `[StrategyAgent] Skipping LLM candidate 'price_volume_divergence_cross_sectional'`，错误为 `selection_rule` 不在允许枚举 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `selection_rule="cross-sectional rank percentile"` 的截面候选，旧逻辑不能映射到合法 `threshold` |
| 修改摘要 | 将 `cross_sectional_rank_percentile/quantile`、`cross_sectional_ranking_percentile/quantile`、`cs_rank_percentile/quantile` 等别名归一为 `threshold` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，42 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2741 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | 仍可能有新的自然语言 selection_rule 别名未覆盖；继续以真实长跑日志为准补确定性映射 |
| 下一步 | 重新启动 300 轮无早停长跑并监控是否还有 StrategyConfig skip |

### 2026-04-29 07:42 - 中文截面选股规则归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免长跑中 LLM 输出中文自然语言 `selection_rule` 时，策略候选被 `StrategyConfig` 枚举校验跳过 |
| 触发来源 | 300 轮无早停长跑中出现 `[StrategyAgent] Skipping LLM candidate '波动率扩张截面多空'`，错误为 `selection_rule` 不是 `top_n/bottom_n/top_bottom_n/threshold` |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `selection_rule="选择因子值最高的20%品种做多，因子值最低的20%品种做空"`，旧逻辑不能映射到 `top_bottom_n` |
| 修改摘要 | 在策略选择规则归一化中增加中文 top/bottom 启发式：`最高/较高/做多/多头` 映射 top 侧，`最低/较低/做空/空头` 映射 bottom 侧；两侧同时出现时截面策略归一为 `top_bottom_n`，时序策略仍归一为 `threshold` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，41 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2740 passed |
| 验证命令 | `git diff --check` |
| 验证结果 | 通过，无输出 |
| 剩余风险 | 中文自然语言仍可能出现未覆盖的行业口径或排序描述；后续长跑若再出现 StrategyConfig skip，继续按真实日志补确定性别名 |
| 下一步 | 重新启动 300 轮无早停长跑并继续监控策略候选跳过、模拟回退、评估失败和内存 |

### 2026-04-29 07:33 - rolling 算子缺省窗口自动修复

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免长跑中 LLM 输出 `Mean(x)` 这类缺少窗口的 rolling 表达式，导致因子重试耗尽并进入 `evaluation_failed=True` |
| 触发来源 | 300 轮无早停长跑中基本面套利专家因子在 2 次重试后失败：`Operator 'Mean' requires at least 2 arguments, but got 1.` |
| 涉及模块 | `agents/factor_agent.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 构造 `Rank(Mean($close))`、`Rank(Add(Delta($volume), Ref($close)))`、`Rank(Med($volume))`、`Rank(Corr($close, $volume))` 等缺省参数表达式，旧逻辑无法补齐窗口或别名 |
| 修改摘要 | 在 FactorAgent 通用 arity repair 中补齐常见 rolling 默认窗口：`Mean/Std/Median/EMA/WMA/Sum/Ts_*` 默认 20，`Ref/Delta` 默认 1，`Corr/Cov` 缺窗口默认 20；同时将 `Med` 归一为 `Median`，将一元 `Add/Mul` 退化为其唯一参数 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，17 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2739 passed |
| 剩余风险 | 默认窗口是工程降级策略，语义可能偏离 LLM 原意；后续长跑若出现其它缺省/别名算子，继续按真实失败日志补确定性修复 |
| 下一步 | 重新启动 300 轮无早停长跑并继续监控 `evaluation_failed=True`、`simulated=True` 和内存 |

### 2026-04-29 07:02 - 策略 multi_asset/signal 别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免长跑中 LLM 候选输出 `strategy_mode=multi_asset`、`selection_rule=signal` 时被 schema 跳过 |
| 触发来源 | 300 轮无早停长跑中出现 `[StrategyAgent] Skipping LLM candidate 'sharpe_acceleration_zscore_multi'`，错误为 `multi_asset/signal` 不在枚举 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造真实候选 `template_name=sharpe_acceleration_zscore_multi, strategy_mode=multi_asset, selection_rule=signal`，旧逻辑无法归一化 |
| 修改摘要 | 将通用 `multi_asset/multi_instrument/portfolio/cross_asset` 模式按 hint 或市场默认归一化；将 `signal/signals/signal_based/factor_signal` selection rule 归一化为 `threshold` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，40 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2735 passed |
| 剩余风险 | LLM 仍可能创造新的策略族名或 selection rule；长跑继续按实际跳过日志补确定性别名 |
| 下一步 | 重启 300 轮无早停长跑并继续监控 StrategyAgent 跳过日志 |

### 2026-04-29 06:58 - 因子横截面算子参数与 rolling window 校验

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 `CSZScore(..., n)` 和动态 rolling window 表达式绕过 FactorAgent 校验后在后端计算阶段失败 |
| 触发来源 | 300 轮无早停长跑中，基本面套利专家出现 `CSZScore() takes 1 positional argument but 2 were given`，导致 `evaluation_failed=True` |
| 涉及模块 | `agents/factor_agent.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 使用真实失败表达式本地校验；旧逻辑会让 `CSZScore(x, 3)` 和 `Mean(x, Sub(...))` 进入后端，后端才报错 |
| 修改摘要 | AST 修复阶段将 `CSZScore/GroupNeutral/Percentile(x, n)` 裁剪为单参数；校验阶段强制一元横截面/数学算子参数数正确，并要求 `Mean/Std/Sum/Ref/Delta/Ts_*`、`Corr/Cov/Ts_Percentile` 的窗口参数为常量整数 |
| 验证命令 | `python -m py_compile agents/factor_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，13 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2734 passed |
| 剩余风险 | 动态窗口错误现在会反馈给 LLM 重试；若 LLM 连续给出无法修复的结构，仍会被标记为无效轮次，但不会再进入后端才失败 |
| 下一步 | 重启 300 轮无早停长跑并继续观察是否还有最终 `evaluation_failed=True` |

### 2026-04-29 06:53 - 因子 If 指示函数缺参修复

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免长跑中 LLM 将条件指示函数写成 `If(cond)` 或 `If(cond, value)` 时，最终进入 `evaluation_failed=True` |
| 触发来源 | 300 轮无早停长跑中，统计套利专家出现 `Operator 'If' requires 3 arguments, but got 1`，后端评估被跳过 |
| 涉及模块 | `agents/factor_agent.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 构造 `Sum(If(Greater($close, Ref($close, 1))), 20)` 与 `Sum(If(Greater($close, Ref($close, 1)), $volume), 20)`，旧逻辑只能让 LLM 重试 |
| 修改摘要 | AST 修复阶段将 `If(cond)` 归一为 `If(cond, 1, 0)`，将 `If(cond, value)` 归一为 `If(cond, value, 0)`；合法三参数 If 不变，修复后仍经过白名单、签名检查和 dry-run |
| 验证命令 | `python -m py_compile agents/factor_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，10 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2731 passed |
| 剩余风险 | 如果 LLM 生成的 `If` 条件本身不是布尔比较，修复只保证语法可执行，不保证该因子有研究价值；真实长跑继续监控 |
| 下一步 | 重启 300 轮无早停长跑并继续观察是否还有最终 `evaluation_failed=True` |

### 2026-04-29 06:44 - 因子尾部多余括号本地修复

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免长跑中 LLM 生成尾部多余右括号时，因子连续重试后仍进入 `evaluation_failed=True` |
| 触发来源 | 300 轮无早停长跑中，动量专家出现 `Unbalanced parentheses: extra closing ')'`，后端评估被跳过 |
| 涉及模块 | `agents/factor_agent.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 构造 `Rank($close))`，旧逻辑只修缺失右括号，不会裁剪尾部多余右括号 |
| 修改摘要 | 新增保守括号修复：缺右括号仍只在无额外右括号时补齐；尾部连续多余右括号仅在裁掉后表达式重新平衡时修复；中间位置多余右括号保持失败 |
| 验证命令 | `python -m py_compile agents/factor_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，8 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2729 passed |
| 剩余风险 | 如果 LLM 在表达式中间插入多余括号，仍会失败并计为无效轮次；这是有意保守，避免误改表达式语义 |
| 下一步 | 重启 300 轮无早停长跑并继续观察是否还有最终 `evaluation_failed=True` |

### 2026-04-29 06:26 - 策略模式 continuous/single leg 归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免长跑中 LLM 生成 `strategy_mode=continuous/single_short/single_long` 时策略候选被严格 schema 跳过 |
| 触发来源 | 300 轮无早停长跑中出现 `[StrategyAgent] Skipping LLM candidate 'ts_continuous_signal'`，错误为 `strategy_mode input_value='continuous'` |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `template_name=ts_continuous_signal, strategy_mode=continuous` 与 `strategy_mode=single_short` 的候选，旧逻辑无法归一化到合法 `time_series/cross_sectional` |
| 修改摘要 | `ts_/cs_` 模板名前缀可作为模式 hint；`continuous`、`continuous_signal`、`single_long`、`single_short` 等策略模式按市场默认归一化；`continuous_signal` selection rule 归一化为 `threshold` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，39 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2728 passed |
| 剩余风险 | LLM 仍可能产生新的自由文本枚举；长跑中继续按实际跳过日志补确定性别名 |
| 下一步 | 重启 300 轮无早停长跑并继续监控内存与策略候选校验 |

### 2026-04-29 05:56 - 因子一元 Sub 与 Rank 参数本地修复

| 字段 | 内容 |
| --- | --- |
| 目标 | 降低长跑中 LLM 生成 `Sub(x)` 或 ricequant `Rank(x, n)` 导致无效因子、空指标轮次的概率 |
| 触发来源 | 300 轮无早停长跑中，波动率专家再次出现 `evaluation_failed=True`，错误为 `Operator 'Sub' requires at least 2 arguments, but got 1` |
| 涉及模块 | `agents/factor_agent.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 构造 `Rank(Sub($close))` 与 `Rank(Mean($close, 20), 20)`，旧逻辑只能反馈给 LLM 重试，连续重试失败会跳过后端评估 |
| 修改摘要 | 新增 AST 级本地 arity 修复：`Sub/Minus/Subtract(x)` 转 `Neg(x)`；ricequant 后端下 `Rank/CSRank(x, n)` 去掉误传窗口；修复后仍经过白名单、签名检查和 dry-run |
| 验证命令 | `python -m py_compile agents/factor_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，7 passed |
| 验证命令 | `pytest -q tests/unit/test_agent_workflow_regressions.py tests/unit/test_factor_agent_json.py tests/unit/test_settings.py tests/test_early_stopping.py` |
| 验证结果 | 通过，39 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2727 passed |
| 验证命令 | `git diff --check -- agents/factor_agent.py tests/unit/test_factor_agent_json.py` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它缺参算子如 `Div(x)` 不做猜测性修复，仍会进入安全失败路径；长跑继续观察是否需要补更多确定性归一化 |
| 下一步 | 清理内存后重启 300 轮无早停长跑 |

### 2026-04-29 05:14 - 策略 threshold 模式归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode=threshold` 且模板名无时间序列提示时策略候选被全部跳过 |
| 触发来源 | 关闭早停长跑中，`volume_volatility_order_v1/v2/v3` 因 `strategy_mode=threshold` 未归一化触发模板兜底 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `template_name=volume_volatility_order_v1`、`strategy_mode=threshold`、`selection_rule=threshold` 的期货候选，旧逻辑将 `threshold` 原样传入 `StrategyConfig.strategy_mode` |
| 修改摘要 | 将裸 `threshold/threshold_strategy/threshold_based` 视为按市场默认的阈值策略：期货归一为 `time_series`，股票归一为 `cross_sectional`，仍允许模板 hint 覆盖 |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，38 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2724 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它 LLM 自造的 `strategy_mode` 别名仍需长跑继续捕获 |
| 下一步 | 验证通过后清理 worker 并重启 300 轮无早停长跑 |

### 2026-04-29 05:06 - 策略 quantile_threshold 选择规则归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `selection_rule=quantile_threshold` 时策略候选被跳过 |
| 触发来源 | 关闭早停长跑中，统计套利专家 `cross_sectional_quantile` 候选因 `quantile_threshold` 未归一化失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=cross_sectional`、`selection_rule=quantile_threshold`、带 0.8/0.2 阈值的策略候选，旧逻辑将别名原样传入 `StrategyConfig.selection_rule` |
| 修改摘要 | 将 `quantile_threshold/percentile_threshold/cs_quantile_threshold/cross_sectional_percentile_threshold` 等别名归一为 `threshold` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，37 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2723 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它 selection_rule 命名仍需长跑继续捕获 |
| 下一步 | 验证通过后清理 worker 并重启 300 轮无早停长跑 |

### 2026-04-29 05:00 - 策略 single_leg/dual_leg 模式归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode=single_leg/dual_leg` 时全部策略候选被跳过并回退模板 |
| 触发来源 | 关闭早停长跑中，基本面套利专家 3 个策略候选因 `single_leg`、`dual_leg` 不属于 `StrategyConfig.strategy_mode` 失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `Long_on_high_alignment_momentum`/`Long_short_alignment_momentum` 候选，旧逻辑将 `single_leg/dual_leg` 原样传入严格 schema |
| 修改摘要 | 将 `single_leg/one_leg/dual_leg/two_leg` 等策略形态别名按模板提示或市场默认归一到 `time_series/cross_sectional` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，36 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2722 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它非枚举 strategy_mode 文案仍需长跑继续捕获 |
| 下一步 | 验证通过后清理 worker 并重启 300 轮无早停长跑 |

### 2026-04-29 04:55 - 因子表达式缺失右括号本地修复

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 生成仅缺少末尾右括号的 Qlib 表达式在 2 次重试后仍失败并浪费迭代 |
| 触发来源 | 关闭早停长跑中，波动率专家因子表达式连续报 `Unbalanced parentheses: 2 unclosed '('`，最终被标记 evaluation_failed |
| 涉及模块 | `agents/factor_agent.py`，`tests/unit/test_factor_agent_json.py` |
| 复现方式 | 构造 `Rank(Mul($close, Ref($close, 1))`，旧逻辑只报未闭合括号并依赖 LLM 重试 |
| 修改摘要 | 增加本地 `_repair_unclosed_parentheses`，仅在没有多余右括号且只缺末尾右括号时补齐；补齐后仍走原有 AST/operator/dry-run 验证 |
| 验证命令 | `python -m py_compile agents/factor_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py tests/unit/test_agent_workflow_regressions.py` |
| 验证结果 | 通过，16 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2721 passed |
| 验证命令 | `git diff --check -- agents/factor_agent.py tests/unit/test_factor_agent_json.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 非括号类语法错误仍需 LLM 自修或被失败迭代兜底 |
| 下一步 | 验证通过后清理 worker 并重启 300 轮无早停长跑 |

### 2026-04-29 04:45 - 策略比例型 counts 解析归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 在 `counts` 中输出 `quantile_long=0.2`、`quantile_short=0.2` 时整批策略解析失败并退回模板 |
| 触发来源 | 关闭早停长跑中，动量专家 `StrategyProposalBatchOutput` 因 counts 浮点比例不满足 `Dict[str, int]` 直接 validation error |
| 涉及模块 | `schemas/messages.py`，`agents/strategy_agent.py`，`tests/unit/test_strategy_output_schema.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造包含 `counts={"quantile_long": 0.2, "quantile_short": 0.2}` 的策略候选，旧 schema 在 batch parse 阶段失败，无法进入候选归一化 |
| 修改摘要 | `StrategyCandidateOutput.counts` 接受整数或浮点；策略归一化将比例型 quantile count alias 转成 `long_threshold/short_threshold`，并在缺少 top/bottom 绝对数量时切换为 `threshold` 选择规则 |
| 验证命令 | `python -m py_compile schemas/messages.py agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，41 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2719 passed |
| 验证命令 | `git diff --check -- schemas/messages.py agents/strategy_agent.py tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它比例别名或自然语言 selection/count 组合仍需长跑继续捕获 |
| 下一步 | 验证通过后清理 worker 并重启 300 轮无早停长跑 |

### 2026-04-29 04:41 - 策略描述型 long/short 方向归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `long_on_positive_signal_short_on_negative` 等描述型 direction 时全部候选被跳过 |
| 触发来源 | 关闭早停长跑中，动量专家策略候选因 3 个描述型 long/short direction 未归一化失败并退回模板 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `direction=long_on_positive_signal_short_on_negative/long_top_decile_short_bottom_decile/long_on_high_signal_short_on_low` 的候选，旧逻辑会把原字符串传入 `StrategyConfig.direction` |
| 修改摘要 | 当 direction token 同时包含 `long` 和 `short` 时归一为 `long_short`，覆盖描述型双边交易文案 |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，34 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2717 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它自然语言 direction 仍需长跑继续捕获 |
| 下一步 | 验证通过后清理 worker 并重启 300 轮无早停长跑 |

### 2026-04-29 04:32 - 策略 rank_threshold 选择规则归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `selection_rule=rank_threshold` 时策略候选被跳过 |
| 触发来源 | 关闭早停长跑中，波动率专家候选 `futures_cross_sectional_rank` 因 `rank_threshold` 未归一化失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=cross_sectional`、`selection_rule=rank_threshold`、带 rank 阈值的策略候选，旧逻辑将 `rank_threshold` 原样传入 `StrategyConfig.selection_rule` |
| 修改摘要 | 将 `rank_threshold/rank_signal_threshold/cs_rank_threshold/cross_sectional_rank_threshold` 等别名归一为 `threshold` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，33 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2716 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它 selection_rule 命名仍需长跑继续捕获 |
| 下一步 | 完成验证后重启 300 轮无早停长跑 |

### 2026-04-29 04:28 - 策略 contrarian 方向归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `direction=contrarian` 时策略候选全部失败并回退模板 |
| 触发来源 | 关闭早停长跑中，波动率专家 3 个 `MeanReversion_VolumePrice_*` 候选均因 `contrarian` 未归一化失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=time_series`、`direction=contrarian`、`selection_rule=threshold` 候选，旧逻辑将 `contrarian` 原样传入 `StrategyConfig.direction` |
| 修改摘要 | 将 `contrarian/mean_reversion/reversal/counter_trend` 等反向策略方向别名归一为 `long_short` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，32 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2715 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它方向语义词仍可能需要通过长跑日志继续补齐 |
| 下一步 | 完成验证后重启 300 轮无早停长跑 |

### 2026-04-29 04:21 - 策略 biweek 调仓频率归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `rebalance_freq=biweek` 时策略候选被跳过 |
| 触发来源 | 关闭早停长跑中，基本面套利策略候选 `future_cross_sectional_quantile_neutral` 因 `biweek` 不属于 `daily/weekly/monthly` 失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `rebalance_freq=biweek` 的策略候选，旧逻辑未将其归一化为 `weekly` |
| 修改摘要 | 将 `biweek/bi_week/fortnight/fortnightly/2_weeks/two_weeks` 等两周频率别名归一到当前支持的 `weekly` 档 |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，31 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2714 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它非标准频率别名仍需长跑中继续捕获 |
| 下一步 | 完成验证后重启 300 轮无早停长跑 |

### 2026-04-29 04:10 - 无效因子语法跳过后端评估

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 FactorAgent 语法修复失败后仍把坏表达式送入本地 RiceQuant 评估链路 |
| 触发来源 | 关闭早停长跑中，统计套利专家输出括号不闭合表达式，后端报 `(` was never closed 并产生失败评估记录 |
| 涉及模块 | `agents/factor_agent.py`，`agents/eval_agent.py`，`app_workflow/state.py`，`app_workflow/graph.py`，`tests/unit/test_agent_workflow_regressions.py` |
| 复现方式 | 构造 `is_valid_syntax=False` 且 `syntax_error=parentheses are not balanced` 的状态；旧逻辑仍调用 `_execute_alphaeval_backtest` |
| 修改摘要 | FactorAgent 记录最终语法错误；EvalAgent 对无效语法直接返回真实失败零指标并跳过 evaluator；迭代递增时清理语法和评估失败标记 |
| 验证命令 | `python -m py_compile agents/factor_agent.py agents/eval_agent.py app_workflow/graph.py app_workflow/state.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_agent_workflow_regressions.py` |
| 验证结果 | 通过，12 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2713 passed |
| 验证命令 | `git diff --check -- agents/factor_agent.py agents/eval_agent.py app_workflow/state.py app_workflow/graph.py tests/unit/test_agent_workflow_regressions.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 语法失败仍会计入无产出迭代；长跑会继续观察是否还存在其它 LLM 输出 schema/算子别名问题 |
| 下一步 | 完成验证后重启 300 轮无早停长跑 |

### 2026-04-29 03:59 - 策略字符串数字方向归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `direction="-1"` 时单个策略候选被跳过 |
| 触发来源 | 关闭早停长跑第 2 次重启中，统计套利专家候选 `trend_short_low_factor` 因字符串 `-1` 未归一化失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=time_series_momentum`、`direction="-1"`、`selection_rule=threshold` 候选，旧逻辑将 `-1` 原样传入 `StrategyConfig.direction` |
| 修改摘要 | 在方向归一化中显式识别字符串 `+1/1.0/-1/-1.0` 为双边 `long_short`，保留既有数字 `0` 到 `long_flat/long_only` 行为 |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，30 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2711 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它字符串编码方向仍可能需要通过长跑日志继续补齐 |
| 下一步 | 跑单测和 unit 后重启 300 轮无早停长跑 |

### 2026-04-29 03:55 - 策略 time_series 前缀与 absolute_threshold 归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode=time_series_mean_reversion/time_series_momentum` 与 `selection_rule=absolute_threshold` 时整批策略候选 fallback |
| 触发来源 | 关闭早停长跑第 1 轮，统计套利专家 3 个候选因上述组合无法通过 `StrategyConfig` 校验 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `Volume_Price_Correlation_*_TS` 候选，旧逻辑不识别 `time_series_*` 模式前缀，也不识别 `absolute_threshold` selection rule |
| 修改摘要 | 将 `time_series* / timeseries* / ts_*` 归一化为 `time_series`；将 `cross_sectional* / cross_section* / cs_*` 归一化为 `cross_sectional`；将 `absolute_threshold*` 归一化为 `threshold` |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，29 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2710 passed |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 其它 LLM 自由文本策略模式仍可能需要继续通过长跑日志扩充别名 |
| 下一步 | 跑单测和 unit 后重启 300 轮无早停长跑 |

### 2026-04-29 01:00 - Swarm 支持显式关闭早停

| 字段 | 内容 |
| --- | --- |
| 目标 | 支持用户要求“早停也要接着跑”，让研究流程可跑满 `--iterations` |
| 触发来源 | 用户要求用本地期货后端持续运行 300 轮，且即使早停条件满足也继续 |
| 涉及模块 | `manager.py`，`sub_agent.py`，`core/settings.py`，`app_workflow/graph.py`，`app_workflow/state.py`，`tests/test_early_stopping.py`，`tests/unit/test_settings.py` |
| 复现方式 | 旧逻辑在 `current_ic >= 0.05` 或 `patience_counter >= 4` 时直接返回 `end`，没有 CLI/配置可关闭 |
| 修改摘要 | 新增 `--disable-early-stop` 与 `AIMINER_DISABLE_EARLY_STOP=1`；该开关传入子 agent state 后跳过高 IC 和 patience 早停，但仍遵守 `max_iterations` |
| 验证命令 | `python -m py_compile manager.py sub_agent.py core/settings.py app_workflow/graph.py app_workflow/state.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/test_early_stopping.py tests/unit/test_settings.py` |
| 验证结果 | 通过，20 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2709 passed |
| 验证命令 | `git diff --check -- manager.py sub_agent.py core/settings.py app_workflow/graph.py app_workflow/state.py tests/test_early_stopping.py tests/unit/test_settings.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 300 轮无早停耗时显著高于 2000 秒，需要本次运行把全局 timeout 调大，否则会被超时机制截断 |
| 下一步 | 跑语法和目标单测后，用 `--disable-early-stop` 启动用户命令并持续监控 |

### 2026-04-29 00:21 - 策略 mode 使用 template_name 兜底推断

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 将 `strategy_mode=threshold` 等执行规则词误填为模式时整批策略候选 fallback |
| 触发来源 | 用户命令重跑中，基本面套利专家三个 `time_series_*` 候选因 `strategy_mode=threshold` 非法全部失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `template_name=time_series_fixed_threshold`、`strategy_mode=threshold` 的候选，旧逻辑无法从模板名恢复为 `time_series` |
| 修改摘要 | 对未识别的 `strategy_mode`，若 `template_name` 明确包含 `time_series` 或 `cross_sectional`，用该提示兜底推断模式 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，28 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2708 passed |
| 剩余风险 | 只有模板名明确含 time_series/cross_sectional 时才兜底，其他自由文本仍会按未知值暴露 |
| 下一步 | 跑单测后重启用户命令 |

### 2026-04-29 00:16 - 策略 both_legs 方向别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `direction=both_legs` 时单个策略候选被跳过 |
| 触发来源 | 用户命令重跑中，波动率专家候选 `VolRatio_TZ_LongShort` 因 `both_legs` 非法被跳过 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=time_series`、`direction=both_legs`、`selection_rule=threshold` 的候选，旧逻辑保留原字符串并触发 `StrategyConfig.direction` 校验失败 |
| 修改摘要 | 将 `both_legs/both_leg/both_sides` 归一化为 `long_short` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，27 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2707 passed |
| 剩余风险 | LLM 仍可能输出新的双边交易短语，需要继续通过真实长跑日志扩充别名表 |
| 下一步 | 跑单测后重启用户命令 |

### 2026-04-29 00:01 - 策略 top_long 方向别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `direction=top_long_bottom_short/top_long_only` 时策略候选整批 fallback |
| 触发来源 | 用户命令重跑第 1 轮，动量专家 3 个策略候选因上述 direction 非法被跳过 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `top_long_bottom_short` 和 `top_long_only` 候选，旧逻辑未命中方向别名并触发 `StrategyConfig.direction` 校验失败 |
| 修改摘要 | 将 `top_long_bottom_short/top_long_short_bottom/long_top_bottom_short` 归一化为 `long_short`；将 `top_long_only/long_top_only/top_only_long` 归一化为单边做多 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，26 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2706 passed |
| 剩余风险 | LLM 仍可能输出新的 top/bottom 自然语言方向短语，需要继续通过真实长跑日志扩充别名表 |
| 下一步 | 跑单测后重启用户命令，确认不再整批 fallback |

### 2026-04-28 23:57 - PortfolioAgent DeepSeek response_format 降级

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 DeepSeek 不支持结构化 `response_format` 时组合方法选择阶段记录 ERROR |
| 触发来源 | 用户命令完整跑完后，`PortfolioAgent` 选择组合方法报 `This response_format type is unavailable now`，随后虽 fallback 到 risk_parity 但日志为 ERROR |
| 涉及模块 | `agents/portfolio_agent.py`，`tests/unit/test_portfolio_agent.py` |
| 复现方式 | 构造 DeepSeek provider 或结构化 LLM invoke 抛出 response_format 错误，旧逻辑只捕获外层异常并记录 ERROR |
| 修改摘要 | DeepSeek 直接使用普通 JSON 回复解析；其他 provider 结构化调用失败时自动重试普通 JSON；最终兜底日志降为 warning |
| 验证命令 | `pytest -q tests/unit/test_portfolio_agent.py` |
| 验证结果 | 通过，4 passed |
| 验证命令 | `python -m py_compile agents/portfolio_agent.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2705 passed |
| 剩余风险 | 普通 JSON 回复若被模型严重污染仍会回退 risk_parity，但不会阻断主流程 |
| 下一步 | 跑单测后重启用户命令，确认最终组合阶段不再出现 ERROR |

### 2026-04-28 23:31 - 策略 rank_based 模式别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode=rank_based` 时截面 rank 策略候选被跳过 |
| 触发来源 | 用户命令真实运行中，`futures_cross_sectional_rank` 候选因 `rank_based` 非法被跳过 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=rank_based`、`selection_rule=cross_sectional_rank` 的候选，旧逻辑保持原字符串并触发 Pydantic literal 校验失败 |
| 修改摘要 | 将 `rank_based/rank_based_strategy/rank_strategy` 归一化为 `cross_sectional` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，25 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2703 passed |
| 剩余风险 | LLM 仍可能输出新的 rank 家族短语，需要继续通过真实长跑日志扩充别名表 |
| 下一步 | 跑单测和用户命令，继续观察参数漂移 |

### 2026-04-28 23:23 - 策略 single_asset 模式别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode=single_asset` 时整批策略候选被跳过并回退模板 |
| 触发来源 | 用户命令真实运行中，三个 `momentum_acceleration_ts*` 候选因 `single_asset` 非法而全部失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=single_asset`、`direction=bidirectional` 的时序策略候选，旧逻辑保持原字符串并触发 Pydantic literal 校验失败 |
| 修改摘要 | 将 `single_asset/single_asset_strategy/single_asset_time_series/single_instrument/single_contract` 归一化为 `time_series` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，24 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2702 passed |
| 剩余风险 | LLM 仍可能输出新的执行域短语，需要继续通过真实长跑日志扩充别名表 |
| 下一步 | 跑单测和用户命令，继续观察参数漂移 |

### 2026-04-28 23:16 - 策略双向方向别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `direction=bidirectional` 时策略候选被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `direction=bidirectional` 不符合 `StrategyConfig.direction` 枚举 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `direction=bidirectional` 的 CTA 策略候选，旧逻辑保持原字符串并触发 Pydantic literal 校验失败 |
| 修改摘要 | 将 `bidirectional/bi_directional/both_directions/two_way/two_way_directional/long_short_both` 归一化为 `long_short` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，23 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2701 passed |
| 剩余风险 | LLM 仍可能输出新的方向短语，需要继续通过真实长跑日志扩充别名表 |
| 下一步 | 跑单测和用户命令，继续观察参数漂移 |

### 2026-04-28 23:07 - 策略 CTA/Alpha 模式别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `strategy_mode=CTA/Alpha` 时策略候选被跳过并退回模板 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `CTA` 和 `Alpha` 不符合 `StrategyConfig.strategy_mode` 枚举 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `CTA` 和 `Alpha` 候选，旧逻辑保持原字符串并触发 Pydantic literal 校验失败 |
| 修改摘要 | 将 `CTA/cta_strategy/managed_futures` 归一化为 `time_series`，将 `Alpha/alpha_strategy/cross_sectional_alpha/alpha_long_short` 归一化为 `cross_sectional` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，22 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2700 passed |
| 剩余风险 | LLM 仍可能输出新的策略家族名，需要继续用真实长跑日志扩充别名表 |
| 下一步 | 跑单测和用户命令，继续观察参数漂移 |

### 2026-04-28 22:51 - 策略时间序列分位选择别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 输出 `time_series_percentile/time_series_top_decile` 等选择规则时策略候选被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `selection_rule=time_series_percentile` 和 `time_series_top_decile` 非法 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 selection_rule 为时间序列分位/decile 的候选，旧逻辑在非 time_series mode 下保留原字符串 |
| 修改摘要 | 将 time-series/absolute percentile、quantile、top/bottom decile 别名统一归一化为 `threshold` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，21 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2699 passed |
| 剩余风险 | 分位阈值仍映射到默认 0.75/0.25 或 0.6/0.45，若需精确 decile 需扩展阈值推断 |
| 下一步 | 跑单测和用户命令，继续观察策略候选漂移 |

### 2026-04-28 22:48 - 策略数值字典丢弃文本条件

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 在 `thresholds` 等数值字典中混入文本条件导致整批策略候选校验失败 |
| 触发来源 | 用户命令真实运行中，`thresholds.additional_long_confirmation='close > sma20'` 导致 `StrategyProposalBatchOutput` 校验失败 |
| 涉及模块 | `schemas/messages.py`，`tests/unit/test_strategy_output_schema.py` |
| 复现方式 | 构造 `thresholds` 含数值字符串和文本表达式的策略候选，旧 schema 会保留文本并在 `Dict[str,float]` 解析时报错 |
| 修改摘要 | 所有策略数值字典预清洗时只保留有限数值和数值字符串，丢弃文本条件、嵌套结构和空值 |
| 验证命令 | `pytest -q tests/unit/test_strategy_output_schema.py` |
| 验证结果 | 通过，5 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2698 passed |
| 剩余风险 | 文本型确认条件会被丢弃；如果未来要支持它，应新增显式 schema 字段而不是塞进 `thresholds` |
| 下一步 | 跑单测和用户命令，继续观察实跑参数漂移 |

### 2026-04-28 22:42 - Wiki Chroma 503 重试与降级

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 Wiki/Chroma 临时 503 导致知识库写入和检索路径持续报错 |
| 触发来源 | 用户命令真实运行中，`core.hybrid_knowledge` 写 Wiki 报 `Error code: 503 in upsert`，随后 Wiki/RAG 查询也出现 503 |
| 涉及模块 | `core/wiki.py`，`tests/unit/test_wiki_resilience.py` |
| 复现方式 | 用测试 collection 模拟 upsert/query 首次或持续返回 503，旧逻辑无重试且 upsert 异常会冒泡到 HybridKnowledge |
| 修改摘要 | 为 Wiki Chroma count/query/upsert 增加短重试；upsert 最终失败时保留 Markdown 源文件并降级，不阻断主流程 |
| 验证命令 | `pytest -q tests/unit/test_wiki_resilience.py` |
| 验证结果 | 通过，2 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2697 passed |
| 剩余风险 | 外部 embedding/Chroma 服务长时间不可用时，语义索引仍可能滞后于 Markdown 源文件 |
| 下一步 | 跑单测和用户命令，继续观察 503 是否被平滑降级 |

### 2026-04-28 22:35 - 策略正负方向别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出裸 `direction=positive/negative` 时所有候选被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `positive/negative` 不符合 `StrategyConfig.direction` |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 time-series 候选，`direction=positive` 或 `direction=negative`，旧逻辑保留原字符串导致校验失败 |
| 修改摘要 | 将 `positive` 按高信号做多归一化；将 `negative` 按反向/做空侧归一化，避免回退模板吞掉 LLM 候选 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，20 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2695 passed |
| 剩余风险 | `positive` 的 long-only 与 long-short 语义仍依赖 selection rule 是否明确提到空头 |
| 下一步 | 跑单测和用户命令，继续捕获实跑参数漂移 |

### 2026-04-28 22:27 - 评估失败样本跳过 Wiki 更新

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免真实回测失败样本继续写入 Wiki/向量库并触发外部 upsert 参数错误 |
| 触发来源 | 用户命令真实运行中，因子语法修复失败后 `evaluation_failed=True`，随后 `HybridKnowledge` 写 Wiki 报 400 参数错误 |
| 涉及模块 | `app_workflow/graph.py`，`core/hybrid_knowledge.py`，`tests/unit/test_agent_workflow_regressions.py` |
| 复现方式 | 构造 `evaluation_failed=True` 或 `backtest_metrics._evaluation_failed=True` 的状态，旧逻辑仍会调用 `update_wiki_after_eval` |
| 修改摘要 | 在工作流 Wiki 节点和 `HybridKnowledge` 双层跳过评估失败样本；保留 checkpoint 尝试，避免失败样本进入知识库 |
| 验证命令 | `pytest -q tests/unit/test_agent_workflow_regressions.py` |
| 验证结果 | 通过，10 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2695 passed |
| 剩余风险 | 长跑仍依赖外部 LLM/embedding 服务稳定性，需重新执行用户命令观察 |
| 下一步 | 运行单测和用户命令，继续观察新运行错误 |

### 2026-04-28 22:18 - 策略中性方向别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `direction=neutral` 时候选被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `futures_factor_momentum_neutral` 因 `neutral` 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `direction=neutral` 的横截面候选，旧逻辑保留原字符串导致 `StrategyConfig` 校验失败 |
| 修改摘要 | 将 `neutral/market_neutral/factor_neutral/dollar_neutral/beta_neutral` 和中文“中性”归一化为 `long_short` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，20 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2693 passed |
| 剩余风险 | 若未来需要严格区分 market-neutral 和 dollar-neutral，需要扩展策略配置字段 |
| 下一步 | 运行单测和用户命令，继续观察新参数漂移 |

### 2026-04-28 22:15 - 策略高分做多方向别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `direction=long_high` 时候选被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `trend_volume_composite_long_only` 因 `long_high` 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `direction=long_high` 的横截面 long-only 候选，旧逻辑保留原字符串导致 `StrategyConfig` 校验失败 |
| 修改摘要 | 将 `long_high/high_long/long_top/top_long/long_positive/positive_long` 映射到横截面 `long_only`、时序 `long_flat` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，19 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2692 passed |
| 剩余风险 | 语义更复杂的“低分做多/高分做空”仍需独立别名映射 |
| 下一步 | 运行单测和用户命令，继续观察新参数漂移 |

### 2026-04-28 22:03 - 策略候选嵌套阈值字段清洗

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免单个候选在 `thresholds` 中输出嵌套字段导致整个 `StrategyProposalBatchOutput` 解析失败 |
| 触发来源 | 用户命令真实运行中，`thresholds.ma_periods={short:20,long:50}` 被 `Dict[str,float]` 拒绝并触发模板兜底 |
| 涉及模块 | `schemas/messages.py`，`tests/unit/test_strategy_output_schema.py` |
| 复现方式 | 构造 `thresholds`/`counts`/`holding_constraints`/`cost_model` 中包含嵌套 dict/list 的候选，旧 schema 在 batch 解析阶段失败 |
| 修改摘要 | optional dict 字段在 schema 前置校验中丢弃 `dict/list/tuple/set` 非标量值，保留可转换的标量交给后续严格清洗 |
| 验证命令 | `pytest -q tests/unit/test_strategy_output_schema.py` |
| 验证结果 | 通过，4 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2691 passed |
| 剩余风险 | 嵌套字段会被忽略而不是展开；如果未来需要支持结构化参数，需要扩展 `StrategyConfig` schema |
| 下一步 | 运行单测和用户命令，继续观察新参数漂移 |

### 2026-04-28 21:57 - 策略横截面 rank 选择规则归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `selection_rule=cross_sectional_rank` 时候选被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示候选 `cross_sectional_rank` 因 selection_rule 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `selection_rule=cross_sectional_rank` 的横截面 long-short 候选，旧逻辑未命中 `rank/ranking` 别名 |
| 修改摘要 | 将 `cross_sectional_rank/cross_sectional_ranking/cs_rank/cs_ranking/rank_cross_sectional` 等别名映射到横截面 `top_bottom_n`，时序仍按 threshold 处理 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，18 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2690 passed |
| 剩余风险 | 若 LLM 用完整自然语言描述 rank 规则，仍可能需要补自然语言关键词 |
| 下一步 | 运行单测和用户命令，继续观察新参数漂移 |

### 2026-04-28 21:50 - 策略因子方向别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `direction=factor_long` 时所有候选被跳过并回退模板 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 3 个候选因 `factor_long` 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `direction=factor_long/factor_short/factor_long_short` 的候选，旧逻辑保留原字符串导致 `StrategyConfig` 校验失败 |
| 修改摘要 | 将 `factor_long` 映射到横截面 `long_only`、时序 `long_flat`，将 `factor_short` 和 `factor_long_short` 映射到现有可表达的 `long_short` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，17 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2689 passed |
| 剩余风险 | 反向-only 目前没有独立 schema 枚举，只能用 `long_short` 表达反向可交易语义 |
| 下一步 | 运行单测和用户命令，继续观察新参数漂移 |

### 2026-04-28 21:45 - 策略交易日调仓频率归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `rebalance_freq=20_trading_days` 时被严格枚举校验跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示两个候选因 `20_trading_days` 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `rebalance_freq=1_trading_day/5_trading_days/20_trading_days` 的候选，旧逻辑保留原字符串导致 `StrategyConfig` 校验失败 |
| 修改摘要 | 增加交易日/业务日/bar 周期别名归一化：1-3 日映射 daily，4-10 日映射 weekly，10 日以上映射 monthly |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，16 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2688 passed |
| 剩余风险 | 极端自定义周期只能压缩到当前 schema 支持的 daily/weekly/monthly 三档 |
| 下一步 | 运行单测和用户命令，继续观察新参数漂移 |

### 2026-04-28 21:42 - 策略 top/bottom 指标别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `selection_rule=top_volume` 等按指标取 top/bottom 的规则名时被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `cs_volume_price_corr_rank_momentum` 因 `top_volume` 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `selection_rule=top_volume` 的 cross-sectional long-only 候选，旧逻辑未命中 top/percent 规则并保留原字符串 |
| 修改摘要 | 在 selection_rule 归一化中增加 `top_* -> top_n`、`bottom_* -> bottom_n` 兜底，同时保留 time_series 下转 threshold 的既有语义 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，15 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2687 passed |
| 剩余风险 | 若 LLM 使用非 top/bottom 前缀的自然语言字段，仍可能需要新增映射 |
| 下一步 | 重新运行用户命令，继续观察策略候选跳过情况 |

### 2026-04-28 21:32 - 策略 top/bottom percent 别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `selection_rule=top_bottom_percent` 时被跳过 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `CV_stability_rank_CS` 因 `top_bottom_percent` 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 cross-sectional long/short 候选，`selection_rule=top_bottom_percent` 且 counts 为空；旧逻辑未归一化导致 `StrategyConfig` validation error |
| 修改摘要 | 泛化 selection_rule 归一化：包含 top+bottom 的 percent/quantile/pct/bucket 类别映射为 `top_bottom_n`，top-only/bottom-only 映射为对应桶规则 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，14 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2686 passed |
| 剩余风险 | LLM 仍可能创造新的自然语言规则描述；目前覆盖已在真实运行中出现的 top/bottom percent 变体 |
| 下一步 | 重新运行用户命令，确认策略阶段不再跳过该候选 |

### 2026-04-28 21:25 - 策略 selection_rule percentile 别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `selection_rule=cross_sectional_percentile` 时被 `StrategyConfig` 拒绝并跳过候选 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `futures_cross_sectional_vol_price_rank` 因 selection_rule 非法被 skipped |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode=cross_sectional`、`direction=long_short`、`selection_rule=cross_sectional_percentile` 的策略候选，旧逻辑保留原字符串导致校验失败 |
| 修改摘要 | 将 `cross_sectional_percentile/cross_sectional_quantile/cs_percentile/cs_quantile/rank_percentile/rank_quantile` 等别名归一化为合法 `threshold` 策略，并补充默认阈值回归测试 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，13 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2685 passed |
| 剩余风险 | percentile 选股也可能应表达为 top/bottom 桶；当前按已有 cross-sectional threshold 模板落地，保证候选不丢失 |
| 下一步 | 重新运行用户命令，确认策略候选不再因 percentile selection_rule 被跳过 |

### 2026-04-28 21:18 - 策略 direction 数值枚举预处理

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免 LLM 策略输出 `direction=0/1` 时，在进入候选归一化前被 Pydantic schema 拒绝并触发模板 fallback |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `StrategyProposalBatchOutput` 因 `direction` 为 int 失败，导致 LLM 候选未被评估 |
| 涉及模块 | `schemas/messages.py`，`agents/strategy_agent.py`，`tests/unit/test_strategy_output_schema.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 JSON 中 `direction=0/1`、其他枚举字段为数字的策略候选；旧 schema 直接报 `string_type` 校验错误 |
| 修改摘要 | Strategy candidate schema 对标量文本字段做安全字符串化；策略归一化支持 `1 -> long_short`、`0 -> time_series long_flat / cross_sectional long_only`；修复 token 化把 `0` 误当空值的问题 |
| 验证命令 | `pytest -q tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，15 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2684 passed |
| 剩余风险 | 数字方向的语义来自 LLM 输出习惯推断；如果后续出现不同编码规则，需要结合原始 candidate 再扩展映射 |
| 下一步 | 重新运行用户命令，确认策略阶段不再因数值 direction fallback |

### 2026-04-28 21:12 - 策略模式 multi_long_short 别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 避免长跑策略阶段把 LLM 生成的 `strategy_mode=multi_long_short` 当非法枚举跳过候选策略 |
| 触发来源 | 用户命令真实运行中，`StrategyAgent` 日志显示 `multi_long_short` 不符合 `cross_sectional|time_series`，导致 `futures_volume_efficiency_*` 候选被跳过 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造 `strategy_mode="multi_long_short"`、`selection_rule="top_bottom"` 的 futures 策略候选，旧逻辑无法通过 `StrategyConfig` 校验 |
| 修改摘要 | 将多品种/组合多空类 mode 别名归一化为 `cross_sectional`，并补充回归测试覆盖默认 top/bottom 数量填充 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py` |
| 验证结果 | 通过，11 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2682 passed |
| 剩余风险 | LLM 仍可能生成新的未见枚举别名；后续运行若出现新的跳过警告，应继续纳入归一化表 |
| 下一步 | 重新运行用户命令，确认策略候选不再因 `multi_long_short` 被跳过 |

### 2026-04-28 20:45 - Parallel swarm 超时 checkpoint 恢复

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复并行 300 轮长跑触发 `--swarm-global-timeout-seconds` 或末轮 LLM 连接失败后，Manager 丢弃已完成迭代结果的问题 |
| 触发来源 | 用户命令真实运行到 2000 秒全局超时，日志显示取消 4 个 pending agent，最终 `0 orthogonal factors found; 0 strategies evaluated`；重跑又发现已有有效 checkpoint 的 agent 因末轮 `Connection error` 被 Manager 拒绝 |
| 涉及模块 | `core/agent_result.py`，`core/agent_checkpoint.py`，`sub_agent.py`，`app_workflow/graph.py`，`manager.py`，`tests/unit/test_manager_strategy_eval.py`，`tests/unit/test_agent_workflow_regressions.py` |
| 复现方式 | 单测模拟 `ProcessPoolExecutor.as_completed` 抛出 `TimeoutError`，并预写当前 run 的 agent checkpoint；单测构造 best snapshot 后末轮 `Connection error` 的 final state |
| 修改摘要 | 抽出 agent result 组装逻辑；worker 每次 `wiki_update` 后把当前 best factor snapshot 写入 SQLite `agent_checkpoints`；Manager 并行超时或 final result 带 error 时用 checkpoint 恢复/替换；已有 best snapshot 的后续错误降级为 `terminal_error`，不再阻断该 best factor 入池 |
| 验证命令 | `pytest -q tests/unit/test_manager_strategy_eval.py::test_run_swarm_global_timeout_cancels_pending_agents tests/unit/test_manager_strategy_eval.py::test_run_swarm_timeout_recovers_agent_checkpoints tests/unit/test_agent_workflow_regressions.py::test_sub_agent_result_uses_best_snapshot_and_plot_paths` |
| 验证结果 | 通过，3 passed |
| 验证命令 | `pytest -q tests/unit/test_manager_strategy_eval.py tests/unit/test_agent_workflow_regressions.py tests/unit/test_rq_eval_metrics.py` |
| 验证结果 | 通过，23 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2681 passed |
| 剩余风险 | 原命令的 2000 秒仍不足以完整跑完每个 role 的 300 轮；该修复保证超时不丢中间最佳结果，但若目标是完整 300 轮，需要禁用或显著提高全局超时 |
| 下一步 | 重新运行用户命令，观察 checkpoint 恢复、最终报告和 SQLite 持久化 |

### 2026-04-28 19:37 - EvalAgent 禁止真实评估失败回退 simulated

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复 local/ricequant 长跑中表达式运行时错误后回退 simulated metrics，污染后续筛选和 Wiki 的问题 |
| 触发来源 | 真实重跑时 `Sqrt(Div(20,19))` 标量表达式触发 Pandas engine `'float' object has no attribute 'clip'`，随后 EvalAgent 使用 simulated metrics |
| 涉及模块 | `agents/eval_agent.py`，`core/alphaeval/rq_eval.py`，`tests/unit/test_agent_workflow_regressions.py`，`tests/unit/test_rq_eval_metrics.py` |
| 复现方式 | 单测复现评估器异常和 `Sqrt(Div(20,19))` 标量广播表达式 |
| 修改摘要 | Pandas factor engine 将标量算子输入广播为参考因子矩阵；EvalAgent 真实评估异常时返回 `evaluation_failed` 零指标，不再生成 simulated metrics，也不写 RAG/最优快照 |
| 验证命令 | `pytest -q tests/unit/test_agent_workflow_regressions.py::test_eval_backtest_failure_returns_failed_metrics_not_simulated tests/unit/test_rq_eval_metrics.py::test_pandas_factor_engine_broadcasts_scalar_math_operands` |
| 验证结果 | 通过，2 passed |
| 验证命令 | `pytest -q tests/unit/test_agent_workflow_regressions.py tests/unit/test_rq_eval_metrics.py tests/unit/test_manager_strategy_eval.py` |
| 验证结果 | 通过，20 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2678 passed |
| 剩余风险 | 需要重启真实长跑确认不再出现 simulated fallback；其他未见过的 LLM 算子组合仍可能触发真实失败指标 |
| 下一步 | 重启用户命令 |

### 2026-04-28 19:30 - Manager crossover 独立迭代上限

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复 4 角色并行 swarm 完成后，Genetic Crossover 误继承 `--iterations 300` 导致继续长时间运行的问题 |
| 触发来源 | 用户要求执行 local futures/ricequant 长跑；实测主 swarm 已完成并产出 4 个有效因子，但后续 crossover 在 2000 秒后仍继续第 10 轮 |
| 涉及模块 | `manager.py`，`tests/unit/test_manager_strategy_eval.py` |
| 复现方式 | 运行 `python manager.py --iterations 300 --mode ricequant --data-backend local ... --parallel --swarm-global-timeout-seconds 2000`，观察主 Agent 完成后 crossover 继续按 300 轮运行 |
| 修改摘要 | 新增 `--crossover-iterations` / `AIMINER_CROSSOVER_ITERATIONS`，默认 1；crossover Agent 显式使用独立上限，主 Agent 仍使用 `--iterations` |
| 验证命令 | `pytest -q tests/unit/test_manager_strategy_eval.py::test_run_swarm_crossover_uses_dedicated_iteration_cap` |
| 验证结果 | 通过，1 passed |
| 验证命令 | `pytest -q tests/unit/test_manager_strategy_eval.py tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_critic.py` |
| 验证结果 | 通过，35 passed |
| 验证命令 | `pytest -q tests/unit/test_parameter_matrix.py tests/unit/test_settings.py` |
| 验证结果 | 通过，2541 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，2676 passed |
| 剩余风险 | 需要重启真实长跑确认最终报告、SQLite 持久化和组合构建能在 crossover 结束后正常完成 |
| 下一步 | 重启用户命令观察到完整结束 |

### 2026-04-28 18:43 - StrategyAgent absolute_momentum 阈值别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复真实长跑中 `strategy_mode=absolute_momentum` 与 `selection_rule=by_thresholds` 导致所有 LLM 策略候选失败并 fallback 的问题 |
| 触发来源 | 4 角色 local futures swarm 在统计套利专家策略阶段输出 3 个 time-series momentum divergence 候选，均因该别名组合无法通过 `StrategyConfig` 校验 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 单测构造 `time_series_momentum_divergence_long_short/long_only` 候选，使用 `absolute_momentum` 和 `by_thresholds` |
| 修改摘要 | 将 absolute momentum/absolute thresholds 类策略模式映射为 futures time-series；将 `by_threshold(s)`、`thresholds`、`signal_thresholds` 等选择规则归一为 `threshold` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_critic.py` |
| 验证结果 | 24 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py agents/strategy_critic.py` |
| 验证结果 | 通过 |
| 剩余风险 | LLM 自由枚举仍可能继续产生新的同义词；长跑继续观察并补齐 |
| 下一步 | 重启同一组 local futures swarm，确认该类候选不再整批 fallback |

### 2026-04-28 18:32 - StrategyAgent RQ 频率和分位选择别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复长跑中 LLM 候选输出 `strategy_mode=absolute`、`selection_rule=top_quantile`、`rebalance_freq=W-MON/D/M`、负持仓约束时被策略校验跳过的问题 |
| 触发来源 | 4 角色 local futures swarm 真实日志中出现 `top_quantile` 选择规则校验失败，上一轮日志也出现 `absolute` 与 RQ/Pandas 频率别名导致整批 fallback |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 单测构造 absolute/time-series + top_quantile + W-MON，以及 ranking/cross-sectional + top_quantile + M，并带入负 `max_weight_per_position`/成本参数 |
| 修改摘要 | StrategyAgent 校验前将 absolute/absolute_threshold 归一为可执行模式；top/bottom quantile/percentile 映射到对应选择规则；`D/W-MON/M` 归一为 daily/weekly/monthly；非法持仓和成本约束清洗后使用默认值 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_critic.py` |
| 验证结果 | 23 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py agents/strategy_critic.py schemas/messages.py` |
| 验证结果 | 通过 |
| 剩余风险 | LLM 仍可能产生新的自由文本策略族名；长跑会继续用真实输出暴露并补齐 |
| 下一步 | 重启同一组 4 角色 300 轮 local futures swarm，继续观察是否还有策略候选整批 fallback 或硬异常 |

### 2026-04-28 18:15 - StrategyAgent 策略族名模式推断

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复真实 swarm 中 LLM 将 `price_volume_divergence`、`momentum_divergence`、`momentum` 等策略族名填入 `strategy_mode`，导致策略候选整批 fallback 的问题 |
| 触发来源 | 4 角色 local futures swarm 中基本面套利专家 3 个策略候选全部因 `strategy_mode` 不属于内部枚举而失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造真实日志中的 `template_name=futures_cross_sectional_long_short` + `strategy_mode=price_volume_divergence`，以及 `template_name=futures_time_series_historical_percentile` + `strategy_mode=momentum_divergence` |
| 修改摘要 | StrategyAgent 将常见策略族名视作可恢复别名，并优先从 `template_name` 推断 `cross_sectional` 或 `time_series`；`selection_rule=rank/ranking` 归一化为 cross-sectional 的 `top_bottom_n` 或 time-series 的 `threshold` |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_critic.py tests/unit/test_strategy_output_schema.py tests/unit/test_agent_workflow_regressions.py tests/unit/test_factor_agent_json.py` |
| 验证结果 | 30 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py agents/strategy_critic.py agents/eval_agent.py agents/factor_agent.py schemas/messages.py` |
| 验证结果 | 通过 |
| 验证命令 | `git diff --check -- agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py agents/eval_agent.py tests/unit/test_agent_workflow_regressions.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 仍可能出现新的任意策略族名；当前仅对真实日志和高频可推断别名做保守映射 |
| 下一步 | 重新执行 4 角色 300 轮 local futures swarm，确认该类策略候选不再整批 fallback |

### 2026-04-28 17:58 - EvalAgent review 空响应兜底

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复真实回测已完成后，EvalAgent 因 LLM review 返回空字符串导致 `ReflexiveReviewOutput` JSON 解析失败、子 agent 在 eval 节点报错的问题 |
| 触发来源 | 4 角色 local futures swarm 中动量专家第 3 轮真实回测完成后，review 阶段报 `Invalid JSON: EOF while parsing a value` |
| 涉及模块 | `agents/eval_agent.py`，`tests/unit/test_agent_workflow_regressions.py` |
| 复现方式 | 将 EvalAgent 的 review LLM 替换为空响应，同时让 `_execute_alphaeval_backtest` 返回真实指标 |
| 修改摘要 | EvalAgent review 解析失败或空响应时不再让节点失败，改用确定性指标评审兜底；真实 metrics、best snapshot、RAG/Wiki 后续链路继续保留 |
| 验证命令 | `pytest -q tests/unit/test_agent_workflow_regressions.py tests/unit/test_factor_agent_json.py tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_critic.py` |
| 验证结果 | 29 passed |
| 验证命令 | `python -m py_compile agents/eval_agent.py agents/factor_agent.py agents/strategy_agent.py agents/strategy_critic.py schemas/messages.py` |
| 验证结果 | 通过 |
| 验证命令 | `git diff --check -- agents/eval_agent.py tests/unit/test_agent_workflow_regressions.py agents/strategy_agent.py tests/unit/test_strategy_agent_normalization.py regression_log.md` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 兜底 review 只基于 IC、Rank IC、Sharpe、Drawdown 做保守判断，不替代 LLM 的细粒度研究建议 |
| 下一步 | 重新执行 4 角色 300 轮 local futures swarm，确认 review 空响应不再中断子 agent |

### 2026-04-28 17:51 - StrategyAgent compact longshort 别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复真实 swarm 中 LLM 输出 `strategy_mode=longshort`、`direction=long_and_short` 时策略候选整批校验失败并 fallback 到模板的问题 |
| 触发来源 | 4 角色 local futures swarm 运行中，基本面套利专家 3 个策略候选全部因 `strategy_mode='longshort'` 未归一化失败 |
| 涉及模块 | `agents/strategy_agent.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 用真实日志中的 `strategy_mode=longshort`、`direction=long_and_short` 构造 futures 策略候选 |
| 修改摘要 | 将 compact `longshort` 和 `long_and_short` 别名纳入策略模式/方向归一化；futures 下映射为 `time_series` + `long_short`，避免可恢复候选进入模板 fallback |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_critic.py tests/unit/test_strategy_output_schema.py` |
| 验证结果 | 21 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py agents/strategy_critic.py schemas/messages.py` |
| 验证结果 | 通过 |
| 剩余风险 | 需要重新跑同一 swarm 命令确认真实长跑不再出现该别名导致的整批 fallback；其他未知 LLM 枚举别名仍可能被跳过 |
| 下一步 | 重新执行 4 角色 300 轮 local futures swarm 并继续监控 StrategyAgent 日志 |

### 2026-04-28 17:40 - FactorAgent 非法反斜杠 JSON 容错

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复真实 swarm 中 FactorAgent 因 LLM 返回 LaTeX 单反斜杠导致 `Invalid \escape`，使子 agent 在 factor_agent 节点报错的问题 |
| 触发来源 | 本地 futures swarm 运行到第 2 轮时出现 `Unparseable LLM JSON response: Invalid \escape`；同时策略层又暴露 `long_high_short_low/top_n_and_bottom_n/statistical_arbitrage` 别名 |
| 涉及模块 | `agents/factor_agent.py`，`agents/strategy_agent.py`，`tests/unit/test_factor_agent_json.py`，`tests/unit/test_strategy_agent_normalization.py` |
| 复现方式 | 构造包含 `\max`、`\rho`、`\alpha` 等 JSON 非法转义的 LLM payload；构造 `direction=long_high_short_low`、`selection_rule=top_n_and_bottom_n` 的策略候选 |
| 修改摘要 | FactorAgent 解析 LLM JSON 时增加 string-aware 反斜杠修复，保留合法 `\"/\\/\/\uXXXX` 转义，修复 LaTeX 单反斜杠；策略候选归一化增加多空方向、top/bottom 组合和统计套利模式别名 |
| 验证命令 | `pytest -q tests/unit/test_factor_agent_json.py tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_critic.py tests/unit/test_agent_workflow_regressions.py` |
| 验证结果 | 27 passed |
| 验证命令 | `pytest -q tests/unit/test_parameter_matrix.py tests/unit/test_settings.py` |
| 验证结果 | 2541 passed |
| 验证命令 | `python -m py_compile agents/factor_agent.py agents/strategy_agent.py agents/strategy_critic.py schemas/messages.py` |
| 验证结果 | 通过 |
| 剩余风险 | 仍需重新完整跑 swarm；解析器只修复 JSON 字符串内非法反斜杠，若 LLM 返回截断 JSON 或缺必填字段仍会报错 |
| 下一步 | 重新执行 4 角色 300 轮 local futures swarm 并继续监控 FactorAgent/StrategyAgent |

### 2026-04-28 17:31 - 策略候选枚举别名归一化

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复真实 swarm 中 StrategyAgent 对 LLM 候选字段值过严，导致 `both/quantile/zscore/biweekly`、中文策略模式描述等可恢复别名全部被丢弃的问题 |
| 触发来源 | 重新跑本地 futures swarm 时，真实有效因子进入策略阶段后出现 `All LLM candidates failed StrategyConfig validation`，只能 fallback 到模板 |
| 涉及模块 | `agents/strategy_agent.py`，`agents/strategy_critic.py`，`tests/unit/test_strategy_agent_normalization.py`，`tests/unit/test_strategy_critic.py` |
| 复现方式 | 用真实日志中的别名构造候选：`direction=both`、`selection_rule=quantile/zscore/signal_threshold/all`、`rebalance_freq=biweekly`、`strategy_mode=趋势跟踪/signal/ranking`，以及 `bottom_n=0` |
| 修改摘要 | 在进入严格 `StrategyConfig` 前增加候选归一化：常见英文/中文枚举别名映射为内部枚举；time_series 的 top/quantile/zscore/all 统一为 threshold；ranking 统一为 cross_sectional；无效非正 count 清理；阈值策略缺少阈值时补模板默认阈值；StrategyCritic 同步使用归一化后的候选记录 |
| 验证命令 | `pytest -q tests/unit/test_strategy_agent_normalization.py tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_critic.py tests/unit/test_agent_workflow_regressions.py` |
| 验证结果 | 23 passed |
| 验证命令 | `pytest -q tests/unit/test_parameter_matrix.py tests/unit/test_settings.py` |
| 验证结果 | 2541 passed |
| 验证命令 | `python -m py_compile agents/strategy_agent.py agents/strategy_critic.py schemas/messages.py core/settings.py manager.py` |
| 验证结果 | 通过 |
| 剩余风险 | 仍需重新完整跑 swarm，确认真实 LLM 候选不再全部 fallback；不可识别枚举仍会被跳过，避免把任意文本误映射成交易配置 |
| 下一步 | 重新执行 4 角色 300 轮 local futures swarm 并重点观察 StrategyAgent/StrategyCritic 日志 |

### 2026-04-28 17:22 - 策略 LLM 输出空字典容错

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复策略生成/评审阶段 LLM 返回 `counts=null`、`thresholds=null` 或字典内部值为 `null` 时触发 fallback/critic halt 的问题 |
| 触发来源 | 本地 futures 长跑真实回测阶段日志显示 StrategyAgent/StrategyCritic 因 Pydantic 校验失败降级，主回测指标虽真实但策略链路未完整执行 |
| 涉及模块 | `schemas/messages.py`，`tests/unit/test_strategy_output_schema.py` |
| 复现方式 | 用 `StrategyProposalBatchOutput.model_validate_json` 和 `RefinementProposalOutput.model_validate_json` 校验包含 `null` 策略字典字段的 LLM payload |
| 修改摘要 | 对策略候选的 `thresholds/counts/holding_constraints/cost_model` 做前置规范化：字段为 `null` 时转为空字典，字典内 `null` 值移除；新增 schema 回归测试覆盖 StrategyAgent 和 StrategyCritic 两类结构化输出 |
| 验证命令 | `pytest -q tests/unit/test_strategy_output_schema.py tests/unit/test_strategy_critic.py tests/unit/test_agent_workflow_regressions.py` |
| 验证结果 | 19 passed |
| 验证命令 | `python -m py_compile schemas/messages.py agents/strategy_agent.py agents/strategy_critic.py` |
| 验证结果 | 通过 |
| 验证命令 | `pytest -q tests/unit/test_parameter_matrix.py tests/unit/test_settings.py` |
| 验证结果 | 2541 passed |
| 剩余风险 | 仍需重新跑完整 swarm，确认真实 LLM 输出下不再降级；本修复只处理可恢复的空字典/空值，不掩盖缺失必填策略字段 |
| 下一步 | 重新执行 4 角色 300 轮 local futures swarm，并继续监控真实日志 |

### 2026-04-28 17:12 - 参数组合矩阵校验前移

| 字段 | 内容 |
| --- | --- |
| 目标 | 检测 CLI/settings 枚举参数全组合，避免 settings 放行但 evaluator 后续失败 |
| 触发来源 | 用户要求“检测全部参数组合是否会出现任何问题” |
| 涉及模块 | `core/settings.py`，`tests/unit/test_parameter_matrix.py`，`tests/unit/test_settings.py` |
| 复现方式 | 枚举 `mode/data_backend/engine/market_mode/market_profile/market_profiles/local_data_layout` 后发现 settings 放行 324 个基础组合，其中 144 个到 evaluator 才失败 |
| 修改摘要 | 将组合约束前移到 settings：`qlib` 后端必须配 `qlib` 模式且不支持 futures/mixed；`ricequant/local` 后端必须配 `ricequant` 模式；RiceQuant 仅支持 cn_stock 且不支持 mixed；新增参数矩阵测试覆盖枚举组合和 provider/embedding/reasoning 组合 |
| 验证命令 | `pytest -q tests/unit/test_parameter_matrix.py tests/unit/test_settings.py` |
| 验证结果 | 2541 passed |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 2660 passed |
| 验证命令 | `git diff --check -- core/settings.py tests/unit/test_settings.py tests/unit/test_parameter_matrix.py regression_log.md core/alphaeval/rq_eval.py` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | “全部组合”仅覆盖有限枚举和代表性自由文本值；真实 LLM API key、真实 qlib/RiceQuant 数据初始化、任意日期/roles/模型名无法穷举 |
| 下一步 | 若需要运行级别穷举，应增加 `--dry-run-config` CLI，只做初始化和 evaluator factory，不触发 LLM 长调用 |

### 2026-04-28 17:07 - 本地 futures 默认使用完整主力数据

| 字段 | 内容 |
| --- | --- |
| 目标 | 修复 `--data-backend local` 默认命中仓库短样本，导致 2015-2020 评估 IC 全 0 和分层图报空的问题 |
| 触发来源 | 用户追问本地 futures 长跑结果如何修复 |
| 涉及模块 | `core/settings.py`，`core/alphaeval/rq_eval.py` |
| 复现方式 | 原自动路径解析到 `data/local_futures/dominant/1d`，仅 70 行、3 个品种、2015-01-05 到 2015-04-16；完整数据位于 `../llm/data/local_futures/dominant/1d` |
| 修改摘要 | futures local 自动发现优先使用相邻 `../llm` 完整主力连续数据；分层收益按实际横截面动态调整组数，避免 4 个品种固定切 5 组时丢图 |
| 验证命令 | `python - <<'PY'\nfrom core.settings import build_settings\nfrom core.local_data import load_local_ohlcv\ns = build_settings({'max_iterations':300,'mode':'ricequant','data_backend':'local','llm_provider':'deepseek','llm_model':'deepseek-v4-flash','embedding_provider':'glm','market_start':'2015-01-01','market_end':'2020-12-01','roles':['动量专家','波动率专家','统计套利专家','基本面套利专家']})\nprint(s.market_profile)\nprint(s.local_data_path)\ndf = load_local_ohlcv(s.local_data_path, market_profile=s.market_profile, start_date=s.market_start, end_date=s.market_end)\nprint('rows', len(df), 'instruments', df.index.get_level_values('instrument').nunique())\nprint('range', df.index.get_level_values('datetime').min(), df.index.get_level_values('datetime').max())\nPY` |
| 验证结果 | 通过；解析为 `futures` / `../llm/data/local_futures/dominant/1d`，加载 5626 行、4 个品种、2015-01-05 到 2020-12-01 |
| 验证命令 | `python - <<'PY'\nfrom core.alphaeval.local_eval import LocalDataEval\nexpr='Rank(Div(Sub($close, Ref($close,20)), Ref($close,20)))'\ne=LocalDataEval([expr], test_start_date='2015-01-01', test_end_date='2020-12-01', local_data_path='../llm/data/local_futures/dominant/1d', market_profile='futures', engine='pandas')\ne.run()\nprint('ic', e.ic, 'rankic', getattr(e, 'rankic', None), 'sharpe', getattr(e, 'sharpe', None))\nprint('plots', e.plot_paths)\nPY` |
| 验证结果 | 通过；IC=0.0045、RankIC=0.0048、Sharpe≈0.24，生成 equity 和 layers 图 |
| 验证命令 | `pytest -q tests/unit/test_settings.py tests/unit/test_agent_workflow_regressions.py tests/unit/test_rq_eval_metrics.py tests/test_operators.py tests/test_dry_run.py` |
| 验证结果 | 21 passed |
| 验证命令 | `git diff --check -- core/settings.py core/alphaeval/rq_eval.py` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 尚未重新完整跑 4 角色 300 上限长任务；完整数据横截面仍只有 4 个主力品种，IC 稳定性有限 |
| 下一步 | 用原命令重新跑 swarm，确认不再使用短样本；如需要更大横截面，显式传 `--local-data-path ../llm/data/local_futures/contracts/1d` 做合约池实验 |

### 2026-04-28 14:54 - RAG 单测去除真实 embedding 依赖

| 字段 | 内容 |
| --- | --- |
| 目标 | 对齐当前项目进度时复核 RAG/API/Manager/local data/settings 相关未提交改动，并修复 hermetic 单测依赖外部环境的问题 |
| 触发来源 | 本轮进度对齐验证发现 `tests/test_rag.py` 在默认 LLM provider 为 `deepseek` 时回退到 HuggingFace 本地模型，网络受限下失败；完整 unit 进一步发现 `tests/unit/test_settings.py` 会被本机 `.env` 中的 `DEEPSEEK_API_KEY` 污染 |
| 涉及模块 | `wiki-rag`，`settings-runtime-path`，`tests/test_rag.py`，`tests/unit/test_settings.py` |
| 复现方式 | `pytest -q tests/unit/test_api_contract.py tests/unit/test_manager_strategy_eval.py tests/unit/test_local_data.py tests/unit/test_rq_index_futures_download.py tests/unit/test_rag_readiness.py tests/test_rag.py` 初次结果为 51 passed / 2 failed，失败用例为 `TestRAG.test_chunking`、`TestRAG.test_empty_retrieval` |
| 修改摘要 | `tests/test_rag.py` 显式使用 fake Chroma embedding function 和临时目录，避免测试初始化真实 API/HuggingFace embedding 模型或写入 tracked `data/test_db`；`tests/unit/test_settings.py` 在 Codex 显式 provider 用例中屏蔽 dotenv 加载，避免本机 `.env` 影响空环境断言 |
| 验证命令 | `pytest -q tests/test_rag.py tests/unit/test_rag_readiness.py` |
| 验证结果 | 通过，5 passed |
| 验证命令 | `pytest -q tests/unit/test_api_contract.py tests/unit/test_manager_strategy_eval.py tests/unit/test_local_data.py tests/unit/test_rq_index_futures_download.py tests/unit/test_rag_readiness.py tests/test_rag.py` |
| 验证结果 | 通过，53 passed |
| 验证命令 | `python -m py_compile tests/test_rag.py core/rag.py api.py manager.py core/local_data.py scripts/download_rq_index_futures.py` |
| 验证结果 | 通过 |
| 验证命令 | `git diff --check -- tests/test_rag.py core/rag.py api.py manager.py core/local_data.py scripts/download_rq_index_futures.py` |
| 验证结果 | 通过，无 whitespace error |
| 验证命令 | `pytest -q tests/unit` |
| 验证结果 | 通过，127 passed |
| 验证命令 | `git diff --check -- .` |
| 验证结果 | 通过，无 whitespace error |
| 剩余风险 | 未跑前端构建、真实 Web/TUI run lifecycle、真实 RiceQuant/LLM/RAG embedding smoke；当前确认 hermetic unit 绿，但外部依赖和交互路径仍待复核 |
| 下一步 | 完整收敛前继续跑前端 build 和手工 Web/TUI smoke，并清理/归档 `local-dist/` 等大体积产物 |

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
