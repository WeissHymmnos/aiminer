# Utility scripts

Helpers for bootstrapping knowledge and market data. None of these are required
for a minimal dry run of the agent graph, but they improve RAG quality.

| Script | Purpose |
|--------|---------|
| `download_qlib_data.py` | Download Qlib market data for `--mode qlib` |
| `fetch_academic_papers.py` | Academic paper metadata into `data/rag_docs/academic/` |
| `fetch_arxiv_qfin.py` | Recent arXiv q-fin abstracts |
| `fetch_arxiv_with_pkg.py` | arXiv fetch via the `arxiv` package |
| `fetch_macro_news.py` | Macro news into year-partitioned folders |
| `fetch_market_metadata.py` | Market metadata via AKShare |

Large corpora (e.g. full `papers_title_abstract.json`) are **not** stored in
git; regenerate them with the scripts above when needed.

Example:

```bash
python scripts/fetch_arxiv_qfin.py
python scripts/fetch_market_metadata.py
```
