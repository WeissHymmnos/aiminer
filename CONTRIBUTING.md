# 贡献指南 (Contributing)

感谢关注并参与 AI Alpha Miner 的开发。本文档说明本地开发环境搭建、仓库目录结构、代码规范及补丁提交流程。

## 开源许可说明

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0-only)** 协议发布。提交 Pull Request 或任何形式的补丁，即代表你同意将所提交的代码按 AGPL-3.0-only 协议授权，并确认自己拥有合法的提交权限。若无法接受 AGPL-3.0-only 条款，请勿提交代码。

## 开发环境搭建

推荐使用 Conda（Python 3.10+）或标准虚拟环境，并以可编辑模式安装全部开发依赖：

```bash
# 方式一：Conda 环境（推荐）
conda env create -f environment.yml
conda activate aiminer
pip install -e ".[all,test]"

# 方式二：标准 venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 初始化本地配置
cp .env.example .env
```

如需开发或测试基于 Rust 的横截面/时序加速算子，需安装 Rust 工具链与 `maturin`，并在 `polars_plugins/` 下执行编译：

```bash
cd polars_plugins && maturin develop --release
```

## 运行测试与静态检查

仓库测试按依赖边界通过 Pytest Marker 区分：

```bash
# 纯本地单元测试（默认 CI 门禁，无需外部密钥、网络或原生编译插件）
PYTHONPATH=src pytest tests/unit -m "unit and not external and not native" -q

# 全量本地测试（未配置 RQ_TOKEN 时会自动跳过需线上凭证的用例）
PYTHONPATH=src pytest tests/ -q

# 原生算子插件测试
PYTHONPATH=src pytest -m native -q
```

提交前建议运行 CI 矩阵自检脚本，一次性完成 Python 字节码编译检查、CI 工作流校验、Ruff 代码格式检查与 Pytest 用例收集：

```bash
python scripts/verify_ci_matrix.py
```

前端改动请在 `frontend/` 目录下执行类型检查与生产构建验证：

```bash
cd frontend && npm run build
```

## 仓库目录结构

| 路径 | 职责说明 |
|---|---|
| `src/aiminer/manager.py` | 多智能体 Swarm 顶层调度器（`PortfolioManager`）与 CLI 入口 |
| `src/aiminer/scheduler.py` | 进程池/线程池并发调度、超时控制与日志队列转发 |
| `src/aiminer/selector.py` | 因子评分、收益率相关性去重与负 IC 方向翻转 |
| `src/aiminer/crossover.py` | 头部父代因子的遗传杂交逻辑 |
| `src/aiminer/persistence.py` | SQLite（`alpha_miner.db`）建表、原子写入与检查点恢复 |
| `src/aiminer/sub_agent.py` | 单个研究员（`AlphaResearcher`）执行封装 |
| `src/aiminer/main.py` | 单智能体调试工作流入口 |
| `src/aiminer/api.py` / `src/aiminer/routers/` | FastAPI 服务端入口与模块化路由（`swarm`、`backtest`、`strategy`、`wiki`、`admin`、`websocket`） |
| `src/aiminer/tui.py` | 基于 Textual 的终端交互工作台 |
| `src/aiminer/app_workflow/` | LangGraph 状态图定义（`graph.py`）与共享状态（`state.py`） |
| `src/aiminer/agents/` | 假说（`idea`）、因子（`factor`）、回测（`eval`）、策略（`strategy` / `strategy_critic`）、组合（`portfolio`）与汇总（`summary`）智能体 |
| `src/aiminer/core/` | LLM 网关、混合知识库（RAG + LLMWiki）、回测引擎（`alphaeval/`）、策略回测、生命周期管理与配置解析 |
| `src/aiminer/schemas/` | Pydantic 结构化输出契约 |
| `polars_plugins/` | Rust 编写的 Polars 原生扩展算子 |
| `frontend/` | React + TypeScript + Vite Web 工作台源码 |
| `scripts/` | 行情下载、文献抓取、工作区重置与运维脚本 |
| `tests/` | Pytest 单元测试、集成测试与前端 E2E 测试 |

## 编码规范

1. **严禁硬编码凭证**：所有 API Key、RiceQuant Token 均通过环境变量或 `.env` 读取，切勿提交真实密钥。
2. **禁止提交运行期产物**：`results/`、`logs/`、`data/wiki_db/`、`data/chroma_db/` 以及运行生成的 Wiki 卡片（`data/wiki_vault/*_iter*.md`）不应纳入版本控制。
3. **保持表达式求值边界安全**：扩充算子时必须在 `FactorAgent` 白名单、`SafeEvalTransformer` 以及对应计算引擎（Pandas / Polars）中同步注册并补充单测，严禁对模型输出直接调用不受限的 `eval()`。
4. **代码风格与日志**：Python 代码遵循 Google Style（80 列行宽，使用 `ruff check` 与 `ruff format`），日志统一使用 `loguru`，LLM 结构化输出统一使用 Pydantic v2 模型定义。
5. **契约同步**：新增或修改策略参数、分页接口字段时，需同步更新 `src/aiminer/core/strategy.py`、`src/aiminer/routers/`、`frontend/src/types.ts` 及对应页面表单。

## Pull Request 检查清单

- [ ] `python scripts/verify_ci_matrix.py` 与相关单元/集成测试全部通过
- [ ] Git diff 中不包含 `.env`、私钥、行情缓存或 SQLite 数据库文件
- [ ] 若调整了 CLI 参数、环境变量或 HTTP 接口，已同步更新 `README.md` 与 `instruction.md`
- [ ] 新增第三方依赖已在 `pyproject.toml` 与 `requirements.txt` 中声明并说明原因

## 延伸阅读

完整的模块职责、数据流、表结构与接口契约请查阅 [instruction.md](./instruction.md)；面向 AI 编程助手的快速上下文说明见 [CLAUDE.md](./CLAUDE.md)。
