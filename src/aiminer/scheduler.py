"""Concurrency, worker process supervision, and task scheduling for swarm runs."""

from __future__ import annotations

import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import multiprocessing
import os
import random
import time
from typing import Any

from loguru import logger

# Optional dependencies imported with fallbacks for testing / mocking
try:
    from aiminer.sub_agent import AlphaResearcher
except ImportError:  # pragma: no cover
    AlphaResearcher = None  # type: ignore[misc, assignment]

CROSSOVER_ROLE = "遗传交叉"


def _normalize_role(role: str | None) -> str | None:
    """Map leftover crossover prompts to 遗传交叉 (len>20 or starts with 'You are')."""
    if not role:
        return role
    text = str(role).strip()
    if len(text) > 20 or text.startswith("You are"):
        return CROSSOVER_ROLE
    return text


def _is_local_embedding_mode(embedding_provider: str | None = None) -> bool:
    try:
        from aiminer.core.embeddings import resolve_embedding_backend

        backend = resolve_embedding_backend(embedding_provider)
        return backend.get("mode") == "local"
    except Exception:
        return False


_WORKER_LOG_QUEUE: Any = None


def _init_worker_context(log_queue: Any = None) -> None:
    global _WORKER_LOG_QUEUE
    _WORKER_LOG_QUEUE = log_queue
    # One BLAS/tokenizer/Polars thread per spawned worker;
    # more than that crashes Chroma HNSW.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("POLARS_MAX_THREADS", "1")


def run_agent_task(kwargs: dict[str, Any]) -> dict[str, Any]:
    task_kwargs = dict(kwargs)
    if _WORKER_LOG_QUEUE is not None and "log_queue" not in task_kwargs:
        task_kwargs["log_queue"] = _WORKER_LOG_QUEUE
    # Process workers each load a local embedding model; stagger start times.
    try:
        is_spawned_worker = (
            multiprocessing.current_process().name != "MainProcess"
        )
    except Exception:
        is_spawned_worker = False
    if is_spawned_worker:
        time.sleep(random.uniform(0.5, 2.5))
    else:
        time.sleep(random.uniform(0.1, 0.8))
    if AlphaResearcher is None:
        raise RuntimeError("AlphaResearcher is not available")
    agent = AlphaResearcher(**task_kwargs)
    result = agent.run()
    if result and isinstance(result, dict) and result.get("role"):
        result["role"] = _normalize_role(result.get("role"))
    return result


def _forward_worker_logs(worker_log_queue: Any, parent_log_queue: Any) -> None:
    """Bridge log records from ProcessPool workers back to swarm log queue.

    In spawn mode, a raw multiprocessing.Queue cannot be passed as task args
    into a nested ProcessPoolExecutor. Workers therefore write into a
    Manager-backed queue proxy, and this helper forwards those records into the
    inherited queue used by the API/WebSocket layer.
    """
    while True:
        try:
            record = worker_log_queue.get()
        except Exception:
            break
        if record is None:
            break
        try:
            parent_log_queue.put(record)
        except Exception:
            break


def _configured_worker_limit(
    explicit_value: Any, env_name: str
) -> int | None:
    raw = explicit_value if explicit_value is not None else os.getenv(env_name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning(f"[Parallel] Ignoring invalid {env_name}={raw!r}")
        return None
    return value if value > 0 else None


def _configured_timeout(
    explicit_value: Any, env_name: str, default: float | None = None
) -> float | None:
    raw = explicit_value if explicit_value is not None else os.getenv(env_name)
    if raw in (None, ""):
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        logger.warning(f"[Parallel] Ignoring invalid {env_name}={raw!r}")
        return default
    return value if value > 0 else None


def _configured_positive_int(
    explicit_value: Any, env_name: str, default: int
) -> int:
    raw = explicit_value if explicit_value is not None else os.getenv(env_name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning(f"[Config] Ignoring invalid {env_name}={raw!r}")
        return default
    if value <= 0:
        logger.warning(f"[Config] Ignoring non-positive {env_name}={raw!r}")
        return default
    return value


def _configured_swarm_executor(explicit_value: Any) -> str:
    raw = (
        explicit_value
        if explicit_value is not None
        else os.getenv("AIMINER_SWARM_EXECUTOR")
    )
    value = str(raw or "process").strip().lower()
    aliases = {
        "processes": "process",
        "multiprocess": "process",
        "multi-process": "process",
        "threads": "thread",
        "threaded": "thread",
    }
    value = aliases.get(value, value)
    if value not in {"process", "thread"}:
        logger.warning(
            f"[Parallel] Ignoring invalid AIMINER_SWARM_EXECUTOR={raw!r}; "
            "using 'process'."
        )
        return "process"
    return value


def _terminate_process_pool(executor: Any) -> None:
    terminate_workers = getattr(executor, "terminate_workers", None)
    if callable(terminate_workers):
        try:
            terminate_workers()
            return
        except Exception as exc:
            logger.debug(f"[Parallel] terminate_workers failed: {exc}")

    processes = getattr(executor, "_processes", None)
    if not isinstance(processes, dict):
        return
    for process in list(processes.values()):
        terminate = getattr(process, "terminate", None)
        if callable(terminate):
            try:
                terminate()
            except Exception as exc:
                logger.debug(f"[Parallel] process terminate failed: {exc}")


def _is_broken_process_pool_error(exc: BaseException) -> bool:
    if isinstance(exc, BrokenProcessPool):
        return True
    message = str(exc).lower()
    exc_name = type(exc).__name__.lower()
    return (
        "brokenprocesspool" in exc_name
        or "process pool was terminated abruptly" in message
        or "process pool is not usable anymore" in message
    )


def _cancel_pending_futures(
    futures: list[Any], completed: set[Any] | list[Any]
) -> int:
    pending = set(futures) - set(completed)
    for future in pending:
        try:
            future.cancel()
        except Exception as exc:
            logger.debug(f"[Parallel] future cancel failed: {exc}")
    return len(pending)


def _bounded_worker_count(
    task_count: int, configured_limit: Any = None
) -> int:
    if task_count <= 1:
        return 1
    cpu_limit = os.cpu_count() or 1
    hard_limit = cpu_limit
    if configured_limit is not None:
        hard_limit = min(hard_limit, int(configured_limit))
    return max(1, min(task_count, hard_limit))


def _process_safe_worker_count(
    task_count: int,
    configured_limit: Any = None,
    *,
    swarm_executor: str | None = None,
) -> int:
    """Cap ProcessPool size when workers load local embedding models.

    Default cap is min(4, cpu//2). AIMINER_MAX_WORKERS_PER_SWARM can lower it.
    Skip the cap with AIMINER_DISABLE_CHROMA=1 or an API embedding provider.
    """
    base = _bounded_worker_count(task_count, configured_limit)
    executor = (
        swarm_executor or os.getenv("AIMINER_SWARM_EXECUTOR") or "process"
    ).lower()
    if executor != "process":
        return base
    if os.getenv("AIMINER_DISABLE_CHROMA", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return base
    try:
        from aiminer.core.settings import build_settings as _build_settings

        settings = _build_settings({})
        provider = settings.embedding_provider
        if _is_local_embedding_mode(provider):
            cpu = os.cpu_count() or 4
            safe_cap = min(4, max(1, cpu // 2))
            limited = min(base, safe_cap)
            if limited < base:
                logger.warning(
                    f"[Parallel] Capping ProcessPool workers {base}->{limited} "
                    f"for local embedding safety (cpu={cpu}, safe_cap={safe_cap}). "
                    f"Set AIMINER_MAX_WORKERS_PER_SWARM to override lower, or "
                    f"use AIMINER_DISABLE_CHROMA=1 / --embedding-provider glm."
                )
            return limited
    except Exception as exc:
        logger.debug(f"[Parallel] worker cap detection failed: {exc}")
    return base
