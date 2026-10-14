# AlphaMax 组合优化实验归档（2026-08）

本目录归档了 2026 年 8 月 AlphaMax 多因子组合优化实验期间编写的独立研究与审计脚本。实验最初尝试在已挖掘的 Alpha 因子池上探索激进的均值方差与波动率目标组合边界；随后的金融逻辑审计（`alphamax_audit.py`）识别出早期版本（`v1`–`v6`）存在 EWMA 收益平滑虚增夏普比率、样本内前视偏差及漏计交易与杠杆成本等问题。后续版本（`v7`、`v8`）修正为严格的样本外滚动（Walk-Forward）回测框架。

此目录下的脚本仅作历史方法论对照与审计复现保留，生产级多因子组合构建已合并至主包 `src/aiminer/core/portfolio.py` 与 `src/aiminer/manager.py`。

## 归档脚本清单

| 脚本 | 说明 |
|---|---|
| `alphamax_optimize.py` | 多因子组合权重优化初版探索脚本 |
| `alphamax_v2.py` | 基于全量高 IC 因子筛选与协方差矩阵优化的实验版本 |
| `alphamax_v3.py` | 引入前向贪心筛选与相关性过滤的迭代选因子版本 |
| `alphamax_v4.py` | Ledoit-Wolf 压缩协方差（Shrinkage MVO）叠加 EWMA 收益平滑 |
| `alphamax_v5.py` | 在压缩协方差组合上叠加日频目标波动率控制（Volatility Targeting） |
| `alphamax_v6.py` | 高杠杆配置叠加回撤熔断机制实验 |
| `alphamax_audit.py` | 五项金融逻辑审计脚本，用于复现并量化收益平滑与前视偏差对夏普比率的虚增效应 |
| `alphamax_v7.py` | 修正后的样本外滚动框架：月度调仓、1 日执行延迟、双边 10 bps 交易成本、移除 EWMA 平滑 |
| `alphamax_v8_portfolio.py` | 日频样本外滚动组合生成与持仓导出脚本（支持 `--live`） |

## 审计与复盘记录

- 偏差拆解与审计报告：`docs/notes/alphamax-audit-20260822.md`
- 阶段实验汇总：`docs/notes/alphamax-final-20260822.md`
