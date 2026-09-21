# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for an OFFLINE PROXY of AlphaEvolve Problem 66,
# "The function guessing game".
#
# DEVIATION FROM THE UPSTREAM NOTEBOOK (read this carefully):
#   The upstream problem is INTERACTIVE / AGENTIC: a program guesses a hidden function
#   f: R -> R, and to gather information it may (1) evaluate the function at a point for
#   1 currency unit, (2) ask a yes/no Oracle for 10 units, or (3) query a separate LLM
#   for 10 units, executing any code it returns. The reward is 1000 currency units per
#   function reconstructed within a small L^1 error. This loop depends on live LLM/Oracle
#   calls and therefore does NOT fit our deterministic, offline constructor+evaluator
#   contract.
#
#   We implement the closest faithful runnable version: the deterministic economic core
#   of the game using ONLY the cheapest information source (point evaluations). A
#   "strategy" is a fixed set of k query locations in [-1, 1]. The hidden functions are a
#   fixed, seeded family of degree-5 polynomials. For each hidden function the evaluator:
#     - samples it at the strategy's query points (paying k currency units),
#     - reconstructs it by degree-5 least-squares polynomial interpolation,
#     - awards the 1000-unit reward iff the reconstruction's mean L^1 error over a dense
#       grid is below a small threshold.
#   The score is the NET REWARD = 1000 * (fraction correct) - k. Because a degree-D
#   polynomial is pinned down by D + 1 distinct samples, the optimal strategy uses
#   exactly DEGREE + 1 = 6 well-chosen, distinct points (duplicate or out-of-domain
#   points waste money and break reconstruction). This preserves the original game's
#   reward-vs-query-cost trade-off while being fully deterministic and offline.
#
# ===--------------------------------------------------------------------------------------===#
#
# Some of the code in this file is adapted from:
#
# google-deepmind/alphaevolve_results:
# Licensed under the Apache License v2.0.
#
# ===--------------------------------------------------------------------------------------===#

import time
import warnings
import numpy as np
import sys
import os
from importlib import __import__

DEGREE = 5  # Degree of the hidden polynomial functions.
NUM_FUNCTIONS = 20  # Size of the fixed, seeded hidden-function test family.
REWARD = 1000.0  # Currency units earned per function reconstructed correctly.
OPTIMAL_QUERIES = DEGREE + 1  # 6: minimum samples that pin down a degree-5 polynomial.
DOMAIN = 1.0  # Query domain is [-DOMAIN, DOMAIN].
GRID_POINTS = 256  # Dense grid for measuring reconstruction L^1 error.
L1_THRESHOLD = 1e-4  # Mean L^1 error below which a reconstruction counts as correct.
TOL = 1e-9  # Tolerance for the domain feasibility check.

# Best achievable net reward: reconstruct every function correctly using the minimal
# number of queries. Used to normalize combined_score toward 1.0.
BENCHMARK = REWARD - OPTIMAL_QUERIES  # 994.0


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        query_points = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            query_points = program.function_guessing_game_strategy()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(query_points, np.ndarray):
            query_points = np.array(query_points)
        query_points = np.asarray(query_points, dtype=np.float64).reshape(-1)

        # ---- Validation -------------------------------------------------------------
        if query_points.ndim != 1 or query_points.shape[0] < 1:
            raise ValueError(
                f"Strategy must be a non-empty 1-D array of query points; got shape "
                f"{query_points.shape}"
            )
        if not np.all(np.isfinite(query_points)):
            raise ValueError("Query points contain NaN or infinite values.")
        if np.any(np.abs(query_points) > DOMAIN + TOL):
            raise ValueError(
                f"Query points must lie within the domain [-{DOMAIN}, {DOMAIN}]; "
                "an infeasible (out-of-domain) evaluation was requested."
            )

        num_queries = int(query_points.shape[0])

        # ---- Fixed, seeded family of hidden degree-5 polynomials --------------------
        rng = np.random.RandomState(0)
        coeffs = rng.uniform(-1.0, 1.0, size=(NUM_FUNCTIONS, DEGREE + 1))

        grid = np.linspace(-DOMAIN, DOMAIN, GRID_POINTS)

        # ---- Play the game against every hidden function ----------------------------
        # A degree-D polynomial needs at least D + 1 DISTINCT samples to be recovered;
        # a degenerate query set (too few distinct points) reconstructs nothing and
        # earns no reward. Short-circuiting it also avoids ill-posed least-squares fits.
        num_correct = 0
        if np.unique(query_points).shape[0] >= DEGREE + 1:
            for c in coeffs:
                # Pay to sample the hidden function at the strategy's query points.
                sampled_values = np.polyval(c, query_points)
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        recon = np.polyfit(query_points, sampled_values, DEGREE)
                except Exception:
                    # Reconstruction impossible (degenerate query set): no reward.
                    continue
                if not np.all(np.isfinite(recon)):
                    continue

                true_curve = np.polyval(c, grid)
                recon_curve = np.polyval(recon, grid)
                l1_error = float(np.mean(np.abs(recon_curve - true_curve)))
                if l1_error < L1_THRESHOLD:
                    num_correct += 1

        fraction_correct = num_correct / NUM_FUNCTIONS
        net_reward = REWARD * fraction_correct - num_queries

        combined_score = net_reward / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "net_reward": float(net_reward),
            "fraction_correct": float(fraction_correct),
            "num_queries": int(num_queries),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
