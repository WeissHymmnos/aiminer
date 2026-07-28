# AI Alpha Miner

Multi-agent swarm for **automated quantitative alpha factor discovery**.

A Manager coordinates specialized SubAgents (LLM-powered quant researchers) that
generate hypotheses, implement factor expressions, backtest them, and curate an
orthogonal factor pool. Built on **LangGraph**, with dual evaluation backends
(**RiceQuant** / **Qlib**) and a hybrid RAG + LLM-Wiki knowledge layer.

> **Status:** research prototype, prepared for open-source collaboration.
> Expect sharp edges; contributions and issue reports are welcome.

## Features

- **Manager–SubAgent swarm** — parallel or serial researchers with role priors
  (momentum, mean-reversion, stat-arb, …)
- **Closed research loop** — Idea → Formula → Code → Backtest → Reflect
- **Orthogonal factor pool** — IC filter + return-correlation de-duplication
- **Hybrid knowledge** — ChromaDB RAG + structured LLM Wiki cards
- **Dual engines** — RiceQuant (A-share) and Microsoft Qlib
- **Optional Polars/Rust plugins** — faster cross-sectional / time-series ops
- **API + TUI** — FastAPI workstation API and Textual terminal UI

## Quick start

### 1. Environment

```bash
conda env create -f environment.yml
conda activate aiminer
# or: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

cp .env.example .env
# Edit .env: set at least one LLM key; for RiceQuant also set RQ_TOKEN (or RQ_USER/RQ_PASS)
```

Required secrets (never commit real values):

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` / `ZHIPU_API_KEY` / … | At least one LLM provider |
| `RQ_TOKEN` (or `RQ_USER` + `RQ_PASS`) | RiceQuant backtest mode |

See [`.env.example`](./.env.example) for the full list and base-URL overrides.

### 2. Run the swarm

```bash
python manager.py --iterations 5 --mode ricequant \
  --llm-provider glm --llm-model glm-4 \
  --roles "动量反转专家" "统计套利专家" \
  --parallel --wiki-bootstrap
```

Single-agent legacy mode:

```bash
python main.py --iterations 3 --mode ricequant --llm-provider glm --llm-model glm-5
```

### 3. Optional services

```bash
# HTTP API
uvicorn api:app --host 0.0.0.0 --port 8000

# Terminal UI
python tui.py

# Docker
docker compose up --build
```

See [README_DOCKER.md](./README_DOCKER.md) for container details.

## Project structure

```
aiminer/
├── manager.py / sub_agent.py   # Swarm entry points
├── main.py                     # Single-agent mode
├── api.py / tui.py             # API & TUI
├── agents/                     # Idea / Factor / Eval / Summary
├── workflow/                   # LangGraph graph + state
├── core/                       # LLM, RAG, Wiki, backtesters
├── schemas/                    # Pydantic structured outputs
├── scripts/                    # Data fetch utilities
├── tests/                      # Pytest suite
├── data/rag_docs/              # Seed RAG documents (safe to commit)
├── data/wiki_vault/            # Seed wiki pages only
└── polars_plugins/             # Optional Rust operators
```

Runtime artifacts (`results/`, `data/chroma_db/`, `data/wiki_db/`, generated
wiki factor cards) are **gitignored** and recreated on first run.

## Tests

```bash
python -m pytest tests/ -q
```

## Outputs

| Path | Content |
|------|---------|
| `results/alpha_miner.db` | SQLite factor pool |
| `results/factor_pool.json` | JSON backup |
| `results/reports/` | Per-factor Markdown reports |
| `results/charts/` | Equity curves |
| `data/chroma_db/` | RAG embeddings |
| `data/wiki_db/` / `data/wiki_vault/` | Wiki store + markdown cards |

## Documentation

| Doc | Audience |
|-----|----------|
| [instruction.md](./instruction.md) | Full architecture & operator reference |
| [CLAUDE.md](./CLAUDE.md) | Concise map for AI coding agents |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Dev setup & PR guidelines |
| [SECURITY.md](./SECURITY.md) | Vulnerability reporting |
| [README_DOCKER.md](./README_DOCKER.md) | Docker usage |

## License

**GNU Affero General Public License v3.0 (AGPL-3.0)** — see [LICENSE](./LICENSE).

This is a **strong copyleft** license:

- Any distributed modification (or larger work based on this project) must also
  be released under AGPL-3.0, with complete corresponding source.
- If you run a modified version as a **network service** (e.g. the FastAPI API
  or a hosted swarm), you must offer the complete source of that version to
  users who interact with it over the network (AGPL §13).

Contributions are accepted only under AGPL-3.0 (see [CONTRIBUTING.md](./CONTRIBUTING.md)).

## Disclaimer

This software is for **research and educational purposes only**. It is not
investment advice. Past backtest performance does not guarantee future results.
Users are solely responsible for compliance with data-vendor terms (RiceQuant,
exchange data, etc.) and for any trading decisions they make.
