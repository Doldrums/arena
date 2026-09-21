"""Run the pinned CoEvo LLM-SR task evaluators on a candidate equation file.

CoEvo (pgg3/CoEvo, MIT) ships the four LLM-SR benchmark tasks (oscillation_1,
oscillation_2, bactgrow, stress_strain) as ``PythonTask`` subclasses under
``CoEvo/src/coevo/tasks/`` together with the benchmark CSV data. Each task's
``_evaluate_code_impl`` executes the candidate source, fits its ten free
parameters with BFGS on the task's training split and returns the mean squared
error. That method is self-contained; only the base classes come from the
external ``evotoolkit`` package, which is not on PyPI.

This adapter imports the unmodified task module from the pinned checkout. When
``evotoolkit`` is not installed it registers a minimal stand-in for the two
symbols the task modules import (``EvaluationResult``/``TaskSpec`` containers
and a ``PythonTask`` base that only stores its constructor arguments). The
stand-in is used solely so the pinned module can be imported; the scientific
scoring code is CoEvo's own. The outer runner timeout replaces evotoolkit's
per-evaluation subprocess timeout.

The result exposes ``mse`` (minimize), CoEvo's ``score`` (``-mse``), and the
task's explicit ``valid`` flag.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
TASKS = {
    "oscillation_1": {"module": "CoEvo/src/coevo/tasks/oscillation_1.py", "class": "Oscillation1Task", "data": "data/oscillation_1/train.csv"},
    "oscillation_2": {"module": "CoEvo/src/coevo/tasks/oscillation_2.py", "class": "Oscillation2Task", "data": "data/oscillation_2/train.csv"},
    "bactgrow": {"module": "CoEvo/src/coevo/tasks/bactgrow.py", "class": "BactGrowTask", "data": "data/bactgrow/train.csv"},
    "stress_strain": {"module": "CoEvo/src/coevo/tasks/stress_strain.py", "class": "StressStrainTask", "data": "data/stress_strain/train.csv"},
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _install_evotoolkit_stub() -> bool:
    try:
        import evotoolkit.core  # noqa: F401
        import evotoolkit.task.python_task  # noqa: F401
        return bool(getattr(sys.modules["evotoolkit"], "_autoresearch_stub", False))
    except ImportError:
        pass

    class EvaluationResult:
        def __init__(self, valid=False, score=None, additional_info=None):
            self.valid, self.score, self.additional_info = valid, score, dict(additional_info or {})

    class TaskSpec:
        def __init__(self, name=None, prompt=None, modality=None, extras=None):
            self.name, self.prompt, self.modality, self.extras = name, prompt, modality, dict(extras or {})

    class PythonTask:
        def __init__(self, data=None, timeout_seconds=30.0):
            self.data, self.timeout_seconds = data, timeout_seconds

    root = types.ModuleType("evotoolkit")
    core = types.ModuleType("evotoolkit.core")
    core.EvaluationResult, core.TaskSpec = EvaluationResult, TaskSpec
    task_pkg = types.ModuleType("evotoolkit.task")
    python_task = types.ModuleType("evotoolkit.task.python_task")
    python_task.PythonTask = PythonTask
    root.core, root.task, task_pkg.python_task = core, task_pkg, python_task
    for name, module in (("evotoolkit", root), ("evotoolkit.core", core), ("evotoolkit.task", task_pkg), ("evotoolkit.task.python_task", python_task)):
        module._autoresearch_stub = True
        sys.modules[name] = module
    return True


def load_task(checkout: Path, task: str):
    spec = TASKS[task]
    stubbed = _install_evotoolkit_stub()
    module_path = checkout / spec["module"]
    loader_spec = importlib.util.spec_from_file_location(f"coevo_task_{task}", module_path)
    module = importlib.util.module_from_spec(loader_spec)
    loader_spec.loader.exec_module(module)
    task_class = getattr(module, spec["class"])
    instance = task_class(dataset_dir=str(checkout / spec["data"]))
    return instance, stubbed, module_path


def seed_source(checkout: Path, task: str) -> str:
    """Extract the original program template CoEvo shows the model, as the seed."""
    instance, _, _ = load_task(checkout, task)
    template = instance.build_python_spec(None).extras["program_template"]
    start = template.index("```python") + len("```python")
    end = template.index("```", start)
    return template[start:end].strip() + "\n"


def evaluate(program_path: str, checkout: str, task: str, expected_module_sha256: str | None = None) -> dict:
    if task not in TASKS:
        raise ValueError(f"Unknown CoEvo task: {task}")
    checkout_path = Path(checkout).resolve()
    result = {"task": task, "score": None, "mse": None, "valid": None, "split": TASKS[task]["data"]}
    try:
        instance, stubbed, module_path = load_task(checkout_path, task)
        digest = _sha256(module_path)
        if expected_module_sha256 and digest != expected_module_sha256:
            raise ValueError("Pinned task module differs from its recorded SHA256")
        result.update(task_module_sha256=digest, data_sha256=_sha256(checkout_path / TASKS[task]["data"]), evotoolkit_stubbed=stubbed)
        code = Path(program_path).read_text()
        outcome = instance._evaluate_code_impl(code)
        info = dict(getattr(outcome, "additional_info", {}) or {})
        valid = bool(getattr(outcome, "valid", False))
        result.update(valid=valid, coevo_score=getattr(outcome, "score", None) if valid else None,
                      elapsed_seconds=info.get("time"), fitness_string=info.get("fitness_string"))
        if valid:
            mse = float(info["mse"])
            result.update(mse=mse, score=-mse)
        else:
            result["error"] = str(info.get("error", "CoEvo evaluator rejected the candidate"))
    except Exception as error:  # noqa: BLE001
        result.update(valid=False, error=f"{type(error).__name__}: {error}")
    return result


if __name__ == "__main__":
    print(json.dumps(evaluate(sys.argv[1], sys.argv[2], sys.argv[3]), indent=2, default=str))
