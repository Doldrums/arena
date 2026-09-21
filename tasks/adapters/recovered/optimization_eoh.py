"""Use EoH's released problem classes with explicit bounded CPU budgets."""
from pathlib import Path
import hashlib
import importlib.util
import math
import sys
import types

# The bridge adds this evaluator directory to sys.path.
from optimization_original import _imports, _load


def evaluate(candidate_path, *, checkout, problem, max_instances=1, iterations=2,
             seconds_per_instance=10.0):
    import numpy as np
    if max_instances < 1 or iterations < 1 or seconds_per_instance <= 0:
        raise ValueError("Smoke budgets must be positive")
    root = Path(checkout).resolve()
    directory = root / "examples" / problem
    if problem not in ("bp_online", "tsp_gls", "fssp_gls"):
        raise ValueError("Unsupported EoH problem")
    with _imports(root, directory):
        candidate = _load("gpt", candidate_path)
        # Import the released BaseProblem directly; eoh.__init__ eagerly imports
        # network clients unrelated to candidate evaluation.
        package = types.ModuleType("eoh")
        package.__path__ = [str(root / "eoh/src/eoh")]
        sys.modules["eoh"] = package
        package.BaseProblem = _load("eoh.problem", root / "eoh/src/eoh/problem.py").BaseProblem
        evaluator = _load("_recovered_eoh_prob", directory / "prob.py")
        names = {"bp_online": ("BPONLINE", "score"),
                 "tsp_gls": ("TSPGLS", "update_edge_distance"),
                 "fssp_gls": ("FSSPGLS", "get_matrix_and_jobs")}
        cls_name, fn_name = names[problem]
        function = getattr(candidate, fn_name)
        calls = []
        errors = []

        def checked(*args):
            calls.append(1)
            try:
                result = function(*args)
                if problem == "fssp_gls":
                    matrix, jobs = result
                    if np.shape(matrix) != np.shape(args[1]) or not np.isfinite(matrix).all():
                        raise ValueError("Perturbed matrix shape/values invalid")
                    if any(not isinstance(i, (int, np.integer)) or not 0 <= i < len(args[0]) for i in jobs):
                        raise ValueError("Perturbation job index invalid")
                else:
                    expected = np.shape(args[1] if problem == "bp_online" else args[0])
                    if np.shape(result) != expected or not np.isfinite(result).all():
                        raise ValueError("Heuristic output shape/values invalid")
                return result
            except Exception as exc:
                errors.append(str(exc))
                raise

        cls = getattr(evaluator, cls_name)
        if problem == "bp_online":
            runner = cls(capacity=100)
            # Recompute the lower bound for the exact selected released instances.
            for name, dataset in runner.instances.items():
                runner.instances[name] = dict(list(dataset.items())[:max_instances])
                runner.lb[name] = float(np.mean([
                    math.ceil(sum(inst["items"]) / inst["capacity"])
                    for inst in runner.instances[name].values()]))
            dataset_files = [directory / "get_instance.py"]
        elif problem == "tsp_gls":
            runner = cls(n_inst_eva=max_instances, time_limit=seconds_per_instance,
                         ite_max=iterations)
            dataset_files = [directory / "TrainingData/TSPAEL64.pkl"]
        else:
            runner = cls(n_inst_eva=max_instances, time_max=seconds_per_instance,
                         iter_max=iterations)
            dataset_files = [directory / "TrainingData" / f"{i}.txt"
                             for i in range(1, max_instances + 1)]
        value = runner.evaluate_program(Path(candidate_path).read_text(), checked)
        # Original GLS catches candidate exceptions and emits a 1e10 sentinel.
        # Surface that as an error, rather than a successful numerical score.
        if errors or not calls or value is None or not math.isfinite(value) or value >= 1e10:
            raise ValueError("EoH candidate evaluation failed: " + "; ".join(errors or ["invalid/sentinel result or callback not called"]))
        return {"score": float(value), "validity": None, "instances": max_instances,
                "candidate_calls": len(calls), "iterations": iterations,
                "seconds_per_instance": seconds_per_instance,
                "profile": "bounded_original_training",
                "dataset_origin": "released_training_data",
                "dataset_files": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in dataset_files},
                "validation_scope": "finite original solver objective; no independent solution certificate"}
