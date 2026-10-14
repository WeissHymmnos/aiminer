# AI Alpha Miner

AI Alpha Miner 是一套面向公式化因子与量化策略研究的多智能体系统。系统以 `PortfolioManager` 作为顶层调度器，按研究方向（如量价反转、动量趋势、统计套利、期限结构等）启动多个 `AlphaResearcher` 子进程，在 LangGraph 状态机内独立完成假设生成、算子表达式编写、历史回测、策略转化与迭代修正，最终由主控层汇总筛选并构建低相关性的因子池与策略池。

除命令行批处理外，项目内置基于 FastAPI 与 React 的 Web 工作台，以及基于 Textual 的终端交互界面（TUI），支持手工因子回测、横截面与时序策略回测、Obsidian 风格的本地研究知识图谱浏览，以及运行态任务管理。

---

## 架构与工作流

单次多智能体研究运行（Swarm Run）包含以下阶段：

1. **知识检索与假说提出（`IdeaAgent`）**：结合 ChromaDB 向量检索（学术论文、WorldQuant 101、市场元数据）与本地 Markdown 知识库（`LLMWiki`），在指定角色与市场约束下生成可检验的量化假说。
2. **表达式编译与安全检查（`FactorAgent`）**：将研究假说转化为算子表达式，经白名单算子校验与 AST 安全变换（`SafeEvalTransformer`）后送入计算引擎，拒绝任意 Python 代码注入。
3. **因子回测与迭代（`EvalAgent`）**：在 RiceQuant、Qlib 或本地 Parquet/CSV 数据集上执行因子计算（支持 Pandas 与 Polars/Rust 原生插件加速），提取 IC、Rank IC、ICIR、多空夏普与换手率。若触发高显著性阈值（默认 `|IC| >= 0.05`）或连续未改进达到耐心上限（`patience = 3`），当前子任务自动收敛。
4. **交易策略验证（`StrategyAgent` & `StrategyCritic`）**：对通过筛选的因子生成横截面（Top-N、多空对冲、阈值）或时序（趋势多空、多头/空仓切换）交易配置，计入手续费、滑点与最短持有期约束后回测净值，并根据分时段表现修正策略参数。
5. **正交化筛选与因子杂交（`PortfolioManager`）**：主控层过滤低质量与模拟回退结果，按日收益率序列计算相关性矩阵，剔除同质化信号（默认相关系数阈值 `0.7`）；随后可选取头部父代因子执行一轮遗传杂交（Crossover），并将最终因子、策略、图表与运行清单（Manifest）写入 SQLite（`results/alpha_miner.db`）。

```text
PortfolioManager (manager.py)
  ├─ 派发 N 个角色任务 (ProcessPoolExecutor / ThreadPoolExecutor)
  │    └─ AlphaResearcher (sub_agent.py)
  │         └─ LangGraph 状态机 (app_workflow/graph.py)
  │              ├─ IdeaAgent      : RAG + LLMWiki 混合检索 -> 研究假说
  │              ├─ FactorAgent    : 假说 -> 算子表达式 + AST 白名单校验
  │              ├─ EvalAgent      : 因子回测 (RiceQuant / Qlib / Local)
  │              ├─ StrategyAgent  : 因子信号 -> 交易仓位回测 + Critic 参数修正
  │              └─ WikiUpdate     : 有效因子沉淀为 Markdown 知识卡片
  ├─ 因子池过滤 (IC 阈值 + 收益率序列正交化去重 + 因子生命周期衰减跟踪)
  ├─ 头部父代因子遗传杂交 (crossover.py)
  └─ 持久化至 SQLite (results/alpha_miner.db)、JSON 备份、图表与 Markdown 报告
```

---

## 环境安装

推荐使用 Conda 创建隔离环境（Python 3.10+），并以可编辑模式安装完整依赖栈：

```bash
conda env create -f environment.yml
conda activate aiminer
pip install -e ".[all]"
```

若仅需核心数据结构与基础脚本，可直接执行 `pip install -e .`；完整研究、回测、Web 与 TUI 功能包含在 `.[all]`（涵盖 `swarm`、`qlib`、`rq`、`tui`、`portfolio`、`web` 扩展组）中。

### 编译 Rust / Polars 算子插件（可选）

仓库下的 `polars_plugins/` 提供基于 Rust 编写的横截面与时序滚窗加速算子。本机安装 Rust 工具链与 `maturin` 后可编译安装：

```bash
cd polars_plugins && maturin develop --release
```

### 配置环境变量

复制环境变量模板并填入所需的模型密钥与行情凭证：

```bash
cp .env.example .env
```

常用配置项：

- **LLM 接口密钥**：支持 `ZHIPU_API_KEY`（智谱 GLM）、`KIMI_API_KEY`、`QWEN_API_KEY`、`DEEPSEEK_API_KEY`、`MIMO_API_KEY`、`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`OPENROUTER_API_KEY`、`GROQ_API_KEY` 等，系统会根据环境变量或命令行参数自动初始化客户端。
- **RiceQuant 凭证**：使用米筐线上数据或评估模式时，需配置 `RQ_TOKEN`，或同时配置 `RQ_USER` 与 `RQ_PASS`。
- **本地向量嵌入**：设置 `USE_LOCAL_EMBEDDING=true` 可改用本地 Sentence-Transformers 模型生成知识库向量，无需调用远端 Embedding 接口。
- **运行目录**：默认使用仓库根目录下的 `data/`、`results/` 与 `logs/`，可通过 `AIMINER_DATA_DIR`、`AIMINER_RESULTS_DIR`、`AIMINER_LOGS_DIR` 覆盖。

---

## 运行方式

安装完成后，可直接使用命令行入口（`aiminer-manager`、`aiminer`、`aiminer-api`、`aiminer-tui`），也可通过 `PYTHONPATH=src python -m aiminer.<module>` 运行。

### 1. 启动 Web 工作台

开发模式会同时拉起 FastAPI 后端（默认端口 `8000`）与 Vite 前端开发服（默认端口 `5173`），若端口占用会自动顺延并同步 CORS 配置：

```bash
./start_web.sh
```

生产模式仅启动 FastAPI 进程，由后端直接托管 `frontend/dist` 下的静态构建产物：

```bash
cd frontend && npm run build && cd ..
./start_web.sh --prod
```

`start_web.sh` 会统一导出 `AIMINER_DATA_DIR`、`AIMINER_RESULTS_DIR` 与 `AIMINER_LOG_DIR`，确保 API、Swarm 子进程、手工回测与前端读取同一套数据库和日志目录。

### 2. 命令行多智能体挖掘（Swarm）

并发启动多个指定研究方向的 Agent 执行因子挖掘：

```bash
PYTHONPATH=src python -m aiminer.manager \
  --iterations 5 \
  --mode ricequant \
  --engine polars \
  --llm-provider glm \
  --llm-model glm-4 \
  --roles "量价反转研究员" "宏观周期对冲研究员" "统计套利研究员" \
  --parallel \
  --wiki-bootstrap
```

常用参数说明：

- `--mode {ricequant,qlib}`：指定评估器协议。
- `--data-backend {ricequant,qlib,local}`：指定底层行情数据源。当使用本地 Parquet/CSV 时设为 `local`，并配合 `--local-data-path` 与 `--local-data-layout {auto,panel,instrument_files}`。
- `--market-profile {cn_stock,us_stock,futures}`：切换 A 股、美股或国内股指期货配置；多市场批处理可通过 `--market-mode {single,batch,mixed}` 与 `--market-profiles` 组合指定。
- `--engine {pandas,polars}`：在 `ricequant` 评估模式下选择 Pandas 或 Polars 算子执行引擎。
- `--disable-early-stop`：禁用高 IC 与耐心值提前终止，强制跑满 `--iterations` 轮。

### 3. 使用本地 Codex CLI 作为生成后端

若本机已安装并登录 `codex` CLI，可将其作为文本生成模型接入（仅负责文本推理，RAG 向量化需配合 `--embedding-provider local` 或其他 Embedding API）：

```bash
PYTHONPATH=src python -m aiminer.manager \
  --iterations 3 \
  --mode ricequant \
  --llm-provider codex \
  --llm-model gpt-5.4 \
  --llm-reasoning-effort xhigh \
  --embedding-provider local \
  --roles "量价反转研究员" \
  --parallel
```

系统通过 `codex exec` 在只读临时会话中调用本地 CLI。可通过环境变量 `AIMINER_CODEX_CMD` 指定可执行文件路径，`AIMINER_CODEX_TIMEOUT_SECONDS` 调整单次调用超时，`AIMINER_CODEX_REASONING_EFFORT`（`low` / `medium` / `high` / `xhigh`）设置默认推理强度。Web 工作台的启动表单同样支持上述参数。

### 4. 单智能体调试与终端工作台（TUI）

调试单个研究闭环或算子路由时，可运行单 Agent 入口：

```bash
PYTHONPATH=src python -m aiminer.main --iterations 3 --mode ricequant
```

在无浏览器环境或远程服务器上，可启动终端交互工作台浏览因子池、编辑表达式并触发回测：

```bash
PYTHONPATH=src python -m aiminer.tui
```

### 5. 接口鉴权与任务终止状态

在共享环境部署 Web/API 时，可通过环境变量开启访问控制：

```bash
export AIMINER_AUTH_TOKEN="your-secret-token"
```

在 Web 工作台左侧边栏填入该 Token 后，前端请求会自动携带 `Authorization: Bearer <token>` 与 `X-API-Key: <token>` 请求头。本机开发若未设置该变量，或显式设置 `AIMINER_DISABLE_AUTH=1`，则默认免鉴权。

Swarm 任务停止采用两阶段状态机：发出终止请求后状态先置为 `stopping`，待后台工作进程树确认退出后再收敛为 `stopped`。在 Web 或 TUI 中点击 `Stop Run` 后短暂显示 `Stopping...` 属于正常回收过程。

---

## 数据源与股指期货下载工具

系统支持三类行情后端：

- **RiceQuant（`ricequant`）**：通过 `rqdatac` 拉取 A 股或期货行情，适合在线研究与增量更新。
- **Qlib（`qlib`）**：读取本地 `~/.qlib/qlib_data/` 数据包，可通过 `python scripts/download_qlib_data.py` 初始化。
- **本地数据集（`local`）**：直接加载本地 CSV 或 Parquet 文件，支持面板格式（`panel`）与单标的独立文件（`instrument_files`）。

针对国内股指期货研究，仓库提供 `scripts/download_rq_index_futures.py`，可从 RiceQuant 批量拉取 `IF`、`IH`、`IC`、`IM` 的全量合约与主力连续合约（日线与分钟线），落盘为 Parquet 并自动执行完整性校验：

```bash
python scripts/download_rq_index_futures.py \
  --output data/local_futures \
  --start 2015-04-16 \
  --end 2026-04-17 \
  --frequencies 1d,1m \
  --underlyings IF,IH,IC,IM
```

可选参数包括 `--contracts-only`（仅实际合约）、`--dominant-only`（仅主力连续）、`--full-refresh`（全量重抓）、`--dry-run`（仅打印计划）、`--skip-validate`（跳过校验）以及 `--validate-skip-1m`（校验时仅检查日线）。输出目录结构如下：

```text
data/local_futures/
  ├─ contracts/1d/*.parquet
  ├─ contracts/1m/*.parquet
  ├─ dominant/1d/*.parquet
  ├─ dominant/1m/*.parquet
  └─ manifests/download_manifest.json
```

更多知识库抓取与维护脚本见 [scripts/README.md](./scripts/README.md)。

---

## Docker 部署

`docker-compose.yml` 默认仅常驻启动 `api` 服务（内置构建好的前端静态资源与 Rust Polars 插件），避免有限轮次的研究任务因容器重启策略反复执行：

```bash
docker compose up -d --build
```

启动一次性 Swarm 挖掘任务或进入容器化 TUI 时，使用对应的 Compose Profile：

```bash
AIMINER_ITERATIONS=5 docker compose --profile research run --rm worker
docker compose --profile tui run --rm tui
```

独立前端镜像构建与手动容器运行方式详见 [README_DOCKER.md](./README_DOCKER.md)。

---

## 测试与工作区清理

测试套件按依赖边界划分为三类 Pytest Marker：

```bash
# 1. 纯本地单元测试（CI 默认运行，不依赖外部凭证、网络或原生编译插件）
PYTHONPATH=src pytest tests/unit -m "unit and not external and not native" -q

# 2. 外部依赖测试（需配置 RiceQuant 凭证或网络访问）
PYTHONPATH=src pytest -m external -q

# 3. 原生插件测试（需先通过 maturin 编译安装 polars_plugins）
PYTHONPATH=src pytest -m native -q
```

也可运行 `python scripts/verify_ci_matrix.py` 一键检查语法编译、CI 配置、Ruff 代码规范与 Pytest 用例收集。

需要清理历史运行产物时，可使用 `scripts/reset_workspace.py`。该脚本默认为只读预览（dry-run），加上 `--confirm` 后才会将匹配文件移入回收目录 `results/.trash/<timestamp>/`：

```bash
python scripts/reset_workspace.py --scope runs
python scripts/reset_workspace.py --scope runs --confirm
```

支持的作用域包括 `pool`（因子与策略库）、`memory`（Wiki 知识库）、`rag`（Chroma 向量库）、`runs`（`results/swarm_runs` 运行记录）和 `all`。

---

## 文档索引与许可协议

- [PRODUCT_MANUAL.md](./PRODUCT_MANUAL.md)：产品功能手册、使用场景与 RustMiner 双轨架构说明
- [instruction.md](./instruction.md)：系统架构、模块实现、数据表结构与接口契约技术参考
- [README_DOCKER.md](./README_DOCKER.md)：容器化构建与部署指南
- [CONTRIBUTING.md](./CONTRIBUTING.md)：开发环境配置、目录结构与代码贡献规范
- [SECURITY.md](./SECURITY.md)：安全策略与表达式执行边界说明
- [docs/hermesagent_automation.md](./docs/hermesagent_automation.md)：HermesAgent 夜间定时任务配置说明

本项目基于 [GNU Affero General Public License v3.0 (AGPL-3.0-only)](./LICENSE) 开源，版权声明见 [NOTICE](./NOTICE)。
