# EVOLVE-BLOCK-START
"""Symbolic-regression example for OpenEvolve (self-contained, drop-in).

Discover a closed-form model y = f(X) for a hidden 2-feature target from
sampled data. The naive seed is a plain linear model and fits the nonlinear
target poorly; evolution must discover the right STRUCTURE (trig / powers /
interactions) and good constants.

`propose_models()` returns a list of candidate predictors. Each predictor
maps X (n_samples, 2) -> y_pred (n_samples,). The evolved code may call
`score_train(predict)` to compare candidates on the training data, but only
a hard-capped number of times per run (see MAX_FITS below), so a
sample-efficient strategy (a few well-reasoned structures) beats brute force.
"""

import numpy as np


def propose_models():
    """Return candidate predictors. Seed: one linear model only.

    Evolution should grow this into structured candidates, e.g.
    lambda X: a*np.sin(b*X[:, 0]) + c*X[:, 1]**2 + d*X[:, 0]*X[:, 1] + e,
    and may use score_train() (budgeted) to pick the best.
    """

    def linear(X):
        return 0.0 * X[:, 0] + 0.0 * X[:, 1]

    return [linear]


def search_model():
    """Pick the best proposed model under the training-fit-call budget."""
    candidates = propose_models()
    best_predict, best_err = None, float("inf")
    for predict in candidates:
        err = score_train(predict)  # budgeted (fixed code below)
        if err < best_err:
            best_err, best_predict = err, predict
    if best_predict is None:
        return lambda X: np.zeros(X.shape[0])
    return best_predict


# EVOLVE-BLOCK-END


# This part remains fixed (not evolved).
#
# Hard training-fit-evaluation budget. The evolvable code above may query the
# training scorer `score_train` only MAX_FITS times per run_search(); further
# calls return a large error so a brute-force "try thousands of random
# structures and keep the best on train" strategy cannot win. Enforced here,
# OUTSIDE the EVOLVE-BLOCK, so an evolved program cannot lift the budget by
# rewriting its own loop. Scoring (held-out test NMSE) is done by evaluator.py
# on data the evolved code never sees. Tune MAX_FITS to set difficulty.
MAX_FITS = 8
_OVER_BUDGET_ERR = 1e9
_fit_count = 0

# Deterministic hidden target + dataset (the evolved code only ever touches
# the TRAIN split via the budgeted scorer; evaluator.py holds out a TEST split).
_SEED = 20260517
_N = 400


def _hidden_target(X):
    x0, x1 = X[:, 0], X[:, 1]
    return 2.5 * np.sin(1.3 * x0) + 0.7 * x1**2 - 0.4 * x0 * x1 + 1.1


def _make_data():
    rng = np.random.default_rng(_SEED)
    X = rng.uniform(-3.0, 3.0, size=(_N, 2))
    y = _hidden_target(X)
    n_train = _N // 2
    return X[:n_train], y[:n_train], X[n_train:], y[n_train:]


_Xtr, _ytr, _Xte, _yte = _make_data()
_y_var_tr = float(np.var(_ytr)) or 1.0


def _nmse(predict, X, y, y_var):
    try:
        pred = np.asarray(predict(X), dtype=float).reshape(-1)
        if pred.shape[0] != y.shape[0] or not np.all(np.isfinite(pred)):
            return _OVER_BUDGET_ERR
        return float(np.mean((pred - y) ** 2) / y_var)
    except Exception:
        return _OVER_BUDGET_ERR


def score_train(predict):
    """Budgeted training-NMSE scorer: true value for the first MAX_FITS calls
    of a run, then a large error so extra trials cannot improve the result."""
    global _fit_count
    _fit_count += 1
    if _fit_count > MAX_FITS:
        return _OVER_BUDGET_ERR
    return _nmse(predict, _Xtr, _ytr, _y_var_tr)


def run_search():
    """Fresh budget per evaluation trial; return the chosen predictor."""
    global _fit_count
    _fit_count = 0
    return search_model()


if __name__ == "__main__":
    f = run_search()
    te_var = float(np.var(_yte)) or 1.0
    print(f"test NMSE = {_nmse(f, _Xte, _yte, te_var):.6f}")
