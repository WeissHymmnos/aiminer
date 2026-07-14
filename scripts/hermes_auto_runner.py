from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "results" / "hermes_runner"
STATE_PATH = STATE_DIR / "state.json"
LOG_DIR = ROOT / "logs"
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
DEFAULT_PYTHON = os.getenv("AIMINER_PYTHON")
if not DEFAULT_PYTHON:
    conda_python = Path("/home/wh/.conda/envs/aiminer/bin/python")
    DEFAULT_PYTHON = str(conda_python) if conda_python.exists() else sys.executable

DEFAULT_COMMAND = [
    DEFAULT_PYTHON,
    "manager.py",
    "--iterations",
    "300",
    "--mode",
    "ricequant",
    "--data-backend",
    "local",
    "--engine",
    "polars",
    "--llm-provider",
    "mimo",
    "--llm-model",
    "Mimo-v2.5",
    "--market-start",
    "2015-01-01",
    "--market-end",
    "2020-12-01",
    "--roles",
    "动量专家",
    "波动率专家",
    "统计套利专家",
    "基本面套利专家",
    "反转专家",
    "流动性专家",
    "量价背离专家",
    "均值回归专家",
    "资金流专家",
    "情绪面专家",
    "--parallel",
    "--swarm-global-timeout-seconds",
    "2000",
]


def _now() -> datetime:
    return datetime.now(BEIJING_TZ)


def _load_state() -> dict[str, Any]:
    try:
        with STATE_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)
    tmp_path.replace(STATE_PATH)


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        with open(f"/proc/{pid}/stat") as f:
            state = f.read().split()[2]
        return state not in ("Z", "x", "X")
    except ProcessLookupError:
        return False
    except PermissionError:
        try:
            with open(f"/proc/{pid}/stat") as f:
                state = f.read().split()[2]
            return state not in ("Z", "x", "X")
        except Exception:
            return True
    except Exception:
        return False


def _active_pid(state: dict[str, Any] | None = None) -> int | None:
    state = state if state is not None else _load_state()
    pid = state.get("pid")
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    return pid if _pid_alive(pid) else None


def _in_auto_window(now: datetime | None = None) -> bool:
    current = now or _now()
    return 0 <= current.hour < 8


def _current_window_end(now: datetime | None = None) -> datetime:
    current = now or _now()
    end = current.replace(hour=8, minute=0, second=0, microsecond=0)
    if current >= end:
        end += timedelta(days=1)
    return end


def _paused(state: dict[str, Any], now: datetime | None = None) -> bool:
    raw = state.get("pause_until")
    if not raw:
        return False
    try:
        pause_until = datetime.fromisoformat(str(raw))
    except ValueError:
        return False
    if pause_until.tzinfo is None:
        pause_until = pause_until.replace(tzinfo=BEIJING_TZ)
    if (now or _now()) >= pause_until:
        state.pop("pause_until", None)
        _save_state(state)
        return False
    return True


def _apply_model_for_mode(command: list[str], mode: str) -> list[str]:
    """Swap --llm-model based on mode: auto=Mimo-v2.5pro, manual=Mimo-v2.5."""
    model = "Mimo-v2.5pro" if mode == "auto" else "Mimo-v2.5"
    result = list(command)
    if "--llm-model" in result:
        idx = result.index("--llm-model")
        if idx + 1 < len(result):
            result[idx + 1] = model
    return result


def _command_from_args(extra_args: list[str] | None = None) -> list[str]:
    if extra_args:
        if extra_args[0] == "--":
            extra_args = extra_args[1:]
        return extra_args

    raw = os.getenv("AIMINER_HERMES_COMMAND")
    if raw:
        import shlex

        return shlex.split(raw)
    return list(DEFAULT_COMMAND)


def _run_id_for_mode(mode: str, state: dict[str, Any]) -> str:
    stamp = _now().strftime("%Y%m%d_%H%M%S")
    if mode == "auto":
        return f"hermes_auto_{stamp}"
    return f"hermes_manual_{stamp}"


def _with_run_id(command: list[str], run_id: str) -> list[str]:
    if "--run-id" in command:
        return command
    if not any(Path(part).name == "manager.py" for part in command):
        return command
    return [*command, "--run-id", run_id]


def start(mode: str, extra_args: list[str] | None = None) -> int:
    state = _load_state()
    pid = _active_pid(state)
    if pid:
        print(f"already running pid={pid}")
        return 0

    state.pop("pause_until", None)
    run_id = _run_id_for_mode(mode, state)
    command = _apply_model_for_mode(
        _with_run_id(_command_from_args(extra_args), run_id), mode
    )
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"hermes_{mode}_{stamp}.log"
    log_fh = log_path.open("ab")

    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    state.update(
        {
            "pid": process.pid,
            "mode": mode,
            "run_id": run_id,
            "run_date": _now().strftime("%Y%m%d"),
            "command": command,
            "log_path": str(log_path.relative_to(ROOT)),
            "started_at": _now().isoformat(),
            "updated_at": _now().isoformat(),
        }
    )
    _save_state(state)
    print(f"started pid={process.pid} mode={mode} log={log_path.relative_to(ROOT)}")
    return 0


def stop(*, pause: bool = True, force: bool = False) -> int:
    state = _load_state()
    pid = _active_pid(state)
    if not pid:
        if pause and _in_auto_window():
            state["pause_until"] = _current_window_end().isoformat()
            _save_state(state)
        print("not running")
        return 0

    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        os.kill(pid, sig)
    except OSError:
        os.kill(pid, sig)

    deadline = time.monotonic() + (1 if force else 20)
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            break
        time.sleep(0.5)

    if _pid_alive(pid) and not force:
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    state.pop("pid", None)
    state["stopped_at"] = _now().isoformat()
    state["updated_at"] = _now().isoformat()
    if pause and _in_auto_window():
        state["pause_until"] = _current_window_end().isoformat()
    _save_state(state)
    print(f"stopped pid={pid}")
    return 0


def resume(extra_args: list[str] | None = None) -> int:
    state = _load_state()
    state.pop("pause_until", None)
    _save_state(state)
    return start("manual", extra_args=extra_args)


def status() -> int:
    state = _load_state()
    pid = _active_pid(state)
    paused = _paused(state)
    payload = {
        "running": bool(pid),
        "pid": pid,
        "mode": state.get("mode"),
        "run_id": state.get("run_id"),
        "auto_window": _in_auto_window(),
        "pause_until": state.get("pause_until"),
        "paused": paused,
        "log_path": state.get("log_path"),
        "started_at": state.get("started_at"),
        "now_beijing": _now().isoformat(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _dump_errors_to_daily_log():
    """Append new errors/warnings from latest log to results/error_log_YYYYMMDD.txt"""
    try:
        log_files = sorted(LOG_DIR.glob("hermes_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not log_files:
            return
        log = log_files[0]
        errlog = ROOT / "results" / f"error_log_{datetime.now(BEIJING_TZ).strftime('%Y%m%d')}.txt"
        errlog.parent.mkdir(parents=True, exist_ok=True)

        existing = set()
        if errlog.exists():
            existing = set(errlog.read_text().splitlines())

        pattern = re.compile(r'error|traceback|warning|failed|timeout', re.IGNORECASE)
        new_lines = []
        for line in log.read_text(errors='replace').splitlines():
            if pattern.search(line) and 'INFO' not in line and line not in existing:
                new_lines.append(line)

        if new_lines:
            with open(errlog, 'a') as f:
                f.write('\n'.join(new_lines) + '\n')
    except Exception:
        pass


def tick() -> int:
    _dump_errors_to_daily_log()
    state = _load_state()
    pid = _active_pid(state)
    now = _now()

    if _paused(state, now):
        print("paused")
        return 0

    if _in_auto_window(now):
        if pid:
            print(f"running pid={pid}")
            return 0
        return start("auto")

    if pid and state.get("mode") == "auto":
        return stop(pause=False)

    if pid:
        print(f"running pid={pid}")
        return 0

    # Outside auto window, no process running, not paused: auto-restart manual run
    return start("manual")


def watch(interval_seconds: int) -> int:
    while True:
        try:
            tick()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"watch error: {exc}", file=sys.stderr)
        time.sleep(max(5, interval_seconds))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HermesAgent-compatible AIMiner auto runner"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start a manual run now")
    start_parser.add_argument("manager_args", nargs=argparse.REMAINDER)

    resume_parser = subparsers.add_parser("resume", help="Clear pause and start now")
    resume_parser.add_argument("manager_args", nargs=argparse.REMAINDER)

    stop_parser = subparsers.add_parser("stop", help="Stop current run")
    stop_parser.add_argument("--no-pause", action="store_true")
    stop_parser.add_argument("--force", action="store_true")

    subparsers.add_parser("status", help="Print JSON status")
    subparsers.add_parser("tick", help="Run one schedule check")

    watch_parser = subparsers.add_parser("watch", help="Run schedule loop forever")
    watch_parser.add_argument("--interval-seconds", type=int, default=60)

    args = parser.parse_args()
    if args.command == "start":
        return start("manual", extra_args=args.manager_args or None)
    if args.command == "resume":
        return resume(extra_args=args.manager_args or None)
    if args.command == "stop":
        return stop(pause=not args.no_pause, force=args.force)
    if args.command == "status":
        return status()
    if args.command == "tick":
        return tick()
    if args.command == "watch":
        return watch(args.interval_seconds)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
