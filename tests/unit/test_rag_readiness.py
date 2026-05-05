import sqlite3

from core.rag import RAGModule, chroma_sqlite_summary, resolve_embedding_model_tag


def test_chroma_sqlite_summary_reports_empty_store_not_ready(tmp_path):
    db_dir = tmp_path / "chroma_db" / "kimi_embedding-2"
    db_dir.mkdir(parents=True)
    sqlite_path = db_dir / "chroma.sqlite3"
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("CREATE TABLE collections (id TEXT)")
        conn.execute("CREATE TABLE embeddings (id TEXT)")
        conn.commit()

    payload = chroma_sqlite_summary(str(tmp_path / "chroma_db"), "kimi_embedding-2")

    assert payload["exists"] is True
    assert payload["collections"] == 0
    assert payload["embeddings"] == 0
    assert payload["ready"] is False


def test_chroma_sqlite_summary_reports_populated_store_ready(tmp_path):
    db_dir = tmp_path / "wiki_db" / "openai_text-embedding-3-large"
    db_dir.mkdir(parents=True)
    sqlite_path = db_dir / "chroma.sqlite3"
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("CREATE TABLE collections (id TEXT)")
        conn.execute("CREATE TABLE embeddings (id TEXT)")
        conn.execute("INSERT INTO collections (id) VALUES ('c1')")
        conn.execute("INSERT INTO embeddings (id) VALUES ('e1')")
        conn.commit()

    payload = chroma_sqlite_summary(
        str(tmp_path / "wiki_db"), "openai_text-embedding-3-large"
    )

    assert payload["collections"] == 1
    assert payload["embeddings"] == 1
    assert payload["ready"] is True


def test_resolve_embedding_model_tag_uses_local_embedding_env(monkeypatch):
    monkeypatch.setenv("USE_LOCAL_EMBEDDING", "true")

    assert resolve_embedding_model_tag() == "Qwen_Qwen3-Embedding-4B"


def test_repair_deletes_unhealthy_collection(tmp_path, monkeypatch):
    db_dir = tmp_path / "chroma_db" / "glm_embedding-3"
    db_dir.mkdir(parents=True)
    sqlite_path = db_dir / "chroma.sqlite3"
    sqlite_path.touch()

    deleted = []
    quarantined = []
    rag = RAGModule.__new__(RAGModule)
    rag.db_dir = str(db_dir)

    def fake_probe(collection_name):
        return collection_name == "knowledge_base"

    def fake_delete(collection_name):
        deleted.append(collection_name)
        return True

    monkeypatch.setattr(rag, "_probe_collection_health", fake_probe)
    monkeypatch.setattr(rag, "_delete_collection_out_of_process", fake_delete)
    monkeypatch.setattr(
        rag, "_quarantine_chroma_dir", lambda: quarantined.append(True)
    )

    rag._repair_unhealthy_chroma_collections(("knowledge_base", "experiences"))

    assert deleted == ["experiences"]
    assert quarantined == []
