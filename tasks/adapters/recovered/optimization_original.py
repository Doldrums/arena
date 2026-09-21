"""Bounded direct evaluation through pinned EoH/ReEvo-family CPU protocols.

The upstream solver and official training generator remain authoritative. This
adapter removes the model/search driver, supplies the candidate as ``gpt``, and
limits instances/search iterations explicitly. See docs/RECOVERY_OPTIMIZATION.md.
"""
from contextlib import contextmanager
from pathlib import Path
import ast
import functools
import hashlib
import importlib.util
import inspect
import math
import pickle
import random
import sys
import tempfile
import types


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def _imports(root, problem, extra=()):
    """Keep bare upstream import names isolated between evaluations."""
    saved_path = sys.path[:]
    names = ("gpt", "aco", "gls", "gen_inst", "get_instance", "utils", "eoh") + tuple(extra)
    saved = {k: v for k, v in sys.modules.items()
             if any(k == n or k.startswith(n + ".") for n in names)}
    for key in saved:
        del sys.modules[key]
    sys.path[:0] = [str(problem), str(root), str(root / "eoh/src")]
    try:
        yield
    finally:
        sys.path[:] = saved_path
        for key in list(sys.modules):
            if any(key == n or key.startswith(n + ".") for n in names):
                del sys.modules[key]
        sys.modules.update(saved)


def _candidate(filename, black_box=False):
    """Load code and reject nonfinite heuristic outputs before solver clipping."""
    import numpy as np
    module = _load("gpt", filename)
    calls = []
    for base in ("heuristics", "select_next_node", "select_next_item", "priority"):
        found = next((getattr(module, n) for n in (base + "_v2", base,
                      base + "_v1", base + "_v3") if hasattr(module, n)), None)
        if found is None:
            continue

        def make_checked(function, name):
            @functools.wraps(function)
            def checked(*args, **kwargs):
                value = function(*args, **kwargs)
                array = np.asarray(value)
                if array.size == 0 or not np.isfinite(array).all():
                    raise ValueError(f"{name} returned empty/nonfinite output")
                if name.startswith("select_next") and (array.shape != () or
                        not np.issubdtype(array.dtype, np.integer)):
                    raise ValueError(f"{name} must return an integer index")
                if name == "heuristics":
                    expected = np.shape(args[0])
                    if black_box and len(args) == 1 and np.shape(args[0])[-1:] == (1,):
                        expected = (len(args[0]),)
                    if len(args) == 2 and np.ndim(args[1]) == 2:
                        expected = (len(args[0]),)  # multidimensional knapsack
                    elif len(args) == 3 and np.ndim(args[1]) == 2:
                        expected = np.shape(args[1])  # orienteering
                    elif len(args) == 2 and np.ndim(args[1]) == 0:
                        expected = (len(args[0]), len(args[0]))  # offline BPP
                    if array.shape != expected:
                        raise ValueError(f"{name} shape {array.shape}, expected {expected}")
                calls.append(name)
                return value
            checked.__signature__ = inspect.signature(function)
            return checked

        checked = make_checked(found, base)
        for name in (base, base + "_v1", base + "_v2", base + "_v3"):
            setattr(module, name, checked)
    return module, calls


def _selector_only(root):
    """Load the exact upstream selector without importing unused LLM clients."""
    source = root / "utils/utils.py"
    tree = ast.parse(source.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "get_heuristic_name")
    package = types.ModuleType("utils")
    package.__path__ = [str(root / "utils")]
    module = types.ModuleType("utils.utils")
    module.__file__ = str(source)
    module.inspect = inspect
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), module.__dict__)
    sys.modules["utils"] = package
    sys.modules["utils.utils"] = module


def _training_dataset(generator, problem, scratch, kind, size):
    """Use released training data, otherwise run the unmodified generator."""
    suffix = ".npz" if kind in ("mkp_aco", "op_aco", "bpp_offline_aco") else ".npy"
    filename = "weibull_5k_train.pickle" if kind == "bpp_online" else f"train{size}_dataset{suffix}"
    released = problem / "dataset" / filename
    if released.is_file():
        return released, "released_training_data"
    # __file__ relocation only changes output destination, not generator code.
    # No generated validation/test artifacts are left in the pinned checkout.
    original_file = generator.__file__
    generator.__file__ = str(scratch / "gen_inst.py")
    try:
        generator.generate_datasets()
    finally:
        generator.__file__ = original_file
    return scratch / "dataset" / filename, "official_generator_training_data"


def evaluate(candidate_path, *, checkout, problem, max_instances=2,
             iterations=5, ants=10, random_seed=1234, black_box=False,
             profile="bounded_original_training"):
    import numpy as np
    # np.float_ was removed in NumPy 2; upstream uses it only for annotations.
    if not hasattr(np, "float_"):
        np.float_ = np.float64
    root = Path(checkout).resolve()
    directory = root / "problems" / problem
    if not directory.is_dir() or not directory.is_relative_to(root):
        raise ValueError("Unknown contained upstream problem")
    if max_instances < 1 or iterations < 1 or ants < 1:
        raise ValueError("Smoke budgets must be positive")
    np.random.seed(random_seed)
    random.seed(random_seed)
    try:
        import torch
        torch.manual_seed(random_seed)
        torch.set_num_threads(1)
    except ImportError:
        pass
    with _imports(root, directory), tempfile.TemporaryDirectory(prefix="artask-optimization-") as temp:
        candidate, calls = _candidate(candidate_path, black_box=black_box)
        if (root / "utils/utils.py").is_file():
            _selector_only(root)
        evaluator_file = "eval_black_box.py" if black_box else "eval.py"
        evaluator = _load("_recovered_optimization_eval", directory / evaluator_file)
        evaluator.N_ITERATIONS = iterations
        evaluator.N_ANTS = ants
        evaluator.iter_limit = iterations
        # Keep the original 30 perturbation moves per GLS iteration.
        validity = None
        if problem == "asp_constructive":
            scores = [float(evaluator.evaluate(15, 10))]
            data_hash = None
            data_origin = "official_training_parameters_n15_w10"
            size = 15
        else:
            generator = sys.modules.get("gen_inst") or _load("gen_inst", directory / "gen_inst.py")
            size = {"tsp_gls": 200, "mkp_aco": 100, "bpp_offline_aco": 500,
                    "kp_constructive": 100, "bpp_online": 5000}.get(problem, 50)
            datafile, data_origin = _training_dataset(generator, directory, Path(temp), problem, size)
            data_hash = hashlib.sha256(datafile.read_bytes()).hexdigest()
            scores = []
            if problem == "bpp_online":
                with datafile.open("rb") as handle:
                    dataset = pickle.load(handle)
                used = []
                bounds = []
                for name, inst in dataset.items():
                    if name == "l1_bound":
                        continue
                    items = np.array(inst["items"], dtype=float)
                    bins = np.full(inst["num_items"], inst["capacity"], dtype=float)
                    packing, capacities = evaluator.online_binpack(items, bins)
                    if not evaluator.is_valid_packing(packing, list(items), inst["capacity"]):
                        raise ValueError("Official packing feasibility check failed")
                    used.append(int(np.count_nonzero(capacities != inst["capacity"])))
                    bounds.append(math.ceil(float(items.sum()) / inst["capacity"]))
                    if len(used) >= max_instances:
                        break
                scores = [100 * (float(np.mean(used)) - float(np.mean(bounds))) / float(np.mean(bounds))]
                count = len(used)
                validity = True
            elif problem in ("tsp_gls", "op_aco", "bpp_offline_aco"):
                for inst in generator.load_dataset(str(datafile))[:max_instances]:
                    score = evaluator.solve(inst, mode="aco") if problem == "bpp_offline_aco" else evaluator.solve(inst)
                    scores.append(float(score))
            else:
                dataset = np.load(datafile)
                if problem == "mkp_aco":
                    for prize, weight in zip(dataset["prizes"][:max_instances], dataset["weights"][:max_instances]):
                        scores.append(float(evaluator.solve(prize, weight)))
                else:
                    for inst in dataset[:max_instances]:
                        if problem == "cvrp_aco":
                            score = evaluator.solve(inst[:, 1:], inst[:, 0])
                        elif problem == "tsp_constructive":
                            score = evaluator.eval_heuristic(inst)
                            validity = True  # upstream explicitly rejects revisited/missing nodes
                        elif problem == "kp_constructive":
                            # Official capacity and loop retained; reject negative indices
                            # before NumPy could interpret them as legal reverse indexing.
                            original_select = evaluator.select_next_item
                            def checked_select(**kw):
                                index = original_select(**kw)
                                if not 0 <= index < len(kw["weights"]):
                                    raise ValueError("Knapsack item index out of range")
                                return index
                            evaluator.select_next_item = checked_select
                            score = evaluator.eval_heuristic(inst, 25)
                            evaluator.select_next_item = original_select
                        else:
                            score = evaluator.solve(inst)
                        scores.append(float(score))
            if problem != "bpp_online":
                count = len(scores)
        if problem == "asp_constructive":
            count = 1
        if not calls or not scores or not all(math.isfinite(x) for x in scores):
            raise ValueError("Candidate was not evaluated or produced a nonfinite objective")
        return {"score": float(np.mean(scores)), "validity": validity,
                "instances": count, "instance_size": size,
                "candidate_calls": len(calls), "instance_objectives": scores,
                "profile": profile, "iterations": iterations, "ants": ants,
                "black_box": black_box,
                "random_seed": random_seed, "dataset_origin": data_origin,
                "dataset_sha256": data_hash,
                "validation_scope": "official feasible construction checks" if validity else
                    "finite original solver objective; no independent solution certificate"}
