"""ahc027 Cleaning route (EvoX, ShinkaEvolve).

Protocol: original. The evaluator is the EvoX (skydiscover) ALE-Bench evaluator
for ahc027, copied verbatim into suite/_lib/vendor/evox_alebench/ahc027; it
scores a C++ heuristic-contest program on 50 public cases through the public
ALE-Bench package (Docker judge). The unpublished helper it imports
(ale_bench_eval.safe_ale_session) is provided by the shim in
suite/_lib/ale_bench_eval. 
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE_LIB = HERE.parents[0] / "_lib"
for entry in (SUITE_LIB, SUITE_LIB / "vendor" / "evox_alebench" / "ahc027"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))
from autoresearch_suite import runtime  # noqa: E402

DIRECTION = "maximize"


def evaluate(program_path="initial_program.cpp"):
    os.environ.setdefault("DYLD_FALLBACK_LIBRARY_PATH", "/opt/homebrew/lib")
    try:
        spec = importlib.util.spec_from_file_location("evox_alebench_ahc027", SUITE_LIB / "vendor" / "evox_alebench" / "ahc027" / "evaluator.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with runtime.Deadline(1800):
            result = module.evaluate(str(Path(program_path).resolve()))
    except Exception as error:  # noqa: BLE001
        return runtime.failure(f"{type(error).__name__}: {error}", DIRECTION)
    result = dict(getattr(result, "metrics", result))
    score = result.get("combined_score")
    if result.get("error") or not isinstance(score, (int, float)) or not math.isfinite(float(score)) or float(score) <= -1e15:
        return runtime.failure(result.get("error") or "ALE-Bench rejected the program", DIRECTION, upstream=result)
    return runtime.success(float(score), DIRECTION, upstream=result)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
