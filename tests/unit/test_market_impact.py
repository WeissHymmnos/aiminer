from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aiminer.core.alphaeval.market_impact import (
    FixedCostImpactModel,
    LinearParticipationImpactModel,
    SquareRootImpactModel,
    build_impact_model,
)
from aiminer.core.alphaeval.rq_eval import RiceQuantEval
from aiminer.core.evaluator_factory import (
    EvaluationConfig,
    evaluation_config_from_mapping,
)


def _make_dummy_weights_and_data():
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    insts = ["A", "B"]
    idx = pd.MultiIndex.from_product(
        [dates, insts], names=["datetime", "instrument"]
    )
    raw = pd.DataFrame(
        {
            "close": [10.0, 20.0] * 10,
            "volume": [100000.0, 50000.0] * 10,
            "total_turnover": [1000000.0, 1000000.0] * 10,
        },
        index=idx,
    )

    # Alternate long/short weights to create turnover
    w_data = {
        "A": [0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5],
        "B": [-0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5],
    }
    weights = pd.DataFrame(w_data, index=dates)

    label_mat = pd.DataFrame(
        {
            "A": [0.01] * 10,
            "B": [-0.01] * 10,
        },
        index=dates,
    )
    return weights, raw, label_mat


def test_fixed_cost_impact_model():
    weights, raw, label = _make_dummy_weights_and_data()
    model = FixedCostImpactModel(cost_bps=10.0)
    drag, cost_matrix = model.compute_drag(weights, raw, label)

    assert len(drag) == len(weights)
    assert drag.iloc[0] == 0.0  # Day 0 diff is 0
    # Day 1: A changes 1.0, B changes 1.0 -> sum(|dw|) = 2.0 -> turnover = 1.0
    # drag = 1.0 * 10 / 10000 = 0.001
    assert np.isclose(drag.iloc[1], 0.001)
    assert np.isclose(cost_matrix.iloc[0, 0], 0.001)


def test_square_root_impact_model_scales_with_participation():
    weights, raw, label = _make_dummy_weights_and_data()

    # Small portfolio value -> low participation -> lower impact
    small_model = SquareRootImpactModel(
        base_cost_bps=5.0,
        impact_gamma=0.2,
        portfolio_value=1e5,
    )
    small_drag, _ = small_model.compute_drag(weights, raw, label)

    # Large portfolio value -> higher participation -> higher impact
    large_model = SquareRootImpactModel(
        base_cost_bps=5.0,
        impact_gamma=0.2,
        portfolio_value=5e6,
    )
    large_drag, _ = large_model.compute_drag(weights, raw, label)

    assert (large_drag.iloc[1:] >= small_drag.iloc[1:]).all()
    assert large_drag.sum() > small_drag.sum()


def test_linear_impact_model():
    weights, raw, label = _make_dummy_weights_and_data()
    model = LinearParticipationImpactModel(
        base_cost_bps=5.0,
        impact_gamma=0.1,
        portfolio_value=1e6,
    )
    drag, rates = model.compute_drag(weights, raw, label)
    assert len(drag) == len(weights)
    assert drag.iloc[1] > 0.0005  # Greater than base 5 bps


def test_build_impact_model_factory():
    fixed = build_impact_model("fixed", cost_bps=4.0)
    assert isinstance(fixed, FixedCostImpactModel)
    assert fixed.cost_bps == 4.0

    sqrt_m = build_impact_model("square_root", cost_bps=5.0, impact_gamma=0.15)
    assert isinstance(sqrt_m, SquareRootImpactModel)
    assert sqrt_m.impact_gamma == 0.15

    lin_m = build_impact_model("linear", cost_bps=5.0)
    assert isinstance(lin_m, LinearParticipationImpactModel)

    with pytest.raises(ValueError, match="Unsupported market impact model"):
        build_impact_model("unknown_model")


def test_rq_eval_integration_with_impact_model():
    evaluator = RiceQuantEval(
        factor_expressions=["Mean($close, 5)"],
        test_start_date="2024-01-01",
        test_end_date="2024-01-10",
        cost_bps=5.0,
        slippage_model="square_root",
        impact_gamma=0.2,
        skip_auth=True,
    )
    assert isinstance(evaluator.impact_model, SquareRootImpactModel)

    # Fabricate raw data and factor data for PnL run
    weights, raw, label = _make_dummy_weights_and_data()
    evaluator.raw_data = raw

    idx = weights.stack().index
    idx.names = ["datetime", "instrument"]
    all_data = pd.DataFrame(
        {
            "factor": weights.stack().values,
            "label": label.stack().values,
        },
        index=idx,
    )

    net_returns = evaluator.calculate_pnl(all_data)
    assert not net_returns.empty
    assert hasattr(evaluator, "effective_cost_bps")
    assert evaluator.effective_cost_bps >= 5.0
    assert evaluator.total_cost_drag > 0.0


def test_evaluator_factory_config_parsing():
    cfg = evaluation_config_from_mapping(
        {
            "data_backend": "local",
            "slippage_model": "square_root",
            "impact_gamma": 0.25,
            "portfolio_value": 2e7,
        }
    )
    assert cfg.slippage_model == "square_root"
    assert cfg.impact_gamma == 0.25
    assert cfg.portfolio_value == 2e7


def test_market_impact_flat_raw_data():
    model = SquareRootImpactModel(base_cost_bps=5.0, portfolio_value=1e6)
    weights = pd.DataFrame(
        {"AAPL": [0.5, 0.5]},
        index=pd.date_range("2024-01-01", periods=2),
    )
    flat_raw = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=2),
            "instrument": ["AAPL", "AAPL"],
            "close": [100.0, 101.0],
            "volume": [10000.0, 12000.0],
            "total_turnover": [1000000.0, 1212000.0],
        }
    )
    drag, rates = model.compute_drag(weights, raw_data=flat_raw)
    assert len(drag) == 2
    assert not drag.isna().any()


def test_market_impact_zero_volume_illiquid_asset():
    model = SquareRootImpactModel(base_cost_bps=5.0, portfolio_value=1e6)
    weights = pd.DataFrame(
        {"ILLIQ": [0.2, 0.4]},
        index=pd.date_range("2024-01-01", periods=2),
    )
    raw = pd.DataFrame(
        {
            "close": [10.0, 10.0],
            "volume": [0.0, 0.0],
            "total_turnover": [0.0, 0.0],
        },
        index=pd.MultiIndex.from_product(
            [pd.date_range("2024-01-01", periods=2), ["ILLIQ"]],
            names=["datetime", "instrument"],
        ),
    )
    drag, rates = model.compute_drag(weights, raw_data=raw)
    assert len(drag) == 2
    assert not drag.isna().any()
    assert np.isfinite(drag.iloc[1])

