import os
import tempfile
import unittest
from pathlib import Path

from scripts.reset_workspace import (
    DEFAULT_PURGE_AFTER_DAYS,
    SCOPE_TARGETS,
    build_plan,
    execute_plan,
    expand_scopes,
    purge_old_trash,
)


def _seed(root: Path, rel_path: str, content: bytes = b"x") -> Path:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def _seed_dir(root: Path, rel_dir: str, files: int = 2) -> Path:
    target = root / rel_dir
    target.mkdir(parents=True, exist_ok=True)
    for i in range(files):
        (target / f"f{i}.bin").write_bytes(b"x" * 16)
    return target


class TestExpandScopes(unittest.TestCase):
    def test_default_known_scopes(self):
        self.assertEqual(expand_scopes(["pool"]), ["pool"])

    def test_dedupes(self):
        self.assertEqual(expand_scopes(["pool", "pool"]), ["pool"])

    def test_comma_separated(self):
        self.assertEqual(
            expand_scopes(["pool,memory"]), ["pool", "memory"]
        )

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            expand_scopes(["nope"])

    def test_all_kept_as_token(self):
        self.assertEqual(expand_scopes(["all"]), ["all"])


class TestBuildPlan(unittest.TestCase):
    def test_pool_scope_lists_pool_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed(root, "results/alpha_miner.db", b"db")
            _seed_dir(root, "results/reports", files=3)

            plan = build_plan(["pool"], root=root)

            rels = [t.rel_path for t in plan.targets]
            for expected in SCOPE_TARGETS["pool"]:
                self.assertIn(expected, rels)
            existing = {t.rel_path for t in plan.existing}
            self.assertIn("results/alpha_miner.db", existing)
            self.assertIn("results/reports", existing)
            self.assertGreater(plan.total_bytes, 0)

    def test_all_scope_unions_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_plan(["all"], root=root)
            rels = {t.rel_path for t in plan.targets}
            self.assertEqual(rels, set(SCOPE_TARGETS["all"]))

    def test_dedupes_across_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_plan(["pool", "all"], root=root)
            rels = [t.rel_path for t in plan.targets]
            # No path appears twice even though "all" overlaps "pool".
            self.assertEqual(len(rels), len(set(rels)))

    def test_runs_scope_targets_real_swarm_runs_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed(root, "results/swarm_runs/run-1.jsonl", b"log")
            legacy_root_run = _seed(root, "swarm_runs/legacy.jsonl", b"legacy")

            plan = build_plan(["runs"], root=root)
            rels = [t.rel_path for t in plan.targets]

            self.assertEqual(rels, ["results/swarm_runs"])
            summary = execute_plan(
                plan,
                confirm=True,
                root=root,
                timestamp="20260101-000000",
            )

            self.assertFalse((root / "results" / "swarm_runs").exists())
            self.assertTrue(legacy_root_run.exists())
            self.assertEqual(
                summary["moved"][0]["path"],
                "results/swarm_runs",
            )
            self.assertTrue(
                (
                    root
                    / "results"
                    / ".trash"
                    / "20260101-000000"
                    / "results"
                    / "swarm_runs"
                    / "run-1.jsonl"
                ).exists()
            )


class TestExecutePlan(unittest.TestCase):
    def test_dry_run_does_not_move_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = _seed(root, "results/alpha_miner.db", b"db_payload")
            reports = _seed_dir(root, "results/reports", files=2)

            plan = build_plan(["pool"], root=root)
            summary = execute_plan(plan, confirm=False, root=root, timestamp="20260101-000000")

            self.assertFalse(summary["confirm"])
            self.assertTrue(db.exists())
            self.assertTrue(reports.exists())
            # Nothing actually moved.
            trash = root / "results" / ".trash"
            self.assertFalse(trash.exists() and any(trash.iterdir()))
            # But the report describes what would happen.
            paths = {item["path"] for item in summary["moved"]}
            self.assertIn("results/alpha_miner.db", paths)
            self.assertIn("results/reports", paths)
            for item in summary["moved"]:
                self.assertIn("would_move_to", item)

    def test_confirm_moves_into_trash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = _seed(root, "results/alpha_miner.db", b"db_payload")
            reports = _seed_dir(root, "results/reports", files=2)

            plan = build_plan(["pool"], root=root)
            summary = execute_plan(plan, confirm=True, root=root, timestamp="20260101-000000")

            self.assertTrue(summary["confirm"])
            self.assertFalse(db.exists())
            self.assertFalse(reports.exists())
            trash_batch = root / "results" / ".trash" / "20260101-000000"
            self.assertTrue((trash_batch / "results" / "alpha_miner.db").exists())
            self.assertTrue((trash_batch / "results" / "reports").is_dir())
            # Each moved item carries its destination.
            for item in summary["moved"]:
                self.assertIn("moved_to", item)

    def test_skips_missing_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_plan(["pool"], root=root)
            summary = execute_plan(plan, confirm=True, root=root)
            # Nothing exists, so everything is skipped, nothing moved.
            self.assertEqual(summary["moved"], [])
            self.assertGreater(len(summary["skipped"]), 0)
            for item in summary["skipped"]:
                self.assertEqual(item["reason"], "missing")

    def test_does_not_eat_its_own_trash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Pre-create a trash file under the path that "all" scope would target
            # (results/strategies). Make sure execute_plan never tries to move
            # things that already live inside .trash.
            trash_marker = root / "results" / ".trash" / "old-batch" / "marker.txt"
            trash_marker.parent.mkdir(parents=True, exist_ok=True)
            trash_marker.write_bytes(b"old")

            plan = build_plan(["all"], root=root)
            summary = execute_plan(plan, confirm=True, root=root, timestamp="20260101-000000")

            # Trash content untouched.
            self.assertTrue(trash_marker.exists())
            for item in summary["moved"]:
                self.assertNotIn(".trash", item.get("moved_to", ""))


class TestPurgeOldTrash(unittest.TestCase):
    def test_only_removes_old_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            trash = Path(tmp)
            old = trash / "old-batch"
            new = trash / "new-batch"
            old.mkdir()
            new.mkdir()
            (old / "x.txt").write_bytes(b"x")
            (new / "x.txt").write_bytes(b"x")

            old_mtime = (
                # 30 days ago
                int(__import__("time").time()) - DEFAULT_PURGE_AFTER_DAYS * 86400 - 86400
            )
            os.utime(old, (old_mtime, old_mtime))

            removed = purge_old_trash(trash, older_than_days=DEFAULT_PURGE_AFTER_DAYS)
            self.assertEqual(len(removed), 1)
            self.assertFalse(old.exists())
            self.assertTrue(new.exists())

    def test_missing_trash_dir_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            removed = purge_old_trash(Path(tmp) / "does-not-exist")
            self.assertEqual(removed, [])


if __name__ == "__main__":
    unittest.main()
