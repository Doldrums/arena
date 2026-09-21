"""Hyperparameter-optimization objectives on bundled scikit-learn datasets (recreated).

* FunBO's SVM / AdaBoost tasks: the candidate is an acquisition function driving
  GP-based Bayesian optimization of a model's cross-validated error.
* LLaMEA-BO's Bayesmark suite: the candidate is a black-box optimizer class
  ``Optimizer(budget, dim)`` that optimizes the normalized hyperparameter box
  of {RandomForest, SVM, DecisionTree, MLP_SGD, AdaBoost} on {breast, digits,
  wine, iris, diabetes}; scores are the best cross-validated loss found.

The datasets ship with scikit-learn (no download); folds and model sizes are
reduced so that one evaluation takes seconds. Scores are comparable within
this suite only.
"""
from __future__ import annotations

import math

import numpy as np

from .runtime import CandidateError, require

SPACES = {
    "svm": [("C", -3, 3, "log"), ("gamma", -4, 1, "log")],
    "adaboost": [("n_estimators", 1, 100, "int"), ("learning_rate", -3, 0.5, "log")],
    "randomforest": [("n_estimators", 5, 100, "int"), ("max_depth", 1, 15, "int"), ("min_samples_split", 0.01, 0.5, "lin")],
    "decisiontree": [("max_depth", 1, 15, "int"), ("min_samples_split", 0.01, 0.5, "lin"), ("min_samples_leaf", 0.01, 0.49, "lin")],
    "mlp_sgd": [("hidden", 8, 128, "int"), ("alpha", -6, -1, "log"), ("learning_rate_init", -4, -1, "log")],
}
DATASETS = {"breast": "load_breast_cancer", "digits": "load_digits", "wine": "load_wine", "iris": "load_iris", "diabetes": "load_diabetes"}


def _decode(model, u):
    params = {}
    for (name, lo, hi, kind), v in zip(SPACES[model], u):
        x = lo + (hi - lo) * float(np.clip(v, 0, 1))
        params[name] = 10 ** x if kind == "log" else int(round(x)) if kind == "int" else x
    return params


def _estimator(model, params, regression):
    from sklearn import ensemble, neural_network, svm, tree
    if model == "svm":
        return (svm.SVR if regression else svm.SVC)(C=params["C"], gamma=params["gamma"])
    if model == "adaboost":
        cls = ensemble.AdaBoostRegressor if regression else ensemble.AdaBoostClassifier
        return cls(n_estimators=params["n_estimators"], learning_rate=params["learning_rate"], random_state=0)
    if model == "randomforest":
        cls = ensemble.RandomForestRegressor if regression else ensemble.RandomForestClassifier
        return cls(n_estimators=params["n_estimators"], max_depth=params["max_depth"], min_samples_split=params["min_samples_split"], random_state=0)
    if model == "decisiontree":
        cls = tree.DecisionTreeRegressor if regression else tree.DecisionTreeClassifier
        return cls(max_depth=params["max_depth"], min_samples_split=params["min_samples_split"], min_samples_leaf=params["min_samples_leaf"], random_state=0)
    if model == "mlp_sgd":
        cls = neural_network.MLPRegressor if regression else neural_network.MLPClassifier
        return cls(hidden_layer_sizes=(params["hidden"],), alpha=params["alpha"], learning_rate_init=params["learning_rate_init"], solver="sgd", max_iter=200, random_state=0)
    raise ValueError(model)


def make_objective(dataset, model, folds=3, max_samples=600):
    """Return (objective(u in [0,1]^d) -> CV loss, dim). Loss is 1 - accuracy or normalized MSE."""
    try:
        from sklearn import datasets as skd, model_selection, preprocessing
    except ImportError as error:  # pragma: no cover
        raise CandidateError(f"scikit-learn is required: {error}") from None
    import warnings
    data = getattr(skd, DATASETS[dataset])()
    X, y = data.data[:max_samples], data.target[:max_samples]
    X = preprocessing.StandardScaler().fit_transform(X)
    regression = dataset == "diabetes"
    dim = len(SPACES[model])
    cv = (model_selection.KFold if regression else model_selection.StratifiedKFold)(folds, shuffle=True, random_state=0)

    def objective(u):
        u = np.asarray(u, dtype=float).ravel()
        require(u.shape == (dim,), f"expected a point of dimension {dim}")
        est = _estimator(model, _decode(model, u), regression)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scores = model_selection.cross_val_score(est, X, y, cv=cv, scoring="neg_mean_squared_error" if regression else "accuracy")
        loss = -float(np.mean(scores)) / float(np.var(y)) if regression else 1 - float(np.mean(scores))
        return loss if math.isfinite(loss) else 1e6
    return objective, dim


def bo_hpo_score(acquisition, dataset, model, budget=15, n_init=4, n_candidates=500, seed=0):
    """Best CV loss found by GP-BO with the candidate acquisition (FunBO contract). Lower is better."""
    from .blackbox import gp_posterior
    objective, dim = make_objective(dataset, model)
    rng = np.random.default_rng(seed)
    X = rng.random((n_init, dim))
    y = np.array([objective(x) for x in X])
    while len(y) < budget:
        Xs = rng.random((n_candidates, dim))
        mu, sigma = gp_posterior(X, y, Xs)
        scores = np.asarray(acquisition(mu, sigma, float(y.min())), dtype=float).ravel()
        require(scores.shape == (n_candidates,) and np.all(np.isfinite(scores)), "acquisition must return one finite score per candidate")
        x = Xs[int(np.argmax(scores))]
        X = np.vstack([X, x])
        y = np.append(y, objective(x))
    return float(y.min())


def griewank_objective(dim):
    def objective(u):
        x = (np.asarray(u, dtype=float).ravel() - 0.5) * 20
        require(x.shape == (dim,), f"expected a point of dimension {dim}")
        return float(1 + np.sum(x ** 2) / 4000 - np.prod(np.cos(x / np.sqrt(np.arange(1, dim + 1)))))
    return objective


def ktablet_objective(dim):
    def objective(u):
        x = (np.asarray(u, dtype=float).ravel() - 0.5) * 10
        require(x.shape == (dim,), f"expected a point of dimension {dim}")
        k = max(1, dim // 4)
        return float(np.sum(x[:k] ** 2) + np.sum((100 * x[k:]) ** 2))
    return objective


def rosenbrock_objective(dim):
    def objective(u):
        x = (np.asarray(u, dtype=float).ravel() - 0.5) * 4
        require(x.shape == (dim,), f"expected a point of dimension {dim}")
        return float(np.sum(100 * (x[1:] - x[:-1] ** 2) ** 2 + (1 - x[:-1]) ** 2)) if dim > 1 else float((1 - x[0]) ** 2)
    return objective


SYNTHETIC_OBJECTIVES = {"griewank": griewank_objective, "ktablet": ktablet_objective, "rosenbrock": rosenbrock_objective}


def bayesmark_score(optimizer_class, dataset, model, budget=15, seed=0):
    """Best loss found by ``Optimizer(budget, dim)(objective)`` on the model's normalized hyperparameter box. Lower is better.

    Bayesmark's synthetic objectives (griewank, ktablet, rosenbrock) are evaluated over the same box as the model's hyperparameters.
    """
    if dataset in SYNTHETIC_OBJECTIVES:
        dim = len(SPACES[model])
        objective = SYNTHETIC_OBJECTIVES[dataset](dim)
    else:
        objective, dim = make_objective(dataset, model)
    history = []

    def budgeted(u):
        require(len(history) < budget, f"evaluation budget of {budget} exhausted")
        value = objective(np.clip(np.asarray(u, dtype=float).ravel(), 0, 1))
        history.append(value)
        return value

    np.random.seed(seed)
    try:
        optimizer_class(budget, dim)(budgeted)
    except CandidateError:
        raise
    except Exception as error:  # noqa: BLE001
        if not history:
            raise CandidateError(f"optimizer raised before evaluating anything: {type(error).__name__}: {error}") from None
    require(history, "the optimizer did not evaluate the objective")
    return float(min(history))
