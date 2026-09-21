"""Anthropic performance take-home (CORAL, AEvo).

Protocol: original. The Anthropic performance take-home is evaluated with the
CORAL kernel_builder grader (https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408, examples/kernel_builder, Apache-2.0):
``grader.py`` (its ``_run_evaluation`` subprocess script) and the frozen VLIW
simulator ``frozen_problem.py`` are copied verbatim into
suite/_lib/vendor/kernel_builder. The grader's CORAL base classes are stubbed
so the unmodified module imports; the real-mode workload parameters are used.
Score: simulated cycle count (lower is better); a kernel with incorrect output
is invalid.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE_LIB = HERE.parents[0] / "_lib"
VENDOR = SUITE_LIB / "vendor" / "kernel_builder"
if str(SUITE_LIB) not in sys.path:
    sys.path.insert(0, str(SUITE_LIB))
from autoresearch_suite import runtime  # noqa: E402

DIRECTION = "minimize"


def _grader():
    for name, attrs in (("coral", {}), ("coral.grader", {"TaskGrader": object}), ("coral.types", {"ScoreBundle": object})):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__dict__.update(attrs)
            sys.modules[name] = module
    spec = importlib.util.spec_from_file_location("kernel_builder_grader", VENDOR / "grader.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(program_path="initial_program.py"):
    try:
        grader = _grader()
        result = grader._run_evaluation(str(Path(program_path).resolve()), str(VENDOR / "frozen_problem.py"), 600, [sys.executable], grader.REAL_PARAMS)
    except Exception as error:  # noqa: BLE001
        return runtime.failure(f"{type(error).__name__}: {error}", DIRECTION)
    if "error" in result:
        return runtime.failure(result["error"], DIRECTION, upstream=result)
    if not result.get("is_correct"):
        return runtime.failure("kernel produces incorrect output: " + str(result.get("error_msg")), DIRECTION, upstream=result)
    return runtime.success(float(result["cycles"]), DIRECTION, baseline_cycles=grader.BASELINE_CYCLES, best_known_cycles=grader.BEST_KNOWN_CYCLES)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
