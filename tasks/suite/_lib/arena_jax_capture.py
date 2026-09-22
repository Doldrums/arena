"""Bind numerical feasibility checks to one pinned evaluator invocation.

The candidate is called only by the unchanged original scorer. Missing or
ambiguous constructor/verifier observations stay unknown. This is cooperative
same-process validation, not an adversarial verifier or a theorem certificate.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

from arena_jax_snapshot import snapshot as _snapshot
from arena_jax_checks import check_jax_construction


CONTRACTS = {
    "autocorrelation_c1": ("run", "verify_autocorrelation_solution",
                           ("f_values", "c1_achieved", "n_points")),
    "autocorrelation_c2": ("run", "verify_c2_solution",
                           ("f_values", "c2_achieved_from_opt", "n_points")),
    "autocorrelation_c3": ("run", "verify_c3_solution",
                           ("f_values", "c3_achieved", "n_points")),
    "minimum_overlap": ("run", "verify_c5_solution", ("h_values", "c5_achieved", "n_points")),
    "finite_sum_difference": ("run", "verify_c6_solution", ("u_set", "c6_achieved")),
    "matmul_2_4_5": ("run", "verify_tensor_decomposition", ("decomposition", "n", "m", "p", "rank")),
    "heilbronn_convex_14": ("heilbronn_convex14", None, ()),
    "sign_uncertainty": ("run", "verify_c4_solution_strict", ("user_coeffs", "reported_c4", "reported_rmax")),
}
LOCAL_FIELDS = {
    "f_values", "h_values", "c1_achieved", "c2_achieved_from_opt", "c2_verified",
    "c3_achieved", "c5_bound", "c6_bound", "n_points", "decomposition", "n", "m",
    "p", "rank", "points", "min_triangle_area", "convex_hull_area",
    "min_area_normalized", "u_set", "coeffs", "c4_bound", "r_max", "c4", "rmax",
}


def evaluate_jax_construction(program_path, wrapper_file, contract, upstream_sha256):
    path = Path(wrapper_file).with_name("upstream_evaluator.py")
    if hashlib.sha256(path.read_bytes()).hexdigest() != upstream_sha256:
        raise ValueError("Original evaluator differs from the pinned numerical contract")
    spec = importlib.util.spec_from_file_location("arena_jax_" + contract, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    constructor, verifier, arguments = CONTRACTS[contract]
    evaluator_code = module.evaluate.__code__
    verifier_code = getattr(module, verifier).__code__ if verifier else None
    candidates, evaluations, verifiers = [], [], []
    previous = sys.getprofile()

    def observe(frame, event, value):
        if previous is not None:
            previous(frame, event, value)
        if event != "return":
            return
        if frame.f_code is evaluator_code:
            evaluations.append({"result": value, "locals": {
                key: _snapshot(item) for key, item in frame.f_locals.items()
                if key in LOCAL_FIELDS}})
            return
        caller = frame.f_back
        trusted = caller is not None and caller.f_code is evaluator_code
        if frame.f_code is verifier_code:
            verifiers.append({"trusted_call": trusted, "conclusion": _snapshot(value),
                              "arguments": {key: _snapshot(frame.f_locals[key]) for key in arguments}})
        if trusted:
            function = getattr(caller.f_locals.get("program"), constructor, None)
            if getattr(function, "__code__", None) is frame.f_code:
                candidates.append(_snapshot(value))

    try:
        sys.setprofile(observe)
        result = module.evaluate(str(program_path))
    finally:
        sys.setprofile(previous)
    if type(result) is not dict:
        raise ValueError("Original evaluator did not return a metric dictionary")
    checks, measurements, validity = None, {}, None
    same_call = len(candidates) == len(evaluations) == 1 and evaluations[0]["result"] is result
    same_verifier = verifier is None or (len(verifiers) == 1 and verifiers[0]["trusted_call"])
    if same_call and same_verifier and not result.get("error"):
        checks, measurements = check_jax_construction(
            contract, module, candidates[0], evaluations[0]["locals"], result,
            verifiers[0] if verifier else None)
        if checks:
            validity = all(checks.values())
    if result.get("error"):
        validity = False
    return {**result, "arena_valid": validity, "arena_validation": {
        "contract": contract, "upstream_evaluator_sha256": upstream_sha256,
        "candidate_observations": len(candidates), "evaluator_observations": len(evaluations),
        "verifier_observations": len(verifiers), "checks": checks, "measurements": measurements,
        "scope": "Feasibility and numerical consistency of this same finite construction; not a theorem, exact algebraic certificate, optimum, or paper reproduction.",
    }}
