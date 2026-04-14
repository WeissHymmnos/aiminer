import unittest
from core.rag import RAGModule

class TestRAG(unittest.TestCase):
    def setUp(self):
        # 初始化一个轻量级的RAG，尽量不触发大规模DB加载
        self.rag = RAGModule(db_dir="data/test_db", rebuild=False)

    def test_chunking(self):
        text = "This is a paragraph.\n\nThis is another paragraph."
        chunks = self.rag._chunk_text(text, chunk_size=10, overlap=0)
        self.assertGreaterEqual(len(chunks), 2)
        
    def test_empty_retrieval(self):
        # 测试在没有任何文档时的检索行为
        res = self.rag.retrieve("What is Alpha158?")
        self.assertIn("No relevant entries found.", res)

if __name__ == "__main__":
    unittest.main()
