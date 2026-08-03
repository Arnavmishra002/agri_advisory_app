import os
import unittest
from unittest.mock import patch

from phase1.rag import eval_retrieval


class RetrievalEvalConfigurationTests(unittest.TestCase):
    def test_ollama_url_uses_runtime_environment(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://ollama.internal:11434"}):
            self.assertEqual(eval_retrieval._ollama_url(), "http://ollama.internal:11434")


if __name__ == "__main__":
    unittest.main()
