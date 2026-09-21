"""SCiEL: AlgoTune complex FFT (SCiEL AlgoTune example, original evaluator with vendored registry).

The unmodified SCiEL evaluator (evaluator_sciel.py in this directory) looks
for an AlgoTune checkout at fixed machine-specific paths and otherwise runs
with an empty task registry. This wrapper imports the byte-verified vendored
AlgoTune subset (suite/_lib/vendor/algotune, see SOURCES.json), registers the
task and hands the original evaluator its TASK_REGISTRY; scoring, timing and
validity logic are the SCiEL source's.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE_LIB = HERE.parents[0] / "_lib"
for entry in (SUITE_LIB, SUITE_LIB / "vendor" / "algotune"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import os
from arena_task_paths import cache_path, external_path

os.environ["ALGOTUNE_HF_CACHE_DIR"] = str(external_path(os.environ.get("ALGOTUNE_HF_CACHE_DIR", cache_path("algotune", "huggingface"))))
os.environ["DATA_DIR"] = str(external_path(os.environ.get("DATA_DIR", cache_path("algotune", "data"))))

TASK = "fft_cmplx_scipy_fftpack"


def _original():
    importlib.import_module(f"AlgoTuneTasks.{TASK}.{TASK}")
    from AlgoTuneTasks.base import TASK_REGISTRY
    spec = importlib.util.spec_from_file_location("sciel_algotune_" + TASK, HERE / "evaluator_sciel.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TASK_REGISTRY = TASK_REGISTRY
    return module


def evaluate(program_path="initial_program.py"):
    result = _original().evaluate(str(Path(program_path).resolve()))
    return getattr(result, "metrics", result)


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(sys.argv[1] if len(sys.argv) > 1 else "initial_program.py"), default=str))
