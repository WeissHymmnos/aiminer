# Contributing to AI Alpha Miner

Thanks for your interest in improving this project. This document covers the
minimum needed to develop and submit changes productively.

## License of contributions

This project is licensed under the **GNU Affero General Public License v3.0
(AGPL-3.0-only)**. By submitting a pull request or other contribution, you
agree that your contribution is licensed under AGPL-3.0-only and that you have
the right to submit it under those terms.

If you cannot accept AGPL-3.0, please do not contribute code.

## Development setup

```bash
# Conda (recommended)
conda env create -f environment.yml
conda activate aiminer
pip install -r requirements.txt

# Or plain venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill in API keys you need
```

Optional Polars Rust plugins (faster CS/TS operators):

```bash
cd polars_plugins && maturin develop --release
```

## Running tests

```bash
python -m pytest tests/ -q
```

Integration tests that need RiceQuant credentials are skipped when `RQ_TOKEN`
(or `RQ_USER`/`RQ_PASS`) is unset.

## Project layout

| Path | Role |
|------|------|
| `manager.py` / `sub_agent.py` | Swarm orchestration entry points |
| `main.py` | Single-agent legacy entry point |
| `workflow/` | LangGraph state machine |
| `agents/` | Idea / Factor / Eval / Summary agents |
| `core/` | LLM gateway, RAG, Wiki, backtest engines |
| `schemas/` | Pydantic structured-output models |
| `scripts/` | Data fetch / bootstrap utilities |
| `tests/` | Pytest suite (preferred over root-level scripts) |
| `api.py` / `tui.py` | HTTP API and Textual TUI |

## Coding guidelines

1. **No secrets in source** — use env vars via `.env` / `python-dotenv`.
2. **Do not commit runtime artifacts** — `results/`, `data/wiki_db/`,
   `data/chroma_db/`, generated wiki factor cards (`*_iter*.md`).
3. **Keep factor evaluation safe** — extend operator whitelists deliberately;
   never re-enable unrestricted `eval` of LLM output.
4. **Prefer small, focused PRs** — one concern per PR when possible.
5. **Add or update tests** when changing operators, routing, or validation.
6. **Match existing style** — type hints where helpful, `loguru` for logging,
   Pydantic models for LLM structured output.

## Pull request checklist

- [ ] `pytest tests/` passes (or failures are explained)
- [ ] No `.env`, credentials, or large binary DBs in the diff
- [ ] README / docs updated if CLI flags or env vars changed
- [ ] New dependencies pinned or justified in `requirements.txt`

## Architecture deep-dive

See [instruction.md](./instruction.md) for the full system design, operator
catalog, and evaluation pipeline details. Agent-oriented notes live in
[CLAUDE.md](./CLAUDE.md).
