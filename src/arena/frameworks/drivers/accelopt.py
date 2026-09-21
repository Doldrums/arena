"""Prepare one NKIBench service and delegate AccelOpt's complete native loop.

The upstream experiment generator substitutes positional template variables.
This bridge instead braces positions 10..15 in a hash-checked copy, preserving
every planner, executor, experience-selection and hardware-profile command.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit

from ._specialized import bounded_positive, output_directory

TEMPLATE = "templates/complete_local/run_single_loop.sh"
TEMPLATE_SHA256 = "ff68bc0a9653444f355e02ef6db54c9e9722853f45a0fd2921135c9f63e8ee61"
CONFIG_NAMES = ("planner_config.json", "executor_config.json", "summarizer_config.json")


def corrected_template(raw):
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ValueError("AccelOpt loop template differs from its pinned source")
    text = raw.decode("utf-8")
    for name, position in (("TOPK_CANDIDATES", 10), ("NUM_SAMPLES", 11), ("MAX_THRESHOLD", 12),
                           ("MIN_THRESHOLD", 13), ("TOPK", 14), ("EXP_N", 15)):
        old = f"{name}=${position}\n"
        if text.count(old) != 1:
            raise ValueError("Unexpected native positional template")
        text = text.replace(old, f"{name}=${{{position}}}\n")
    return text.encode("utf-8")


def native_token(value):
    # Native stage scripts expand variables unquoted. Restrict their positional
    # values to prevent word splitting/globbing; no shell command text is built.
    if not re.fullmatch(r"[A-Za-z0-9_./:+-]+", value):
        raise argparse.ArgumentTypeError("Native paths/labels must contain no whitespace or shell metacharacters")
    return value


def finite_positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("Expected a finite positive value")
    return value


def contained_file(root, value):
    path = root / value
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError("Prepared AccelOpt input must be a regular file inside the workspace")
    native_token(str(path.resolve()))
    return path.resolve()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-dir", required=True, type=native_token)
    parser.add_argument("--project", required=True, type=native_token)
    parser.add_argument("--organization", required=True, type=native_token)
    parser.add_argument("--iterations", required=True, type=bounded_positive,
                        help="Feedback iterations after the initial planning/execution pass")
    parser.add_argument("--neuron-core", type=int, default=0)
    parser.add_argument("--breadth", type=bounded_positive, default=12)
    parser.add_argument("--top-candidates", type=bounded_positive, default=6)
    parser.add_argument("--samples", type=bounded_positive, default=2)
    parser.add_argument("--max-threshold", type=finite_positive, default=1.04)
    parser.add_argument("--min-threshold", type=finite_positive, default=1.15)
    parser.add_argument("--topk", type=bounded_positive, default=8)
    parser.add_argument("--experience-count", type=bounded_positive, default=16)
    parser.add_argument("--relative-tolerance", type=finite_positive, default=2e-5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not 0 <= args.neuron_core <= 1024:
        raise ValueError("Neuron core must be between 0 and 1024")
    root = Path.cwd().resolve()
    native_token(str(root))
    prepared = (root / args.prepared_dir).resolve()
    if not prepared.is_relative_to(root) or not prepared.is_dir():
        raise ValueError("Prepared directory must be staged inside the isolated workspace")
    template = contained_file(root, TEMPLATE)
    original = template.read_bytes()
    patched = corrected_template(original)
    baseline = contained_file(root, str(prepared.relative_to(root) / "profile_results.csv"))
    with baseline.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames, rows = reader.fieldnames, list(reader)
    required = {"service_name", "task", "kernel", "profile", "problem", "values", "case_name"}
    if not fieldnames or not required <= set(fieldnames) or len(rows) != 1:
        raise ValueError("Provide a genuine native baseline CSV for exactly one NKIBench service")
    row = rows[0]
    native_token(row["service_name"])
    for key in ("task", "kernel"):
        row[key] = str(contained_file(root, row[key]))
    if type(json.loads(row["profile"])) is not dict:
        raise ValueError("Native baseline profile must contain a JSON object")
    configs = {}
    for name in CONFIG_NAMES:
        path = contained_file(root, str(prepared.relative_to(root) / "configs" / name))
        value = json.loads(path.read_text())
        url = urlsplit(value.get("url", ""))
        if (url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password
                or not isinstance(value.get("model"), str) or not value["model"]):
            raise ValueError("Each native model config needs a credential-free endpoint and model")
        if value.get("api_key") not in {"None", "EMPTY", "not-needed"}:
            raise ValueError("Use a prepared local/worker-authenticated endpoint and a nonsecret placeholder key")
        configs[name] = path
    for binary in ("bash", "logfire", "python"):
        if shutil.which(binary) is None:
            raise ValueError(f"Prepared native execution environment is missing {binary}")
    output = output_directory(args.output)
    native_token(str(output))
    config_dir = output / "configs"
    config_dir.mkdir(exist_ok=False)
    for name, path in configs.items():
        shutil.copyfile(path, config_dir / name)
    initial = "arena-initial"
    candidates = output / initial / "candidates"
    candidates.mkdir(parents=True, exist_ok=False)
    with (candidates / "profile_results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader(); writer.writerow(row)
    script = output / "arena-native-loop.sh"
    script.write_bytes(patched)
    manifest = {"schema": "arena.native-patch/1", "framework": "accelopt", "source_path": TEMPLATE,
                "source_sha256": TEMPLATE_SHA256, "execution_copy_sha256": hashlib.sha256(patched).hexdigest(),
                "changes": [f"Brace positional parameter {i}" for i in range(10, 16)],
                "native_initial_passes": 1, "native_feedback_iterations": args.iterations,
                "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                "model_configs": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in configs.items()}}
    (output / "arena-patch.json").write_text(json.dumps(manifest, indent=2) + "\n")
    native_args = [str(output), initial, "arena", args.neuron_core, args.project, args.relative_tolerance,
                   args.organization, args.iterations, args.breadth, args.top_candidates, args.samples,
                   args.max_threshold, args.min_threshold, args.topk, args.experience_count]
    completed = subprocess.run(["bash", str(script), *map(str, native_args)],
                               env=os.environ | {"ACCELOPT_BASE_DIR": str(root)}, check=False)
    if completed.returncode:
        return completed.returncode
    # Native shell stages do not consistently fail fast. Missing expected stage
    # outputs must not turn a shell exit 0 into a successful complete-loop run.
    journal = output / "log.txt"
    iterations = journal.read_text().splitlines() if journal.is_file() else []
    if len(iterations) != args.iterations + 1 or len(set(iterations)) != len(iterations) or any(
            not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not (output / name / "executor_results.json").is_file()
            for name in iterations):
        raise ValueError("Native loop did not record every expected execution stage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
