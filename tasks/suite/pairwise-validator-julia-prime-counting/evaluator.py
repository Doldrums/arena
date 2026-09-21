"""julia_prime_counting (Pairwise Validator).

Protocol: original. The ShinkaEvolve julia_prime_counting evaluator
(SakanaAI/ShinkaEvolve examples/julia_prime_counting/evaluate.py, Apache-2.0) is
copied verbatim into suite/_lib/vendor/shinka_julia; this wrapper calls its
unmodified functions and returns the common result envelope. Needs the julia
executable on PATH.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE_LIB = HERE.parents[0] / "_lib"
if str(SUITE_LIB) not in sys.path:
    sys.path.insert(0, str(SUITE_LIB))
from autoresearch_suite import runtime  # noqa: E402

DIRECTION = "maximize"


def evaluate(program_path="initial_program.jl"):
    spec = importlib.util.spec_from_file_location("shinka_julia_evaluate", SUITE_LIB / "vendor" / "shinka_julia" / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    queries = module.QUERIES_PUBLIC + module.QUERIES_PRIVATE
    try:
        predicted, seconds = module._run_program(str(Path(program_path).resolve()), queries)
        metrics, correct, error = module._build_metrics(queries=queries, expected=module._expected_counts(queries), predicted=predicted, runtime_seconds=seconds)
    except FileNotFoundError:
        return runtime.failure("julia executable not found on PATH", DIRECTION)
    except subprocess.TimeoutExpired:
        return runtime.failure(f"Julia program timed out after {module.TIMEOUT_SECONDS} seconds", DIRECTION)
    except Exception as exc:  # noqa: BLE001
        return runtime.failure(str(exc), DIRECTION)
    if not correct:
        return runtime.failure(error or "incorrect prime counts", DIRECTION, upstream=metrics)
    return runtime.success(float(metrics["combined_score"]), DIRECTION, upstream=metrics)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
