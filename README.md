# AI Alpha Miner: 基于 claudecode 的多智能体量化因子挖掘系统

AI Alpha Miner 是一个自动化量化交易因子挖掘平台。它模仿高级量化研究员的工作流，通过 Claude 4.6 Opus 驱动的多智能体协同（Multi-Agent System）与检索增强生成（RAG）技术，实现从学术灵感检索到因子代码生成、再到严苛金融回测的闭环自动化。


## 核心架构

系统采用 LangGraph 编排了一个有状态的循环工作流（Looping Workflow）：

1. **知识检索 (RAG)**：从本地向量数据库（包含前沿论文、Alpha 101 公式、市场元数据）中提取上下文。

2. **灵感构思 (Idea Agent)**：基于检索到的知识，由 Claude 4.6 Opus 提出具有金融逻辑的因子假设。

3. **代码实现 (Factor Agent)**：将假设转化为 Qlib 兼容的数学表达式。

4. **深度评估 (Eval Agent)**：利用集成的 AlphaEval 框架，从 5 个维度对因子进行科学体检。

5. **自我进化 (Reflexive Loop)**：根据评估反馈，Agent 自动反思并修正因子，开启下一轮迭代。


## 关键技术特性

### 1. Claude 4.6 Opus

系统全面接入 Claude 4.6 Opus 模型，利用其行业领先的逻辑推理能力进行因子构思。通过 gptsapi.net 代理实现高性能、低延迟的 API 调用。

### 2. 专业评估：AlphaEval 框架

系统集成了最新的 AlphaEval 评估器，不仅仅关注收益率，更关注因子的统计质量：

- **Predictive Power**: 计算 IC / Rank IC。

- **Robustness (PFS)**：通过注入金融噪声测试因子在极端行情下的稳定性。

- **Diversity**: 评估新因子与已有因子库的正交性，防止策略同质化。

- **Relative Return Entropy (RRE)**：从信息熵角度衡量因子的有效性。

### 3. RAG 知识引擎

本地 data/rag\_docs/ 目录下存储了丰富的量化知识：

- **Academic**: 提炼自 2025-2026 年 arXiv 前沿量化论文。

- **Alphas**: 完整的 WorldQuant Alpha 101 与国泰君安 191 公式模板。

- **Market Meta**: 通过 AKShare 实时拉取的 A 股/期货市场元数据，确保 Agent 了解真实字段（如 $vwap, $open, $volume）。


## 项目目录结构

```
.  
├── agents/                 \# 多智能体定义  
│   ├── idea\_agent.py       \# 负责金融逻辑构思  
│   ├── factor\_agent.py     \# 负责编写 Qlib 公式  
│   └── eval\_agent.py       \# 封装 AlphaEval 与反射逻辑  
├── core/                   \# 核心底层模块  
│   ├── alphaeval/          \# AlphaEval 评估框架实现  
│   ├── llm.py              \# Claude 4.6 Opus 接口集成  
│   └── rag.py              \# ChromaDB 向量检索与文档加载  
├── data/rag\_docs/          \# RAG 原始文档仓库  
│   ├── academic/           \# 前沿论文提炼  
│   ├── alphas/             \# 经典因子公式库  
│   └── market\_meta/        \# 真实市场字段元数据  
├── workflow/               \# LangGraph 工作流定义  
│   ├── graph.py            \# 节点流转逻辑  
│   └── state.py            \# 全局状态管理  
├── scripts/                \# 数据拉取与预处理脚本  
├── main.py                 \# 系统入口，支持 --iterations 参数  
└── requirements.txt        \# 项目依赖
```


## 安装与配置

### 1. 环境准备

推荐使用 Python 3.10+。

```
git clone \<your-repo-url\>  
cd aiminer  
pip install -r requirements.txt
```

### 2. 环境变量配置

系统从环境变量中读取 API Key。请确保你的环境变量中包含以下配置：

```
export ClaudeCode\_KEY="你的\_gptsapi\_key"
```

### 3. 初始化市场元数据

运行脚本从 AKShare 同步最新的市场字段信息：

```
python scripts/fetch\_market\_metadata.py
```


## 使用说明

运行主程序开启自动化挖掘工作流。你可以通过 --iterations 指定希望进行的循环挖掘次数：

```
\# 运行 5 轮因子的构思、编写与评估  
python main.py --iterations 5
```

### 运行流程说明：

- **第一步**: RAGModule 自动扫描 data/rag\_docs/ 并将新知识向量化到本地 ChromaDB。

- **第二步**: Idea Agent 检索论文，提出一个诸如“基于成交量加权的动量反转特征”的假设。

- **第三步**: Factor Agent 生成 Qlib 代码：Rank(Corr($close, $volume, 10)) \* -1。

- **第四步**: EvalAgent 运行 AlphaEval，输出 IC 值和鲁棒性得分。

- **第五步**: 如果得分不理想，Claude 4.6 会分析原因并自动调整逻辑进入下一轮。


## 评估维度详情 (AlphaEval Metrics)

| 指标 | 说明 | 理想值 |
| - | - | - |
| **IC / Rank IC** | 预测值与真实收益的相关性 | \> 0.02 |
| **PFS (Robustness)** | 注入 5% 噪声后的性能保持率 | \> 0.8 |
| **Diversity** | 因子与已有库的正交性指数 | \> 0.5 |
| **LLM Score** | Claude 4.6 对因子金融逻辑合理性的定性评分 | 80 - 100 |




