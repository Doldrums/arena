"""Run the pinned LLM4AD task evaluators used by MEoH on a candidate heuristic file.

MEoH (Multi-objective Evolution of Heuristics) is implemented in the LLM4AD
platform (``llm4ad/method/meoh``). Its two objectives are the task score
returned by the platform's task ``Evaluation`` class and the wall-clock
evaluation time measured by ``SecureEvaluator.evaluate_program_record_time``.
This adapter imports the unmodified task evaluation class from the pinned
checkout (``OBPEvaluation`` for online bin packing, ``TSPEvaluation`` for the
constructive TSP heuristic), executes the candidate source in a fresh
namespace, extracts the heuristic function named in the task template and
calls ``evaluate_program`` while timing it.

The primary score is the platform's own return value (a negated cost, so
higher is better); ``evaluation_seconds`` is the second MEoH objective and is
recorded, not folded into the score. A ``None`` return (the TSP evaluator's
signal for an invalid tour) is reported as ``valid: false``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import time

TASKS = {
    "online_bin_packing": {
        "module": "llm4ad.task.optimization.online_bin_packing.evaluation",
        "class": "OBPEvaluation",
        "function": "priority",
        "path": "llm4ad/task/optimization/online_bin_packing/evaluation.py",
        "template": "llm4ad/task/optimization/online_bin_packing/template.py",
    },
    "tsp_construct": {
        "module": "llm4ad.task.optimization.tsp_construct.evaluation",
        "class": "TSPEvaluation",
        "function": "select_next_node",
        "path": "llm4ad/task/optimization/tsp_construct/evaluation.py",
        "template": "llm4ad/task/optimization/tsp_construct/template.py",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def template_program(checkout: Path, task: str) -> str:
    namespace = {}
    exec((checkout / TASKS[task]["template"]).read_text(), namespace)  # noqa: S102 - pinned template module
    return namespace["template_program"].strip() + "\n"


def evaluate(program_path: str, checkout: str, task: str, expected_evaluator_sha256: str | None = None) -> dict:
    if task not in TASKS:
        raise ValueError(f"Unknown LLM4AD task: {task}")
    spec = TASKS[task]
    checkout_path = Path(checkout).resolve()
    result = {"task": task, "score": None, "valid": None, "evaluation_seconds": None, "function": spec["function"]}
    try:
        digest = _sha256(checkout_path / spec["path"])
        if expected_evaluator_sha256 and digest != expected_evaluator_sha256:
            raise ValueError("Pinned LLM4AD evaluation module differs from its recorded SHA256")
        result["evaluator_module_sha256"] = digest
        if str(checkout_path) not in sys.path:
            sys.path.insert(0, str(checkout_path))
        import importlib
        module = importlib.import_module(spec["module"])
        evaluation = getattr(module, spec["class"])()
        code = Path(program_path).read_text()
        namespace = {}
        exec(code, namespace)  # noqa: S102 - candidate heuristic, executed as LLM4AD does
        function = namespace.get(spec["function"])
        if not callable(function):
            raise ValueError(f"Candidate must define {spec['function']}()")
        started = time.time()
        score = evaluation.evaluate_program(code, function)
        elapsed = time.time() - started
        result["evaluation_seconds"] = elapsed
        if score is None:
            result.update(valid=False, error="LLM4AD evaluator returned None (invalid heuristic output)")
        else:
            value = float(score)
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError("Evaluator returned a nonfinite score")
            result.update(score=value, valid=True, cost=-value)
    except Exception as error:  # noqa: BLE001
        result.update(valid=False, error=f"{type(error).__name__}: {error}")
    return result
