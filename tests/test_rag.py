import unittest
import tempfile
from unittest.mock import patch

from aiminer.core.rag import RAGModule


class FakeEmbeddingFunction:
    def __init__(self, *args, **kwargs):
        pass

    def name(self):
        return "default"

    def __call__(self, input):
        return [[0.0, 0.0, 0.0, 0.0] for _ in input]


class TestRAG(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.embedding_patch = patch(
            "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction",
            FakeEmbeddingFunction,
        )
        self.embedding_patch.start()
        # Keep Chroma writes inside an ephemeral directory; never touch tracked data/test_db.
        self.rag = RAGModule(
            db_dir=f"{self.tmpdir.name}/chroma",
            docs_dir=f"{self.tmpdir.name}/docs",
            rebuild=False,
            embedding_provider="local",
        )

    def tearDown(self):
        self.embedding_patch.stop()
        self.tmpdir.cleanup()

    def test_chunking(self):
        text = "This is a paragraph.\n\nThis is another paragraph."
        chunks = self.rag._chunk_text(text, chunk_size=10, overlap=0)
        self.assertGreaterEqual(len(chunks), 2)

    def test_empty_retrieval(self):
        # 测试在没有任何文档时的检索行为
        res = self.rag.retrieve("What is Alpha158?")
        self.assertIn("No relevant knowledge found", res)


if __name__ == "__main__":
    unittest.main()
