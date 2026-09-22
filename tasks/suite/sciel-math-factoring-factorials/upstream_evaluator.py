# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the "factoring factorials" problem: factoring N!
# into N factors so as to maximize the smallest factor, with N = 100.
#
# ===--------------------------------------------------------------------------------------===#
#
# Some of the code in this file is adapted from:
#
# google-deepmind/alphaevolve_results:
# Licensed under the Apache License v2.0.
#
# ===--------------------------------------------------------------------------------------===#
#
# DEVIATION FROM THE UPSTREAM NOTEBOOK
# The upstream notebook's reference signature is `get_factorization(n) -> list[list[int]]`
# (a ragged list of N prime groups). This template requires a no-argument constructor that
# returns a numpy array, so the solution is represented as a 1-D integer *bin-assignment*
# array over the prime factors of N! taken in a fixed canonical order (sorted ascending, with
# multiplicity). This is mathematically equivalent: assign[i] is the factor/bin that the i-th
# canonical prime is placed into, and the factor values are the per-bin products. The notebook
# ships only an empty baseline stub and no known optimal constant, so BENCHMARK is set to the
# score of this template's own deterministic greedy baseline (combined_score starts at ~1.0).

import os
import sys
import time
from importlib import __import__

import numpy as np

# Number of factors N, and the score of the greedy baseline construction for N = 100. The
# upstream notebook gives no known-optimal constant, so BENCHMARK is the baseline's own score.
N = 100
BENCHMARK = 26.0


def _prime_factors_factorial(n: int):
    """Multiset of prime factors of n! in canonical ascending order (with multiplicity)."""
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, n + 1, i):
                is_prime[j] = False
    factors = []
    for p in range(2, n + 1):
        if not is_prime[p]:
            continue
        exponent = 0
        pk = p
        while pk <= n:
            exponent += n // pk
            pk *= p
        factors.extend([p] * exponent)
    factors.sort()
    return factors


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        assign = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            assign = program.factoring_factorials100()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        primes = _prime_factors_factorial(N)
        length = len(primes)

        if not isinstance(assign, np.ndarray):
            assign = np.array(assign)

        if assign.shape != (length,):
            raise ValueError(
                f"Invalid shape: assign = {assign.shape}, expected {(length,)}"
            )

        if not np.all(np.isfinite(assign)):
            raise ValueError("Assignment contains NaN or infinite values.")

        # Must be integer bin indices in [0, N-1].
        assign_int = np.round(assign).astype(np.int64)
        if not np.array_equal(assign_int, assign):
            raise ValueError("Assignment entries must be integers.")
        if assign_int.min() < 0 or assign_int.max() > N - 1:
            raise ValueError(f"Bin indices must lie in [0, {N - 1}].")

        # Compute the N factor values as exact integer products (Python ints, no overflow).
        products = [1] * N
        for i in range(length):
            products[int(assign_int[i])] *= primes[i]

        # Sanity check: the multiset of prime factors must be exactly reproduced (it always is
        # for a valid bin-assignment, but verify to never reward an infeasible factorization).
        total = 1
        for p in primes:
            total *= p
        prod_all = 1
        for v in products:
            prod_all *= v
        if prod_all != total:
            raise ValueError("Factorization does not reproduce N! exactly.")

        min_factor = min(products)

        combined_score = min_factor / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "min_factor": float(min_factor),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
