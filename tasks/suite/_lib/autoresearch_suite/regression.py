"""Symbolic-regression families.

* LLM-SR benchmark datasets (oscillation 1/2, E. coli growth, stress-strain)
  embedded from the MIT-licensed CoEvo release under ``data/llmsr/``; the
  candidate is ``equation(*inputs, params) -> prediction`` with ten free
  parameters fitted by BFGS on the training split, exactly as the LLM-SR /
  CoEvo in-loop evaluator does. The reported score is the normalized MSE on the
  in-distribution test split (the papers' headline metric); the OOD split is
  also reported.
* Feynman-style and univariate targets (LaSR, LLM-LEx): synthetic data from
  known closed-form equations, same ``equation`` contract, NMSE on a held-out
  sample. Recreated protocols with locally generated data.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

from .runtime import CandidateError, require

DATA = Path(__file__).with_name("data")

LLMSR = {
    "oscillation_1": {"inputs": ["x", "v"], "target": "a", "columns": ["x", "v", "a"], "description": "acceleration of a damped nonlinear oscillator with driving force from position and velocity"},
    "oscillation_2": {"inputs": ["t", "x", "v"], "target": "a", "columns": ["t", "x", "v", "a"], "description": "acceleration of a damped nonlinear oscillator with time-dependent driving force"},
    "bactgrow": {"inputs": ["b", "s", "temp", "pH"], "target": "db", "columns": ["b", "s", "temp", "pH", "db"], "description": "E. coli growth rate from population density, substrate, temperature and pH"},
    "stress_strain": {"inputs": ["strain", "temp"], "target": "stress", "columns": ["strain", "temp", "stress"], "description": "stress of an aluminium rod from strain and temperature"},
}


def load_llmsr(name, split="train"):
    spec = LLMSR[name]
    path = DATA / "llmsr" / name / f"{split}.csv"
    rows = list(csv.reader(path.open()))
    header, body = rows[0], rows[1:]
    arr = np.array([[float(v) for v in r] for r in body])
    columns = spec["columns"]
    require(len(header) == len(columns), f"unexpected columns in {path.name}")
    inputs = [arr[:, i] for i in range(len(spec["inputs"]))]
    target = arr[:, len(spec["inputs"])]
    return inputs, target


def _fit(equation, inputs, target, n_params=10):
    from scipy.optimize import minimize

    def loss(params):
        pred = np.asarray(equation(*inputs, params), dtype=float)
        if pred.shape != target.shape:
            return 1e30
        value = float(np.mean((pred - target) ** 2))
        return value if math.isfinite(value) else 1e30

    result = minimize(loss, np.ones(n_params), method="BFGS")
    return result.x, float(result.fun)


def _nmse(equation, params, inputs, target):
    pred = np.asarray(equation(*inputs, params), dtype=float)
    require(pred.shape == target.shape and np.all(np.isfinite(pred)), "equation must return a finite prediction per sample")
    return float(np.mean((pred - target) ** 2) / (np.var(target) + 1e-12))


def llmsr_score(equation, name):
    """Fit on train, report NMSE on test_id (score) and test_ood. Lower is better."""
    x_train, y_train = load_llmsr(name, "train")
    try:
        params, train_mse = _fit(equation, x_train, y_train)
    except CandidateError:
        raise
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"equation failed during fitting: {type(error).__name__}: {error}") from None
    require(math.isfinite(train_mse) and train_mse < 1e29, "fitting produced a non-finite residual")
    x_id, y_id = load_llmsr(name, "test_id")
    x_ood, y_ood = load_llmsr(name, "test_ood")
    return {"score": _nmse(equation, params, x_id, y_id), "nmse_test_ood": _nmse(equation, params, x_ood, y_ood), "train_mse": train_mse}


# --- synthetic targets ------------------------------------------------------

FEYNMAN = {
    "I.6.2a": {"inputs": ["theta"], "ranges": [(1, 3)], "f": lambda th: np.exp(-th ** 2 / 2) / np.sqrt(2 * np.pi), "formula": "exp(-theta^2/2)/sqrt(2 pi)"},
    "I.9.18": {"inputs": ["m1", "m2", "r"], "ranges": [(1, 2), (1, 2), (1, 2)], "f": lambda m1, m2, r: 6.674e-11 * m1 * m2 / r ** 2, "formula": "G m1 m2 / r^2"},
    "I.12.1": {"inputs": ["mu", "Nn"], "ranges": [(1, 5), (1, 5)], "f": lambda mu, Nn: mu * Nn, "formula": "mu N"},
    "I.14.3": {"inputs": ["m", "g", "z"], "ranges": [(1, 5), (1, 5), (1, 5)], "f": lambda m, g, z: m * g * z, "formula": "m g z"},
    "I.25.13": {"inputs": ["q", "C"], "ranges": [(1, 5), (1, 5)], "f": lambda q, C: q / C, "formula": "q / C"},
    "I.29.4": {"inputs": ["omega", "c"], "ranges": [(1, 10), (1, 10)], "f": lambda w, c: w / c, "formula": "omega / c"},
    "I.34.27": {"inputs": ["omega"], "ranges": [(1, 5)], "f": lambda w: 1.0546e-34 * w, "formula": "hbar omega"},
    "II.3.24": {"inputs": ["Pwr", "r"], "ranges": [(1, 5), (1, 5)], "f": lambda P, r: P / (4 * np.pi * r ** 2), "formula": "P / (4 pi r^2)"},
    "I.27.6": {"inputs": ["d1", "d2", "n"], "ranges": [(1, 5), (1, 5), (1, 5)], "f": lambda d1, d2, n: 1 / (1 / d1 + n / d2), "formula": "1/(1/d1 + n/d2)"},
    "I.39.1": {"inputs": ["pr", "V"], "ranges": [(1, 5), (1, 5)], "f": lambda p, V: 1.5 * p * V, "formula": "3/2 p V"},
}

UNIVARIATE = {
    "random_univariate": {"inputs": ["x"], "ranges": [(-3, 3)], "f": lambda x: 1.5 * x ** 3 - 2.0 * x + np.sin(2 * x), "formula": "1.5x^3 - 2x + sin(2x)", "noise": 0.0},
    "noisy_univariate": {"inputs": ["x"], "ranges": [(-3, 3)], "f": lambda x: 1.5 * x ** 3 - 2.0 * x + np.sin(2 * x), "formula": "1.5x^3 - 2x + sin(2x) + N(0, 0.1)", "noise": 0.1},
    "special_functions": {"inputs": ["x"], "ranges": [(0.1, 6)], "f": lambda x: __import__("scipy.special", fromlist=["j0"]).j0(x), "formula": "Bessel J0(x)", "noise": 0.0},
    "kan_exp_sin_pi_x_y2": {"inputs": ["x", "y"], "ranges": [(-1, 1), (-1, 1)], "f": lambda x, y: np.exp(np.sin(np.pi * x) + y ** 2), "formula": "exp(sin(pi x) + y^2)", "noise": 0.0},
    "kan_multiplication": {"inputs": ["x", "y"], "ranges": [(-1, 1), (-1, 1)], "f": lambda x, y: x * y, "formula": "x y", "noise": 0.0},
    "kan_gravitational": {"inputs": ["x", "y", "z"], "ranges": [(0.5, 2), (0.5, 2), (0.5, 2)], "f": lambda x, y, z: x * y / z, "formula": "x y / z", "noise": 0.0},
    "kan_rescue_univariate": {"inputs": ["x"], "ranges": [(-2, 2)], "f": lambda x: np.tanh(3 * x) + 0.3 * x ** 2, "formula": "tanh(3x) + 0.3x^2", "noise": 0.0},
    "srbench_banana": {"inputs": ["x", "y"], "ranges": [(-2, 2), (-1, 3)], "f": lambda x, y: 100 * (y - x ** 2) ** 2 + (1 - x) ** 2, "formula": "banana (Rosenbrock) surface", "noise": 0.0},
    "polynomial_cubic": {"inputs": ["x"], "ranges": [(-2, 2)], "f": lambda x: x ** 3 - 2 * x + 1, "formula": "x^3 - 2x + 1", "noise": 0.0},
}


def synthetic_data(spec, n, seed):
    rng = np.random.default_rng(seed)
    inputs = [rng.uniform(lo, hi, n) for lo, hi in spec["ranges"]]
    target = np.asarray(spec["f"](*inputs), dtype=float)
    if spec.get("noise"):
        target = target + rng.normal(0, spec["noise"], n)
    return inputs, target


def synthetic_score(equation, spec, n_train=200, n_test=200, seed=0):
    """Fit params on generated training data, report held-out NMSE. Lower is better."""
    x_train, y_train = synthetic_data(spec, n_train, seed)
    x_test, y_test = synthetic_data(spec, n_test, seed + 1)
    try:
        params, train_mse = _fit(equation, x_train, y_train)
    except CandidateError:
        raise
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"equation failed during fitting: {type(error).__name__}: {error}") from None
    require(math.isfinite(train_mse) and train_mse < 1e29, "fitting produced a non-finite residual")
    return {"score": _nmse(equation, params, x_test, y_test), "train_mse": train_mse}


# --- LLM-SRBench (LSR-Transform, LSR-Synth) from the Hugging Face mirror ----------------

LSR_SUBSETS = {"lsr_transform": "LSR-Transform", "lsr_synth_chem_react": "LSR-Synth chemistry", "lsr_synth_bio_pop_growth": "LSR-Synth biology",
               "lsr_synth_phys_osc": "LSR-Synth physics", "lsr_synth_matsci": "LSR-Synth materials"}


def load_lsr(subset, instance_id=None, max_instances=4, seed=0):
    """Instances of an LLM-SRBench subset as dicts with X_train/y_train/X_test/y_test (and OOD when present)."""
    import json
    import random
    try:
        from datasets import load_dataset
    except ImportError as error:
        raise CandidateError(f"the datasets package is required: {error}") from None
    try:
        rows = load_dataset("pkuHaowei/llm-srbench", data_dir=subset, split="train")
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"cannot load LLM-SRBench {subset}: {type(error).__name__}: {str(error)[:200]}") from None
    items = [r for r in rows if instance_id is None or r["instance_id"].lower().endswith(instance_id.lower())]
    require(items, f"instance {instance_id} not found in {subset}")
    if instance_id is None:
        random.Random(seed).shuffle(items)
        items = items[:max_instances]
    out = []
    for r in items:
        def parse(value):
            return json.loads(value.replace("'", '"')) if isinstance(value, str) else value
        entry = {"id": r["instance_id"], "description": r["description"], "input_vars": parse(r["input_vars"]), "output_vars": parse(r["output_vars"]),
                 "X_train": np.array(parse(r["train_input"]), dtype=float), "y_train": np.array(parse(r["train_output"]), dtype=float).ravel(),
                 "X_test": np.array(parse(r["test_input"]), dtype=float), "y_test": np.array(parse(r["test_output"]), dtype=float).ravel()}
        if r.get("ood_input") is not None and len(r["ood_input"]):
            entry["X_ood"] = np.array(parse(r["ood_input"]), dtype=float)
            entry["y_ood"] = np.array(parse(r["ood_output"]), dtype=float).ravel()
        out.append(entry)
    return out


def lsr_score(equation, subset, instance_id=None, max_instances=4, seed=0):
    """Mean test NMSE of ``equation(X, params) -> y`` (X columns in input_vars order, 10 fitted params) over the selected instances. Lower is better."""
    from scipy.optimize import minimize
    instances = load_lsr(subset, instance_id, max_instances, seed)
    scores, per_instance = [], {}
    for inst in instances:
        X, y = inst["X_train"], inst["y_train"]

        def loss(params):
            try:
                pred = np.asarray(equation(X, params), dtype=float).ravel()
            except Exception:  # noqa: BLE001
                return 1e30
            if pred.shape != y.shape:
                return 1e30
            value = float(np.mean((pred - y) ** 2))
            return value if math.isfinite(value) else 1e30
        try:
            result = minimize(loss, np.ones(10), method="BFGS")
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"fitting failed: {type(error).__name__}: {error}") from None
        require(math.isfinite(result.fun) and result.fun < 1e29, f"equation produced no finite residual on {inst['id']}")
        pred = np.asarray(equation(inst["X_test"], result.x), dtype=float).ravel()
        require(pred.shape == inst["y_test"].shape and np.all(np.isfinite(pred)), f"non-finite test prediction on {inst['id']}")
        nmse = float(np.mean((pred - inst["y_test"]) ** 2) / (np.var(inst["y_test"]) + 1e-12))
        per_instance[inst["id"]] = nmse
        scores.append(nmse)
    return {"score": float(np.mean(scores)), "per_instance": per_instance, "instances": [i["id"] for i in instances]}
