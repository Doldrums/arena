"""ReEvo's circuit simulator/GA with the published DevFormer benchmark data.

The old split probe/keepout files are reconstructed in memory from the original
DevFormer dataset feature column, not synthesized. Exact equality to ReEvo's
unreleased split files cannot be established; this distinction is reported.
"""
from pathlib import Path
import hashlib
import math
import pickle
import random

from optimization_original import _imports, _load


def evaluate(candidate_path, *, checkout, max_instances=1, iterations=1,
             population_size=20, random_seed=5678):
    import numpy as np
    if not 1 <= max_instances <= 100 or iterations < 1 or population_size < 10:
        raise ValueError("DPP smoke budgets are outside valid ranges")
    root = Path(checkout).resolve()
    directory = root / "problems/dpp_ga"
    np.random.seed(random_seed)
    random.seed(str(random_seed))
    with _imports(root, directory, extra=("reward_functions", "decap_gen")):
        candidate = _load("gpt", candidate_path)
        function = next((getattr(candidate, name) for name in ("crossover_v2", "crossover", "crossover_v1")
                         if hasattr(candidate, name)), None)
        if function is None:
            raise ValueError("Candidate must export crossover")
        calls = []

        def checked(parents, n_pop):
            result = np.asarray(function(parents, n_pop))
            if result.shape != (n_pop, 20) or not np.issubdtype(result.dtype, np.integer):
                raise ValueError("Crossover must return an integer (n_pop, 20) placement array")
            if (result < 0).any() or (result >= 100).any():
                raise ValueError("Crossover placement is outside the 10x10 circuit")
            calls.append(1)
            return result

        candidate.crossover = checked
        candidate.crossover_v2 = checked
        evaluator = _load("_recovered_dpp_eval", directory / "eval.py")
        datafile = directory / "test_problems/devformer_test_data.pkl"
        with datafile.open("rb") as stream:
            dataset = np.asarray(pickle.load(stream))
        if dataset.shape != (100, 100, 3) or not np.isin(dataset[:, :, 2], [0, 1, 2]).all():
            raise ValueError("Unexpected official DevFormer benchmark representation")
        probes, keepouts = [], []
        for row in dataset[:max_instances]:
            probe = np.flatnonzero(row[:, 2] == 2)
            if len(probe) != 1:
                raise ValueError("Expected exactly one probe per circuit")
            probes.append(int(probe[0]))
            keepouts.append(np.flatnonzero(row[:, 2] == 1))
        evaluator.test_probe = np.array(probes)
        evaluator.test_prohibit = keepouts
        evaluator.keepout_num = np.array([len(k) for k in keepouts])
        evaluator.n = evaluator.m = 10
        reward_model = evaluator.RewardModel(str(directory), n=10, m=10,
                                             model_number=5, freq_pts=201)
        original_evaluate = evaluator.eval_population
        checked_populations = []

        def feasible_population(population, probe, reward):
            instance_index = len(checked_populations) // (iterations + 1)
            if instance_index >= len(probes) or probes[instance_index] != probe:
                raise ValueError("Unexpected GA population evaluation order")
            evaluator.check_feasibility(population, probe, keepouts[instance_index])
            if (population < 0).any() or (population >= 100).any():
                raise ValueError("Circuit placement index out of bounds")
            checked_populations.append(1)
            return original_evaluate(population, probe, reward)

        # The original GA leaves this feasibility call commented out. Enable it
        # before physical simulation without changing the objective/repair rule.
        evaluator.eval_population = feasible_population
        score = float(evaluator.run_ga(population_size, iterations, max_instances,
                                       0.2, 20, reward_model))
        if not calls or not checked_populations or not math.isfinite(score):
            raise ValueError("DPP candidate not exercised or objective nonfinite")
        return {"score": score, "validity": True, "instances": max_instances,
                "candidate_calls": len(calls), "checked_populations": len(checked_populations),
                "population_size": population_size, "iterations": iterations,
                "decap_count": 20, "circuit_shape": [10, 10], "frequency_points": 201,
                "reward_model": 5, "random_seed": random_seed,
                "profile": "bounded_original_solver_reconstructed_dataset_transport",
                "dataset_sha256": hashlib.sha256(datafile.read_bytes()).hexdigest(),
                "dataset_limitation": "Official DevFormer test100; identity with missing ReEvo split files is unverified",
                "validation_scope": "unique feasible non-probe/non-keepout placements; objective computed by original physical simulator"}
