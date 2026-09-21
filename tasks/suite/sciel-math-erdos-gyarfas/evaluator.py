# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the Erdős-Gyárfás conjecture counterexample
# search: a finite graph with minimum degree at least 3 that avoids cycles whose length
# is a power of two.
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
from collections import deque

# The conjecture (believed true) says a minimum-degree->=3 graph must contain a
# power-of-two cycle, so no perfect counterexample (cost 0) is known. With no record
# constant available, BENCHMARK is set to the seeded baseline construction's own cost
# (the number of power-of-two cycles in its fundamental cycle basis), so that the
# initial program scores combined_score ~= 1.0 and improvements push it higher.
BENCHMARK = 14
MIN_DEGREE = 3
MIN_NODES = 4
MAX_NODES = 2000


def _fundamental_cycle_lengths(adjacency: np.ndarray):
    """
    Lengths of the fundamental cycles of a BFS spanning forest of the graph. This mirrors
    the notebook's nx.cycle_basis (a cycle basis built from a spanning forest); each
    non-tree edge closes exactly one fundamental cycle. The specific spanning forest can
    differ from networkx's, so the exact set of basis-cycle lengths is implementation
    dependent, but the construction is the same in spirit.
    """
    n = adjacency.shape[0]
    visited = np.zeros(n, dtype=bool)
    parent = -np.ones(n, dtype=np.int64)
    depth = np.zeros(n, dtype=np.int64)
    tree_edges = set()

    for s in range(n):
        if visited[s]:
            continue
        visited[s] = True
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v in np.nonzero(adjacency[u])[0]:
                v = int(v)
                if not visited[v]:
                    visited[v] = True
                    parent[v] = u
                    depth[v] = depth[u] + 1
                    tree_edges.add((min(u, v), max(u, v)))
                    queue.append(v)

    lengths = []
    rows, cols = np.nonzero(np.triu(adjacency, 1))
    for u, v in zip(rows.tolist(), cols.tolist()):
        if (u, v) in tree_edges:
            continue
        # Walk both endpoints up to their lowest common ancestor in the spanning tree.
        a, b, steps = u, v, 0
        while depth[a] > depth[b]:
            a = int(parent[a])
            steps += 1
        while depth[b] > depth[a]:
            b = int(parent[b])
            steps += 1
        while a != b:
            a = int(parent[a])
            b = int(parent[b])
            steps += 2
        lengths.append(steps + 1)  # +1 for the non-tree edge that closes the cycle
    return lengths


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        adjacency = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            adjacency = program.erdos_gyarfas_graph()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(adjacency, np.ndarray):
            adjacency = np.array(adjacency)

        # ---- structural validation: a simple undirected graph as a 0/1 adjacency matrix ----
        if adjacency.ndim != 2 or adjacency.shape[0] != adjacency.shape[1]:
            raise ValueError(f"Adjacency matrix must be square 2D; got shape {adjacency.shape}")

        n = adjacency.shape[0]
        if n < MIN_NODES or n > MAX_NODES:
            raise ValueError(f"Number of vertices {n} outside [{MIN_NODES}, {MAX_NODES}]")

        if not np.all(np.isfinite(adjacency)):
            raise ValueError("Adjacency matrix contains NaN or infinite values.")

        adjacency = np.rint(adjacency).astype(np.int64)
        if not np.array_equal(np.unique(adjacency), np.array([0, 1])) and not set(
            np.unique(adjacency).tolist()
        ).issubset({0, 1}):
            raise ValueError("Adjacency matrix must be {0, 1}-valued.")
        if np.any(np.diag(adjacency) != 0):
            raise ValueError("Adjacency matrix must have a zero diagonal (no self-loops).")
        if not np.array_equal(adjacency, adjacency.T):
            raise ValueError("Adjacency matrix must be symmetric (undirected graph).")

        # ---- feasibility constraint: minimum degree at least 3 ----
        degrees = adjacency.sum(axis=1)
        if int(degrees.min()) < MIN_DEGREE:
            raise ValueError(
                f"Infeasible: minimum degree {int(degrees.min())} < required {MIN_DEGREE}."
            )

        # ---- primary metric: number of power-of-two cycles in the cycle basis ----
        lengths = _fundamental_cycle_lengths(adjacency)
        num_power2_cycles = sum(
            1 for length in lengths if length >= 4 and (length & (length - 1)) == 0
        )

        # Minimization (fewer power-of-two cycles is better, 0 = a true counterexample)
        # converted to higher-is-better via score = BENCHMARK / cost, mirroring the other
        # minimization problems in this repo. cost == 0 means the (open) target is met, so
        # we award a finite score just above the best positive-cost score.
        if num_power2_cycles > 0:
            combined_score = BENCHMARK / float(num_power2_cycles)
        else:
            combined_score = float(BENCHMARK + 1)

        if not np.isfinite(combined_score):
            combined_score = 0.0

        return {
            "num_power2_cycles": float(num_power2_cycles),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
