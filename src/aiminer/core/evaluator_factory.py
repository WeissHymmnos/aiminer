from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiminer.core.interfaces import BacktestBackend
from aiminer.core.market_profiles import get_market_profile


@dataclass(frozen=True)
class EvaluationConfig:
    data_backend: str
    evaluation_engine: str
    market_mode: str
    market_profile: str
    market_profiles: list[str]
    local_data_path: str | None = None
    local_data_layout: str = "auto"
    market_start: str | None = None
    market_end: str | None = None


def resolve_data_backend(value: str | None, *, evaluation_mode: str | None = None) -> str:
    backend = (value or evaluation_mode or "ricequant").strip().lower()
    aliases = {
        "rq": "ricequant",
        "local": "local",
        "csv": "local",
        "parquet": "local",
    }
    return aliases.get(backend, backend)


def evaluation_config_from_mapping(source: dict[str, Any] | Any) -> EvaluationConfig:
    get = source.get if isinstance(source, dict) else lambda name, default=None: getattr(source, name, default)
    market_profile = (get("market_profile") or "cn_stock").strip().lower()
    raw_profiles = get("market_profiles") or [market_profile]
    market_profiles = [str(item).strip().lower() for item in raw_profiles if str(item).strip()]
    market_profiles = [market_profile] + [item for item in market_profiles if item != market_profile]
    return EvaluationConfig(
        data_backend=resolve_data_backend(get("data_backend"), evaluation_mode=get("evaluation_mode")),
        evaluation_engine=(get("evaluation_engine") or "pandas").strip().lower(),
        market_mode=(get("market_mode") or "single").strip().lower(),
        market_profile=market_profile,
        market_profiles=market_profiles,
        local_data_path=get("local_data_path"),
        local_data_layout=(get("local_data_layout") or "auto").strip().lower(),
        market_start=get("market_start") or get("market_analysis_start_date"),
        market_end=get("market_end") or get("market_analysis_end_date"),
    )


def build_evaluator(
    *,
    factor_expressions: list[str],
    config: EvaluationConfig,
    test_start_date: str | None = None,
    test_end_date: str | None = None,
    daily_normalize: bool = True,
) -> BacktestBackend:
    profile = get_market_profile(config.market_profile)
    start_date = test_start_date or config.market_start or "2018-01-01"
    end_date = test_end_date or config.market_end or "2025-12-31"

    if config.data_backend == "ricequant":
        if config.market_mode == "mixed":
            raise ValueError("ricequant backend does not support mixed market mode.")
        if profile.name != "cn_stock":
            raise ValueError("ricequant backend currently supports cn_stock only.")
        from aiminer.core.alphaeval.rq_eval import RiceQuantEval

        return RiceQuantEval(
            factor_expressions=factor_expressions,
            test_start_date=start_date,
            test_end_date=end_date,
            market=profile.default_market,
            daily_normalize=daily_normalize,
            engine=config.evaluation_engine,
        )

    if config.data_backend == "qlib":
        if config.market_mode == "mixed":
            raise ValueError("qlib backend does not support mixed market mode yet.")
        if profile.name == "futures":
            raise ValueError("qlib backend does not support futures market_profile.")
        from aiminer.core.alphaeval.modeltester import AlphaEval

        return AlphaEval(
            factor_expressions=factor_expressions,
            test_start_date=start_date,
            test_end_date=end_date,
            daily_normalize=daily_normalize,
            market_profile=profile.name,
            qlib_market=profile.qlib_market,
            qlib_region=profile.qlib_region,
        )

    if config.data_backend == "local":
        if not config.local_data_path:
            raise ValueError("local backend requires local_data_path to be configured.")
        from aiminer.core.alphaeval.local_eval import LocalDataEval

        market_profiles = (
            config.market_profiles if config.market_mode in {"batch", "mixed"} else [config.market_profile]
        )
        market_name = (
            "LOCAL_MIXED" if config.market_mode == "mixed" else get_market_profile(market_profiles[0]).default_market
        )
        return LocalDataEval(
            factor_expressions=factor_expressions,
            test_start_date=start_date,
            test_end_date=end_date,
            market=market_name,
            daily_normalize=daily_normalize,
            engine=config.evaluation_engine,
            local_data_path=config.local_data_path,
            local_data_layout=config.local_data_layout,
            market_profile=config.market_profile,
            market_profiles=market_profiles,
            market_mode=config.market_mode,
        )

    raise ValueError(f"Unsupported data backend: {config.data_backend}")
