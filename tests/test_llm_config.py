"""Unit tests for LLM provider configuration (no network)."""

import os
import unittest
from unittest import mock

from core.llm import (
    get_llm_config,
    get_embedding_defaults,
    get_provider_base_url,
    EMBEDDING_DEFAULTS,
)


class TestLLMConfig(unittest.TestCase):
    def test_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            get_llm_config(provider="not-a-real-provider")

    def test_explicit_provider_reads_env(self):
        env = {"OPENAI_API_KEY": "sk-test-openai", "ZHIPU_API_KEY": "zk-test"}
        with mock.patch.dict(os.environ, env, clear=False):
            cfg = get_llm_config(provider="openai")
            self.assertEqual(cfg["provider"], "openai")
            self.assertEqual(cfg["api_key"], "sk-test-openai")

            cfg_glm = get_llm_config(provider="glm")
            self.assertEqual(cfg_glm["provider"], "glm")
            self.assertEqual(cfg_glm["api_key"], "zk-test")

    def test_auto_detect_finds_first_available_key(self):
        # Clear common keys then set only deepseek
        clear_keys = [
            "OPENAI_API_KEY",
            "OpenAI_KEY",
            "ANTHROPIC_API_KEY",
            "ClaudeCode_KEY",
            "ZHIPU_API_KEY",
            "GLM_KEY",
            "KIMI_API_KEY",
            "LLM_KEY",
            "QWEN_API_KEY",
            "DEEPSEEK_API_KEY",
            "OPENROUTER_API_KEY",
            "GROQ_API_KEY",
        ]
        env = {k: "" for k in clear_keys}
        env["DEEPSEEK_API_KEY"] = "ds-test"
        with mock.patch.dict(os.environ, env, clear=False):
            # Empty string is falsy in os.getenv usage after patch — ensure None-like
            for k in clear_keys:
                if k != "DEEPSEEK_API_KEY" and k in os.environ and not os.environ[k]:
                    del os.environ[k]
            cfg = get_llm_config()
            self.assertEqual(cfg["provider"], "deepseek")
            self.assertEqual(cfg["api_key"], "ds-test")

    def test_openai_embedding_uses_official_api(self):
        emb = get_embedding_defaults("openai")
        self.assertIn("api.openai.com", emb["api_base"])
        self.assertNotIn("gptsapi", emb["api_base"])

    def test_base_url_override(self):
        with mock.patch.dict(
            os.environ, {"OPENAI_BASE_URL": "https://example.com/v1"}, clear=False
        ):
            self.assertEqual(
                get_provider_base_url("openai"), "https://example.com/v1"
            )

    def test_embedding_defaults_cover_core_providers(self):
        for name in ("openai", "glm", "kimi", "qwen"):
            self.assertIn(name, EMBEDDING_DEFAULTS)


if __name__ == "__main__":
    unittest.main()
