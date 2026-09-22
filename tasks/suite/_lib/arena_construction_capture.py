"""Observe a pinned evaluation and validate its one returned construction.

The candidate is never rerun. Only returns from the expected Python constructor,
called directly by the pinned evaluator, are accepted. Unsupported call shapes
or missing/ambiguous observations remain unknown. Numerical predicates are not
theorem or optimality certificates; original scorer bytes and values are kept.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import numpy as np

from arena_construction_checks import check_construction


CONTRACTS = {
    "no_five_sphere": (("no_5_on_a_sphere8",), {"_has_five_cospherical": ("points",)}),
    "pipeline_config": (("run_pipeline", "configure_pipeline"), {"validate_config": ("config",)}),
    "squarefree_subset": (("erdos_squarefree500",), {"_squarefree_sieve": ("limit",)}),
    "factorial_assignment": (("factoring_factorials100",), {"_prime_factors_factorial": ("n",)}),
    "sarkozy_subset": (("furstenberg_sarkozy_205",), {}),
    "no_isosceles_grid": (("grid_subset",), {}),
    "flat_sign_polynomial": (("flat_polynomial",), {}),
    "sendov_roots": (("sendov_polynomial6",), {}),
}
LOCAL_INPUTS = {
    "points", "config", "subset", "sf", "violations", "primes", "assign_int",
    "products", "prod_all", "total", "elements", "a", "roots", "poly", "crit_points",
}
UNSUPPORTED = object()


def _snapshot(value, depth=0):
    """Copy only plain data, without invoking a candidate's copy/coercion hooks."""
    if depth > 5:
        return UNSUPPORTED
    if type(value) in (int, float, complex, bool, str, type(None)):
        return value
    if type(value) is np.ndarray:
        return value.copy() if value.dtype.kind in "biufc" else UNSUPPORTED
    if type(value) in (list, tuple):
        return type(value)(_snapshot(item, depth + 1) for item in value)
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _snapshot(item, depth + 1) for key, item in value.items()}
    if isinstance(value, np.generic) and value.dtype.kind in "biufc":
        scalar = value.item()
        return scalar if type(scalar) in (int, float, complex, bool) else UNSUPPORTED
    return UNSUPPORTED


def evaluate_construction(program_path, wrapper_file, contract, upstream_sha256):
    path = Path(wrapper_file).with_name("upstream_evaluator.py")
    if hashlib.sha256(path.read_bytes()).hexdigest() != upstream_sha256:
        raise ValueError("Original evaluator differs from the reviewed construction contract")
    spec = importlib.util.spec_from_file_location("arena_construction_" + contract, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names, helper_fields = CONTRACTS[contract]
    evaluator_code = module.evaluate.__code__
    helper_codes = {getattr(module, name).__code__: name for name in helper_fields}
    candidates, evaluations = [], []
    observations = {name: [] for name in helper_fields}
    previous = sys.getprofile()

    def observe(frame, event, value):
        if previous is not None:
            previous(frame, event, value)
        if event != "return":
            return
        if frame.f_code is evaluator_code:
            evaluations.append({"result": value, "locals": {
                key: _snapshot(item) for key, item in frame.f_locals.items() if key in LOCAL_INPUTS}})
            return
        caller = frame.f_back
        trusted = caller is not None and caller.f_code is evaluator_code
        if frame.f_code in helper_codes:
            name = helper_codes[frame.f_code]
            observations[name].append({"trusted_call": trusted, "conclusion": _snapshot(value),
                "arguments": {key: _snapshot(frame.f_locals[key]) for key in helper_fields[name]}})
        if trusted:
            program = caller.f_locals.get("program") or caller.f_locals.get("module")
            for name in names:
                function = getattr(program, name, None)
                if getattr(function, "__code__", None) is frame.f_code:
                    candidates.append(_snapshot(value))
                    break

    try:
        sys.setprofile(observe)
        result = module.evaluate(str(program_path))
    finally:
        sys.setprofile(previous)
    if type(result) is not dict:
        raise ValueError("Original evaluator did not return its metric dictionary")
    checks, validity = None, None
    if (len(candidates) == len(evaluations) == 1 and
            evaluations[0]["result"] is result):
        checks = check_construction(contract, module, candidates[0],
                                    evaluations[0]["locals"], observations)
        if checks:
            validity = all(checks.values())
    if result.get("error"):
        validity = False
    return {**result, "arena_valid": validity, "arena_validation": {
        "contract": contract, "upstream_evaluator_sha256": upstream_sha256,
        "candidate_observations": len(candidates), "evaluator_observations": len(evaluations),
        "verifier_observations": {name: len(rows) for name, rows in observations.items()},
        "checks": checks,
        "scope": "Feasibility of this same evaluation's construction; not optimality or a theorem.",
    }}
