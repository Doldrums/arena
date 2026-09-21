"""Pinned IOH objectives and the released LLaMEA-BO scoring implementation.

Only the original ConvergenceCurveAnalyzer class is compiled from the pinned
checkout, avoiding provider/model imports in llamevol.__init__.  The bounded
profile evaluates one held-out instance, rather than the paper's repeated suite.
"""
import ast
import hashlib
import importlib.util
from importlib.metadata import version
from pathlib import Path


def _load_candidate(path):
    spec = importlib.util.spec_from_file_location("recovered_bo_candidate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _original_scorer(checkout):
    import numpy as np
    path = Path(checkout) / "llamevol/evaluator/evaluator_result.py"
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.ClassDef)
             and n.name == "ConvergenceCurveAnalyzer"]
    if len(nodes) != 1:
        raise ValueError("Pinned source lacks the expected original scoring class")

    class NumpyCompatibility:
        # NumPy 2.4 removed the alias; trapezoid implements the same operation.
        def __getattr__(self, name):
            return np.trapezoid if name == "trapz" else getattr(np, name)

    namespace = {"np": NumpyCompatibility()}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["ConvergenceCurveAnalyzer"], hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(candidate_path, *, checkout, problem_id, dimension=5, budget=100,
             instance=4, random_seed=0):
    import numpy as np
    import ioh
    if version("ioh") != "0.3.18":
        raise ValueError("This protocol requires pinned ioh==0.3.18")
    if (not isinstance(problem_id, int) or not 1 <= problem_id <= 24
            or dimension < 2 or budget < 2 or instance < 1):
        raise ValueError("Invalid BBOB task parameters")
    np.random.seed(random_seed)
    candidate = _load_candidate(candidate_path)
    problem = ioh.get_problem(problem_id, instance=instance, dimension=dimension)
    values, points = [], []
    bounds = np.vstack([problem.bounds.lb, problem.bounds.ub])

    class Objective:
        def __init__(self):
            self.bounds = bounds.copy()
            self.dim = dimension
            self.budget = budget
            self.random_seed = random_seed

        def __call__(self, x):
            batch = np.asarray(x, dtype=float)
            scalar = batch.ndim == 1
            if scalar:
                batch = batch[None, :]
            if batch.ndim != 2 or batch.shape[1] != dimension or not len(batch):
                raise ValueError("Objective requires a vector or a batch of vectors")
            if (not np.isfinite(batch).all() or (batch < bounds[0]).any()
                    or (batch > bounds[1]).any()):
                raise ValueError("Candidate evaluated a nonfinite or out-of-domain point")
            if len(values) + len(batch) > budget:
                raise ValueError("Candidate exceeded the declared objective budget")
            result = []
            for point in batch:
                value = float(problem(point))
                if not np.isfinite(value):
                    raise ValueError("Nonfinite objective evaluation")
                points.append(point.copy())
                values.append(value)
                result.append(value)
            return result[0] if scalar else np.asarray(result)

    result = candidate.Optimizer(dim=dimension, budget=budget)(func=Objective())
    if len(values) != budget:
        raise ValueError(f"Candidate consumed {len(values)} of the required {budget} evaluations")
    if not isinstance(result, (tuple, list)) or len(result) != 2:
        raise ValueError("Optimizer must return (best_y, best_x)")
    best_y, best_x = float(result[0]), np.asarray(result[1], dtype=float)
    minimum = min(values)
    if (best_x.shape != (dimension,) or not np.isfinite(best_y)
            or not np.isclose(best_y, minimum, rtol=1e-10, atol=1e-10)
            or not any(np.array_equal(best_x, x) and np.isclose(y, best_y)
                       for x, y in zip(points, values))):
        raise ValueError("Reported solution does not match the observed best objective")
    scorer, source_hash = _original_scorer(checkout)
    upper = 1e4 if dimension <= 5 else 1e9
    score = float(scorer(max_y=upper, min_y=1e-8, log_scale=True,
                         shift_value=problem.optimum.y).calculate_aoc(np.asarray(values)))
    if not np.isfinite(score) or not -1e-12 <= score <= 1 + 1e-12:
        raise ValueError("Invalid original AOCC score")
    return {"score": score, "normalized_log_gap_AOCC": score, "validity": True, "metric": "normalized_log_gap_AOCC",
            "direction": "maximize", "problem_id": problem_id, "dimension": dimension,
            "instance": instance, "budget": budget, "candidate_calls": len(values),
            "best_objective": minimum, "optimum": float(problem.optimum.y),
            "final_gap": minimum - float(problem.optimum.y),
            "objective_package": "ioh==0.3.18", "random_seed": random_seed,
            "objective_trace_sha256": hashlib.sha256(np.asarray(values, dtype="<f8").tobytes()).hexdigest(),
            "scoring_source_sha256": source_hash,
            "profile": "bounded_original_objective_and_metric",
            "validation_scope": "finite in-domain budget-complete trace and observed returned optimum; no paper reproduction"}
