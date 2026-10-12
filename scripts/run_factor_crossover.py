from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import sys
from typing import Any
import urllib.error
import urllib.request

DEFAULT_API_URL = os.getenv("AIMINER_API_URL", "http://127.0.0.1:8000")


def _now_run_id() -> str:
    return f"factor_pool_crossover_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _post_json(
    url: str, payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Cannot connect to {url}: {exc.reason}. Start the web server first, "
            "for example: CONDA_ENV=aiminer ./start_web.sh"
        ) from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON response from {url}: {body[:500]}"
        ) from exc
    if not isinstance(parsed, dict):
        raise SystemExit(f"Unexpected response from {url}: {parsed!r}")
    return parsed


def _print_summary(result: dict[str, Any], run_id: str) -> None:
    factor = (
        result.get("factor") if isinstance(result.get("factor"), dict) else {}
    )
    metrics = (
        factor.get("metrics") if isinstance(factor.get("metrics"), dict) else {}
    )

    print(f"status: {result.get('status')}")
    print(f"reason: {result.get('reason')}")
    print(f"run_id: {factor.get('run_id') or run_id}")
    print(
        f"parent_factor_ids: {', '.join(str(x) for x in result.get('parent_factor_ids', []))}"
    )

    if factor:
        print(f"factor_id: {factor.get('id')}")
        print(f"hypothesis: {factor.get('hypothesis')}")
        print(f"code: {factor.get('code')}")
        print(
            f"ic: {factor.get('ic') or metrics.get('information_coefficient')}"
        )
        print(f"rank_ic: {factor.get('rank_ic') or metrics.get('rank_ic')}")
        if metrics.get("oos_ic") is not None:
            print(f"oos_ic: {metrics.get('oos_ic')}")
        if metrics.get("sharpe") is not None:
            print(f"sharpe: {metrics.get('sharpe')}")
        if factor.get("best_strategy_id"):
            print(f"best_strategy_id: {factor.get('best_strategy_id')}")
        if factor.get("report_path"):
            print(f"report_path: {factor.get('report_path')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run standalone genetic crossover on the AIMiner alpha factor pool."
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"AIMiner API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--factor-id",
        action="append",
        default=[],
        help="Parent factor id. Repeat twice or more. Omit to use the top two factors.",
    )
    parser.add_argument(
        "--iterations",
        "--crossover-iterations",
        dest="crossover_iterations",
        type=int,
        default=1,
        help="Crossover agent iterations (default: 1).",
    )
    parser.add_argument(
        "--threshold",
        "--acceptance-threshold",
        dest="acceptance_threshold",
        type=float,
        default=0.01,
        help="Minimum perf metric required for acceptance (default: 0.01).",
    )
    parser.add_argument(
        "--run-id", default=None, help="Run id to tag the generated factor."
    )
    parser.add_argument(
        "--mode", default=None, help="Evaluation mode override."
    )
    parser.add_argument(
        "--data-backend", default=None, help="Data backend override."
    )
    parser.add_argument(
        "--engine", default=None, help="Evaluation engine override."
    )
    parser.add_argument(
        "--market-start", default=None, help="Market start date override."
    )
    parser.add_argument(
        "--market-end", default=None, help="Market end date override."
    )
    parser.add_argument(
        "--market-mode", default=None, help="Market mode override."
    )
    parser.add_argument(
        "--market-profile", default=None, help="Market profile override."
    )
    parser.add_argument(
        "--local-data-path", default=None, help="Local data path override."
    )
    parser.add_argument(
        "--local-data-layout", default=None, help="Local data layout override."
    )
    parser.add_argument(
        "--llm-provider", default=None, help="LLM provider override."
    )
    parser.add_argument("--llm-model", default=None, help="LLM model override.")
    parser.add_argument(
        "--llm-base-url", default=None, help="LLM base URL override."
    )
    parser.add_argument(
        "--llm-reasoning-effort",
        default=None,
        help="LLM reasoning effort override.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=3600.0,
        help="HTTP request timeout in seconds (default: 3600).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the full JSON response."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the request payload without sending it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    factor_ids = [item for item in args.factor_id if item]
    if len(factor_ids) == 1:
        parser.error("--factor-id must be omitted or provided at least twice")

    run_id = args.run_id or _now_run_id()
    payload: dict[str, Any] = {
        "factor_ids": factor_ids,
        "crossover_iterations": args.crossover_iterations,
        "acceptance_threshold": args.acceptance_threshold,
        "run_id": run_id,
    }
    for key in (
        "mode",
        "data_backend",
        "engine",
        "market_start",
        "market_end",
        "market_mode",
        "market_profile",
        "local_data_path",
        "local_data_layout",
        "llm_provider",
        "llm_model",
        "llm_base_url",
        "llm_reasoning_effort",
    ):
        value = getattr(args, key)
        if value is not None:
            payload[key] = value

    endpoint = args.api_url.rstrip("/") + "/api/factors/crossover"
    if args.dry_run:
        print(
            json.dumps(
                {"url": endpoint, "payload": payload},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    result = _post_json(endpoint, payload, timeout=args.timeout)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_summary(result, run_id)
    return 0 if result.get("status") == "accepted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
