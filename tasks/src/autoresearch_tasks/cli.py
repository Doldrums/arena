"""Local task discovery, inspection, validation and candidate evaluation."""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from arena_task_paths import runtime_path

from .registry import get_task, merged_view, repository_root, suite_runnable, tasks, validate
from .runner import evaluate_suite, evaluate_upstream, setup_upstream
from .source_assets import status as source_asset_status


def emit(value, output=None):
    text = json.dumps(value, indent=2, allow_nan=False) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    print(text, end="")


def missing_requirements(root, task):
    """Read-only checks; never install dependencies or invoke a task model."""
    suite = task.get("execution", {}).get("suite") or {}
    missing = []
    for requirement in suite.get("requires", []):
        kind, _, value = requirement.partition(":")
        if kind == "py":
            try:
                available = importlib.util.find_spec(value) is not None
            except (ImportError, ModuleNotFoundError, ValueError):
                available = False
            if not available:
                missing.append(requirement)
        elif kind == "env" and not os.environ.get(value):
            missing.append(requirement)
        elif kind == "bin" and not shutil.which(value):
            missing.append(requirement)
        elif kind == "file":
            path = runtime_path(value) if value.startswith(("data/", "vendor/adrs/", "../../.cache/")) else root / "suite" / "_lib" / value
            if not path.is_file():
                missing.append(requirement)
    missing.extend(f"source-asset:{row['path']} ({row['status']})"
                   for row in source_asset_status(root, task["id"]) if row["status"] != "ready")
    return missing


def select_tasks(root, args):
    selected = tasks(root)
    if args.paper:
        selected = [task for task in selected if args.paper in task["paper_ids"]]
    if args.search:
        term = args.search.casefold()
        selected = [task for task in selected if term in json.dumps(task).casefold()]
    for label in args.label:
        if "=" not in label:
            raise ValueError("--label expects AXIS=VALUE")
        axis, expected = label.split("=", 1)
        selected = [task for task in selected
                    if str((task.get("labels") or {}).get(axis)).casefold() == expected.casefold()]
    return selected


def parser():
    result = argparse.ArgumentParser(description="Arena task library")
    result.add_argument("--root", type=Path, help="Bundled tasks root")
    commands = result.add_subparsers(dest="action", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--search")
    listing.add_argument("--paper")
    listing.add_argument("--label", action="append", default=[])
    listing.add_argument("--json", action="store_true")
    for action in ("show", "doctor", "setup", "evaluate"):
        command = commands.add_parser(action)
        command.add_argument("task")
        command.add_argument("--paper", help="Select a merged paper's original protocol")
        if action in ("setup", "evaluate"):
            command.add_argument("--route", choices=("suite", "upstream"), default="suite")
        if action == "evaluate":
            command.add_argument("--candidate", type=Path)
            command.add_argument("--python", type=Path)
            command.add_argument("--timeout", type=float, default=300)
            command.add_argument("--output", type=Path)
    commands.add_parser("validate").add_argument("--output", type=Path)
    commands.add_parser("coverage")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        root = args.root.resolve() if args.root else repository_root()
        if args.action == "list":
            selected = select_tasks(root, args)
            if args.json:
                emit(selected)
            else:
                for task in selected:
                    print(f"{task['id']}\t{task['name']}")
            return 0
        if args.action == "validate":
            result = validate(root)
            emit(result, args.output)
            return 0 if result["valid"] else 1
        if args.action == "coverage":
            selected = tasks(root)
            protocols = collections.Counter(
                (task.get("execution", {}).get("suite") or {}).get("protocol", "none")
                for task in selected
            )
            emit({"task_packages": len(selected), "evaluator_protocols": dict(protocols),
                  "evaluation_definitions": sum(suite_runnable(task) for task in selected)})
            return 0
        task = merged_view(get_task(root, args.task), args.paper)
        if args.action == "show":
            emit(task)
            return 0
        if args.action == "doctor":
            missing = missing_requirements(root, task)
            emit({"task_id": task["id"], "evaluation_definition": suite_runnable(task),
                  "missing_requirements": missing, "requirements": task["requirements"],
                  "setup": task.get("execution", {}).get("setup"),
                  "note": "Read-only dependency checks; scientific data, simulators and runtime assets require task-specific setup."})
            return 0 if suite_runnable(task) and not missing else 2
        if args.action == "setup":
            if args.route == "upstream":
                emit(setup_upstream(root, task))
            else:
                emit({"task_id": task["id"], "missing_requirements": missing_requirements(root, task),
                      "requirements": (task.get("execution", {}).get("suite") or {}).get("requires", []),
                      "setup": task.get("execution", {}).get("setup"),
                      "note": "No packages installed or datasets downloaded. Follow the declared task setup requirements."})
            return 0
        evaluator = evaluate_suite if args.route == "suite" else evaluate_upstream
        result = evaluator(root, task, args.candidate, args.python, args.timeout)
        emit(result, args.output)
        return 0 if result["status"] in ("success", "completed") else 1
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
