"""
Evaluator for the self-contained symbolic-regression example.

Scores the evolved predictor on a HELD-OUT test set whose ground truth is
re-derived here independently of the program file, so an evolved program
cannot fake the metric by touching its own internals. Mirrors the
function_minimization evaluator contract (EvaluationResult + combined_score
+ evaluate_stage1 for cascade).
"""

import importlib.util
import traceback
import concurrent.futures

import numpy as np

from openevolve.evaluation_result import EvaluationResult

# Independent ground truth (must match initial_program._hidden_target /
# _make_data; duplicated on purpose so test scoring is tamper-proof, exactly
# as function_minimization hardcodes its global optimum).
_SEED = 20260517
_N = 400


def _hidden_target(X):
    x0, x1 = X[:, 0], X[:, 1]
    return 2.5 * np.sin(1.3 * x0) + 0.7 * x1**2 - 0.4 * x0 * x1 + 1.1


def _test_split():
    rng = np.random.default_rng(_SEED)
    X = rng.uniform(-3.0, 3.0, size=(_N, 2))
    y = _hidden_target(X)
    n_train = _N // 2
    return X[n_train:], y[n_train:]  # the held-out half


_Xte, _yte = _test_split()
_y_var_te = float(np.var(_yte)) or 1.0


def run_with_timeout(func, args=(), kwargs={}, timeout_seconds=10):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(func, *args, **kwargs).result(timeout=timeout_seconds)


def _test_nmse(predict):
    pred = np.asarray(predict(_Xte), dtype=float).reshape(-1)
    if pred.shape[0] != _yte.shape[0] or not np.all(np.isfinite(pred)):
        return _OVER  # treated as failure
    return float(np.mean((pred - _yte) ** 2) / _y_var_te)


_OVER = 1e9


def _score_from_nmse(nmse: float) -> float:
    """NMSE -> combined_score with a solution-quality multiplier that widens
    the dynamic range (mirrors function_minimization's multiplier), so a weak
    linear seed and a structure-recovering model are well separated."""
    base = 1.0 / (1.0 + nmse)
    if nmse < 1e-3:  # structure + constants essentially recovered
        mult = 1.5
    elif nmse < 0.05:  # right structure, imperfect constants
        mult = 1.2
    elif nmse < 0.3:  # partially right
        mult = 1.0
    else:  # linear-seed territory / wrong structure
        mult = 0.6
    return float(base * mult)


def _load(program_path):
    spec = importlib.util.spec_from_file_location("program", program_path)
    program = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(program)
    return program


def _missing_run_search():
    return EvaluationResult(
        metrics={
            "test_nmse": _OVER,
            "fit_quality": 0.0,
            "combined_score": 0.0,
            "error": "Missing run_search function",
        },
        artifacts={
            "suggestion": "Program must define run_search() returning " "a predictor f(X)->y."
        },
    )


def evaluate(program_path):
    """Run the evolved search a few times; score held-out test NMSE."""
    try:
        program = _load(program_path)
        if not hasattr(program, "run_search"):
            return _missing_run_search()

        num_trials = 3
        nmses = []
        for _ in range(num_trials):
            try:
                predict = run_with_timeout(program.run_search, timeout_seconds=10)
                if not callable(predict):
                    nmses.append(_OVER)
                    continue
                nmses.append(_test_nmse(predict))
            except Exception as e:  # noqa: BLE001
                print(f"Trial failed: {e}")
                nmses.append(_OVER)

        avg_nmse = float(np.mean(nmses))
        best_nmse = float(np.min(nmses))
        success_rate = float(np.mean([n < _OVER for n in nmses]))
        combined = _score_from_nmse(avg_nmse) * (0.5 + 0.5 * success_rate)
        fit_quality = float(1.0 / (1.0 + avg_nmse))

        return EvaluationResult(
            metrics={
                "test_nmse": avg_nmse,
                "best_test_nmse": best_nmse,
                "fit_quality": fit_quality,
                "reliability": success_rate,
                "combined_score": float(combined),
            },
            artifacts={
                "avg_test_nmse": f"{avg_nmse:.6g}",
                "best_test_nmse": f"{best_nmse:.6g}",
                "note": "lower NMSE is better; combined_score is higher-better "
                "and rewards recovering the hidden structure within "
                "the training-fit-call budget.",
            },
        )
    except Exception as e:  # noqa: BLE001
        print(f"Evaluation failed completely: {e}")
        print(traceback.format_exc())
        return EvaluationResult(
            metrics={
                "test_nmse": _OVER,
                "fit_quality": 0.0,
                "combined_score": 0.0,
                "error": str(e),
            },
            artifacts={"error_type": type(e).__name__, "full_traceback": traceback.format_exc()},
        )


def evaluate_stage1(program_path):
    """Cheap single-trial gate for cascade evaluation (config cascade_thresholds)."""
    try:
        program = _load(program_path)
        if not hasattr(program, "run_search"):
            return _missing_run_search()
        predict = run_with_timeout(program.run_search, timeout_seconds=10)
        if not callable(predict):
            return EvaluationResult(
                metrics={"test_nmse": _OVER, "combined_score": 0.0},
                artifacts={"error": "run_search() must return a predictor f(X)->y"},
            )
        nmse = _test_nmse(predict)
        return EvaluationResult(
            metrics={"test_nmse": nmse, "combined_score": _score_from_nmse(nmse)},
        )
    except Exception as e:  # noqa: BLE001
        return EvaluationResult(
            metrics={"test_nmse": _OVER, "combined_score": 0.0, "error": str(e)},
            artifacts={"full_traceback": traceback.format_exc()},
        )
