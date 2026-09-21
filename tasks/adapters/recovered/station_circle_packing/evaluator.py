"""Run The Station's circle-packing verification on a candidate program.

The Station (dualverse-ai/station, Apache-2.0) evaluates its AlphaEvolve-style
circle-packing research tasks with ``Task1Evaluator._evaluate`` in
``example/research_alpha_evolve/circle_n{26,32}/research/evaluators/evaluator.py``.
The class inherits from the station package's ``ResearchTaskEvaluator`` and
saves accepted packings into the station's data rooms, but the verification
itself (``_evaluate``) is a self-contained NumPy function whose exact text is
also published in the task specification ``research_task.md``.

This adapter hash-checks the pinned evaluator file, extracts the unmodified
``_evaluate`` method source with ``ast``, compiles it as a standalone function,
imports the candidate and calls the documented entry point
``construct_packing() -> (centers, radii)``. A raised ``AssertionError`` is the
evaluator's rejection and is reported as ``valid: false``. Nothing is written
to the station's storage.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
import sys


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_evaluate(source: str):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Task1Evaluator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_evaluate":
                    item.args.args = [a for a in item.args.args if a.arg != "self"]
                    item.decorator_list = []
                    module = ast.Module(body=[item], type_ignores=[])
                    ast.fix_missing_locations(module)
                    namespace = {}
                    import numpy as np  # the extracted function uses the module alias np
                    namespace["np"] = np
                    exec(compile(module, "<station Task1Evaluator._evaluate>", "exec"), namespace)  # noqa: S102
                    return namespace["_evaluate"], ast.unparse(item)
    raise ValueError("Task1Evaluator._evaluate not found in the pinned evaluator")


def evaluate(program_path: str, checkout: str, n: int, expected_evaluator_sha256: str | None = None) -> dict:
    checkout_path = Path(checkout).resolve()
    relative = f"example/research_alpha_evolve/circle_n{int(n)}/research/evaluators/evaluator.py"
    result = {"n": int(n), "evaluator_path": relative, "score": None, "valid": None}
    try:
        evaluator_file = checkout_path / relative
        digest = _sha256(evaluator_file)
        if expected_evaluator_sha256 and digest != expected_evaluator_sha256:
            raise ValueError("Pinned Station evaluator differs from its recorded SHA256")
        result["station_evaluator_sha256"] = digest
        verify, _ = _extract_evaluate(evaluator_file.read_text())
        spec = importlib.util.spec_from_file_location("station_candidate", Path(program_path).resolve())
        module = importlib.util.module_from_spec(spec)
        sys.modules["station_candidate"] = module
        spec.loader.exec_module(module)
        if not hasattr(module, "construct_packing"):
            raise ValueError("Candidate must define construct_packing() -> (centers, radii)")
        packing = module.construct_packing()
        score = verify(packing)
        result.update(score=float(score), valid=True)
    except AssertionError as error:
        result.update(valid=False, error=f"Station verification failed: {error}")
    except Exception as error:  # noqa: BLE001
        result.update(valid=False, error=f"{type(error).__name__}: {error}")
    return result
