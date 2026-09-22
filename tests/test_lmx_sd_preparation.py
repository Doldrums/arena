"""Asset acquisition uses only reviewed public origins and rejects unsafe plans."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prepare_lmx_sd_assets", ROOT / "scripts/deployment/prepare_lmx_sd_assets.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def lock():
    return json.loads((ROOT / "tasks/adapters/lmx_sd_assets.json").read_text())


def test_checked_in_lock_contains_full_pipeline_and_license():
    value = prepare.validate_lock(lock())
    assert len(value["files"]) == 17
    assert "safety_checker/pytorch_model.bin" in value["files"]
    assert "tokenizer/vocab.json" in value["files"]
    assert "LICENSE_SD.txt" in value["files"]
    assert sum(x["size"] for x in value["files"].values()) == 2742615730


@pytest.mark.parametrize("change", ["path", "host", "revision", "gated", "size"])
def test_unsafe_or_unreviewed_download_plan_is_rejected(change):
    value = copy.deepcopy(lock())
    if change == "path":
        value["files"]["../model.bin"] = value["files"].pop("model_index.json")
    elif change == "host":
        value["files"]["model_index.json"]["url"] = "https://example.invalid/model"
    elif change == "revision":
        value["revision"] = "main"
    elif change == "gated":
        value["gated"] = True
    else:
        value["files"]["model_index.json"]["size"] = -1
    with pytest.raises(ValueError):
        prepare.validate_lock(value)


def test_existing_asset_directory_is_not_overwritten(tmp_path):
    manifest = tmp_path / "lock.json"
    manifest.write_text(json.dumps(lock()))
    with pytest.raises(ValueError, match="new absolute"):
        prepare.prepare(manifest, tmp_path)


def test_private_seed_evidence_binds_current_code_without_granting_readiness():
    evidence = json.loads((ROOT / "tasks/validation/lmx-sd14-seed-probes.json").read_text())
    assert evidence["canonical_admission"] is False
    assert evidence["paper_reproduction"] is False
    assert evidence["model_usage"] == {"diffusion_images": 9, "llm_calls": 0, "external_api_calls": 0}
    for relative, expected in evidence["code_sha256"].items():
        assert hashlib.sha256((ROOT / "tasks" / relative).read_bytes()).hexdigest() == expected
    assert evidence["model_asset_lock_sha256"] == hashlib.sha256(
        (ROOT / "tasks/adapters/lmx_sd_assets.json").read_bytes()).hexdigest()
    for color in ("red", "green", "blue"):
        task_id = "lmx-stable-diffusion-excess-" + color
        records = [row for row in evidence["evaluations"] if row["task_id"] == task_id]
        assert {row["repeat"] for row in records} == {1, 2, 3}
        assert len({row["raw_score"] for row in records}) == 1
        assert all(row["valid"] and row["safety_checker_enabled"] for row in records)
        task = json.loads((ROOT / "tasks/suite" / task_id / "task.json").read_text())
        assert task["status"] == "requires_setup"
        assert task["validation"]["canonical_readiness"] == "pending_gpu_profile_admission"
