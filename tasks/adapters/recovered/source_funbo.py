"""Paper-guided reconstruction of FunBO's nine OOD acquisition tasks.

Appendix C.1 fixes the domains, Sobol-grid sizes, GP parameters and 30 trials.
The original FunBO implementation/grid seed was not published in the inspected
sources. This is a new deterministic SciPy implementation, not that evaluator.
MetaBO (cited by FunBO) supplies three objective definitions; its normalizations
are explicitly inverted. Remaining standard definitions are documented in
docs/RECOVERY_SOURCES.md. No MetaBO training or pretrained policy is invoked.
"""
import hashlib
import importlib.util
import math
from pathlib import Path


# Appendix C.1 Table 1, including the paper's unusual Beale domain [-4, 5]^2.
SETTINGS = {
    "sphere": (1, [(-5, 5)], 1000, 18.46, 924202.43, 1e-5),
    "styblinski-tang": (1, [(-5, 5)], 1000, 7.34, 119522207.86, 1e-5),
    "weierstrass": (1, [(-0.5, 0.5)], 1000, 0.01, 0.39, 1e-5),
    "beale": (2, [(-4, 5)] * 2, 10000, 0.46, 546837.32, 1e-5),
    "branin": (2, [(-5, 10), (0, 15)], 10000, 4.65, 155233.52, 1e-5),
    "michalewicz": (2, [(0, math.pi)] * 2, 10000, 0.22, 0.10, 1e-5),
    "goldstein-price": (2, [(-2, 2)] * 2, 10000, 0.27, 117903.96, 1e-5),
    "hartmann-3": (3, [(0, 1)] * 3, 1728, [0.716, 0.298, 0.186], 0.83, 1.688e-11),
    "hartmann-6": (6, [(0, 1)] * 6, 729, 1.0, 1.0, 1e-5),
}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def objective_values(problem, points, metabo):
    import numpy as np
    x = np.asarray(points)
    if problem == "sphere":
        return np.sum(x * x, axis=1)
    if problem == "styblinski-tang":
        return np.sum(x ** 4 - 16 * x ** 2 + 5 * x, axis=1) / 2
    if problem == "weierstrass":
        # Standard finite Weierstrass benchmark convention, not specified by
        # FunBO: a=.5, b=3, k_max=20; this assumption is part of the manifest.
        k = np.arange(21)
        terms = 0.5 ** k * np.cos(2 * np.pi * (3.0 ** k) * (x[:, :, None] + 0.5))
        origin = np.sum(0.5 ** k * np.cos(np.pi * (3.0 ** k)))
        return terms.sum(axis=(1, 2)) - x.shape[1] * origin
    if problem == "beale":
        a, b = x.T
        return (1.5 - a + a * b) ** 2 + (2.25 - a + a * b ** 2) ** 2 + (2.625 - a + a * b ** 3) ** 2
    if problem == "branin":
        scaled = (x - np.array([-5, 0])) / 15
        return 54.44 - 51.44 * metabo.bra(scaled).ravel()
    if problem == "michalewicz":
        return -np.sum(np.sin(x) * np.sin(np.arange(1, x.shape[1] + 1) * x ** 2 / np.pi) ** 20, axis=1)
    if problem == "goldstein-price":
        return np.exp(8.693 - 2.427 * metabo.gprice((x + 2) / 4).ravel())
    if problem == "hartmann-3":
        return -0.93 - 0.95 * metabo.hm3(x).ravel()
    if problem == "hartmann-6":
        alpha = np.array([1, 1.2, 3, 3.2])
        a = np.array([[10, 3, 17, 3.5, 1.7, 8], [0.05, 10, 17, 0.1, 8, 14],
                      [3, 3.5, 1.7, 10, 17, 8], [17, 8, 0.05, 10, 0.1, 14]])
        p = 1e-4 * np.array([[1312, 1696, 5569, 124, 8283, 5886],
                             [2329, 4135, 8307, 3736, 1004, 9991],
                             [2348, 1451, 3522, 2883, 3047, 6650],
                             [4047, 8828, 8732, 5743, 1091, 381]])
        return -np.sum(alpha * np.exp(-np.sum(a * (x[:, None, :] - p) ** 2, axis=-1)), axis=1)
    raise ValueError("Unknown FunBO objective")


def evaluate(candidate_path, *, checkout, problem, trials=30, random_seed=0):
    import numpy as np
    from scipy.linalg import cho_factor, cho_solve, solve_triangular
    from scipy.stats import qmc
    if problem not in SETTINGS or not isinstance(trials, int) or not 1 <= trials <= 30:
        raise ValueError("Unknown task or trial budget outside 1..30")
    dim, bounds, count, length, variance, noise = SETTINGS[problem]
    source = Path(checkout) / "metabo/environment/objectives.py"
    metabo = _load("recovered_metabo_objectives", source)
    candidate = _load("recovered_funbo_candidate", candidate_path)
    # The original grid seed is unavailable. Use a documented scrambled Sobol
    # sequence, taking exactly Table 1's number of points from a dyadic draw.
    unit = qmc.Sobol(d=dim, scramble=True, seed=random_seed).random_base2(math.ceil(math.log2(count)))[:count]
    bounds = np.asarray(bounds)
    grid = qmc.scale(unit, bounds[:, 0], bounds[:, 1])
    objective = np.asarray(objective_values(problem, grid, metabo), dtype=float)
    if objective.shape != (count,) or not np.isfinite(objective).all():
        raise ValueError("Invalid benchmark objective grid")
    indices = [int(np.argmax(objective))]
    jitters = []
    for _ in range(trials):
        train = grid[indices]
        def kernel(a, b):
            return variance * np.exp(-0.5 * np.sum(((a[:, None, :] - b[None, :, :]) / length) ** 2, axis=-1))
        covariance = kernel(train, train)
        jitter = 0.0
        for attempt in range(6):
            try:
                factor = cho_factor(covariance + np.eye(len(train)) * (noise + jitter), lower=True)
                break
            except np.linalg.LinAlgError:
                jitter = np.finfo(float).eps * variance * (10 ** attempt)
        else:
            raise ValueError("GP covariance remains singular after bounded numerical jitter")
        jitters.append(float(jitter))
        cross = kernel(train, grid)
        mean = cross.T @ cho_solve(factor, objective[indices])
        projected = solve_triangular(factor[0], cross, lower=True)
        # GPy.predict includes Gaussian likelihood variance by default.
        predictive_var = np.maximum(variance - np.sum(projected ** 2, axis=0), 0) + noise
        selected = candidate.acquisition_function(mean.reshape(-1, 1).copy(),
                        predictive_var.reshape(-1, 1).copy(), float(min(objective[indices])))
        if (isinstance(selected, (bool, np.bool_)) or not isinstance(selected, (int, np.integer))
                or not 0 <= int(selected) < count):
            raise ValueError("Acquisition function must return an integer grid index")
        indices.append(int(selected))
    best, optimum, initial = float(min(objective[indices])), float(min(objective)), float(objective[indices[0]])
    regret = (best - optimum) / (initial - optimum) if initial > optimum else 0.0
    hit = next((i for i, j in enumerate(indices) if objective[j] == optimum), None)
    return {"score": regret, "normalized_grid_simple_regret": regret, "validity": True, "direction": "minimize",
            "metric": "normalized_grid_simple_regret", "raw_simple_regret": best - optimum,
            "best_objective": best, "grid_optimum": optimum,
            "trials_to_grid_optimum": hit, "candidate_calls": trials,
            "initial_evaluations": 1, "trials": trials, "grid_size": count,
            "dimension": dim, "random_seed": random_seed, "numerical_jitter": jitters,
            "grid_sha256": hashlib.sha256(grid.astype("<f8").tobytes()).hexdigest(),
            "objective_grid_sha256": hashlib.sha256(objective.astype("<f8").tobytes()).hexdigest(),
            "objective_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "selected_indices": indices, "profile": "paper_guided_reconstructed_ood",
            "validation_scope": "finite original-form objective values and valid acquisition indices; no paper reproduction"}
