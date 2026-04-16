from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


SUPPORTED_LLM_PROVIDERS = (
    "kimi",
    "qwen",
    "claude",
    "glm",
    "openai",
    "deepseek",
    "openrouter",
    "groq",
    "ollama",
    "vllm",
    "lmstudio",
)

SUPPORTED_EVALUATION_MODES = ("qlib", "ricequant")
SUPPORTED_DATA_BACKENDS = ("qlib", "ricequant", "local")
SUPPORTED_MARKET_MODES = ("single", "batch", "mixed")
SUPPORTED_LOCAL_DATA_LAYOUTS = ("auto", "panel", "instrument_files")
SUPPORTED_MARKET_PROFILES = ("cn_stock", "us_stock", "futures")


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("["):
        try:
            raw = json.loads(text)
            if isinstance(raw, list):
                items = [str(item).strip() for item in raw if str(item).strip()]
                return items or None
        except json.JSONDecodeError:
            pass
    items = [item.strip() for item in text.split(",") if item.strip()]
    return items or None


class AiminerSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_iterations: int = Field(default=1, ge=1)
    evaluation_mode: str = "ricequant"
    evaluation_engine: str = "pandas"
    data_backend: str = "ricequant"
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    embedding_provider: str | None = None
    market_mode: str = "single"
    market_profile: str = "cn_stock"
    market_profiles: list[str] = Field(default_factory=lambda: ["cn_stock"])
    local_data_path: str | None = None
    local_data_layout: str = "auto"
    market_start: str | None = None
    market_end: str | None = None
    market_lookback: int = Field(default=60, ge=1)
    use_gpu: bool = False
    rebuild_rag: bool = False
    wiki_bootstrap: bool = False
    verbose: bool = False
    roles: list[str] | None = None
    data_dir: str = "data"
    results_dir: str = "results"
    logs_dir: str = "logs"

    @model_validator(mode="after")
    def validate_values(self) -> "AiminerSettings":
        if self.evaluation_mode not in SUPPORTED_EVALUATION_MODES:
            raise ValueError(
                f"evaluation_mode must be one of: {', '.join(SUPPORTED_EVALUATION_MODES)}"
            )
        if self.evaluation_engine not in {"pandas", "polars"}:
            raise ValueError("evaluation_engine must be either 'pandas' or 'polars'")
        if self.data_backend not in SUPPORTED_DATA_BACKENDS:
            raise ValueError(
                f"data_backend must be one of: {', '.join(SUPPORTED_DATA_BACKENDS)}"
            )
        if self.llm_provider and self.llm_provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"Unsupported llm_provider '{self.llm_provider}'. "
                f"Expected one of: {', '.join(SUPPORTED_LLM_PROVIDERS)}"
            )
        if self.embedding_provider and (
            self.embedding_provider != "local"
            and self.embedding_provider not in SUPPORTED_LLM_PROVIDERS
        ):
            raise ValueError(
                f"Unsupported embedding_provider '{self.embedding_provider}'. "
                "Expected 'local' or a supported LLM provider."
            )
        if self.market_mode not in SUPPORTED_MARKET_MODES:
            raise ValueError(
                f"market_mode must be one of: {', '.join(SUPPORTED_MARKET_MODES)}"
            )
        if self.market_profile not in SUPPORTED_MARKET_PROFILES:
            raise ValueError(
                f"market_profile must be one of: {', '.join(SUPPORTED_MARKET_PROFILES)}"
            )
        bad_profiles = [item for item in self.market_profiles if item not in SUPPORTED_MARKET_PROFILES]
        if bad_profiles:
            raise ValueError(
                f"Unsupported market_profiles: {', '.join(bad_profiles)}. "
                f"Expected only: {', '.join(SUPPORTED_MARKET_PROFILES)}"
            )
        if self.market_mode == "single":
            self.market_profiles = [self.market_profile]
        elif self.market_profile not in self.market_profiles:
            self.market_profiles = [self.market_profile] + self.market_profiles
        if self.local_data_layout not in SUPPORTED_LOCAL_DATA_LAYOUTS:
            raise ValueError(
                f"local_data_layout must be one of: {', '.join(SUPPORTED_LOCAL_DATA_LAYOUTS)}"
            )
        if self.data_backend == "local" and not self.local_data_path:
            raise ValueError("local_data_path is required when data_backend='local'")
        return self

    @property
    def db_path(self) -> Path:
        return Path(self.results_dir) / "alpha_miner.db"


def provider_api_key(provider: str | None) -> str | None:
    provider_env = {
        "kimi": ("LLM_KEY", "KIMI_API_KEY"),
        "qwen": ("QWEN_API_KEY",),
        "claude": ("ClaudeCode_KEY", "ANTHROPIC_API_KEY"),
        "glm": ("GLM_KEY", "ZHIPU_API_KEY"),
        "openai": ("OpenAI_KEY", "OPENAI_API_KEY"),
        "deepseek": ("DEEPSEEK_API_KEY",),
        "openrouter": ("OPENROUTER_API_KEY",),
        "groq": ("GROQ_API_KEY",),
        "ollama": ("OLLAMA_API_KEY",),
        "vllm": ("VLLM_API_KEY",),
        "lmstudio": ("LMSTUDIO_API_KEY", "LM_STUDIO_API_KEY"),
    }
    if not provider:
        return None
    for env_name in provider_env.get(provider, ()):
        value = _normalize_str(os.getenv(env_name))
        if value:
            return value
    if provider == "ollama":
        return "ollama"
    if provider == "vllm":
        return "vllm"
    if provider == "lmstudio":
        return "lm-studio"
    return None


def detect_llm_provider() -> str | None:
    for provider in SUPPORTED_LLM_PROVIDERS:
        api_key = provider_api_key(provider)
        if api_key and api_key not in {"ollama", "vllm", "lm-studio"}:
            return provider
    return None


def build_settings(overrides: Mapping[str, Any] | None = None) -> AiminerSettings:
    load_dotenv()
    overrides = dict(overrides or {})

    provider = _normalize_str(overrides.get("llm_provider")) or detect_llm_provider()
    embedding_provider = _normalize_str(overrides.get("embedding_provider"))
    market_profile = _normalize_str(overrides.get("market_profile")) or "cn_stock"
    market_profiles = _coerce_list(overrides.get("market_profiles")) or [market_profile]
    data_backend = _normalize_str(overrides.get("data_backend"))
    if not data_backend:
        data_backend = (
            _normalize_str(overrides.get("evaluation_mode", overrides.get("mode")))
            or "ricequant"
        )

    payload = {
        "max_iterations": overrides.get("max_iterations", overrides.get("iterations", 1)),
        "evaluation_mode": _normalize_str(
            overrides.get("evaluation_mode", overrides.get("mode"))
        )
        or "ricequant",
        "evaluation_engine": _normalize_str(
            overrides.get("evaluation_engine", overrides.get("engine"))
        )
        or "pandas",
        "data_backend": data_backend,
        "llm_provider": provider,
        "llm_model": _normalize_str(overrides.get("llm_model")),
        "llm_base_url": _normalize_str(overrides.get("llm_base_url"))
        or _normalize_str(os.getenv("LLM_BASE_URL"))
        or _normalize_str(os.getenv("OPENAI_BASE_URL")),
        "embedding_provider": embedding_provider,
        "market_mode": _normalize_str(overrides.get("market_mode")) or "single",
        "market_profile": market_profile,
        "market_profiles": market_profiles,
        "local_data_path": _normalize_str(overrides.get("local_data_path")),
        "local_data_layout": _normalize_str(overrides.get("local_data_layout")) or "auto",
        "market_start": _normalize_str(overrides.get("market_start")),
        "market_end": _normalize_str(overrides.get("market_end")),
        "market_lookback": overrides.get("market_lookback", 60),
        "use_gpu": _coerce_bool(overrides.get("use_gpu"), default=False),
        "rebuild_rag": _coerce_bool(overrides.get("rebuild_rag"), default=False),
        "wiki_bootstrap": _coerce_bool(overrides.get("wiki_bootstrap"), default=False),
        "verbose": _coerce_bool(overrides.get("verbose"), default=False),
        "roles": overrides.get("roles"),
        "data_dir": _normalize_str(overrides.get("data_dir")) or "data",
        "results_dir": _normalize_str(overrides.get("results_dir")) or "results",
        "logs_dir": _normalize_str(overrides.get("logs_dir")) or "logs",
    }

    try:
        return AiminerSettings.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
