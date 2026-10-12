"""Unit tests for factor orthogonalization and incremental IC calculation."""

import numpy as np
import pandas as pd
import pytest

from aiminer.core.orthogonalization import (
    compute_cross_sectional_factor_correlation,
    compute_incremental_ic,
)


@pytest.fixture
def sample_factor_data():
    np.random.seed(42)
    dates = pd.date_range("2021-01-01", periods=50)
    instruments = [f"stock_{i:02d}" for i in range(20)]
    idx = pd.MultiIndex.from_product(
        [dates, instruments], names=["datetime", "instrument"]
    )
    n = len(idx)

    base = np.random.randn(n)
    signal = base * 0.5 + np.random.randn(n) * 0.5
    label = signal * 0.4 + np.random.randn(n) * 0.6

    # Collinear factor (nearly 100% correlated with base)
    collinear = base * 2.0 + np.random.randn(n) * 0.001

    # Truly orthogonal factor
    orthogonal = np.random.randn(n)
    label += orthogonal * 0.5

    f_base = pd.Series(base, index=idx)
    f_collinear = pd.Series(collinear, index=idx)
    f_orthogonal = pd.Series(orthogonal, index=idx)
    labels = pd.Series(label, index=idx)

    return f_base, f_collinear, f_orthogonal, labels


def test_cross_sectional_factor_correlation(sample_factor_data):
    f_base, f_collinear, f_orthogonal, _ = sample_factor_data

    corr_high = compute_cross_sectional_factor_correlation(f_base, f_collinear)
    assert corr_high is not None
    assert corr_high > 0.95

    corr_low = compute_cross_sectional_factor_correlation(f_base, f_orthogonal)
    assert corr_low is not None
    assert abs(corr_low) < 0.15


def test_incremental_ic_redundant_factor(sample_factor_data):
    f_base, f_collinear, _, labels = sample_factor_data

    inc_ic, raw_ic = compute_incremental_ic(
        new_factor=f_collinear,
        existing_factors=[f_base],
        labels=labels,
    )
    assert inc_ic is not None
    assert raw_ic is not None
    # Raw IC has meaningful predictive power
    assert abs(raw_ic) > 0.10
    # Incremental IC should be dramatically culled compared to raw IC
    assert abs(inc_ic) < 0.05
    assert abs(inc_ic) < abs(raw_ic) * 0.25


def test_incremental_ic_orthogonal_factor(sample_factor_data):
    f_base, _, f_orthogonal, labels = sample_factor_data

    inc_ic, raw_ic = compute_incremental_ic(
        new_factor=f_orthogonal,
        existing_factors=[f_base],
        labels=labels,
    )
    assert inc_ic is not None
    assert raw_ic is not None
    # Orthogonal factor adds real independent predictive power
    assert abs(inc_ic) > 0.05
    assert abs(inc_ic - raw_ic) < 0.05  # Since it's orthogonal, inc_ic ~ raw_ic


def test_incremental_ic_no_existing_factors(sample_factor_data):
    f_base, _, _, labels = sample_factor_data

    inc_ic, raw_ic = compute_incremental_ic(
        new_factor=f_base,
        existing_factors=[],
        labels=labels,
    )
    assert inc_ic is not None
    assert raw_ic is not None
    assert np.isclose(inc_ic, raw_ic)
