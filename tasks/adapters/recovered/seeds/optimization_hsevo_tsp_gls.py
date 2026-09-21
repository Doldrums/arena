"""Recreated baseline for HSEvo's actual one-matrix GLS evaluator contract.
The released seed has an incompatible three-argument function; use the standard
GLS distance guidance, matching the evaluator's heuristics(distance_matrix).
"""
import numpy as np

def heuristics(distance_matrix: np.ndarray) -> np.ndarray:
    return distance_matrix.copy()
