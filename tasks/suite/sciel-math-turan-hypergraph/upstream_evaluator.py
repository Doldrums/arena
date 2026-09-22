# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the hypergraph Turan number of the
# tetrahedron K4^(3): maximize the Turan density lower bound C achievable by a
# tetrahedron-free, weighted 3-uniform blow-up hypergraph.
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
from itertools import combinations_with_replacement

# Turan's conjectured optimum / classical record lower bound for K4^(3) is 5/9.
BENCHMARK = 5.0 / 9.0
TOL = 1e-12


def _is_tetrahedron_free(num_vertices: int, edge_set: set) -> bool:
    """
    A blow-up pattern contains a tetrahedron iff there exist 4 parts (a multiset
    of vertex indices, repetition allowed since blow-up parts are large) whose
    four size-3 sub-multisets are all edges. Returns True if no such quadruple
    exists.
    """
    for quad in combinations_with_replacement(range(num_vertices), 4):
        if all(tuple(sorted(quad[:i] + quad[i + 1:])) in edge_set for i in range(4)):
            return False
    return True


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        result = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            result = program.turan_hypergraph_tetrahedron()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(result, (tuple, list)) or len(result) != 2:
            raise ValueError("Constructor must return a (weights, edges) pair.")

        weights = np.asarray(result[0], dtype=np.float64).reshape(-1)
        edges = np.asarray(result[1])

        # --- Validate weights ---
        if weights.ndim != 1 or weights.shape[0] < 1:
            raise ValueError(f"Invalid weights shape: {weights.shape}")
        if not np.all(np.isfinite(weights)):
            raise ValueError("Weights contain NaN or infinite values.")
        if np.any(weights < -TOL):
            raise ValueError("Weights must be non-negative.")
        weights = np.maximum(weights, 0.0)
        total = float(weights.sum())
        if total <= TOL:
            raise ValueError("Weights sum to zero; cannot normalize.")
        w = weights / total
        num_vertices = w.shape[0]

        # --- Validate edges ---
        if edges.ndim != 2 or edges.shape[1] != 3 or edges.shape[0] < 1:
            raise ValueError(f"Invalid edges shape: {edges.shape}, expected (E, 3)")
        if not np.all(np.isfinite(edges)):
            raise ValueError("Edges contain NaN or infinite values.")
        edges_int = np.rint(edges).astype(np.int64)
        if np.any(np.abs(edges - edges_int) > 1e-6):
            raise ValueError("Edge indices must be integers.")
        if np.any(edges_int < 0) or np.any(edges_int >= num_vertices):
            raise ValueError("Edge index out of range [0, V-1].")

        # Deduplicate edges as size-3 multisets (a hypergraph edge set is a set).
        edge_set = set(tuple(sorted(int(v) for v in row)) for row in edges_int)

        # --- Feasibility: the construction must be tetrahedron-free ---
        if not _is_tetrahedron_free(num_vertices, edge_set):
            raise ValueError("Construction contains a tetrahedron K4^(3); infeasible.")

        # --- Primary metric: Turan density lower bound C ---
        turan_density = 0.0
        for edge in edge_set:
            a, b, c = edge
            distinct = len(set(edge))
            if distinct == 3:
                turan_density += 6.0 * w[a] * w[b] * w[c]
            elif distinct == 2:
                if edge.count(a) == 2:
                    dup, other = a, c
                elif edge.count(b) == 2:
                    dup, other = b, a
                else:
                    dup, other = c, a
                turan_density += 3.0 * w[dup] * w[dup] * w[other]
            else:
                turan_density += w[a] ** 3

        combined_score = turan_density / BENCHMARK
        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "turan_density": float(turan_density),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
