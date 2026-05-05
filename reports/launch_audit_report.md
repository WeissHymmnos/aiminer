# 上线前彻底检查报告

审计日期：2026-04-25  
仓库：`/home/wh/Documents/aiminer`  
分支与提交：`master` / `be0387a`  
审计方式：主 agent 本地验证 + 8 个专题 subagent 并行审计；未修改业务代码。

## 1. 执行摘要

- 当前是否建议上线：暂缓上线
- 总体风险等级：Critical
- 上线准备度评分：42/100

评分拆分：

| 维度 | 分数 | 主要原因 |
|---|---:|---|
| 功能正确性 | 52 | 核心路径有测试，但 full unit 命令未收敛；真实评估失败会降级为模拟结果 |
| 安全性 | 25 | 默认关闭鉴权、表达式 `eval`、敏感读接口未授权、SSRF 与日志隐私风险 |
| 性能稳定性 | 48 | API 内存分页、本地数据全量读入、长任务缺少 heartbeat/deadline/幂等 |
| 数据可靠性 | 50 | SQLite/JSON 不一致、活跃 Chroma 可能为空、数据 manifest 不足、非原子写入 |
| 部署运维 | 38 | `.env` 装载冲突、无 healthcheck、无指标/报警、镜像不可复现 |
| 用户体验 | 55 | 无 404/ErrorBoundary、表单校验不足、危险操作确认弱、a11y 缺口 |
| 文档可维护性 | 40 | Docker 文档过期、依赖清单漂移、无 LICENSE/NOTICE/SBOM |

最重要的 5 个风险：

| 排名 | 风险 |
|---:|---|
| 1 | 未配置 `AIMINER_AUTH_TOKEN` 时 API 默认关闭鉴权，Compose 又暴露 8000 端口 |
| 2 | 因子表达式通过 Python `eval` 执行，且上下文暴露 `pd/np` 等对象，存在远程代码执行路径 |
| 3 | 多个敏感读接口未挂鉴权，即使启用 token 也可读取因子、策略、报告、Wiki |
| 4 | 真实评估失败后会生成并可能持久化模拟指标，可能把“伪 Alpha”当成真实研究成果上线 |
| 5 | 生产配置、依赖和部署不可复现：`.env` 是目录、无 healthcheck、Python/Rust 依赖未锁定 |

上线前必须完成的事项：

- 鉴权改为 fail-closed：生产缺少 `AIMINER_AUTH_TOKEN` 必须启动失败，并给所有业务读写接口加授权。
- 移除或严格沙箱化表达式 `eval`，禁止表达式访问模块对象、属性链和任意函数调用。
- 禁止生产模拟结果进入 alpha pool；所有 `is_simulated=True` 结果必须标为不可采信或直接失败。
- 修复 `.env`/secret 装载、CORS、前端 API/WS base URL、Docker healthcheck 和容器 smoke test。
- 锁定依赖和发布物：Python lock、`pyqlib` 固定 commit、Docker 保留 `Cargo.lock`、补 LICENSE/NOTICE。

## 2. 项目概览

- 技术栈：Python 3.10/3.11、FastAPI、Uvicorn、LangGraph、LangChain、SQLite、ChromaDB、Pandas、Polars、Rust Polars plugin、React 18、Vite、TypeScript、Tauri 2、Docker Compose。
- 产品形态：AI 量化因子挖掘工作台，包含 Web/API、桌面壳、TUI、CLI、数据/RAG/本地回测能力。
- 主要模块：`api.py` Web API 与运行编排；`manager.py` 多 agent 调度；`sub_agent.py` LangGraph worker；`agents/*` 研究/因子/评估/策略/总结；`core/*` 数据、RAG、LLM、回测、策略；`frontend/src/*` 工作台 UI；`src-tauri/*` 桌面打包。
- 核心业务路径：配置 token、启动 swarm run、LLM 生成假设、生成因子表达式、RiceQuant/Qlib/local 回测、策略回测、结果入 SQLite/JSON、查看 Alpha Pool/报告/图表、Wiki/RAG 检索与编辑、Admin reset。
- 部署方式：Dockerfile + docker-compose 后端单服务，前端可由 FastAPI 托管 `frontend/dist` 或独立 Nginx 容器；Tauri 使用 sidecar 启动后端。
- 数据存储与第三方依赖：`results/alpha_miner.db`、`results/swarm_runs/*.json/jsonl`、`results/strategies/*.json`、`data/local_futures/*.parquet`、`data/chroma_db`、`data/wiki_db`、RiceQuant、多个 LLM provider、embedding provider。
- 当前上线风险最高的模块：`api.py`、`core/alphaeval/rq_eval.py`、`agents/eval_agent.py`、`manager.py`、`core/local_data.py`、Docker/Compose 配置。

## 3. 检查范围与方法

阅读或抽样阅读的关键文件/目录：

- 根目录：`README.md`、`README_DOCKER.md`、`.env.example`、`.gitignore`、`.dockerignore`、`requirements.txt`、`environment.yml`、`Dockerfile`、`docker-compose.yml`、`pytest.ini`。
- 后端：`api.py`、`main.py`、`manager.py`、`sub_agent.py`、`core/settings.py`、`core/runtime.py`、`core/llm.py`、`core/codex_llm.py`、`core/manual_runner.py`、`core/local_data.py`、`core/evaluator_factory.py`、`core/strategy.py`、`core/rag.py`、`core/wiki.py`、`core/alphaeval/rq_eval.py`、`core/alphaeval/polars_engine.py`。
- 前端：`frontend/package.json`、`frontend/package-lock.json`、`frontend/vite.config.ts`、`frontend/src/App.tsx`、`frontend/src/lib/api.ts`、`frontend/src/lib/ws.ts`、`frontend/src/lib/monaco.ts`、`frontend/src/pages/*`、`frontend/src/styles.css`。
- 发布：`.github/workflows/ci.yml`、`.github/workflows/packaging.yml`、`frontend/Dockerfile`、`frontend/nginx.conf`、`src-tauri/tauri.conf.json`、`src-tauri/Cargo.toml`、`src-tauri/capabilities/default.json`、`aiminer-backend.spec`。
- 测试与数据：`tests/**`、`data/local_futures`、`data/chroma_db`、`data/wiki_db`、`results/**`。

运行命令与结果：

| 命令 | 结果 |
|---|---|
| `pwd` | 成功，当前目录 `/home/wh/Documents/aiminer` |
| `git status --short` | 初始仅 `?? PRODUCT_MANUAL.md`；测试后出现 `M data/test_db/kimi_embedding-2/chroma.sqlite3` |
| `ls -la`、`find . -maxdepth 2 -type d`、`rg --files` | 成功，确认项目结构 |
| `python -m py_compile api.py manager.py core/strategy.py tui.py` | 成功 |
| `npm run build` | 成功，但 Vite 警告大 chunk：`CodeEditor` 约 3.8MB、`ts.worker` 约 7.0MB |
| `PYTHONPATH=. pytest tests/unit -m "unit and not external and not native" -q` | 未获得最终通过结果，长时间仅输出部分 dots 后无收敛；视为验证失败/不可信 |
| `python -m pip check` | 失败，当前 Python 环境存在多项依赖冲突 |
| `npm ls --depth=0` | 成功 |
| `npm audit --omit=dev --audit-level=moderate` | 失败，网络/DNS 受限：`EAI_AGAIN registry.npmjs.org` |
| `python -m pip_audit -r requirements.txt` | 失败，`pip_audit` 未安装 |
| `cargo audit` | 失败，`cargo-audit` 未安装 |
| `cargo metadata --no-deps --format-version 1` | 成功，覆盖 `polars_plugins` 和 `src-tauri` |
| `docker compose config` | 成功，Compose 语法可解析 |
| `find tests -type f -name "test*.py"`、`rg "def test_" tests` | 成功，确认测试分布 |

无法验证项及原因：

- 无法完成 CVE 级依赖漏洞扫描：网络受限且本地缺少 `pip-audit`、`cargo audit`。
- 未执行真实 RiceQuant/LLM/短信/邮件/支付/交易等外部调用：遵守上线前审计安全约束。
- 未执行真实 Docker build：会大量下载和构建依赖，当前网络受限且耗时高。
- 未完成完整 unit/integration/e2e 验证：本地 pytest 命令未收敛，Subagent B 被关闭前未返回结论。
- 未进行浏览器真机/移动端/a11y 自动化测试：仓库无 Playwright/Cypress/axe 脚本。

## 4. 风险总表

| ID | 严重级别 | 类型 | 问题标题 | 影响范围 | 相关文件 | 是否阻塞上线 | 建议处理优先级 |
|---|---|---|---|---|---|---|---|
| R-001 | Critical | 安全/部署 | 默认关闭鉴权且 Compose 暴露 API | 全部 API、结果、后台任务 | `api.py:65`, `docker-compose.yml:8` | 是 | P0 |
| R-002 | Critical | 安全 | 因子表达式 `eval` 存在 RCE 路径 | 回测验证、手工回测、swarm 评估 | `core/alphaeval/rq_eval.py:651`, `api.py:1838` | 是 | P0 |
| R-003 | High | 安全 | 多个敏感读接口未鉴权 | 因子、策略、报告、Wiki、图表 | `api.py:1605`, `api.py:1964`, `api.py:1664` | 是 | P0 |
| R-004 | High | 安全 | 用户可传 `llm_base_url` 导致 SSRF/密钥外送 | LLM 调用、内网资产、API key | `api.py:1444`, `core/llm.py:125` | 是 | P0 |
| R-005 | High | 正确性/数据 | 真实评估失败后可能持久化模拟结果 | Alpha Pool、策略选择、报告可信度 | `agents/eval_agent.py:188`, `manager.py:478` | 是 | P0 |
| R-006 | High | 部署 | `.env` 是目录且 Compose 挂载为文件，配置读取分散 | Docker/Compose 启动、凭证加载、鉴权 | `docker-compose.yml:14`, `core/settings.py:244` | 是 | P0 |
| R-007 | High | 部署/运维 | 无容器 healthcheck、readiness、基础指标和报警 | 部署稳定性、自动恢复、故障发现 | `api.py:1596`, `docker-compose.yml:1` | 是 | P0 |
| R-008 | High | 依赖/发布 | 依赖不可复现、清单漂移、Docker 忽略 Rust lock | 构建、CI、供应链、回滚 | `requirements.txt:1`, `.dockerignore:8` | 是 | P0 |
| R-009 | High | 数据 | SQLite schema/迁移分散且 JSON 备份与 DB 不一致 | 数据恢复、迁移、历史指标 | `api.py:166`, `manager.py:317`, `core/strategy.py:602` | 是 | P0 |
| R-010 | High | 数据/RAG | 活跃 Chroma/RAG 库可能为空 | Wiki/RAG 检索、知识驱动生成 | `core/rag.py:122`, `core/wiki.py:162` | 条件阻塞 | P0 |
| R-011 | High | 性能 | `/api/results` 和 `/api/strategies` 先全量 `fetchall()` 再分页 | API 延迟、内存 | `api.py:1605`, `api.py:1965`, `api.py:1055` | 否 | P1 |
| R-012 | High | 性能/数据 | 本地行情全量读入且 layout 推断重复读文件 | 大数据回测、内存、启动耗时 | `core/local_data.py:122`, `core/local_data.py:177` | 否 | P1 |
| R-013 | High | 稳定性 | 长任务缺少端到端 deadline、heartbeat、启动幂等 | worker 卡死、重复任务、成本失控 | `api.py:2093`, `manager.py:667`, `manager.py:1093` | 是 | P0 |
| R-014 | Medium | 安全/稳定性 | 缺少速率限制、请求体大小和 iterations/roles 上限 | DoS、外部额度消耗 | `api.py:1428`, `api.py:2093` | 条件阻塞 | P1 |
| R-015 | Medium | 安全/隐私 | WebSocket token 在 URL query，日志可能泄露账号标识 | token、RiceQuant 用户隐私 | `frontend/src/lib/ws.ts:32`, `core/alphaeval/rq_eval.py:78` | 条件阻塞 | P1 |
| R-016 | Medium | 数据 | 本地 futures 连续合约存在非正价格，manifest 不足以证明覆盖 | 回测准确性、数据排障 | `scripts/download_rq_index_futures.py:132` | 否 | P1 |
| R-017 | Medium | 数据/运维 | Parquet 与 manifest 写入非原子，删除非软删除且可能遗留缓存 | 数据损坏、回滚、合规删除 | `scripts/download_rq_index_futures.py:239`, `core/manual_runner.py:266` | 否 | P1 |
| R-018 | High | 体验 | 无 404/ErrorBoundary，核心表单无校验，危险操作确认不足 | 首次使用、任务误触、白屏 | `frontend/src/App.tsx:39`, `frontend/src/pages/SwarmRunsPage.tsx:96` | 条件阻塞 | P1 |
| R-019 | Medium | 体验/a11y | 焦点、aria-live、图表/graph 可访问性不足 | 键盘用户、屏幕阅读器、合规 | `frontend/src/styles.css:358`, `frontend/src/components/Sparkline.tsx:52` | 条件阻塞 | P2 |
| R-020 | Medium | 文档/许可证 | Docker 文档过期，缺 LICENSE/NOTICE/SBOM | 交付复现、商业/公开发布 | `README_DOCKER.md:18`, `src-tauri/Cargo.toml:6` | 条件阻塞 | P1 |

## 5. 详细发现

### [R-001] 默认关闭鉴权且 Compose 暴露 API

- 严重级别：Critical
- 类型：安全 / 部署
- 相关文件/位置：`api.py:65`、`docker-compose.yml:8`、`.env.example:1`
- 现象：`AUTH_DISABLED` 在未配置 `AIMINER_AUTH_TOKEN` 时为 true；Compose 默认发布 `8000:8000`，`.env.example` 未要求配置 `AIMINER_AUTH_TOKEN`。
- 复现或验证方式：阅读 `api.py` 的 `AUTH_TOKEN/AUTH_DISABLED` 逻辑；`tests/unit/test_api_contract.py:155` 还明确测试“缺失 token 默认 auth disabled”；`docker compose config` 显示 8000 端口发布。
- 影响：服务一旦暴露到局域网/公网，未带任何凭证即可访问大量 API，进一步触发回测、读取结果或执行危险操作。
- 根因分析：认证策略采用“未配置则关闭”的开发默认值，没有生产模式 fail-closed 门禁。
- 修复建议：增加 `AIMINER_ENV=production` 或类似生产开关；生产缺少 `AIMINER_AUTH_TOKEN` 时启动失败；Compose/README/.env.example 强制声明 token。
- 推荐测试：新增 `test_production_requires_auth_token`；容器 smoke test 验证无 token 请求核心 API 返回 401。
- 是否阻塞上线：是。

### [R-002] 因子表达式 `eval` 存在远程代码执行路径

- 严重级别：Critical
- 类型：安全
- 相关文件/位置：`core/alphaeval/rq_eval.py:651`、`core/alphaeval/rq_eval.py:1073`、`core/alphaeval/polars_engine.py:466`、`api.py:1838`
- 现象：因子表达式经 AST 转换后使用 Python `eval`，上下文中包含 `pd`、`np`、函数对象等；前端/API 可提交表达式进行 validate/run。
- 复现或验证方式：静态检查 `eval(compiled_expr, {"__builtins__": {}}, context)`；安全子审计确认 `pd/np` 属性链可达。未执行破坏性 PoC。
- 影响：若攻击者可访问 validate/run 接口，可能通过表达式触发服务器端任意代码路径，进而读取/写入挂载数据卷或窃取凭证。
- 根因分析：`__builtins__` 置空不足以隔离 Python 对象属性访问；表达式 DSL 没有严格白名单解释器。
- 修复建议：替换为 AST 白名单解释器；只允许数字、字段、白名单函数和简单算术/比较节点；禁止 `ast.Attribute`、未知 `ast.Call`、模块对象和所有双下划线属性；`skip_validation` 不得绕过安全校验。
- 推荐测试：添加恶意属性链、未知函数、超长表达式、深度嵌套表达式的拒绝测试；对 pandas/polars 两条引擎路径同时覆盖。
- 是否阻塞上线：是。

### [R-003] 多个敏感读接口未鉴权

- 严重级别：High
- 类型：安全 / API
- 相关文件/位置：`api.py:1605`、`api.py:1638`、`api.py:1664`、`api.py:1673`、`api.py:1685`、`api.py:1964`、`api.py:2007`、`api.py:2050`
- 现象：`/api/results`、`/api/factors/{factor_id}`、`/api/charts/{factor_id}`、`/api/reports/{factor_id}`、`/api/wiki/*`、`/api/strategies*` 等读接口没有 `Depends(_require_actor)`。
- 复现或验证方式：静态搜索路由定义，确认上述函数签名没有 `actor: Actor = Depends(_require_actor)`。
- 影响：即使启用了 token，未授权访问者也能读取策略代码、回测指标、报告、Wiki 内容和图表。
- 根因分析：认证只覆盖部分写接口和 swarm 操作，读接口默认被当作公开资源。
- 修复建议：默认所有 `/api/*` 走鉴权；若确需公开，只单独暴露脱敏匿名视图。
- 推荐测试：无 token 访问每个 `/api/*` 业务接口均应返回 401；带 token 返回 200/业务错误。
- 是否阻塞上线：是。

### [R-004] 用户可传 `llm_base_url` 导致 SSRF/密钥外送

- 严重级别：High
- 类型：安全
- 相关文件/位置：`api.py:1444`、`core/llm.py:125`
- 现象：Swarm 配置允许传入 `llm_base_url`，后端会构造 OpenAI-compatible 客户端并向该 URL 发送请求，可能携带真实 provider API key。
- 复现或验证方式：阅读 `SwarmConfig.llm_base_url` 和 `get_llm()` 的 base URL 解析。
- 影响：攻击者可诱导后端访问内网地址、metadata 服务或攻击者控制的 URL，造成 SSRF 或 API key 外送。
- 根因分析：把 provider base URL 作为用户输入透传给服务端网络客户端，缺少白名单和私网地址拦截。
- 修复建议：生产禁用用户自定义 `llm_base_url`；只允许管理员配置白名单；拒绝 localhost、私网、link-local、metadata 地址；不要把真实 provider key 发往自定义 host。
- 推荐测试：提交 `localhost`、私网 IP、metadata 地址、非 HTTPS 地址时返回 400；白名单域名通过。
- 是否阻塞上线：是。

### [R-005] 真实评估失败后可能持久化模拟结果

- 严重级别：High
- 类型：正确性 / 数据
- 相关文件/位置：`agents/eval_agent.py:188`、`sub_agent.py:259`、`manager.py:478`
- 现象：评估异常后 `EvalAgent` 返回 `_simulated_metrics()`；`AlphaResearcher` 保留 `is_simulated`；`PortfolioManager` 仍按 `perf_metric` 过滤和入池，没有生产阻断。
- 复现或验证方式：阅读异常处理与 `evaluate_and_combine` 逻辑。
- 影响：数据源、凭证或评估引擎失败时，系统仍可能展示“有效 Alpha”，误导研究和后续策略筛选。
- 根因分析：开发 fallback 与生产可信结果没有边界；候选选择逻辑未排除模拟结果。
- 修复建议：生产默认禁用模拟 fallback；`is_simulated=True` 结果不得入 `alpha_pool` 或必须显著标红且不可被策略选择；运行状态应标为 `failed/partial_failed`。
- 推荐测试：模拟 RiceQuant/Qlib 失败，断言 run 失败或无 alpha 入池；API 返回包含可信度字段。
- 是否阻塞上线：是，尤其是面向真实研究或投资决策。

### [R-006] `.env` 装载冲突且配置读取分散

- 严重级别：High
- 类型：部署 / 配置
- 相关文件/位置：`docker-compose.yml:14`、`api.py:48`、`api.py:65`、`core/settings.py:244`、`core/manual_runner.py:25`
- 现象：当前根目录 `.env` 是目录；Compose 把 `./.env` 挂载为 `/app/.env:ro`；`api.py` import 时固化 settings/auth/CORS，其他模块多次 `build_settings()`。
- 复现或验证方式：`ls -la .env` 显示目录；`docker compose config` 显示 `.env` 文件挂载。
- 影响：容器可能无法正确读取凭证；API、CLI、TUI、worker 使用不同设置；env 变更后行为不可预测。
- 根因分析：没有统一配置入口、启动时配置校验和生产环境 profile。
- 修复建议：把 `.env` 改为文件或改用 `env_file`/Docker secrets；启动时校验 auth、data/results/logs、provider、CORS；配置对象集中注入。
- 推荐测试：容器启动 smoke test 校验 env 已加载；缺失关键 env 直接失败。
- 是否阻塞上线：是。

### [R-007] 无 healthcheck、readiness、metrics 和报警

- 严重级别：High
- 类型：部署 / 运维
- 相关文件/位置：`api.py:1596`、`docker-compose.yml:1`、`main.py:13`
- 现象：后端有 `/api/health`，但 Dockerfile/Compose 无 healthcheck；无 metrics/tracing/alerting；日志主要靠 Loguru 和 JSONL。
- 复现或验证方式：检查 Dockerfile/Compose，无 `HEALTHCHECK` 或 service `healthcheck`；无 Prometheus/OpenTelemetry/Sentry 接入。
- 影响：容器假活、配置缺失、worker 卡死、队列积压、外部依赖失败不能及时发现或自动恢复。
- 根因分析：部署配置仍偏开发/本机运行，没有生产可观测性门禁。
- 修复建议：Compose 加 `/api/health` healthcheck；增加 `/metrics` 或接入 OpenTelemetry/Sentry；监控 active run、队列丢日志、DB locked、外部依赖超时。
- 推荐测试：部署 smoke test 验证 health healthy；模拟 DB 不可写/缺 token 时 health 或 startup 失败。
- 是否阻塞上线：是。

### [R-008] 依赖不可复现，发布物边界不清

- 严重级别：High
- 类型：依赖 / 发布
- 相关文件/位置：`requirements.txt:1`、`requirements.txt:18`、`environment.yml:10`、`.dockerignore:8`、`Dockerfile:29`
- 现象：Python 依赖几乎全是范围或未锁版本，`pyqlib` 直接从 GitHub 拉取未固定 commit；`environment.yml` 缺少 FastAPI/uvicorn/polars 等；`.dockerignore` 排除 `Cargo.lock`；Docker 使用未 pin digest base image 和 `curl | sh` 安装 Rust。
- 复现或验证方式：阅读依赖清单；`python -m pip check` 在当前环境失败；Subagent H 统计 `requirements.txt` 25/25 个条目非精确锁定或 Git 依赖。
- 影响：CI/生产/本地环境可能装出不同版本，构建不可复现，回滚无法保证二进制一致，供应链审计缺证据。
- 根因分析：原型阶段依赖清单没有转为发布级 lockfile 与 SBOM。
- 修复建议：生成 Python lockfile；`pyqlib` 固定 commit；统一 `requirements.txt` 与 `environment.yml`；从 Docker build context 保留 `polars_plugins/Cargo.lock`；构建使用 locked 模式。
- 推荐测试：clean checkout + no-cache container build；`pip check`、`cargo metadata --locked`、`npm ci` 全部通过。
- 是否阻塞上线：是。

### [R-009] SQLite schema/迁移分散且 JSON 备份与 DB 不一致

- 严重级别：High
- 类型：数据 / 迁移
- 相关文件/位置：`api.py:166`、`manager.py:317`、`core/strategy.py:602`、`manager.py:399`
- 现象：`alpha_pool` 和 `strategy_backtests` schema 在多处重复定义；Subagent E 检测 DB 有 4 条 alpha，`results/alpha_pool.json` 只有 1 条，且部分 DB 记录缺 `metrics_json/returns_json`。
- 复现或验证方式：静态比对 schema 定义；SQLite 只读检查和 JSON 文件检查。
- 影响：恢复/迁移可能丢数据；谁先创建 DB 会影响字段；未来新增字段容易漂移。
- 根因分析：没有单一 schema/migration source of truth，没有迁移版本，也没有备份恢复演练。
- 修复建议：抽出统一 DB migration 模块；SQLite 作为唯一 source of truth；提供导出/恢复脚本；启动时执行 schema version 校验。
- 推荐测试：从空 DB 启动迁移；从旧 schema 迁移；备份恢复后 row count 和关键 JSON 字段一致。
- 是否阻塞上线：是。

### [R-010] 活跃 Chroma/RAG 库可能为空

- 严重级别：High
- 类型：数据 / RAG
- 相关文件/位置：`core/rag.py:122`、`core/wiki.py:162`
- 现象：当前 `build_settings()` 检测到 provider 可能落到 `kimi_embedding-2`，但 `data/chroma_db/kimi_embedding-2` 与 `data/wiki_db/kimi_embedding-2` embeddings 计数为 0；其他历史库非空。
- 复现或验证方式：Subagent E 读取 Chroma sqlite 计数；检查 RAG/Wiki 初始化路径。
- 影响：RAG/Wiki 检索上线后返回空结果，或首次请求触发重建导致冷启动失败。
- 根因分析：embedding provider 与持久化向量库没有绑定验证，缺少 readiness。
- 修复建议：生产固定 `EMBEDDING_PROVIDER`；上线前重建并验证 active collection count；health/readiness 纳入 RAG 状态。
- 推荐测试：启动后查询知识库必须返回非空；provider 切换时拒绝使用空库或提示重建。
- 是否阻塞上线：如果 RAG/Wiki 是核心功能，则阻塞。

### [R-011] API 列表先全量读取再分页

- 严重级别：High
- 类型：性能
- 相关文件/位置：`api.py:1605`、`api.py:1965`、`api.py:1055`
- 现象：`/api/results`、`/api/strategies` 先 `fetchall()` 获取所有行，再 `_paginate_rows()` 在 Python 中切片。
- 复现或验证方式：阅读 SQL 查询和 `_paginate_rows()`。
- 影响：因子/策略增长后，接口延迟和内存线性上升；前端轮询会放大压力。
- 根因分析：响应 limit 只限制返回，不限制 DB 查询。
- 修复建议：改成 SQL 级 `COUNT(*)` + `LIMIT/OFFSET`；增加 `(run_id, timestamp DESC)`、`(run_id, ran_at DESC)` 复合索引。
- 推荐测试：构造 10 万行结果，验证 p95 延迟和 RSS；检查 query plan。
- 是否阻塞上线：否，但上线前强烈建议。

### [R-012] 本地行情全量读入且重复读取

- 严重级别：High
- 类型：性能 / 数据
- 相关文件/位置：`core/local_data.py:122`、`core/local_data.py:177`、`core/local_data.py:222`
- 现象：layout 推断会读取完整 CSV/Parquet；加载时再次全量读取、concat、排序、去重；无列裁剪和日期下推。
- 复现或验证方式：阅读 `_has_instrument_column()`、`infer_layout()`、`load_local_ohlcv()`。
- 影响：大文件或多文件 futures 数据会 OOM 或长时间阻塞 worker。
- 根因分析：Pandas eager loading 设计未设置数据规模保护。
- 修复建议：CSV 用 `nrows=0` 读表头；Parquet 用 schema/columns；优先 Polars lazy scan；加入文件数、行数、内存预算上限。
- 推荐测试：大文件 smoke test、超限保护测试、日期过滤下推测试。
- 是否阻塞上线：否，但面向大型本地数据时应先修。

### [R-013] 长任务缺少 deadline、heartbeat 和幂等

- 严重级别：High
- 类型：稳定性 / 正确性
- 相关文件/位置：`api.py:2093`、`api.py:996`、`manager.py:667`、`manager.py:1093`、`frontend/src/pages/SwarmRunsPage.tsx:66`
- 现象：`start_swarm()` 每次 POST 都生成新 run；部分并行执行有 global timeout，但 manual/strategy backtest 和 worker join 缺少统一 deadline/heartbeat；前端只靠按钮 pending 防重复。
- 复现或验证方式：阅读 run 启动、process join、ThreadPool/ProcessPool 逻辑。
- 影响：浏览器重试/双击可启动重复昂贵任务；worker 卡死会占用并发槽；停止后状态可能不一致。
- 根因分析：缺少任务系统层的幂等键、租约、heartbeat 和超时回收。
- 修复建议：支持 `Idempotency-Key` 或 config hash 短窗口去重；为每阶段设置 deadline；worker 定期 heartbeat；无 heartbeat 自动回收并标记失败。
- 推荐测试：重复提交同 payload 只创建一个 run；模拟卡死 worker 后自动停止；stop 后进程树清理完成。
- 是否阻塞上线：是，若多人/公网使用或成本敏感。

### [R-014] 缺少速率限制、请求体大小和任务规模上限

- 严重级别：Medium
- 类型：安全 / 稳定性
- 相关文件/位置：`api.py:1428`、`api.py:2093`
- 现象：`iterations` 仅 `ge=1`，无上限；roles、expression、wiki content、strategy config 缺少长度限制；无 per-token rate limit。
- 复现或验证方式：阅读 Pydantic model 和路由层。
- 影响：攻击者或误操作可发起超长任务、超大请求体、过多并发消耗 CPU/LLM/RiceQuant 额度。
- 根因分析：缺少 API 网关/应用层配额控制。
- 修复建议：增加 `le` 上限、字符串长度、body size limit、每 token 启动频率限制；网关层加限流。
- 推荐测试：超限 payload 返回 413/422/429；正常 payload 不受影响。
- 是否阻塞上线：公网暴露时阻塞。

### [R-015] WebSocket token query 与日志隐私泄露风险

- 严重级别：Medium
- 类型：安全 / 隐私
- 相关文件/位置：`frontend/src/lib/ws.ts:32`、`api.py:2276`、`core/alphaeval/rq_eval.py:78`
- 现象：WebSocket token 放在 URL query；RiceQuant 用户名/手机号可能写入运行日志；日志和 JSONL 可能被前端/API 查看。
- 复现或验证方式：阅读 `getSocketUrl()` 和 RiceQuant auth logging。
- 影响：token 可能进入代理/access log、浏览器历史或错误日志；用户隐私泄露。
- 根因分析：WebSocket 鉴权使用 query token，日志缺脱敏层。
- 修复建议：改短期一次性 ws ticket；代理不记录 query string；统一脱敏 Authorization、API key、手机号、token。
- 推荐测试：日志中不出现 token/手机号；ws ticket 过期后无法连接。
- 是否阻塞上线：若日志可访问或公网暴露，则阻塞。

### [R-016] 本地 futures 数据存在异常价格且 manifest 不足

- 严重级别：Medium
- 类型：数据
- 相关文件/位置：`scripts/download_rq_index_futures.py:132`
- 现象：Subagent E 全量校验发现 `IC888.parquet` 存在非正价格；manifest 不能完整证明实际覆盖范围和版本。
- 复现或验证方式：`python scripts/test_local_futures_data.py --root data/local_futures` 通过基础校验；扩展 sanity 检查发现非正价格。
- 影响：若默认回测路径包含连续/调整合约，异常价格会污染因子与策略结果。
- 根因分析：下载/生成流程没有把价格正值、合约类型和数据版本作为发布门禁。
- 修复建议：增加价格正值和合约白名单校验；明确 `888` 连续合约是否可参与默认回测；补 dataset-level manifest/checksum。
- 推荐测试：异常价格文件导致数据 readiness 失败；可接受合约路径通过。
- 是否阻塞上线：否，但数据产品上线前应处理。

### [R-017] 数据写入非原子，删除策略不一致

- 严重级别：Medium
- 类型：数据 / 运维
- 相关文件/位置：`scripts/download_rq_index_futures.py:239`、`scripts/download_rq_index_futures.py:470`、`core/manual_runner.py:266`、`core/manual_runner.py:603`
- 现象：Parquet 直接 `to_parquet(path)` 覆盖，manifest 直接 `write_text`；策略图表按 cache key 写入，但删除按 strategy id 删除，可能遗留缓存。
- 复现或验证方式：静态阅读下载和删除逻辑。
- 影响：中断可能留下损坏文件；删除/合规清理不完整；回滚无法确认状态。
- 根因分析：缺少临时文件 + `os.replace` 原子写入和统一资源索引。
- 修复建议：所有数据产物使用临时文件原子替换；删除改为 manifest 驱动或软删除；上线前快照 data/results/logs。
- 推荐测试：模拟写入中断不破坏旧文件；删除后图表/缓存/DB 一致。
- 是否阻塞上线：否。

### [R-018] 前端核心体验缺少兜底与校验

- 严重级别：High
- 类型：体验 / 正确性
- 相关文件/位置：`frontend/src/App.tsx:39`、`frontend/src/main.tsx:23`、`frontend/src/pages/SwarmRunsPage.tsx:96`、`frontend/src/pages/AdminPage.tsx:55`
- 现象：无 404 route 和 ErrorBoundary；Swarm/Manual/Strategy 表单大量普通 input，提交前校验弱；Admin reset 和删除操作主要靠原生 confirm 或 token。
- 复现或验证方式：静态阅读路由、表单和 Admin 页面。
- 影响：未知路径/懒加载失败可能白屏；非法输入触发长任务或外部费用；误点造成数据移动/删除。
- 根因分析：工作台 UI 偏内部研发，缺少生产用户体验门禁。
- 修复建议：增加 NotFound/ErrorBoundary；表单 schema 校验；危险操作要求输入对象 ID 或 `RESET`；reset token 用 password。
- 推荐测试：E2E 覆盖非法输入、404、chunk 失败、reset preview/execute、删除确认。
- 是否阻塞上线：正式产品或多人使用时阻塞。

### [R-019] 可访问性与状态公告不足

- 严重级别：Medium
- 类型：体验 / 可访问性
- 相关文件/位置：`frontend/src/styles.css:358`、`frontend/src/components/Sparkline.tsx:52`、`frontend/src/pages/WikiPage.tsx:512`
- 现象：输入框和 ResizeHandle 移除 outline，缺少统一 `:focus-visible`；loading/error/status 无 `role=status/alert`；SVG/Canvas graph 缺少文本替代。
- 复现或验证方式：静态阅读 CSS 和组件。
- 影响：键盘用户和屏幕阅读器用户难以使用；合规上线存在风险。
- 根因分析：缺少 a11y 设计和自动化检查。
- 修复建议：增加 focus-visible、aria-live、图表 `<title>/<desc>` 和表格 fallback；Wiki graph 提供键盘列表视图。
- 推荐测试：axe/Playwright a11y smoke；键盘全流程操作测试。
- 是否阻塞上线：有合规要求时阻塞。

### [R-020] 文档、许可证和发布物清单不足

- 严重级别：Medium
- 类型：文档 / 许可证
- 相关文件/位置：`README_DOCKER.md:18`、`README_DOCKER.md:23`、`src-tauri/Cargo.toml:6`
- 现象：Docker 文档提到旧容器名 `aiminer_app`；`.env.example` 缺少上线关键 token；根目录无 LICENSE/NOTICE；Tauri license 为空。
- 复现或验证方式：阅读文档和 Cargo manifest；`find . -iname "*license*"` 未发现根 LICENSE。
- 影响：他人无法可靠部署；商业/公开分发缺少许可证和第三方 notice。
- 根因分析：产品文档未随部署结构和发布形态更新。
- 修复建议：更新 Docker/部署/回滚文档；补 LICENSE、NOTICE、SBOM；生成第三方 license 清单。
- 推荐测试：按 README 从 clean checkout 复现部署；发布包包含 license/notice。
- 是否阻塞上线：对外分发或交给他人部署时阻塞。

## 6. 测试与验证结果

- 单元测试：仓库有 `tests/unit`，CI 目标为 `PYTHONPATH=. pytest tests/unit -m "unit and not external and not native" -q`；本次运行未获得最终通过结果，长时间无收敛，且产生 `data/test_db/kimi_embedding-2/chroma.sqlite3` 二进制改动。
- 集成测试：存在 `tests/integration/test_manual_strategy_runner.py`；未完整运行，避免真实外部服务和长任务。
- E2E 测试：未发现 Playwright/Cypress/Selenium 脚本。
- 类型检查：前端 `npm run build` 执行 `tsc -b && vite build`，通过。
- lint：未发现前端 `lint` 脚本；后端未发现 ruff/mypy 脚本。
- build：前端 build 成功；Docker build 和 Tauri packaging 未执行。
- 安全扫描：`npm audit` 因网络失败；`pip-audit` 未安装；`cargo audit` 未安装。
- 依赖检查：`python -m pip check` 失败，当前环境存在依赖冲突；`npm ls --depth=0` 成功。
- 结果总结：基础语法和前端 build 可通过，但测试、依赖扫描和容器级 smoke 不足以支撑正式上线。

## 7. 安全审计结果

- 认证与授权：默认 auth-disabled 是 Critical；多个读接口未鉴权；Admin reset 需要 `AIMINER_RESET_TOKEN` 是正向设计，但生产配置缺示例和门禁。
- 输入校验：Pydantic 枚举覆盖部分 runtime 字段；表达式 DSL 仍是最大风险；roles/content/expression 长度和任务规模缺少上限。
- 敏感信息：WebSocket query token、RiceQuant 用户标识日志、API token localStorage 都是风险点。
- 依赖漏洞：未能完成 CVE 扫描；依赖未锁定导致漏洞复现和修复追踪困难。
- 前端安全：未发现 `dangerouslySetInnerHTML`；`react-markdown` 未启用 `rehypeRaw` 是正向项；但 Tauri CSP 为 null。
- 后端安全：SQL 查询大多参数化；路径参数多数使用 `_safe_segment`；主要问题集中在 eval、auth、SSRF 和限流。
- API 安全：缺少 rate limit、body size limit、统一权限模型和审计关联 ID。
- 文件上传/下载：未发现通用上传接口；图表/报告读取路径拼接有 `_safe_segment`，但部分 chart path 来自 DB，应限制在 `CHART_DIR` 内。
- 日志与隐私：需要统一脱敏和访问控制，历史日志上线前应隔离或清理。

## 8. 性能与稳定性审计结果

- 前端性能：路由级 lazy loading 是正向项；Monaco/worker 体积大，Wiki/编辑路径首载慢；Nginx 无 gzip/brotli/immutable cache。
- 后端性能：列表接口内存分页；run/status/log 读取会扫描文件；日志广播串行发送给 socket。
- 数据库性能：SQLite 启用 WAL 和 busy timeout 是正向项；缺复合索引和 SQL 级分页。
- 并发与幂等：有 `MAX_CONCURRENT_SWARMS` 是正向项；缺幂等键、per-user 配额、heartbeat 和统一 deadline。
- 缓存：手工回测/策略有 job id/cache key；删除和缓存清理不完全一致。
- 超时/重试/限流：LLM client 有部分重试/timeout；worker、manual、strategy、local data 缺统一超时；API 无限流。
- 可观测性：无 metrics/tracing/alerting；必须补活跃 run、失败率、队列丢日志、DB locked、外部依赖失败率。

## 9. 数据与迁移风险

- schema/migration：schema 分散在 `api.py`、`manager.py`、`core/strategy.py`；无迁移版本和回滚脚本。
- 索引与约束：部分 timestamp/run_id 索引存在；无外键、严格 JSON 校验和 source-of-truth 约束。
- 数据一致性：`alpha_pool.json` 与 SQLite 不一致；策略删除可能遗留 cache-key 图表。
- 备份与恢复：未见正式备份/恢复脚本；`data/`、`results/`、`logs/` 都在 `.gitignore`，上线前必须快照。
- 回滚风险：如果未来 schema 变化，旧版本读取新 DB 未验证；manifest 不足以证明数据版本。

## 10. 部署与运维检查

- 环境变量：`.env.example` 缺 `AIMINER_AUTH_TOKEN`、`AIMINER_RESET_TOKEN`、生产 CORS 示例；当前 `.env` 是目录。
- CI/CD：CI 跑 Python syntax、unit、frontend build；未跑 Docker build、compose smoke、health、security scan、SBOM。
- Docker/容器：默认 root 运行；base image 未 pin digest；Rust `curl | sh`；Compose 用 `aiminer:latest`；无资源限制和 log rotation。
- health check：API 有 `/api/health`，但 Docker/Compose 未使用。
- 日志：Loguru 和 JSONL 存在；容器日志轮转、结构化字段、隐私脱敏不足。
- 监控：无 metrics/tracing/alerting。
- 报警：未见错误率、任务失败、外部依赖失败、磁盘增长报警。
- 回滚方案：文档未明确；必须保留不可变 image tag 和数据卷快照。

## 11. 产品体验检查

- 首次使用路径：README 有启动说明；Web 缺统一鉴权状态和服务连接状态。
- 错误状态：局部错误块存在；缺全局 401/403/500/404 和 ErrorBoundary。
- 空状态：多数列表有 “No ...” 提示；可进一步增加下一步操作建议。
- loading 状态：存在 loading 文案；缺 `aria-live` 和长任务进度指标。
- 移动端：CSS 有响应式媒体查询；三栏 Wiki/面板在移动端堆叠过长，需真机 smoke。
- 可访问性：焦点、图表、graph、状态公告不足。
- 文案与国际化：`html lang=zh-CN`，UI 大多英文，默认 roles/部分提示中文；日期和数字格式未统一。

## 12. 上线 Checklist

上线前必须完成：

- 生产鉴权 fail-closed，所有业务 API 默认授权。
- 移除或沙箱化表达式 `eval`，限制 `llm_base_url`。
- 禁止模拟结果进入真实 Alpha Pool。
- 修复 `.env`/secret、CORS、前端 API/WS base URL。
- 增加 Docker healthcheck、smoke test、日志轮转和基础监控。
- 生成 Python lockfile，固定 Git 依赖，Docker 构建保留 Rust lock。
- 备份 `data/`、`results/`、`logs/`，验证 SQLite quick_check 和 RAG 非空。
- 明确生产可开放的功能，至少限制 `/ops`、`qlib`、自定义 base URL、超大任务。

上线当天确认：

- 部署镜像使用不可变 tag，不只用 `latest`。
- `/api/health` healthy，无 token 核心 API 返回 401。
- `AIMINER_AUTH_TOKEN`、`AIMINER_RESET_TOKEN`、CORS、前端 base URL 与生产域名一致。
- `results/alpha_miner.db` 已备份，`data/local_futures` 校验通过。
- 活跃 Chroma collection 非空且能查询。
- active run 数、CPU、内存、磁盘、日志增长在阈值内。

上线后一周监控：

- API 5xx/4xx、p95/p99 latency、请求量。
- `/api/results`、`/api/strategies`、`/api/swarm/status`、`/api/swarm/runs/*/logs` 慢请求。
- active run 数、运行时长、failed/stopped/completed 比例、stopping 超时。
- Worker heartbeat、进程数、stop 回收耗时。
- SQLite busy/locked 次数、DB/WAL 大小、写入耗时。
- Log queue depth、drop count、WebSocket 连接数和断开率。
- RiceQuant/LLM/embedding 超时、429/5xx、重试次数。
- `data/`、`results/`、`logs/` 磁盘增长。
- 前端 LCP/INP、chunk 加载失败、Wiki/CodeEditor 加载耗时。

## 13. 建议的修复路线

P0：必须立刻处理

- 鉴权 fail-closed，并给所有业务读写 API 加授权。
- 替换表达式 `eval` 为白名单解释器，禁止 `pd/np` 模块对象暴露。
- 禁止生产模拟结果入池，失败即失败或标记 `partial_failed`。
- 修复 `.env`/secret 装载，补 `AIMINER_AUTH_TOKEN`、`AIMINER_RESET_TOKEN`。
- 增加 healthcheck、部署 smoke test、生产 CORS/base URL。
- 生成锁文件，固定 `pyqlib` commit，Docker 构建保留 `Cargo.lock`。
- 修复 SQLite/JSON source-of-truth 不一致，并验证 RAG active collection 非空。
- 长任务增加 deadline、heartbeat、幂等键和基本配额。

P1：上线前强烈建议处理

- SQL 级分页和复合索引。
- 本地数据加载增加规模上限、schema/日期下推和异常价格阻断。
- `llm_base_url` 白名单和 SSRF 防护。
- WebSocket ticket、日志脱敏、Docker 非 root、日志轮转、资源限制。
- 前端 404/ErrorBoundary、核心表单校验、危险操作强确认。
- Nginx 静态缓存/压缩，CodeEditor 按编辑模式 lazy load。
- Docker/README/.env.example/回滚文档更新。

P2：上线后短期处理

- metrics/tracing/Sentry/Prometheus 接入。
- RAG 预热和 readiness；embedding 服务化。
- Wiki 编辑 route blocker 和 sessionStorage 草稿。
- a11y 改进：focus-visible、aria-live、图表 fallback。
- Parquet/manifest 原子写入、删除软删除/manifest 驱动。
- 前端 lint/a11y/e2e 门禁。

P3：长期优化

- 拆分 `api.py` 为 router/service/repository/run manager。
- 统一 LLM JSON 解析模块。
- Run 状态迁移到 SQLite/Redis/队列系统，支持多 API worker。
- 正式迁移框架和 schema version。
- SBOM、license automation、依赖更新策略。

## 14. 附录

运行过的命令与结果摘要：

- `pwd`：成功。
- `git status --short`：初始 `?? PRODUCT_MANUAL.md`；审计后 `M data/test_db/kimi_embedding-2/chroma.sqlite3` 和 `?? PRODUCT_MANUAL.md`。
- `rg --files`、`find`、`sed`、`rg`：成功，用于结构和代码审计。
- `python -m py_compile api.py manager.py core/strategy.py tui.py`：成功。
- `npm run build`：成功，存在大 chunk 警告。
- `PYTHONPATH=. pytest tests/unit -m "unit and not external and not native" -q`：未收敛，未获得成功结果。
- `python -m pip check`：失败，依赖冲突。
- `npm audit`：失败，网络/DNS 受限。
- `pip-audit`：失败，模块未安装。
- `cargo audit`：失败，命令未安装。
- `docker compose config`：成功。
- `cargo metadata --no-deps --format-version 1`：成功。

Subagent 分工与结论摘要：

| Subagent | 方向 | 结论 |
|---|---|---|
| A | 架构与代码质量 | 后端巨石化、模拟结果入池、配置分散、schema 漂移是核心风险 |
| B | 功能正确性与测试覆盖 | 未完成，subagent shutdown；本地 pytest 也未收敛 |
| C | 安全 | 暂缓上线，安全等级 Critical |
| D | 性能稳定性 | 有条件上线；大数据、分页、长任务和幂等需修 |
| E | 数据与迁移 | 有条件上线；RAG 空库、SQLite/JSON 不一致需修 |
| F | 部署运维 | 不建议直接生产上线；auth、env、health、监控缺失 |
| G | 产品体验/a11y | 内部试用可用，正式产品需补表单、错误、危险操作和 a11y |
| H | 依赖/许可证/发布物 | 不建议正式发布；依赖不可复现、license/notice 缺失 |

无法验证项：

- 完整 unit/integration/e2e 通过性。
- Docker image 从 clean checkout 构建。
- CVE/OSV 依赖漏洞扫描。
- RiceQuant/LLM 真实链路。
- 浏览器真机、移动端、a11y 自动化。
- 生产环境健康检查和回滚演练。

建议补充的测试用例：

- 生产缺 token 启动失败；无 token 全 `/api/*` 返回 401。
- 表达式安全拒绝属性链、未知函数、超长/深度嵌套、跳过校验绕过。
- `llm_base_url` 私网/metadata/localhost 拒绝。
- 外部评估失败不入 alpha pool。
- SQL 分页大数据性能测试。
- 本地行情大文件超限和异常价格阻断。
- Run 幂等、heartbeat 超时、stop 回收。
- RAG active collection 非空 readiness。
- 备份恢复、schema 迁移、SQLite quick_check。
- 前端 404/ErrorBoundary、非法表单、危险操作确认、Wiki 草稿保护。

## 最终回答

1. 现在能不能上线？

不能按当前状态正式上线。内部单机、受控网络、无真实资金/交易决策场景可以短期试运行，但必须明确是“有重大安全与数据可信度风险的试运行”。

2. 如果只能修 3 个问题，应该修哪 3 个？

第一，修鉴权和授权：fail-closed、所有业务接口鉴权、生产 token/secret 门禁。第二，修表达式执行安全：替换 `eval` 或实现严格白名单解释器。第三，修生产可信度门禁：禁用模拟结果入池，同时修 `.env`/healthcheck/依赖 lock，确保部署可复现且可观测。

3. 如果今晚必须上线，最低限度要做哪些保护措施？

只允许 VPN/内网访问，不直接公网暴露；设置强 `AIMINER_AUTH_TOKEN` 和 `AIMINER_RESET_TOKEN`；反向代理再加一层 Basic Auth/IP allowlist；临时禁用 `/ops`、自定义 `llm_base_url`、`qlib` 路径和大规模任务；`AIMINER_MAX_CONCURRENT_SWARMS=1`；上线前快照 `data/`、`results/`、`logs/`；人工验证 `/api/health`、无 token 401、RAG 非空、DB 可读；安排值守监控 CPU/内存/磁盘/日志/外部依赖失败。

4. 上线后最应该监控哪些指标？

API 5xx/4xx、p95/p99 延迟、active run 数、run 失败率、stopping 超时、worker heartbeat、CPU/内存/磁盘、SQLite locked/WAL 大小、日志队列丢弃、WebSocket 断开率、RiceQuant/LLM/embedding 超时和 429/5xx、`data/results/logs` 增长、前端 chunk 加载失败和 Wiki/CodeEditor 加载耗时。

## 最小修复计划

等待确认后再进入修复阶段。建议第一阶段只做 P0：鉴权 fail-closed、表达式安全、模拟结果禁止入池、生产 env/healthcheck、依赖 lock 和数据 readiness。第二阶段做性能分页、任务 heartbeat/幂等、本地数据保护和前端错误/表单/危险操作兜底。
