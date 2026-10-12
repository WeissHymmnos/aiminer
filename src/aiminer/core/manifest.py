"""Reproducible Run Manifest generation and environment verification."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Dict, Optional
import uuid

from aiminer.core.exceptions import ManifestError


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _get_git_info(repo_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    """Safely query git commit, branch, and dirty status."""
    cwd = str(repo_dir) if repo_dir else None
    git_info: Dict[str, Any] = {
        "commit": "unknown",
        "branch": "unknown",
        "is_dirty": False,
    }
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if res.returncode == 0:
            git_info["commit"] = res.stdout.strip()
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if res.returncode == 0:
            git_info["branch"] = res.stdout.strip()
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if res.returncode == 0:
            git_info["is_dirty"] = bool(res.stdout.strip())
    except Exception:
        pass

    return git_info


def _get_hardware_and_env() -> Dict[str, Any]:
    """Capture hardware and runtime environment metadata."""
    env_info: Dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count() or 1,
        "memory_total_bytes": None,
        "torch_available": False,
        "cuda_available": False,
        "cuda_device_count": 0,
        "gpu_name": None,
    }

    try:
        import psutil

        env_info["memory_total_bytes"] = psutil.virtual_memory().total
    except Exception:
        pass

    try:
        import torch

        env_info["torch_available"] = True
        env_info["torch_version"] = getattr(torch, "__version__", "unknown")
        cuda_ok = torch.cuda.is_available()
        env_info["cuda_available"] = cuda_ok
        if cuda_ok:
            env_info["cuda_device_count"] = torch.cuda.device_count()
            if env_info["cuda_device_count"] > 0:
                env_info["gpu_name"] = torch.cuda.get_device_name(0)
    except Exception:
        pass

    return env_info


def _compute_hash(data: Any) -> str:
    """Compute deterministic SHA-256 hash of JSON-serializable data."""
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class RunManifest:
    """Reproducibility run manifest capturing full execution environment."""

    run_id: str
    created_at: str
    git_commit: str
    git_branch: str
    git_dirty: bool
    random_seed: int
    date_window: Dict[str, str]
    market_profile: str
    market_mode: str
    llm_config: Dict[str, Any]
    prompt_info: Dict[str, Any]
    environment: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunManifest:
        """Construct a RunManifest from dictionary."""
        required = [
            "run_id",
            "git_commit",
            "random_seed",
            "market_profile",
            "market_mode",
            "llm_config",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ManifestError(
                f"Missing required manifest field(s): {', '.join(missing)}"
            )

        return cls(
            run_id=str(data["run_id"]),
            created_at=str(data.get("created_at") or _now_iso()),
            git_commit=str(data["git_commit"]),
            git_branch=str(data.get("git_branch", "unknown")),
            git_dirty=bool(data.get("git_dirty", False)),
            random_seed=int(data["random_seed"]),
            date_window=dict(data.get("date_window") or {}),
            market_profile=str(data["market_profile"]),
            market_mode=str(data["market_mode"]),
            llm_config=dict(data.get("llm_config") or {}),
            prompt_info=dict(data.get("prompt_info") or {}),
            environment=dict(data.get("environment") or {}),
            metadata=dict(data.get("metadata") or {}),
        )

    def manifest_hash(self) -> str:
        """Compute reproducibility hash of key execution parameters."""
        reproducibility_payload = {
            "git_commit": self.git_commit,
            "random_seed": self.random_seed,
            "date_window": self.date_window,
            "market_profile": self.market_profile,
            "market_mode": self.market_mode,
            "llm_config": self.llm_config,
            "prompt_info": self.prompt_info,
        }
        return _compute_hash(reproducibility_payload)

    def diff(self, other: RunManifest) -> Dict[str, Any]:
        """Compute key parameter diff against another manifest."""
        differences: Dict[str, Any] = {}
        for attr in (
            "git_commit",
            "git_dirty",
            "random_seed",
            "date_window",
            "market_profile",
            "market_mode",
            "llm_config",
            "prompt_info",
        ):
            val_self = getattr(self, attr)
            val_other = getattr(other, attr)
            if val_self != val_other:
                differences[attr] = {
                    "self": val_self,
                    "other": val_other,
                }
        return differences

    def save(self, path: str | Path) -> Path:
        """Save manifest atomically to JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
            return target
        except Exception as e:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise ManifestError(
                f"Failed to write run manifest to {target}: {e}"
            ) from e

    @classmethod
    def load(cls, path: str | Path) -> RunManifest:
        """Load manifest from JSON file."""
        target = Path(path)
        if not target.exists():
            raise ManifestError(f"Run manifest file not found: {target}")
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            if isinstance(e, ManifestError):
                raise
            raise ManifestError(
                f"Failed to load run manifest from {target}: {e}"
            ) from e


def generate_run_manifest(
    run_id: Optional[str] = None,
    seed: int = 42,
    market_start: str = "2020-01-01",
    market_end: str = "2023-12-31",
    market_profile: str = "cn_stock",
    market_mode: str = "single",
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o",
    llm_temperature: float = 0.7,
    llm_reasoning_effort: Optional[str] = None,
    prompt_version: Optional[str] = None,
    prompt_template: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    repo_dir: Optional[Path | str] = None,
) -> RunManifest:
    """Generate a reproducible run manifest for a mining run."""
    rid = run_id or f"run_{uuid.uuid4().hex[:12]}"
    git_info = _get_git_info(repo_dir=repo_dir)
    env_info = _get_hardware_and_env()

    date_window = {
        "market_start": market_start,
        "market_end": market_end,
    }

    llm_cfg: Dict[str, Any] = {
        "provider": llm_provider,
        "model": llm_model,
        "temperature": float(llm_temperature),
        "reasoning_effort": llm_reasoning_effort,
    }

    prompt_info: Dict[str, Any] = {
        "version": prompt_version or "1.0.0",
        "template_hash": (
            _compute_hash(prompt_template)
            if prompt_template is not None
            else None
        ),
    }

    return RunManifest(
        run_id=rid,
        created_at=_now_iso(),
        git_commit=git_info["commit"],
        git_branch=git_info["branch"],
        git_dirty=git_info["is_dirty"],
        random_seed=int(seed),
        date_window=date_window,
        market_profile=market_profile,
        market_mode=market_mode,
        llm_config=llm_cfg,
        prompt_info=prompt_info,
        environment=env_info,
        metadata=dict(metadata or {}),
    )
