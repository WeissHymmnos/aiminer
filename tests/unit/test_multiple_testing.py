"""Unit tests for Deflated Sharpe Ratio (DSR) and multiple testing helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

import numpy as np
import pytest

from aiminer.core.alphaeval.multiple_testing import (
    adjust_pvalues_holm,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    holm_bonferroni,
    probabilistic_sharpe_ratio,
    select_factors_holm,
)
from aiminer.manager import PortfolioManager
from aiminer.pool_io import (
    ensure_alpha_pool_schema,
    load_alpha_pool_rows,
    persist_alpha_pool_rows,
)


class TestExpectedMaxSharpe:
    def test_single_or_zero_trials(self):
        assert expected_max_sharpe(1) == 0.0
        assert expected_max_sharpe(0) == 0.0
        assert expected_max_sharpe(-5) == 0.0

    def test_monotonic_increase(self):
        trials = [2, 5, 10, 20, 50, 100, 500]
        values = [expected_max_sharpe(n) for n in trials]
        for a, b in zip(values, values[1:]):
            assert b > a, f"Expected {b} > {a}"

    def test_methods_consistency(self):
        for n in [10, 50, 100]:
            bp = expected_max_sharpe(n, method="bailey_prado")
            ev = expected_max_sharpe(n, method="extreme_value")
            assert bp > 0.0
            assert ev > 0.0
            # Both should be positive and within reasonable bounds
            assert abs(bp - ev) < 2.0


class TestProbabilisticSharpeRatio:
    def test_benchmark_equality(self):
        # When SR == benchmark and skew=0, kurt=3, PSR is exactly 0.5
        psr = probabilistic_sharpe_ratio(
            estimated_sharpe=0.5,
            sr_benchmark=0.5,
            skewness=0.0,
            kurtosis=3.0,
            sample_length=252,
        )
        assert pytest.approx(psr, abs=1e-5) == 0.5

    def test_higher_sharpe_gives_higher_psr(self):
        psr_low = probabilistic_sharpe_ratio(
            estimated_sharpe=0.2, sr_benchmark=0.0
        )
        psr_high = probabilistic_sharpe_ratio(
            estimated_sharpe=0.8, sr_benchmark=0.0
        )
        assert 0.5 < psr_low < psr_high <= 1.0

    def test_negative_skewness_penalizes_psr(self):
        psr_sym = probabilistic_sharpe_ratio(
            estimated_sharpe=0.5,
            sr_benchmark=0.0,
            skewness=0.0,
            kurtosis=3.0,
        )
        psr_neg_skew = probabilistic_sharpe_ratio(
            estimated_sharpe=0.5,
            sr_benchmark=0.0,
            skewness=-1.0,
            kurtosis=3.0,
        )
        assert psr_sym > psr_neg_skew

    def test_nan_handling(self):
        psr = probabilistic_sharpe_ratio(float("nan"))
        assert np.isnan(psr)


class TestDeflatedSharpeRatio:
    def test_dsr_monotonic_decrease_with_n_trials(self):
        """Requirement: Test DSR monotonic decrease with increasing n_trials."""
        sr = 0.8
        var_sr = 0.25  # std = 0.5
        trial_counts = [1, 2, 5, 10, 20, 50, 100]
        dsr_values = [
            deflated_sharpe_ratio(
                estimated_sharpe=sr,
                var_sharpe_or_trials=var_sr,
                n_trials=n,
                sample_length=252,
            )
            for n in trial_counts
        ]

        # Verify strict or non-strict monotonic decrease across trial counts
        for i in range(len(dsr_values) - 1):
            assert dsr_values[i] >= dsr_values[i + 1], (
                f"DSR at N={trial_counts[i]} ({dsr_values[i]:.6f}) should be "
                f">= DSR at N={trial_counts[i+1]} ({dsr_values[i+1]:.6f})"
            )
        # N=1 should be strictly greater than N=100
        assert dsr_values[0] > dsr_values[-1]

    def test_dsr_with_trial_sequence(self):
        trials = [0.1, 0.4, 0.6, 0.2, 0.5, 0.3, 0.7, 0.0]
        dsr = deflated_sharpe_ratio(
            estimated_sharpe=0.8,
            var_sharpe_or_trials=trials,
        )
        assert 0.0 <= dsr <= 1.0

    def test_dsr_single_trial_equals_psr(self):
        psr = probabilistic_sharpe_ratio(0.5, sr_benchmark=0.0)
        dsr = deflated_sharpe_ratio(
            0.5, var_sharpe_or_trials=0.0, n_trials=1
        )
        assert pytest.approx(psr, abs=1e-6) == dsr

    def test_dsr_nan_input(self):
        assert np.isnan(deflated_sharpe_ratio(float("nan")))


class TestHolmBonferroni:
    def test_adjust_known_values(self):
        # Raw p-values: [0.01, 0.04, 0.03, 0.005]
        # Sorted: 0.005 (rank 1), 0.01 (rank 2), 0.03 (rank 3), 0.04 (rank 4)
        # Multipliers: 4, 3, 2, 1
        # Adjusted:
        #   0.005 * 4 = 0.02
        #   0.01 * 3 = 0.03 (max(0.02, 0.03) = 0.03)
        #   0.03 * 2 = 0.06 (max(0.03, 0.06) = 0.06)
        #   0.04 * 1 = 0.04 (max(0.06, 0.04) = 0.06)
        pvals = [0.01, 0.04, 0.03, 0.005]
        adj, reject = holm_bonferroni(pvals, alpha=0.05)
        np.testing.assert_allclose(adj, [0.03, 0.06, 0.06, 0.02])
        np.testing.assert_array_equal(reject, [True, False, False, True])

    def test_empty_and_single(self):
        adj, rej = holm_bonferroni([])
        assert adj.size == 0
        assert rej.size == 0

        adj1, rej1 = holm_bonferroni([0.02], alpha=0.05)
        assert adj1[0] == 0.02
        assert rej1[0] is True or rej1[0] == 1

    def test_capped_at_one(self):
        pvals = [0.7, 0.8, 0.9]
        adj = adjust_pvalues_holm(pvals)
        assert all(x <= 1.0 for x in adj)

    def test_select_factors_holm(self):
        factors: list[dict[str, Any]] = [
            {"id": "f1", "p_value": 0.001, "perf_metric": 0.15},
            {"id": "f2", "p_value": 0.04, "perf_metric": 0.05},
            {"id": "f3", "p_value": 0.20, "perf_metric": 0.02},
        ]
        selected = select_factors_holm(factors, alpha=0.05)
        selected_ids = [f["id"] for f in selected]
        assert "f1" in selected_ids
        assert "f3" not in selected_ids
        for f in selected:
            assert "p_value_holm" in f


class TestSchemaAndPersistence:
    def test_schema_has_dsr_and_n_trials(self, tmp_path):
        db_file = tmp_path / "test_pool.db"
        ensure_alpha_pool_schema(db_file)

        with sqlite3.connect(db_file) as conn:
            cols = {
                row[1] for row in conn.execute("PRAGMA table_info(alpha_pool)")
            }
        assert "dsr" in cols
        assert "n_trials" in cols

    def test_schema_migration_idempotent(self, tmp_path):
        db_file = tmp_path / "legacy_pool.db"
        with sqlite3.connect(db_file) as conn:
            conn.execute(
                "CREATE TABLE alpha_pool (id TEXT PRIMARY KEY, code TEXT)"
            )
        # Migrate once
        ensure_alpha_pool_schema(db_file)
        with sqlite3.connect(db_file) as conn:
            cols1 = {
                row[1] for row in conn.execute("PRAGMA table_info(alpha_pool)")
            }
        assert "dsr" in cols1
        assert "n_trials" in cols1

        # Migrate second time (must be idempotent without error)
        ensure_alpha_pool_schema(db_file)
        with sqlite3.connect(db_file) as conn:
            cols2 = {
                row[1] for row in conn.execute("PRAGMA table_info(alpha_pool)")
            }
        assert cols1 == cols2

    def test_persist_alpha_pool_rows_stores_dsr_and_n_trials(self, tmp_path):
        db_file = tmp_path / "persist.db"
        results_dir = tmp_path / "results"
        factors = [
            {
                "id": "alpha_dsr_test",
                "role": "momentum",
                "hypothesis": "momentum factor",
                "perf_metric": 0.05,
                "dsr": 0.852,
                "n_trials": 42,
            }
        ]
        persist_alpha_pool_rows(db_file, results_dir, factors)
        rows = load_alpha_pool_rows(db_file)
        assert len(rows) == 1
        assert pytest.approx(rows[0]["dsr"], abs=1e-3) == 0.852
        assert rows[0]["n_trials"] == 42


class TestPortfolioManagerMultipleTesting:
    def test_manager_records_trials_and_computes_dsr(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        pm = PortfolioManager(
            roles=[],
            data_backend="local",
            local_data_path=str(tmp_path),
            results_dir=str(tmp_path / "results"),
        )
        assert pm.n_trials == 0
        assert pm.trial_sharpes == []

        # Record individual trials
        pm.record_trial(0.5)
        pm.record_trial(0.8)
        assert pm.n_trials == 2
        assert len(pm.trial_sharpes) == 2

        # Simulate candidate factors entering evaluate_and_combine
        returns = {f"2024-01-{i:02d}": 0.01 * (i % 3 - 1) for i in range(1, 20)}
        candidates = [
            {
                "id": "factor_one",
                "role": "trend",
                "hypothesis": "trend hypothesis",
                "perf_metric": 0.08,
                "selection_score": 0.08,
                "iteration": 3,
                "metrics": {"sharpe": 1.2},
                "returns": returns,
            },
            {
                "id": "factor_two",
                "role": "reversion",
                "hypothesis": "reversion hypothesis",
                "perf_metric": 0.06,
                "selection_score": 0.06,
                "iteration": 2,
                "metrics": {"sharpe": 0.9},
                "returns": returns,
            },
        ]
        pm.evaluate_and_combine(candidates)
        # Trials should be 2 (prior) + 3 + 2 = 7
        assert pm.n_trials == 7

        # Persist and check DSR calculation
        persisted = pm._persist_alpha_factors()
        assert len(persisted) > 0
        for f in persisted:
            assert "dsr" in f
            assert f["dsr"] is not None
            assert 0.0 <= f["dsr"] <= 1.0
            assert f["n_trials"] >= 7

        # Verify rows stored in SQLite
        rows = load_alpha_pool_rows(pm.db_path)
        assert len(rows) > 0
        for r in rows:
            assert r["dsr"] is not None
            assert r["n_trials"] >= 7
