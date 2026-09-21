"""LLM-SQL (CORAL, AdaEvolve, EvoX).

Protocol: original. The evaluator, simulator and data of the ADRS "llm_sql"
task are copied verbatim from the CORAL checkout (https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408,
examples/ADRS/llm_sql/taskdata, Apache-2.0) into suite/_lib/vendor/adrs/llm_sql;
this file only loads that evaluator and normalises its result. The upstream
module imports ``initial_program`` at import time, so this directory is put on
sys.path; outputs the simulator writes go to a temporary directory.
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE_LIB = HERE.parents[0] / "_lib"
VENDOR = SUITE_LIB / "vendor" / "adrs" / "llm_sql"
if str(SUITE_LIB) not in sys.path:
    sys.path.insert(0, str(SUITE_LIB))
from autoresearch_suite import runtime  # noqa: E402
from arena_task_paths import runtime_path, stage_vendor

DIRECTION = "maximize"
REQUIRES = ["py:numpy", "py:pandas", "file:vendor/adrs/llm_sql/datasets/BIRD.csv"]


def evaluate(program_path="initial_program.py"):
    program = str(Path(program_path).resolve())
    for item in REQUIRES:
        if item.startswith("file:") and not runtime_path(item[5:]).exists():
            return runtime.failure(f"missing data file {item[5:]}; run scripts/prepare_adrs_data.py --suite", DIRECTION, requires=REQUIRES)
    cwd, saved = os.getcwd(), sys.path[:]
    with tempfile.TemporaryDirectory(prefix="artask-adrs-") as scratch:
        try:
            os.chdir(scratch)
            staged = stage_vendor(VENDOR, "adrs/" + VENDOR.name, Path(scratch) / "vendor")
            sys.path[:0] = [str(staged), str(HERE)]
            for name in ("initial_program", "utils", "simulator", "broadcast", "solver", "txn_simulator", "workloads"):
                sys.modules.pop(name, None)
            spec = importlib.util.spec_from_file_location("adrs_llm_sql_evaluator", staged / "evaluator.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with runtime.Deadline(900):
                result = module.evaluate(program)
        except Exception as error:  # noqa: BLE001
            return runtime.failure(f"{type(error).__name__}: {error}", DIRECTION)
        finally:
            os.chdir(cwd)
            sys.path[:] = saved
    if hasattr(result, "metrics"):
        result = result.metrics
    result = dict(result)
    score = result.get("combined_score")
    error = result.get("error")
    if error or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
        return runtime.failure(error or "upstream evaluator returned no finite combined_score", DIRECTION, upstream=result)
    return runtime.success(float(score), DIRECTION, upstream=result)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
