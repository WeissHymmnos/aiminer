import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.wiki import LLMWiki


class FakeCollection:
    def __init__(self):
        self.docs = {}

    def upsert(self, ids, documents, metadatas):
        for idx, doc, meta in zip(ids, documents, metadatas):
            self.docs[idx] = (doc, meta)

    def count(self):
        return len(self.docs)

    def get(self, where=None, include=None):
        ids, documents, metadatas = [], [], []
        for idx, (doc, meta) in self.docs.items():
            if where:
                if any(meta.get(k) != v for k, v in where.items()):
                    continue
            ids.append(idx)
            documents.append(doc)
            metadatas.append(meta)
        return {"ids": ids, "documents": documents, "metadatas": metadatas}

    def query(self, query_texts, n_results, where=None):
        results = self.get(where=where)
        docs = results["documents"][:n_results]
        metas = results["metadatas"][:n_results]
        return {"documents": [docs], "metadatas": [metas]}


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.collection = FakeCollection()

    def get_or_create_collection(self, *args, **kwargs):
        return self.collection


class TestWikiGraph(unittest.TestCase):
    @patch("core.wiki.chromadb.PersistentClient", FakeClient)
    @patch("core.wiki.SentenceTransformerEmbeddingFunction", lambda *args, **kwargs: object())
    def test_upgrade_to_graph_schema_rewrites_factor_card(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "wiki_vault"
            vault.mkdir(parents=True, exist_ok=True)
            (vault / "index.md").write_text("# Index\n", encoding="utf-8")
            (vault / "log.md").write_text("# Log\n", encoding="utf-8")
            (vault / "sample_factor.md").write_text(
                """---
title: "Sample Factor"
type: "factor_card"
status: "proven"
summary: "short summary"
simulated: true
is_effective: true
---

**Hypothesis**: VWAP liquidity reversal

**Rationale**: Uses volume and vwap in a high-volatility regime.

**Implementation (Qlib)**: `Rank(Div(Delta($close,1),Mean($volume,3)))`

**Math Formula**: x

**IC / RankIC**: 0.02 / 0.03

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Some implementation mismatch.

**Suggested Improvements**: Reduce turnover.
""",
                encoding="utf-8",
            )

            wiki = LLMWiki(db_dir=str(Path(tmpdir) / "wiki_db"), wiki_vault=str(vault))
            result = wiki.upgrade_to_graph_schema()
            self.assertIn("sample_factor", result["upgraded"])

            upgraded = (vault / "sample_factor.md").read_text(encoding="utf-8")
            self.assertIn('type: "experiment_card"', upgraded)
            self.assertIn('evidence_level: "simulated"', upgraded)
            self.assertIn("## Related Concepts", upgraded)
            self.assertTrue((vault / "taxonomy_strategy_families.md").exists())
