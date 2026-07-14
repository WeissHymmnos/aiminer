from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


SUPPORTED_LLM_PROVIDERS = (
    "deepseek",
    "mimo",
    "kimi",
    "qwen",
    "claude",
    "glm",
    "openai",
    "openrouter",
    "groq",
    "ollama",
    "vllm",
    "lmstudio",
    "codex",
)
SUPPORTED_LLM_REASONING_EFFORTS = ("low", "medium", "high", "xhigh")

SUPPORTED_EVALUATION_MODES = ("qlib", "ricequant")
SUPPORTED_DATA_BACKENDS = ("qlib", "ricequant", "local")
SUPPORTED_MARKET_MODES = ("single", "batch", "mixed")
SUPPORTED_LOCAL_DATA_LAYOUTS = ("auto", "panel", "instrument_files")
SUPPORTED_MARKET_PROFILES = ("cn_stock", "us_stock", "futures")

PROVIDER_API_KEY_ENV = {
    "kimi": ("LLM_KEY", "KIMI_API_KEY"),
    "qwen": ("QWEN_API_KEY",),
    "claude": ("ClaudeCode_KEY", "ANTHROPIC_API_KEY"),
    "glm": ("GLM_KEY", "ZHIPU_API_KEY"),
    "openai": ("OpenAI_KEY", "OPENAI_API_KEY"),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "mimo": ("MIMO_API_KEY", "XIAOMI_API_KEY", "XIAOMIMIMO_API_KEY"),
    "openrouter": ("OPENROUTER_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "ollama": ("OLLAMA_API_KEY",),
    "vllm": ("VLLM_API_KEY",),
    "lmstudio": ("LMSTUDIO_API_KEY", "LM_STUDIO_API_KEY"),
}


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


def _contains_local_data_files(path: Path) -> bool:
    if path.is_file():
        return path.suffix.lower() in {".csv", ".parquet", ".pq"}
    if not path.is_dir():
        return False
    return any(
        child.is_file() and child.suffix.lower() in {".csv", ".parquet", ".pq"}
        for child in path.iterdir()
    )


def _default_local_data_path(data_dir: str, market_profile: str) -> str | None:
    data_root = Path(data_dir)
    candidates: list[Path] = []
    if market_profile == "futures":
        candidates.extend(
            [
                Path("../llm/data/local_futures/dominant/1d"),
                Path("../llm/data/local_futures/contracts/1d"),
                data_root / "local_futures" / "dominant" / "1d",
                data_root / "local_futures" / "contracts" / "1d",
                Path("src-tauri/resources/market_data/local_futures/dominant/1d"),
                Path("src-tauri/resources/market_data/local_futures/contracts/1d"),
                Path(
                    "local-dist/AIMiner.AppDir/usr/lib/app/market_data/"
                    "local_futures/dominant/1d"
                ),
                Path(
                    "local-dist/AIMiner.AppDir/usr/lib/app/market_data/"
                    "local_futures/contracts/1d"
                ),
            ]
        )
    else:
        candidates.extend(
            [
                data_root / f"local_{market_profile}",
                data_root / market_profile,
            ]
        )

    for candidate in candidates:
        expanded = candidate.expanduser()
        if _contains_local_data_files(expanded):
            return str(expanded)
    return None


class AiminerSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_iterations: int = Field(default=1, ge=1)
    evaluation_mode: str = "ricequant"
    evaluation_engine: str = "pandas"
    data_backend: str = "ricequant"
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_reasoning_effort: str | None = None
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
    disable_early_stop: bool = False
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
        if self.data_backend == "qlib" and self.evaluation_mode != "qlib":
            raise ValueError("data_backend='qlib' requires evaluation_mode='qlib'")
        if self.data_backend in {"ricequant", "local"} and self.evaluation_mode != "ricequant":
            raise ValueError(
                f"data_backend='{self.data_backend}' requires evaluation_mode='ricequant'"
            )
        if self.llm_provider and self.llm_provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"Unsupported llm_provider '{self.llm_provider}'. "
                f"Expected one of: {', '.join(SUPPORTED_LLM_PROVIDERS)}"
            )
        if self.llm_reasoning_effort:
            self.llm_reasoning_effort = self.llm_reasoning_effort.strip().lower()
            if self.llm_reasoning_effort not in SUPPORTED_LLM_REASONING_EFFORTS:
                raise ValueError(
                    "llm_reasoning_effort must be one of: "
                    f"{', '.join(SUPPORTED_LLM_REASONING_EFFORTS)}"
                )
        if self.embedding_provider and (
            self.embedding_provider != "local"
            and self.embedding_provider not in SUPPORTED_LLM_PROVIDERS
        ):
            raise ValueError(
                f"Unsupported embedding_provider '{self.embedding_provider}'. "
                "Expected 'local' or a supported LLM provider."
            )
        if self.embedding_provider == "codex":
            raise ValueError("embedding_provider='codex' is not supported; use local or an embedding API provider.")
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
        if self.data_backend == "ricequant":
            if self.market_mode == "mixed":
                raise ValueError("ricequant backend does not support market_mode='mixed'")
            if any(profile != "cn_stock" for profile in self.market_profiles):
                raise ValueError("ricequant backend currently supports cn_stock only")
        if self.data_backend == "qlib":
            if self.market_mode == "mixed":
                raise ValueError("qlib backend does not support market_mode='mixed'")
            if any(profile == "futures" for profile in self.market_profiles):
                raise ValueError("qlib backend does not support futures market_profile")
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

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def results_path(self) -> Path:
        return Path(self.results_dir)

    @property
    def logs_path(self) -> Path:
        return Path(self.logs_dir)

    @property
    def wiki_dir(self) -> Path:
        return self.data_path / "wiki_vault"

    @property
    def swarm_run_dir(self) -> Path:
        return self.results_path / "swarm_runs"

    @property
    def manual_dir(self) -> Path:
        return self.results_path / "manual"

    @property
    def strategy_dir(self) -> Path:
        return self.results_path / "strategies"

    @property
    def chart_dir(self) -> Path:
        return self.results_path / "charts"

    @property
    def report_dir(self) -> Path:
        return self.results_path / "reports"


def provider_api_key(provider: str | None) -> str | None:
    if not provider:
        return None
    for env_name in PROVIDER_API_KEY_ENV.get(provider, ()):
        value = _normalize_str(os.getenv(env_name))
        if value:
            return value
    if provider == "mimo":
        value = _claudecode_mimo_token()
        if value:
            return value
    if provider == "ollama":
        return "ollama"
    if provider == "vllm":
        return "vllm"
    if provider == "lmstudio":
        return "lm-studio"
    if provider == "codex":
        from aiminer.core.codex_llm import is_codex_available

        return "codex" if is_codex_available() else None
    return None


def _claudecode_mimo_token() -> str | None:
    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    env = payload.get("env") if isinstance(payload, dict) else None
    if not isinstance(env, dict):
        return None
    return _normalize_str(env.get("ANTHROPIC_AUTH_TOKEN"))


def detect_llm_provider() -> str | None:
    for provider in SUPPORTED_LLM_PROVIDERS:
        if provider == "codex":
            continue
        api_key = None
        for env_name in PROVIDER_API_KEY_ENV.get(provider, ()):
            api_key = _normalize_str(os.getenv(env_name))
            if api_key:
                break
        if api_key and api_key not in {"ollama", "vllm", "lm-studio"}:
            return provider
    return None


def build_settings(overrides: Mapping[str, Any] | None = None) -> AiminerSettings:
    load_dotenv()
    overrides = dict(overrides or {})

    provider = _normalize_str(overrides.get("llm_provider")) or detect_llm_provider()
    embedding_provider = _normalize_str(overrides.get("embedding_provider"))
    data_backend = _normalize_str(overrides.get("data_backend"))
    if not data_backend:
        data_backend = (
            _normalize_str(overrides.get("evaluation_mode", overrides.get("mode")))
            or "ricequant"
        )
    data_dir = (
        _normalize_str(overrides.get("data_dir"))
        or _normalize_str(os.getenv("AIMINER_DATA_DIR"))
        or "data"
    )
    explicit_market_profile = _normalize_str(overrides.get("market_profile"))
    market_profile = explicit_market_profile or "cn_stock"
    local_data_path = (
        _normalize_str(overrides.get("local_data_path"))
        or _normalize_str(os.getenv("AIMINER_LOCAL_DATA_PATH"))
        or _normalize_str(os.getenv("AIMINER_LOCAL_FUTURES_PATH"))
    )
    if data_backend == "local" and not local_data_path:
        if explicit_market_profile:
            local_data_path = _default_local_data_path(data_dir, explicit_market_profile)
        else:
            for candidate_profile in ("futures", "cn_stock", "us_stock"):
                local_data_path = _default_local_data_path(data_dir, candidate_profile)
                if local_data_path:
                    market_profile = candidate_profile
                    break
    market_profiles = _coerce_list(overrides.get("market_profiles")) or [market_profile]

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
        "llm_reasoning_effort": _normalize_str(overrides.get("llm_reasoning_effort"))
        or _normalize_str(os.getenv("AIMINER_CODEX_REASONING_EFFORT"))
        or _normalize_str(os.getenv("AIMINER_LLM_REASONING_EFFORT")),
        "embedding_provider": embedding_provider,
        "market_mode": _normalize_str(overrides.get("market_mode")) or "single",
        "market_profile": market_profile,
        "market_profiles": market_profiles,
        "local_data_path": local_data_path,
        "local_data_layout": _normalize_str(overrides.get("local_data_layout")) or "auto",
        "market_start": _normalize_str(overrides.get("market_start")),
        "market_end": _normalize_str(overrides.get("market_end")),
        "market_lookback": overrides.get("market_lookback", 60),
        "use_gpu": _coerce_bool(overrides.get("use_gpu"), default=False),
        "rebuild_rag": _coerce_bool(overrides.get("rebuild_rag"), default=False),
        "wiki_bootstrap": _coerce_bool(overrides.get("wiki_bootstrap"), default=False),
        "disable_early_stop": _coerce_bool(
            overrides.get("disable_early_stop")
            or os.getenv("AIMINER_DISABLE_EARLY_STOP"),
            default=False,
        ),
        "verbose": _coerce_bool(overrides.get("verbose"), default=False),
        "roles": overrides.get("roles"),
        "data_dir": data_dir,
        "results_dir": _normalize_str(overrides.get("results_dir"))
        or _normalize_str(os.getenv("AIMINER_RESULTS_DIR"))
        or "results",
        "logs_dir": _normalize_str(overrides.get("logs_dir"))
        or _normalize_str(os.getenv("AIMINER_LOG_DIR"))
        or _normalize_str(os.getenv("AIMINER_LOGS_DIR"))
        or "logs",
    }

    try:
        return AiminerSettings.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
