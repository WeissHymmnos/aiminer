# AI Alpha Miner 产品与操作手册

> **双轨实现说明**：本项目提供 Python 实现（AI Alpha Miner，位于当前仓库）与原生 Rust 实现（RustMiner，位于 `~/Documents/finance/archive/rustminer`）。两者共享相同的数据目录布局、SQLite 表结构与 JSON 接口契约，可按场景单独或并行部署。关于 RustMiner 的对照说明见第 8 章。

---

## 1. 系统概述

AI Alpha Miner 是一套面向公式化因子挖掘与量化策略验证的研究工作台。系统将因子假说构思、表达式编写、回测检验、相关性正交化、交易策略转化与研究文档归档整合在同一套本地可控的环境中，支持通过 Web 界面、终端界面（TUI）、命令行（CLI）和 HTTP API 四种方式操作。

各运行入口职责如下：

| 入口 | 启动方式 | 适用场景 |
|---|---|---|
| Web 工作台 | `./start_web.sh` 或 `./start_web.sh --prod` | 日常交互研究：发起并监控 Swarm、浏览因子池、执行手工/策略回测、查看知识图谱 |
| Swarm 调度器 | `PYTHONPATH=src python -m aiminer.manager`（或 `aiminer-manager`） | 批量并发启动多个研究角色，自动执行多轮挖掘、去重与杂交 |
| 单智能体入口 | `PYTHONPATH=src python -m aiminer.main`（或 `aiminer`） | 针对单一角色或单条研究链路做快速验证与调试 |
| 终端工作台 (TUI) | `PYTHONPATH=src python -m aiminer.tui`（或 `aiminer-tui`） | 无浏览器服务器环境下的终端交互、因子查看与表达式回测 |
| HTTP / WS 服务 | `PYTHONPATH=src python -m aiminer.api`（或 `aiminer-api`） | 向前端、TUI 或外部平台提供 REST 接口与实时日志流 |

---

## 2. 核心功能模块

### 2.1 多智能体并行挖掘（Swarm）

在一次 Swarm 运行中，顶层调度器 `PortfolioManager` 会根据用户设定的研究角色（如“量价反转”、“动量趋势”、“统计套利”、“波动率微结构”、“期限结构”等）启动多个 `AlphaResearcher` 子任务。每个子任务在独立的 LangGraph 状态图中循环执行以下步骤：

1. **假说生成**：从 Chroma 向量库（学术文献、WorldQuant 101 因子、宏观与市场元数据）和 `LLMWiki` 检索上下文，提出本轮量化假说。
2. **算子编码与语法检查**：将假说翻译为算子表达式，通过算子与字段白名单校验及 AST 安全重写，拦截非法语法或未授权变量。
3. **因子回测与反馈反思**：计算 IC、Rank IC、ICIR、夏普比率与多空收益曲线；若指标未达标，结合评估反馈修正表达式进入下一轮迭代；若达到高显著性阈值（`|IC| >= 0.05`）或连续 3 轮无改善则提前收敛。
4. **策略衍生与调优**：对有效因子自动生成多组横截面或时序交易策略候选，回测净值并由 `StrategyCritic` 根据分时段回撤与换手表现微调参数。
5. **汇总筛选与遗传杂交**：主控层收集所有子任务产出，剔除模拟降级数据与低 IC 因子，按日收益率序列计算皮尔逊相关系数矩阵（默认剔除相关系数 `>= 0.7` 的同质化因子），对负 IC 因子自动翻转信号方向（`signal_multiplier = -1`），并选取头部父代因子执行遗传杂交（Crossover）。

同时，系统内置因子生命周期跟踪（`src/aiminer/core/lifecycle.py`）与可复现运行清单（`src/aiminer/core/manifest.py`），记录因子在后续评估中的衰减计数（Decay Streak）以及每次运行完整的数据集与环境元数据。

### 2.2 因子池管理（Alpha Pool）

通过主控筛选的因子统一存入 SQLite 数据库（`results/alpha_miner.db` 的 `alpha_pool` 表），并同步生成 `results/alpha_pool.json` 备份。每条因子记录包含因子 ID、所属 Run ID、角色来源、研究假说、算子表达式、核心指标（IC、Rank IC、夏普等）、每日收益率序列、净值曲线图路径、Markdown 评估报告路径，以及关联的最佳策略回测结果（`best_strategy`）。

研究员可在 Alpha Pool 页面对比不同因子的净值与指标，或一键将某条因子的表达式与最佳策略配置回填至策略回测台继续调参。

### 2.3 手工因子回测（Manual Backtest）

当研究员已有明确公式想法、仅需验证单个表达式而无需启动多智能体循环时，可通过手工回测模块直接测试。模块支持“先校验语法、再执行回测”的两步流程：

- **语法校验（Validate）**：检查算子名称、参数个数与行情字段是否合法，秒级返回诊断信息。
- **执行回测（Run）**：拉取指定市场与区间的行情数据，计算因子面板与前瞻收益，生成累计收益曲线与统计指标，并将结果存入手工回测历史。

### 2.4 策略回测（Strategy Backtest）

因子具备统计预测能力（IC 显著）并不直接等同于扣除交易成本后仍具备可执行收益。策略回测模块将二维因子信号面板转换为具体目标仓位，并在调仓周期、持仓上限、最短持有期与双边交易成本约束下核算净值。

内置五种基础策略模板，支持在表单模式与 JSON 高级编辑模式间切换：

| 模板标识 | 模式 | 方向与选股规则 | 适用信号特征 |
|---|---|---|---|
| `cs_top_bottom` | 横截面 (`cross_sectional`) | 多空对冲（做多 Top-N，做空 Bottom-N） | 截面区分度稳定、多空两端对称的选股因子 |
| `cs_top_only` | 横截面 (`cross_sectional`) | 纯多头（仅做多 Top-N） | 空头受限（如融券成本高）或多头端超额显著的股票因子 |
| `cs_threshold` | 横截面 (`cross_sectional`) | 阈值选股（信号突破阈值即入场） | 经过标准化或分位数映射的截面评分信号 |
| `ts_long_flat` | 时序 (`time_series`) | 多头/空仓择时（突破上轨做多，跌破退出线平仓） | 趋势跟踪或波段择时信号 |
| `ts_long_short` | 时序 (`time_series`) | 时序多空（突破上轨做多，跌破下轨做空） | 股指期货或具备双向交易条件的时序信号 |

可调参数涵盖：调仓频率（`daily` / `weekly` / `monthly`）、多空标的数量（`top_n` / `bottom_n`）、入场与退出阈值（`long_threshold` / `short_threshold` / `exit_threshold`）、最大持仓标的数（`max_positions`）、单票最大权重（`max_weight_per_position`）、最短持有天数（`min_holding_days`），以及佣金与滑点（`commission_bps` / `slippage_bps`）。

### 2.5 研究知识库与图谱（LLMWiki）

`data/wiki_vault/` 存放 Obsidian 风格的 Markdown 知识卡片。每次 Swarm 挖掘出的优质因子会自动生成带 YAML Frontmatter 与 `[[wikilink]]` 引用的卡片，并与基准市场状态页（`market_regime_base.md`）、策略分类页（`strategy_families_base.md`）及算子手册（`qlib_operator_guide.md`）建立关联。

Web 工作台的 `/wiki` 页面支持：

- 浏览与在线编辑 Markdown 页面（带未保存修改拦截与 GFM 渲染）
- 切换全局关系图（Global Graph）与当前节点一跳邻居局部图（Local Graph）
- 执行知识库格式检查（Lint）与旧版数据迁移（Migrate）

---

## 3. 操作界面说明

### 3.1 Web 工作台路由与视图

启动 `./start_web.sh` 后，浏览器默认打开 Web 工作台，主要包含以下视图：

- **`/`（Swarm Runs）**：配置并启动新的多智能体挖掘任务，查看当前活跃运行数、历史运行列表、有效因子产出统计，支持停止或清理历史运行。
- **`/runs/:runId`（Run Detail）**：通过 WebSocket（`/ws`）实时订阅单次 Swarm 的事件流与节点状态，查看本次运行产出的因子与策略摘要。
- **`/pool`（Alpha Pool）**：分页浏览全部入库因子，查看详情指标、净值缩略图（Sparkline）、完整评估报告，支持一键将因子带入策略回测页（Seed to Strategy）。
- **`/manual`（Manual Backtest）**：输入算子表达式、选择市场与回测区间，执行语法校验、回测计算与历史对比。
- **`/strategy`（Strategy Backtest）**：加载内置模板或自定义 JSON，执行横截面/时序策略回测，查看净值曲线、换手率曲线、最新持仓快照与交易统计（年化收益、夏普、最大回撤、胜率、平均持有期、成本拖累）。
- **`/wiki`（Wiki & Graph）**：三栏式知识库浏览、编辑与力导向图谱交互。
- **`/ops`（Workspace Ops）**：按作用域（`pool`、`memory`、`rag`、`runs`、`all`）预览并执行工作区清理，被清理文件安全移入 `results/.trash/<timestamp>/`。

### 3.2 终端工作台（TUI）

在终端执行 `PYTHONPATH=src python -m aiminer.tui` 可进入基于 Textual 的全键盘交互界面（支持 Vim 风格方向键导航），提供因子池与策略表浏览、内置代码编辑器、手工与策略回测触发，以及后台 Swarm 进程的启动与停止。

---

## 4. 数据源、市场配置与期货工具链

### 4.1 评估模式与数据后端

系统将“评估协议（`evaluation_mode`）”与“底层数据源（`data_backend`）”解耦：

- **数据源（`data_backend`）**：支持 `ricequant`（米筐在线接口）、`qlib`（本地 Qlib 数据目录）和 `local`（本地 CSV/Parquet 文件）。
- **市场配置（`market_profile`）**：内置 `cn_stock`（A 股）、`us_stock`（美股）和 `futures`（国内股指期货）。
- **多市场执行模式（`market_mode`）**：支持 `single`（单市场）、`batch`（按 `--market-profiles` 列表依次为每个市场派发完整角色组）和 `mixed`（跨市场混合分配）。

### 4.2 国内股指期货本地数据流

针对股指期货研究，可使用 `scripts/download_rq_index_futures.py` 将 `IF`、`IH`、`IC`、`IM` 的历史日线（`1d`）与分钟线（`1m`）拉取至本地 Parquet 目录：

```bash
python scripts/download_rq_index_futures.py \
  --output data/local_futures \
  --start 2015-04-16 \
  --end 2026-04-17 \
  --frequencies 1d,1m \
  --underlyings IF,IH,IC,IM
```

下载完成后，脚本默认会对合约连续性、字段完整性与时间轴顺序做本地校验。随后即可脱离在线接口，直接使用本地数据后端运行期货因子挖掘：

```bash
PYTHONPATH=src python -m aiminer.manager \
  --iterations 5 \
  --mode ricequant \
  --data-backend local \
  --market-profile futures \
  --local-data-path data/local_futures/dominant/1d \
  --engine polars \
  --parallel
```

此外，项目还提供专门的期货策略命令行入口 `aiminer-futures-strategy`（`src/aiminer/futures_strategy.py`），用于多品种期货面板合成与执行回测。

---

## 5. 常用工作流示例

### 场景一：从单表达式试错到多角色并行挖掘

初次接入新数据集或验证新研究方向时，建议按以下顺序推进：

1. 启动 `./start_web.sh` 打开 Web 工作台，进入 `/manual` 页面，用 1～2 个基础算子表达式（如滚窗均值或横截面排名）执行回测，确认行情读取与算子计算正常。
2. 命令行或 Web 首页发起小规模 Swarm（例如 2～3 个角色、每个角色迭代 3 轮），观察 `/runs/:runId` 实时日志流，确认假说生成与回测反馈闭环运转正常。
3. 在 `/pool` 中挑选高 IC、低相关性的有效因子，点击“Seed to Strategy”跳转至 `/strategy`，测试不同调仓周期与费率假设下的净值表现。
4. 将经过策略验证的因子结论补充至 `/wiki` 知识页，供后续 Swarm 检索复用。

### 场景二：团队内网共享部署

在实验室服务器或团队内网部署时，建议开启 API Token 鉴权并使用生产模式或 Docker 容器运行：

```bash
export AIMINER_AUTH_TOKEN="team-shared-secret-token"
export AIMINER_MAX_CONCURRENT_SWARMS=2
./start_web.sh --prod
```

团队成员在浏览器打开工作台后，于左侧边栏填入 `API Token` 即可正常发起回测与挖掘任务；未携带有效 Token 的写操作请求将被后端拒绝。

---

## 6. 环境变量与配置参考

| 变量名 | 说明 | 默认值 / 示例 |
|---|---|---|
| `ZHIPU_API_KEY` / `GLM_KEY` | 智谱 GLM 接口密钥 | - |
| `KIMI_API_KEY` / `LLM_KEY` | Moonshot Kimi 接口密钥 | - |
| `QWEN_API_KEY` | 通义千问接口密钥 | - |
| `DEEPSEEK_API_KEY` | DeepSeek 接口密钥 | - |
| `MIMO_API_KEY` / `MIMO_BASE_URL` | 小米 MiMo 接口密钥与地址 | `https://token-plan-cn.xiaomimimo.com/v1` |
| `OPENAI_API_KEY` / `OpenAI_KEY` | OpenAI 兼容接口密钥 | - |
| `ANTHROPIC_API_KEY` / `ClaudeCode_KEY` | Anthropic Claude 接口密钥 | - |
| `OPENROUTER_API_KEY` / `GROQ_API_KEY` | OpenRouter / Groq 接口密钥 | - |
| `AIMINER_CODEX_CMD` | 本地 Codex CLI 可执行文件路径 | `codex` |
| `AIMINER_CODEX_TIMEOUT_SECONDS` | Codex 单次调用超时秒数 | `300` |
| `AIMINER_CODEX_REASONING_EFFORT` | Codex 默认推理强度（`low`/`medium`/`high`/`xhigh`） | - |
| `RQ_TOKEN` 或 `RQ_USER` + `RQ_PASS` | RiceQuant 行情凭证 | - |
| `USE_LOCAL_EMBEDDING` | 是否使用本地模型计算 RAG 向量 | `false` |
| `AIMINER_DATA_DIR` | 数据与知识库根目录 | `data` |
| `AIMINER_RESULTS_DIR` | 数据库、图表、报告与运行记录目录 | `results` |
| `AIMINER_LOGS_DIR` / `AIMINER_LOG_DIR` | 日志输出目录 | `logs` |
| `AIMINER_AUTH_TOKEN` | HTTP / WebSocket 接口访问令牌 | 未设置时默认免鉴权 |
| `AIMINER_DISABLE_AUTH` | 显式关闭接口鉴权 | `false` |
| `AIMINER_CORS_ORIGINS` | 允许跨域访问的前端源列表（逗号分隔） | 本地 `8000` 与 `5173` 端口 |
| `AIMINER_MAX_CONCURRENT_SWARMS` | 允许同时运行的 Swarm 任务上限 | `1` |
| `AIMINER_SWARM_GLOBAL_TIMEOUT_SECONDS` | 并行 Swarm 全局超时秒数（`0` 表示不限制） | `600` |

---

## 7. 产物目录结构

```text
aiminer/
  ├─ data/
  │    ├─ rag_docs/          # 学术论文、WorldQuant 101、宏观新闻与市场元数据语料
  │    ├─ wiki_vault/        # Obsidian 风格 Markdown 知识卡片
  │    ├─ wiki_db/           # LLMWiki 向量索引 (ChromaDB)
  │    ├─ chroma_db/         # RAG 文献向量索引 (ChromaDB)
  │    └─ local_futures/     # 本地股指期货 Parquet 数据集
  ├─ results/
  │    ├─ alpha_miner.db     # 核心 SQLite 数据库（含 alpha_pool、strategy_backtests、agent_checkpoints 等表）
  │    ├─ alpha_pool.json    # 因子池 JSON 镜像备份
  │    ├─ swarm_runs/        # 单次 Swarm 运行的 Manifest (.json) 与事件流 (.jsonl)
  │    ├─ strategies/        # 策略回测详情 JSON、缓存与净值/换手图表
  │    ├─ charts/            # 因子回测净值曲线 PNG
  │    ├─ reports/           # 因子评估 Markdown 报告
  │    └─ .trash/            # reset_workspace.py 移入的可恢复历史产物
  └─ logs/
       ├─ backend.log        # Web API 后端日志
       └─ frontend.log       # Vite 开发服日志
```

---

## 8. RustMiner：原生 Rust 双轨实现

### 8.1 定位与架构差异

`RustMiner`（位于 `~/Documents/finance/archive/rustminer`）是 AI Alpha Miner 的全量 Rust 原生实现。它与当前仓库的 Python 版本共享相同的目录结构、SQLite 表定义与 JSON 接口契约，可在同一工作区并行读写。两者的技术栈对照如下：

| 维度 | AI Alpha Miner (Python) | RustMiner (Rust) |
|---|---|---|
| 运行时与并发 | CPython 3.10+（多进程绕过 GIL） | 原生编译二进制，多线程 + `mpsc` 通道 |
| 行情与算子引擎 | Pandas / Polars + Qlib / RiceQuant | 原生 Arrow / Parquet 列式求值器（不依赖 Qlib 运行时） |
| 工作流状态机 | LangGraph 状态图 | `WorkflowNode` 枚举状态机 + 纯函数路由 |
| HTTP 服务 | FastAPI + Uvicorn | Axum 0.7 异步多线程服务 |
| 图表绘制 | Matplotlib | Plotters 原生 PNG 渲染 |
| 数据存储 | Python `sqlite3` | `rusqlite`（内置 bundled `libsqlite3`） |
| 分发形态 | Conda 环境 + Python 包 | 单一静态可执行文件（约 20 MB） |

Python 版本适合快速修改提示词、扩展实验算子、调用 RiceQuant Python SDK 或接入 PyData 科学计算生态；RustMiner 则适合追求高并发吞吐、零环境依赖分发、快速冷启动与大批量 Arrow 原生求值的生产环境。

### 8.2 渐进切流与一致性校验（Parity & Cutover）

RustMiner 内置了从 Python 向 Rust 平滑迁移的校验与切流工具：

1. **Plan / Execute 预演机制**：每个核心子命令均支持 `plan`（仅输出预期副作用 JSON 而不执行实际 I/O）与 `run`/`serve`（实际执行）两种模式，便于在 CI/CD 中验证执行计划。
2. **输出一致性比对（Parity Compare）**：直接比对 Python 与 Rust 针对同一输入的输出 JSON，校验数值误差是否在容差范围内：
   ```bash
   rustminer parity compare python_output.json rust_output.json --tolerance 1e-6
   ```
3. **分阶段切流评估（Cutover Readiness）**：按 `cli` → `api` → `swarm_manager` 三个入口阶段与九道校验关卡评估切流就绪度及回滚能力：
   ```bash
   rustminer cutover readiness --switched cli,api,swarm_manager --rollback-ready --native-only
   ```

常用 RustMiner 命令速查：

```bash
rustminer help                                    # 查看命令列表
rustminer cli plan|run [选项]                     # 单智能体工作流
rustminer manager plan|run [选项]                 # 多智能体 Swarm 调度
rustminer api plan|serve [选项]                   # 启动 Axum HTTP API 服务
rustminer tui [snapshot]                          # 启动终端交互工作台
rustminer parity compare <PYTHON> <RUST> [选项]   # 跨语言结果一致性比对
rustminer cutover readiness                       # 切流就绪度评估
```
