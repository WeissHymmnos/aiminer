from core import wiki as wiki_module
from core.wiki import LLMWiki


def _wiki_without_init(tmp_path, wiki_col):
    wiki = LLMWiki.__new__(LLMWiki)
    wiki.wiki_vault = str(tmp_path)
    wiki._batch_mode = False
    wiki.wiki_col = wiki_col
    wiki._backlink_audit = lambda *_args, **_kwargs: None
    wiki._log_event = lambda *_args, **_kwargs: None
    wiki._recompile_index = lambda: None
    return wiki


def test_wiki_upsert_503_does_not_block_markdown_write(tmp_path, monkeypatch):
    class FailingCollection:
        def __init__(self):
            self.upsert_calls = 0

        def upsert(self, **_kwargs):
            self.upsert_calls += 1
            raise RuntimeError("Error code: 503 in upsert.")

    monkeypatch.setattr(wiki_module.time, "sleep", lambda _seconds: None)
    collection = FailingCollection()
    wiki = _wiki_without_init(tmp_path, collection)

    page_id = wiki.add_or_update_page(
        slug="retry_factor",
        title="Retry Factor",
        content="factor content",
        metadata={"type": "experiment_card", "status": "active"},
    )

    assert page_id == "wiki_retry_factor"
    assert collection.upsert_calls == 3
    assert (tmp_path / "retry_factor.md").exists()


def test_wiki_retrieve_retries_transient_503(tmp_path, monkeypatch):
    class FlakyCollection:
        def __init__(self):
            self.query_calls = 0

        def count(self):
            return 1

        def query(self, **_kwargs):
            self.query_calls += 1
            if self.query_calls == 1:
                raise RuntimeError("Error code: 503 in query.")
            return {
                "documents": [["# Retry Factor\n\nfactor content"]],
                "metadatas": [[{"title": "Retry Factor", "type": "experiment_card"}]],
            }

    monkeypatch.setattr(wiki_module.time, "sleep", lambda _seconds: None)
    collection = FlakyCollection()
    wiki = _wiki_without_init(tmp_path, collection)

    result = wiki.retrieve("factor")

    assert collection.query_calls == 2
    assert "Retry Factor" in result
