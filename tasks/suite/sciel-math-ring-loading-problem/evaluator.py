# ===--------------------------------------------------------------------------------------===#
#
# This file implements the evaluator for the SONET ring loading problem on a ring of
# 10 nodes with a fixed set of 15 demands.
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

NUM_NODES = 10
NUM_EDGES = 10

# Fixed problem instance: a list of (source, target, weight) demand triples.
DEMANDS = [(0,5,3),(1,7,2),(2,9,4),(3,6,1),(0,4,5),(2,8,2),(5,9,3),(1,4,2),(6,0,4),(3,8,1),(7,2,3),(4,9,2),(8,1,5),(0,6,1),(5,2,2)]

# Maximum edge load of the all-clockwise routing (all zeros) for the fixed DEMANDS above.
BENCHMARK = 23.0


def clockwise_edges(s: int, t: int):
    """Edges traversed by routing a demand from s to t clockwise (the +1 direction).

    Clockwise from s to t traverses edges s, s+1, ..., t-1 (indices mod NUM_NODES).
    """
    edges = []
    i = s % NUM_NODES
    while i != t % NUM_NODES:
        edges.append(i)
        i = (i + 1) % NUM_NODES
    return edges


def evaluate(program_path: str):
    try:
        abs_program_path = os.path.abspath(program_path)
        program_dir = os.path.dirname(abs_program_path)
        module_name = os.path.splitext(os.path.basename(program_path))[0]

        routing = None
        try:
            sys.path.insert(0, program_dir)
            program = __import__(module_name)

            start_time = time.time()
            routing = program.ring_routing()
            end_time = time.time()
            eval_time = end_time - start_time
        except Exception as err:
            raise err
        finally:
            if program_dir in sys.path:
                sys.path.remove(program_dir)

        if not isinstance(routing, np.ndarray):
            routing = np.array(routing)

        routing = np.asarray(routing).reshape(-1)
        if routing.shape != (len(DEMANDS),):
            raise ValueError(
                f"Invalid shape: routing = {routing.shape}, expected {(len(DEMANDS),)}"
            )

        # Coerce each entry to a 0/1 direction (>= 0.5 -> counter-clockwise).
        directions = (routing >= 0.5).astype(int)

        all_edges = set(range(NUM_EDGES))
        loads = np.zeros(NUM_EDGES)
        for (s, t, w), d in zip(DEMANDS, directions):
            cw = clockwise_edges(s, t)
            if d == 0:
                path_edges = cw
            else:
                path_edges = list(all_edges - set(cw))
            for e in path_edges:
                loads[e] += w

        max_load = float(loads.max())

        combined_score = BENCHMARK / max_load if max_load > 0 else 0.0

        return {
            "max_load": float(max_load),
            "combined_score": float(combined_score),
            "eval_time": float(eval_time),
        }
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}
