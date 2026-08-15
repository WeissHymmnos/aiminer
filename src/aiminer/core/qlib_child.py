"""Standalone AlphaEval child. Importable by AIMINER_PYTHON without finaince."""

from __future__ import annotations

import json
import sys
from typing import Any


def run_request(req: dict[str, Any]) -> dict[str, Any]:
    """Keyword-only build_evaluator + ev.run(). No evaluate() method exists."""
    expr = str(req.get("expression") or "").strip()
    if not expr:
        return {
            "ok": False,
            "error": "empty_expression",
            "error_type": "EmptyExpression",
            "metrics": {},
        }
    from aiminer.core.evaluator_factory import EvaluationConfig, build_evaluator, resolve_data_backend

    backend = resolve_data_backend(req.get("data_backend") or req.get("backend") or "qlib")
    start = req.get("start")
    end = req.get("end")
    config = EvaluationConfig(
        data_backend=backend,
        evaluation_engine=str(req.get("evaluation_engine") or "pandas"),
        market_mode="single",
        market_profile=str(req.get("market_profile") or "cn_stock"),
        market_profiles=["cn_stock"],
        local_data_path=req.get("local_data_path"),
        local_data_layout=str(
            req.get("local_data_layout")
            or ("panel" if str(req.get("local_data_path") or "").endswith((".parquet", ".pq", ".csv")) else "auto")
        ),
        market_start=start,
        market_end=end,
    )
    ev = build_evaluator(
        factor_expressions=[expr],
        config=config,
        test_start_date=start,
        test_end_date=end,
    )
    ev.run()
    returns = getattr(ev, "daily_returns", None) or {}
    rows = len(returns) if hasattr(returns, "__len__") else 0
    ic = getattr(ev, "ic", None)
    metrics = {
        "ic_mean": ic,
        "rank_ic": getattr(ev, "rankic", None),
        "oos_ic": getattr(ev, "oos_ic", None),
        "sharpe_ratio": getattr(ev, "sharpe", None),
        "max_drawdown": getattr(ev, "max_dd", None),
        "rows": rows,
        "via": "qlib_child",
    }
    ok = ic is not None
    return {
        "ok": bool(ok),
        "metrics": metrics,
        "error": None if ok else "empty_or_missing_ic",
        "error_type": None if ok else "EmptyEval",
    }


def main() -> None:
    try:
        raw = sys.stdin.read() or "{}"
        req = json.loads(raw)
        if not isinstance(req, dict):
            raise ValueError("request must be an object")
        body = run_request(req)
    except Exception as exc:  # noqa: BLE001
        body = {
            "ok": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "metrics": {},
        }
    sys.stdout.write(json.dumps(body, default=str) + "\n")


if __name__ == "__main__":
    main()
