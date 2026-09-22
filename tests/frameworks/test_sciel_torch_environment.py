"""The real pinned CPU thread environment is exact, never general env admission."""
import json
from pathlib import Path

import pytest

from arena import task_library
from arena.frameworks import sciel_catalog_torch as torch
from test_sciel_catalog_campaign import prepared_inputs
from test_sciel_catalog_evaluate import setup, bridge, evaluation
from test_sciel_torch_campaign import torch_inputs, campaign, digest, rewrite_receipt


def test_all_reviewed_torch_tasks_declare_the_same_exact_thread_environment():
    root = Path(__file__).resolve().parents[2] / "tasks/suite"
    expected = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
    assert len(torch.TORCH_TASK_REQUIREMENTS) == 51
    for name in torch.TORCH_TASK_REQUIREMENTS:
        suite = json.loads((root / name / "task.json").read_bytes())["execution"]["suite"]
        assert suite["env"] == expected
        assert suite["timing_protocol"]["id"] == torch.TORCH_THREAD_POLICY
        assert suite["timing_protocol"]["intra_op_threads"] == 1
        assert suite["timing_protocol"]["inter_op_threads"] == 1


@pytest.mark.parametrize("mutation", ["absent", "empty", "missing", "extra", "value", "integer", "boolean", "null", "list"])
def test_rehashed_task_metadata_cannot_change_or_omit_exact_thread_limits(torch_inputs, mutation):
    args, manifest_path, receipt_path, catalog = torch_inputs
    name = catalog["tasks"][0]["id"]
    task_path = args["tasks_root"] / "suite" / name / "task.json"
    task = json.loads(task_path.read_bytes())
    suite = task["execution"]["suite"]
    if mutation == "absent": del suite["env"]
    elif mutation == "empty": suite["env"] = {}
    elif mutation == "missing": del suite["env"]["NUMEXPR_NUM_THREADS"]
    elif mutation == "extra": suite["env"]["PYTHONPATH"] = "/unreviewed"
    elif mutation == "value": suite["env"]["OMP_NUM_THREADS"] = "2"
    elif mutation == "integer": suite["env"]["OMP_NUM_THREADS"] = 1
    elif mutation == "boolean": suite["env"]["OMP_NUM_THREADS"] = True
    elif mutation == "null": suite["env"] = None
    else: suite["env"] = []
    task_path.write_text(json.dumps(task))
    source = catalog["sources"][0]
    library_path = args["tasks_root"].parent / "registry/task-library-manifest.json"
    library = json.loads(library_path.read_bytes())
    library["files"][task_path.relative_to(args["tasks_root"]).as_posix()] = digest(task_path)
    library_path.write_text(json.dumps(library))
    source["manifest_sha256"] = digest(library_path)
    identity = task_library.verify_task_library(args["tasks_root"], source)
    receipt = json.loads(receipt_path.read_bytes())
    receipt["task_source"] = identity
    rewrite_receipt(manifest_path, receipt_path, receipt)
    manifest = json.loads(manifest_path.read_bytes())
    manifest["task_source"] = identity
    manifest_path.write_text(json.dumps(manifest))
    evidence = manifest_path.read_bytes(), receipt_path.read_bytes()
    result = campaign.prepare(**args)
    assert result["counts"] == {"pending": 2}
    assert json.loads((args["config_destination"] / "templates.json").read_bytes()) == []
    inventory = json.loads((args["config_destination"] / "campaign-inventory.json").read_bytes())
    rejected = next(row for row in inventory["tasks"] if row["task_id"] == name)
    assert rejected["reason"] == "Native task integration: Task execution requires undeclared dependencies or environment"
    assert not list(args["native_tasks"].rglob("task.yaml"))
    assert evidence == (manifest_path.read_bytes(), receipt_path.read_bytes())


def test_general_cpu_profile_still_rejects_the_torch_thread_environment(setup):
    config, _, _, _, _, root, _ = setup
    task_path = root / "suite/fixture/task.json"
    metadata = json.loads(task_path.read_bytes())
    real_task = (Path(__file__).resolve().parents[2] / "tasks/suite" /
                 next(iter(torch.TORCH_TASK_REQUIREMENTS)) / "task.json")
    metadata["execution"]["suite"]["env"] = json.loads(real_task.read_bytes())["execution"]["suite"]["env"]
    task_path.write_text(json.dumps(metadata))
    library_path = root.parent / "registry/task-library-manifest.json"
    library = json.loads(library_path.read_bytes())
    library["files"]["suite/fixture/task.json"] = digest(task_path)
    library_path.write_text(json.dumps(library))
    evaluation.get_catalog()["sources"][0]["manifest_sha256"] = digest(library_path)
    with pytest.raises(ValueError, match="undeclared dependencies or environment"):
        bridge.validate_config(config)
