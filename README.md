# 🚀 AI Alpha Miner: Multi-Agent Swarm

AI Alpha Miner 是一款基于 **LangGraph** 和 **主从架构 (Master-Slave)** 构建的量化因子自动挖掘系统。它通过模拟多个具有不同专业背景的量化研究员（Sub-Agents），在主控（Manager）的调度下，自主完成从宏观分析、假设生成、代码实现到回测评估的全流程闭环。

## 🌟 核心功能

*   **主从架构调度 (Manager-SubAgent)**: 由 `Manager` 统筹全局，支持并发或串行启动多个具备特定先验知识（如“动量专家”、“高频专家”）的子 Agent。
*   **自动化迭代研究**: 每个子 Agent 在其专业领域内执行 `Research -> Code -> Backtest -> Reflect` 的微循环，不断自我优化因子逻辑。
*   **因子正交化主干 (Orthogonalization Backbone)**: 主 Agent 汇总所有结果，不仅筛选表现优异的因子，还通过计算每日收益率的相关性矩阵，自动剔除同质化因子，确保最终生成的 Alpha 池具备多样性。
*   **多源 RAG 知识驱动**: 整合学术论文、Qlib 文档、WorldQuant 101 因子库以及实时宏观新闻，为 AI 提供深度策略启发。
*   **双引擎支持**: 完美适配 Qlib (离线数据) 与 RiceQuant (实时/线上数据) 评估环境。

## 🛠️ 快速上手

### 环境安装
```bash
conda env create -f environment.yml
conda activate aiminer
pip install -r requirements.txt
```

### 启动多 Agent 协作挖掘
```bash
python manager.py --iterations 5 --mode ricequant \
--llm-provider glm --llm-model glm-4 \
--roles "专注量价反转的专家" "宏观周期对冲专家" "统计套利专家" \
--parallel
```

### 使用本地 Codex 作为 LLM Provider

如果本机已经安装并登录 `codex` CLI，可以把它作为文本生成 LLM 的替代选项：

```bash
python manager.py --iterations 3 --mode ricequant \
  --llm-provider codex --llm-model gpt-5.4 \
  --llm-reasoning-effort xhigh \
  --embedding-provider local \
  --roles "专注量价反转的专家" \
  --parallel
```

Web Run Launcher 中也可以填写：

- `LLM Provider`: `codex`
- `LLM Model`: 例如 `gpt-5.4`
- `Reasoning Effort`: `low`、`medium`、`high`、`xhigh`，留空则使用 Codex 默认配置
- `Embedding Provider`: `local` 或现有 embedding API provider

Codex provider 通过 `codex exec` 调用本地 CLI，默认使用只读、临时会话边界；它只替代文本生成 LLM，不提供 embedding。可用 `AIMINER_CODEX_CMD` 指定 Codex CLI 路径，用 `AIMINER_CODEX_TIMEOUT_SECONDS` 调整单次调用超时。
可用 `AIMINER_CODEX_REASONING_EFFORT` 设置默认思考强度，也可以通过 `--llm-reasoning-effort` 或 Web/TUI 表单覆盖。

### 启动 Web 工作台
开发模式：

```bash
./start_web.sh
```

生产模式（后端直接托管 `frontend/dist`）：

```bash
./start_web.sh --prod
```

默认情况下，脚本会统一设置：

- `AIMINER_DATA_DIR`
- `AIMINER_RESULTS_DIR`
- `AIMINER_LOG_DIR`

这保证 API、Manager、手工回测和 Web 工作台读取的是同一套数据与日志目录，而不是各自落到不同路径。

### 鉴权说明

如果启用了鉴权，请先设置：

```bash
export AIMINER_AUTH_TOKEN="your-token"
```

Web 工作台侧边栏提供 `API Token` 输入框。输入后，前端会自动为请求附带：

- `Authorization: Bearer <token>`
- `X-API-Key: <token>`

### Stop Run 说明

Swarm 的停止现在是两阶段状态机：

- `stopping`：停止请求已经发出，正在等待 worker 进程退出
- `stopped`：进程已经确认退出，运行真正结束

因此，点击 `Stop Run` 后，Web/TUI 可能会短暂显示 `Stopping...`，这是预期行为，不代表失败。

### Docker / Compose

`docker compose up -d --build` 默认只启动 API 服务，避免有限研究任务在 `restart: unless-stopped` 下反复执行并写入产物。

```bash
docker compose up -d --build
```

研究 worker 和 TUI 使用 profile 或一次性 run 启动：

```bash
AIMINER_ITERATIONS=5 docker compose --profile research run --rm worker
docker compose --profile tui run --rm tui
```

### 测试矩阵

默认 CI 只跑 hermetic unit，不依赖外部凭证、网络服务、生成数据目录或本地 Rust/Polars 原生插件：

```bash
PYTHONPATH=. pytest tests/unit -m "unit and not external and not native" -q
```

可选测试分开执行：

```bash
PYTHONPATH=. pytest -m external -q  # RiceQuant/外部依赖
PYTHONPATH=. pytest -m native -q    # Rust/Polars 原生插件
```

### Reset 产物

reset 默认是 dry-run，使用 `--confirm` 才会把匹配路径移动到 `results/.trash/<timestamp>/`。`runs` scope 对应真实 Swarm 产物目录 `results/swarm_runs`：

```bash
python scripts/reset_workspace.py --scope runs
python scripts/reset_workspace.py --scope runs --confirm
```

## 📊 系统输出
*   **最优代码**: 每个 Agent 迭代出的最佳 Python 因子表达式。
*   **评估报告**: 包含 IC、Rank IC、夏普比率等核心指标。
*   **正交化池**: 经过 Manager 筛选后的高表现、低相关性因子集合。

## 📥 下载米筐国内股指期货数据

项目现在提供一个独立 CLI，可从 RiceQuant 自动下载国内股指期货的全量合约数据和主力连续数据，默认覆盖 `IF`、`IH`、`IC`、`IM`，并按 Parquet 落到本地目录。

使用前需要配置现有 RiceQuant 环境变量之一：

- `RQ_TOKEN`
- `RQ_USER` + `RQ_PASS`

示例：

```bash
python scripts/download_rq_index_futures.py \
  --output data/local_futures \
  --start 2015-04-16 \
  --end 2026-04-17 \
  --frequencies 1d,1m \
  --underlyings IF,IH,IC,IM
```

常用选项：

- `--contracts-only`：只下载实际合约，不生成主力连续
- `--dominant-only`：只生成主力连续
- `--full-refresh`：忽略已有文件，全量重抓
- `--dry-run`：只打印任务，不写文件
- 默认下载完成后会自动做一次本地数据校验
- `--skip-validate`：跳过下载后自动校验
- `--validate-skip-1m`：校验时只检查日线，不扫分钟线

输出目录结构：

```text
data/local_futures/
  contracts/1d/*.parquet
  contracts/1m/*.parquet
  dominant/1d/*.parquet
  dominant/1m/*.parquet
  manifests/download_manifest.json
```

---
更多详细文档请参考 [instruction.md](./instruction.md)。
