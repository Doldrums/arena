# Extracted from EoH MIT-licensed prob.py template_program.
import numpy as np
def get_matrix_and_jobs(current_sequence: list, time_matrix: np.ndarray,
                         m: int, n: int) -> tuple:
    """Modify the processing-time matrix and select jobs to perturb.

    Args:
        current_sequence: current permutation of job indices (list of n ints)
        time_matrix:      n*m matrix of processing times (numpy array)
        m:                number of machines
        n:                number of jobs
    Returns:
        new_matrix:   modified n*m processing-time matrix (numpy array)
        perturb_jobs: list of 2-5 job indices to apply targeted local search on
    """
    return time_matrix.copy(), list(range(min(3, n)))
