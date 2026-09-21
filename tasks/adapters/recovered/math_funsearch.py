"""Run the pinned FunSearch greedy constructors with candidate priority functions.

Construction code is unchanged; this wrapper checks priorities and independently
certifies the returned mathematical objects. Search/model infrastructure is omitted.
"""
import importlib.util
import itertools
import math
import numbers
from pathlib import Path
import sys


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def certify(points, problem, n):
    """Independent exact checks, including maximality for the minimizing task."""
    if problem == "nat":
        if not points or len(set(points)) != len(points) or any(type(x) is not int or not 0 <= x <= n for x in points):
            raise ValueError("Invalid admissible tuple domain")
        for p in range(2, len(points) + 1):
            if all(p % d for d in range(2, math.isqrt(p) + 1)) and len({x % p for x in points}) == p:
                raise ValueError("Tuple fills every residue class")
        return
    # Certificates must already be integer coordinates. Truncating a float or
    # accepting bool would certify a different object than the one returned.
    try:
        tuples = [tuple(p) for p in points]
    except TypeError as exc:
        raise ValueError("Invalid point set coordinates") from exc
    if any(not isinstance(x, numbers.Integral) or isinstance(x, bool)
           for p in tuples for x in p):
        raise ValueError("Point coordinates must be integers")
    tuples = [tuple(int(x) for x in p) for p in tuples]
    dimension, bound = (n, 3) if problem == "cap" else (2, n)
    if not tuples or len(set(tuples)) != len(tuples) or any(len(p) != dimension or any(x < 0 or x >= bound for x in p) for p in tuples):
        raise ValueError("Invalid point set")
    existing = set(tuples)
    if problem == "cap":
        for a, b in itertools.combinations(tuples, 2):
            if tuple((-x-y) % 3 for x, y in zip(a, b)) in existing:
                raise ValueError("Cap set contains a line")
    else:
        def distance(a, b):
            return sum((x-y)**2 for x, y in zip(a, b))
        for a, b, c in itertools.combinations(tuples, 3):
            if len({distance(a, b), distance(a, c), distance(b, c)}) != 3:
                raise ValueError("Set contains an isosceles triple")
        if problem == "minimum-maximal":
            for point in itertools.product(range(n), repeat=2):
                if point not in existing and not any(
                    len({distance(a, b), distance(a, point), distance(b, point)}) != 3
                    for a, b in itertools.combinations(tuples, 2)):
                    raise ValueError("Isosceles-free set is not maximal")


def evaluate(candidate_path, *, checkout, problem, n):
    import numpy as np
    paths = {"cap": "cap_set_spec.py", "nat": "nat_spec.py",
             "no-isosceles": "isosceles.py", "minimum-maximal": "isosceles.py"}
    if problem not in paths or type(n) is not int or n < 2:
        raise ValueError("Unsupported task or dimension")
    root = Path(checkout).resolve()
    sys.path.insert(0, str(root))
    original = _load("_original_funsearch_spec", root / "examples" / paths[problem])
    candidate = _load("_funsearch_candidate", candidate_path)
    function = candidate.priority
    calls = 0
    def checked(*args):
        nonlocal calls
        calls += 1
        value = function(*args)
        if problem == "nat":
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise ValueError("NAT priority must return an integer residue")
            return int(value)
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real) or not np.isfinite(value):
            raise ValueError("Priority must return a finite real scalar")
        return float(value)
    original.priority = checked
    points = original.solve(n)
    certify(points, problem, n)
    return {"score": len(points), "validity": True, "problem": problem, "n": n,
            "candidate_calls": calls, "certificate": np.asarray(points).tolist(),
            "profile": "published_dimension_original_constructor",
            "validation_scope": "independent exact combinatorial certificate"}
