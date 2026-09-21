#!/usr/bin/env python3
"""Prepare six more models from an already approved SCiEL private-image pilot.

No image build, approval, broker request, model call or queue mutation occurs.
The original successful model's configuration and task package stay untouched.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra",
          "gpt-5.5", "gpt-reserve", "codex-auto-review")
BASE_ID = "private-image-sciel-worker1-gpt-5-6-sol"
TASK_FILES = {"README.md", "evaluation.json", "evaluator.py", "initial_program.py", "task.yaml"}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def model_configuration(baseline, model):
    if model not in MODELS[1:]:
        raise ValueError("Choose one of the six remaining exact model IDs")
    if (baseline.get("budget") != 4 or baseline.get("max_iterations") != 6
            or baseline.get("research", {}).get("max_aux_calls") != 1
            or baseline.get("llm", {}).get("models") != [MODELS[0]]
            or baseline["llm"].get("model_capabilities") != {MODELS[0]: {"temperature": False}}):
        raise ValueError("Baseline must match the reviewed successful private-image pilot")
    result = copy.deepcopy(baseline)
    result["llm"]["models"] = [model]
    result["llm"]["model_capabilities"] = {model: {"temperature": False}}
    return result


def task_snapshot(root):
    root = Path(root)
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError("Task root must not traverse symlinks")
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Task package must contain regular files without symlinks")
        if path.is_file():
            if path.stat().st_size > 1024 * 1024:
                raise ValueError("Unexpected oversized pilot task input")
            files[str(path.relative_to(root))] = path.read_bytes()
    expected = {"arena/reference-sat/" + name for name in TASK_FILES}
    if set(files) != expected:
        raise ValueError("Expected exactly the five reviewed SAT task package files")
    evaluation = json.loads(files["arena/reference-sat/evaluation.json"])
    if (evaluation.get("task_id") != "reference-sat"
            or evaluation.get("profile") != "sciel-unit-interval/1"
            or evaluation.get("execution", {}).get("require_control_cgroup") is not True):
        raise ValueError("Task package must retain the controlled canonical SAT bridge")
    return files


def write(path, data):
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    path.chmod(0o640)


def prepare(control_path, destination, tasks_destination, approved_root):
    from arena.control import validate_config
    from arena.engine_broker import checked_native_config
    from arena.frameworks.runtime import prepare_plan
    from arena.release_deployment import load_manifest, materialize_template

    for path in (control_path, destination, tasks_destination, approved_root):
        if not path.is_absolute() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("All operator paths must be absolute without symlinks")
    if destination.exists() or tasks_destination.exists():
        raise ValueError("Matrix configuration and task destinations must be new")
    control_raw = control_path.read_bytes()
    control = validate_config(json.loads(control_raw))
    baseline = next(t for t in control["templates"] if t["id"] == BASE_ID)
    request = baseline["spec"]["request"]
    if (baseline["framework"] != "sciel-release" or baseline["model"] != MODELS[0]
            or request.get("budget") != 4 or request.get("seed") != 0
            or baseline["resources"] != {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512}
            or baseline["spec"]["environment_names"] != []):
        raise ValueError("Baseline private image template does not match the reviewed pilot")
    config_path = Path(request["config"])
    baseline_raw = config_path.read_bytes()
    baseline_config = json.loads(baseline_raw)
    model_configuration(baseline_config, MODELS[1])
    files = task_snapshot(Path(request["tasks_root"]))
    manifest, digest = load_manifest(Path(request["deployment"]), expected_release=request["release"])
    approval = approved_root / (digest + ".json")
    destination.mkdir(mode=0o750, parents=True)
    tasks_destination.mkdir(mode=0o750, parents=True)
    templates, records = [], []
    for model in MODELS[1:]:
        slug = model.replace(".", "-")
        model_dir = destination / slug
        task_root = tasks_destination / slug / "sciel"
        config = model_configuration(baseline_config, model)
        config_target = model_dir / "sciel.json"
        write(config_target, encoded(config))
        task_hashes = {}
        for relative, data in files.items():
            if relative.endswith("/evaluation.json"):
                evaluation = json.loads(data)
                # require_control_cgroup makes the admitted broker context
                # authoritative. This unused fallback remains model-specific.
                evaluation["receipts_dir"] = str(Path("/srv/arena/runs") / destination.name / slug / "canonical-sciel")
                data = encoded(evaluation)
            write(task_root / relative, data)
            task_hashes[relative] = sha(data)
        template = materialize_template(Path(request["deployment"]), approval,
            template_id="private-image-sciel-worker1-" + slug,
            name="SCiEL private image worker1 · " + model, model=model,
            python=request["python"], config=config_target, tasks_root=task_root,
            resources=baseline["resources"], timeout_seconds=baseline["spec"]["timeout_seconds"],
            seed=request["seed"], budget=request["budget"], environment_names=())
        if any(t["id"] == template["id"] for t in control["templates"]):
            raise ValueError("A requested matrix template already exists in live control")
        artifacts = Path("/srv/arena/control/runs") / ("0" * 32) / "artifacts"
        transformed = checked_native_config(config_target.read_bytes(), model, artifacts,
                                            "http://127.0.0.1:8789/v1")
        assert transformed["llm"]["models"] == [model]
        plan = prepare_plan({**template["spec"], "output_dir": str(Path("/srv/arena/runs") / (template["id"] + "-plan-only"))})
        write(model_dir / "plan.json", encoded(plan))
        write(model_dir / "template.json", encoded(template))
        templates.append(template)
        records.append({"model": model, "template_id": template["id"], "config_sha256": sha(config_target.read_bytes()),
                        "task_hashes": task_hashes, "plan_sha256": plan["sha256"],
                        "broker_config_validation": "passed", "research_executed": False})
    validate_config({**control, "templates": templates})
    if config_path.read_bytes() != baseline_raw or task_snapshot(Path(request["tasks_root"])) != files:
        raise ValueError("Baseline inputs changed during preparation")
    write(destination / "templates.json", encoded(templates))
    write(destination / "preparation.json", encoded({
        "schema": "arena.sciel-image-matrix-preparation/1", "models": list(MODELS),
        "new_templates": len(templates), "existing_template": BASE_ID,
        "existing_successful_run_reference": "5a72d1e3d80749fbbffb10f6174572b6",
        "release": manifest["release"], "image": manifest["image"],
        "deployment_sha256": digest, "source": manifest["source"],
        "baseline_config_sha256": sha(baseline_raw),
        "baseline_task_hashes": {k: sha(v) for k, v in files.items()},
        "observed_control_sha256": sha(control_raw), "records": records,
        "model_calls": 0, "canonical_evaluator_calls": 0, "research_executed": False,
        "scope": "Same approved private image and native pilot settings across seven exact model IDs; configuration preparation, not a scientific comparison.",
        "provider_accounting": "Same gateway and native provider slots; outer global admission and gateway limits remain operator-controlled. max_tokens/temperature are not enforced compute limits.",
        "task_changes": "Only each task package's fallback receipts_dir is model-specific; controlled runtime receipt paths come from the broker context.",
    }))
    return {"new_templates": len(templates), "destination": str(destination), "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--control", type=Path, default=Path("/srv/arena/configs/control.json"))
    parser.add_argument("--destination", type=Path, default=Path("/srv/arena/configs/image-matrix-20260921"))
    parser.add_argument("--tasks-destination", type=Path, default=Path("/srv/arena/tasks/image-matrix-20260921"))
    parser.add_argument("--approved-root", type=Path, default=Path("/srv/arena/releases/approved"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.control, args.destination, args.tasks_destination, args.approved_root)))


if __name__ == "__main__":
    main()
