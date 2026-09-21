# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for Sidorenko's conjecture for the bipartite graph
# H = K_{5,5} minus a perfect matching (10 vertices, 20 edges). A candidate graphon W is
# given as a symmetric n x n step-graphon matrix with entries in [0,1]; the evaluator
# computes the Sidorenko ratio t(H, W) / t(K2, W)^|E(H)| and rewards making it small.
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
import numpy as np
import sys
import os
from importlib import __import__

# BENCHMARK is the conjectured/record optimal value of the ratio. Sidorenko's conjecture
# asserts t(H, W) / t(K2, W)^|E(H)| >= 1 for every graphon W, with equality attained by
# the constant graphon. H = K_{5,5} minus a perfect matching is a known Sidorenko graph,
# so 1.0 is the best (smallest) value attainable; a value < 1 would be a counterexample.
# Source: notebook problem statement (t(H,W) >= t(K2,W)^|E(H)|); baseline ratio == 1.0.
BENCHMARK = 1.0
TOL = 1e-9
NUM_VERTICES = 10  # H has vertices 0..9 (left part 0..4, right part 5..9)

# H = K_{5,5} minus the perfect matching {0-9, 1-5, 2-6, 3-7, 4-8}; 4-regular bipartite.
EDGES = [
    (0, 5), (0, 6), (0, 7), (0, 8),
    (1, 6), (1, 7), (1, 8), (1, 9),
    (2, 7), (2, 8), (2, 9), (2, 5),
    (3, 8), (3, 9), (3, 5), (3, 6),
    (4, 9), (4, 5), (4, 6), (4, 7),
]
NUM_EDGES = len(EDGES)  # 20

# H is bipartite. We compute t(H, W) exactly for an equal-block step graphon via a fast
# two-stage tensor contraction (summing all left vertices independently, then combining
# over the right vertices), which avoids the huge intermediates of a naive 20-operand
# einsum. _LEFT / _RIGHT are the two parts; for each left vertex we contract its own
# integration variable ("z") against the matrix factors to its right neighbours.
_LEFT = sorted(set(u for u, v in EDGES))
_RIGHT = sorted(set(v for u, v in EDGES))
_RLET = {rv: chr(ord("a") + k) for k, rv in enumerate(_RIGHT)}
_NBRS = {lv: [v for (u, v) in EDGES if u == lv] for lv in _LEFT}
# Stage 1: per left vertex, subscript and number of matrix operands.
_STAGE1 = {
    lv: (
        ",".join("z" + _RLET[v] for v in _NBRS[lv]) + "->" + "".join(_RLET[v] for v in _NBRS[lv]),
        len(_NBRS[lv]),
    )
    for lv in _LEFT
}
# Stage 2: combine the per-left-vertex tensors over the right-vertex indices.
_STAGE2 = ",".join("".join(_RLET[v] for v in _NBRS[lv]) for lv in _LEFT) + "->"


def _homomorphism_sum(M: np.ndarray) -> float:
    """Exact sum over all block assignments of prod over edges M[block_u, block_v].

    Equals t(H, W) * n^(num_vertices) for the equal-block step graphon defined by M.
    """
    left_tensors = []
    for lv in _LEFT:
        sub, k = _STAGE1[lv]
        left_tensors.append(np.einsum(sub, *([M] * k), optimize=True))
    return float(np.einsum(_STAGE2, *left_tensors, optimize=True))


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        graphon = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            graphon = program.sidorenko_graphon()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(graphon, np.ndarray):
            graphon = np.array(graphon, dtype=np.float64)
        graphon = graphon.astype(np.float64)

        if graphon.ndim != 2 or graphon.shape[0] != graphon.shape[1]:
            raise ValueError(f"Graphon must be a square matrix; got shape {graphon.shape}")
        n = graphon.shape[0]
        if n < 1:
            raise ValueError("Graphon matrix must have at least one block.")

        if not np.all(np.isfinite(graphon)):
            raise ValueError("Graphon contains NaN or infinite values.")

        # A graphon is symmetric: W(x, y) = W(y, x). Interpret the construction as its
        # symmetrization (no-op if already symmetric).
        M = 0.5 * (graphon + graphon.T)

        # Feasibility: a graphon takes values in [0, 1].
        if np.min(M) < -1e-6 or np.max(M) > 1.0 + 1e-6:
            raise ValueError("Graphon entries must lie in [0, 1].")
        M = np.clip(M, 0.0, 1.0)

        # Edge density t(K2, W) = average of W over [0,1]^2 = mean of the step matrix.
        t_k2 = float(np.mean(M))
        if t_k2 <= TOL:
            raise ValueError("Edge density t(K2, W) is (near) zero; ratio is undefined.")

        # Exact homomorphism density t(H, W) for an equal-block step graphon.
        total = _homomorphism_sum(M)
        t_h = total / float(n ** NUM_VERTICES)

        # Sidorenko ratio (PRIMARY metric, minimize). >= 1 if the conjecture holds.
        denom = t_k2 ** NUM_EDGES
        if denom <= TOL:
            raise ValueError("t(K2, W)^|E(H)| underflowed to zero.")
        ratio = t_h / denom

        # Convert minimization -> higher-is-better: combined_score = BENCHMARK / ratio.
        # ratio == 1 (baseline / conjectured optimum) -> combined_score == 1.0.
        safe_ratio = max(ratio, TOL)
        combined_score = BENCHMARK / safe_ratio
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "sidorenko_ratio": float(ratio),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
