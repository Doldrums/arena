"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


class Policy:
    """LinUCB with a forgetting factor."""

    def __init__(self, n_arms, dim):
        self.n, self.d = n_arms, dim
        self.A = [np.eye(dim) for _ in range(n_arms)]
        self.b = [np.zeros(dim) for _ in range(n_arms)]

    def select(self, context):
        scores = []
        for a in range(self.n):
            inv = np.linalg.inv(self.A[a])
            theta = inv @ self.b[a]
            scores.append(theta @ context + 0.5 * np.sqrt(context @ inv @ context))
        return int(np.argmax(scores))

    def update(self, context, arm, reward):
        self.A[arm] = 0.995 * self.A[arm] + np.outer(context, context)
        self.b[arm] = 0.995 * self.b[arm] + reward * context
# EVOLVE-BLOCK-END
