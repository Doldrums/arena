"""Bounded MCTS-AHD cost-aware BO evaluation with its released functions."""
from pathlib import Path
import hashlib
import math

from optimization_original import _imports, _load


def evaluate(candidate_path, *, checkout, max_instances=1, cost_budget=4.0, random_seed=1):
    import torch
    root = Path(checkout).resolve()
    directory = root / "problems/bo_caf"
    if max_instances < 1 or not math.isfinite(cost_budget) or cost_budget <= 0:
        raise ValueError("BO budgets must be positive")
    torch.set_num_threads(1)
    torch.manual_seed(random_seed)
    with _imports(root, directory):
        candidate = _load("gpt", candidate_path)
        function = getattr(candidate, "utility_v2", getattr(candidate, "utility", None))
        if function is None:
            raise ValueError("Candidate must export utility")
        calls = []

        def checked(*args, **kwargs):
            value = function(*args, **kwargs)
            if not isinstance(value, torch.Tensor) or not torch.isfinite(value).all():
                raise ValueError("Utility must return a finite torch tensor")
            calls.append(1)
            return value

        candidate.utility = checked
        candidate.utility_v2 = checked
        evaluator = _load("_recovered_bo_eval", directory / "eval.py")
        datafile = directory / "instance/botorch_problem_train.pkl"
        protocol = evaluator.Evaluation(str(datafile))
        scores = []
        names = []
        for instance in protocol.instance_data[:max_instances]:
            scores.append(float(protocol.EGO(cost_total=cost_budget,
                                            real_problem=instance,
                                            random_seed=random_seed)))
            names.append(type(instance).__name__)
        if not calls or not scores or not all(math.isfinite(score) for score in scores):
            raise ValueError("BO returned no finite objective or never called the candidate")
        return {"score": sum(scores) / len(scores), "validity": None,
                "instances": len(scores), "instance_names": names,
                "candidate_calls": len(calls), "instance_objectives": scores,
                "cost_budget": cost_budget, "trials_per_instance": 1,
                "random_seed": random_seed, "profile": "bounded_original_training",
                "dataset_sha256": hashlib.sha256(datafile.read_bytes()).hexdigest(),
                "validation_scope": "original EGO absolute optimality gap on released benchmark; no independent certificate"}
