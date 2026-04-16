from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketProfile:
    name: str
    asset_class: str
    default_market: str
    qlib_region: str | None = None
    qlib_market: str | None = None


MARKET_PROFILES: dict[str, MarketProfile] = {
    "cn_stock": MarketProfile(
        name="cn_stock",
        asset_class="stock",
        default_market="000300.XSHG",
        qlib_region="cn",
        qlib_market="csi300",
    ),
    "us_stock": MarketProfile(
        name="us_stock",
        asset_class="stock",
        default_market="SPY",
        qlib_region="us",
        qlib_market="sp500",
    ),
    "futures": MarketProfile(
        name="futures",
        asset_class="futures",
        default_market="LOCAL_FUTURES",
    ),
}


def get_market_profile(name: str | None) -> MarketProfile:
    key = (name or "cn_stock").strip().lower()
    if key not in MARKET_PROFILES:
        supported = ", ".join(sorted(MARKET_PROFILES))
        raise ValueError(f"Unsupported market_profile '{name}'. Expected one of: {supported}")
    return MARKET_PROFILES[key]
