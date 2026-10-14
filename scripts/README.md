# 辅助与运维脚本 (`scripts/`)

本目录包含行情下载、RAG 语料抓取、因子池查询、工作区清理与自动化值守脚本。最小化的单次研究运行并不强制依赖这些脚本，但在正式开展大规模挖掘前，使用它们准备本地行情与最新文献语料可显著提升因子质量与回测速度。

## 1. 行情与 RAG 语料准备

| 脚本 | 用途 |
|---|---|
| `download_rq_index_futures.py` | 从 RiceQuant 下载国内股指期货（默认 `IF`、`IH`、`IC`、`IM`）的全量合约与主力连续数据（日线/分钟线 Parquet），落盘至 `data/local_futures/` 并自动执行数据完整性校验 |
| `download_qlib_data.py` | 下载并初始化 Qlib 离线数据包（供 `--mode qlib` 使用） |
| `fetch_academic_papers.py` | 抓取量化金融学术论文元数据并写入 `data/rag_docs/academic/` |
| `fetch_arxiv_qfin.py` | 拉取 arXiv `q-fin`（Quantitative Finance）最新论文摘要 |
| `fetch_arxiv_with_pkg.py` | 基于 `arxiv` Python 包拉取定量金融文献摘要 |
| `fetch_macro_news.py` | 抓取宏观财经新闻并按年份归档至 `data/rag_docs/` |
| `fetch_market_metadata.py` | 通过 AKShare 拉取市场结构与行业元数据，写入 `data/rag_docs/market_meta/` |

注：体量较大的原始语料（如全量论文摘要 JSON 与本地期货 Parquet 数据）不纳入 Git 版本控制，按需通过上述脚本在本地生成即可。数据更新后，可在运行 `aiminer.manager` 时传入 `--rebuild-rag` 重新构建 Chroma 向量索引。

示例：

```bash
# 更新 arXiv 定量金融摘要与市场元数据
python scripts/fetch_arxiv_qfin.py
python scripts/fetch_market_metadata.py

# 下载股指期货日线与分钟线至本地 Parquet
python scripts/download_rq_index_futures.py \
  --output data/local_futures \
  --start 2015-04-16 \
  --end 2026-04-17 \
  --frequencies 1d,1m \
  --underlyings IF,IH,IC,IM
```

## 2. 因子池查询与后处理

| 脚本 | 用途 |
|---|---|
| `query_pool.py` | 在终端查询并筛选 `results/alpha_miner.db` 中的有效因子与策略表现 |
| `run_factor_crossover.py` | 从现有因子池挑选头部父代因子，单独执行遗传杂交与回测验证 |
| `run_portfolio.py` | 基于因子池中的低相关性有效因子构建多因子组合并评估净值 |

## 3. 工作区维护、自动化与 CI 校验

| 脚本 | 用途 |
|---|---|
| `reset_workspace.py` | 可逆清理运行期产物（支持 `pool`、`memory`、`rag`、`runs`、`all` 作用域）。默认为只读预览，传入 `--confirm` 后将目标移动至 `results/.trash/<timestamp>/` |
| `hermes_auto_runner.py` | 夜间自动挖掘守护脚本，在 `00:00–08:00`（北京时间）窗口内自动拉起并守护 Swarm 进程，支持断点恢复（详见 [docs/hermesagent_automation.md](../docs/hermesagent_automation.md)） |
| `verify_ci_matrix.py` | 本地一键执行字节码编译检查、CI 配置校验、Ruff 格式检查与 Pytest 用例收集验证 |
| `check_status.sh` | 快速查看当前活跃任务、日志尾部与数据库统计摘要 |
