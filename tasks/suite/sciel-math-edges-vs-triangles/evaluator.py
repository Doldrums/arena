# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the edges-vs-triangles problem: build a
# triangle-free graph on 16 vertices that maximizes the number of edges.
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

BENCHMARK = 64
NUM_VERTICES = 16


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        M = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            M = program.graph_edges()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(M, np.ndarray):
            M = np.array(M)

        if M.shape != (NUM_VERTICES, NUM_VERTICES):
            raise ValueError(
                f"Invalid shapes: matrix = {M.shape}, expected {(NUM_VERTICES, NUM_VERTICES)}"
            )

        # Coerce to a clean undirected simple graph.
        A = (np.asarray(M) >= 0.5).astype(int)
        A = np.maximum(A, A.T)
        np.fill_diagonal(A, 0)

        num_edges = A.sum() // 2
        triangles = np.trace(A @ A @ A) // 6

        if triangles > 0:
            return {
                "num_edges": int(num_edges),
                "combined_score": 0.0,
                "error": "graph contains triangles",
            }

        return {
            "num_edges": int(num_edges),
            "combined_score": float(num_edges / BENCHMARK),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
