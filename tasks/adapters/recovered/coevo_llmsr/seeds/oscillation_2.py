# Original CoEvo program template for this task, extracted from build_python_spec() of the pinned task module.
import numpy as np
def equation(t: np.ndarray, x: np.ndarray, v: np.ndarray, params: np.ndarray) -> np.ndarray:
    """ Mathematical function for acceleration in a damped nonlinear oscillator

    Args:
        t: A numpy array representing time.
        x: A numpy array representing observations of current position.
        v: A numpy array representing observations of velocity.
        params: Array of numeric constants or parameters to be optimized, there are 10 params.
    Return:
        A numpy array representing acceleration as the result of applying the mathematical function to the inputs.
    """
    dv = params[0] * t + params[1] * x  +  params[2] * v +  + params[3]  # Example equation
    return dv
