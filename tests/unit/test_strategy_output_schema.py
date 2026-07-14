import json

from aiminer.schemas.messages import RefinementProposalOutput, StrategyProposalBatchOutput


def _candidate_payload(**overrides):
    payload = {
        "template_name": "cs_top_bottom_weekly",
        "strategy_mode": "cross_sectional",
        "direction": "long_short",
        "selection_rule": "top_bottom_n",
        "rebalance_freq": "weekly",
        "thresholds": {},
        "counts": {"top_n": 30, "bottom_n": 30},
        "holding_constraints": {
            "max_positions": 60,
            "max_weight_per_position": 0.04,
            "min_holding_days": 3,
        },
        "cost_model": {"commission_bps": 5.0, "slippage_bps": 5.0},
        "rationale": "Weekly rebalance to cut turnover.",
    }
    payload.update(overrides)
    return payload


def test_strategy_batch_accepts_null_optional_strategy_dicts():
    payload = {
        "execution_style": "cs_long_short",
        "candidates": [
            _candidate_payload(
                thresholds=None,
                counts={"top_n": 30, "bottom_n": None},
                holding_constraints={"max_positions": None, "min_holding_days": 3},
                cost_model=None,
            )
        ],
    }

    parsed = StrategyProposalBatchOutput.model_validate_json(json.dumps(payload))
    candidate = parsed.candidates[0]

    assert candidate.thresholds == {}
    assert candidate.counts == {"top_n": 30}
    assert candidate.holding_constraints == {"min_holding_days": 3}
    assert candidate.cost_model == {}


def test_strategy_batch_coerces_scalar_enum_fields_from_numbers():
    payload = {
        "execution_style": "cs_long_short",
        "candidates": [
            _candidate_payload(
                template_name=123,
                strategy_mode=0,
                direction=1,
                selection_rule=0,
                rebalance_freq=1,
                rationale=456,
            )
        ],
    }

    parsed = StrategyProposalBatchOutput.model_validate_json(json.dumps(payload))
    candidate = parsed.candidates[0]

    assert candidate.template_name == "123"
    assert candidate.strategy_mode == "0"
    assert candidate.direction == "1"
    assert candidate.selection_rule == "0"
    assert candidate.rebalance_freq == "1"
    assert candidate.rationale == "456"


def test_strategy_batch_drops_nested_optional_dict_values():
    payload = {
        "execution_style": "cs_long_short",
        "candidates": [
            _candidate_payload(
                thresholds={
                    "long_threshold": 0.75,
                    "ma_periods": {"short": 20, "long": 50},
                },
                counts={"top_n": 30, "buckets": [1, 2, 3]},
                holding_constraints={"max_positions": 60, "weights": {"max": 0.04}},
                cost_model={"commission_bps": 5.0, "tiers": [{"bps": 3.0}]},
            )
        ],
    }

    parsed = StrategyProposalBatchOutput.model_validate_json(json.dumps(payload))
    candidate = parsed.candidates[0]

    assert candidate.thresholds == {"long_threshold": 0.75}
    assert candidate.counts == {"top_n": 30}
    assert candidate.holding_constraints == {"max_positions": 60}
    assert candidate.cost_model == {"commission_bps": 5.0}


def test_strategy_batch_drops_non_numeric_optional_dict_values():
    payload = {
        "execution_style": "ts_threshold",
        "candidates": [
            _candidate_payload(
                strategy_mode="time_series",
                selection_rule="threshold",
                thresholds={
                    "long_threshold": "0.75",
                    "additional_long_confirmation": "close > sma20",
                },
                counts={"top_n": "30", "bucket": "highest_decile"},
                holding_constraints={"max_positions": "60", "note": "liquid only"},
                cost_model={"commission_bps": "5.0", "slippage": "low"},
            )
        ],
    }

    parsed = StrategyProposalBatchOutput.model_validate_json(json.dumps(payload))
    candidate = parsed.candidates[0]

    assert candidate.thresholds == {"long_threshold": 0.75}
    assert candidate.counts == {"top_n": 30}
    assert candidate.holding_constraints == {"max_positions": 60}
    assert candidate.cost_model == {"commission_bps": 5.0}


def test_strategy_batch_accepts_fractional_quantile_counts():
    payload = {
        "execution_style": "cs_long_short",
        "candidates": [
            _candidate_payload(
                counts={"quantile_long": 0.2, "quantile_short": 0.2},
            )
        ],
    }

    parsed = StrategyProposalBatchOutput.model_validate_json(json.dumps(payload))
    candidate = parsed.candidates[0]

    assert candidate.counts == {"quantile_long": 0.2, "quantile_short": 0.2}


def test_strategy_batch_accepts_structured_selection_rule():
    payload = {
        "execution_style": "ts_threshold",
        "candidates": [
            _candidate_payload(
                strategy_mode="time_series",
                selection_rule={
                    "method": "rolling_rank",
                    "long_threshold": 0.7,
                    "short_threshold": 0.2,
                },
                thresholds={},
            )
        ],
    }

    parsed = StrategyProposalBatchOutput.model_validate_json(json.dumps(payload))
    candidate = parsed.candidates[0]

    assert candidate.selection_rule == {
        "method": "rolling_rank",
        "long_threshold": 0.7,
        "short_threshold": 0.2,
    }


def test_refinement_output_accepts_null_optional_strategy_dicts():
    payload = {
        "failure_modes": ["high_turnover"],
        "should_continue": True,
        "rationale": "Reduce trading frequency.",
        "proposals": [
            _candidate_payload(
                thresholds={"long_threshold": None, "short_threshold": 0.2},
                counts=None,
            )
        ],
    }

    parsed = RefinementProposalOutput.model_validate_json(json.dumps(payload))
    candidate = parsed.proposals[0]

    assert candidate.thresholds == {"short_threshold": 0.2}
    assert candidate.counts == {}
