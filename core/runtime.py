from __future__ import annotations

import uuid
from typing import Any


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


def new_agent_id(index: int) -> str:
    return f"agent_{index:02d}"


def log_context(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}
