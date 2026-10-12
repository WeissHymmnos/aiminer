"""Factor lifecycle management, rolling IC decay tracking, and culling."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from aiminer.core.constants import IC_CULL_THRESHOLD
from aiminer.core.exceptions import LifecycleError


class FactorStatus(str, Enum):
    """Lifecycle status enumeration for quant alpha factors."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    CULLED = "culled"


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FactorEvaluation:
    """Represents a single periodic evaluation snapshot for a factor."""

    timestamp: str
    ic: float
    rank_ic: Optional[float] = None
    period: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert evaluation record to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FactorEvaluation:
        """Create an evaluation snapshot from dictionary."""
        return cls(
            timestamp=str(data.get("timestamp") or _now_iso()),
            ic=float(data["ic"]),
            rank_ic=(
                float(data["rank_ic"])
                if data.get("rank_ic") is not None
                else None
            ),
            period=data.get("period"),
            metrics=dict(data.get("metrics") or {}),
        )


@dataclass
class FactorLifecycleRecord:
    """Complete lifecycle state and decay tracking record for a factor."""

    factor_id: str
    expression: str
    status: FactorStatus = FactorStatus.ACTIVE
    history: List[FactorEvaluation] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    degraded_at: Optional[str] = None
    culled_at: Optional[str] = None
    degradation_reason: Optional[str] = None
    cull_reason: Optional[str] = None
    consecutive_degraded_count: int = 0
    peak_ic: Optional[float] = None
    latest_ic: Optional[float] = None
    rolling_ic: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record into dictionary."""
        return {
            "factor_id": self.factor_id,
            "expression": self.expression,
            "status": self.status.value,
            "history": [eval_rec.to_dict() for eval_rec in self.history],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "degraded_at": self.degraded_at,
            "culled_at": self.culled_at,
            "degradation_reason": self.degradation_reason,
            "cull_reason": self.cull_reason,
            "consecutive_degraded_count": self.consecutive_degraded_count,
            "peak_ic": self.peak_ic,
            "latest_ic": self.latest_ic,
            "rolling_ic": self.rolling_ic,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FactorLifecycleRecord:
        """Deserialize dictionary into lifecycle record."""
        raw_status = data.get("status", FactorStatus.ACTIVE.value)
        status = (
            FactorStatus(raw_status)
            if isinstance(raw_status, str)
            else raw_status
        )
        history = [
            FactorEvaluation.from_dict(h) for h in data.get("history", [])
        ]
        return cls(
            factor_id=str(data["factor_id"]),
            expression=str(data.get("expression", "")),
            status=status,
            history=history,
            created_at=str(data.get("created_at") or _now_iso()),
            updated_at=str(data.get("updated_at") or _now_iso()),
            degraded_at=data.get("degraded_at"),
            culled_at=data.get("culled_at"),
            degradation_reason=data.get("degradation_reason"),
            cull_reason=data.get("cull_reason"),
            consecutive_degraded_count=int(
                data.get("consecutive_degraded_count", 0)
            ),
            peak_ic=(
                float(data["peak_ic"])
                if data.get("peak_ic") is not None
                else None
            ),
            latest_ic=(
                float(data["latest_ic"])
                if data.get("latest_ic") is not None
                else None
            ),
            rolling_ic=(
                float(data["rolling_ic"])
                if data.get("rolling_ic") is not None
                else None
            ),
            metadata=dict(data.get("metadata") or {}),
        )


class FactorLifecycleManager:
    """Manages factor lifecycle transitions, IC decay monitoring, and culling.
    """

    def __init__(
        self,
        decay_threshold: float = IC_CULL_THRESHOLD,
        cull_threshold: float = 0.0,
        consecutive_degraded_limit: int = 3,
        window_size: int = 5,
        decay_drop_pct: Optional[float] = 0.5,
        allow_recovery: bool = True,
    ) -> None:
        """Initialize factor lifecycle manager.

        Args:
            decay_threshold: IC threshold below which a factor is degraded.
            cull_threshold: IC threshold below which a factor is culled.
            consecutive_degraded_limit: Max consecutive evaluation periods
                degraded before being culled.
            window_size: Evaluation window size for rolling IC computation.
            decay_drop_pct: Fractional drop from peak IC triggering degradation
                (e.g. 0.5 means a 50% drop from peak IC).
            allow_recovery: Whether degraded factors can recover to active if
                their rolling IC rebounds above decay threshold.
        """
        if window_size < 1:
            raise LifecycleError(f"window_size must be >= 1, got {window_size}")
        if consecutive_degraded_limit < 1:
            raise LifecycleError(
                "consecutive_degraded_limit must be >= 1, "
                f"got {consecutive_degraded_limit}"
            )
        if float(cull_threshold) > float(decay_threshold):
            raise LifecycleError(
                f"cull_threshold ({cull_threshold}) cannot exceed "
                f"decay_threshold ({decay_threshold})"
            )
        self.decay_threshold = float(decay_threshold)
        self.cull_threshold = float(cull_threshold)
        self.consecutive_degraded_limit = int(consecutive_degraded_limit)
        self.window_size = int(window_size)
        self.decay_drop_pct = (
            float(decay_drop_pct) if decay_drop_pct is not None else None
        )
        self.allow_recovery = bool(allow_recovery)
        self._records: Dict[str, FactorLifecycleRecord] = {}

    def register_factor(
        self,
        factor_id: str,
        expression: str,
        initial_ic: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FactorLifecycleRecord:
        """Register a new factor in the lifecycle manager."""
        if not factor_id:
            raise LifecycleError("factor_id must not be empty")
        if factor_id in self._records:
            raise LifecycleError(f"Factor '{factor_id}' is already registered")

        record = FactorLifecycleRecord(
            factor_id=factor_id,
            expression=expression,
            status=FactorStatus.ACTIVE,
            metadata=dict(metadata or {}),
        )
        self._records[factor_id] = record
        if initial_ic is not None:
            self.record_evaluation(factor_id=factor_id, ic=initial_ic)
        return self._records[factor_id]

    def has_factor(self, factor_id: str) -> bool:
        """Check if factor is registered."""
        return factor_id in self._records

    def get_factor(self, factor_id: str) -> FactorLifecycleRecord:
        """Retrieve factor lifecycle record or raise LifecycleError."""
        if factor_id not in self._records:
            raise LifecycleError(
                f"Factor '{factor_id}' not found in lifecycle manager"
            )
        return self._records[factor_id]

    def calculate_rolling_ic(
        self, factor_id: str, window: Optional[int] = None
    ) -> Optional[float]:
        """Compute rolling mean IC over the most recent window periods."""
        record = self.get_factor(factor_id)
        if not record.history:
            return None
        if window is not None and window < 1:
            raise LifecycleError(f"window must be >= 1, got {window}")
        w = window if window is not None else self.window_size
        recent_evals = record.history[-w:]
        return sum(e.ic for e in recent_evals) / len(recent_evals)

    def calculate_ema_ic(
        self, factor_id: str, span: int = 5
    ) -> Optional[float]:
        """Compute Exponential Moving Average (EMA) of historical IC values."""
        record = self.get_factor(factor_id)
        if not record.history:
            return None
        if span < 1:
            raise LifecycleError(f"span must be >= 1, got {span}")
        alpha = 2.0 / (span + 1.0)
        ema = record.history[0].ic
        for ev in record.history[1:]:
            ema = alpha * ev.ic + (1.0 - alpha) * ema
        return ema

    def record_evaluation(
        self,
        factor_id: str,
        ic: float,
        rank_ic: Optional[float] = None,
        timestamp: Optional[str] = None,
        period: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> FactorLifecycleRecord:
        """Record a periodic evaluation and update lifecycle state."""
        record = self.get_factor(factor_id)
        now_ts = timestamp or _now_iso()

        evaluation = FactorEvaluation(
            timestamp=now_ts,
            ic=float(ic),
            rank_ic=float(rank_ic) if rank_ic is not None else None,
            period=period,
            metrics=dict(metrics or {}),
        )
        record.history.append(evaluation)
        record.latest_ic = float(ic)
        record.updated_at = now_ts

        # Update peak IC
        if record.peak_ic is None or record.latest_ic > record.peak_ic:
            record.peak_ic = record.latest_ic

        # Calculate rolling IC
        rolling_ic = self.calculate_rolling_ic(factor_id)
        record.rolling_ic = rolling_ic

        if rolling_ic is None:
            return record

        # Evaluate decay triggers
        if record.status == FactorStatus.ACTIVE:
            if rolling_ic <= self.cull_threshold:
                self.cull_factor(
                    factor_id,
                    reason=(
                        f"Rolling IC {rolling_ic:.4f} dropped to or below cull "
                        f"threshold {self.cull_threshold:.4f}"
                    ),
                )
            elif self._is_decayed(record, rolling_ic):
                self.degrade_factor(
                    factor_id,
                    reason=self._decay_reason(record, rolling_ic),
                )
        elif record.status == FactorStatus.DEGRADED:
            if rolling_ic <= self.cull_threshold:
                self.cull_factor(
                    factor_id,
                    reason=(
                        f"Rolling IC {rolling_ic:.4f} dropped to or below cull "
                        f"threshold {self.cull_threshold:.4f}"
                    ),
                )
            elif self._is_decayed(record, rolling_ic):
                record.consecutive_degraded_count += 1
                if (
                    record.consecutive_degraded_count
                    >= self.consecutive_degraded_limit
                ):
                    self.cull_factor(
                        factor_id,
                        reason=(
                            f"Factor remained degraded for "
                            f"{record.consecutive_degraded_count} "
                            f"consecutive windows "
                            f"(limit: {self.consecutive_degraded_limit})"
                        ),
                    )
            elif self.allow_recovery and rolling_ic >= self.decay_threshold:
                self.reactivate_factor(
                    factor_id,
                    reason=(
                        f"Rolling IC {rolling_ic:.4f} recovered above decay "
                        f"threshold {self.decay_threshold:.4f}"
                    ),
                )
            else:
                record.consecutive_degraded_count = 0
        return record

    def _is_decayed(
        self, record: FactorLifecycleRecord, rolling_ic: float
    ) -> bool:
        """Check whether rolling IC represents significant decay."""
        if rolling_ic < self.decay_threshold:
            return True
        if (
            self.decay_drop_pct is not None
            and record.peak_ic is not None
            and record.peak_ic > 0
        ):
            drop_ratio = (record.peak_ic - rolling_ic) / record.peak_ic
            if drop_ratio >= self.decay_drop_pct:
                return True
        return False

    def _decay_reason(
        self, record: FactorLifecycleRecord, rolling_ic: float
    ) -> str:
        """Generate human-readable reason for degradation."""
        if rolling_ic < self.decay_threshold:
            return (
                f"Rolling IC {rolling_ic:.4f} below decay threshold "
                f"{self.decay_threshold:.4f}"
            )
        if (
            self.decay_drop_pct is not None
            and record.peak_ic is not None
            and record.peak_ic > 0
        ):
            drop_pct = (record.peak_ic - rolling_ic) / record.peak_ic * 100.0
            return (
                f"Rolling IC {rolling_ic:.4f} dropped {drop_pct:.1f}% from "
                f"peak IC {record.peak_ic:.4f} "
                f"(limit {self.decay_drop_pct * 100:.1f}%)"
            )
        return f"IC decay detected (rolling IC {rolling_ic:.4f})"

    def degrade_factor(
        self, factor_id: str, reason: str = ""
    ) -> FactorLifecycleRecord:
        """Transition factor from ACTIVE to DEGRADED."""
        record = self.get_factor(factor_id)
        if record.status == FactorStatus.CULLED:
            raise LifecycleError(
                f"Cannot degrade already culled factor '{factor_id}'"
            )
        now_ts = _now_iso()
        record.status = FactorStatus.DEGRADED
        record.degraded_at = now_ts
        record.updated_at = now_ts
        record.degradation_reason = reason or "Manual degradation"
        record.consecutive_degraded_count = max(
            1, record.consecutive_degraded_count
        )
        return record

    def cull_factor(
        self, factor_id: str, reason: str = ""
    ) -> FactorLifecycleRecord:
        """Transition factor to CULLED status."""
        record = self.get_factor(factor_id)
        now_ts = _now_iso()
        record.status = FactorStatus.CULLED
        record.culled_at = now_ts
        record.updated_at = now_ts
        record.cull_reason = reason or "Manual culling"
        return record

    def reactivate_factor(
        self, factor_id: str, reason: str = ""
    ) -> FactorLifecycleRecord:
        """Reactivate a degraded factor back to ACTIVE."""
        record = self.get_factor(factor_id)
        if record.status == FactorStatus.CULLED and not self.allow_recovery:
            raise LifecycleError(
                f"Cannot reactivate culled factor '{factor_id}' "
                "when allow_recovery is False"
            )
        now_ts = _now_iso()
        record.status = FactorStatus.ACTIVE
        record.updated_at = now_ts
        record.consecutive_degraded_count = 0
        record.degradation_reason = None
        record.cull_reason = None
        if reason:
            record.metadata["reactivation_reason"] = reason
        return record

    def check_decay(self, factor_id: str) -> FactorStatus:
        """Query current lifecycle status of factor."""
        return self.get_factor(factor_id).status

    def get_factors_by_status(
        self, status: FactorStatus | str
    ) -> List[FactorLifecycleRecord]:
        """List all factors matching given status."""
        target_status = (
            status if isinstance(status, FactorStatus) else FactorStatus(status)
        )
        return [
            rec for rec in self._records.values() if rec.status == target_status
        ]

    def get_active_factors(self) -> List[FactorLifecycleRecord]:
        """Return all factors currently active."""
        return self.get_factors_by_status(FactorStatus.ACTIVE)

    def get_degraded_factors(self) -> List[FactorLifecycleRecord]:
        """Return all factors currently degraded."""
        return self.get_factors_by_status(FactorStatus.DEGRADED)

    def get_culled_factors(self) -> List[FactorLifecycleRecord]:
        """Return all factors currently culled."""
        return self.get_factors_by_status(FactorStatus.CULLED)

    def summary(self) -> Dict[str, Any]:
        """Generate high-level summary of factor pool lifecycle states."""
        total = len(self._records)
        active = len(self.get_active_factors())
        degraded = len(self.get_degraded_factors())
        culled = len(self.get_culled_factors())
        rolling_ics = [
            rec.rolling_ic
            for rec in self._records.values()
            if rec.rolling_ic is not None
        ]
        mean_rolling_ic = (
            sum(rolling_ics) / len(rolling_ics) if rolling_ics else None
        )
        return {
            "total_factors": total,
            "active_factors": active,
            "degraded_factors": degraded,
            "culled_factors": culled,
            "mean_rolling_ic": mean_rolling_ic,
            "decay_threshold": self.decay_threshold,
            "cull_threshold": self.cull_threshold,
            "consecutive_degraded_limit": self.consecutive_degraded_limit,
            "window_size": self.window_size,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager configuration and all factor records."""
        return {
            "decay_threshold": self.decay_threshold,
            "cull_threshold": self.cull_threshold,
            "consecutive_degraded_limit": self.consecutive_degraded_limit,
            "window_size": self.window_size,
            "decay_drop_pct": self.decay_drop_pct,
            "allow_recovery": self.allow_recovery,
            "factors": {
                fid: rec.to_dict() for fid, rec in self._records.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FactorLifecycleManager:
        """Create a lifecycle manager instance from dictionary."""
        manager = cls(
            decay_threshold=data.get("decay_threshold", IC_CULL_THRESHOLD),
            cull_threshold=data.get("cull_threshold", 0.0),
            consecutive_degraded_limit=data.get(
                "consecutive_degraded_limit", 3
            ),
            window_size=data.get("window_size", 5),
            decay_drop_pct=data.get("decay_drop_pct", 0.5),
            allow_recovery=data.get("allow_recovery", True),
        )
        factors_dict = data.get("factors", {})
        for fid, raw_record in factors_dict.items():
            record = FactorLifecycleRecord.from_dict(raw_record)
            manager._records[fid] = record
        return manager

    def save_json(self, path: str | Path) -> None:
        """Save lifecycle state atomically to JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        except Exception as e:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise LifecycleError(
                f"Failed to save lifecycle state to JSON: {e}"
            ) from e

    @classmethod
    def load_json(cls, path: str | Path) -> FactorLifecycleManager:
        """Load lifecycle state from JSON file."""
        target = Path(path)
        if not target.exists():
            raise LifecycleError(f"Lifecycle file not found: {target}")
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            raise LifecycleError(
                f"Failed to load lifecycle state from JSON: {e}"
            ) from e

    def export_to_sqlite(
        self, db_path: str | Path, table_name: str = "factor_lifecycle"
    ) -> None:
        """Export lifecycle state into SQLite database."""
        db_file = str(db_path)
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(db_file) as conn:
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        factor_id TEXT PRIMARY KEY,
                        expression TEXT,
                        status TEXT,
                        consecutive_degraded_count INTEGER,
                        peak_ic REAL,
                        latest_ic REAL,
                        rolling_ic REAL,
                        created_at TEXT,
                        updated_at TEXT,
                        degraded_at TEXT,
                        culled_at TEXT,
                        degradation_reason TEXT,
                        cull_reason TEXT,
                        history_json TEXT,
                        metadata_json TEXT
                    )
                    """
                )
                cursor = conn.cursor()
                for rec in self._records.values():
                    cursor.execute(
                        f"""
                        INSERT OR REPLACE INTO {table_name} (
                            factor_id, expression, status,
                            consecutive_degraded_count, peak_ic, latest_ic,
                            rolling_ic, created_at, updated_at, degraded_at,
                            culled_at, degradation_reason, cull_reason,
                            history_json, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            rec.factor_id,
                            rec.expression,
                            rec.status.value,
                            rec.consecutive_degraded_count,
                            rec.peak_ic,
                            rec.latest_ic,
                            rec.rolling_ic,
                            rec.created_at,
                            rec.updated_at,
                            rec.degraded_at,
                            rec.culled_at,
                            rec.degradation_reason,
                            rec.cull_reason,
                            json.dumps(
                                [e.to_dict() for e in rec.history],
                                ensure_ascii=False,
                            ),
                            json.dumps(rec.metadata, ensure_ascii=False),
                        ),
                    )
                conn.commit()
        except Exception as e:
            raise LifecycleError(
                f"Failed to export factor lifecycle to SQLite: {e}"
            ) from e

    @classmethod
    def import_from_sqlite(
        cls,
        db_path: str | Path,
        table_name: str = "factor_lifecycle",
        decay_threshold: float = IC_CULL_THRESHOLD,
        cull_threshold: float = 0.0,
        consecutive_degraded_limit: int = 3,
        window_size: int = 5,
        decay_drop_pct: Optional[float] = 0.5,
        allow_recovery: bool = True,
    ) -> FactorLifecycleManager:
        """Import factor lifecycle records from SQLite database."""
        db_file = str(db_path)
        if not Path(db_file).exists():
            raise LifecycleError(f"Database file not found: {db_file}")

        manager = cls(
            decay_threshold=decay_threshold,
            cull_threshold=cull_threshold,
            consecutive_degraded_limit=consecutive_degraded_limit,
            window_size=window_size,
            decay_drop_pct=decay_drop_pct,
            allow_recovery=allow_recovery,
        )
        try:
            with sqlite3.connect(db_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                for row in rows:
                    raw_history = (
                        json.loads(row["history_json"])
                        if row["history_json"]
                        else []
                    )
                    history = [
                        FactorEvaluation.from_dict(h) for h in raw_history
                    ]
                    raw_meta = (
                        json.loads(row["metadata_json"])
                        if row["metadata_json"]
                        else {}
                    )
                    record = FactorLifecycleRecord(
                        factor_id=str(row["factor_id"]),
                        expression=str(row["expression"] or ""),
                        status=FactorStatus(str(row["status"])),
                        history=history,
                        created_at=str(row["created_at"]),
                        updated_at=str(row["updated_at"]),
                        degraded_at=row["degraded_at"],
                        culled_at=row["culled_at"],
                        degradation_reason=row["degradation_reason"],
                        cull_reason=row["cull_reason"],
                        consecutive_degraded_count=int(
                            row["consecutive_degraded_count"] or 0
                        ),
                        peak_ic=(
                            float(row["peak_ic"])
                            if row["peak_ic"] is not None
                            else None
                        ),
                        latest_ic=(
                            float(row["latest_ic"])
                            if row["latest_ic"] is not None
                            else None
                        ),
                        rolling_ic=(
                            float(row["rolling_ic"])
                            if row["rolling_ic"] is not None
                            else None
                        ),
                        metadata=raw_meta,
                    )
                    manager._records[record.factor_id] = record
            return manager
        except Exception as e:
            raise LifecycleError(
                f"Failed to import factor lifecycle from SQLite: {e}"
            ) from e
