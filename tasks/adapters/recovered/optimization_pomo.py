"""CPU ReEvo POMO rollout with official weights and independent route checks."""
from pathlib import Path
import hashlib
import math
import tempfile

from optimization_original import _imports, _load


def _validate_routes(environment, reward, problem):
    """Recompute objective from the immutable input and check every visit/load."""
    import torch
    routes = environment.selected_node_list[:, 0, :].tolist()
    objectives = []
    for batch, route in enumerate(routes):
        if problem == "tsp_pomo":
            coordinates = environment.problems[batch]
            n = len(coordinates)
            if sorted(route) != list(range(n)):
                raise ValueError("POMO TSP rollout is not a permutation")
        else:
            coordinates = environment.depot_node_xy[batch]
            demands = environment.depot_node_demand[batch]
            n = len(coordinates) - 1
            if sorted(node for node in route if node != 0) != list(range(1, n + 1)):
                raise ValueError("POMO CVRP rollout misses or repeats customers")
            if route[0] != 0 or route[-1] != 0:
                raise ValueError("POMO CVRP rollout does not start/end at depot")
            load = 0.0
            for node in route:
                if node == 0:
                    load = 0.0
                else:
                    load += float(demands[node])
                    if load > 1.0 + 1e-5:
                        raise ValueError("POMO CVRP capacity exceeded")
        path = coordinates[torch.tensor(route)]
        cost = float((path - path.roll(1, dims=0)).norm(p=2, dim=1).sum())
        if not math.isclose(cost, -float(reward[batch, 0]), rel_tol=1e-5, abs_tol=1e-4):
            raise ValueError("POMO reward disagrees with independently recomputed route length")
        objectives.append(cost)
    return objectives


def evaluate(candidate_path, *, checkout, problem, max_instances=2):
    import torch
    if problem not in ("tsp_pomo", "cvrp_pomo") or not 1 <= max_instances <= 10:
        raise ValueError("Unknown POMO task or invalid training subset size")
    root = Path(checkout).resolve()
    directory = root / "problems" / problem
    prefix = "TSP" if problem == "tsp_pomo" else "CVRP"
    epoch = 3100 if problem == "tsp_pomo" else 30500
    torch.set_num_threads(1)
    torch.manual_seed(5)  # original len('train') seed
    extras = ("TSPEnv", "TSPModel", "TSProblemDef", "CVRPEnv", "CVRPModel", "CVRProblemDef")
    with _imports(root, directory, extra=extras), tempfile.TemporaryDirectory(prefix="artask-pomo-") as temp:
        candidate = _load("gpt", candidate_path)
        function = next((getattr(candidate, name) for name in ("heuristics_v2", "heuristics", "heuristics_v1")
                         if hasattr(candidate, name)), None)
        if function is None:
            raise ValueError("Candidate must export heuristics")
        calls = []

        def checked(*args):
            result = function(*args)
            if not isinstance(result, torch.Tensor) or result.shape != args[0].shape or not torch.isfinite(result).all():
                raise ValueError("POMO attention bias must be finite and match distance matrix shape")
            calls.append(1)
            return result

        candidate.heuristics = checked
        candidate.heuristics_v2 = checked
        model_module = _load(prefix + "Model", directory / (prefix + "Model.py"))
        env_module = _load(prefix + "Env", directory / (prefix + "Env.py"))
        generator = _load("gen_inst", directory / "gen_inst.py")
        datafile = Path(temp) / "train200_dataset.pt"
        generator.generate_dataset(str(datafile), 200, batch_size=10)
        dataset = torch.load(datafile, weights_only=True)
        # Selecting the first complete instances does not change their size/distribution.
        selected = dataset[:max_instances] if isinstance(dataset, torch.Tensor) else {
            key: value[:max_instances] for key, value in dataset.items()}
        digest = hashlib.sha256()
        for key, tensor in ([('coordinates', selected)] if isinstance(selected, torch.Tensor) else sorted(selected.items())):
            digest.update(key.encode()); digest.update(tensor.numpy().tobytes())
        torch.save(selected, datafile)
        params = dict(embedding_dim=128, sqrt_embedding_dim=128**0.5,
                      encoder_layer_num=6, qkv_dim=16, head_num=8,
                      logit_clipping=10, ff_hidden_dim=512, eval_type="argmax")
        model = getattr(model_module, prefix + "Model")(**params)
        checkpoint = directory / "checkpoints" / f"checkpoint-{epoch}.pt"
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(state["model_state_dict"], strict=True)
        model.eval()
        env_params = dict(problem_size=200, pomo_size=1)
        if problem == "tsp_pomo":
            env_params["test_file_path"] = str(datafile)
        environment = getattr(env_module, prefix + "Env")(**env_params)
        if problem == "cvrp_pomo":
            environment.use_saved_problems(str(datafile), torch.device("cpu"))
        with torch.no_grad():
            environment.load_problems(max_instances, aug_factor=1)
            reset_state, _, _ = environment.reset()
            model.pre_forward(reset_state)
            current, reward, done = environment.pre_step()
            steps = 0
            while not done:
                selected_nodes, _ = model(current)
                current, reward, done = environment.step(selected_nodes)
                steps += 1
                if steps > 2 * 200 + 2:
                    raise ValueError("POMO rollout exceeds a complete feasible route length")
        objectives = _validate_routes(environment, reward, problem)
        if not calls or not all(math.isfinite(score) for score in objectives):
            raise ValueError("Candidate was not exercised or route objective is nonfinite")
        return {"score": sum(objectives) / len(objectives), "validity": True,
                "instances": max_instances, "instance_size": 200,
                "candidate_calls": len(calls), "instance_objectives": objectives,
                "profile": "bounded_original_training", "device": "cpu",
                "pomo_size": 1, "augmentation_factor": 1, "random_seed": 5,
                "training_subset_tensor_sha256": digest.hexdigest(),
                "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                "validation_scope": "every customer visited once, CVRP depot/capacity checked, route length independently recomputed"}
