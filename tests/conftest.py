from __future__ import annotations

import pathlib

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = pathlib.Path(str(item.fspath))
        if "external" in path.parts:
            item.add_marker(pytest.mark.external)
        elif "integration" in path.parts:
            item.add_marker(pytest.mark.integration)
