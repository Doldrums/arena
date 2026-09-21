"""Explicit local integration CLI; the board remains strictly read-only."""
import argparse
import json
from pathlib import Path
import subprocess

from . import FRAMEWORKS, describe, get_adapter
from .runtime import prepare_plan, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List implemented native drivers and their verification limits")
    for action in ("plan", "run"):
        command = commands.add_parser(action, help="Inspect a launch without execution" if action == "plan" else "Execute an explicit native run spec")
        command.add_argument("spec", type=Path)
    results = commands.add_parser("results", help="Read saved native results without executing code")
    results.add_argument("framework", help="Native framework or engine ID from list")
    results.add_argument("--output", type=Path, required=True)
    evaluation = commands.add_parser("evaluate", help="Explicitly evaluate a candidate against a pinned Arena task")
    evaluation.add_argument("config", type=Path)
    evaluation.add_argument("--candidate", type=Path, required=True)
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--plan", action="store_true", help="Validate and inspect without execution")
    task = commands.add_parser("create-task", help="Write a native task using the Arena evaluator bridge")
    task.add_argument("framework", choices=("sciel", "shinka"))
    task.add_argument("config", type=Path)
    task.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            value = describe()
        elif args.command == "results":
            value = get_adapter(args.framework).read_results(args.output.expanduser().resolve())
        elif args.command == "evaluate":
            from .evaluation import evaluate, prepare_evaluation
            config = json.loads(args.config.read_text(encoding="utf-8"))
            function = prepare_evaluation if args.plan else evaluate
            value = function(config, args.candidate.absolute(), args.output.absolute())
        elif args.command == "create-task":
            from importlib import import_module
            bridge = import_module(f"arena.frameworks.{args.framework}_evaluate")
            value = bridge.create_task(json.loads(args.config.read_text()), args.output.absolute())
        else:
            spec = json.loads(args.spec.read_text(encoding="utf-8"))
            value = prepare_plan(spec) if args.command == "plan" else run(spec)
        print(json.dumps(value, indent=2, allow_nan=False))
        if args.command == "run":
            return int(value["status"] != "process_completed")
        if args.command == "evaluate" and not args.plan:
            return int(value["status"] != "completed" or value["validity"] is not True)
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(2, f"Native integration: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
