from __future__ import annotations

from pathlib import Path

from scripts.verify_ci_matrix import (
    check_ci_workflows,
    check_pytest_collection,
    check_syntax,
    run_full_matrix,
)


def test_ci_workflow_integrity():
    repo_root = Path(__file__).resolve().parent.parent.parent
    assert check_ci_workflows(repo_root) is True


def test_syntax_check_integrity():
    repo_root = Path(__file__).resolve().parent.parent.parent
    assert check_syntax(repo_root) is True


def test_run_full_matrix_quick():
    repo_root = Path(__file__).resolve().parent.parent.parent
    assert run_full_matrix(repo_root, quick=True) == 0


def test_pytest_collection_integrity():
    repo_root = Path(__file__).resolve().parent.parent.parent
    assert check_pytest_collection(repo_root) is True
