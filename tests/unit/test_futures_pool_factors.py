"""Gating test: every strategy factor exists in the live non-simulated pool."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiminer.core.futures_super import (
    assert_factors_in_pool,
    load_pool_factors,
    select_strategy_factors,
)

HAS_LIVE_POOL = (
    Path("results/alpha_miner.db").exists()
    or Path("results/alpha_pool.json").exists()
)
pytestmark = pytest.mark.skipif(
    not HAS_LIVE_POOL, reason="Requires live alpha factor pool on disk"
)


def test_delayed_ic_candidates_are_live_pool_members():
    pool = load_pool_factors()
    # Wide unique net used as the delayed-IC screen universe.
    candidates = select_strategy_factors(
        pool, max_factors=48, max_per_family=48
    )
    assert candidates
    checked = assert_factors_in_pool(candidates)
    assert {f.factor_id for f in checked} == {f.factor_id for f in candidates}
    assert all(f.is_simulated == 0 for f in checked)


def test_selected_factors_exist_in_non_simulated_pool():
    pool = load_pool_factors()
    assert pool, "expected a non-empty live futures pool"
    assert all(f.is_simulated == 0 for f in pool)
    assert all(f.market_profile == "futures" for f in pool)

    selected = select_strategy_factors(pool, max_factors=16)
    assert selected
    checked = assert_factors_in_pool(selected)
    assert [f.factor_id for f in checked] == [f.factor_id for f in selected]

    db = Path("results/alpha_miner.db")
    assert db.exists()
    ids = {f.factor_id for f in pool}
    for factor in selected:
        assert factor.factor_id in ids
        assert factor.is_simulated == 0
        assert factor.expression.strip()
