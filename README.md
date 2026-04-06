# AI Alpha Miner: 多智能体量化因子挖掘系统

AI Alpha Miner 是一个自动化量化交易因子挖掘平台。它模仿高级量化研究员的工作流，通过 Kimi/Claude/Qwen 驱动的多智能体协同（Multi-Agent System）与弹性 RAG 检索技术，实现从学术灵感检索到因子代码生成、再到严苛金融回测的闭环自动化。

## 核心架构

系统采用 LangGraph 编排了一个有状态的循环工作流：

1. **知识检索 (RAG)**：从本地向量库提取前沿论文、Alpha 101 公式及市场元数据。
2. **灵感构思 (Idea Agent)**：基于检索知识提出具有金融逻辑的因子假设。
3. **代码实现 (Factor Agent)**：将假设转化为 Qlib 兼容的数学表达式。
4. **深度评估 (Eval Agent)**：利用 AlphaEval 或 RiceQuant 框架进行多维度体检。
5. **自我进化 (Reflexive Loop)**：根据回测反馈自动反思并修正因子。

## 关键技术特性

### 1. 多厂商 LLM 支持
- **Kimi (Moonshot)**: 默认支持 `kimi-k2-thinking-turbo` 思考模型，擅长逻辑推理。
- **Claude**: 支持 `claude-opus-4-6` 等主流模型。
- **通义千问 (Qwen)**: 支持 `qwen-max` 高性能模型。

### 2. 评估模式：RiceQuant (米筐) 兼容
系统深度兼容米筐量化 SDK (`rqdatac`)：
- **无需本地数据**：实时拉取 A 股指数成分股及行情。
- **云端测算**：直接计算因子 IC、Rank IC 等指标。

### 3. 弹性 RAG 引擎
- **本地 Embedding**: 支持使用 `BAAI/bge-small-zh-v1.5` 进行 100% 本地向量化，零 API 成本。
- **自动降级**: 当 API 异常时，自动切换为本地关键词检索，确保流程不断。
- **Token 优化**: 自动截断超长上下文（1500 字符内），显著节省 Token 支出。

## 安装与配置

### 1. 环境准备
推荐使用 Python 3.10+。
```bash
pip install -r requirements.txt
# 可选：如果使用本地 Embedding 模型
pip install sentence-transformers
```

### 2. 环境变量配置
在 `.env` 中配置对应的 API Key：
```bash
# LLM 配置 (三选一或多选)
LLM_KEY="你的_Kimi_API_Key"
QWEN_API_KEY="你的_Qwen_API_Key"
ClaudeCode_KEY="你的_Claude_Proxy_Key"

# 米筐配置 (如果你使用 ricequant 模式)
RQ_TOKEN="你的米筐许可证"

# 可选：强制开启本地 RAG
USE_LOCAL_EMBEDDING="true"
```

## 使用说明

通过命令行参数灵活启动：

```bash
# 默认模式：自动检测 API，本地 Qlib 评估
python main.py --iterations 5

# 推荐组合：Kimi 思考 + 米筐数据 + 本地 RAG
python main.py --iterations 3 --mode ricequant --llm-provider kimi --embedding-provider local

# 指定具体模型
python main.py --llm-provider kimi --llm-model kimi-k2-thinking-turbo
```

### 参数详解：
- `--iterations`: 执行多少轮挖掘。
- `--mode`: 评估模式 (`qlib` 或 `ricequant`)。
- `--llm-provider`: 指定厂商 (`kimi`, `qwen`, `claude`)。
- `--llm-model`: 指定模型全称。
- `--embedding-provider`: 嵌入厂商 (`local`, `kimi`, `qwen`, `claude`)。

## 评估维度 (AlphaEval Metrics)

| 指标 | 说明 | 理想值 |
| - | - | - |
| **IC / Rank IC** | 预测值与真实收益的相关性 | > 0.02 |
| **PFS (Robustness)** | 注入 5% 噪声后的性能保持率 | > 0.8 |
| **Diversity** | 因子与已有库的正交性指数 | > 0.5 |
| **LLM Score** | AI 对因子金融逻辑合理性的评分 | 80 - 100 |
