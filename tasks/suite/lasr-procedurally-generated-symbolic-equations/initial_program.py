"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


def fit(X_train, y_train):
    # Least-squares fit of a degree-2 polynomial feature expansion.
    def features(X):
        cols = [np.ones(len(X))] + [X[:, j] for j in range(X.shape[1])] + [X[:, i] * X[:, j] for i in range(X.shape[1]) for j in range(i, X.shape[1])]
        return np.column_stack(cols)
    w, *_ = np.linalg.lstsq(features(X_train), y_train, rcond=None)
    return lambda X: features(X) @ w
# EVOLVE-BLOCK-END
