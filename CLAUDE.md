# CLAUDE.md

This file provides context and engineering guidelines for Claude Code and other AI coding agents working in this repository.

## Project Overview

AI Alpha Miner (`aiminer`) is a multi-agent quantitative factor discovery and strategy evaluation system. A `PortfolioManager` orchestrates multiple role-specialized `AlphaResearcher` workers, each running a LangGraph state machine (`IdeaAgent` → `FactorAgent` → `EvalAgent` → `StrategyAgent` / `StrategyCritic` → `LLMWiki` update). Proven factors are filtered by IC/Sharpe thresholds, deduplicated by daily return correlation, optionally recombined via genetic crossover, and persisted to SQLite (`results/alpha_miner.db`) alongside run manifests, charts, and Markdown reports.

## Environment & Installation

```bash
conda env create -f environment.yml && conda activate aiminer
pip install -e ".[all,test]"
cp .env.example .env  # configure LLM API keys and RiceQuant credentials
```

Optional Rust Polars native plugin build:

```bash
cd polars_plugins && maturin develop --release
```

## Running the System

Console script entry points (installed via `pip install -e .`) or module invocations with `PYTHONPATH=src`:

```bash
# Multi-agent swarm CLI
PYTHONPATH=src python -m aiminer.manager --iterations 5 --mode ricequant \
  --llm-provider glm --llm-model glm-4 \
  --roles "量价反转研究员" "统计套利研究员" --parallel --wiki-bootstrap

# Single-agent workflow CLI
PYTHONPATH=src python -m aiminer.main --iterations 3 --mode ricequant

# Web workstation (FastAPI on :8000 + Vite dev server on :5173, or --prod for single-port SPA)
./start_web.sh
./start_web.sh --prod

# Terminal UI (Textual)
PYTHONPATH=src python -m aiminer.tui
```

## Running Tests & Verification

```bash
# Hermetic unit tests (default CI gate — no network, credentials, or compiled Rust plugin required)
PYTHONPATH=src pytest tests/unit -m "unit and not external and not native" -q

# External dependency tests (requires RQ_TOKEN / RiceQuant credentials)
PYTHONPATH=src pytest -m external -q

# Native Rust Polars plugin tests
PYTHONPATH=src pytest -m native -q

# Full CI matrix check (bytecode compilation, CI workflow check, Ruff lint, pytest collection)
python scripts/verify_ci_matrix.py
```

## Architecture & Module Map

All Python package source lives under `src/aiminer/`:

```text
src/aiminer/
  ├─ manager.py          : PortfolioManager top-level swarm orchestrator & CLI
  ├─ scheduler.py        : Process/thread pool execution, worker limits, timeouts, log queue forwarding
  ├─ selector.py         : Factor scoring, return-correlation culling, negative-IC orientation
  ├─ crossover.py        : Genetic crossover of top parent factors
  ├─ persistence.py      : SQLite schema initialization, atomic JSON backups, checkpoint recovery
  ├─ sub_agent.py        : AlphaResearcher single-worker runner
  ├─ main.py             : Single-agent CLI entry point
  ├─ tui.py              : Textual terminal UI
  ├─ api.py              : FastAPI application entry point & backward-compatible re-exports
  ├─ routers/            : Modular FastAPI routers (admin, backtest, strategy, swarm, wiki, websocket, common)
  ├─ app_workflow/       : LangGraph state machine (graph.py) and AlphaMinerState TypedDict (state.py)
  ├─ agents/             : LLM agents (idea_agent, factor_agent, eval_agent, strategy_agent, strategy_critic, portfolio_agent, summary_agent)
  ├─ core/               : Settings, LLM gateway, Codex CLI wrapper, RAG, LLMWiki, StrategyBacktester, local data loader, lifecycle & manifest tracking
  │    └─ alphaeval/     : Factor evaluation engines (rq_eval.py, polars_engine.py, modeltester.py)
  └─ schemas/            : Pydantic structured output models (messages.py)
```

### Key Architectural Invariants

1. **Factor Expression Safety**: `FactorAgent` validates generated expressions against an explicit operator and field whitelist before evaluation. `SafeEvalTransformer` in `src/aiminer/core/alphaeval/rq_eval.py` rewrites AST nodes to prevent arbitrary code execution. Never introduce raw `eval()` on untrusted strings.
2. **No Silent Simulation Contamination**: When real backtest evaluation fails, fallback simulated metrics are flagged with `is_simulated=True` and strictly excluded from the production alpha pool by `PortfolioManager`.
3. **API Compatibility & State Consistency**: `src/aiminer/api.py` mounts modular routers from `src/aiminer/routers/` and syncs monkeypatched attributes across submodules for test compatibility. Swarm run status checks combine on-disk run manifests (`results/swarm_runs/*.json`) with OS process liveness (`psutil`) and use a two-phase stop transition (`stopping` → `stopped`).
4. **Formatting & Lint**: Follow Google Python Style at 80 columns (`ruff check src tests`).
