#!/usr/bin/env python3
"""Automated regression test matrix and CI integrity validator."""

from __future__ import annotations

import argparse
import compileall
import os
from pathlib import Path
import shutil
import subprocess
import sys


def check_syntax(repo_root: Path) -> bool:
    """Verify python byte-compilation across src/ and tests/."""
    src_dir = repo_root / "src"
    tests_dir = repo_root / "tests"

    print(f"[1/4] Checking python syntax in {src_dir} and {tests_dir}...")
    ok1 = compileall.compile_dir(str(src_dir), quiet=1)
    ok2 = compileall.compile_dir(str(tests_dir), quiet=1)
    if ok1 and ok2:
        print("  -> Syntax check passed.")
        return True
    print("  -> Syntax compilation failed!")
    return False


def check_ci_workflows(repo_root: Path) -> bool:
    """Verify GitHub Actions CI workflow files exist and contain matrix."""
    ci_file = repo_root / ".github" / "workflows" / "ci.yml"
    print(f"[2/4] Checking CI workflow integrity in {ci_file}...")
    if not ci_file.exists():
        print(f"  -> Error: CI file {ci_file} does not exist.")
        return False

    content = ci_file.read_text(encoding="utf-8")
    checks = [
        ("matrix", "matrix configuration"),
        ("python-version", "python versions specification"),
        ("3.10", "Python 3.10 in matrix"),
        ("3.12", "Python 3.12 in matrix"),
        ("PYTHONPATH=src", "PYTHONPATH=src for tests"),
        ("tsc -b", "TypeScript typecheck"),
    ]
    all_ok = True
    for needle, desc in checks:
        if needle in content:
            print(f"  -> Found {desc}.")
        else:
            print(f"  -> Warning/Error: Missing {desc} in {ci_file.name}.")
            all_ok = False
    return all_ok


def check_ruff_lint(repo_root: Path) -> bool:
    """Verify ruff lint and import formatting clean status."""
    print("[3/4] Running ruff check...")
    ruff_bin = shutil.which("ruff")
    if ruff_bin:
        cmd = [ruff_bin, "check", "--no-cache", "src", "tests"]
    else:
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "src",
            "tests",
        ]
    res = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        print("  -> Ruff linting clean (0 errors).")
        return True
    print(f"  -> Ruff lint errors:\n{res.stdout}\n{res.stderr}")
    return False


def check_pytest_collection(repo_root: Path) -> bool:
    """Verify pytest test discovery passes without errors."""
    print("[4/4] Verifying pytest test collection...")
    python_bin = sys.executable
    res = subprocess.run(
        [
            python_bin,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    if res.returncode == 0:
        print("  -> Pytest collection succeeded.")
        return True
    print(f"  -> Pytest collection failed:\n{res.stdout}\n{res.stderr}")
    return False


def run_full_matrix(repo_root: Path, *, quick: bool = False) -> int:
    """Run all automated regression test matrix and integrity checks."""
    print("=== AI Alpha Miner Automated Regression Test Matrix ===")
    ok = True
    ok = check_syntax(repo_root) and ok
    ok = check_ci_workflows(repo_root) and ok
    ok = check_ruff_lint(repo_root) and ok
    if not quick:
        ok = check_pytest_collection(repo_root) and ok

    if ok:
        print("\n[SUCCESS] All matrix and CI integrity checks passed!")
        return 0
    print("\n[FAILURE] One or more integrity checks failed.")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify regression test matrix & CI integrity"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip full test collection for fast validation",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    sys.exit(run_full_matrix(repo_root, quick=args.quick))


if __name__ == "__main__":
    main()
