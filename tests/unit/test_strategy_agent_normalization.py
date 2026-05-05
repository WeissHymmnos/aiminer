from agents.strategy_agent import (
    candidate_to_strategy_config,
    normalize_strategy_candidate_payload,
)


def _state(**overrides):
    state = {
        "market_profile": "futures",
        "evaluation_engine": "pandas",
        "market_analysis_start_date": "2015-01-01",
        "market_analysis_end_date": "2020-12-01",
        "hypothesis_name": "test_factor",
    }
    state.update(overrides)
    return state


def _candidate(**overrides):
    payload = {
        "template_name": "llm_candidate",
        "strategy_mode": "time_series",
        "direction": "long_short",
        "selection_rule": "threshold",
        "rebalance_freq": "daily",
        "thresholds": {},
        "counts": {},
        "holding_constraints": {},
        "cost_model": {},
        "rationale": "test",
    }
    payload.update(overrides)
    return payload


def test_futures_strategy_aliases_are_normalized_before_config_validation():
    candidate = _candidate(
        strategy_mode="long_short",
        direction="both",
        selection_rule="quantile",
        rebalance_freq="biweekly",
        counts={"top_n": 10, "bottom_n": 0},
    )

    normalized = normalize_strategy_candidate_payload(candidate, _state())
    config = candidate_to_strategy_config(candidate, _state())

    assert normalized["strategy_mode"] == "time_series"
    assert normalized["direction"] == "long_short"
    assert normalized["selection_rule"] == "threshold"
    assert normalized["rebalance_freq"] == "weekly"
    assert normalized["counts"] == {"top_n": 10}
    assert config["long_threshold"] == 0.75
    assert config["short_threshold"] == 0.25
    assert config["bottom_n"] is None


def test_compact_longshort_aliases_are_normalized_for_futures():
    config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="longshort",
            direction="long_and_short",
            selection_rule="quantile",
        ),
        _state(),
    )

    assert config["strategy_mode"] == "time_series"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.75
    assert config["short_threshold"] == 0.25


def test_chinese_descriptive_time_series_candidate_is_normalized():
    candidate = _candidate(
        strategy_mode="\u8d8b\u52bf\u8ddf\u8e2a",
        direction="long",
        selection_rule=(
            "\u5f53\u6807\u51c6\u5316\u540e\u7684\u52a0\u901f\u5927\u4e8e0.5"
            "\u65f6\u505a\u591a\uff0c\u5c0f\u4e8e-0.5\u65f6\u505a\u7a7a"
        ),
        thresholds={"long_threshold": 0.5, "short_threshold": -0.5},
        counts={"bottom_n": 0},
    )

    config = candidate_to_strategy_config(candidate, _state())

    assert config["strategy_mode"] == "time_series"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.5
    assert config["short_threshold"] == -0.5
    assert config["bottom_n"] is None


def test_stock_cross_sectional_aliases_get_count_defaults():
    candidate = _candidate(
        strategy_mode="cross-section",
        direction="long",
        selection_rule="top",
        counts={},
    )

    config = candidate_to_strategy_config(candidate, _state(market_profile="cn_stock"))

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_only"
    assert config["selection_rule"] == "top_n"
    assert config["top_n"] == 20


def test_signal_and_ranking_strategy_mode_aliases_are_normalized():
    ts_config = candidate_to_strategy_config(
        _candidate(strategy_mode="signal", selection_rule="all"),
        _state(),
    )
    cs_config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="ranking",
            direction="long",
            selection_rule="top_bottom_n",
            counts={},
        ),
        _state(),
    )

    assert ts_config["strategy_mode"] == "time_series"
    assert ts_config["selection_rule"] == "threshold"
    assert ts_config["long_threshold"] == 0.75
    assert ts_config["short_threshold"] == 0.25
    assert cs_config["strategy_mode"] == "cross_sectional"
    assert cs_config["selection_rule"] == "top_bottom_n"
    assert cs_config["top_n"] == 20
    assert cs_config["bottom_n"] == 20


def test_simple_and_composite_modes_use_template_ts_cs_hints():
    ts_config = candidate_to_strategy_config(
        _candidate(
            template_name="price_volume_divergence_ts_percentile",
            strategy_mode="simple",
            direction="long_short",
            selection_rule="time_series_percentile",
            thresholds={"long_threshold": 0.8, "short_threshold": 0.2},
        ),
        _state(),
    )
    cs_config = candidate_to_strategy_config(
        _candidate(
            template_name="price_volume_divergence_cs_rank",
            strategy_mode="composite",
            direction="long_short",
            selection_rule="cross_sectional_rank",
            counts={},
        ),
        _state(),
    )

    assert ts_config["strategy_mode"] == "time_series"
    assert ts_config["selection_rule"] == "threshold"
    assert cs_config["strategy_mode"] == "cross_sectional"
    assert cs_config["selection_rule"] == "top_bottom_n"


def test_breakout_strategy_mode_alias_follows_market_default():
    futures_config = candidate_to_strategy_config(
        _candidate(
            template_name="volume_confirmed_breakout",
            strategy_mode="breakout",
            direction="long",
            selection_rule="threshold",
        ),
        _state(),
    )
    stock_config = candidate_to_strategy_config(
        _candidate(
            template_name="volume_confirmed_breakout",
            strategy_mode="breakout",
            direction="long",
            selection_rule="top_n",
            counts={},
        ),
        _state(market_profile="cn_stock"),
    )

    assert futures_config["strategy_mode"] == "time_series"
    assert futures_config["selection_rule"] == "threshold"
    assert stock_config["strategy_mode"] == "cross_sectional"
    assert stock_config["selection_rule"] == "top_n"


def test_threshold_and_ma_cross_strategy_mode_aliases_follow_market_default():
    configs = [
        candidate_to_strategy_config(
            _candidate(
                template_name=f"futures_momentum_{mode}",
                strategy_mode=mode,
                direction="long_short",
                selection_rule="threshold",
            ),
            _state(),
        )
        for mode in ("signal_threshold", "quantile_threshold", "ma_cross")
    ]

    for config in configs:
        assert config["strategy_mode"] == "time_series"
        assert config["selection_rule"] == "threshold"


def test_mixed_hybrid_strategy_mode_alias_follows_market_default():
    futures_config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_hybrid_factor",
            strategy_mode="mixed",
            direction="long_short",
            selection_rule="threshold",
        ),
        _state(),
    )
    stock_config = candidate_to_strategy_config(
        _candidate(
            template_name="stock_hybrid_factor",
            strategy_mode="hybrid",
            direction="long",
            selection_rule="top_n",
            counts={},
        ),
        _state(market_profile="cn_stock"),
    )

    assert futures_config["strategy_mode"] == "time_series"
    assert futures_config["selection_rule"] == "threshold"
    assert stock_config["strategy_mode"] == "cross_sectional"
    assert stock_config["selection_rule"] == "top_n"


def test_rank_based_strategy_mode_alias_is_cross_sectional():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_cross_sectional_rank",
            strategy_mode="rank_based",
            direction="long_short",
            selection_rule="cross_sectional_rank",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "top_bottom_n"


def test_long_high_short_low_and_top_bottom_aliases_are_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="ranking",
            direction="long_high_short_low",
            selection_rule="top_n_and_bottom_n",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "top_bottom_n"
    assert config["top_n"] == 20
    assert config["bottom_n"] == 20


def test_chinese_cross_sectional_selection_description_is_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule=(
                "\u9009\u62e9\u56e0\u5b50\u503c\u6700\u9ad8\u768420%"
                "\u54c1\u79cd\u505a\u591a\uff0c\u56e0\u5b50\u503c\u6700\u4f4e"
                "\u768420%\u54c1\u79cd\u505a\u7a7a"
            ),
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "top_bottom_n"
    assert config["top_n"] == 20
    assert config["bottom_n"] == 20


def test_cross_sectional_rank_percentile_selection_alias_is_threshold():
    config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="cross-sectional rank percentile",
            thresholds={"long_threshold": 0.8, "short_threshold": 0.2},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.8
    assert config["short_threshold"] == 0.2


def test_statistical_arbitrage_mode_alias_is_cross_sectional():
    config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="statistical_arbitrage",
            direction="long_short",
            selection_rule="top_n_and_bottom_n",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "top_bottom_n"


def test_cta_and_alpha_strategy_mode_aliases_are_normalized():
    cta_config = candidate_to_strategy_config(
        _candidate(
            template_name="TrendMomentum_TSZscore",
            strategy_mode="CTA",
            direction="long_short",
            selection_rule="threshold",
        ),
        _state(),
    )
    alpha_config = candidate_to_strategy_config(
        _candidate(
            template_name="TrendMomentum_CrossSectional",
            strategy_mode="Alpha",
            direction="long_short",
            selection_rule="cross_sectional_rank",
            counts={},
        ),
        _state(),
    )

    assert cta_config["strategy_mode"] == "time_series"
    assert cta_config["direction"] == "long_short"
    assert cta_config["selection_rule"] == "threshold"
    assert alpha_config["strategy_mode"] == "cross_sectional"
    assert alpha_config["direction"] == "long_short"
    assert alpha_config["selection_rule"] == "top_bottom_n"


def test_single_asset_strategy_mode_alias_is_time_series():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="momentum_acceleration_ts1",
            strategy_mode="single_asset",
            direction="bidirectional",
            selection_rule="threshold",
        ),
        _state(),
    )

    assert config["strategy_mode"] == "time_series"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"


def test_single_and_dual_leg_strategy_mode_aliases_follow_market_default():
    single_leg = candidate_to_strategy_config(
        _candidate(
            template_name="Long_on_high_alignment_momentum",
            strategy_mode="single_leg",
            direction="long_only",
            selection_rule="threshold",
        ),
        _state(),
    )
    dual_leg = candidate_to_strategy_config(
        _candidate(
            template_name="Long_short_alignment_momentum",
            strategy_mode="dual_leg",
            direction="long_short",
            selection_rule="threshold",
        ),
        _state(),
    )
    stock_dual_leg = candidate_to_strategy_config(
        _candidate(
            template_name="stock_dual_leg_rank",
            strategy_mode="dual_leg",
            direction="long_short",
            selection_rule="top_bottom",
            counts={},
        ),
        _state(market_profile="cn_stock"),
    )

    assert single_leg["strategy_mode"] == "time_series"
    assert single_leg["direction"] == "long_flat"
    assert dual_leg["strategy_mode"] == "time_series"
    assert dual_leg["direction"] == "long_short"
    assert stock_dual_leg["strategy_mode"] == "cross_sectional"
    assert stock_dual_leg["selection_rule"] == "top_bottom_n"


def test_template_hint_recovers_unknown_strategy_mode():
    time_series = candidate_to_strategy_config(
        _candidate(
            template_name="time_series_fixed_threshold",
            strategy_mode="threshold",
            direction="long_short",
            selection_rule="threshold",
        ),
        _state(),
    )
    cross_sectional = candidate_to_strategy_config(
        _candidate(
            template_name="cross_sectional_rank_signal",
            strategy_mode="rank_signal",
            direction="long_short",
            selection_rule="top_bottom",
            counts={},
        ),
        _state(),
    )

    assert time_series["strategy_mode"] == "time_series"
    assert time_series["selection_rule"] == "threshold"
    assert cross_sectional["strategy_mode"] == "cross_sectional"
    assert cross_sectional["selection_rule"] == "top_bottom_n"


def test_bare_threshold_strategy_mode_follows_market_default():
    futures_config = candidate_to_strategy_config(
        _candidate(
            template_name="volume_volatility_order_v1",
            strategy_mode="threshold",
            direction="long_short",
            selection_rule="threshold",
        ),
        _state(),
    )
    stock_config = candidate_to_strategy_config(
        _candidate(
            template_name="stock_volume_volatility_order_v1",
            strategy_mode="threshold",
            direction="long_short",
            selection_rule="top_bottom",
            counts={},
        ),
        _state(market_profile="cn_stock"),
    )

    assert futures_config["strategy_mode"] == "time_series"
    assert futures_config["selection_rule"] == "threshold"
    assert stock_config["strategy_mode"] == "cross_sectional"
    assert stock_config["selection_rule"] == "top_bottom_n"


def test_multi_instrument_long_short_alias_is_cross_sectional():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_volume_efficiency_top_bottom",
            strategy_mode="multi_long_short",
            direction="long_short",
            selection_rule="top_bottom",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "top_bottom_n"
    assert config["top_n"] == 20
    assert config["bottom_n"] == 20


def test_multi_asset_signal_aliases_follow_market_default():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="sharpe_acceleration_zscore_multi",
            strategy_mode="multi_asset",
            direction="long_short",
            selection_rule="signal",
        ),
        _state(),
    )

    assert config["strategy_mode"] == "time_series"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"


def test_numeric_direction_aliases_are_normalized():
    cross_sectional = candidate_to_strategy_config(
        _candidate(
            strategy_mode="multi_long_short",
            direction=1,
            selection_rule="top_bottom",
            counts={},
        ),
        _state(),
    )
    time_series = candidate_to_strategy_config(
        _candidate(
            strategy_mode="absolute_momentum",
            direction=0,
            selection_rule="threshold",
        ),
        _state(),
    )

    assert cross_sectional["strategy_mode"] == "cross_sectional"
    assert cross_sectional["direction"] == "long_short"
    assert cross_sectional["selection_rule"] == "top_bottom_n"
    assert time_series["strategy_mode"] == "time_series"
    assert time_series["direction"] == "long_flat"
    assert time_series["selection_rule"] == "threshold"


def test_string_numeric_direction_aliases_are_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="time_series_momentum",
            direction="-1",
            selection_rule="threshold",
            thresholds={"long_threshold": 0.2, "short_threshold": -0.2},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "time_series"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.2
    assert config["short_threshold"] == -0.2


def test_factor_direction_aliases_are_normalized():
    cross_sectional = candidate_to_strategy_config(
        _candidate(
            strategy_mode="ranking",
            direction="factor_long",
            selection_rule="top_volume",
            counts={},
        ),
        _state(),
    )
    time_series = candidate_to_strategy_config(
        _candidate(
            strategy_mode="absolute_signal",
            direction="factor_long",
            selection_rule="threshold",
        ),
        _state(),
    )
    inverse = candidate_to_strategy_config(
        _candidate(
            strategy_mode="absolute_signal",
            direction="factor_short",
            selection_rule="threshold",
        ),
        _state(),
    )
    positive = candidate_to_strategy_config(
        _candidate(
            template_name="time_series_long_only_high_threshold",
            strategy_mode="time_series",
            direction="positive",
            selection_rule="zscore",
        ),
        _state(),
    )
    negative = candidate_to_strategy_config(
        _candidate(
            template_name="time_series_short_only_extreme_low",
            strategy_mode="time_series",
            direction="negative",
            selection_rule="zscore",
        ),
        _state(),
    )
    two_sided = candidate_to_strategy_config(
        _candidate(
            strategy_mode="ranking",
            direction="factor_long_short",
            selection_rule="top_bottom",
            counts={},
        ),
        _state(),
    )

    assert cross_sectional["direction"] == "long_only"
    assert cross_sectional["selection_rule"] == "top_n"
    assert time_series["direction"] == "long_flat"
    assert inverse["direction"] == "long_short"
    assert positive["direction"] == "long_flat"
    assert negative["direction"] == "long_short"
    assert two_sided["direction"] == "long_short"


def test_high_score_long_direction_alias_is_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="trend_volume_composite_long_only",
            strategy_mode="cross_sectional",
            direction="long_high",
            selection_rule="top_volume",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_only"
    assert config["selection_rule"] == "top_n"
    assert config["top_n"] == 20


def test_top_long_direction_aliases_are_normalized():
    long_short = candidate_to_strategy_config(
        _candidate(
            strategy_mode="cross_sectional",
            direction="top_long_bottom_short",
            selection_rule="threshold",
            thresholds={},
        ),
        _state(),
    )
    long_only = candidate_to_strategy_config(
        _candidate(
            strategy_mode="cross_sectional",
            direction="top_long_only",
            selection_rule="top_n",
            counts={},
        ),
        _state(),
    )

    assert long_short["direction"] == "long_short"
    assert long_short["long_threshold"] == 0.75
    assert long_short["short_threshold"] == 0.25
    assert long_only["direction"] == "long_only"
    assert long_only["top_n"] == 20


def test_neutral_direction_alias_is_long_short():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_factor_momentum_neutral",
            strategy_mode="cross_sectional",
            direction="neutral",
            selection_rule="cross_sectional_rank",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "top_bottom_n"


def test_contrarian_direction_aliases_are_long_short():
    for alias in ("contrarian", "mean_reversion", "reversal", "counter_trend"):
        config = candidate_to_strategy_config(
            _candidate(
                strategy_mode="time_series",
                direction=alias,
                selection_rule="threshold",
            ),
            _state(),
        )

        assert config["direction"] == "long_short"


def test_descriptive_long_short_direction_aliases_are_normalized():
    for alias in (
        "long_on_positive_signal_short_on_negative",
        "long_top_decile_short_bottom_decile",
        "long_on_high_signal_short_on_low",
    ):
        config = candidate_to_strategy_config(
            _candidate(
                strategy_mode="time_series",
                direction=alias,
                selection_rule="threshold",
            ),
            _state(),
        )

        assert config["direction"] == "long_short"


def test_bidirectional_direction_alias_is_long_short():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_ts_momentum_volume_zscore",
            strategy_mode="CTA",
            direction="bidirectional",
            selection_rule="threshold",
        ),
        _state(),
    )

    assert config["strategy_mode"] == "time_series"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"


def test_both_legs_direction_alias_is_long_short():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="VolRatio_TZ_LongShort",
            strategy_mode="time_series",
            direction="both_legs",
            selection_rule="threshold",
        ),
        _state(),
    )

    assert config["strategy_mode"] == "time_series"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"


def test_cross_sectional_percentile_selection_alias_is_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_cross_sectional_vol_price_rank",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="cross_sectional_percentile",
            thresholds={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.75
    assert config["short_threshold"] == 0.25


def test_time_series_percentile_and_decile_selection_aliases_are_normalized():
    percentile = candidate_to_strategy_config(
        _candidate(
            template_name="futures_time_series_acceleration_volatility",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="time_series_percentile",
            thresholds={},
        ),
        _state(),
    )
    top_decile = candidate_to_strategy_config(
        _candidate(
            template_name="futures_directional_acceleration_volatility",
            strategy_mode="cross_sectional",
            direction="positive",
            selection_rule="time_series_top_decile",
            thresholds={},
        ),
        _state(),
    )

    assert percentile["strategy_mode"] == "cross_sectional"
    assert percentile["selection_rule"] == "threshold"
    assert percentile["long_threshold"] == 0.75
    assert percentile["short_threshold"] == 0.25
    assert top_decile["strategy_mode"] == "cross_sectional"
    assert top_decile["direction"] == "long_only"
    assert top_decile["selection_rule"] == "threshold"
    assert top_decile["long_threshold"] == 0.6


def test_cross_sectional_rank_selection_alias_is_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="cross_sectional_rank",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="cross_sectional_rank",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_short"
    assert config["selection_rule"] == "top_bottom_n"
    assert config["top_n"] == 20
    assert config["bottom_n"] == 20


def test_rank_threshold_selection_alias_is_normalized_to_threshold():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_cross_sectional_rank",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="rank_threshold",
            thresholds={"long_threshold": 0.8, "short_threshold": 0.2},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.8
    assert config["short_threshold"] == 0.2


def test_fractional_quantile_counts_are_mapped_to_thresholds():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_cross_sectional_quantile",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="top_bottom_n",
            counts={"quantile_long": 0.2, "quantile_short": 0.2},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.8
    assert config["short_threshold"] == 0.2
    assert config["top_n"] is None
    assert config["bottom_n"] is None


def test_quantile_threshold_selection_alias_is_normalized_to_threshold():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="cross_sectional_quantile",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="quantile_threshold",
            thresholds={"long_threshold": 0.8, "short_threshold": 0.2},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.8
    assert config["short_threshold"] == 0.2


def test_top_bottom_percent_selection_alias_is_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="CV_stability_rank_CS",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="top_bottom_percent",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["selection_rule"] == "top_bottom_n"
    assert config["top_n"] == 20
    assert config["bottom_n"] == 20


def test_top_metric_selection_alias_is_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            template_name="cs_volume_price_corr_rank_momentum",
            strategy_mode="cross_sectional",
            direction="long_only",
            selection_rule="top_volume",
            counts={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "cross_sectional"
    assert config["direction"] == "long_only"
    assert config["selection_rule"] == "top_n"
    assert config["top_n"] == 20


def test_strategy_family_names_use_template_mode_hint():
    cs_config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_cross_sectional_long_short",
            strategy_mode="price_volume_divergence",
            direction="long_short",
            selection_rule="rank",
            counts={},
        ),
        _state(),
    )
    ts_config = candidate_to_strategy_config(
        _candidate(
            template_name="futures_time_series_historical_percentile",
            strategy_mode="momentum_divergence",
            direction="long_and_short",
            selection_rule="rank",
        ),
        _state(),
    )

    assert cs_config["strategy_mode"] == "cross_sectional"
    assert cs_config["selection_rule"] == "top_bottom_n"
    assert cs_config["top_n"] == 20
    assert cs_config["bottom_n"] == 20
    assert ts_config["strategy_mode"] == "time_series"
    assert ts_config["selection_rule"] == "threshold"
    assert ts_config["direction"] == "long_short"


def test_absolute_mode_quantile_and_rq_rebalance_aliases_are_normalized():
    ts_config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="absolute",
            direction="long",
            selection_rule="top_quantile",
            rebalance_freq="W-MON",
            holding_constraints={
                "max_positions": 0,
                "max_weight_per_position": -0.1,
                "min_holding_days": 0,
            },
            cost_model={"commission_bps": -1, "slippage_bps": 2},
        ),
        _state(),
    )
    cs_config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="ranking",
            direction="long",
            selection_rule="top_quantile",
            rebalance_freq="M",
        ),
        _state(market_profile="cn_stock"),
    )
    daily_config = candidate_to_strategy_config(
        _candidate(rebalance_freq="D"),
        _state(),
    )

    assert ts_config["strategy_mode"] == "time_series"
    assert ts_config["selection_rule"] == "threshold"
    assert ts_config["rebalance_freq"] == "weekly"
    assert ts_config["max_weight_per_position"] == 0.1
    assert ts_config["min_holding_days"] == 1
    assert ts_config["commission_bps"] == 5.0
    assert ts_config["slippage_bps"] == 2.0
    assert cs_config["strategy_mode"] == "cross_sectional"
    assert cs_config["selection_rule"] == "top_n"
    assert cs_config["rebalance_freq"] == "monthly"
    assert daily_config["rebalance_freq"] == "daily"


def test_trading_day_rebalance_aliases_are_normalized():
    daily_config = candidate_to_strategy_config(
        _candidate(rebalance_freq="1_trading_day"),
        _state(),
    )
    weekly_config = candidate_to_strategy_config(
        _candidate(rebalance_freq="5_trading_days"),
        _state(),
    )
    monthly_config = candidate_to_strategy_config(
        _candidate(rebalance_freq="20_trading_days"),
        _state(),
    )

    assert daily_config["rebalance_freq"] == "daily"
    assert weekly_config["rebalance_freq"] == "weekly"
    assert monthly_config["rebalance_freq"] == "monthly"


def test_two_week_rebalance_aliases_are_normalized_to_weekly():
    for alias in ("biweek", "bi_week", "fortnightly", "2_weeks", "two_weeks"):
        config = candidate_to_strategy_config(
            _candidate(rebalance_freq=alias),
            _state(),
        )

        assert config["rebalance_freq"] == "weekly"


def test_absolute_momentum_by_thresholds_aliases_are_normalized():
    long_short = candidate_to_strategy_config(
        _candidate(
            template_name="time_series_momentum_divergence_long_short",
            strategy_mode="absolute_momentum",
            direction="long_short",
            selection_rule="by_thresholds",
            thresholds={"long_threshold": 0.2, "short_threshold": -0.2},
        ),
        _state(),
    )
    long_only = candidate_to_strategy_config(
        _candidate(
            template_name="time_series_momentum_divergence_long_only",
            strategy_mode="absolute_momentum",
            direction="long_only",
            selection_rule="by_thresholds",
            thresholds={"long_threshold": 0.2},
        ),
        _state(),
    )

    assert long_short["strategy_mode"] == "time_series"
    assert long_short["selection_rule"] == "threshold"
    assert long_short["direction"] == "long_short"
    assert long_short["long_threshold"] == 0.2
    assert long_short["short_threshold"] == -0.2
    assert long_only["strategy_mode"] == "time_series"
    assert long_only["selection_rule"] == "threshold"
    assert long_only["direction"] == "long_flat"


def test_time_series_prefixed_modes_and_absolute_threshold_are_normalized():
    mean_reversion = candidate_to_strategy_config(
        _candidate(
            template_name="Volume_Price_Correlation_Reversal_TS",
            strategy_mode="time_series_mean_reversion",
            direction="long_short",
            selection_rule="absolute_threshold",
            thresholds={"long_threshold": 0.3, "short_threshold": -0.3},
        ),
        _state(),
    )
    momentum = candidate_to_strategy_config(
        _candidate(
            template_name="Volume_Price_Correlation_Breakout_Long_TS",
            strategy_mode="time_series_momentum",
            direction="long_only",
            selection_rule="absolute_threshold",
            thresholds={"long_threshold": 0.4},
        ),
        _state(),
    )

    assert mean_reversion["strategy_mode"] == "time_series"
    assert mean_reversion["selection_rule"] == "threshold"
    assert mean_reversion["direction"] == "long_short"
    assert mean_reversion["long_threshold"] == 0.3
    assert mean_reversion["short_threshold"] == -0.3
    assert momentum["strategy_mode"] == "time_series"
    assert momentum["selection_rule"] == "threshold"
    assert momentum["direction"] == "long_flat"
    assert momentum["long_threshold"] == 0.4


def test_continuous_and_single_leg_mode_aliases_are_normalized():
    continuous = candidate_to_strategy_config(
        _candidate(
            template_name="ts_continuous_signal",
            strategy_mode="continuous",
            direction="long_only",
            selection_rule="continuous_signal",
            thresholds={"long_threshold": 0.1, "exit_threshold": 0.0},
        ),
        _state(),
    )
    single_short = candidate_to_strategy_config(
        _candidate(
            template_name="vol_price_corr_short_only",
            strategy_mode="single_short",
            direction="short_only",
            selection_rule="absolute_threshold",
            thresholds={"short_threshold": -0.2, "exit_threshold": 0.0},
        ),
        _state(),
    )

    assert continuous["strategy_mode"] == "time_series"
    assert continuous["selection_rule"] == "threshold"
    assert continuous["direction"] == "long_flat"
    assert continuous["long_threshold"] == 0.1
    assert single_short["strategy_mode"] == "time_series"
    assert single_short["selection_rule"] == "threshold"
    assert single_short["direction"] == "long_short"
    assert single_short["short_threshold"] == -0.2


def test_structured_rolling_rank_selection_rule_is_normalized():
    config = candidate_to_strategy_config(
        _candidate(
            strategy_mode="time_series",
            direction="long_short",
            selection_rule={
                "method": "rolling_rank",
                "long_threshold": 0.7,
                "short_threshold": 0.2,
            },
            thresholds={},
        ),
        _state(),
    )

    assert config["strategy_mode"] == "time_series"
    assert config["selection_rule"] == "threshold"
    assert config["long_threshold"] == 0.7
    assert config["short_threshold"] == 0.2
