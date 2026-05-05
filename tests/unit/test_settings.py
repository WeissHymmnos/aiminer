import os
import tempfile
import unittest
from pathlib import Path
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
                "mode": "ricequant",
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
                "disable_early_stop": True,
            }
        )
        self.assertEqual(settings.max_iterations, 3)
        self.assertEqual(settings.evaluation_mode, "ricequant")
        self.assertEqual(settings.data_backend, "local")
        self.assertEqual(settings.evaluation_engine, "polars")
        self.assertEqual(settings.llm_provider, "lmstudio")
        self.assertEqual(settings.llm_base_url, "http://127.0.0.1:1234/v1")
        self.assertEqual(settings.market_mode, "mixed")
        self.assertEqual(settings.market_profiles, ["cn_stock", "us_stock"])
        self.assertTrue(settings.use_gpu)
        self.assertTrue(settings.disable_early_stop)

    @patch.dict(os.environ, {}, clear=True)
    def test_invalid_provider_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_settings({"llm_provider": "unknown-provider"})

    @patch.dict(os.environ, {}, clear=True)
    def test_local_backend_requires_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("core.settings.load_dotenv"):
                    with self.assertRaises(ValueError):
                        build_settings({"data_backend": "local"})
            finally:
                os.chdir(cwd)

    @patch.dict(os.environ, {}, clear=True)
    def test_local_backend_auto_detects_bundled_futures_daily_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            futures_dir = root / "data" / "local_futures" / "dominant" / "1d"
            futures_dir.mkdir(parents=True)
            (futures_dir / "IF.parquet").write_bytes(b"placeholder")
            cwd = os.getcwd()
            os.chdir(root)
            try:
                with patch("core.settings.load_dotenv"):
                    settings = build_settings({"data_backend": "local"})
            finally:
                os.chdir(cwd)

        self.assertEqual(settings.market_profile, "futures")
        self.assertEqual(settings.market_profiles, ["futures"])
        self.assertEqual(
            settings.local_data_path, str(Path("data/local_futures/dominant/1d"))
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_provider_api_key_uses_lmstudio_sentinel(self):
        self.assertEqual(provider_api_key("lmstudio"), "lm-studio")

    @patch.dict(os.environ, {"MIMO_API_KEY": "mimo-test-key"}, clear=True)
    def test_provider_api_key_uses_mimo_key(self):
        self.assertEqual(provider_api_key("mimo"), "mimo-test-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_claudecode_mimo_token_is_explicit_only(self):
        with patch("core.settings._claudecode_mimo_token", return_value="mimo-token"):
            self.assertEqual(provider_api_key("mimo"), "mimo-token")
            self.assertIsNone(detect_llm_provider())

    @patch("shutil.which", return_value="/usr/bin/codex")
    @patch.dict(os.environ, {}, clear=True)
    def test_codex_provider_is_explicit_only(self, _which):
        with patch("core.settings.load_dotenv"):
            settings = build_settings({"llm_provider": "codex"})

        self.assertEqual(settings.llm_provider, "codex")
        self.assertEqual(provider_api_key("codex"), "codex")
        self.assertIsNone(detect_llm_provider())

    @patch.dict(os.environ, {}, clear=True)
    def test_codex_is_not_supported_for_embeddings(self):
        with self.assertRaises(ValueError):
            build_settings({"embedding_provider": "codex"})

    @patch.dict(os.environ, {"AIMINER_CODEX_REASONING_EFFORT": "XHIGH"}, clear=True)
    def test_reasoning_effort_from_environment_is_normalized(self):
        settings = build_settings()

        self.assertEqual(settings.llm_reasoning_effort, "xhigh")

    @patch.dict(os.environ, {"AIMINER_DISABLE_EARLY_STOP": "1"}, clear=True)
    def test_disable_early_stop_from_environment(self):
        settings = build_settings()

        self.assertTrue(settings.disable_early_stop)

    @patch.dict(os.environ, {}, clear=True)
    def test_invalid_reasoning_effort_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_settings({"llm_reasoning_effort": "extreme"})
