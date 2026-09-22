"""Full-image metric fixtures and child/asset integrity gates; no model calls."""
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "suite/_lib"))
from autoresearch_suite import lmx_sd, lmx_sd_assets


@pytest.mark.parametrize("channel,index", [("r", 0), ("g", 1), ("b", 2)])
def test_entire_image_contributes_to_original_excess_metric(channel, index):
    image = np.zeros((512, 512, 3), dtype=np.uint8)
    image[:, :, index] = 255
    score, digest = lmx_sd.excess_color(image, channel)
    assert score == 66846720
    assert digest == hashlib.sha256(image.tobytes()).hexdigest()
    image[511, 511, (index + 1) % 3] = 200
    assert lmx_sd.excess_color(image, channel)[0] == 66846620


def test_safety_filtered_black_image_is_valid_zero_not_missing():
    image = np.zeros((512, 512, 3), dtype=np.uint8)
    assert lmx_sd.excess_color(image, "r")[0] == 0
    # A white image has zero excess even though each channel is maximal.
    image.fill(255)
    assert lmx_sd.excess_color(image, "g")[0] == 0


@pytest.mark.parametrize("image", [np.zeros((256, 256, 3), dtype=np.uint8),
                                   np.zeros((512, 512, 4), dtype=np.uint8),
                                   np.zeros((512, 512, 3), dtype=np.float32)])
def test_no_downsampled_or_float_or_alpha_image_can_be_scored(image):
    with pytest.raises(ValueError, match="complete"):
        lmx_sd.excess_color(image, "r")


def assets_fixture(tmp_path):
    root = (tmp_path / "model").resolve()
    root.mkdir(mode=0o700)
    data = b"fixed model bytes"
    target = root / "model_index.json"
    target.write_bytes(data)
    target.chmod(0o444)
    root.chmod(0o555)
    manifest = tmp_path / "lock.json"
    manifest.write_text(json.dumps({"schema": "arena.lmx-sd-assets/1",
        "model_id": "CompVis/stable-diffusion-v1-4", "revision": lmx_sd_assets.REVISION,
        "files": {"model_index.json": {"size": len(data),
                   "sha256": hashlib.sha256(data).hexdigest()}}}))
    return root, target, manifest


def test_asset_bytes_are_verified_before_model_loading(tmp_path):
    root, target, manifest = assets_fixture(tmp_path)
    assert lmx_sd_assets.verify_assets(root, manifest_path=manifest)[1]["verified_files"] == 1
    target.chmod(0o644)
    target.write_bytes(b"wrong model bytes")
    target.chmod(0o444)
    with pytest.raises(ValueError, match="integrity"):
        lmx_sd_assets.verify_assets(root, manifest_path=manifest)


def test_asset_symlink_and_parent_escape_are_rejected(tmp_path):
    root, target, manifest = assets_fixture(tmp_path)
    root.chmod(0o755)
    target.unlink()
    target.symlink_to(manifest)
    root.chmod(0o555)
    with pytest.raises(ValueError, match="symlink"):
        lmx_sd_assets.verify_assets(root, manifest_path=manifest)
    root.chmod(0o755)
    target.unlink()
    root.chmod(0o555)
    value = json.loads(manifest.read_text())
    value["files"]["../lock.json"] = value["files"].pop("model_index.json")
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="inventory|Unsafe"):
        lmx_sd_assets.verify_assets(root, manifest_path=manifest)


def test_writable_model_file_is_rejected_even_if_hash_matches(tmp_path):
    root, target, manifest = assets_fixture(tmp_path)
    target.chmod(0o644)
    with pytest.raises(ValueError, match="immutable"):
        lmx_sd_assets.verify_assets(root, manifest_path=manifest)


def test_unlisted_weight_index_cannot_redirect_pipeline_loading(tmp_path):
    root, target, manifest = assets_fixture(tmp_path)
    root.chmod(0o755)
    extra = root / "pytorch_model.bin.index.json"
    extra.write_text('{"weight_map":{"model":"untrusted.bin"}}')
    extra.chmod(0o444)
    root.chmod(0o555)
    with pytest.raises(ValueError, match="inventory"):
        lmx_sd_assets.verify_assets(root, manifest_path=manifest)


linux = pytest.mark.skipif(sys.platform != "linux", reason="Linux resource-limit subprocess")


@linux
def test_candidate_cannot_mutate_parent_grader_state(tmp_path):
    path = tmp_path / "candidate.py"
    path.write_text("import os\nos.environ['LMX_TEST_POISON']='yes'\n"
                    "def candidate():\n    print('incidental stdout')\n    return 'A landscape.'\n")
    assert lmx_sd.candidate_prompt(path) == "A landscape."
    assert "LMX_TEST_POISON" not in os.environ


@linux
@pytest.mark.parametrize("body", ["return {'score': 1e99}", "return b'image bytes'",
                                  "return 'x'*4097", "raise RuntimeError('bad candidate')"])
def test_only_a_bounded_string_is_a_candidate_result(tmp_path, body):
    path = tmp_path / "candidate.py"
    path.write_text("def candidate():\n    " + body + "\n")
    with pytest.raises(ValueError):
        lmx_sd.candidate_prompt(path)


@linux
def test_raw_stdout_flood_is_bounded_in_parent(tmp_path):
    path = tmp_path / "candidate.py"
    path.write_text("import os\nwhile True: os.write(1,b'x'*4096)\n")
    with pytest.raises(ValueError, match="output limit"):
        lmx_sd.candidate_prompt(path)


@linux
def test_hanging_candidate_is_killed_without_loading_model(tmp_path):
    path = tmp_path / "candidate.py"
    path.write_text("import time\ndef candidate():\n    time.sleep(30)\n")
    with pytest.raises(TimeoutError):
        lmx_sd.candidate_prompt(path, timeout=0.1)


@pytest.mark.skipif(sys.platform != "linux" or os.geteuid() != 0,
                    reason="Demonstrates cleanup when root bypasses RLIMIT_NPROC")
def test_exited_leader_cannot_leave_a_sleeping_descendant(tmp_path):
    import time
    path = tmp_path / "candidate.py"
    path.write_text("import os,time,json\npid=os.fork()\nif pid==0:\n"
                    " os.close(1);os.close(2);time.sleep(30);os._exit(0)\n"
                    "os.write(1,json.dumps({'prompt':str(pid)}).encode());os._exit(0)\n")
    child_pid = int(lmx_sd.candidate_prompt(path))
    status = Path(f"/proc/{child_pid}/stat")
    for _ in range(100):
        if not status.exists() or status.read_text().split()[2] == "Z":
            break
        time.sleep(0.01)
    else:
        pytest.fail("Candidate descendant survived after its leader exited")


def test_three_tasks_preserve_full_generation_contract_and_share_neutral_seed():
    seeds = set()
    for color, channel in [("red", "r"), ("green", "g"), ("blue", "b")]:
        task = ROOT / "suite" / f"lmx-stable-diffusion-excess-{color}"
        problem = json.loads((task / "problem.json").read_text())
        parameters = problem["parameters"]
        assert parameters["channel"] == channel
        assert parameters["height"] == parameters["width"] == 512
        assert parameters["seed"] == 99 and parameters["num_inference_steps"] == 10
        assert parameters["safety_checker"] is True
        assert problem["evaluation_protocol"]["paper_reproduction"] is False
        seeds.add((task / "initial_program.py").read_bytes())
    assert len(seeds) == 1 and b"A photograph of a landscape." in seeds.pop()
