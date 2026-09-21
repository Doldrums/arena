# EVOLVE-BLOCK-START
import numpy as np


def moving_sofa_2d() -> np.ndarray:
    """
    The 2D moving-sofa problem: find the largest-area rigid shape that can be moved
    through an L-shaped corridor of width 1 that makes a single 90-degree turn.

    The shape is specified IMPLICITLY by a motion "path". Each path point is a triple
    (x, y, angle_degrees) giving the position of the corridor's inner corner and the
    corridor's rotation at one instant of the move. In the reference frame of the sofa
    the corridor sweeps over the plane; the sofa is then the intersection of every
    corridor placement along the path, so by construction it always clears the corridor.
    The objective is to maximize the area of that intersection.

    The evaluator prepends the start state (0, 0, 0) and appends the end state
    (-2, 0, 90), then densifies the path to <=1-degree rotation steps, exactly as in the
    AlphaEvolve "single turn" corridor notebook.

    Returns:
        path: np.ndarray of shape (n, 3); each row is (x, y, angle_degrees) for the
            corridor's inner corner. Here n = 8. Endpoints are added by the evaluator.
    """
    # Baseline construction taken from the notebook's initial program (a hand-set path
    # that slides the inner corner along a gentle arc while rotating from ~15 to ~86 deg).
    path = np.array(
        [
            [-0.1, 0.1, 15.0],
            [-0.2, 0.2, 20.0],
            [-0.3, 0.3, 34.0],
            [-0.3, 0.3, 40.0],
            [-0.4, 0.3, 50.0],
            [-0.5, 0.2, 55.0],
            [-0.6, 0.2, 75.0],
            [-0.7, 0.3, 86.0],
        ],
        dtype=np.float64,
    )
    return path


# EVOLVE-BLOCK-END
