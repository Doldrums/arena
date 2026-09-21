#!/usr/bin/env python3
"""Replay native EoH-S population/thread behavior without models or evaluators."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.eohs_gateway_v2 import COMMIT, GuardRecord, execute_native, verify_source


def check(source, output):
    verify_source(source)
    git = ["git", "-c", "safe.directory=" + str(source), "-C", str(source)]
    if subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip() != COMMIT:
        raise ValueError("Wrong EoH-S pin")
    if subprocess.check_output(git + ["status", "--porcelain", "--untracked-files=all"], text=True).strip():
        raise ValueError("Native source must be clean")
    output.mkdir(parents=True, exist_ok=False)
    def denied(*args, **kwargs):
        raise AssertionError("Network is forbidden in this fixture")
    socket.socket.connect = denied
    socket.create_connection = denied
    sys.path.insert(0, str(source / "code"))
    from llm4ad.method.eohs import EoHS
    from llm4ad.method.eohs.population import Population
    from arena.frameworks.drivers.eohs_gateway_v2 import guard_native_selection
    population = Population(pop_size=2, top_k=2)
    population.register_function_set(SimpleNamespace(score=[0.1, 0.2], code="first fixture"))
    population.register_function_set(SimpleNamespace(score=[0.1, 0.2], code="distinct fixture; equal scores"))
    # Actual run() calls survival once after native initialization. The resulting
    # singleton is the observed first-pilot state; no candidate code is executed.
    population.survival()
    assert len(population) == 1 and population.generation == 2
    method = object.__new__(EoHS)
    method._population = population
    method._max_generations, method._max_sample_nums, method._tot_sample_nums = 4, 8, 2
    method._num_samplers, method._use_c_operator, method._debug_mode = 1, True, False
    method._resume_mode, method._profiler = True, None
    method._evaluation_executor = ThreadPoolExecutor(max_workers=1)
    assert method._continue_loop()
    pair_before, loop_before = Population.select_complementary_pair, EoHS._iteratively_use_eoh_operator
    record = GuardRecord(output / "selection-guard-v2.json")
    code = execute_native(method, Population, EoHS, record)
    assert code == 75 and record.event["registered_samples"] == 2
    assert not json.loads(record.path.read_text())["native_completed"]
    assert Population.select_complementary_pair is pair_before
    assert EoHS._iteratively_use_eoh_operator is loop_before
    # Healthy native pair selection remains available and is not replaced.
    healthy = Population(pop_size=2, top_k=2, generation=2)
    healthy._population = [SimpleNamespace(score=[0.1, 0.9]), SimpleNamespace(score=[0.8, 0.2])]
    untouched = GuardRecord(output / "healthy.json")
    with guard_native_selection(Population, EoHS, untouched):
        pair = healthy.select_complementary_pair()
        assert len(pair) == 2 and all(any(f is p for p in healthy.population) for f in pair)
    assert untouched.event is None
    value = {"schema": "arena.eohs-guard-conformance/2", "source_commit": COMMIT,
             "native_singleton_reproduced": True, "actual_native_sampler_thread_exits": True,
             "partial_returncode": code, "healthy_native_pair_preserved": True,
             "hooks_restored": True, "model_calls": 0, "candidate_evaluations": 0,
             "native_search_completed": False,
             "driver_sha256": hashlib.sha256((ROOT / "src/arena/frameworks/drivers/eohs_gateway_v2.py").read_bytes()).hexdigest()}
    (output / "conformance.json").write_text(json.dumps(value, indent=2) + "\n")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.source.resolve(), args.output.resolve())))
