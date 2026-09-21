# Original CoEvo program template for this task, extracted from build_python_spec() of the pinned task module.
import numpy as np
def equation(strain: np.ndarray, temp: np.ndarray, params: np.ndarray) -> np.ndarray:
    """ Mathematical function for stress in Aluminium rod

    Args:
        strain: A numpy array representing observations of strain.
        temp: A numpy array representing observations of temperature.
        params: Array of numeric constants or parameters to be optimized, there are 10 params.

    Return:
        A numpy array representing stress as the result of applying the mathematical function to the inputs.
    """
    stress = params[0] * strain  +  params[1] * temp  # Example equation
    return stress
