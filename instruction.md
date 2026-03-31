# AlphaMiner — Project Instruction Manual

> A fully "vibe-coded" autonomous alpha factor mining framework built on **LangGraph**, **Qlib**, and **LLM agents**. The system automatically 
proposes market hypotheses, translates them into quantitative factors, backtests them, and iteratively improves through a reflexive feedback loop.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Workflow & State Machine](#workflow--state-machine)
4. [Agents](#agents)
   - [IdeaAgent](#ideaagent)
   - [FactorAgent](#factoragent)
   - [EvalAgent](#evalagent)
5. [Core Modules](#core-modules)
   - [LLM Wrapper](#llm-wrapper-corellmpy)
   - [RAG Module](#rag-module-coreragpy)
   - [AlphaEval Backtesting Engine](#alphaeval-backtesting-engine)
6. [Schemas / Data Models](#schemas--data-models)
7. [Data & Knowledge Base](#data--knowledge-base)
8. [Scripts (Data Fetching)](#scripts-data-fetching)
9. [Entry Point](#entry-point-mainpy)
10. [Configuration & Environment](#configuration--environment)
11. [End-to-End Flow](#end-to-end-flow)
12. [Technical Details](#technical-details)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                    │
│                   (workflow/graph.py)                    │
│                                                         │
│   ┌───────────┐    ┌─────────────┐    ┌──────────────┐  │
│   │ IdeaAgent │───▶│ FactorAgent │───▶│  EvalAgent   │  │
│   │ (Propose) │    │ (Implement) │    │ (Backtest &  │  │
│   └─────┬─────┘    └─────────────┘    │   Review)    │  │
│         │                             └──────┬───────┘  │
│         │          ┌──────────────┐           │          │
│         └──────────│ RAG Module   │◀──────────┘          │
│                    │ (Experience) │                      │
│                    └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

The system follows a **cyclic agent graph**:

1. **IdeaAgent** proposes a market hypothesis using RAG-retrieved context.
2. **FactorAgent** formalizes the hypothesis into math and implements it as Qlib expression code.
3. **EvalAgent** backtests the factor, scores it, and writes a reflexive review.
4. Based on the evaluation, the workflow either **accepts** the factor, **retries** with feedback, or **terminates** after max iterations.

---

## Directory Structure

```
.
├── main.py                          # CLI entry point
├── requirements.txt                 # pip dependencies
├── environment.yml                  # conda environment
├── .env.example                     # environment variable template
│
├── agents/
│   ├── idea_agent.py                # IdeaAgent — hypothesis generation
│   ├── factor_agent.py              # FactorAgent — formalization & implementation
│   └── eval_agent.py                # EvalAgent — backtesting & reflexive review
│
├── core/
│   ├── llm.py                       # LLM client factory (get_llm)
│   ├── rag.py                       # RAGModule — ChromaDB vector store
│   └── alphaeval/
│       ├── __init__.py              # Package init
│       ├── modeltester.py           # AlphaEval — single/multi-factor backtester
│       ├── combo.py                 # WeightCalculator — factor combination optimizer
│       └── noise_proc.py           # Noise injection processors for robustness
│
├── schemas/
│   └── messages.py                  # Pydantic models for structured LLM outputs
│
├── workflow/
│   ├── state.py                     # AlphaMinerState TypedDict definition
│   └── graph.py                     # LangGraph graph builder & routing logic
│
├── scripts/
│   ├── fetch_academic_papers.py     # Fetch arXiv papers (custom query)
│   ├── fetch_arxiv_qfin.py          # Fetch recent q-fin arXiv papers
│   ├── fetch_arxiv_with_pkg.py      # Fetch arXiv papers (using arxiv package)
│   └── fetch_market_metadata.py     # Generate market metadata document
│
└── data/
    └── rag_docs/
        ├── academic/
        │   ├── academic_papers_simulated.md
        │   └── recent_qfin_papers.md
        ├── alphas/
        │   ├── alpha_library.md
        │   └── worldquant_101_formulas.md
        └── market_meta/
            ├── current_market_metadata.md
            └── market_metadata.md
```

---

## Workflow & State Machine

### `workflow/state.py` — AlphaMinerState

Defines the **shared state** that flows through the entire LangGraph graph as a `TypedDict`. All agents read from and write to this state. Key 
fields likely include:

| Field | Type | Description |
|-------|------|-------------|
| `hypothesis` | `str` | Current market hypothesis text |
| `formalization` | `str` | Mathematical formalization of the hypothesis |
| `factor_code` | `str` | Qlib expression code implementing the factor |
| `metrics` | `Dict[str, float]` | Backtest performance metrics (IC, Sharpe, etc.) |
| `review` | `str` | Reflexive review feedback |
| `iteration` | `int` | Current iteration count |
| `max_iterations` | `int` | Maximum allowed iterations |
| `is_effective` | `bool` | Whether the factor passed evaluation |
| `experiences` | `List` | Accumulated past experiences for RAG |

### `workflow/graph.py` — Graph Builder & Routing

This is the **orchestration layer** built with **LangGraph**. It wires the three agents into a stateful, cyclic graph.

**Key functions:**

- **`build_workflow(rebuild_rag=False)`**: Constructs the full LangGraph `StateGraph`:
  - Adds nodes: `idea_agent`, `factor_agent`, `eval_agent`, `increment_iteration`
  - Adds conditional edges based on routing functions
  - Compiles and returns the runnable graph

- **`route_after_idea(state)`**: Decides what happens after IdeaAgent runs. Likely routes to FactorAgent, or ends if no viable hypothesis.

- **`route_after_factor(state)`**: Decides what happens after FactorAgent runs. Routes to EvalAgent on success, or back to IdeaAgent on failure.

- **`route_after_eval(state)`**: The critical routing decision:
  - If factor is **effective** → accept and end (or continue mining)
  - If factor is **not effective** and iterations remain → loop back to IdeaAgent with feedback
  - If **max iterations reached** → terminate

- **`increment_iteration(state)`**: Simple utility node that bumps the iteration counter.

**Graph topology:**
```
START → IdeaAgent → FactorAgent → EvalAgent → increment_iteration
                                                      │
                                          ┌───────────┴───────────┐
                                          ▼                       ▼
                                    (loop back to           (END — accept
                                     IdeaAgent)             or terminate)
```

---

## Agents

### IdeaAgent

**File:** `agents/idea_agent.py`

**Role:** Proposes market hypotheses — the creative "idea generation" step.

**How it works:**

1. **RAG Retrieval**: Queries the `RAGModule` to fetch relevant context from:
   - Qlib documentation
   - Alpha/Academic library (WorldQuant 101, academic papers)
   - Market metadata (current regime, sector info)
   - Past experiences (what worked/failed before)

2. **LLM Reasoning**: Sends the retrieved context plus any feedback from previous iterations to a structured LLM call.

3. **Output**: Returns a `HypothesisOutput` containing the market hypothesis text, which is written into `AlphaMinerState`.

**Key design:** Uses RAG to ground the LLM's creativity in real financial knowledge and past experimental results, preventing hallucinated or 
redundant hypotheses.

---

### FactorAgent

**File:** `agents/factor_agent.py`

**Role:** Translates a natural-language hypothesis into executable Qlib factor code. This is a **two-stage** process:

**Stage 1 — Formalization:**
- Takes the hypothesis from IdeaAgent
- Uses LLM to convert it into a mathematical expression / formula
- Outputs a `FormalizationOutput`

**Stage 2 — Implementation:**
- Takes the mathematical formalization
- Uses LLM to generate a valid **Qlib expression** string
- Validates the expression via `_validate_qlib_expression()` — a static method that checks syntax and operator validity
- Outputs an `ImplementationOutput` with the final code

**Qlib Expression Validation:**
The `_validate_qlib_expression()` method ensures the generated expression uses only valid Qlib operators (e.g., `Ref`, `Mean`, `Std`, `Corr`, 
`Rank`, `Delta`, `$close`, `$volume`, etc.). This is critical because invalid expressions would crash the backtester.

---

### EvalAgent

**File:** `agents/eval_agent.py`

**Role:** Evaluates the generated factor through backtesting and reflexive review.

**How it works:**

1. **AlphaEval Backtest** (`_execute_alphaeval_backtest`):
   - Takes the factor code from FactorAgent
   - Runs it through the `AlphaEval` backtesting engine (see below)
   - Returns quantitative metrics: IC (Information Coefficient), Sharpe ratio, PnL, etc.

2. **Reflexive Review**:
   - An LLM-based review that analyzes the backtest results
   - Determines if the factor is "effective" (meets quality thresholds)
   - Generates feedback explaining why the factor succeeded or failed
   - Outputs a `ReflexiveReviewOutput`

3. **Experience Storage**:
   - Writes the (hypothesis, code, metrics, effectiveness) tuple to the RAG module via `rag_module.add_experience()`
   - This creates a growing knowledge base of what has been tried

**Key design:** The reflexive review creates a feedback loop — failed factors generate specific improvement suggestions that IdeaAgent uses in the
next iteration.

---

## Core Modules

### LLM Wrapper (`core/llm.py`)

**Function:** `get_llm(temperature=0.7, model_name="claude-opus-4-6") -> BaseChatModel`

A factory function that returns a LangChain-compatible `BaseChatModel` instance. 

- Uses **Anthropic Claude** as the default model
- Configurable temperature for controlling creativity vs. determinism
- Returns a LangChain `BaseChatModel` so it integrates seamlessly with structured output parsing, chains, and agents
- API key and proxy/base_url are configured via environment variables (see `.env.example`)

---

### RAG Module (`core/rag.py`)

**Class:** `RAGModule`

A **Retrieval-Augmented Generation** module backed by **ChromaDB** (local vector database) and **OpenAI-compatible embeddings**.

**Initialization:**
- `db_dir`: Path to ChromaDB persistent storage (default: `data/chroma_db`)
- `docs_dir`: Path to markdown knowledge documents (default: `data/rag_docs`)
- `rebuild`: If `True`, re-indexes all documents from scratch
- Uses `ClaudeCode_KEY` environment variable for the embedding API

**Key methods:**

| Method | Description |
|--------|-------------|
| `_chunk_text(text, chunk_size, overlap)` | Splits documents into overlapping chunks for embedding |
| `_init_knowledge_base()` | Reads all `.md` files from `docs_dir`, chunks them, embeds them, and stores in ChromaDB |
| `retrieve(query, n_results)` | Semantic search — returns the top-N most relevant text chunks for a query |
| `_safe_query(collection, query, n_results)` | Wrapper around ChromaDB query with error handling |
| `add_experience(hypothesis, code, metrics, is_effective)` | Stores a completed experiment as a new document in the vector store for future 
retrieval |

**Knowledge sources indexed:**
- Academic papers (arXiv q-fin, simulated)
- Alpha formulas (WorldQuant 101, custom alpha library)
- Market metadata (regime, sector, macro indicators)
- Past experiences (dynamically added during runtime)

---

### AlphaEval Backtesting Engine

Located in `core/alphaeval/`, this is the quantitative evaluation backbone.

#### `core/alphaeval/modeltester.py` — AlphaEval

**Class:** `AlphaEval`

The main backtesting class that evaluates factor expressions against historical market data using **Qlib**.

**Constructor parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `factor_expressions` | — | List of Qlib expression strings to evaluate |
| `weights` | `None` | Optional weights for multi-factor combination |
| `train_start_date` | `"2010-01-01"` | Training period start |
| `train_end_date` | `"2016-12-31"` | Training period end |
| `test_start_date` | `"2017-01-01"` | Test period start |
| `test_end_date` | `"2020-10-31"` | Test period end |
| `instruments` | `None` | Stock universe (defaults to CSI300 or similar) |
| `daily_normalize` | `True` | Whether to cross-sectionally normalize factors daily |

**Key methods:**

- **`fetch_data()`**: Pulls factor values and forward returns from Qlib's data engine
- **`calculate_pnl()`**: Computes the profit-and-loss curve of a long-short portfolio based on factor ranks
- **`calculate_covariance_entropy()`**: Measures factor diversity/redundancy using covariance matrix entropy
- **`LLM_scores()`**: Uses an LLM to qualitatively score the factor (novelty, interpretability, etc.)
- **`run()`**: Full evaluation pipeline — fetch data, compute metrics, generate summary
- **`run_single_factor()`**: Simplified pipeline for evaluating a single factor
- **`summary()`**: Returns a dictionary of all computed metrics

**Helper:** `zscore(df)` — Cross-sectional z-score normalization function.

#### `core/alphaeval/combo.py` — WeightCalculator

**Class:** `WeightCalculator`

Optimizes the linear combination weights for a multi-factor portfolio.

**How it works:**
1. Fetches factor values and returns via Qlib
2. Cross-sectionally normalizes (z-score) each factor
3. Optimizes weights to **maximize mean IC** (Information Coefficient) using `scipy.optimize`
4. The objective function normalizes weights to sum to 1 (in absolute value)

**Key methods:**
- `fetch_data()`: Retrieves and normalizes factor data
- `compute_mean_ic(X, y, weights)`: Computes the mean IC for a given weight vector
- `train_optimal_weights(X, y)`: Runs the optimization (minimizes negative IC)
- `fit()`: End-to-end pipeline

#### `core/alphaeval/noise_proc.py` — Noise Processors

**Classes:** `NoiseInjection`, `NoiseInjection_t`

Qlib-compatible `Processor` subclasses that inject noise into factor values for **robustness testing**.

- `NoiseInjection`: Adds Gaussian noise with configurable variance
- `NoiseInjection_t`: Adds Student's t-distributed noise (heavier tails) with configurable variance and degrees of freedom

**Purpose:** If a factor's performance degrades significantly under noise injection, it's likely overfitted.

---

## Schemas / Data Models

### `schemas/messages.py`

Defines **Pydantic `BaseModel`** classes used for **structured LLM output parsing**. LangChain uses these to force the LLM to return JSON 
conforming to the schema.

| Model | Used By | Fields (likely) |
|-------|---------|-----------------|
| `HypothesisOutput` | IdeaAgent | `hypothesis`, `reasoning`, `confidence` |
| `FormalizationOutput` | FactorAgent (Stage 1) | `mathematical_expression`, `variables`, `explanation` |
| `ImplementationOutput` | FactorAgent (Stage 2) | `qlib_expression`, `description` |
| `ReflexiveReviewOutput` | EvalAgent | `is_effective`, `score`, `feedback`, `suggestions` |

These schemas ensure deterministic, parseable outputs from every LLM call.

---

## Data & Knowledge Base

### `data/rag_docs/`

Static knowledge documents that are indexed into ChromaDB at startup.

| File | Content |
|------|---------|
| `academic/academic_papers_simulated.md` | Simulated summaries of academic finance papers |
| `academic/recent_qfin_papers.md` | Recent quantitative finance papers from arXiv |
| `alphas/alpha_library.md` | Curated library of known alpha factors with descriptions |
| `alphas/worldquant_101_formulas.md` | The 101 formulaic alphas from the WorldQuant paper |
| `market_meta/current_market_metadata.md` | Current market regime and conditions |
| `market_meta/market_metadata.md` | General market structure metadata |

These documents give the IdeaAgent grounded context for generating hypotheses.

---

## Scripts (Data Fetching)

Utility scripts to populate the `data/rag_docs/` knowledge base.

| Script | Purpose |
|--------|---------|
| `scripts/fetch_academic_papers.py` | Fetches arXiv papers by custom query string, saves as markdown |
| `scripts/fetch_arxiv_qfin.py` | Fetches recent papers from arXiv `q-fin` category |
| `scripts/fetch_arxiv_with_pkg.py` | Alternative fetcher using the `arxiv` Python package |
| `scripts/fetch_market_metadata.py` | Generates market metadata document (likely using an LLM or data API) |

**Usage:** Run these scripts periodically to keep the knowledge base fresh.

---

## Entry Point (`main.py`)

The CLI entry point that ties everything together.

**Key functions:**

- **`setup_logging(verbose)`**: Configures Python logging (debug vs. info level)
- **`print_summary(final_state)`**: Pretty-prints the final results after the workflow completes
- **`main()`**: 
  1. Parses CLI arguments
  2. Calls `build_workflow()` to construct the LangGraph
  3. Initializes the starting `AlphaMinerState`
  4. Invokes the graph and collects the final state
  5. Prints the summary

---

## Configuration & Environment

### `.env.example`

Template for required environment variables:

| Variable | Purpose |
|----------|---------|
| `ClaudeCode_KEY` | API key for Anthropic Claude (used for LLM calls and embeddings) |
| *(likely others)* | Proxy base URL, Qlib data path, etc. |

### `environment.yml`

Conda environment specification with all dependencies.

### `requirements.txt`

Pip dependencies — likely includes:
- `langchain`, `langgraph` — agent orchestration
- `anthropic` — Claude API client
- `chromadb` — vector database
- `qlib` — quantitative investment platform
- `pandas`, `numpy`, `scipy` — data processing
- `pydantic` — data validation

---

## End-to-End Flow

```
1. User runs: python main.py
                    │
2. build_workflow() constructs LangGraph
                    │
3. RAGModule initializes, indexes knowledge docs into ChromaDB
                    │
4. Graph starts at IdeaAgent
   ├── RAG retrieves relevant context (papers, alphas, past experiences)
   ├── LLM generates a market hypothesis
   └── State updated with hypothesis
                    │
5. FactorAgent receives hypothesis
   ├── Stage 1: LLM formalizes hypothesis → math expression
   ├── Stage 2: LLM implements math → Qlib expression code
   ├── Validation: _validate_qlib_expression() checks syntax
   └── State updated with factor code
                    │
6. EvalAgent receives factor code
   ├── AlphaEval runs backtest on historical data via Qlib
   ├── Metrics computed: IC, Sharpe, PnL, covariance entropy
   ├── LLM reflexive review analyzes results
   ├── Experience stored in RAG for future iterations
   └── State updated with metrics + review
                    │
7. Routing decision (route_after_eval):
   ├── Factor effective? → Accept, END
   ├── Iterations remaining? → Loop back to step 4 with feedback
   └── Max iterations? → Terminate, END
                    │
8. print_summary() displays final results
```

---

## Technical Details

### Why LangGraph?

LangGraph provides a **stateful, cyclic graph** execution model — unlike simple LangChain chains which are linear. This is essential because:
- The workflow has **conditional branching** (accept/retry/terminate)
- The workflow has **cycles** (eval → idea → factor → eval → ...)
- State must be **persisted and mutated** across iterations

### Why Qlib?

Microsoft's Qlib provides:
- A standardized **expression engine** for defining factors (e.g., `Ref($close, 5) / $close - 1`)
- Built-in **data infrastructure** for Chinese A-share and US equity markets
- Efficient **cross-sectional operations** needed for factor evaluation

### Why ChromaDB for RAG?

- **Local-first**: No external vector DB service needed
- **Persistent**: Survives restarts without re-indexing
- **Lightweight**: Suitable for the moderate-sized knowledge base (~6 documents)

### Reflexive Review Loop

The reflexive review is the key innovation — it creates a **self-improving** system:
1. Failed factors generate specific feedback ("IC too low because momentum signal is too noisy")
2. This feedback is stored in RAG as "experience"
3. In the next iteration, IdeaAgent retrieves this experience
4. The new hypothesis explicitly avoids past mistakes

This mimics how a human quant researcher iterates on ideas.

### Noise Robustness Testing

The `noise_proc.py` processors implement a form of **factor robustness validation**:
- Gaussian noise tests stability under normal perturbations
- Student's t noise tests stability under fat-tailed perturbations
- A robust factor should maintain its IC even with injected noise

---

## Quick Start

```bash
# 1. Clone and setup environment
cp .env.example .env
# Edit .env with your API keys

# 2. Install dependencies
pip install -r requirements.txt
# or
conda env create -f environment.yml

# 3. (Optional) Fetch fresh knowledge base data
python scripts/fetch_arxiv_qfin.py
python scripts/fetch_market_metadata.py

# 4. Run the alpha mining workflow
python main.py
```
=======
# AlphaMiner — 项目技术说明书 (Project Instruction Manual)

> 一个完全 "vibe-coded" 的自主 Alpha 因子挖掘框架，基于 **LangGraph**、**Qlib** 和 **LLM Agents** 
构建。系统自动提出市场假设、将其转化为量化因子、回测评估，并通过反思反馈循环迭代改进。

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Directory Structure](#2-directory-structure)
3. [Workflow & State Machine](#3-workflow--state-machine)
4. [Agents](#4-agents)
   - 4.1 [IdeaAgent](#41-ideaagent-agentsidea_agentpy)
   - 4.2 [FactorAgent](#42-factoragent-agentsfactor_agentpy)
   - 4.3 [EvalAgent](#43-evalagent-agentseval_agentpy)
5. [Core Modules](#5-core-modules)
   - 5.1 [LLM Wrapper](#51-llm-wrapper-corellmpy)
   - 5.2 [RAG Module](#52-rag-module-coreragpy)
   - 5.3 [AlphaEval Backtesting Engine](#53-alphaeval-backtesting-engine-corealphaeval)
6. [Schemas / Data Models](#6-schemas--data-models-schemasmessagespy)
7. [Data & Knowledge Base](#7-data--knowledge-base-datarag_docs)
8. [Scripts (Data Fetching)](#8-scripts-data-fetching)
9. [Entry Point](#9-entry-point-mainpy)
10. [Configuration & Environment](#10-configuration--environment)
11. [End-to-End Flow](#11-end-to-end-flow)
12. [Technical Deep-Dive](#12-technical-deep-dive)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      LangGraph StateGraph                        │
│                      (workflow/graph.py)                          │
│                                                                  │
│  ┌────────────┐     ┌──────────────┐     ┌───────────────────┐   │
│  │ IdeaAgent  │────▶│ FactorAgent  │────▶│    EvalAgent      │   │
│  │ (假设生成)  │     │ (公式化+实现) │     │ (回测+反思评审)    │   │
│  └─────┬──────┘     └──────────────┘     └────────┬──────────┘   │
│        ▲                                          │              │
│        │         ┌──────────────────┐              │              │
│        │         │   increment()   │◀─────────────┘              │
│        └─────────│  (迭代计数器+1)  │   (if iteration < max)     │
│                  └──────────────────┘                             │
│                                                                  │
│  Shared State: AlphaMinerState (workflow/state.py)               │
│  Knowledge:    RAGModule ←→ ChromaDB (core/rag.py)              │
│  LLM:         Claude via OpenAI-compatible proxy (core/llm.py)  │
└──────────────────────────────────────────────────────────────────┘
```

**核心循环：**
1. **IdeaAgent** — 利用 RAG 检索上下文，提出市场假设
2. **FactorAgent** — 将假设形式化为数学公式，再实现为 Qlib 表达式
3. **EvalAgent** — 用 AlphaEval 回测因子，LLM 反思评审，将经验写入 RAG
4. **路由决策** — 若未达最大迭代次数，带着改进建议回到 IdeaAgent

---

## 2. Directory Structure

```
.
├── main.py                              # CLI 入口
├── .env.example                         # 环境变量模板
├── requirements.txt                     # pip 依赖
├── environment.yml                      # conda 环境定义
│
├── agents/                              # 三个核心 Agent
│   ├── idea_agent.py                    #   IdeaAgent — 假设生成
│   ├── factor_agent.py                  #   FactorAgent — 形式化 + 代码实现
│   └── eval_agent.py                    #   EvalAgent — 回测 + 反思评审
│
├── core/                                # 核心基础设施
│   ├── llm.py                           #   LLM 客户端工厂
│   ├── rag.py                           #   RAG 模块 (ChromaDB + Embedding)
│   └── alphaeval/                       #   因子评估引擎
│       ├── __init__.py
│       ├── modeltester.py               #     AlphaEval 主类
│       ├── combo.py                     #     WeightCalculator 权重优化
│       └── noise_proc.py               #     噪声注入处理器
│
├── schemas/
│   └── messages.py                      # Pydantic 结构化输出模型
│
├── workflow/
│   ├── state.py                         # AlphaMinerState 状态定义
│   └── graph.py                         # LangGraph 图构建 & 路由逻辑
│
├── scripts/                             # 数据获取脚本
│   ├── fetch_academic_papers.py         #   arXiv 论文 (自定义查询)
│   ├── fetch_arxiv_qfin.py              #   arXiv q-fin 分类论文
│   ├── fetch_arxiv_with_pkg.py          #   arXiv 论文 (arxiv 包)
│   └── fetch_market_metadata.py         #   市场元数据生成 (AKShare)
│
└── data/
    ├── chroma_db/                       # ChromaDB 持久化存储 (运行时生成)
    └── rag_docs/                        # 知识库文档
        ├── academic/
        │   ├── academic_papers_simulated.md
        │   ├── recent_qfin_papers.md
        │   └── arxiv_recent/            # 脚本抓取的论文 (运行时生成)
        ├── alphas/
        │   ├── alpha_library.md         # Alpha158/Alpha360 因子库
        │   └── worldquant_101_formulas.md # WorldQuant 101 + GTJA 191
        └── market_meta/
            ├── market_metadata.md       # Qlib 数据格式说明
            └── current_market_metadata.md # 当前市场元数据
```

---

## 3. Workflow & State Machine

### 3.1 `workflow/state.py` — AlphaMinerState

使用 Python `TypedDict` 定义的共享状态，所有 Agent 通过读写此状态进行通信。`total=False` 表示所有字段均为可选。

```python
class AlphaMinerState(TypedDict, total=False):
    # 控制
    iteration: int                          # 当前迭代轮次
    max_iterations: int                     # 最大迭代次数

    # 上下文
    rag_context: str                        # RAG 检索到的上下文文本

    # IdeaAgent 输出
    hypothesis_name: str                    # 假设的简短名称
    hypothesis_description: str             # 假设的详细描述
    rationale: str                          # 金融逻辑理由

    # FactorAgent 输出
    math_formula: str                       # 数学公式
    variables_defined: Dict[str, str]       # 变量定义字典
    code_expression: str                    # Qlib 表达式代码
    is_valid_syntax: bool                   # 语法是否有效

    # EvalAgent 输出
    backtest_metrics: Dict[str, float]      # 回测指标 (IC, RankIC, RRE, PFS, ...)
    review_summary: str                     # 反思评审摘要
    is_effective: bool                      # 因子是否有效 (IC>0.02 且 RankIC>0.02)
    suggested_improvements: str             # 改进建议
    is_simulated: bool                      # 是否使用了模拟指标 (无 Qlib 数据时)

    # 错误 & 消息
    error: Optional[str]                    # 错误信息
    messages: Annotated[List[str], operator.add]  # 累积消息日志 (使用 operator.add 合并)
```

**关键设计：** `messages` 字段使用 `Annotated[List[str], operator.add]`，这是 LangGraph 的 **reducer** 机制 — 每个节点返回的 messages 列表会被 
**追加** 而非覆盖，形成完整的执行日志。

### 3.2 `workflow/graph.py` — 图构建与路由

使用 LangGraph 的 `StateGraph` 构建有状态的循环图。

**节点 (Nodes):**

| 节点名 | 实现 | 功能 |
|--------|------|------|
| `idea_agent` | `IdeaAgent.__call__` | 生成市场假设 |
| `factor_agent` | `FactorAgent.__call__` | 形式化 + 实现因子 |
| `eval_agent` | `EvalAgent.__call__` | 回测 + 反思评审 |
| `increment` | `increment_iteration()` | 迭代计数器 +1，清除瞬态错误 |

**路由函数 (Routing):**

```python
def route_after_idea(state) -> str:
    # 有错误 → 结束; 否则 → factor_agent
    if state.get("error"): return "end"
    return "factor_agent"

def route_after_factor(state) -> str:
    # 有错误 → 结束; 语法无效时仍继续到 eval (带警告)
    if state.get("error"): return "end"
    return "eval_agent"

def route_after_eval(state) -> str:
    # 当前迭代 < 最大迭代 → 继续循环; 否则 → 结束
    if state["iteration"] < state["max_iterations"]: return "increment"
    return "end"
```

**`increment_iteration(state)`:**
```python
def increment_iteration(state):
    return {
        "iteration": state.get("iteration", 1) + 1,
        "error": None,              # 清除上一轮错误
        "is_valid_syntax": True,    # 重置语法标志
    }
```

**完整图拓扑：**
```
         ┌──────────────────────────────────────────────┐
         │                                              │
         ▼                                              │
    IdeaAgent ──[error?]──▶ END                         │
         │                                              │
         ▼                                              │
    FactorAgent ──[error?]──▶ END                       │
         │                                              │
         ▼                                              │
    EvalAgent ──[iteration < max?]──▶ increment ────────┘
         │
         ▼
        END
```

---

## 4. Agents

### 4.1 IdeaAgent (`agents/idea_agent.py`)

**职责：** 提出新的市场假设（Alpha 因子的创意来源）。

**初始化：**
- 接收一个 `RAGModule` 实例
- 创建 `temperature=0.7` 的 LLM（鼓励创造性）
- 使用 `llm.with_structured_output(HypothesisOutput)` 确保输出结构化

**执行流程 (`__call__`)：**

```
1. 读取状态
   ├── iteration: 当前迭代轮次
   ├── suggested_improvements: 上一轮的改进建议
   └── hypothesis_name: 上一轮的假设名称

2. 构建 RAG 查询
   ├── 基础查询: "Generate a novel quantitative trading alpha factor hypothesis..."
   └── 若 iteration > 1 且有改进建议: 追加 "Previous attempt had these suggestions: ..."

3. RAG 检索 (self.rag.retrieve(query))
   └── 返回知识库 + 历史经验的相关文本片段

4. LLM 推理
   ├── System Prompt: "You are an elite quantitative researcher..."
   │   └── 包含 RAG 上下文 + 上一轮反馈
   ├── User Prompt: "Propose a new factor hypothesis for iteration {iteration}..."
   └── 输出: HypothesisOutput (结构化)

5. 写入状态
   ├── rag_context: RAG 检索到的上下文
   ├── hypothesis_name: 假设名称 (如 "Volume-Weighted Momentum Reversal")
   ├── hypothesis_description: 详细描述
   ├── rationale: 金融逻辑理由
   └── messages: 日志消息
```

**关键设计：**
- 第一轮迭代使用纯 RAG 上下文生成假设
- 后续迭代会将 `suggested_improvements` 注入 prompt，实现 **反思改进**
- `temperature=0.7` 平衡创造性与合理性

---

### 4.2 FactorAgent (`agents/factor_agent.py`)

**职责：** 将自然语言假设翻译为可执行的 Qlib 因子表达式。分为 **形式化** 和 **实现** 两个阶段。

**初始化：**
- 创建 `temperature=0.2` 的 LLM（低温度确保代码精确性）
- 两个结构化输出 LLM：
  - `self.formalization_llm` → `FormalizationOutput`
  - `self.implementation_llm` → `ImplementationOutput`

**类常量 — 已知 Qlib 算子和字段：**
```python
QLIB_OPERATORS = {
    "Ref", "Mean", "Std", "Rank", "Max", "Min", "Sum", "Abs",
    "Log", "Sign", "Power", "Corr", "Cov", "Delta", "Delay",
    "Ts_Rank", "Ts_Min", "Ts_Max", "Ts_ArgMax", "Ts_ArgMin",
    "WMA", "EMA", "If", "Greater", "Less",
}
QLIB_FIELDS = {"$close", "$open", "$high", "$low", "$volume", "$vwap", "$turn", "$factor"}
```

**执行流程 (`__call__`)：**

```
1. 读取状态
   ├── hypothesis_description
   └── rationale

2. Stage 1: 形式化 (Formalization)
   ├── Prompt: "Convert the given financial hypothesis into a strict mathematical formula"
   ├── 输入: hypothesis + rationale
   └── 输出: FormalizationOutput
       ├── math_formula: "σ(R_t, 20) / μ(V_t, 20)"
       └── variables_defined: {"R_t": "daily return", "V_t": "daily volume", ...}

3. Stage 2: 实现 (Implementation)
   ├── Prompt: "Convert the mathematical formula into a syntactically correct Qlib expression"
   ├── 输入: math_formula + variables_defined
   └── 输出: ImplementationOutput
       ├── code_expression: "Std($close/Ref($close,1)-1, 20) / Mean($volume, 20)"
       └── is_valid_syntax: True/False (LLM 自评)

4. 独立语法验证 (_validate_qlib_expression)
   ├── 检查表达式非空
   ├── 检查括号平衡
   └── 检查包含至少一个 $ 字段引用

5. 最终有效性 = LLM自评 AND 独立验证

6. 写入状态
   ├── math_formula, variables_defined, code_expression
   ├── is_valid_syntax: 最终有效性
   └── messages: 日志
```

**`_validate_qlib_expression(expr)` 静态方法：**
```python
@staticmethod
def _validate_qlib_expression(expr: str) -> tuple[bool, str]:
    # 1. 检查非空
    # 2. 检查括号平衡 (遍历字符，维护深度计数器)
    # 3. 检查包含 '$' (至少引用一个 Qlib 字段)
    # 返回 (is_valid, message)
```

> **注意：** 当前验证是轻量级的 — 只检查括号和字段引用，不做完整的 Qlib 表达式解析。即使语法无效，工作流仍会继续到 EvalAgent（带警告日志）。

---

### 4.3 EvalAgent (`agents/eval_agent.py`)

**职责：** 评估因子的有效性，包括回测、反思评审、经验存储。

**初始化：**
- 接收 `RAGModule` 实例
- 创建 `temperature=0.4` 的 LLM（中等温度，平衡分析深度与一致性）
- `self.review_llm` → `ReflexiveReviewOutput`

**执行流程 (`__call__`)：**

```
1. 读取状态
   ├── code_expression: Qlib 表达式
   └── hypothesis_description: 假设描述

2. 回测模块 (_execute_alphaeval_backtest)
   ├── 尝试: 使用 AlphaEval 真实回测
   │   ├── 创建 AlphaEval(factor_expressions=[code], weights=[1.0], ...)
   │   ├── 调用 evaluator.run()
   │   └── 返回: {ic, rankic, rre, pfs1, pfs2, diversity, llm_score}
   │
   └── 失败回退: 生成模拟指标 (deterministic seed based on code hash)
       ├── ic: uniform(-0.05, 0.15)
       ├── rankic: uniform(-0.05, 0.15)
       ├── rre, pfs1, pfs2, diversity: uniform(0, 1)
       ├── llm_score: uniform(50, 100)
       └── _simulated: True

3. 反思评审模块 (Reflexive Review)
   ├── Prompt: "Analyze the evaluation metrics against the original hypothesis"
   ├── 输入: hypothesis + code + metrics
   └── 输出: ReflexiveReviewOutput
       ├── review_summary: 分析摘要
       ├── is_effective: IC > 0.02 AND Rank IC > 0.02
       └── suggested_improvements: 具体改进建议

4. 经验存储 (rag.add_experience)
   └── 将 (hypothesis, code, metrics, is_effective, review) 写入 ChromaDB

5. 写入状态
   ├── backtest_metrics, review_summary, is_effective
   ├── is_simulated: 是否使用了模拟指标
   ├── suggested_improvements: 改进建议 (供下一轮 IdeaAgent 使用)
   └── messages: 日志
```

**模拟回测的确定性：**
```python
seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
rng = random.Random(seed)
```
相同的表达式总是产生相同的模拟指标，确保可复现性。

---

## 5. Core Modules

### 5.1 LLM Wrapper (`core/llm.py`)

```python
def get_llm(temperature=0.7, model_name="claude-opus-4-6") -> BaseChatModel:
```

**实现细节：**
- 使用 `langchain_openai.ChatOpenAI` 类（因为代理 API `gptsapi.net` 兼容 OpenAI 协议）
- API Key: 从环境变量 `ClaudeCode_KEY` 读取
- Base URL: `https://api.gptsapi.net/v1`（OpenAI 兼容的聚合代理）
- `max_retries=3`：自动重试失败的 API 调用
- 默认模型: `claude-opus-4-6`

**各 Agent 使用的温度：**
| Agent | Temperature | 原因 |
|-------|-------------|------|
| IdeaAgent | 0.7 | 鼓励创造性假设 |
| FactorAgent | 0.2 | 确保数学/代码精确性 |
| EvalAgent | 0.4 | 平衡分析深度与一致性 |

---

### 5.2 RAG Module (`core/rag.py`)

**类：** `RAGModule`

基于 **ChromaDB** 的检索增强生成模块，使用 OpenAI 兼容的 embedding API。

**初始化参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `db_dir` | `"data/chroma_db"` | ChromaDB 持久化目录 |
| `docs_dir` | `"data/rag_docs"` | 知识文档目录 |
| `rebuild` | `False` | 是否强制重建知识库 |

**Embedding 配置：**
```python
self.embedding_fn = OpenAIEmbeddingFunction(
    api_key=os.getenv("ClaudeCode_KEY"),
    model_name="text-embedding-3-small",
    api_base="https://api.gptsapi.net/v1"
)
```

**两个 ChromaDB Collection：**
| Collection | 用途 |
|------------|------|
| `knowledge_base` | 静态知识（论文、因子库、市场元数据） |
| `experiences` | 动态经验（每次回测结果） |

**`_chunk_text(text, chunk_size=1500, overlap=200)`：**
- 按 `\n\n`（段落）分割文本
- 每个 chunk 不超过 `chunk_size` 字符
- 超大段落直接作为独立 chunk
- **注意：** 当前实现没有真正的 overlap（参数 `overlap` 未使用）

**`_init_knowledge_base()`：**
```
1. 若 rebuild=True 且已有数据 → 删除并重建 collection
2. 若已有数据 → 跳过（幂等）
3. 递归扫描 docs_dir 下所有 .md/.rst/.txt 文件
4. 对每个文件: 读取 → chunk → 生成 ID
5. 批量写入 ChromaDB (batch_size=100)
```

**`retrieve(query, n_results=3)`：**
```python
def retrieve(self, query: str, n_results: int = 3) -> str:
    # 1. 从 knowledge_base 检索 top-N
    # 2. 从 experiences 检索 top-N
    # 3. 拼接为格式化文本:
    #    === KNOWLEDGE BASE ===
    #    - chunk1
    #    - chunk2
    #    === PAST EXPERIENCES ===
    #    - exp1
    #    - exp2
```

**`add_experience(hypothesis, code, metrics, is_effective, review)`：**
```python
# 创建富文本文档:
document = f"Hypothesis: {hypothesis}\nCode: {code}\nMetrics: {json.dumps(metrics)}\n..."
# 元数据:
metadata = {"is_effective": bool, "ic": float, "rank_ic": float}
# 写入 experiences collection
self.experiences_col.add(documents=[document], metadatas=[metadata], ids=[exp_id])
```

---

### 5.3 AlphaEval Backtesting Engine (`core/alphaeval/`)

#### 5.3.1 `modeltester.py` — AlphaEval 主类

**构造函数参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `factor_expressions` | (必填) | Qlib 表达式列表 |
| `weights` | `None` | 因子权重（None 时自动通过 WeightCalculator 优化） |
| `train_start_date` | `"2010-01-01"` | 训练期起始 |
| `train_end_date` | `"2016-12-31"` | 训练期结束 |
| `test_start_date` | `"2017-01-01"` | 测试期起始 |
| `test_end_date` | `"2020-10-31"` | 测试期结束 |
| `instruments` | `None` | 股票池（默认 CSI300） |
| `daily_normalize` | `True` | 是否每日截面 z-score 标准化 |

**标签定义：**
```python
self.label_expr = "Ref($close, -1)/$close - 1"  # 次日收益率
```

**`fetch_data()` — 数据获取：**
```
1. 获取因子数据 (factor_data): D.features(instruments, factor_expressions, test_period)
2. 获取基准收盘价 (SH000300): 用于计算噪声方差
   ├── 归一化到 [0,1]
   └── 计算方差 variance
3. 生成噪声因子数据1 (noise_factor_data1): 高斯噪声注入
4. 生成噪声因子数据2 (noise_factor_data2): t 分布噪声注入 (dof=3)
5. 获取标签数据 (label_data): 次日收益率
6. 若 daily_normalize: 对所有因子数据做截面 z-score
7. 计算组合因子: alphacombo = factor_data.dot(weights)
8. 计算噪声组合: noisecombo1, noisecombo2
```

**`run()` — 核心评估指标：**

| 指标 | 计算方式 | 含义 |
|------|----------|------|
| `ic` | `Corr(factor, label)` 按日分组求均值 | 信息系数 — 因子与未来收益的线性相关性 |
| `rankic` | `Corr(Rank(factor), Rank(label))` 按日分组求均值 | 秩信息系数 — 抗异常值 |
| `rre` | `1 / (1 + KL_divergence)` 基于因子排名分布的日间变化 | 相对排名熵 — 衡量因子稳定性 |
| `pfs1` | `Corr(factor, noisy_factor_gaussian)` | 高斯噪声下的预测力稳定性 |
| `pfs2` | `Corr(factor, noisy_factor_t)` | t 分布噪声下的预测力稳定性 |
| `diversity` | 因子协方差矩阵的归一化特征值熵 | 多因子组合的多样性 |
| `llm_avg_score` | LLM 对每个因子的逻辑评分 (50-100) | 因子的金融逻辑合理性 |

**`calculate_pnl()` — PnL 计算：**
```
每日:
1. 按因子值排名，取 top 20% 做多，bottom 20% 做空
2. long_ret = 多头组平均收益
3. short_ret = -空头组平均收益
4. pnl = (long_ret + short_ret) / 2
5. 计算换手率 turnover = 换仓股票数 / 持仓股票数
6. 扣除交易成本: cost = turnover × 0.15%
7. net_pnl = pnl - cost
```

**`calculate_covariance_entropy()` — 多样性计算：**
```python
C = np.cov(factor_matrix, rowvar=False)       # 因子协方差矩阵
eigs = np.linalg.eigvalsh(C)                  # 特征值
p = eigs / eigs.sum()                         # 归一化为概率分布
diversity = -sum(p * log(p)) / log(n_factors) # 归一化熵 ∈ [0, 1]
```

**`LLM_scores()` — LLM 评分：**
```
1. 将所有因子表达式发送给 LLM
2. Prompt: "Score each factor from 50 to 100 based on financial logic rationality"
3. 要求返回纯 JSON 数组: [{factor, score, explanation}, ...]
4. 解析 JSON，提取分数和解释
5. 计算平均分 llm_avg_score
```

**`run_single_factor()` — 单因子评估：**
与 `run()` 类似，但逐个评估每个因子，返回每个因子的独立指标列表。

---

#### 5.3.2 `combo.py` — WeightCalculator

**职责：** 为多因子组合优化线性权重，最大化 IC。

**核心算法：**
```python
def train_optimal_weights(self, X, y, maxiter=1):
    def obj(u):
        w = u / np.sum(np.abs(u))          # 归一化权重 (L1 = 1)
        return -1 * self.compute_mean_ic(X, y, w)  # 最大化 IC = 最小化 -IC

    bounds = [(-1, 1)] * n_factors          # 每个权重在 [-1, 1]
    result = differential_evolution(obj, bounds, maxiter=1, popsize=20)
    return result.x / np.sum(np.abs(result.x))
```

- 使用 `scipy.optimize.differential_evolution`（差分进化算法）
- `maxiter=1`：仅运行一代（快速但粗糙）
- `popsize=20`：种群大小
- 权重通过 L1 归一化：`w = u / sum(|u|)`

**`compute_mean_ic(X, y, weights)`：**
```python
alpha = X.dot(weights)                      # 加权组合因子
ic_series = grouped_corr(alpha, label)      # 每日 IC
mean_ic = ic_series.dropna().mean()         # 平均 IC
```

**`fetch_data(start, end)`：**
- 从 Qlib 获取因子数据和标签
- 截面 z-score 标准化
- 处理 inf/nan

---

#### 5.3.3 `noise_proc.py` — 噪声注入处理器

继承 Qlib 的 `Processor` 基类，在数据管道中注入噪声。

**`NoiseInjection` — 高斯噪声：**
```python
class NoiseInjection(Processor):
    def __init__(self, var=0.001):
        self.sigma = np.sqrt(var)

    def __call__(self, df):
        noise = np.random.normal(0, self.sigma, size=df.shape)
        return df * (1.0 + noise)   # 乘性噪声: x' = x * (1 + ε)
```

**`NoiseInjection_t` — Student's t 分布噪声：**
```python
class NoiseInjection_t(Processor):
    def __init__(self, var=0.001, dof=3):
        self.sigma = np.sqrt(var)
        self.dof = dof

    def __call__(self, df):
        t_raw = np.random.standard_t(self.dof, size=df.shape)
        t_noise = t_raw * self.sigma * np.sqrt((dof - 2) / dof)  # 方差校正
        return df * (1.0 + t_noise)
```

**噪声方差来源：** 使用沪深300指数 (`SH000300`) 在训练期的归一化收盘价方差，模拟真实市场波动水平。

**用途：** 通过 Qlib 的 `inst_processors` 参数注入到数据管道中：
```python
provider.dataset(
    ...,
    inst_processors=[{
        "class": "core.alphaeval.noise_proc.NoiseInjection",
        "kwargs": {"var": variance}
    }]
)
```

---

## 6. Schemas / Data Models (`schemas/messages.py`)

使用 **Pydantic v2 `BaseModel`** 定义结构化 LLM 输出。LangChain 的 `with_structured_output()` 方法使用这些 schema 强制 LLM 返回符合格式的 JSON。

### `HypothesisOutput` (IdeaAgent 使用)
```python
class HypothesisOutput(BaseModel):
    hypothesis_name: str        # 简短名称，如 "Volume-Weighted Momentum Reversal"
    hypothesis_description: str # 详细描述
    rationale: str              # 金融逻辑理由
```

### `FormalizationOutput` (FactorAgent Stage 1 使用)
```python
class FormalizationOutput(BaseModel):
    math_formula: str                   # 数学公式，如 "σ(R_t, 20) / μ(V_t, 20)"
    variables_defined: Dict[str, str]   # 变量定义，如 {"R_t": "daily return", ...}
```

### `ImplementationOutput` (FactorAgent Stage 2 使用)
```python
class ImplementationOutput(BaseModel):
    code_expression: str    # Qlib 表达式，如 "Std($close/Ref($close,1)-1, 20)"
    is_valid_syntax: bool   # LLM 自评语法是否有效
```

### `ReflexiveReviewOutput` (EvalAgent 使用)
```python
class ReflexiveReviewOutput(BaseModel):
    review_summary: str          # 分析摘要，包含具体指标值
    is_effective: bool           # IC > 0.02 AND Rank IC > 0.02
    suggested_improvements: str  # 具体可操作的改进建议
```

---

## 7. Data & Knowledge Base (`data/rag_docs/`)

启动时被 RAGModule 索引到 ChromaDB 中的静态知识文档。

### 7.1 `alphas/alpha_library.md`
**内容：** Alpha158 和 Alpha360 因子库的完整说明。
- **Alpha360：** 过去 60 天的归一化价格/成交量序列（适合 LSTM/GRU 等时序模型）
  - 字段：`CLOSE{i}`, `OPEN{i}`, `HIGH{i}`, `LOW{i}`, `VWAP{i}`, `VOLUME{i}`
- **Alpha158：** 158 个统计/技术指标，滚动窗口 5/10/20/30/60 天
  - K-bar 特征：`KMID`, `KLEN`, `KMID2`, `KUP`, `KLOW`, `KSFT`
  - 滚动算子：`ROC`, `MA`, `STD`, `BETA`, `RSQR`, `RESI`, `MAX`, `MIN`, `QTLU`, `QTLD`, `RANK`, `RSV`, `IMAX`, `IMIN`, `IMXD`, `CORR`, `CORD`, 
`CNTP`, `CNTN`, `CNTD`, `SUMP`, `SUMN`, `SUMD`

### 7.2 `alphas/worldquant_101_formulas.md`
**内容：** WorldQuant Alpha 101 和 GTJA 191 的部分公式，已翻译为 Qlib 语法。
- Alpha 001-054 的 Qlib 表达式示例
- GTJA Alpha 001, 010 的 Qlib 表达式
- **Alpha Mining 指南：**
  1. 组合价格与成交量（`Corr`, `Cov`, 乘法）
  2. 使用 `Rank()` 做截面中性化
  3. 使用 `If()` 创建非对称响应

### 7.3 `market_meta/market_metadata.md`
**内容：** Qlib 数据格式的完整说明。
- 基础字段：`$open`, `$close`, `$high`, `$low`, `$volume`, `$vwap`
- 表达式语法：`Ref`, `Mean`, `Std`, `Slope`, `Rsquare`, `Resi`, `Max`, `Min`, `Quantile`, `Rank`, `IdxMax`, `IdxMin`, `Corr`, `Cov`, `Abs`, `Log`,
`Sign`
- 标签定义：`Ref($close, -2)/Ref($close, -1) - 1`

### 7.4 `market_meta/current_market_metadata.md`
**内容：** 当前市场元数据（由 `fetch_market_metadata.py` 生成）。
- A 股总数：5493
- 期货合约数：86
- 日线数据结构（中文列名）
- AKShare 列名到 Qlib 字段的映射

### 7.5 `academic/academic_papers_simulated.md`
**内容：** 5 篇经典量化金融论文的模拟摘要。
- Kakushadze "101 Formulaic Alphas" (2015)
- GTJA 191 Alpha Factors
- Gu, Kelly, Xiu "Machine Learning for Stock Prediction" (2020)
- "Deep Alpha: A New Paradigm for Factor Mining"
- O'Hara "Market Microstructure" (1995)

### 7.6 `academic/recent_qfin_papers.md`
**内容：** 2025-2026 年量化金融前沿论文的综合摘要。
- LLM 用于 Alpha 挖掘
- 订单簿不平衡与 Transformer
- 因子评估的鲁棒性（RRE, Rank IC, PFS）
- 截面动量 vs 时序动量
- 非线性特征交互与正交化

---

## 8. Scripts (Data Fetching)

### 8.1 `scripts/fetch_academic_papers.py`
**功能：** 通过 arXiv API 按自定义查询获取论文摘要。
- 使用 `urllib` 直接调用 arXiv Atom API
- 预设查询：`"quantitative finance alpha factor"`, `"machine learning stock return prediction"`, 等
- 每个查询获取 20 篇，保存为 markdown
- 输出目录：`data/rag_docs/academic/`

### 8.2 `scripts/fetch_arxiv_qfin.py`
**功能：** 获取 arXiv q-fin 分类的最新论文。
- 查询：`cat:q-fin.TR OR cat:q-fin.PM OR cat:q-fin.ST OR cat:q-fin.CP`
- 获取 100 篇最新论文
- 添加 2 秒延迟和 User-Agent 避免 429 错误
- 输出目录：`data/rag_docs/academic/arxiv_recent/`

### 8.3 `scripts/fetch_arxiv_with_pkg.py`
**功能：** 使用 `arxiv` Python 包获取论文（更简洁的 API）。
- 查询：`cat:q-fin.PM OR cat:q-fin.ST OR cat:q-fin.TR`
- 获取 50 篇，按提交日期降序
- 输出目录：`data/rag_docs/academic/arxiv_recent/`

### 8.4 `scripts/fetch_market_metadata.py`
**功能：** 使用 **AKShare** 获取 A 股市场元数据。
- 获取 A 股代码列表 (`ak.stock_info_a_code_name()`)
- 获取样本日线数据 (`ak.stock_zh_a_hist()`)
- 获取期货合约信息 (`ak.futures_symbol_mark()`)
- 生成 markdown 格式的元数据文档
- 输出：`data/rag_docs/market_meta/current_market_metadata.md`

---

## 9. Entry Point (`main.py`)

### CLI 参数

```bash
python main.py [--iterations N] [--rebuild-rag] [--verbose]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--iterations` | `1` | 因子挖掘迭代次数 |
| `--rebuild-rag` | `False` | 强制重建 RAG 知识库 |
| `--verbose` | `False` | 启用 DEBUG 级别日志输出到 stderr |

### 执行流程

```python
def main():
    # 1. 解析参数
    # 2. 配置日志 (loguru → logs/aiminer_{time}.log, 10MB rotation)
    # 3. 检查 ClaudeCode_KEY 环境变量
    # 4. 构建工作流: app = build_workflow(rebuild_rag=args.rebuild_rag)
    # 5. 初始化状态:
    initial_state = {
        "iteration": 1,
        "max_iterations": args.iterations,
        "messages": ["[System] Starting Alpha Miner Workflow"]
    }
    # 6. 流式执行:
    for output in app.stream(initial_state):
        for node_name, state_update in output.items():
            final_state.update(state_update)
    # 7. 打印摘要
```

### `print_summary(final_state)`

格式化输出最终结果：
```
============================================================
  ALPHA MINER — EXECUTION SUMMARY
============================================================
  Iterations completed: 3 / 5
  Last Hypothesis: Volume-Weighted Momentum Reversal
  Description: ...
  Expression: Corr(Rank($close/Ref($close,1)), Rank($volume), 20)

  Backtest Metrics (REAL):
    information_coefficient: 0.045
    rank_ic: 0.038
    rre: 0.82
    ...

  Effective: ✓ YES
  Review: ...
  Improvements: ...
============================================================
```

---

## 10. Configuration & Environment

### `.env.example`
```bash
ClaudeCode_KEY="sk-your-api-key-here"
QLIB_DATA_PATH="~/.qlib/qlib_data/cn_data"
```

| 变量 | 用途 | 使用位置 |
|------|------|----------|
| `ClaudeCode_KEY` | API Key（用于 LLM 调用和 Embedding） | `core/llm.py`, `core/rag.py`, `core/alphaeval/modeltester.py` |
| `QLIB_DATA_PATH` | Qlib 数据目录路径 | `core/alphaeval/modeltester.py`, `core/alphaeval/combo.py` |

### `requirements.txt` / `environment.yml`

**核心依赖：**
| 包 | 版本 | 用途 |
|----|------|------|
| `langchain` | ≥0.1.0 | Agent 编排框架 |
| `langchain-openai` | — | OpenAI 兼容 LLM 客户端 |
| `langchain-anthropic` | — | Anthropic Claude 客户端 |
| `langchain-chroma` | — | ChromaDB 集成 |
| `langgraph` | — | 有状态循环图执行引擎 |
| `chromadb` | — | 本地向量数据库 |
| `pyqlib` | — | 量化投资平台 |
| `pandas` / `numpy` / `scipy` | — | 数据处理与优化 |
| `pydantic` | ≥2.0.0 | 数据验证与结构化输出 |
| `python-dotenv` | — | 环境变量加载 |
| `loguru` | — | 日志框架 |
| `tiktoken` | — | Token 计数 |

---

## 11. End-to-End Flow

```
用户执行: python main.py --iterations 3
    │
    ▼
[main.py] 加载 .env → 配置日志 → 检查 API Key
    │
    ▼
[workflow/graph.py] build_workflow()
    ├── 初始化 RAGModule → 扫描 data/rag_docs/ → 索引到 ChromaDB
    ├── 初始化 IdeaAgent, FactorAgent, EvalAgent
    └── 编译 StateGraph
    │
    ▼
=== 迭代 1 ===
    │
    ▼
[IdeaAgent]
    ├── RAG 检索: "Generate a novel alpha factor hypothesis..."
    │   └── 返回: WorldQuant 101 公式 + 学术论文摘要 + 市场元数据
    ├── LLM 生成假设: "Intraday Pressure Reversal"
    │   └── "当日内买卖压力 (High-Open vs Open-Low) 出现极端值时，次日倾向反转"
    └── 写入状态: hypothesis_name, hypothesis_description, rationale
    │
    ▼
[FactorAgent]
    ├── Stage 1 (形式化): "P_pressure = (H-O)/(O-L+ε), Signal = -Rank(MA(P_pressure, 5))"
    ├── Stage 2 (实现): "-1 * Rank(Mean(($high-$open)/($open-$low+1e-12), 5))"
    ├── 语法验证: ✓ 括号平衡, ✓ 包含 $ 字段
    └── 写入状态: math_formula, code_expression, is_valid_syntax=True
    │
    ▼
[EvalAgent]
    ├── AlphaEval 回测 (或模拟回退)
    │   └── {ic: 0.012, rankic: 0.018, rre: 0.75, ...}
    ├── LLM 反思评审:
    │   ├── is_effective: False (IC=0.012 < 0.02)
    │   └── suggested_improvements: "尝试更长的滚动窗口 (20天)，并加入成交量确认信号"
    ├── 经验存储 → ChromaDB experiences collection
    └── 写入状态: backtest_metrics, is_effective=False, suggested_improvements
    │
    ▼
[route_after_eval] iteration(1) < max_iterations(3) → increment
    │
    ▼
[increment] iteration: 1 → 2, error: None
    │
    ▼
=== 迭代 2 ===
    │
    ▼
[IdeaAgent]
    ├── RAG 检索: "...Previous attempt 'Intraday Pressure Reversal' had these suggestions: 尝试更长窗口..."
    │   └── 返回: 上一轮经验 + 相关知识
    ├── LLM 生成改进假设: "Volume-Confirmed Pressure Reversal"
    └── ...
    │
    ▼
... (继续迭代直到 iteration == max_iterations)
    │
    ▼
[main.py] print_summary(final_state)
```

---

## 12. Technical Deep-Dive

### 12.1 为什么用 LangGraph？

LangGraph 提供 **有状态的循环图** 执行模型，与简单的 LangChain 链（线性）不同：
- **条件分支：** `route_after_idea`, `route_after_factor`, `route_after_eval`
- **循环：** eval → increment → idea → factor → eval → ...
- **状态持久化：** `AlphaMinerState` 在迭代间保持和变异
- **Reducer 机制：** `messages` 字段使用 `operator.add` 自动累积

### 12.2 为什么用 Qlib？

Microsoft Qlib 提供：
- **表达式引擎：** 声明式因子定义（如 `Ref($close, 5) / $close - 1`），无需手写 pandas 代码
- **数据基础设施：** 内置中国 A 股和美股数据支持
- **高效截面操作：** 因子评估所需的跨股票排名、相关性等
- **处理器管道：** `inst_processors` 支持噪声注入等自定义数据变换

### 12.3 为什么用 ChromaDB？

- **本地优先：** 无需外部向量数据库服务
- **持久化：** 重启后无需重新索引
- **轻量级：** 适合中等规模知识库（~20 个文档，~100 个 chunk）
- **原生 Embedding 支持：** `OpenAIEmbeddingFunction` 直接集成

### 12.4 反思循环 (Reflexive Loop)

这是系统的核心创新 — 创建 **自我改进** 的闭环：

```
IdeaAgent (生成假设)
    ↓
FactorAgent (实现因子)
    ↓
EvalAgent (评估 + 反思)
    ├── 写入经验到 RAG (add_experience)
    └── 生成 suggested_improvements
    ↓
IdeaAgent (下一轮)
    ├── RAG 检索到上一轮经验
    └── Prompt 中包含 suggested_improvements
    ↓
... (改进的假设)
```

这模拟了人类量化研究员的迭代过程：
1. 失败的因子生成具体反馈（"IC 太低因为动量信号太嘈杂"）
2. 反馈存储在 RAG 中作为"经验"
3. 下一轮 IdeaAgent 检索到这些经验
4. 新假设明确避免过去的错误

### 12.5 噪声鲁棒性测试

`noise_proc.py` 实现因子鲁棒性验证：
- **高斯噪声 (PFS1)：** 测试正常扰动下的稳定性
- **Student's t 噪声 (PFS2)：** 测试厚尾扰动下的稳定性（`dof=3`，非常厚的尾部）
- **乘性噪声模型：** `x' = x * (1 + ε)`，保持数据的量级特征
- **方差校准：** 使用沪深300指数的历史波动率作为噪声方差，确保噪声水平与真实市场波动一致

### 12.6 模拟回测回退机制

当 Qlib 数据不可用时（常见于开发/演示环境），EvalAgent 使用确定性模拟：
```python
seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
rng = random.Random(seed)
```
- 相同表达式 → 相同种子 → 相同指标（可复现）
- 指标范围模拟真实分布：IC ∈ [-0.05, 0.15]
- 状态中标记 `is_simulated=True`，在摘要中显示 `(SIMULATED)`

### 12.7 LLM 评分机制

`AlphaEval.LLM_scores()` 使用 LLM 对因子进行定性评估：
- 评分范围：50-100
- 评估维度：金融市场逻辑的合理性
- 偏好较长/复杂的因子（符合自动搜索目标）
- 返回 JSON 数组，包含每个因子的分数和解释
- 使用正则表达式清理 Markdown 代码块包装

---

## Quick Start

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 2. 安装依赖
pip install -r requirements.txt
# 或使用 conda:
# conda env create -f environment.yml && conda activate aiminer

# 3. (可选) 获取最新知识库数据
python scripts/fetch_arxiv_qfin.py
python scripts/fetch_market_metadata.py

# 4. (可选) 准备 Qlib 数据 (用于真实回测)
# python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn

# 5. 运行 Alpha 挖掘工作流
python main.py --iterations 3 --verbose

# 6. (首次运行或知识库更新后) 强制重建 RAG
python main.py --iterations 1 --rebuild-rag
```
# AlphaMiner — 项目技术说明书 (Project Instruction Manual)

> 一个完全 "vibe-coded" 的自主 Alpha 因子挖掘框架,基于 **LangGraph**、**Qlib** 和 **LLM Agents** 
构建。系统自动提出市场假设、将其转化为量化因子、回测评估,并通过反思反馈循环迭代改进。

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Directory Structure](#2-directory-structure)
3. [Workflow & State Machine](#3-workflow--state-machine)
4. [Agents](#4-agents)
5. [Core Modules](#5-core-modules)
6. [Schemas / Data Models](#6-schemas--data-models-schemasmessagespy)
7. [Data & Knowledge Base](#7-data--knowledge-base-datarag_docs)
8. [Scripts (Data Fetching)](#8-scripts-data-fetching)
9. [Entry Point](#9-entry-point-mainpy)
10. [Configuration & Environment](#10-configuration--environment)
11. [End-to-End Flow](#11-end-to-end-flow)
12. [Technical Deep-Dive](#12-technical-deep-dive)
13. [Troubleshooting](#13-troubleshooting)
14. [Performance Optimization](#14-performance-optimization)
15. [Extension Ideas](#15-extension-ideas)
16. [Best Practices](#16-best-practices)
17. [API Reference](#17-api-reference)
18. [Contributing](#18-contributing)

---

## 1. Architecture Overview

[Content continues with full Chinese documentation as shown in the file...]

## 13. Troubleshooting

### Common Issues

**1. JSON Parsing Errors**:
```
Invalid JSON: control character (\u0000-\u001F) found
```
**Solution**: Already handled by `_strip_markdown_json()` in agents. If persists, check LLM temperature (lower = more structured output).

**2. Qlib Expression Validation Failures**:
```
ExpressionOps parse error: unmatched parentheses
```
**Solution**: FactorAgent includes basic validation. If errors persist, manually test expressions in Qlib REPL:
```python
from qlib.data.ops import ExpressionOps
expr = "($close - Mean($close, 20)) / Std($close, 20)"
ops = ExpressionOps(expr)
ops.load("csi300", "2020-01-01", "2020-12-31")
```

**3. ChromaDB Initialization Errors**:
```
chromadb.errors.InvalidCollectionException
```
**Solution**: Delete `data/chroma_db/` and rebuild:
```bash
rm -rf data/chroma_db
python main.py --rebuild-rag --iterations 1
```

**4. API Rate Limiting**:
```
429 Too Many Requests
```
**Solution**: Reduce iteration count or add delays between LLM calls.

**5. Qlib Data Not Found**:
```
FileNotFoundError: Qlib data directory not found
```
**Solution**: Download Qlib data:
```bash
python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

---

## 14. Performance Optimization

### RAG Retrieval Speed
- Reduce `n_results` in `retrieve()` calls
- Use smaller embedding models
- Implement caching for repeated queries

### Backtesting Performance
- Reduce date range for faster iteration
- Use smaller stock universe during development
- Disable noise injection when not needed

---

## 15. Extension Ideas

### Multi-Asset Support
Extend beyond Chinese equities to US stocks, futures, crypto.

### Ensemble Factor Mining
Run multiple parallel workflows with different LLM parameters.

### Real-Time Factor Monitoring
Deploy factors to production and monitor live performance.

---

## 16. Best Practices

### Prompt Engineering
- Be specific about output format
- Include examples
- Use chain-of-thought reasoning

### Iteration Strategy
- Start with 5-10 iterations for exploration
- Increase to 30-50 for production
- Review logs after each run

### Knowledge Base Curation
- Use high-quality academic sources
- Include industry reports
- Avoid outdated or overfitted strategies

### Factor Validation Checklist
- IC > 0.02 on out-of-sample data
- Rank IC > 0.01
- Sharpe ratio > 1.0
- Low correlation with existing factors
- Stable across market regimes

---

## 17. API Reference

See code documentation for detailed API specifications.

---

## 18. Contributing

Create new agents by extending the base pattern and adding to the workflow graph.

---

**Last Updated**: 2026-03-31
