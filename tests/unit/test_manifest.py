"""Unit tests for reproducible run manifest generation and environment capture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiminer.core.exceptions import ManifestError
from aiminer.core.manifest import RunManifest, generate_run_manifest


def test_generate_run_manifest_defaults():
    manifest = generate_run_manifest()
    assert manifest.run_id.startswith("run_")
    assert manifest.random_seed == 42
    assert manifest.date_window["market_start"] == "2020-01-01"
    assert manifest.date_window["market_end"] == "2023-12-31"
    assert manifest.market_profile == "cn_stock"
    assert manifest.market_mode == "single"
    assert manifest.llm_config["provider"] == "openai"
    assert manifest.llm_config["model"] == "gpt-4o"
    assert "python_version" in manifest.environment
    assert "platform" in manifest.environment
    assert manifest.git_commit is not None


def test_generate_run_manifest_custom_params():
    manifest = generate_run_manifest(
        run_id="custom_run_123",
        seed=1007,
        market_start="2021-06-01",
        market_end="2022-06-01",
        market_profile="us_stock",
        market_mode="batch",
        llm_provider="deepseek",
        llm_model="deepseek-chat",
        llm_temperature=0.2,
        llm_reasoning_effort="high",
        prompt_version="2.1.0",
        prompt_template="Generate momentum factor based on volume",
        metadata={"user": "quant_tester"},
    )
    assert manifest.run_id == "custom_run_123"
    assert manifest.random_seed == 1007
    assert manifest.date_window["market_start"] == "2021-06-01"
    assert manifest.date_window["market_end"] == "2022-06-01"
    assert manifest.market_profile == "us_stock"
    assert manifest.market_mode == "batch"
    assert manifest.llm_config["provider"] == "deepseek"
    assert manifest.llm_config["model"] == "deepseek-chat"
    assert manifest.llm_config["temperature"] == 0.2
    assert manifest.llm_config["reasoning_effort"] == "high"
    assert manifest.prompt_info["version"] == "2.1.0"
    assert manifest.prompt_info["template_hash"] is not None
    assert manifest.metadata["user"] == "quant_tester"


def test_manifest_hash_reproducibility():
    m1 = generate_run_manifest(
        run_id="run_a",
        seed=42,
        market_start="2020-01-01",
        market_end="2022-12-31",
    )
    m2 = generate_run_manifest(
        # different run_id should not affect reproducibility hash
        run_id="run_b",
        seed=42,
        market_start="2020-01-01",
        market_end="2022-12-31",
    )
    # Different run_id, but identical inputs -> identical reproducibility hash
    assert m1.manifest_hash() == m2.manifest_hash()

    # Different seed -> different hash
    m3 = generate_run_manifest(
        run_id="run_c",
        seed=999,
        market_start="2020-01-01",
        market_end="2022-12-31",
    )
    assert m1.manifest_hash() != m3.manifest_hash()


def test_manifest_diff():
    m1 = generate_run_manifest(seed=42, llm_model="gpt-4o")
    m2 = generate_run_manifest(seed=43, llm_model="gpt-4o-mini")

    differences = m1.diff(m2)
    assert "random_seed" in differences
    assert differences["random_seed"] == {"self": 42, "other": 43}
    assert "llm_config" in differences
    assert differences["llm_config"]["self"]["model"] == "gpt-4o"
    assert differences["llm_config"]["other"]["model"] == "gpt-4o-mini"


def test_manifest_save_and_load(tmp_path: Path):
    manifest = generate_run_manifest(
        run_id="save_load_test",
        seed=777,
        prompt_template="Some prompt content",
    )
    manifest_file = tmp_path / "run_manifest.json"
    manifest.save(manifest_file)
    assert manifest_file.exists()

    loaded = RunManifest.load(manifest_file)
    assert loaded.run_id == "save_load_test"
    assert loaded.random_seed == 777
    assert (
        loaded.prompt_info["template_hash"]
        == (manifest.prompt_info["template_hash"])
    )
    assert loaded.manifest_hash() == manifest.manifest_hash()


def test_manifest_missing_required_fields():
    invalid_data = {
        "run_id": "bad_run",
        # missing git_commit, random_seed, etc.
    }
    with pytest.raises(ManifestError, match="Missing required manifest field"):
        RunManifest.from_dict(invalid_data)


def test_manifest_nonexistent_file_load(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist.json"
    with pytest.raises(ManifestError, match="not found"):
        RunManifest.load(nonexistent)


def test_manifest_corrupted_json(tmp_path: Path):
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("{ corrupt json ...", encoding="utf-8")
    with pytest.raises(ManifestError, match="Failed to load run manifest"):
        RunManifest.load(bad_file)


def test_manifest_universe_support(tmp_path: Path):
    manifest = generate_run_manifest(
        run_id="run_univ_test",
        universe="csi300",
        market_profile="cn_stock",
    )
    assert manifest.universe == "csi300"
    manifest_file = tmp_path / "univ_manifest.json"
    manifest.save(manifest_file)

    loaded = RunManifest.load(manifest_file)
    assert loaded.universe == "csi300"

    # Verify diff detects universe difference
    other = generate_run_manifest(run_id="run_univ_test", universe="csi500")
    diff = manifest.diff(other)
    assert "universe" in diff
    assert diff["universe"] == {"self": "csi300", "other": "csi500"}
