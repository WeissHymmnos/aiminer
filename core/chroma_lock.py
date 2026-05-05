import os
import time
from contextlib import contextmanager
from pathlib import Path

from loguru import logger


@contextmanager
def chroma_process_lock(action: str = "operation"):
    """Serialize ChromaDB calls across worker processes.

    Chroma's Rust bindings can start background Tokio threads. In this project
    multiple ProcessPool workers share the same persisted vector stores, so all
    direct Chroma calls go through a single advisory file lock.
    """
    import fcntl

    lock_path = Path(os.getenv("AIMINER_CHROMA_LOCK_PATH", "data/chroma_global.lock"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        waited = time.monotonic() - start
        if waited > 2:
            logger.debug(
                f"[ChromaLock] Waited {waited:.1f}s for Chroma {action} lock."
            )
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
