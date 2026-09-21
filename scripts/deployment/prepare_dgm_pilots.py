#!/usr/bin/env python3
"""Prepare a pinned two-exercise native DGM pilot, without evaluation or models."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from arena.frameworks.drivers.dgm_gateway import DGM_COMMIT, MODELS, SOURCE_HASHES, provider_overlays

AIDER_COMMIT = "7e0611e77b54e2dea774cdc0aa00cf9f7ed6144f"
SWEBENCH_COMMIT = "dc4c087c2b9e4cefebf2e3d201d27e362d899e0f"
TASKS = ("python__dominoes", "python__beer-song")


def files(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Preparation trees must not contain symlinks")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def verify_git(path, commit):
    def git(*args):
        return subprocess.check_output(["git", "--no-replace-objects", "-c", "core.hooksPath=/dev/null", "-C", str(path), *args], text=True).strip()
    if git("rev-parse", "HEAD") != commit or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Preparation requires a clean exact pinned checkout")


def prepare(root: Path, destination: Path):
    source = root / "sources/dgm"
    aider = root / "dependencies/polyglot-benchmark"
    swebench = root / "dependencies/swe-bench-dgm"
    verify_git(source, DGM_COMMIT)
    verify_git(aider, AIDER_COMMIT)
    verify_git(swebench, SWEBENCH_COMMIT)
    overlays = provider_overlays(source)
    dependency_freeze = root / "configs/pilot-dependencies-dgm.txt"
    if not dependency_freeze.is_file():
        raise ValueError("Record the prepared DGM dependency freeze first")
    destination.mkdir(exist_ok=False)
    native = destination / "native-inputs"
    benchmark = native / "polyglot/polyglot-benchmark"
    original_files = {}
    for task in TASKS:
        name = task.split("__", 1)[1]
        relative = Path("python/exercises/practice") / name
        original = aider / relative
        original_files[task] = files(original)
        shutil.copytree(original, benchmark / relative, symlinks=False)
    overlay_dir = destination / "provider-overlays"
    overlay_dir.mkdir()
    for name, content in overlays.items():
        (overlay_dir / name).write_text(content)
    # Native data preparation only: no candidate execution, Docker or LLM use.
    # Fixed synthetic author/date avoid the operator's personal Git identity.
    os.environ.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_COUNT="3",
        GIT_CONFIG_KEY_0="user.name", GIT_CONFIG_VALUE_0="Arena Benchmark Preparation",
        GIT_CONFIG_KEY_1="user.email", GIT_CONFIG_VALUE_1="benchmark-preparation@localhost",
        GIT_CONFIG_KEY_2="core.hooksPath", GIT_CONFIG_VALUE_2=os.devnull,
        GIT_AUTHOR_DATE="2024-12-22T21:47:10+00:00", GIT_COMMITTER_DATE="2024-12-22T21:47:10+00:00",
        PYTHONDONTWRITEBYTECODE="1")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    from polyglot.prepare_polyglot_dataset import register_git, generate_dataset_metadata
    original_cwd = Path.cwd()
    try:
        os.chdir(native)
        commits = register_git(Path("polyglot/polyglot-benchmark"))
        metadata = generate_dataset_metadata("polyglot", commits)
    finally:
        os.chdir(original_cwd)
    metadata.sort(key=lambda item: TASKS.index(item["instance_id"]))
    if tuple(item["instance_id"] for item in metadata) != TASKS:
        raise ValueError("Native preparation did not return exactly the two selected tasks")
    for item in metadata:
        if not item["reference_tests"] or not item["reference_answers"] or not item["test_patch"]:
            raise ValueError("Native exercise metadata lost its tests, reference answer or test patch")
        repo = native / item["repo"]
        for key in ("base_commit", "test_commit"):
            subprocess.run(["git", "-C", str(repo), "cat-file", "-e", item[key] + "^{commit}"], check=True)
    write(native / "polyglot/polyglot_benchmark_metadata.json", metadata)
    from polyglot.test_spec import make_test_spec
    image_recipes = {}
    for item in metadata:
        spec = make_test_spec(item)
        image_recipes[item["instance_id"]] = {
            "base_image": spec.base_image_key, "env_image": spec.env_image_key,
            "instance_image": spec.instance_image_key, "platform": spec.platform,
            "base_dockerfile": spec.base_dockerfile, "env_dockerfile": spec.env_dockerfile,
            "instance_dockerfile": spec.instance_dockerfile,
            "setup_env_script": spec.setup_env_script, "install_repo_script": spec.install_repo_script,
            "eval_script": spec.eval_script,
        }
    write(destination / "native-image-recipes.json", image_recipes)
    write(destination / "selected-task-ids.json", list(TASKS))
    plans = []
    for model in MODELS:
        plans.append({
            "schema": "arena.dgm-pilot-preparation/1", "model": model,
            "status": "prepared_not_runnable", "framework": "dgm", "canonical_evaluation": False,
            "source_commit": DGM_COMMIT, "benchmark_commit": AIDER_COMMIT,
            "python": str(root / "envs/dgm/bin/python"), "task_ids": list(TASKS),
            "roles": {"diagnosis": model, "coding": model, "self_improvement": model},
            "provider_overlays": str(overlay_dir), "native_inputs": str(native),
            "native_outer_argv": ["DGM_outer.py", "--max_generation", "1", "--selfimprove_size", "1",
                "--selfimprove_workers", "1", "--num_swe_evals", "1", "--shallow_eval", "--no_full_eval", "--polyglot"],
            "requires_before_run": ["Scoped DGM image/container broker; raw Docker is prohibited",
                "Immutable native DGM and Python Polyglot images with this provider seam",
                "Explicit fresh native initial baseline on these two task IDs",
                "Hash-recorded workspace small.json subset and fresh initial archive injection"],
            "suggested_admission": {"cpus": 4, "memory_mb": 16384, "evaluation_slots": 2, "pids": 1024,
                                     "timeout_seconds": 3600},
            "fresh_baseline_plan": {"native_function": "polyglot.harness.harness", "kwargs": {
                "test_task_list": list(TASKS), "num_samples": -1, "max_workers": 1, "num_evals": 1,
                "num_evals_parallel": 1, "model_patch_paths": []},
                "performance_function": "utils.evo_utils.get_all_performance",
                "output_requirement": "Fresh initial metadata and native chat/eval logs for these two tasks; never copy the cached 225-task score"},
        })
    write(destination / "plans.json", plans)
    manifest = {"schema": "arena.dgm-native-preparation/1", "source_commit": DGM_COMMIT,
        "benchmark": {"repository": "https://github.com/Aider-AI/polyglot-benchmark", "commit": AIDER_COMMIT,
                      "task_ids": list(TASKS), "original_files": original_files},
        "native_task_commits": {item["instance_id"]: {key: item[key] for key in ("base_commit", "test_commit")} for item in metadata},
        "native_input_files": files(native), "provider_original_files": SOURCE_HASHES,
        "provider_overlay_files": files(overlay_dir),
        "integration_sha256": hashlib.sha256((REPO / "src/arena/frameworks/drivers/dgm_gateway.py").read_bytes()).hexdigest(),
        "dependency_freeze_sha256": hashlib.sha256(dependency_freeze.read_bytes()).hexdigest(),
        "swebench_import_dependency": {"repository": "https://github.com/SWE-bench/SWE-bench",
                                      "commit": SWEBENCH_COMMIT},
        "native_image_recipes_sha256": hashlib.sha256((destination / "native-image-recipes.json").read_bytes()).hexdigest(),
        "model_calls": 0, "task_evaluations": 0, "optimizer_runs": 0, "runtime_readiness": "not_verified"}
    write(destination / "preparation.json", manifest)
    verify_git(source, DGM_COMMIT)
    verify_git(aider, AIDER_COMMIT)
    verify_git(swebench, SWEBENCH_COMMIT)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, default=Path("/srv/arena/configs/dgm-pilot-20260921"))
    args = parser.parse_args()
    if not args.root.is_absolute() or not args.destination.is_absolute():
        parser.error("root and destination must be absolute")
    print(prepare(args.root, args.destination))


if __name__ == "__main__":
    main()
