import os
import unittest
from unittest.mock import patch

from core.settings import build_settings, detect_llm_provider, provider_api_key


class TestSettings(unittest.TestCase):
    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True)
    def test_detects_provider_from_environment(self):
        self.assertEqual(detect_llm_provider(), "openai")
        self.assertEqual(provider_api_key("openai"), "sk-test")

    @patch.dict(os.environ, {}, clear=True)
    def test_build_settings_prefers_overrides(self):
        settings = build_settings(
            {
                "iterations": 3,
                "mode": "qlib",
                "data_backend": "local",
                "engine": "polars",
                "llm_provider": "lmstudio",
                "llm_base_url": "http://127.0.0.1:1234/v1",
                "market_mode": "mixed",
                "market_profile": "cn_stock",
                "market_profiles": "cn_stock,us_stock",
                "local_data_path": "/tmp/local-data",
                "local_data_layout": "panel",
                "market_start": "2020-01-01",
                "market_end": "2020-12-31",
                "use_gpu": True,
            }
        )
        self.assertEqual(settings.max_iterations, 3)
        self.assertEqual(settings.evaluation_mode, "qlib")
        self.assertEqual(settings.data_backend, "local")
        self.assertEqual(settings.evaluation_engine, "polars")
        self.assertEqual(settings.llm_provider, "lmstudio")
        self.assertEqual(settings.llm_base_url, "http://127.0.0.1:1234/v1")
        self.assertEqual(settings.market_mode, "mixed")
        self.assertEqual(settings.market_profiles, ["cn_stock", "us_stock"])
        self.assertTrue(settings.use_gpu)

    @patch.dict(os.environ, {}, clear=True)
    def test_invalid_provider_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_settings({"llm_provider": "unknown-provider"})

    @patch.dict(os.environ, {}, clear=True)
    def test_local_backend_requires_path(self):
        with self.assertRaises(ValueError):
            build_settings({"data_backend": "local"})

    @patch.dict(os.environ, {}, clear=True)
    def test_provider_api_key_uses_lmstudio_sentinel(self):
        self.assertEqual(provider_api_key("lmstudio"), "lm-studio")
