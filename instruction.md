# AI Alpha Miner — 完整技术说明文档

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构总览](#2-系统架构总览)
3. [环境搭建](#3-环境搭建)
4. [快速运行指南](#4-快速运行指南)
5. [模块详解：工作流层](#5-模块详解工作流层)
6. [模块详解：Agent 层](#6-模块详解agent-层)
7. [模块详解：核心能力层](#7-模块详解核心能力层)
8. [模块详解：因子评估层](#8-模块详解因子评估层)
9. [模块详解：Schemas 层](#9-模块详解schemas-层)
10. [模块详解：顶层入口](#10-模块详解顶层入口)
11. [完整数据流与流程说明](#11-完整数据流与流程说明)
12. [配置参数全览](#12-配置参数全览)
13. [输出文件说明](#13-输出文件说明)
14. [已知问题与注意事项](#14-已知问题与注意事项)

---

## 1. 项目概述

AI Alpha Miner 是一个**全自动量化因子挖掘系统**。它利用 LLM（大语言模型）作为核心推理引擎，通过 Manager-SubAgent 群体智能框架，自主完成从市场假说提出、数学公式化、代码实现，到因子回测、反思改进的完整因子挖掘闭环。

核心特点：
- **群体智能**：多个具备不同角色专长的研究员 Agent 并行探索
- **知识积累**：每轮实验结果写入 LLM Wiki，供后续 Agent 参考学习
- **遗传算法**：筛选出最优因子后，通过 LLM 完成"基因交叉"，合成更强因子
- **自适应早停**：基于 IC 阈值和 Patience 计数器控制实验深度
- **双引擎支持**：Pandas（兼容 Qlib）和 Polars（高性能）两种因子计算后端

目标市场：中国A股市场（通过 RiceQuant/rqdatac 接口）或微软 Qlib 框架。

---

## 2. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                         manager.py                                   │
│                       PortfolioManager                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  ProcessPoolExecutor (并行/串行)                              │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │   │
│  │  │  SubAgent #1   │  │  SubAgent #2   │  │  SubAgent #3   │  │   │
│  │  │  (均值回归专家) │  │  (动量专家)     │  │  (套利专家)    │  │   │
│  │  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  │   │
│  └──────────┼────────────────────┼───────────────────┼───────────┘   │
│             │ (每个子进程独立运行 LangGraph 工作流)    │               │
│  ┌──────────▼────────────────────▼───────────────────▼───────────┐   │
│  │              LangGraph 工作流 (每个 SubAgent 独立实例)          │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │   │
│  │  │IdeaAgent │──▶│FactorAgt │──▶│ EvalAgt  │──▶│WikiUpdate│  │   │
│  │  │假说生成   │   │公式+代码  │   │回测+反思  │   │更新知识库 │  │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └────┬─────┘  │   │
│  │       ▲                                             │        │   │
│  │       └──────────── increment (循环迭代) ────────────┘        │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Manager 评估与筛选                              │   │
│  │  1. IC > 0.01 阈值过滤                                      │   │
│  │  2. Pearson 相关性 < 0.7 去冗余                              │   │
│  │  3. 遗传交叉（取 Top-2 生成混合因子）                         │   │
│  │  4. SQLite 持久化 + Markdown 报告生成                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

知识层（所有 Agent 共享）
┌──────────────────────────────────────────────────────────────────┐
│  HybridKnowledge                                                  │
│  ┌──────────────────────────────┐  ┌───────────────────────────┐ │
│  │  RAGModule (core/rag.py)     │  │  LLMWiki (core/wiki.py)   │ │
│  │  - ChromaDB 向量库            │  │  - 结构化因子卡片          │ │
│  │  - BM25 关键词检索             │  │  - ChromaDB 向量索引      │ │
│  │  - 语义相似度混合检索           │  │  - Markdown 文件持久化    │ │
│  │  - 文档：data/rag_docs/       │  │  - 位置：data/wiki_db/    │ │
│  └──────────────────────────────┘  └───────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
aiminer/
├── manager.py               # 入口：多 Agent 群体管理器
├── main.py                  # 入口：单 Agent 顺序模式
├── sub_agent.py             # 单个研究员 Agent 封装
├── workflow/
│   ├── state.py             # LangGraph 状态定义（TypedDict）
│   └── graph.py             # LangGraph 图结构与路由
├── agents/
│   ├── idea_agent.py        # 假说生成代理
│   ├── factor_agent.py      # 公式化与代码实现代理
│   ├── eval_agent.py        # 回测评估代理
│   └── summary_agent.py     # 报告生成代理
├── core/
│   ├── llm.py               # LLM 多提供商网关
│   ├── rag.py               # ChromaDB RAG 模块
│   ├── wiki.py              # LLM Wiki 知识库
│   ├── hybrid_knowledge.py  # RAG + Wiki 混合检索
│   ├── wiki_bootstrapper.py # 从 RAG 文档初始化 Wiki
│   └── alphaeval/
│       ├── rq_eval.py       # RiceQuant 因子评估引擎（主力）
│       ├── modeltester.py   # Qlib 因子评估适配器
│       └── polars_engine.py # Polars 高性能计算引擎
├── polars_plugins/          # Rust 编写的 Polars 算子插件
│   ├── Cargo.toml
│   ├── pyproject.toml
│   └── src/lib.rs
├── schemas/
│   └── messages.py          # Pydantic 结构化输出模型
├── data/
│   ├── rag_docs/            # RAG 知识文档（PDF、TXT、MD）
│   ├── chroma_db/           # ChromaDB 向量数据库（自动生成）
│   └── wiki_db/             # LLMWiki Markdown 卡片（自动生成）
├── results/
│   ├── alpha_miner.db       # SQLite 因子池数据库
│   ├── alpha_pool.json      # JSON 备份
│   ├── reports/             # 每个因子的 Markdown 报告
│   └── charts/              # 权益曲线 PNG 图像
├── tests/                   # pytest 测试套件
├── environment.yml          # Conda 环境配置
├── requirements.txt         # Python 依赖
└── .env.example             # 环境变量模板
```

---

## 3. 环境搭建

### 3.1 创建 Conda 环境

```bash
conda env create -f environment.yml
conda activate aiminer
pip install -r requirements.txt
```

### 3.2 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少填写一个 LLM API Key 和 RiceQuant 凭证
```

必要变量（至少一个 LLM + RiceQuant）：
```ini
# LLM（至少一个）
LLM_KEY=sk-...           # Kimi/Moonshot
ZHIPU_API_KEY=...        # 智谱 GLM（也用于 Embedding）
OPENAI_API_KEY=sk-...    # OpenAI
DEEPSEEK_API_KEY=...     # DeepSeek
GROQ_API_KEY=...         # Groq（免费高速）

# RiceQuant 回测
RQ_USER=用户名
RQ_PASS=密码
# 或者 Token 方式
RQ_TOKEN=your_token
```

### 3.3 编译 Rust 插件

```bash
cd polars_plugins
maturin develop --release
cd ..
```

每次修改 `polars_plugins/src/lib.rs` 后必须重新执行。

### 3.4 准备 RAG 文档（可选）

将量化研究文档（PDF/TXT/MD）放入 `data/rag_docs/`，首次运行自动构建向量库。

---

## 4. 快速运行指南

### 4.1 多 Agent 群体模式（推荐）

```bash
python manager.py \
  --iterations 5 \
  --mode ricequant \
  --engine polars \
  --llm-provider kimi \
  --llm-model kimi-k2-turbo-preview \
  --embedding-provider glm \
  --market-start 2015-01-01 \
  --market-end 2020-12-31 \
  --roles "专注动量反转的量价专家" "基于基本面的价值投资专家" "统计套利专家" \
  --parallel \
  --wiki-bootstrap
```

### 4.2 单 Agent 模式

```bash
python main.py --iterations 3 --mode ricequant --llm-provider glm --llm-model glm-5
```

### 4.3 运行测试

```bash
python -m pytest tests/ -v
python -m pytest tests/test_polars_ops_extensive.py -v   # Polars 算子测试
python -m pytest tests/test_numerical_consistency.py -v  # 数值一致性测试
python test_eval.py     # 因子评估端到端测试（非 pytest）
python test_compile.py  # Polars 编译器测试
```

### 4.4 命令行参数总览

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `--iterations` | int | 2 | 每个 SubAgent 最大迭代次数 |
| `--mode` | str | ricequant | 评估后端：`ricequant` 或 `qlib` |
| `--engine` | str | pandas | 计算引擎：`pandas` 或 `polars` |
| `--parallel` | flag | False | 开启并行多进程模式 |
| `--wiki-bootstrap` | flag | False | 启动时从 RAG 文档初始化 Wiki |
| `--roles` | str... | 默认3个 | 各 Agent 角色描述（空格分隔多个） |
| `--llm-provider` | str | 自动检测 | LLM 提供商名称 |
| `--llm-model` | str | 各商默认 | 指定具体模型名 |
| `--embedding-provider` | str | 自动检测 | Embedding 提供商 |
| `--market-start` | str | None | 市场分析起始日期 YYYY-MM-DD |
| `--market-end` | str | None | 市场分析结束日期 YYYY-MM-DD |
| `--rebuild-rag` | flag | False | 强制重建 ChromaDB 向量库 |
| `--use-gpu` | flag | False | 使用 GPU 加速本地 Embedding |

---

## 5. 模块详解：工作流层

### 5.1 `workflow/state.py`

定义 LangGraph 状态机的全局共享状态 `AlphaMinerState`。

`total=False` 使所有字段均可选。各节点通过返回字典更新状态的指定字段，未返回的字段保持原值不变。唯一例外是 `messages` 字段——它使用 LangGraph Reducer 机制自动追加（`operator.add`），而非覆盖。

```python
class AlphaMinerState(TypedDict, total=False):
    # 迭代控制
    iteration: int              # 当前迭代编号（从 1 开始）
    max_iterations: int         # 允许的最大迭代次数

    # 知识上下文（IdeaAgent 每轮刷新）
    rag_context: str            # RAG 检索返回的文档内容
    wiki_context: str           # Wiki 检索返回的历史因子卡片
    market_regime_summary: str  # 动态市场制度分析文本
    macro_news_summary: str     # 宏观新闻摘要文本

    # IdeaAgent 输出
    hypothesis_name: str         # 因子假说名称，如"流动性冲击反转因子"
    hypothesis_description: str  # 假说详细描述
    rationale: str               # 经济学逻辑说明

    # FactorAgent 输出
    math_formula: str            # LaTeX 数学公式字符串
    variables_defined: Dict[str, str]  # 公式变量释义
    code_expression: str         # Qlib 表达式，如 Rank(Delta($close, 5))
    is_valid_syntax: bool        # 静态语法验证是否通过

    # EvalAgent 输出
    backtest_metrics: Dict[str, float]  # IC, Rank IC, Sharpe, 最大回撤等指标
    daily_returns: Dict[str, float]     # 日期字符串 → 日收益率
    review_summary: str          # LLM 反思评审摘要
    is_effective: bool           # 因子是否有效（IC > 0.02 且 Rank IC > 0.02）
    suggested_improvements: str  # 下一轮改进建议（由 IdeaAgent 读取）
    is_simulated: bool           # True 表示回测指标为模拟生成

    # 早停机制
    best_ic: float               # 历史最优 IC（初始 -999.0）
    best_code_expression: Optional[str]  # 对应历史最优 IC 的因子代码
    patience_counter: int        # 连续无改进轮数（达 3 次触发早停）

    # 工作流控制
    role_prompt: Optional[str]   # Agent 角色设定描述
    evaluation_mode: str         # "ricequant" 或 "qlib"
    evaluation_engine: str       # "pandas" 或 "polars"
    market_analysis_start_date: Optional[str]
    market_analysis_end_date: Optional[str]
    market_analysis_lookback_days: Optional[int]  # 市场制度分析回溯天数，默认 60

    error: Optional[str]         # 错误信息，非空则路由到 END
    messages: Annotated[List[str], operator.add]  # 累积日志，自动追加
```

---

### 5.2 `workflow/graph.py`

构建并编译 LangGraph 有向图，定义各节点和条件路由规则。

#### `build_workflow(rebuild_rag, llm_provider, llm_model, embedding_provider, use_gpu) -> CompiledGraph`

构建整个工作流。内部流程：
1. 初始化 `HybridKnowledge`（所有 Agent 共享同一实例）
2. 实例化 `IdeaAgent`、`FactorAgent`、`EvalAgent`
3. 创建 `StateGraph(AlphaMinerState)` 并添加节点和边
4. 返回编译后的 `app`

**节点定义**：

| 节点名 | 功能 |
|---|---|
| `idea_agent` | 假说生成（`IdeaAgent.__call__`） |
| `factor_agent` | 公式化 + 代码生成（`FactorAgent.__call__`） |
| `eval_agent` | 回测 + LLM 反思（`EvalAgent.__call__`） |
| `wiki_update` | 更新 Wiki 知识库（内部闭包函数） |
| `increment` | 递增迭代计数器，重置当轮状态 |

**图拓扑**：
```
入口: idea_agent
idea_agent  ──[route_after_idea]──>   factor_agent | end
factor_agent ──[route_after_factor]──> eval_agent   | end
eval_agent   ──[route_after_eval]──>   wiki_update  | end
wiki_update  ──[route_after_wiki]──>   increment    | end
increment    ──(固定边)──>             idea_agent
```

#### 路由函数

**`route_after_idea(state) -> str`**
- `error` 非空 → `"end"`
- `hypothesis_name` 缺失 → 记错误日志 → `"end"`
- 否则 → `"factor_agent"`

**`route_after_factor(state) -> str`**
- `error` 非空 → `"end"`
- `code_expression` 缺失 → 记错误日志 → `"end"`
- `is_valid_syntax == False` → 记警告（但仍继续，让 dry_run 做最终判断）→ `"eval_agent"`
- 否则 → `"eval_agent"`

**`route_after_eval(state) -> str`**
- `error` 非空 → `"end"`
- 否则始终 → `"wiki_update"`（确保失败实验也被记录以供学习）

**`route_after_wiki(state) -> str`**（早停判断，按优先级）
1. `IC >= 0.05` → `"end"`（发现异常优秀因子）
2. `patience_counter >= 3` → `"end"`（连续 3 轮无改进）
3. `iteration < max_iterations` → `"increment"`（继续）
4. 达到最大迭代 → `"end"`

#### `increment_iteration(state) -> dict`

重置单轮临时状态，保留跨轮积累信息：
```python
return {
    "iteration": state["iteration"] + 1,
    "best_ic": state["best_ic"],                           # 保留
    "best_code_expression": state["best_code_expression"], # 保留最优代码
    "patience_counter": state["patience_counter"],         # 保留耐心计数
    "error": None,          # 清除错误，允许下轮继续
    "is_valid_syntax": True, # 重置语法标志
}
```

#### `wiki_update_node(state)` 闭包

```python
def wiki_update_node(state):
    knowledge.update_wiki_after_eval(state)  # 写入 Wiki
    query = f"Alpha factor ideas related to {state.get('role_prompt')}"
    return {"wiki_context": knowledge.wiki.retrieve(query)}  # 刷新上下文
```

---

## 6. 模块详解：Agent 层

### 6.1 `agents/idea_agent.py` — IdeaAgent

**职责**：综合多源知识（RAG + Wiki + 市场数据 + 宏观新闻），通过 LLM 提出新的量化因子假说。

**LLM 温度**：`0.7`（高温，鼓励创新假说）

#### `IdeaAgent.__init__(knowledge, provider, model)`
- `knowledge`：`HybridKnowledge` 实例，提供统一的知识检索接口
- 通过 `get_llm(temperature=0.7)` 初始化 LLM 客户端

#### `IdeaAgent._strip_markdown_json(text) -> str` (静态方法)
清理 LLM 返回的 JSON 字符串：
1. 去除 ` ```json ` / ` ``` ` 代码块包装
2. 清除 `\x00-\x08`、`\x0b-\x0c`、`\x0e-\x1f` 等控制字符

#### `IdeaAgent.__call__(state) -> dict`

**步骤 1：读取上下文**
从 state 中读取 `iteration`、`previous_improvements`、`evaluation_mode` 等字段。

**步骤 2：混合知识检索**
```python
base_query = f"Quantitative trading strategies...related to: {role_prompt}"
combined_knowledge = self.knowledge.retrieve(base_query)
# 返回 RAG 文档 + Wiki 因子卡片的拼接文本
```

**步骤 3：宏观新闻检索**（仅 `ricequant` 模式，首次）
```python
macro_context = self.knowledge.rag.retrieve(macro_query, n_results=3)
```

**步骤 4：市场制度分析**（仅 `ricequant` 模式，首次）
调用 `RiceQuantEval.get_market_regime()`，获取市场走势、波动率、趋势文字描述。
- 日期有效性验证：`m_start >= effective_end` 时跳过，记录警告
- 失败时 fallback：`"[市场数据暂时不可用，请基于通用量化逻辑生成假说]"`

**步骤 5：构建 Prompt 并调用 LLM**

系统 Prompt 包含：角色描述、混合知识上下文（最多 6000 字符）、跨 Agent 学习指令。

用户 Prompt 在 `iteration > 1` 时注入上一轮具体改进建议，明确要求 LLM 采纳并修改策略。

**步骤 6：解析 JSON → `HypothesisOutput`**
```json
{"hypothesis_name": "...", "hypothesis_description": "...", "rationale": "..."}
```

**返回值**（写入 State）：
```python
{
    "rag_context": combined_knowledge,
    "macro_news_summary": macro_context,
    "market_regime_summary": market_regime,
    "hypothesis_name": result.hypothesis_name,
    "hypothesis_description": result.hypothesis_description,
    "rationale": result.rationale,
    "messages": [...]
}
```

**错误处理**：所有异常被捕获，记录原始 LLM 响应（DEBUG 级别），返回 `{"error": str(e)}`。

---

### 6.2 `agents/factor_agent.py` — FactorAgent

**职责**：将假说两步转换为可执行的 Qlib 表达式：假说文本 → 数学公式 → Qlib 代码。包含自我纠错重试机制。

**LLM 温度**：`0.1`（低温，保证代码生成确定性）

#### 类常量

```python
QLIB_OPERATORS = {
    "Rank", "CSRank", "CSZScore", "Mean", "Std", "Median", "EMA", "Abs",
    "Ref", "Log", "Sum", "If", "Greater", "Less", "And", "Or", "Delta",
    "Corr", "Correlation", "Cov", "Ts_Rank", "Ts_ArgMax", "Ts_ArgMin",
    "Ts_Percentile", "Winsorize", "GroupNeutral", "Percentile", "Clip",
    "Count", "Sign", "Sqrt"
}  # 算子白名单（验证和 Prompt 注入均使用此集合）

QLIB_FIELDS = {"$close", "$open", "$high", "$low", "$volume", "$vwap"}
# 数据字段白名单

OPERATOR_SIGNATURES = """
- Rank(df): 截面百分比排名
- CSRank(df): 同 Rank(df)
- Mean(df, n): n 日滚动均值
...
"""  # 注入到 Prompt 的算子文档，帮助 LLM 正确使用
```

#### `FactorAgent._strip_markdown_json(text) -> str` (静态方法)

增强版 JSON 清理，核心解决 LLM 生成 LaTeX 公式时的反斜杠转义问题：

1. 去除代码块包装，提取 `{...}` 范围
2. 清除控制字符
3. **先尝试 `json.loads()`**——若成功直接返回，不做任何反斜杠处理
4. 若解析失败，才执行反斜杠修复正则：
   ```python
   re.sub(r'(?<!\\)\\(?!(?:["\\/]|u[0-9a-fA-F]{4}))', r'\\\\', text)
   ```
   含义：匹配不合法的单反斜杠（排除合法的 `\"`, `\\`, `\/`, `\uXXXX`），将其加倍转义。专门解决 `\text{}`、`\frac{}`、`\alpha` 等 LaTeX 命令在 JSON 中失效的问题。

#### `FactorAgent._validate_qlib_expression(expr) -> tuple[bool, str]`

对 Qlib 表达式做静态安全验证（6 道关卡）：

1. **空值检查**：表达式为空则失败
2. **拒绝检查**：含 "Cannot be expressed" 等字样说明 LLM 返回解释而非代码
3. **括号平衡**：逐字符验证括号嵌套深度
4. **字段白名单**：所有 `$xxx` 引用必须在 `QLIB_FIELDS` 内
5. **Python 语法**：将 `$field` 替换为 `field_xxx`，用 `ast.parse()` 验证
6. **算子白名单 + 参数数量**：遍历 AST 的所有 `ast.Call` 节点，验证函数名在 `QLIB_OPERATORS` 内，并检查已知二元/三元算子的参数数量

#### `FactorAgent.__call__(state) -> dict`

**步骤 1：Formalization（假说 → 数学公式）**

Prompt 要求 LLM 严格输出符合 `FormalizationOutput` 的 JSON：
```json
{"math_formula": "F_t = ...", "variables_defined": {"r_t": "第t日收益率"}}
```

**步骤 2：Implementation（数学公式 → Qlib 代码）+ 自我纠错循环**

循环参数：`max_retries = 2`，最多共执行 3 次。

每次循环：
1. 调用 LLM 生成 `ImplementationOutput`：
   ```json
   {"code_expression": "Rank(Delta($close, 5) / Ref($close, 5))", "is_valid_syntax": true}
   ```
2. 调用 `_validate_qlib_expression()` 做静态验证
3. 若通过，再调用 `RiceQuantEval.dry_run()` 做动态干运行验证（用随机数据）
4. 双重通过 → 成功，break
5. 失败 → 构建纠错消息，进入下一轮重试

纠错消息模板（滑动窗口，仅保留基础 2 条 + 最后一次失败对话）：
```python
messages = messages[:2] + [
    ("assistant", f'{{"code_expression": "{safe_code}", "is_valid_syntax": false}}'),
    ("user", f"The code has a syntax error: {safe_feedback}. Please FIX IT..."),
]
# safe_code 和 safe_feedback 已将 { } 转义为 {{ }} 防止 LangChain 模板误解析
```

**返回值**：
```python
{
    "math_formula": ..., "variables_defined": ...,
    "code_expression": ..., "is_valid_syntax": ...,
    "messages": [...]
}
```

---

### 6.3 `agents/eval_agent.py` — EvalAgent

**职责**：执行因子回测，进行 LLM 反思审查，更新早停指标，将经验保存到 RAG。

**LLM 温度**：`0.4`（适度灵活以进行分析推理）

#### `EvalAgent._execute_alphaeval_backtest(code, mode, engine, test_start_date, test_end_date) -> dict`

执行真实回测，失败时回退到模拟指标。

**成功（真实回测）返回**：
```python
{
    "information_coefficient": float,  # IC：因子值与次日收益的 Spearman 相关系数均值
    "rank_ic": float,                  # Rank IC：基于排名的 IC
    "rre": float,                      # Realized Return Efficiency（稳健性指标）
    "sharpe": float,                   # 顶层分组的年化 Sharpe 比率
    "max_drawdown": float,             # 顶层分组累计收益的最大回撤
    "pfs1": float,                     # Portfolio Score 1（顶层组年化收益）
    "pfs2": float,                     # Portfolio Score 2（底层组年化收益）
    "diversity": float,                # 因子多样性分数
    "llm_score": float,                # RiceQuant 内置 LLM 评分
    "daily_returns": dict,             # 日期 → 日收益率映射
}
```

**失败回退（模拟指标）**：
```python
seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
rng = random.Random(seed)
# 相同代码每次生成相同的伪随机指标（确定性）
# 附加 "_simulated": True 标记，供 EvalAgent 和 Manager 识别过滤
```

回退触发条件：`FileNotFoundError`（数据缺失）、`ValueError`（数据异常）、`ImportError`（rqdatac 未安装）或任意其他异常。

#### `EvalAgent.__call__(state) -> dict`

**步骤 1：执行回测**
读取 `code_expression`、日期参数，调用 `_execute_alphaeval_backtest()`。提取 `_simulated` 和 `daily_returns` 字段后从 metrics 中移除（保持 metrics 纯净）。

**步骤 2：LLM 反思审查（Reflexive Review）**
构建 Prompt，传入假说、代码、指标，LLM 输出 `ReflexiveReviewOutput`：
```json
{
  "review_summary": "IC=0.031，因子显示较好的预测能力...",
  "is_effective": true,
  "suggested_improvements": "考虑在高波动期使用条件激活..."
}
```

**步骤 3：RAG 经验保存**（仅真实回测结果，跳过模拟指标）
```python
if not is_simulated:
    self.knowledge.rag.add_experience(hypothesis, code, metrics, is_effective, review)
```

**步骤 4：早停指标更新**
```python
if current_ic > best_ic:
    new_best_ic = current_ic
    new_patience_counter = 0
    new_best_code = code          # 记录最优代码
else:
    new_best_ic = best_ic
    new_patience_counter = patience_counter + 1
    new_best_code = state.get("best_code_expression", code)  # 保留历史最优
```

**返回值**：包含 `backtest_metrics`、`daily_returns`、`review_summary`、`is_effective`、`is_simulated`、`suggested_improvements`、`best_ic`、`best_code_expression`、`patience_counter`。

---

### 6.4 `agents/summary_agent.py` — SummaryAgent

**职责**：在 Manager 阶段（LangGraph 工作流外）为每个通过筛选的因子生成 Markdown 研究报告和权益曲线图表。

**LLM 温度**：`0.3`（稳定的专业报告输出）

#### `SummaryAgent.generate_equity_curve(returns, factor_id) -> str`
- 绘制累计收益曲线 `(1 + returns).cumprod()`
- 保存为 `results/charts/{factor_id}_curve.png`
- `returns.empty` 时返回空字符串

#### `SummaryAgent.generate_markdown_report(factor_data) -> str`
生成包含以下章节的 Markdown 报告并保存至 `results/reports/{factor_id}.md`：
1. **规格描述**：假说名称 + Qlib 代码
2. **性能指标表**：IC / Rank IC / RRE
3. **权益曲线**：图片链接
4. **专业分析**：LLM 生成的经济学解读（含 "Economic Rationale Analysis" 小节）

---

## 7. 模块详解：核心能力层

### 7.1 `core/llm.py`

多提供商 LLM 统一网关，返回 LangChain `ChatOpenAI` 兼容客户端。

#### `get_llm_config(provider=None) -> dict`
- 指定 `provider`：直接返回该提供商的 API Key，不存在则抛 `ValueError`
- 未指定：按顺序遍历所有提供商，返回第一个有 Key 的配置（自动检测）

**支持的提供商**：

| 提供商 | 环境变量 | API 端点 | 默认模型 |
|---|---|---|---|
| `kimi` | `LLM_KEY` / `KIMI_API_KEY` | `api.moonshot.cn/v1` | `kimi-k2-turbo-preview` |
| `qwen` | `QWEN_API_KEY` | `dashscope.aliyuncs.com/...` | `qwen-max` |
| `glm` | `GLM_KEY` / `ZHIPU_API_KEY` | `open.bigmodel.cn/api/paas/v4` | `glm-5` |
| `openai` | `OpenAI_KEY` / `OPENAI_API_KEY` | `api.openai.com/v1` | `gpt-4o` |
| `deepseek` | `DEEPSEEK_API_KEY` | `api.deepseek.com/v1` | `deepseek-reasoner` |
| `openrouter` | `OPENROUTER_API_KEY` | `openrouter.ai/api/v1` | `deepseek/deepseek-r1` |
| `groq` | `GROQ_API_KEY` | `api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| `ollama` | `OLLAMA_API_KEY` | `$OLLAMA_BASE_URL` | `deepseek-r1:14b` |
| `vllm` | `VLLM_API_KEY` | `$VLLM_BASE_URL` | `meta-llama/Llama-3-70b-chat-hf` |
| `claude` (proxy) | `ClaudeCode_KEY` / `ANTHROPIC_API_KEY` | `api.gptsapi.net/v1` | `claude-3-5-sonnet-20241022` |

#### `get_llm(temperature, model_name, provider) -> BaseChatModel`
构建 `ChatOpenAI` 实例，统一配置：
- `max_retries=3`：自动重试 3 次
- `request_timeout=60`：60 秒超时，防止 API 挂起阻塞工作流

**各 Agent 温度设置**：

| Agent | 温度 | 理由 |
|---|---|---|
| `IdeaAgent` | 0.7 | 鼓励创新假说 |
| `EvalAgent` | 0.4 | 分析判断需适度灵活 |
| `SummaryAgent` | 0.3 | 专业报告需稳定 |
| `FactorAgent` | 0.1 | 代码生成需高确定性 |

---

### 7.2 `core/rag.py`

基于 ChromaDB 的向量检索模块，提供两类知识：
- **文档知识库**（静态）：来自 `data/rag_docs/`
- **回测经验库**（动态）：每次评估后通过 `add_experience()` 累积

#### `RAGModule.__init__(rebuild, embedding_provider, use_gpu)`
选择 Embedding 函数，加载或重建 ChromaDB。

**支持的 Embedding**：

| 提供商 | 模型 | 维度 |
|---|---|---|
| `glm` | `embedding-3` | 2048 |
| `openai` | `text-embedding-3-small` | 1536 |
| `local` | `BAAI/bge-m3`（HuggingFace） | 1024 |
| `cohere` | `embed-multilingual-v3.0` | 1024 |

#### `RAGModule._init_knowledge_base()`
递归扫描 `data/rag_docs/`，支持 `.txt`、`.pdf`、`.md`。将文件分块（最大 1000 字符，100 字符重叠），批量写入 ChromaDB（每批 8 条）。

#### `RAGModule.retrieve(query, n_results=3) -> str`
混合检索策略：
1. **语义检索**：ChromaDB 向量余弦相似度
2. **BM25 检索**：基于词频的关键词匹配
3. **去重合并**：以文档 ID 去重
4. **经验检索**：额外从 `experience` 集合检索历史回测记录

返回格式化文本（各片段用 `---` 分隔）。

#### `RAGModule.add_experience(hypothesis, code, metrics, is_effective, review)`
使用 `fcntl.flock()` 文件锁保护并发写入（适用于多进程模式）：
```python
with open(lock_file, "w") as lf:
    fcntl.flock(lf, fcntl.LOCK_EX)
    # 写入 ChromaDB experience 集合
    fcntl.flock(lf, fcntl.LOCK_UN)
# finally: os.unlink(lock_file)  — 清理锁文件
```

---

### 7.3 `core/wiki.py`

结构化因子卡片知识库（LLMWiki）。每张卡片：
- 持久化为 `data/wiki_db/{slug}.md`（带 YAML front-matter 的 Markdown）
- 同时在 ChromaDB `wiki_index` 集合中建立向量索引

#### `LLMWiki.add_or_update_page(slug, title, content, metadata)`
1. 生成 Markdown 文件（带 front-matter）
2. 写入 `data/wiki_db/{slug}.md`
3. Upsert 到 ChromaDB（同 slug 自动覆盖旧记录）
4. 追加日志到 `data/wiki_db/log.md`
5. 重新编译 `data/wiki_db/index.md`（全量索引）

**Markdown 文件格式**：
```markdown
---
title: 流动性冲击反转因子
updated: 2024-01-15T12:00:00
type: factor_card
---

**Hypothesis**: ...
**Implementation (Qlib)**: `Rank(Delta($close, 5))`
**IC / RankIC**: 0.0321 / 0.0289
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: ...
**Suggested Improvements**: ...
```

#### `LLMWiki.retrieve(query, n_results=3) -> str`
从 ChromaDB 检索最相关因子卡片，每条截取前 1000 字符。

#### `LLMWiki.get_page(slug) -> Optional[dict]`
从 Markdown 文件读取单张卡片，解析 YAML front-matter，返回 `{title, content, metadata}` 字典。

#### `LLMWiki.list_pages() -> List[str]`
列出所有 `.md` 文件（排除 `index.md` 和 `log.md`）的 slug 列表。

---

### 7.4 `core/hybrid_knowledge.py`

将 RAG 和 Wiki 封装为统一接口，所有 Agent 通过此接口访问知识。

#### `HybridKnowledge.__init__(rebuild_rag, embedding_provider, use_gpu, llm_provider, llm_model)`
初始化 `RAGModule` 和 `LLMWiki`，保存 LLM 配置供 `bootstrap_wiki()` 使用。

#### `HybridKnowledge.bootstrap_wiki(force=False)`
调用 `WikiBootstrapper`，从 RAG 文档中提取结构化知识写入 Wiki。由 Manager 在主进程中执行一次（`--wiki-bootstrap` 参数）。

#### `HybridKnowledge.retrieve(query, n_results=3) -> str`
同时调用 `rag.retrieve()` 和 `wiki.retrieve()`，拼接返回：
```python
combined = f"{rag_context}\n\n{wiki_context}"
```

#### `HybridKnowledge.update_wiki_after_eval(state) -> dict`
评估完成后自动更新 Wiki（无论是否模拟指标，均写入但附加 `simulated` 元数据）。

**Slug 生成规则**（防止同名碰撞）：
```python
base_slug = "".join([c if c.isalnum() else "_" for c in raw_name]).lower()
slug = f"{base_slug}_iter{iteration}"
```

**写入的元数据**：
```python
{
    "type": "factor_card",
    "status": "proven" if is_effective else "failed",
    "ic": ic, "rank_ic": rank_ic,
    "iteration": iteration,
    "is_effective": is_effective,
    "simulated": is_simulated,
}
```

---

## 8. 模块详解：因子评估层

### 8.1 `core/alphaeval/rq_eval.py`

RiceQuant 因子评估引擎，通过 `rqdatac` 获取 A 股数据，支持 Pandas 和 Polars 两套计算路径。

#### `init_rq_auth()`
通过 `RQ_USER`/`RQ_PASS` 或 `RQ_TOKEN` 认证 RiceQuant API。在 Manager 主进程调用一次，子进程中自动复用凭证。

#### `SafeEvalTransformer(ast.NodeTransformer)`
AST 安全变换器，防止代码注入。核心 `visit_Call` 方法：将未知函数名替换为字符串字面量，使得 `os.system("rm -rf /")` 变成无害的 `"os.system"(...)` 表达式（会产生 `TypeError` 而非执行危险操作）。

#### `RiceQuantEval.__init__(factor_expressions, test_start_date, test_end_date, universe, engine)`

| 参数 | 默认 | 说明 |
|---|---|---|
| `factor_expressions` | 必填 | Qlib 表达式列表 |
| `test_start_date` | `"2017-01-01"` | 回测起始日期 |
| `test_end_date` | `"2020-10-31"` | 回测结束日期 |
| `universe` | `"CSI300"` | 股票池（沪深300） |
| `engine` | `"pandas"` | 计算引擎 |

#### `RiceQuantEval._get_n(n) -> int` (静态方法)
安全提取时间窗口参数。若 `n` 是 `pd.Series`（LLM 错误传入），取最后一个非 NaN 值；失败则返回默认值 20。

#### `RiceQuantEval.compute_factors()` — Pandas 路径

构建完整的 Qlib 算子 `context` 字典，包含约 40 个函数，所有时序函数按 `axis=0`（时间轴）操作，数据格式为 `DataFrame(index=date, columns=stock)`。

**数据字段**（通过 rqdatac 获取）：
- `fields["close"]`：收盘价（`$close`）
- `fields["open"]`：开盘价（`$open`）
- `fields["high"]`：最高价（`$high`）
- `fields["low"]`：最低价（`$low`）
- `fields["volume"]`：成交量（`$volume`）
- `fields["vwap"]`：成交均价（`$vwap`）

**执行流程**：
1. 获取价量数据，构建 fields 字典
2. 对每个因子表达式：用正则替换 `$field` → `fields['field']`，通过 `SafeEvalTransformer` 安全编译，`eval()` 执行
3. 失败时抛出 `RuntimeError`（不填零，让 EvalAgent 知晓失败）

**完整算子列表**（Pandas 实现）：
- 数学：`Abs`, `Log`, `Sign`, `Sqrt`, `Exp`, `Ceil`, `Floor`
- 时序：`Mean(df,n)`, `Std(df,n)`, `Median(df,n)`, `Sum(df,n)`, `EMA(df,n)`, `Ref(df,n)`, `Delta(df,n)`
- 相关：`Corr(df1,df2,n)`（Spearman）, `Cov(df1,df2,n)`
- 排名：`Rank(df)`（截面 pct）, `CSRank(df)`, `Ts_Rank(df,n)`, `Ts_Percentile(df,n,p)`
- 极值：`Ts_ArgMax(df,n)`, `Ts_ArgMin(df,n)`
- 条件：`If(cond,a,b)`, `Greater(a,b)`, `Less(a,b)`, `And(a,b)`, `Or(a,b)`
- 截面：`CSZScore(df)`, `Winsorize(df,pct)`, `GroupNeutral(df)`
- 其他：`Clip(df,lo,hi)`, `Count`, `Scale`, `WMA`

#### `RiceQuantEval.compute_factors_polars()` — Polars 路径

将数据转为长格式 Polars DataFrame（列：`datetime`, `instrument`, `close`, ...），调用 `PolarsEngine.compute_all()` 批量计算，转回 Pandas 格式供后续分析。

#### `RiceQuantEval.get_market_regime(start_date, end_date, lookback_days) -> str`

获取 CSI300 指数的市场制度描述：
- 通过 rqdatac 获取指数日行情
- 计算总收益率、年化波动率、趋势（基于 MA）
- 返回格式化的中文描述字符串

**错误处理**：将 `"Quota exceeded"`/`"rate limit"` 错误与其他错误分别处理（单一 `except` 块内用 `if/elif` 分支，避免死代码）。

#### `RiceQuantEval.run()` — 主回测

**完整流程**：
1. 调用 `compute_factors()` 或 `compute_factors_polars()`
2. 获取标签数据（次日收益率 `return_1d`）
3. 因子数据与标签数据对齐（inner join by `[datetime, instrument]`）
4. 清理 `inf/nan`；若对齐后数据为空，抛出 `ValueError("All factor data is NaN/Inf...")`
5. **IC 计算**：每日截面 Spearman 相关系数，取均值
6. **Rank IC**：每日截面排名相关系数均值
7. **Quintile 分层回测**（5组）：计算各层次日均收益，顶层为 `pfs1`，底层为 `pfs2`
8. **Sharpe**：基于顶层组日收益，年化计算
9. **最大回撤**：顶层组累计收益的 MDD

#### `RiceQuantEval.run_robustness_test(noise_level=0.05)`

对因子加 5% 高斯噪声，重算 IC，与原始 IC 对比：
```python
self.rre = max(0.0, min(1.0, noisy_ic / orig_ic))
```
`rre` 越接近 1，因子越稳健。

#### `RiceQuantEval.dry_run(expression) -> tuple[bool, str]` (静态方法)

用虚拟数据（30 只股票 × 252 交易日）验证表达式可执行性，不需要真实市场数据。

- 为所有支持的 `$field` 生成随机数
- 在 context 中 eval 表达式
- 成功且有非 NaN 值 → `(True, "OK")`
- 失败 → `(False, 错误描述)`

---

### 8.2 `core/alphaeval/polars_engine.py`

Polars 高性能因子计算引擎，包含：
1. Rust 编译器（`polars_plugins.compile_alpha()`）
2. Python AST 逐步求值器（解决 Polars `.over()` 嵌套限制）

#### 模块级算子函数（全部注册到 `PolarsEngine.context`）

**截面算子**（`.over("datetime")`）：
```python
Rank(x)        # 截面百分比排名 = rank / count
CSRank(x)      # 同 Rank
CSZScore(x)    # (x - mean) / std，std=0 时用 1.0 替代
Winsorize(x, pct=0.05)    # 截断超出 [pct, 1-pct] 分位的值
GroupNeutral(x)           # 截面去均值（市场中性化）
Percentile(x)             # 截面百分位排名
Scale(x, a=1)             # 按截面绝对值之和归一化
```

**时序算子**（`.over("instrument")`）：
```python
Mean(x, n)     # Rolling mean（n=None 时退化为截面均值）
Std(x, n)      # Rolling 标准差
Median(x, n)   # Rolling 中位数
Sum(x, n)      # Rolling 求和
EMA(x, n)      # 指数移动平均（ewm_mean）
WMA(x, n)      # 加权移动平均（用 ewm_mean 近似）
Ref(x, n)      # 取 n 日前的值（shift(n)）
Delta(x, n)    # x - Ref(x, n)
Corr(x, y, n)  # Rolling Spearman 相关
Cov(x, y, n)   # Rolling 协方差
Ts_Rank(x, n)  # Rust 插件实现的时序百分比排名
Ts_ArgMax(x, n) / Ts_ArgMin(x, n)  # Rust 插件：最大/最小值距今天数
Ts_Percentile(x, n, p=50)  # n 日内第 p 百分位数值
Ts_Max(x, n) / Ts_Min(x, n)  # Rolling 最大/最小值
```

**数学/逻辑算子**：
```python
Abs, Log, Sign, Sqrt, Exp, Ceil, Floor, Round, Sin, Cos, Tan
If(cond, a, b) = pl.when(cond).then(a).otherwise(b)
Greater(a,b), Less(a,b), GreaterEqual, LessEqual, Equal, NotEqual
And(*args)     # 变长参数，functools.reduce 链式 &
Or(*args)      # 变长参数，functools.reduce 链式 |
```

**别名**（兼容 LLM 可能生成的非标准名称）：
```python
Add=a+b, Sub=a-b, Mul=a*b, Div=a/b
Multiply=Mul, Divide=Div, Subtract=Sub, Negate=Neg
Neg=-a, Inv=1/a, Pow=a**b
Max=pl.max_horizontal(a,b), Min=pl.min_horizontal(a,b)
```

#### `_get_int(n, op_name) -> int`
安全的窗口参数转换。若 `n` 是 `pl.Expr`（LLM 错误传入序列），抛出描述性 `ValueError`。

#### `_python_compile_alpha(expression) -> str`
纯 Python 回退编译器，仅将 `$fieldname` 替换为 `pl.col('fieldname')`。

#### `_preprocess_expression(expression) -> str`
预处理：去首尾空白，合并多余空格。

#### `PolarsEngine.evaluate(expression) -> pl.Expr`

**双层编译策略**：
1. `lib.compile_alpha(expression)` — Rust 编译器（性能最优）
2. 若返回 `"Error:..."` 或 eval 失败 → 回退到 `_python_compile_alpha()`
3. 在 `{"__builtins__": {}}` 受限环境中 `eval()`，结果强制转 `Float64`

#### `PolarsEngine.compute_all(df, expressions) -> pl.DataFrame`
批量计算，单个失败时以 `null` 列代替，继续计算其他因子。

#### `PolarsEngine._eager_eval(df, expr_str) -> pl.DataFrame`

**解决 Polars `.over()` 嵌套全 null 问题的核心方法**。

问题背景：`Rank(Delta($close, 5))` 在 Polars 中，内层 `Delta` 需要 `.over("instrument")`（按股票分组），外层 `Rank` 需要 `.over("datetime")`（按日期截面）。Polars 不允许这种嵌套，会产生全 null 输出。

解决方案：解析 AST，逐节点求值。当遇到截面算子（`_CS_OPS` 集合）且其参数是复合表达式时，先将该参数物化为临时列：
```python
if is_cs and isinstance(arg_val, pl.Expr) and not self._is_bare_col(arg_node):
    tmp = f"__cs_arg_{len(tmp_cols)}__"
    df_container[0] = df_container[0].with_columns(arg_val.alias(tmp))
    tmp_cols.append(tmp)
    arg_val = pl.col(tmp)  # 用物化后的裸列名替换复合表达式
```

截面算子集合：`{"Rank", "CSRank", "CSZScore", "GroupNeutral", "Winsorize", "Percentile", "Scale"}`

#### `PolarsEngine._eval_ast_node(node, df_container, tmp_cols)`

递归 AST 求值器，处理节点类型：
- `ast.Constant` → 字面量
- `ast.Attribute` → `pl.col`, `pl.lit` 等属性访问
- `ast.Name` → 从 `context` 查找函数
- `ast.UnaryOp` → `-x`（USub）、`+x`（UAdd）、`~x`（Not）
- `ast.BinOp` → `+`, `-`, `*`, `/`, `**`, `&`, `|`
- `ast.Compare` → `>`, `<`, `>=`, `<=`, `==`, `!=`
- `ast.Call` → 函数调用，触发截面算子的参数物化逻辑

---

### 8.3 `core/alphaeval/modeltester.py`

微软 Qlib 框架适配器（`--mode qlib` 时使用）。`AlphaEval` 类封装 Qlib 的 Alpha158 评估流程，接口与 `RiceQuantEval` 一致（有 `.run()`、`.ic`、`.rankic` 属性），使 `EvalAgent` 可以无缝切换。

---

### 8.4 `polars_plugins/src/lib.rs`

Rust 编写的 Polars 扩展插件，提供：
1. 高性能时序算子（`ts_rank`、`ts_argmax`、`ts_argmin`）
2. Qlib 表达式编译器（`compile_alpha`）

#### Rust 时序算子

三个算子均通过 `#[polars_expr]` 宏注册为 Polars 插件，使用 `rayon` 并行计算：

- **`ts_rank(inputs, window_size)`**：窗口内当前值的百分比排名（`rank/count`），NaN 安全
- **`ts_argmax(inputs, window_size)`**：窗口内最大值的位置距今天数
- **`ts_argmin(inputs, window_size)`**：窗口内最小值的位置距今天数

均在 `PolarsEngine` 中通过 `register_plugin_function()` 调用，结果再加 `.over("instrument")`。

#### 表达式编译器 AST

```rust
enum Expr {
    Literal(String),                      // 数值字面量：5, 0.05
    Field(String),                        // 字段引用：$close → Field("close")
    Binary(Box<Expr>, String, Box<Expr>), // 二元运算：a + b, a > b
    Call(String, Vec<Expr>),              // 函数调用：Rank($close)
}
```

#### 解析器函数（nom 组合子）

- `identifier`：匹配 `[A-Za-z0-9_.]` 组成的标识符
- `number`：匹配数字（含可选负号和小数点），如 `-5.0`
- `unary_neg`：匹配 `-` 后接任意 `primary`，生成 `Call("Neg", [expr])`
- `primary`：优先级最高，依次尝试：函数调用 → 括号表达式 → `$field` → 数字 → 一元负号 → 裸标识符
- `term`：处理 `*`, `/`, `&`, `|`（左结合）
- `parse_expression`：处理 `+`, `-` 及所有比较运算符（左结合）

#### 代码生成 `to_python(expr) -> String`

| AST 节点 | 生成 Python |
|---|---|
| `Literal("5")` | `"5"` |
| `Field("close")` | `"pl.col('close')"` |
| `Binary(a, "+", b)` | `"(a + b)"` |
| `Call("Rank", [x])` | `"Rank(x)"` |

#### `compile_alpha(expression) -> PyResult<String>`

入口函数，解析后若有剩余未解析输入，返回 `"Error: Unparsed trailing input: '...'"` 供 Python 侧检测并触发回退编译器。

**重新编译命令**：
```bash
cd polars_plugins && maturin develop --release
```

---

## 9. 模块详解：Schemas 层

### `schemas/messages.py`

所有 LLM 结构化输出的 Pydantic 模型，通过 `model_validate_json()` 解析 LLM 的 JSON 输出。

#### `HypothesisOutput`（IdeaAgent 输出）
```python
class HypothesisOutput(BaseModel):
    hypothesis_name: str         # 因子名称（简短有辨识度）
    hypothesis_description: str  # 详细描述
    rationale: str               # 金融逻辑和经济学依据
```

#### `FormalizationOutput`（FactorAgent 第一步输出）
```python
class FormalizationOutput(BaseModel):
    math_formula: str                 # 正式数学公式（可含 LaTeX）
    variables_defined: Dict[str, str] # 变量释义字典
```

#### `ImplementationOutput`（FactorAgent 第二步输出）
```python
class ImplementationOutput(BaseModel):
    code_expression: str    # Qlib 表达式
    is_valid_syntax: bool   # LLM 自评估（不可信，由 FactorAgent 独立验证覆盖）
```

#### `ReflexiveReviewOutput`（EvalAgent 反思审查输出）
```python
class ReflexiveReviewOutput(BaseModel):
    review_summary: str         # 回测结果分析摘要（含具体指标值）
    is_effective: bool          # 是否有效：IC > 0.02 AND Rank IC > 0.02
    suggested_improvements: str # 具体可操作的改进建议（传给下一轮 IdeaAgent）
```

---

## 10. 模块详解：顶层入口

### 10.1 `sub_agent.py`

单个研究员 Agent 的封装，可被 `ProcessPoolExecutor` 在子进程中运行。

#### `AlphaResearcher.__init__(...)`
接收所有运行参数（role_prompt, max_iterations, evaluation_mode 等），调用 `build_workflow()` 构建独立的 LangGraph 应用。

#### `AlphaResearcher.run() -> dict`

**构建初始状态**并调用 `self.app.stream(initial_state)` 流式执行工作流。逐节点累积 `final_state`：
```python
for output in self.app.stream(initial_state):
    for node_name, state_update in output.items():
        final_state.update(state_update)
```

**错误处理**：异常时记录 `final_state["error"]`，确保 Manager 能检测。

**返回值标准化**：
- `perf_metric`：优先用 Sharpe（避免 IC 和 Sharpe 混用——但当前代码中确实混用，是已知设计问题）
- `returns_series`：日期字符串索引转 `pd.Timestamp`（`format="%Y-%m-%d", errors="coerce"`），NaT 行被删除并记录警告

```python
return {
    "role": self.role_prompt,
    "hypothesis": final_state.get("hypothesis_name"),
    "code": final_state.get("code_expression"),
    "metrics": metrics,
    "perf_metric": perf_metric,
    "returns": returns_series,
    "is_effective": final_state.get("is_effective", False),
    "error": final_state.get("error")
}
```

#### `run_agent_task(kwargs)` 全局函数

ProcessPoolExecutor 的任务入口（模块级函数，可被 pickle）。添加 `random.uniform(0.1, 1.0)` 随机延迟，防止多进程同时写 SQLite。

---

### 10.2 `manager.py`

多 Agent 群体协调器。

#### `PortfolioManager.__init__(roles, **kwargs)`

默认 3 个角色（均值回归、动量、统计套利）。初始化 SQLite 数据库：
```sql
CREATE TABLE IF NOT EXISTS alpha_pool (
    id TEXT PRIMARY KEY,
    role TEXT, hypothesis TEXT, code TEXT,
    ic REAL, rank_ic REAL, report_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

#### `PortfolioManager.evaluate_and_combine(results_list) -> list`

**第一关：IC 阈值过滤**（`threshold = 0.01`）
- 跳过有 `error` 的结果
- IC <= 0.01 的因子被淘汰，记录 Culled 日志

**第二关：相关性去冗余**（阈值 0.7）
- 对齐两个因子的日收益序列（`.dropna()`）
- 重叠少于 10 个数据点 → 跳过（视为不相关）
- Pearson 相关 > 0.7 → 标记为冗余，丢弃

通过两关的因子获得唯一 ID `f"alpha_{uuid4().hex[:8]}"` 并进入最终池。

#### `PortfolioManager.run_swarm(parallel=False)`

主流程：
1. **全局认证**（ricequant 模式）：`init_rq_auth()`
2. **Wiki Bootstrap**（`--wiki-bootstrap`）：主进程初始化，防止子进程重复执行
3. **并行/串行执行**：`ProcessPoolExecutor` 或 for 循环
4. **筛选**：`evaluate_and_combine()`
5. **遗传交叉**（≥ 2 个因子时）：
   - 按 IC 排序，取 Top-2 作为父代
   - 构建包含两个父代详细信息的 crossover_role prompt
   - 运行一个新的 `run_agent_task()` 生成混合因子
   - 对混合因子同样做 IC 阈值 + 相关性过滤
6. **报告生成**：`summary_agent.generate_markdown_report(factor)`
7. **SQLite 持久化**（每因子独立 try/except，防止单个失败影响其他）：
   ```python
   try:
       cursor.execute("INSERT OR REPLACE INTO alpha_pool ...")
       conn.commit()
   except Exception as db_err:
       logger.warning(...)  # 记录失败，继续处理其他因子
   ```
8. **JSON 备份**：日期键通过 `.isoformat()` 转为字符串

---

### 10.3 `main.py`

单 Agent 顺序执行入口。与 `manager.py` 的主要区别：
- 只运行一个 SubAgent（无群体协调、无遗传交叉）
- 支持通过 `scripts/fetch_macro_news.py` 预获取宏观新闻
- 不做 IC 阈值过滤，直接输出最终因子信息

**日志配置**：
```python
logger.add("results/run_{time}.log", rotation="10 MB", retention="10 days", level="DEBUG")
```

---

## 11. 完整数据流与流程说明

### 11.1 单次因子挖掘流程（LangGraph 内部）

```
初始状态 {iteration:1, max_iterations:3, role_prompt:"...", best_ic:-999, patience:0}
         │
         ▼
    ┌─────────────────────────────────────────┐
    │            idea_agent                    │
    │  1. 检索 RAG 文档 + Wiki 卡片            │
    │  2. 获取市场制度分析 (RiceQuant)          │
    │  3. 获取宏观新闻 (RAG)                   │
    │  4. 拼接上下文（≤6000字符）              │
    │  5. LLM(temp=0.7) 生成假说 JSON          │
    │  ────────────────────────────────────── │
    │  输出: hypothesis_name/description/rationale│
    └────────────────┬────────────────────────┘
                     │ route_after_idea（检查 error, hypothesis_name）
                     ▼
    ┌─────────────────────────────────────────┐
    │           factor_agent                   │
    │  Step 1: LLM(temp=0.1) 假说→数学公式     │
    │    输出: math_formula, variables_defined  │
    │                                          │
    │  Step 2: LLM(temp=0.1) 公式→Qlib代码     │
    │    + 自我纠错循环（最多 2 次重试）        │
    │    ① _validate_qlib_expression()         │
    │    ② RiceQuantEval.dry_run()             │
    │  ────────────────────────────────────── │
    │  输出: code_expression, is_valid_syntax   │
    └────────────────┬────────────────────────┘
                     │ route_after_factor（检查 error, code_expression）
                     ▼
    ┌─────────────────────────────────────────┐
    │            eval_agent                    │
    │  Step 1: 真实回测 (RiceQuantEval.run())  │
    │    ├─ 若失败 → 模拟指标（_simulated=True）│
    │    └─ 成功 → IC, Rank IC, Sharpe, ...    │
    │                                          │
    │  Step 2: LLM(temp=0.4) 反思审查          │
    │    输出: review_summary, is_effective,    │
    │           suggested_improvements         │
    │                                          │
    │  Step 3: 若真实回测 → add_experience(RAG) │
    │                                          │
    │  Step 4: 早停指标更新                     │
    │    best_ic, best_code, patience_counter  │
    └────────────────┬────────────────────────┘
                     │ route_after_eval（始终 → wiki_update）
                     ▼
    ┌─────────────────────────────────────────┐
    │           wiki_update                    │
    │  update_wiki_after_eval(state)           │
    │  写入因子卡片到 data/wiki_db/            │
    │  刷新 wiki_context 供下一轮使用          │
    └────────────────┬────────────────────────┘
                     │ route_after_wiki（早停判断）
            ┌────────┴────────┐
         continue           end
        （iteration<max      （IC≥0.05
         且patience<3）       或patience≥3
                              或iteration==max）
            │
            ▼
    ┌───────────────┐
    │   increment   │  iteration += 1，重置 error/is_valid_syntax
    └───────┬───────┘
            │ 固定边
            └──────────────> idea_agent（下一轮）
```

### 11.2 因子表达式完整转换链示例

```
原始假说：
"利用近期成交量异常放大预测短期价格反转"

FactorAgent Step1（数学公式）：
math_formula = "F_t = -\Delta P_t \cdot Z_V(t)"
variables_defined = {"Delta_P_t": "第t日价格变化", "Z_V(t)": "成交量截面Z分"}

FactorAgent Step2（Qlib代码）：
code_expression = "Rank(-Delta($close, 1)) * Rank(CSZScore($volume))"

验证链：
  _validate_qlib_expression():
    ✓ 括号平衡
    ✓ $close, $volume 在白名单
    ✓ AST 解析成功
    ✓ Rank, Delta, CSZScore 均在算子白名单
    ✓ Delta 有 2 个参数
  dry_run():
    ✓ 用随机数据执行成功，产生非 NaN 值

Polars 引擎执行：
  Rust: compile_alpha("Rank(-Delta($close, 1)) * Rank(CSZScore($volume))")
      → "Rank(Neg(Delta(pl.col('close'), 1))) * Rank(CSZScore(pl.col('volume')))"

  _eager_eval() AST 遍历：
    1. 解析整体为 BinOp(Mul)
    2. 左侧 Call("Rank", [UnaryOp(Neg, Call("Delta", [$close, 1]))])
       - Delta 是时序算子：Delta(pl.col('close'), 1).over("instrument")
       - 物化为临时列 __cs_arg_0__（因为 Rank 是截面算子，参数是复合表达式）
       - Rank(__cs_arg_0__) 按 datetime 截面排名
    3. 右侧 Call("Rank", [Call("CSZScore", [$volume])])
       - CSZScore(pl.col('volume')) 按 datetime 截面 Z-Score
       - 物化为临时列 __cs_arg_1__
       - Rank(__cs_arg_1__) 按 datetime 截面排名
    4. 两个 Rank 结果相乘
    5. 清除临时列

RiceQuantEval 指标：
  IC = 0.0289（每日截面 Spearman 相关均值）
  Rank IC = 0.0245
  Sharpe = 1.23（顶层分组年化）
  RRE = 0.87（噪声稳健性）

EvalAgent 反思：
  is_effective = True（IC=0.0289 > 0.02）
  suggested_improvements = "考虑在高波动期增加波动率条件过滤，降低假信号..."
```

### 11.3 跨迭代学习机制

```
迭代 1：
  IdeaAgent 生成 "简单动量强度因子"
  FactorAgent → Rank(EMA($close, 10) / EMA($close, 50))
  EvalAgent → IC=0.008（低于有效阈值）
  反思 → "震荡市场中简单动量效果差，建议波动率调整"
  Wiki → 写入失败卡片（status="failed", simulated=False）

迭代 2：
  IdeaAgent 读取 Wiki（"上轮动量因子失败：IC=0.008，建议波动率调整"）
  生成 "波动率调整动量因子"
  FactorAgent → Rank(Delta($close, 20) / Std($close, 20))
  EvalAgent → IC=0.031（有效！），patience_counter 重置为 0
  Wiki → 写入成功卡片（status="proven"）
  RAG → add_experience（记录成功经验供检索）

迭代 3：
  IdeaAgent 读取成功卡片 + 新一轮改进建议
  ...若连续 3 轮 IC 不再提升 → patience_counter = 3 → 工作流结束
```

---

## 12. 配置参数全览

### 12.1 环境变量（`.env`）

```ini
# === LLM 提供商（至少一个）===
LLM_KEY=               KIMI_API_KEY=          # Kimi/Moonshot
ZHIPU_API_KEY=         GLM_KEY=               # 智谱 GLM（兼顾 Embedding）
OPENAI_API_KEY=        OpenAI_KEY=            # OpenAI
DEEPSEEK_API_KEY=                             # DeepSeek
QWEN_API_KEY=                                 # 通义千问
GROQ_API_KEY=                                 # Groq（免费高速）
OPENROUTER_API_KEY=                           # OpenRouter
ClaudeCode_KEY=        ANTHROPIC_API_KEY=     # Claude（代理）

# === 本地 LLM ===
OLLAMA_BASE_URL=http://localhost:11434/v1
VLLM_BASE_URL=http://localhost:8000/v1

# === RiceQuant ===
RQ_USER=用户名
RQ_PASS=密码
RQ_TOKEN=token值  # 与 USER/PASS 二选一
```

### 12.2 关键运行时参数

| 参数位置 | 当前值 | 含义 |
|---|---|---|
| `graph.py` route_after_wiki `current_ic >= 0.05` | 0.05 | IC 早停阈值（异常优秀时提前结束） |
| `graph.py` route_after_wiki `patience >= 3` | 3 | 无改进早停轮数 |
| `manager.py` evaluate_and_combine `threshold` | 0.01 | 因子进入最终池最低 IC |
| `manager.py` evaluate_and_combine 相关性 | 0.7 | Pearson 相关性剔除阈值 |
| `manager.py` 最小相关样本量 | 10 | 计算相关性所需最少重叠点 |
| `idea_agent.py` 上下文截断 | 6000 | 知识上下文最大字符数 |
| `factor_agent.py` max_retries | 2 | 代码自我纠错最多次数 |
| `llm.py` request_timeout | 60s | 单次 API 超时 |
| `llm.py` max_retries | 3 | LLM 自动重试次数 |
| `rq_eval.py` noise_level | 0.05 | 稳健性测试噪声水平（5% 高斯噪声） |
| `rag.py` batch_size | 8 | ChromaDB 批量写入大小 |
| `wiki.py` 卡片截断 | 1000字符 | 检索返回的单卡片最大长度 |

---

## 13. 输出文件说明

### `results/alpha_miner.db`
SQLite 数据库，存储所有通过筛选的因子。
```bash
sqlite3 results/alpha_miner.db \
  "SELECT hypothesis, code, ic, rank_ic FROM alpha_pool ORDER BY ic DESC"
```

### `results/alpha_pool.json`
JSON 备份，与 SQLite 内容相同，额外包含 `daily_returns` 字典（日期 ISO 字符串 → 日收益率）。

### `results/reports/{factor_id}.md`
每个因子的 Markdown 研究报告：规格描述 + 性能指标表 + 权益曲线图 + LLM 经济学解读。

### `results/charts/{factor_id}_curve.png`
权益曲线图，顶层分组的累计收益率随时间变化。

### `data/wiki_db/`
```
data/wiki_db/
├── index.md                     # 自动维护的全量因子索引
├── log.md                       # 所有写入操作的日志记录
└── {hypothesis_slug}_iter{n}.md # 每个因子实验的结构化卡片
```

### `data/chroma_db/`
ChromaDB 向量数据库：`knowledge`（RAG 文档）、`experience`（回测经验）集合。

---

## 14. 已知问题与注意事项

### 14.1 功能性问题

1. **`rq_eval.py` Percentile 实现错误**
   当前实现等同于 Rank（返回百分比排名）而非指定百分位数的数值。
   ```python
   # 当前（错误）
   def Percentile(df, p): return df.rank(axis=1, pct=True)
   # 正确应为
   def Percentile(df, p): return df.apply(lambda x: x.quantile(float(p)/100))
   ```

2. **模拟指标无法区分**
   真实回测失败时回退到哈希确定性模拟指标，Manager 无法区分"零 alpha 因子"和"数据获取失败"。

3. **早停 IC 阈值偏高**
   `route_after_wiki` 中 `IC >= 0.05` 在实际 A 股因子中极难达到，早停几乎不会通过此路径触发。

4. **`perf_metric` 量纲不统一**
   `sub_agent.py` 中若 Sharpe 可用则用 Sharpe，否则用 IC——两者量纲不同，Manager 的 `threshold=0.01` 判断不适用于 Sharpe。

### 14.2 使用限制

- **RiceQuant 权限**：需要有效订阅，免费账号可能无法获取完整历史数据
- **Polars 版本**：要求 `polars >= 1.0.0`；Rust 插件需要 `maturin >= 1.0`
- **并行模式**：多进程 `spawn` 启动在 Windows 上较慢；建议 Linux/macOS
- **内存**：大时间范围（>5年）+ 全市场因子计算需要 >8GB 内存
- **ChromaDB 并发**：多进程写入使用文件锁，但读写并发可能有脏读（轻量负载通常无影响）

### 14.3 调试技巧

```bash
# 查看详细运行日志
tail -f results/run_*.log

# 单因子干运行（无需 RiceQuant 凭证）
python -c "
from core.alphaeval.rq_eval import RiceQuantEval
ok, msg = RiceQuantEval.dry_run('Rank(Delta(\$close, 5) / Ref(\$close, 5))')
print(ok, msg)
"

# 测试 Polars 编译器
python test_compile.py

# 检查 Wiki 积累情况
cat data/wiki_db/index.md

# 查看 SQLite 因子库
sqlite3 results/alpha_miner.db \
  "SELECT id, hypothesis, ic FROM alpha_pool ORDER BY ic DESC LIMIT 10"
```

### 14.4 扩展指南

**添加新 LLM 提供商**：在 `core/llm.py` 的 `get_llm()` 中添加 `elif provider == "new_name":` 分支，设置 `base_url` 和默认 `model_name`；在 `get_llm_config()` 的 `providers` 字典中添加环境变量映射。

**添加新 Qlib 算子**：
1. `rq_eval.py` context 字典：添加 Pandas 实现
2. `polars_engine.py`：添加 Polars 实现函数并注册到 `self.context`
3. `factor_agent.py` `QLIB_OPERATORS` 集合：添加名称
4. `factor_agent.py` `OPERATOR_SIGNATURES`：添加签名文档

**添加新数据字段**：在 `rq_eval.py` 数据获取代码和 `factor_agent.py` 的 `QLIB_FIELDS` 集合中同步添加。

**修改早停策略**：调整 `workflow/graph.py` 中 `route_after_wiki()` 的判断逻辑。

**修改筛选策略**：调整 `manager.py` 中 `evaluate_and_combine()` 的 `threshold`（IC 阈值）和相关性阈值（0.7）。
