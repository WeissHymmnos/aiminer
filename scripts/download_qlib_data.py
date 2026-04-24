from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


COMMON_REQUIRED_FIELDS = ("open.day.bin", "high.day.bin", "low.day.bin", "close.day.bin", "volume.day.bin", "factor.day.bin")
CN_REQUIRED_FIELDS = COMMON_REQUIRED_FIELDS + ("amount.day.bin", "vwap.day.bin")

ARCHIVE_NAMES = {
    "cn": "qlib_bin.tar.gz",
    "us": "qlib_data_us_1d_latest.zip",
}


def default_target_dir(region: str, target_root: str | None = None) -> Path:
    root = Path(os.path.expanduser(target_root or "~/.qlib/qlib_data"))
    return root / ("cn_data" if region == "cn" else "us_data")


def download_url(region: str, release: str, source: str) -> str:
    archive = ARCHIVE_NAMES[region]
    if source == "qlib":
        dataset_release = "v2" if release == "latest" else release
        return f"https://github.com/SunsetWolf/qlib_dataset/releases/download/{dataset_release}/{archive}"
    if release == "latest":
        return f"https://github.com/chenditc/investment_data/releases/latest/download/{archive}"
    return f"https://github.com/chenditc/investment_data/releases/download/{release}/{archive}"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def download_archive(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".part")
    if tmp_path.exists():
        tmp_path.unlink()

    if shutil.which("curl"):
        _run(["curl", "-L", "--fail", "--retry", "3", "-o", str(tmp_path), url])
    elif shutil.which("wget"):
        _run(["wget", "-O", str(tmp_path), url])
    else:
        raise RuntimeError("Neither curl nor wget is available.")

    tmp_path.replace(output_path)


def extract_archive(archive_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".zip":
        print(f"+ unzip {archive_path} -d {target_dir}", flush=True)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(target_dir)
        return
    _run(["tar", "-xzf", str(archive_path), "-C", str(target_dir), "--strip-components=1"])


def validate_qlib_data(target_dir: Path, *, region: str) -> dict[str, object]:
    calendars_dir = target_dir / "calendars"
    features_dir = target_dir / "features"
    instruments_dir = target_dir / "instruments"
    calendar_path = calendars_dir / "day.txt"
    required_fields = CN_REQUIRED_FIELDS if region == "cn" else COMMON_REQUIRED_FIELDS

    summary: dict[str, object] = {
        "target_dir": str(target_dir),
        "region": region,
        "exists": target_dir.exists(),
        "calendar_exists": calendar_path.exists(),
        "features_exists": features_dir.exists(),
        "instruments_exists": instruments_dir.exists(),
        "required_fields": list(required_fields),
        "calendar_count": 0,
        "calendar_first": None,
        "calendar_last": None,
        "feature_instruments": 0,
        "missing_required_field_dirs": 0,
        "missing_required_field_examples": [],
        "instrument_files": {},
    }

    if calendar_path.exists():
        lines = [line.strip() for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        summary["calendar_count"] = len(lines)
        summary["calendar_first"] = lines[0] if lines else None
        summary["calendar_last"] = lines[-1] if lines else None

    if features_dir.exists():
        feature_dirs = sorted(path for path in features_dir.iterdir() if path.is_dir())
        summary["feature_instruments"] = len(feature_dirs)
        examples: list[dict[str, object]] = []
        missing_count = 0
        for path in feature_dirs:
            files = {item.name for item in path.iterdir() if item.is_file()}
            missing = [field for field in required_fields if field not in files]
            if missing:
                missing_count += 1
                if len(examples) < 10:
                    examples.append({"instrument": path.name, "missing": missing})
        summary["missing_required_field_dirs"] = missing_count
        summary["missing_required_field_examples"] = examples

    if instruments_dir.exists():
        files_summary: dict[str, int] = {}
        for path in sorted(instruments_dir.glob("*.txt")):
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            files_summary[path.name] = len(lines)
        summary["instrument_files"] = files_summary

    return summary


def install_region(
    region: str,
    *,
    target_root: str | None,
    target_dir: str | None,
    release: str,
    archive: str | None,
    source: str,
    validate_only: bool,
    keep_archive: bool,
) -> int:
    if target_dir and region == "all":
        raise ValueError("--target-dir cannot be used with region=all")

    destination = Path(os.path.expanduser(target_dir)) if target_dir else default_target_dir(region, target_root)
    resolved_source = "chenditc" if source == "auto" and region == "cn" else "qlib" if source == "auto" else source
    url = download_url(region, release, resolved_source)
    archive_path = Path(os.path.expanduser(archive)) if archive else destination.parent / ARCHIVE_NAMES[region]

    print(f"Region: {region}")
    print(f"Target: {destination}")
    print(f"Source type: {resolved_source}")
    print(f"Source: {url}")

    if not validate_only:
        if archive:
            print(f"Using existing archive: {archive_path}")
        else:
            download_archive(url, archive_path)
        extract_archive(archive_path, destination)
        if not keep_archive and archive_path.exists() and not archive:
            archive_path.unlink()

    summary = validate_qlib_data(destination, region=region)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not summary["exists"] or not summary["calendar_exists"] or not summary["features_exists"]:
        return 1
    if int(summary["feature_instruments"]) <= 0 or int(summary["missing_required_field_dirs"]) > 0:
        return 1
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download and validate Qlib binary market data.")
    parser.add_argument("region", nargs="?", default="cn", choices=("cn", "us", "all"))
    parser.add_argument("--release", default="latest", help="GitHub release tag, or 'latest'. For --source qlib, latest maps to v2/latest asset names.")
    parser.add_argument("--source", default="auto", choices=("auto", "chenditc", "qlib"), help="Download source. auto uses chenditc for CN and qlib_dataset for US.")
    parser.add_argument("--target-root", default=None, help="Root containing cn_data/us_data. Defaults to ~/.qlib/qlib_data.")
    parser.add_argument("--target-dir", default=None, help="Exact output directory for one region.")
    parser.add_argument("--archive", default=None, help="Use an existing local tar.gz instead of downloading.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing data.")
    parser.add_argument("--keep-archive", action="store_true", help="Keep downloaded tar.gz after extraction.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    regions = ("cn", "us") if args.region == "all" else (args.region,)
    rc = 0
    for region in regions:
        rc = max(
            rc,
            install_region(
                region,
                target_root=args.target_root,
                target_dir=args.target_dir,
                release=args.release,
                archive=args.archive,
                source=args.source,
                validate_only=args.validate_only,
                keep_archive=args.keep_archive,
            ),
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
