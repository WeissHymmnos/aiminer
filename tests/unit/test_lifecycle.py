"""Unit tests for factor lifecycle manager and decay tracking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiminer.core.exceptions import LifecycleError
from aiminer.core.lifecycle import (
    FactorEvaluation,
    FactorLifecycleManager,
    FactorLifecycleRecord,
    FactorStatus,
)


def test_factor_registration():
    mgr = FactorLifecycleManager(decay_threshold=0.01)
    record = mgr.register_factor("alpha_01", "Close / Open - 1")
    assert record.factor_id == "alpha_01"
    assert record.expression == "Close / Open - 1"
    assert record.status == FactorStatus.ACTIVE
    assert record.latest_ic is None
    assert mgr.has_factor("alpha_01")
    assert not mgr.has_factor("alpha_02")


def test_duplicate_registration_error():
    mgr = FactorLifecycleManager()
    mgr.register_factor("alpha_01", "expr")
    with pytest.raises(LifecycleError, match="already registered"):
        mgr.register_factor("alpha_01", "expr")


def test_empty_id_error():
    mgr = FactorLifecycleManager()
    with pytest.raises(LifecycleError, match="must not be empty"):
        mgr.register_factor("", "expr")


def test_get_nonexistent_factor():
    mgr = FactorLifecycleManager()
    with pytest.raises(LifecycleError, match="not found"):
        mgr.get_factor("unknown")


def test_rolling_and_ema_ic_calculation():
    mgr = FactorLifecycleManager(window_size=3)
    mgr.register_factor("alpha_01", "expr", initial_ic=0.05)
    mgr.record_evaluation("alpha_01", ic=0.04)
    mgr.record_evaluation("alpha_01", ic=0.03)

    # 3 items: 0.05, 0.04, 0.03 -> rolling avg = 0.04
    rolling = mgr.calculate_rolling_ic("alpha_01")
    assert pytest.approx(rolling, 1e-5) == 0.04

    # 4th item: 0.02 -> window 3: [0.04, 0.03, 0.02] -> avg = 0.03
    mgr.record_evaluation("alpha_01", ic=0.02)
    rolling = mgr.calculate_rolling_ic("alpha_01")
    assert pytest.approx(rolling, 1e-5) == 0.03

    # EMA
    ema = mgr.calculate_ema_ic("alpha_01", span=3)
    assert ema is not None
    assert 0.02 <= ema <= 0.05


def test_decay_transition_to_degraded_and_recovery():
    mgr = FactorLifecycleManager(
        decay_threshold=0.03,
        cull_threshold=0.0,
        window_size=2,
        allow_recovery=True,
    )
    mgr.register_factor("alpha_01", "expr", initial_ic=0.05)
    rec = mgr.get_factor("alpha_01")
    assert rec.status == FactorStatus.ACTIVE

    # IC drops below decay threshold: 0.02 -> rolling avg = (0.05 + 0.02)/2 = 0.035 >= 0.03
    mgr.record_evaluation("alpha_01", ic=0.02)
    assert rec.status == FactorStatus.ACTIVE

    # Next IC drops to 0.01 -> rolling avg = (0.02 + 0.01)/2 = 0.015 < 0.03 -> DEGRADED
    mgr.record_evaluation("alpha_01", ic=0.01)
    assert rec.status == FactorStatus.DEGRADED
    assert rec.degraded_at is not None
    assert "decay threshold" in (rec.degradation_reason or "")

    # Rebound: IC jumps to 0.06 -> rolling avg = (0.01 + 0.06)/2 = 0.035 >= 0.03 -> ACTIVE
    mgr.record_evaluation("alpha_01", ic=0.06)
    assert rec.status == FactorStatus.ACTIVE
    assert rec.consecutive_degraded_count == 0


def test_consecutive_degraded_to_culled():
    mgr = FactorLifecycleManager(
        decay_threshold=0.03,
        cull_threshold=0.001,
        consecutive_degraded_limit=2,
        window_size=2,
    )
    mgr.register_factor("alpha_01", "expr", initial_ic=0.05)

    # Trigger degraded
    mgr.record_evaluation("alpha_01", ic=0.01)
    mgr.record_evaluation("alpha_01", ic=0.01)
    rec = mgr.get_factor("alpha_01")
    assert rec.status == FactorStatus.DEGRADED
    assert rec.consecutive_degraded_count == 1

    # Remains degraded for second window -> hits limit 2 -> CULLED
    mgr.record_evaluation("alpha_01", ic=0.01)
    assert rec.status == FactorStatus.CULLED
    assert rec.culled_at is not None
    assert "consecutive windows" in (rec.cull_reason or "")


def test_drop_below_cull_threshold_immediate_cull():
    mgr = FactorLifecycleManager(
        decay_threshold=0.02,
        cull_threshold=0.0,
        window_size=2,
    )
    mgr.register_factor("alpha_01", "expr", initial_ic=0.05)
    # Severe drop to -0.06 -> rolling avg = (0.05 - 0.06)/2 = -0.005 <= 0.0
    mgr.record_evaluation("alpha_01", ic=-0.06)
    rec = mgr.get_factor("alpha_01")
    assert rec.status == FactorStatus.CULLED
    assert "dropped to or below cull threshold" in (rec.cull_reason or "")


def test_decay_drop_pct_from_peak():
    mgr = FactorLifecycleManager(
        decay_threshold=0.01,
        cull_threshold=0.0,
        decay_drop_pct=0.5,
        window_size=2,
    )
    # Peak IC = 0.10
    mgr.register_factor("alpha_01", "expr", initial_ic=0.10)
    # Rolling becomes (0.10 + 0.04) / 2 = 0.07 (still > decay_threshold 0.01, but peak is 0.10)
    # Next drop to 0.04 -> rolling = (0.04 + 0.04) / 2 = 0.04
    # (0.10 - 0.04) / 0.10 = 60% drop >= 50% drop threshold -> DEGRADED
    mgr.record_evaluation("alpha_01", ic=0.04)
    mgr.record_evaluation("alpha_01", ic=0.04)
    rec = mgr.get_factor("alpha_01")
    assert rec.status == FactorStatus.DEGRADED
    assert "dropped" in (rec.degradation_reason or "")


def test_manual_degrade_cull_reactivate():
    mgr = FactorLifecycleManager(allow_recovery=False)
    mgr.register_factor("alpha_01", "expr")

    mgr.degrade_factor("alpha_01", reason="Manual review")
    rec = mgr.get_factor("alpha_01")
    assert rec.status == FactorStatus.DEGRADED
    assert rec.degradation_reason == "Manual review"

    mgr.cull_factor("alpha_01", reason="Replaced by improved variant")
    assert rec.status == FactorStatus.CULLED
    assert rec.cull_reason == "Replaced by improved variant"

    # Cannot reactivate culled when allow_recovery is False
    with pytest.raises(LifecycleError, match="Cannot reactivate culled factor"):
        mgr.reactivate_factor("alpha_01")

    # Cannot degrade already culled factor
    with pytest.raises(LifecycleError, match="Cannot degrade already culled"):
        mgr.degrade_factor("alpha_01")


def test_manager_filtering_and_summary():
    mgr = FactorLifecycleManager()
    mgr.register_factor("f1", "expr1")
    mgr.register_factor("f2", "expr2")
    mgr.register_factor("f3", "expr3")

    mgr.degrade_factor("f2")
    mgr.cull_factor("f3")

    assert [f.factor_id for f in mgr.get_active_factors()] == ["f1"]
    assert [f.factor_id for f in mgr.get_degraded_factors()] == ["f2"]
    assert [f.factor_id for f in mgr.get_culled_factors()] == ["f3"]

    summary = mgr.summary()
    assert summary["total_factors"] == 3
    assert summary["active_factors"] == 1
    assert summary["degraded_factors"] == 1
    assert summary["culled_factors"] == 1


def test_json_persistence(tmp_path: Path):
    mgr = FactorLifecycleManager()
    mgr.register_factor("f1", "expr1", initial_ic=0.04, metadata={"tag": "vol"})
    mgr.record_evaluation("f1", ic=0.05, rank_ic=0.06, period="2023Q1")

    json_file = tmp_path / "lifecycle.json"
    mgr.save_json(json_file)
    assert json_file.exists()

    loaded = FactorLifecycleManager.load_json(json_file)
    assert loaded.has_factor("f1")
    rec = loaded.get_factor("f1")
    assert rec.factor_id == "f1"
    assert rec.expression == "expr1"
    assert rec.metadata == {"tag": "vol"}
    assert len(rec.history) == 2
    assert rec.history[1].rank_ic == 0.06


def test_sqlite_persistence(tmp_path: Path):
    mgr = FactorLifecycleManager()
    mgr.register_factor("f1", "expr1", initial_ic=0.04)
    mgr.record_evaluation("f1", ic=0.05)
    mgr.register_factor("f2", "expr2", initial_ic=0.01)
    mgr.degrade_factor("f2", reason="Subpar perf")

    db_path = tmp_path / "lifecycle.db"
    mgr.export_to_sqlite(db_path)
    assert db_path.exists()

    loaded = FactorLifecycleManager.import_from_sqlite(db_path)
    assert loaded.has_factor("f1")
    assert loaded.has_factor("f2")
    assert loaded.get_factor("f1").status == FactorStatus.ACTIVE
    assert loaded.get_factor("f2").status == FactorStatus.DEGRADED
    assert loaded.get_factor("f2").degradation_reason == "Subpar perf"
