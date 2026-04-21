# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Alpha Miner is an automated quantitative factor discovery system. A **Manager-SubAgent swarm** of LLM-powered quant researchers autonomously generates, implements, backtests, and curates trading alpha factors. The system runs end-to-end: hypothesis → math formula → Python code → backtest → orthogonalization → final factor pool.

## Environment Setup

```bash
conda env create -f environment.yml && conda activate aiminer
pip install -r requirements.txt
cp .env.example .env  # then fill in API keys
```

Required `.env` keys: `ZHIPU_API_KEY` (or any other LLM provider key), `RQ_USER`/`RQ_PASS`/`RQ_TOKEN` for RiceQuant backtesting.

## Running the System

**Multi-agent swarm (main mode):**
```bash
python manager.py --iterations 5 --mode ricequant --llm-provider glm --llm-model glm-4 \
  --roles "动量反转专家" "统计套利专家" --parallel --wiki-bootstrap
```

**Single-agent legacy mode:**
```bash
python main.py --iterations 3 --mode ricequant --llm-provider glm --llm-model glm-5
```

`--mode` is either `ricequant` (A-stock, requires RQ credentials) or `qlib` (Microsoft Qlib). `--rebuild-rag` forces re-embedding of docs in `data/rag_docs/`.

## Running Tests

```bash
python -m pytest tests/
python -m pytest tests/test_numerical_consistency.py  # single test file
python -m pytest tests/test_polars_ops_extensive.py -v
```

Standalone test scripts (not pytest):
```bash
python scripts/manual_tests/test_eval.py
python scripts/manual_tests/test_ctx.py
```

## Architecture

### Data Flow

```
manager.py (PortfolioManager)
  └─ spawns N SubAgents via ProcessPoolExecutor
       └─ sub_agent.py (AlphaResearcher)
            └─ workflow/graph.py (LangGraph state machine)
                 ├─ idea_agent     → hypothesis generation (RAG + Wiki context)
                 ├─ factor_agent   → math formula + Python code
                 ├─ eval_agent     → backtest (RiceQuant or Qlib)
                 ├─ wiki_update    → persist proven factors to LLMWiki
                 └─ increment      → loop control / early stopping
  └─ filters pool: IC > 0.01, Pearson correlation < 0.7
  └─ optional genetic crossover of top-2 factors
  └─ saves to SQLite (results/alpha_miner.db) + JSON
```

### Key Modules

| Module | Role |
|---|---|
| `workflow/state.py` | `AlphaMinerState` TypedDict — the single shared state object flowing through LangGraph |
| `workflow/graph.py` | LangGraph graph definition; conditional routing based on validity, effectiveness, patience counter |
| `agents/idea_agent.py` | Hypothesis generation using HybridKnowledge (RAG + Wiki) |
| `agents/factor_agent.py` | Translates hypothesis → operator expression; whitelist validation + AST safety check |
| `agents/eval_agent.py` | Runs backtest, extracts IC/RankIC/Sharpe; LLM effectiveness review |
| `core/llm.py` | Multi-provider LLM gateway (Kimi, Qwen, GLM, Claude, OpenAI, DeepSeek, Groq, Ollama, vLLM) |
| `core/rag.py` | ChromaDB vector store; BM25 + semantic hybrid retrieval |
| `core/hybrid_knowledge.py` | Fuses RAG + LLMWiki; auto-updates wiki after successful backtests |
| `core/wiki.py` | LLMWiki: structured card-based knowledge store for proven factors |
| `core/alphaeval/rq_eval.py` | RiceQuant backtester; SafeEvalTransformer for safe expression execution |
| `core/alphaeval/modeltester.py` | Qlib adapter |
| `schemas/messages.py` | Pydantic output models for all LLM structured outputs |

### LangGraph Early Stopping

The workflow loops up to `max_iterations`. Early exit triggers when IC ≥ 0.05 (exceptional signal found) or `patience` counter reaches 3 (no improvement in IC over 3 consecutive iterations).

### Factor Expression Safety

`FactorAgent` validates code expressions against a whitelist of allowed operators (defined in the agent) before any execution. `SafeEvalTransformer` in `rq_eval.py` converts unknown AST names to string literals to prevent injection.

### LLM Provider Selection

`core/llm.py` auto-detects available API keys from environment and returns a `ChatOpenAI`-compatible client. Temperature varies by agent: 0.7 for idea generation, 0.1 for strict code validation, 0.3–0.4 for evaluation review.

### Evaluation Fallback

If the real backtest fails, `eval_agent` falls back to deterministic hash-based simulated metrics (flagged as `is_simulated=True` in state). Simulated factors are filtered out by the manager.

## Output

- `results/alpha_miner.db` — SQLite factor pool
- `results/factor_pool.json` — JSON backup
- `results/reports/` — Markdown reports per factor
- `results/charts/` — Equity curve PNGs
- `data/chroma_db/` — Persistent ChromaDB embeddings
- `data/wiki_db/` — LLMWiki cards
