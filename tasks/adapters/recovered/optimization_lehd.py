"""ReEvo's exact LEHD tester on the first released 200-node instances, CPU."""
from pathlib import Path
import hashlib
import math

from optimization_original import _imports, _load


def evaluate(candidate_path, *, checkout, problem, max_instances=1):
    import torch
    if problem not in ("tsp_lehd", "cvrp_lehd") or not 1 <= max_instances <= 10:
        raise ValueError("Unknown LEHD task or invalid bounded subset")
    root = Path(checkout).resolve()
    directory = root / "problems" / problem
    prefix = "TSP" if problem == "tsp_lehd" else "VRP"
    epoch = 150 if problem == "tsp_lehd" else 40
    filename = "test_TSP200_n128.txt" if problem == "tsp_lehd" else "vrp200_test_lkh.txt"
    torch.set_num_threads(1)
    torch.manual_seed(1234)
    extras = ("TSPEnv", "TSPModel", "TSPTester", "VRPEnv", "VRPModel", "VRPTester")
    with _imports(root, directory, extra=extras):
        candidate = _load("gpt", candidate_path)
        function = next((getattr(candidate, name) for name in ("heuristics_v2", "heuristics", "heuristics_v1")
                         if hasattr(candidate, name)), None)
        if function is None:
            raise ValueError("Candidate must export heuristics")
        calls = []

        def checked(*args):
            value = function(*args)
            if not isinstance(value, torch.Tensor) or value.shape != args[0].shape or not torch.isfinite(value).all():
                raise ValueError("LEHD attention bias must be finite and match distance matrix")
            calls.append(1)
            return value

        candidate.heuristics = checked
        candidate.heuristics_v2 = checked
        module = _load(prefix + "Tester", directory / (prefix + "Tester.py"))
        datafile = directory / "data" / filename
        checkpoint = directory / "checkpoints" / f"checkpoint-{epoch}.pt"
        tester = getattr(module, prefix + "Tester")(
            env_params={"mode": "test", "data_path": str(datafile), "sub_path": False, "RRC_budget": 0},
            model_params={"mode": "test", "embedding_dim": 128, "sqrt_embedding_dim": 128**0.5,
                          "decoder_layer_num": 6, "qkv_dim": 16, "head_num": 8, "ff_hidden_dim": 512},
            tester_params={"use_cuda": False, "cuda_device_num": 0,
                           "test_episodes": max_instances, "test_batch_size": max_instances,
                           "test_start_idx": 0,
                           "model_load": {"path": str(checkpoint.parent), "epoch": epoch}})
        reference, score, gap = tester.run()
        if not calls or not all(math.isfinite(value) for value in (reference, score, gap)):
            raise ValueError("LEHD did not exercise the candidate or returned a nonfinite metric")
        return {"score": float(score), "validity": None, "optimality_gap_percent": float(gap),
                "reference_mean_route_length": float(reference), "instances": max_instances,
                "instance_size": 200, "candidate_calls": len(calls), "RRC_budget": 0,
                "profile": "bounded_original_training_partition", "random_seed": 1234,
                "device": "cpu", "dataset_sha256": hashlib.sha256(datafile.read_bytes()).hexdigest(),
                "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                "validation_scope": "finite original mean route length; no independent route certificate"}
