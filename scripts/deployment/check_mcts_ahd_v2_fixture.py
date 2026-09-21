#!/usr/bin/env python3
"""Offline fixed-response conformance against the pinned native parser/evaluator.

This deliberately evaluates two reviewed, fixed heuristics in a fresh source
copy. It never creates a provider client, calls a model or runs native search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def check(source, destination):
    from arena.frameworks.drivers.mcts_ahd_gateway_v2 import COMMIT, SIGNATURE, SOURCE_HASHES, AttemptBudget, ProposalBudgetExhausted, bounded_native_attempts
    from arena.frameworks.runtime import verify_source
    revision = verify_source(source, COMMIT)
    if not destination.is_absolute() or destination.exists():
        raise ValueError("Fixture destination must be new and absolute")
    destination.mkdir(mode=0o750)
    workspace = destination / "workspace"
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    for relative, digest in SOURCE_HASHES.items():
        if hashlib.sha256((workspace / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("Pinned fixture source mismatch: " + relative)
    sys.path.insert(0, str(workspace))
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.chdir(destination)
    # The fixture response is constant; accidental in-process networking fails.
    def forbidden_network(*args, **kwargs):
        raise AssertionError("No provider/network calls are allowed in this fixture")
    socket.create_connection = forbidden_network
    socket.socket.connect = forbidden_network
    from omegaconf import OmegaConf
    from problem_adapter import Problem
    from source.evolution import Evolution
    from source.evolution_interface import InterfaceEC
    cfg = OmegaConf.create({"timeout": 60, "problem": OmegaConf.to_container(OmegaConf.load(workspace / "cfg/problem/bpp_online.yaml"))})
    results = []
    for name in ("priority", "priority_v2"):
        if name == "priority_v2":
            (workspace / "prompts/bpp_online/func_signature.txt").write_text(SIGNATURE + "\n")
        problem = Problem(cfg, str(workspace))
        assert problem.prompts.get_func_name() == name
        response = ("{Place each item in the tightest feasible bin.}\nimport numpy as np\n"
                    f"def {name}(item: float, bins_remain_cap: np.ndarray) -> np.ndarray:\n"
                    "    priority = -(bins_remain_cap - item)\n    return priority\n")
        calls = []
        class FixedClient:
            def chat_completion(self, n, messages, temperature):
                assert n == 1 and "function named '" + name + "'" in messages[0]["content"]
                calls.append(messages)
                return [SimpleNamespace(message=SimpleNamespace(content=response))]
        evolution = Evolution("unused.invalid", "no-real-key", FixedClient(), False, problem.prompts,
                              use_local_llm=False, url=None)
        code, thought = evolution.i1()  # Actual upstream parser, unchanged.
        compile(code, "fixed-native-parser-output", "exec")
        objectives = problem.batch_evaluate([code], 0)  # Actual native subprocess/scorer.
        assert len(calls) == 1 and isinstance(objectives, list) and len(objectives) == 1
        value = float(objectives[0])
        assert math.isinf(value) if name == "priority" else math.isfinite(value) and value > 0
        results.append({"function_name": name, "valid_native_objective": math.isfinite(value),
                        "native_objective": value if math.isfinite(value) else None,
                        "parsed_code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                        "fixed_response_count": len(calls)})
    # Exercise the real native catch-and-retry path, with deterministic parse failure.
    native = InterfaceEC.__new__(InterfaceEC)
    def invalid_response():
        raise ValueError("fixed malformed-response fixture")
    native.evol = SimpleNamespace(i1=invalid_response)
    budget = AttemptBudget(8, 3, destination / "guard-fixture.json")
    try:
        with bounded_native_attempts(InterfaceEC, budget):
            native.get_algorithm(0, [], "i1")
    except ProposalBudgetExhausted:
        assert len(budget.events) == 3 and budget.exhausted == "initialization"
    else:
        raise AssertionError("Native retry loop escaped the initialization limit")
    # A separate synthetic control-flow fixture exercises the real tree loop.
    # Its deterministic objectives are ONLY branch-test inputs, never results.
    from source.getParas import Paras
    from source.mcts_ahd import MCTS_AHD
    from source import prob_rank, pop_greedy
    search_problem = Problem(cfg, str(workspace))
    scores, responses = [], []
    def fixed_objective(codes, iteration):
        assert len(codes) == 1
        scores.append(codes[0])
        return [1.0 + 1.0 / len(scores)]
    search_problem.batch_evaluate = fixed_objective
    class FixedSearchClient:
        def chat_completion(self, n, messages, temperature):
            prompt = messages[0]["content"]
            if temperature == 0:  # Native post_thought/_get_thought uses temp=0.
                text = "A fixed control-flow fixture description."
            else:
                responses.append(prompt)
                text = ("{Fixed control-flow response.}\nimport numpy as np\n"
                        "def priority_v2(item: float, bins_remain_cap: np.ndarray) -> np.ndarray:\n"
                        f"    fixture_index = {len(responses)}\n"
                        "    priority = -(bins_remain_cap - item)\n    return priority\n")
            return [SimpleNamespace(message=SimpleNamespace(content=text))]
    parameters = Paras()
    control = destination / "synthetic-tree-control-fixture"
    control.mkdir()
    parameters.set_paras(method="mcts_ahd", init_size=2, pop_size=2,
                         llm_model=FixedSearchClient(), ec_fe_max=4,
                         exp_output_path=str(control) + "/", exp_debug_mode=False, eva_timeout=60)
    algorithm = MCTS_AHD(parameters, search_problem, prob_rank, pop_greedy)
    tree_budget = AttemptBudget(8, 3, control / "attempts.json")
    with bounded_native_attempts(InterfaceEC, tree_budget):
        algorithm.run()
    assert len(scores) == len(responses) == len(tree_budget.events) == 7
    assert [e["operator"] for e in tree_budget.events] == ["i1", "e1", "e2", "m1", "m1", "m2", "m2"]
    assert [e["phase"] for e in tree_budget.events] == ["initialization"] * 2 + ["search"] * 5
    tree_budget.status = "synthetic_control_fixture_returned"
    tree_budget.save()
    evidence = {"schema": "arena.mcts-offline-conformance/2", "source": revision,
                "results": results, "actual_native_parser": True, "actual_native_evaluator": True,
                "native_retry_guard": {"attempts": 3, "status": "budget_exhausted"},
                "synthetic_tree_control_fixture": {"actual_native_tree_loop": True, "synthetic_objectives": True,
                                                   "initialization_attempts": 2, "tree_operator_attempts": 5,
                                                   "total_attempts": 7, "native_max_fe_target": 4},
                "model_calls": 0, "research_executed": False, "canonical_evaluation": False,
                "scope": "Two fixed-response parser/evaluator fixtures, a malformed-response guard fixture, and a separate real-tree control-flow test with synthetic objectives; no research result."}
    (destination / "conformance.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.source, args.destination), indent=2))


if __name__ == "__main__":
    main()
