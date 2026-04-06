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

## 📊 系统输出
*   **最优代码**: 每个 Agent 迭代出的最佳 Python 因子表达式。
*   **评估报告**: 包含 IC、Rank IC、夏普比率等核心指标。
*   **正交化池**: 经过 Manager 筛选后的高表现、低相关性因子集合。

---
更多详细文档请参考 [instruction.md](./instruction.md)。
