"""Pinned Darwinian Evolver circle-packing CLI with an exact gateway model.

Only the native Anthropic client constructor and model constant are bound here.
The native prompts, parser, weighted population, mutation and evaluator remain
unchanged. Importing this module does not import an SDK or native framework.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

from .base_gateway import MODELS

ENDPOINT = "http://127.0.0.1:8789"
PIN = "7f12365d2059c47e29068a5a6f498a293148d2a9"
PROBLEM_FILE = "darwinian_evolver/problems/circle_packing.py"
PROBLEM_SHA256 = "a95d3137e531ee75e00d9456c167b9c98959991bbae272bf1c27e20ea602ec4d"


def verify_source(source):
    path = Path(source) / PROBLEM_FILE
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != PROBLEM_SHA256:
        raise ValueError("Pinned native circle-packing source hash mismatch")


def bind_provider(problem, model):
    if model not in MODELS:
        raise ValueError("Use an exact reviewed gateway model")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must contain the scoped local gateway credential")
    from anthropic import Anthropic

    def client():
        return Anthropic(api_key=os.environ["OPENAI_API_KEY"], base_url=ENDPOINT,
                         timeout=180, max_retries=0)

    problem.Anthropic = client
    problem.ANTHROPIC_MODEL = model


def native_arguments(iterations, output):
    if type(iterations) is not int or not 1 <= iterations <= 8:
        raise ValueError("Iterations must be between one and eight")
    return ["circle_packing", "--num_iterations", str(iterations),
            "--num_parents_per_iteration", "1", "--mutator_concurrency", "1",
            "--evaluator_concurrency", "1", "--batch_size", "1",
            "--learning_log", "ancestors", "--output_dir", str(output)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--iterations", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    verify_source(Path.cwd())
    from darwinian_evolver.problems import circle_packing
    bind_provider(circle_packing, args.model)
    args.output.mkdir(parents=True, exist_ok=True)
    native = native_arguments(args.iterations, args.output)
    proof = {"schema": "arena.native-provider-seam/1", "framework": "darwinian-evolver",
             "recipe": "darwinian-evolver-gateway", "source_commit": PIN,
             "model": args.model, "endpoint": ENDPOINT + "/v1/messages",
             "native_entrypoint": "darwinian_evolver", "native_argv": native,
             "native_search_modified": False, "native_evaluator_modified": False,
             "canonical_evaluation": False, "evaluation_concurrency": 1,
             "sdk_timeout_seconds": 180, "sdk_retries": 0,
             "provider_controls_unenforced": ["max_tokens"],
             "scope": "Small-budget native CPU integration pilot, not the paper protocol.",
             "budget_note": "One parent per iteration; failed mutations may yield no candidate. Initial evaluation is separate. Outer cgroup deadline is authoritative.",
             "snapshot_policy": "Native pickle snapshots are opaque artifacts; Arena never deserializes them."}
    (args.output / "provider-seam.json").write_text(json.dumps(proof, indent=2) + "\n")
    sys.argv = ["darwinian_evolver", *native]
    runpy.run_module("darwinian_evolver", run_name="__main__")


if __name__ == "__main__":
    main()
