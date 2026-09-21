"""SCiEL: MLIR attention transformation parameters (SCiEL attention_optimization example, original evaluator).

The unmodified SCiEL evaluator (evaluator_sciel.py) only loads candidate code
from a path under /tmp ending in .py, which is where OpenEvolve writes programs
during evolution. This wrapper copies the candidate to such a path and calls the
original evaluate(); scoring is unchanged. Needs mlir-opt on PATH.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def evaluate(program_path="initial_program.py"):
    spec = importlib.util.spec_from_file_location("sciel_attention_evaluator", HERE / "evaluator_sciel.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.NamedTemporaryFile("w", suffix=".py", prefix="artask-", dir="/tmp", delete=False) as handle:
        shutil.copyfileobj(open(program_path), handle)
        temporary = handle.name
    try:
        result = module.evaluate(temporary)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return getattr(result, "metrics", result)


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(sys.argv[1] if len(sys.argv) > 1 else "initial_program.py"), default=str))
