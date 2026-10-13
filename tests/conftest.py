import os
from pathlib import Path
import sys

import pytest

# Ensure hermetic defaults for unit tests in clean/CI environments
os.environ.setdefault(
    "OPENAI_API_KEY", "mock-openai-key-for-hermetic-unit-tests"
)
os.environ.setdefault("AIMINER_DISABLE_CHROMA", "1")
os.environ.setdefault("AIMINER_COST_BPS", "5.0")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (SRC, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def pytest_collection_modifyitems(items):
    for item in items:
        parts = set(Path(str(item.fspath)).parts)
        if "unit" in parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in parts:
            item.add_marker(pytest.mark.integration)
