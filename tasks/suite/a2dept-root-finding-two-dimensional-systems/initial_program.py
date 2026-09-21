"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def find_root_system(F, x0):
    # Newton's method with a finite-difference Jacobian.
    x = np.array(x0, dtype=float)
    for _ in range(60):
        Fx = F(x)
        if np.linalg.norm(Fx) <= 1e-12:
            return x
        J = np.zeros((2, 2))
        for j in range(2):
            e = np.zeros(2)
            e[j] = 1e-6
            J[:, j] = (F(x + e) - Fx) / 1e-6
        try:
            x = x - np.linalg.solve(J, Fx)
        except np.linalg.LinAlgError:
            break
    return x
# EVOLVE-BLOCK-END
