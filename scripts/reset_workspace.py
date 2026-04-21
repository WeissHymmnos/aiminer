"""Reset AIMiner mining artifacts and learned memory.

Scopes (composable, repeatable on the CLI):
  pool    — alpha pool DB, JSON backup, per-factor reports/charts/strategies
  memory  — LLMWiki sqlite store + Obsidian vault
  rag     — ChromaDB persistent embeddings + test_db cache
  runs    — swarm/run logs and manifests
  all     — every scope above

Default behaviour is a dry-run that prints the targets and their sizes; pass
``--confirm`` to actually move the matched paths into a timestamped folder
under ``results/.trash/``. Nothing is deleted irreversibly here — clean the
.trash directory yourself once you are sure (or run with ``--purge`` to also
empty trash entries older than ``--purge-after-days``).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]


SCOPE_TARGETS: dict[str, list[str]] = {
    "pool": [
        "results/alpha_miner.db",
        "results/alpha_pool.json",
        "results/results.json",
        "results/reports",
        "results/charts",
        "results/strategies",
        "results/manual",
    ],
    "memory": [
        "data/wiki_db",
        "data/wiki_vault",
    ],
    "rag": [
        "data/chroma_db",
        "data/test_db",
    ],
    "runs": [
        "results/swarm_runs",
    ],
}
SCOPE_TARGETS["all"] = sorted({p for paths in SCOPE_TARGETS.values() for p in paths})

VALID_SCOPES = tuple(SCOPE_TARGETS.keys())
TRASH_ROOT_REL = "results/.trash"
DEFAULT_PURGE_AFTER_DAYS = 7


@dataclass
class ResetTarget:
    rel_path: str
    abs_path: Path
    exists: bool
    size_bytes: int = 0
    is_dir: bool = False


@dataclass
class ResetPlan:
    scopes: List[str]
    targets: List[ResetTarget] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(t.size_bytes for t in self.targets if t.exists)

    @property
    def existing(self) -> List[ResetTarget]:
        return [t for t in self.targets if t.exists]


# ---------------------------------------------------------------------------
# Plan / inspect


def expand_scopes(raw_scopes: Sequence[str]) -> List[str]:
    """Normalize CLI scopes; dedupe while preserving order; expand 'all'."""
    seen: list[str] = []
    for raw in raw_scopes:
        for token in str(raw).split(","):
            token = token.strip().lower()
            if not token:
                continue
            if token not in VALID_SCOPES:
                raise ValueError(
                    f"Unknown scope {token!r}; valid options: {', '.join(VALID_SCOPES)}"
                )
            if token == "all":
                # Keep "all" itself so the plan can be reported, but rely on
                # SCOPE_TARGETS to enumerate paths.
                if "all" not in seen:
                    seen.append("all")
                continue
            if token not in seen:
                seen.append(token)
    return seen


def _path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def build_plan(scopes: Sequence[str], root: Path = REPO_ROOT) -> ResetPlan:
    expanded = expand_scopes(scopes)
    seen_paths: set[str] = set()
    targets: list[ResetTarget] = []
    for scope in expanded:
        for rel in SCOPE_TARGETS[scope]:
            if rel in seen_paths:
                continue
            seen_paths.add(rel)
            abs_path = (root / rel).resolve()
            exists = abs_path.exists()
            targets.append(
                ResetTarget(
                    rel_path=rel,
                    abs_path=abs_path,
                    exists=exists,
                    size_bytes=_path_size(abs_path) if exists else 0,
                    is_dir=abs_path.is_dir() if exists else rel.endswith("/"),
                )
            )
    return ResetPlan(scopes=expanded, targets=targets)


# ---------------------------------------------------------------------------
# Execute


def execute_plan(
    plan: ResetPlan,
    *,
    confirm: bool,
    root: Path = REPO_ROOT,
    trash_dir: Path | None = None,
    timestamp: str | None = None,
) -> dict:
    """Move existing targets into the trash directory.

    Returns a summary dict regardless of confirm/dry-run, so callers (CLI,
    tests, API) can render a uniform report.
    """
    if trash_dir is None:
        trash_dir = root / TRASH_ROOT_REL
    if timestamp is None:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
    batch_dir = trash_dir / timestamp

    moved: list[dict] = []
    skipped: list[dict] = []

    for target in plan.targets:
        if not target.exists:
            skipped.append({"path": target.rel_path, "reason": "missing"})
            continue
        # Guard against deleting trash itself if someone asks for results/*
        try:
            target.abs_path.relative_to(trash_dir.resolve())
            skipped.append({"path": target.rel_path, "reason": "inside_trash"})
            continue
        except ValueError:
            pass

        if not confirm:
            moved.append(
                {
                    "path": target.rel_path,
                    "size_bytes": target.size_bytes,
                    "would_move_to": str(batch_dir / target.rel_path),
                }
            )
            continue

        dest = batch_dir / target.rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target.abs_path), str(dest))
        moved.append(
            {
                "path": target.rel_path,
                "size_bytes": target.size_bytes,
                "moved_to": str(dest),
            }
        )

    return {
        "scopes": plan.scopes,
        "confirm": confirm,
        "trash_batch": str(batch_dir),
        "moved": moved,
        "skipped": skipped,
        "total_bytes": plan.total_bytes,
    }


def purge_old_trash(
    trash_dir: Path,
    *,
    older_than_days: int = DEFAULT_PURGE_AFTER_DAYS,
    now: float | None = None,
) -> list[str]:
    """Permanently delete trash batches older than the threshold."""
    if not trash_dir.exists():
        return []
    cutoff = (now if now is not None else time.time()) - older_than_days * 86400
    removed: list[str] = []
    for child in trash_dir.iterdir():
        try:
            if child.stat().st_mtime < cutoff:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed.append(str(child))
        except OSError:
            continue
    return removed


# ---------------------------------------------------------------------------
# CLI


def _format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def render_plan(plan: ResetPlan) -> str:
    lines = [f"Scopes: {', '.join(plan.scopes) or '(none)'}"]
    if not plan.targets:
        lines.append("(no targets resolved)")
        return "\n".join(lines)
    for target in plan.targets:
        marker = "✓" if target.exists else "·"
        size = _format_size(target.size_bytes) if target.exists else "—"
        lines.append(f"  [{marker}] {target.rel_path} ({size})")
    lines.append(f"Total reclaimable: {_format_size(plan.total_bytes)}")
    return "\n".join(lines)


def render_result(summary: dict) -> str:
    head = (
        f"Mode: {'CONFIRMED' if summary['confirm'] else 'DRY-RUN'} | "
        f"Trash batch: {summary['trash_batch']}"
    )
    moved = summary["moved"]
    skipped = summary["skipped"]
    lines = [head, f"Moved/Would move: {len(moved)} | Skipped: {len(skipped)}"]
    for item in moved:
        action = "moved" if "moved_to" in item else "would move"
        dest = item.get("moved_to") or item.get("would_move_to")
        lines.append(f"  - {action} {item['path']} → {dest}")
    for item in skipped:
        lines.append(f"  - skipped {item['path']} ({item['reason']})")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reset AIMiner mining artifacts.")
    parser.add_argument(
        "--scope",
        action="append",
        default=None,
        choices=VALID_SCOPES,
        help="Scope(s) to reset. Repeat or comma-separate. Defaults to 'pool'.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually move targets into .trash. Without this, runs in dry-run mode.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Project root (default: %(default)s)",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Also permanently delete trash batches older than --purge-after-days.",
    )
    parser.add_argument(
        "--purge-after-days",
        type=int,
        default=DEFAULT_PURGE_AFTER_DAYS,
        help="Threshold (days) for --purge (default: %(default)s).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    scopes = args.scope or ["pool"]
    try:
        plan = build_plan(scopes, root=args.root)
    except ValueError as exc:
        print(f"[reset] {exc}", file=sys.stderr)
        return 2

    print(render_plan(plan))
    summary = execute_plan(plan, confirm=args.confirm, root=args.root)
    print()
    print(render_result(summary))

    if args.purge:
        trash_dir = args.root / TRASH_ROOT_REL
        removed = purge_old_trash(trash_dir, older_than_days=args.purge_after_days)
        print(f"\nPurged {len(removed)} trash batches older than {args.purge_after_days}d")
        for path in removed:
            print(f"  - removed {path}")

    if not args.confirm:
        print("\nDry-run only. Re-run with --confirm to actually move the targets.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
