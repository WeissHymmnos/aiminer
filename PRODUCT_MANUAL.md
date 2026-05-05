# AI Alpha Miner 产品手册

> **双轨产品线**：本项目提供 Python 参考实现（AI Alpha Miner）和 Rust 生产实现（RustMiner，位于 `~/Documents/rustminer`）。两者共享同一套数据格式、SQLite schema 和 JSON 契约，可根据场景选用或并行部署。详见第 12 章。


## 1. 产品定位

AI Alpha Miner 是一套面向量化研究场景的多 Agent 因子挖掘与验证工作台。

它把传统上分散在“想法讨论、因子表达、回测验证、组合筛选、策略落地、研究记录”中的工作串成一个闭环，核心目标是：

- 让多个具备不同研究偏好的 AI 研究员并行工作
- 把因子挖掘从“单次试错”升级为“持续迭代”
- 把研究结果沉淀为可回看、可复盘、可筛选的资产
- 同时提供 Web、API、TUI 三种操作面，适应不同使用习惯

从产品形态上看，它是一整套研究平台，包含脚本入口、服务接口和交互式工作台：

- `manager.py`：Swarm 调度入口
- `main.py`：单 Agent 工作流入口
- `api.py`：HTTP API 与前端托管入口
- `tui.py`：终端工作台入口
- `frontend/`：Web 工作台

## 2. 适用对象

这个项目主要适合以下几类用户：

- 量化研究员：希望快速生成、验证和筛选 Alpha 因子
- 研究负责人：希望并行组织多个研究方向，并统一查看产出
- 策略开发者：希望把因子进一步转为横截面或时序策略并评估
- 需要本地化部署的团队：希望把数据、日志、结果与鉴权放在可控环境中

## 3. 产品核心价值

### 3.1 多 Agent 协作，而不是单点问答

系统允许一次启动多个“研究角色”，每个角色围绕不同风格进行因子探索，例如：

- 量价反转
- 动量趋势
- 统计套利
- 宏观周期
- 高频微结构

这些角色可以并发运行，也可以串行运行。由管理器统一筛选、汇总、去重和沉淀。

### 3.2 研究闭环完整

系统覆盖的不是“生成一个表达式”，而是完整研究链路：

1. 形成研究假设
2. 生成因子表达式或代码
3. 发起回测与评估
4. 判断有效性
5. 进行自我反思和下一轮改进
6. 汇总结果并形成报告

### 3.3 因子池强调“质量 + 差异化”

系统除了关注单个指标表现，还会通过收益相关性做正交化筛选，避免最终留下来的 Alpha 池过于同质化。对实际研究团队来说，这种方式更接近真实工作流。

### 3.4 一套系统，覆盖研究、验证、沉淀、展示

项目既有自动化挖掘，也有手工回测、策略回测、Wiki 知识页、运行日志、历史记录、图表与报告归档，因此它更接近“量化研究工作台”，而不是一个单点工具。

## 4. 产品能力总览

### 4.1 自动挖掘 Swarm

自动挖掘是本项目的主能力。用户可以在命令行、Web 工作台或 TUI 中发起一次 Swarm 研究任务，并配置：

- 迭代次数
- 研究角色
- 是否并行
- LLM Provider / Model
- 数据后端
- 市场配置
- 回测引擎

Swarm 运行后，系统会：

- 调度多个子 Agent 执行研究循环
- 收集每个角色的候选因子
- 评估因子有效性
- 执行相关性筛选
- 生成摘要报告
- 持久化到数据库和结果目录

### 4.2 Alpha Pool 因子池

Alpha Pool 是系统的“研究资产池”。它保存已经通过一轮筛选的因子成果，便于后续查看、对比、复用和转策略。

因子池中通常会保留如下信息：

- 因子 ID
- 角色来源
- 假设描述
- 因子代码/表达式
- IC、Rank IC、绩效指标
- 报告路径
- 运行时间
- 所属 Run ID
- 是否有效
- 策略回测关联结果

它适合作为研究团队内部的“候选因子库”。

### 4.3 Manual Backtest 手工回测

除了自动挖掘，系统也支持人工输入表达式做快速验证。这个能力适合：

- 研究员已经有明确想法，只想先验证
- 不想启动完整 Swarm，只想测单个表达式
- 希望调试表达式写法或数据适配问题

系统支持先做表达式校验，再运行回测，并保留历史记录。

### 4.4 Strategy Backtest 策略回测

项目不仅停留在“因子有没有预测性”，还允许把因子转换为交易策略进行进一步验证。

当前支持的策略模板包括：

- 横截面 Top/Bottom 多空
- 横截面 Top-N 多头
- 横截面阈值多头
- 时序阈值 Long/Flat
- 时序阈值 Long/Short

可配置项覆盖：

- 横截面或时序模式
- 做多、做空或空仓逻辑
- 选股规则
- 调仓频率
- 持仓数量
- 单票权重上限
- 最短持有期
- 手续费
- 滑点
- 回测区间
- 引擎选择

这使得系统能够从“研究表达式”进一步推进到“策略可执行性评估”。

### 4.5 Wiki / 知识沉淀

项目内置 Wiki 相关能力，用于沉淀研究结论、页面内容和知识图谱关系。系统支持：

- 查看 Wiki 索引
- 查看单页内容
- 编辑页面
- Lint 校验
- Wiki 迁移
- 图谱关系查看

这部分能力更偏“研究知识管理”，适合把阶段性成果变成长期资产。

### 4.6 Web 工作台

Web 工作台提供更完整的操作入口，当前页面结构包括：

- `/`：Swarm Runs，查看和发起自动挖掘
- `/runs/:runId`：单次 Swarm 运行详情
- `/pool`：Alpha Pool 因子池
- `/manual`：手工回测
- `/strategy`：策略回测
- `/wiki`：Wiki 页面与图谱
- `/ops`：运维/管理页

对多数用户而言，Web 工作台是最适合的日常入口。

### 4.7 TUI 终端工作台

项目同时提供 Textual 构建的 TUI，适合以下场景：

- 服务器环境没有浏览器
- 习惯在终端内完成研究操作
- 想快速看日志、切换页面、编辑表达式、发起回测

TUI 支持：

- 自动探测 API 地址
- 使用 Token 访问受保护接口
- 查看 Swarm 状态与日志
- 运行手工回测
- 编辑代码/表达式
- 读取数据库结果

### 4.8 API 能力

API 面向前端、TUI 或外部集成，主要接口能力包括：

- 健康检查
- 结果列表与单因子详情
- 图表与报告读取
- Wiki 读写与检查
- 手工回测校验、执行、历史查询、删除
- 策略回测执行、历史查询、详情读取、删除
- Swarm 状态查询
- Swarm 运行列表、创建、详情、日志、停止、删除
- WebSocket 实时事件流
- 静态前端托管

如果团队需要把 AIMiner 嵌入自有平台，这一层是最直接的对接面。

### 4.9 多数据后端与多市场配置

系统支持的数据/评估模式不是单一的，当前可见能力包括：

- `qlib`
- `ricequant`
- `local`

市场配置支持：

- `cn_stock`
- `us_stock`
- `futures`

运行模式支持：

- `single`
- `batch`
- `mixed`

这意味着项目既可服务于标准股票因子研究，也支持本地数据或期货场景扩展。

### 4.10 数据下载与本地化数据流

项目包含 RiceQuant 国内股指期货数据下载 CLI，可下载：

- 实际合约数据
- 主力连续数据
- 日线与分钟线

默认覆盖：

- `IF`
- `IH`
- `IC`
- `IM`

并以 Parquet 形式落入本地目录，适合本地回测与研究工作流。

## 5. 典型使用案例

### 案例 1：研究负责人组织多角色因子挖掘

目标：在一个研究主题下，同时让多个不同风格的 Agent 探索可用因子。

典型做法：

1. 设定 3 到 5 个角色，例如反转、动量、统计套利、宏观周期。
2. 设定迭代轮数，例如 3 到 5 轮。
3. 选择数据后端，例如 `ricequant`。
4. 通过 Web 或命令行发起 Swarm。
5. 在运行过程中观察日志和阶段状态。
6. 任务结束后在 Alpha Pool 中查看保留下来的正交化结果。

适合的命令示例：

```bash
python manager.py --iterations 5 --mode ricequant \
  --llm-provider glm --llm-model glm-4 \
  --roles "专注量价反转的专家" "宏观周期对冲专家" "统计套利专家" \
  --parallel
```

预期产出：

- 多个候选因子
- 汇总报告
- 低相关性的因子池
- 数据库与结果目录中的结构化记录

### 案例 2：研究员快速验证一个手写表达式

目标：不启动完整 Swarm，只验证单个表达式是否可算、是否有效。

典型做法：

1. 打开 Web 工作台中的 Manual Backtest 页面。
2. 输入表达式，例如动量、反转或量价组合表达式。
3. 先执行表达式校验。
4. 通过后执行回测。
5. 查看指标、曲线和历史记录。

这个场景适合：

- 日常研究中的快速试错
- 校验想法是否值得进入大规模 Swarm
- 比较多个表达式的初步表现

### 案例 3：把因子进一步变成策略

目标：验证“因子有效”是否能够进一步转化为“策略可执行”。

典型做法：

1. 在 Strategy Backtest 页面选择或输入因子表达式。
2. 选择策略模板，例如 Top/Bottom Long-Short。
3. 调整调仓频率、持仓数、成本、阈值等参数。
4. 发起策略回测。
5. 查看策略指标、持仓、收益曲线与历史记录。

这个场景适合：

- 从研究信号进入策略化验证
- 比较不同执行模板对同一因子的影响
- 识别“纸面上有效，但交易上不成立”的因子

### 案例 4：用本地期货数据做扩展研究

目标：将系统用于国内股指期货的本地研究流程。

典型做法：

1. 先通过数据下载 CLI 拉取本地期货数据。
2. 将数据落到 `data/local_futures`。
3. 运行时将数据后端切到 `local`，市场切到 `futures`。
4. 用手工回测或 Swarm 方式进行研究。

示例命令：

```bash
python scripts/download_rq_index_futures.py \
  --output data/local_futures \
  --start 2015-04-16 \
  --end 2026-04-17 \
  --frequencies 1d,1m \
  --underlyings IF,IH,IC,IM
```

这个场景适合：

- 不希望完全依赖在线数据接口
- 需要分钟级或本地归档数据
- 研究股票以外的市场

### 案例 5：团队内网部署与权限控制

目标：把系统作为团队内部研究平台部署，并对接口做简单鉴权。

典型做法：

1. 在 `.env` 或环境变量中设置 API Key、RiceQuant 凭证等。
2. 设置 `AIMINER_AUTH_TOKEN` 作为访问令牌。
3. 用 `./start_web.sh` 或 `docker compose up -d --build` 启动。
4. 前端侧通过 Token 访问 API。
5. 运维或管理人员通过 `/ops` 页面做清理与维护。

这个场景适合：

- 本地实验室服务器
- 研究组共享环境
- 对外网暴露前需要先做最低限度访问控制的场景

## 6. 功能说明

### 6.1 自动挖掘流程说明

一次标准 Swarm 运行通常包含以下阶段：

1. 初始化运行配置
2. 组装多个研究角色
3. 为每个角色启动研究任务
4. 子 Agent 执行“研究 -> 代码 -> 回测 -> 反思”的微循环
5. 管理器收集结果并进行筛选
6. 对候选因子做相关性裁剪
7. 生成摘要报告并持久化
8. 在 Web/TUI/API 中暴露结果

停止运行时，系统使用两阶段状态：

- `stopping`
- `stopped`

因此点击停止后短暂看到 `Stopping...` 属于预期行为。

### 6.2 结果持久化说明

系统会把运行结果写入数据库和文件系统，典型产出包括：

- 因子池记录
- 策略回测记录
- 图表文件
- Markdown 报告
- JSON 结果
- Swarm 运行日志
- Wiki 页面内容

从产品使用角度看，这意味着研究结果不是“看完就没了”，而是可以长期沉淀与复用。

### 6.3 运行管理说明

系统支持对运行过程进行管理，包括：

- 查看当前 Swarm 状态
- 查看历史 Runs
- 查看单次 Run 的详情与日志
- 停止某次运行
- 删除某次运行记录

这类能力在多人共用环境中特别重要，因为它让系统从“会跑”升级为“可运营”。

### 6.4 鉴权说明

如果启用鉴权，需要设置：

```bash
export AIMINER_AUTH_TOKEN="your-token"
```

前端会通过以下方式附带令牌：

- `Authorization: Bearer <token>`
- `X-API-Key: <token>`

如果未配置 Token，系统可进入无鉴权模式，适合本机开发环境。

## 7. 使用方式

### 7.1 本地环境安装

```bash
conda env create -f environment.yml
conda activate aiminer
pip install -r requirements.txt
```

### 7.2 启动 Web 工作台

开发模式：

```bash
./start_web.sh
```

生产模式：

```bash
./start_web.sh --prod
```

脚本会统一设置：

- `AIMINER_DATA_DIR`
- `AIMINER_RESULTS_DIR`
- `AIMINER_LOG_DIR`

这样 API、Manager、手工回测和 Web 工作台会共用同一套数据与结果目录。

### 7.3 启动 TUI

```bash
python tui.py
```

### 7.4 启动单 Agent 工作流

```bash
python main.py --iterations 1 --mode ricequant
```

### 7.5 启动多 Agent Swarm

```bash
python manager.py --iterations 3 --mode ricequant --parallel
```

### 7.6 Docker / Compose 启动

仅启动 API 服务：

```bash
docker compose up -d --build
```

启动一次性研究 Worker：

```bash
AIMINER_ITERATIONS=5 docker compose --profile research run --rm worker
```

启动 TUI 容器：

```bash
docker compose --profile tui run --rm tui
```

## 8. 关键配置项

### 8.1 LLM 配置

项目支持多种 LLM Provider，当前代码和文档中可见的选项包括：

- `kimi`
- `qwen`
- `claude`
- `glm`
- `openai`
- `deepseek`
- `mimo`
- `openrouter`
- `groq`
- `ollama`
- `vllm`
- `lmstudio`
- `codex`

示例环境变量：

- `KIMI_API_KEY`
- `QWEN_API_KEY`
- `ZHIPU_API_KEY`
- `MIMO_API_KEY`
- `MIMO_BASE_URL`
- `OpenAI_KEY`
- `ClaudeCode_KEY`

### 8.2 数据与账号配置

RiceQuant 凭证可通过以下环境变量提供：

- `RQ_USER`
- `RQ_PASS`
- `RQ_TOKEN`

### 8.3 鉴权与访问配置

- `AIMINER_AUTH_TOKEN`
- `AIMINER_DISABLE_AUTH`
- `AIMINER_CORS_ORIGINS`

### 8.4 本地推理与嵌入配置

- `USE_LOCAL_EMBEDDING`
- `AIMINER_CODEX_CMD`
- `AIMINER_CODEX_TIMEOUT_SECONDS`
- `AIMINER_CODEX_REASONING_EFFORT`

## 9. 产品输入与输出

### 9.1 主要输入

系统的输入通常包括：

- 研究角色描述
- 迭代次数
- 因子表达式
- 策略配置
- 市场配置
- 数据源配置
- LLM 与嵌入配置
- 本地数据目录或在线凭证

### 9.2 主要输出

系统的输出通常包括：

- 因子候选与精选池
- 回测指标
- 收益曲线与图表
- 策略回测结果
- 研究报告
- Wiki 页面
- 数据库存档
- 日志与运行记录

### 9.3 典型目录

- `data/`：原始数据、Wiki、向量库等
- `results/`：研究结果、图表、数据库、运行记录
- `logs/`：后端与前端日志

## 10. 推荐使用流程

对于第一次使用这个项目的团队，推荐流程如下：

1. 先配置 `.env` 与基础凭证。
2. 用 `./start_web.sh` 启动 Web 工作台。
3. 先在 Manual Backtest 页面验证 1 到 3 个表达式。
4. 再启动小规模 Swarm，例如 2 到 3 个角色、1 到 3 轮迭代。
5. 到 Alpha Pool 查看沉淀结果。
6. 对优质因子继续做 Strategy Backtest。
7. 把有价值的结论整理到 Wiki。

这个顺序的优点是：

- 风险更低
- 成本更可控
- 更容易定位配置、数据或表达式问题
- 更符合真实研究团队的试运行节奏

## 11. 这个产品最适合怎样的团队

如果团队符合以下特征，这个项目会比较合适：

- 已经有一定量化研究基础
- 想把 AI 从“聊天助手”升级为“研究执行者”
- 需要同时保留自动化能力和人工干预空间
- 需要可视化工作台，但又不想放弃命令行和 API
- 希望研究成果长期积累，而不是一次性实验

如果团队当前只需要“单个表达式能不能算”，那可以先只使用 Manual Backtest；如果团队已经在做多研究方向并行探索，Swarm 与 Alpha Pool 的价值会更明显。

## 12. RustMiner —— 下一代 Rust 重写

### 12.1 概述

RustMiner（`~/Documents/rustminer`）是 AI Alpha Miner 的完整 Rust 重写版本，目标是在保持 Python 版本全部研究能力的同时，提供原生编译性能、单二进制分发和更强的工程可靠性。

从产品演进角度，RustMiner 不是替代品，而是同一产品线的第二阶段——Python 版本侧重快速迭代和生态兼容，Rust 版本侧重生产部署和长期维护。

### 12.2 架构对比

| 维度 | AI Alpha Miner (Python) | RustMiner (Rust) |
|---|---|---|
| 语言运行时 | CPython 3.10+, GIL 受限 | Rust 编译原生二进制, 多线程 |
| 代码规模 | ~50K+ Python | ~66K Rust (29 模块 + 7 模型子模块) |
| 数据加载 | Polars/Pandas CSV/Parquet | Arrow/Parquet 原生列式读取 |
| 因子求值 | Polars 引擎 / Qlib / RiceQuant | Rust 原生 Arrow 列式求值器 |
| 工作流引擎 | LangGraph 状态图 | 自定义 WorkflowNode 枚举 + 纯函数路由 |
| LLM 客户端 | httpx + LangChain | ureq (阻塞 HTTP) + 自研 JSON 解析 |
| HTTP 服务 | FastAPI + uvicorn | Axum 0.7 (异步多线程) |
| 图表渲染 | matplotlib | plotters (原生 PNG) |
| 数据库 | Python sqlite3 | rusqlite (bundled libsqlite3) |
| 分发方式 | conda 环境 + pip | 单静态二进制 (~20MB) |
| 测试体系 | pytest | cargo test (679+ 内联测试) |

### 12.3 RustMiner 独有能力

以下能力是 RustMiner 原生支持而 Python 版本不具备的：

**a. Phase 10 渐进切流框架**

一套形式化的迁移框架，支撑从 Python 到 Rust 的渐进式替换：

- `CutoverEntrypoint`：三个阶段 (`Cli`, `Api`, `SwarmManager`)，每个阶段有序前置依赖
- `CutoverGate`：九个顺序关卡，包括 SharedFixturesParity、SelectedRealRunsParity、ParityMetrics、RollbackPath、NativeOnlyRuntime
- `CutoverEvidence`：每关的结构化 JSON 证据，带 git SHA 锁定
- `cutover readiness` CLI 命令：评估当前切流状态、已通过关卡、是否可回滚

```bash
rustminer cutover readiness --switched cli,api,swarm_manager --rollback-ready --native-only
```

**b. Plan/Execute 效果 DSL**

15 种 `AdapterEffect` 变体，把所有副作用描述为数据：

- 每个入口命令都有 `plan` 变体（返回 JSON 描述预期效果）和 `run`/`serve` 变体（实际执行）
- `RecordingAdapterExecutor` 支持在不执行 I/O 的情况下测试副作用计划
- 适合 CI/CD 流水线中的预演验证

**c. Parity 一致性测试**

`parity compare` CLI 命令对比 Python 与 Rust 产出的 JSON 文件：

```bash
rustminer parity compare python_output.json rust_output.json --tolerance 1e-6
```

五套 parity 套件覆盖 SharedFixtures、SelectedRealRuns、ApiResponses、CliArtifacts、SwarmArtifacts。

**d. 原生二进制分发**

编译为单一静态可执行文件，无需 Python 运行时、conda 环境或 pip 依赖。预构建二进制覆盖 Linux x86_64 和 macOS ARM64/Intel。

**e. Qlib 策略差异**

Python 版本完整支持 Qlib 作为数据后端和表达式运行时。RustMiner 明确拒绝 Qlib 运行时——Qlib 仅作为表达式语法参考保留兼容性。这意味着：

- `--mode qlib` 在 RustMiner 中不可用
- 所有因子求值走 Rust 原生 Arrow 引擎
- 不需要安装 Qlib 或其 Python 依赖

### 12.4 RustMiner CLI 命令参考

```bash
rustminer help                                    # 查看所有命令
rustminer cutover readiness                       # 切流状态评估
rustminer cli plan|run [选项]                     # CLI 工作流
rustminer manager plan|run [选项]                 # Manager Swarm 调度
rustminer api plan|serve [选项]                   # HTTP API 服务
rustminer swarm plan [选项]                       # Swarm 执行计划
rustminer tui [snapshot]                          # 终端工作台
rustminer parity compare <PYTHON> <RUST> [选项]   # 一致性对比
```

### 12.5 迁移路径

对于已经在使用 Python 版本的团队，推荐的迁移策略：

1. **评估阶段**：运行 `rustminer cutover readiness` 了解当前切流就绪状态
2. **验证阶段**：使用 `rustminer parity compare` 对比同一输入的 Python/Rust 产出
3. **试运行阶段**：在 `--mode ricequant` 下用 RustMiner 跑相同的 Swarm 配置，对比 Alpha Pool 产出
4. **切流阶段**：先切 CLI 入口，再切 API 服务，最后切 Swarm Manager
5. **纯原生阶段**：`--native-only` 标志确认所有 Python 回退路径已移除

两个版本共享同一套数据目录、结果目录和 SQLite schema，可以在同一研究环境中并行使用。

### 12.6 性能特征

基于架构差异，RustMiner 在以下场景有显著优势：

- **批量因子求值**：原生 Arrow 列式引擎，无 Python GIL 开销
- **并行 Agent 调度**：原生线程 + mpsc 通道，无 multiprocessing 序列化开销
- **API 吞吐**：Axum 异步多线程，单实例可承载更高并发
- **冷启动**：单二进制直接执行，无 Python 解释器 + 依赖加载延迟
- **图表渲染**：plotters 原生渲染，不依赖 matplotlib C 扩展

Python 版本在以下场景仍有优势：

- **快速原型**：修改提示词、算子逻辑后即时生效，无需编译
- **生态扩展**：可直接使用 pandas/polars/numpy 生态做 ad-hoc 分析
- **RiceQuant API**：Python SDK 原生支持，Rust 版本通过 HTTP 桥接

## 13. 总结

AI Alpha Miner 是一套围绕量化研究闭环构建的工作平台。它把多 Agent 挖掘、手工验证、策略化评估、知识沉淀、运行管理和多入口使用方式整合到一起，适合从个人研究到小团队协作的多种场景。

RustMiner 作为下一代 Rust 重写，在保持完整研究能力的同时，提供了原生编译性能、单二进制分发、形式化切流框架和更完善的测试体系，适合对部署可靠性、运行效率和长期维护有更高要求的团队。
