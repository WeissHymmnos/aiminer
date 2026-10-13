# Wiki vault (seed knowledge)

Markdown cards consumed / produced by `core.wiki.LLMWiki`.

## What belongs here in git

Only **seed / baseline** pages that help bootstrap a fresh clone:

- `index.md` — vault index
- `market_regime_base.md` — market regime snapshot
- `strategy_families_base.md` — strategy taxonomy
- `qlib_operator_guide.md` — operator reference

## What is gitignored

- `*_iter*.md` — factor cards written during swarm runs
- `log.md` — runtime log
- `.obsidian/` — local editor config

On first run with `--wiki-bootstrap`, the system can also synthesize baseline
pages from RAG documents into the Chroma-backed wiki DB under `data/wiki_db/`.
