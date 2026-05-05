import os
import sys
import types
from pathlib import Path

import pytest

from core.evaluator_factory import build_evaluator, evaluation_config_from_mapping
from core.settings import (
    SUPPORTED_DATA_BACKENDS,
    SUPPORTED_EVALUATION_MODES,
    SUPPORTED_LLM_PROVIDERS,
    SUPPORTED_LLM_REASONING_EFFORTS,
    SUPPORTED_LOCAL_DATA_LAYOUTS,
    SUPPORTED_MARKET_MODES,
    SUPPORTED_MARKET_PROFILES,
    build_settings,
)


class _DummyEvaluator:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _profile_list(primary, raw_profiles, market_mode):
    if market_mode == "single" or not raw_profiles:
        return [primary]
    profiles = [item.strip() for item in raw_profiles.split(",") if item.strip()]
    return [primary] + [item for item in profiles if item != primary]


def _is_supported(mode, backend, market_mode, market_profile, market_profiles):
    profiles = _profile_list(market_profile, market_profiles, market_mode)
    if backend == "qlib" and mode != "qlib":
        return False
    if backend in {"ricequant", "local"} and mode != "ricequant":
        return False
    if backend == "ricequant":
        return market_mode != "mixed" and all(profile == "cn_stock" for profile in profiles)
    if backend == "qlib":
        return market_mode != "mixed" and all(profile != "futures" for profile in profiles)
    return True


@pytest.mark.parametrize("mode", SUPPORTED_EVALUATION_MODES)
@pytest.mark.parametrize("backend", SUPPORTED_DATA_BACKENDS)
@pytest.mark.parametrize("engine", ["pandas", "polars"])
@pytest.mark.parametrize("market_mode", SUPPORTED_MARKET_MODES)
@pytest.mark.parametrize("market_profile", SUPPORTED_MARKET_PROFILES)
@pytest.mark.parametrize(
    "market_profiles",
    [None, "cn_stock", "cn_stock,us_stock", "cn_stock,futures", "us_stock,futures"],
)
@pytest.mark.parametrize("local_data_layout", SUPPORTED_LOCAL_DATA_LAYOUTS)
def test_supported_parameter_matrix_is_validated_consistently(
    tmp_path,
    monkeypatch,
    mode,
    backend,
    engine,
    market_mode,
    market_profile,
    market_profiles,
    local_data_layout,
):
    monkeypatch.setattr("core.settings.load_dotenv", lambda: None)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    local_path = tmp_path / "local"
    local_path.mkdir()
    (local_path / "demo.parquet").write_bytes(b"placeholder")

    overrides = {
        "mode": mode,
        "data_backend": backend,
        "engine": engine,
        "llm_provider": "deepseek",
        "embedding_provider": "local",
        "market_mode": market_mode,
        "market_profile": market_profile,
        "market_profiles": market_profiles,
        "local_data_layout": local_data_layout,
    }
    if backend == "local":
        overrides["local_data_path"] = str(local_path)

    supported = _is_supported(mode, backend, market_mode, market_profile, market_profiles)
    if supported:
        settings = build_settings(overrides)
        assert settings.evaluation_mode == mode
        assert settings.data_backend == backend
        assert settings.evaluation_engine == engine
    else:
        with pytest.raises(ValueError):
            build_settings(overrides)


@pytest.mark.parametrize("llm_provider", [None, *SUPPORTED_LLM_PROVIDERS])
@pytest.mark.parametrize("embedding_provider", [None, "local", *SUPPORTED_LLM_PROVIDERS])
@pytest.mark.parametrize("reasoning_effort", [None, *SUPPORTED_LLM_REASONING_EFFORTS])
def test_provider_embedding_reasoning_matrix(
    tmp_path, monkeypatch, llm_provider, embedding_provider, reasoning_effort
):
    monkeypatch.setattr("core.settings.load_dotenv", lambda: None)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    local_path = tmp_path / "local"
    local_path.mkdir()
    (local_path / "demo.parquet").write_bytes(b"placeholder")

    overrides = {
        "mode": "ricequant",
        "data_backend": "local",
        "local_data_path": str(local_path),
        "llm_provider": llm_provider,
        "embedding_provider": embedding_provider,
        "llm_reasoning_effort": reasoning_effort,
    }

    if embedding_provider == "codex":
        with pytest.raises(ValueError):
            build_settings(overrides)
    else:
        settings = build_settings(overrides)
        assert settings.llm_provider == (llm_provider or "deepseek")
        assert settings.embedding_provider == embedding_provider
        assert settings.llm_reasoning_effort == reasoning_effort


def test_all_settings_supported_combinations_reach_evaluator_factory(tmp_path, monkeypatch):
    monkeypatch.setattr("core.settings.load_dotenv", lambda: None)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    for module_name, class_name in [
        ("core.alphaeval.rq_eval", "RiceQuantEval"),
        ("core.alphaeval.modeltester", "AlphaEval"),
        ("core.alphaeval.local_eval", "LocalDataEval"),
    ]:
        module = types.ModuleType(module_name)
        setattr(module, class_name, _DummyEvaluator)
        monkeypatch.setitem(sys.modules, module_name, module)

    local_path = tmp_path / "local"
    local_path.mkdir()
    (local_path / "demo.parquet").write_bytes(b"placeholder")
    failures = []

    for mode in SUPPORTED_EVALUATION_MODES:
        for backend in SUPPORTED_DATA_BACKENDS:
            for engine in ["pandas", "polars"]:
                for market_mode in SUPPORTED_MARKET_MODES:
                    for market_profile in SUPPORTED_MARKET_PROFILES:
                        for market_profiles in [
                            None,
                            "cn_stock",
                            "cn_stock,us_stock",
                            "cn_stock,futures",
                            "us_stock,futures",
                        ]:
                            for local_data_layout in SUPPORTED_LOCAL_DATA_LAYOUTS:
                                if not _is_supported(
                                    mode,
                                    backend,
                                    market_mode,
                                    market_profile,
                                    market_profiles,
                                ):
                                    continue
                                overrides = {
                                    "mode": mode,
                                    "data_backend": backend,
                                    "engine": engine,
                                    "llm_provider": "deepseek",
                                    "embedding_provider": "local",
                                    "market_mode": market_mode,
                                    "market_profile": market_profile,
                                    "market_profiles": market_profiles,
                                    "local_data_layout": local_data_layout,
                                }
                                if backend == "local":
                                    overrides["local_data_path"] = str(local_path)
                                try:
                                    settings = build_settings(overrides)
                                    build_evaluator(
                                        factor_expressions=["Rank($close)"],
                                        config=evaluation_config_from_mapping(settings),
                                        test_start_date="2015-01-01",
                                        test_end_date="2015-02-01",
                                    )
                                except Exception as exc:
                                    failures.append((overrides, repr(exc)))

    assert failures == []
