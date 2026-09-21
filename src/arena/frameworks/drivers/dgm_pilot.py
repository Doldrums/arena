"""Explicit two-task DGM pilot: fresh native baseline, then the native search.

Planning helpers never import upstream code. Native imports occur only in run().
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from .dgm_gateway import DGM_COMMIT, GATEWAY, MODELS, SOURCE_HASHES, provider_overlays

PROFILE = "gateway-polyglot-pilot"
TASKS = ("python__dominoes", "python__beer-song")
AIDER_COMMIT = "7e0611e77b54e2dea774cdc0aa00cf9f7ed6144f"
SWE_COMMIT = "dc4c087c2b9e4cefebf2e3d201d27e362d899e0f"
DOCKER_HOST = "unix:///run/arena-dgm/docker.sock"
NATIVE_ARGUMENTS = ["DGM_outer.py", "--max_generation", "1", "--selfimprove_size", "1",
                    "--selfimprove_workers", "1", "--num_swe_evals", "1", "--shallow_eval",
                    "--no_full_eval", "--polyglot"]


def sha(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024**2:
        raise ValueError("DGM pilot input must be a bounded regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("DGM pilot tree must be a regular directory")
    result, total = {}, 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("DGM pilot trees cannot contain symlinks")
        if path.is_dir():
            continue
        total += path.stat().st_size
        if total > 64 * 1024**2 or len(result) >= 4096:
            raise ValueError("DGM pilot tree exceeds provenance limits")
        result[path.relative_to(root).as_posix()] = sha(path)
    return result


def read_json(path):
    sha(path)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate DGM pilot JSON key")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON")))


def validate_preparation(source, prepared, freeze):
    manifest = read_json(prepared / "preparation.json")
    if (manifest.get("schema") != "arena.dgm-native-preparation/1"
            or manifest.get("source_commit") != DGM_COMMIT
            or manifest.get("benchmark", {}).get("commit") != AIDER_COMMIT
            or manifest.get("benchmark", {}).get("task_ids") != list(TASKS)
            or manifest.get("swebench_import_dependency", {}).get("commit") != SWE_COMMIT
            or manifest.get("provider_original_files") != SOURCE_HASHES):
        raise ValueError("DGM pilot preparation does not bind the reviewed sources and two tasks")
    if tree(prepared / "native-inputs") != manifest.get("native_input_files"):
        raise ValueError("Prepared native task inputs changed")
    expected = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in provider_overlays(source).items()}
    if tree(prepared / "provider-overlays") != expected or manifest.get("provider_overlay_files") != expected:
        raise ValueError("Prepared provider overlays differ from the reviewed native seam")
    if (sha(prepared / "native-image-recipes.json") != manifest.get("native_image_recipes_sha256")
            or sha(freeze) != manifest.get("dependency_freeze_sha256")
            or sha(Path(__file__).with_name("dgm_gateway.py")) != manifest.get("integration_sha256")):
        raise ValueError("DGM pilot recipes, dependencies or provider helper changed")
    metadata = read_json(prepared / "native-inputs/polyglot/polyglot_benchmark_metadata.json")
    if type(metadata) is not list or any(type(item) is not dict for item in metadata) or [item.get("instance_id") for item in metadata] != list(TASKS):
        raise ValueError("DGM pilot metadata must contain exactly the two reviewed tasks")
    return manifest


def _baseline_task_states(report):
    """Validate decoded native report counts without opening any artifacts."""
    expected = set(TASKS)
    if (type(report) is not dict or report.get("submitted_instances") != 2
            or report.get("completed_instances") != 2 or report.get("total_instances") != 2
            or set(report.get("submitted_ids", [])) != expected
            or set(report.get("completed_ids", [])) != expected
            or report.get("incomplete_ids") != [] or report.get("error_ids") != []
            or report.get("error_instances") != 0 or report.get("unstopped_containers") != []):
        raise ValueError("Fresh DGM baseline is incomplete or contains native errors")
    states = {}
    for key, state in (("resolved_ids", "resolved"), ("unresolved_ids", "unresolved"), ("empty_patch_ids", "empty_patch")):
        values = report.get(key)
        if type(values) is not list or len(values) != len(set(values)) or set(values) - expected or set(values) & states.keys():
            raise ValueError("Fresh DGM baseline task classifications are inconsistent")
        states.update({task: state for task in values})
        count_key = {"resolved": "resolved_instances", "unresolved": "unresolved_instances", "empty_patch": "empty_patch_instances"}[state]
        if report.get(count_key) != len(values):
            raise ValueError("Fresh DGM baseline counts do not match task identities")
    if set(states) != expected:
        raise ValueError("Fresh DGM baseline does not classify both tasks")
    return states


def baseline_records_complete(report, predictions, model_name):
    """Pure validation shared by the live harness and bounded result reader."""
    states = _baseline_task_states(report)
    if type(predictions) is not dict or set(predictions) != set(TASKS):
        raise ValueError("Fresh DGM baseline lacks both prediction records")
    for task in TASKS:
        record = predictions[task]
        if (type(record) is not dict or record.get("instance_id") != task or record.get("success") is not True
                or record.get("eval_result") != states[task] or record.get("model_name_or_path") != model_name):
            raise ValueError("Fresh DGM baseline prediction and report disagree")
    return states


def baseline_complete(report, predictions):
    """Live-harness check; untrusted result readers use decoded records instead."""
    _baseline_task_states(report)
    records = {task: read_json(predictions / (task + ".json")) for task in TASKS}
    states = baseline_records_complete(report, records, predictions.name)
    for task in TASKS:
        sha(predictions / (task + ".md"))
        if states[task] != "empty_patch":
            sha(predictions / (task + "_eval.md"))
    return states


def write_json(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
    path.chmod(0o600)


def run(workspace, model):
    if model not in MODELS or os.environ.get("ARENA_DGM_MODEL") != model:
        raise ValueError("DGM pilot requires the exact selected model for every role")
    if (os.environ.get("DOCKER_HOST") != DOCKER_HOST
            or os.environ.get("ARENA_DGM_GATEWAY_URL") != GATEWAY
            or not re.fullmatch(r"[a-f0-9]{32}", os.environ.get("ARENA_CONTROL_RUN_ID", ""))):
        raise ValueError("DGM pilot requires an admitted control run and the scoped Docker/gateway endpoints")
    if Path.cwd().resolve() != workspace.resolve():
        raise ValueError("DGM pilot must execute inside its isolated workspace")
    prepared = workspace / ".arena-pilot"
    manifest = validate_preparation(workspace, prepared, prepared / "dependencies.txt")
    # The source image and host clone use the same hash-recorded provider seam.
    for name in SOURCE_HASHES:
        shutil.copyfile(prepared / "provider-overlays" / name, workspace / name)
    native = prepared / "native-inputs/polyglot"
    for name in ("polyglot_benchmark_metadata.json", "polyglot-benchmark"):
        target = workspace / "polyglot" / name
        if target.exists() or target.is_symlink():
            raise ValueError("DGM pilot benchmark destination already exists")
        if (native / name).is_dir():
            shutil.copytree(native / name, target)
        else:
            shutil.copyfile(native / name, target)
    (workspace / "polyglot/subsets/small.json").write_text(json.dumps(list(TASKS)) + "\n")
    initial = workspace / "initial_polyglot"
    tree(initial)  # Refuse symlinks before removing only this clone's cached score.
    shutil.rmtree(initial)
    initial.mkdir()
    predictions = initial / "predictions"
    predictions.mkdir()
    sys.path.insert(0, str(workspace))
    from polyglot.harness import harness
    from utils.evo_utils import get_all_performance
    # Native function writes its actual per-task conversations, patches/tests,
    # and report. No cached archive or fixture supplies an initial score.
    harness(test_task_list=list(TASKS), num_samples=-1, max_workers=1,
            model_name_or_path=model, model_patch_paths=[], num_evals=1,
            num_evals_parallel=1, pred_dname=predictions, output_dir=initial)
    report = initial / (model + "_0.0.json")
    baseline_complete(read_json(report), predictions / (model + "_0"))
    _, performance = get_all_performance(model, results_dir=initial)
    if not performance or performance.get("total_submitted_instances") != 2:
        raise ValueError("Native DGM performance did not retain the two-task denominator")
    write_json(initial / "metadata.json", {"run_id": "initial", "overall_performance": performance})
    proof = {"schema": "arena.dgm-fresh-baseline/1", "profile": PROFILE, "model": model,
             "task_ids": list(TASKS), "source_commit": DGM_COMMIT,
             "preparation_sha256": sha(prepared / "preparation.json"),
             "provider_overlay_files": manifest["provider_overlay_files"],
             "files": tree(initial), "canonical_evaluation": False,
             "report": report.name, "native_performance": performance,
             "native_baseline_completed": True}
    write_json(prepared / "baseline-proof.json", proof)
    subprocess.run([sys.executable, *NATIVE_ARGUMENTS], cwd=workspace, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    args = parser.parse_args()
    run(Path.cwd(), args.model)


if __name__ == "__main__":
    main()
