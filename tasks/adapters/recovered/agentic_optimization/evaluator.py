"""Run the pinned AgenticOptimization circle_packing_26 task evaluator on a candidate.

The task module ``tasks/circle_packing_26/task.py`` (Junye-Pan/AgenticOptimization)
implements the server-side evaluation: it executes ``run_packing()`` in a
spawned worker with a timeout, validates shapes, finiteness, containment,
pairwise overlap and the reported sum, and scores the packing with a strict
fixed-center linear-programming safety margin (``strict_safe_score``). The
control plane normally loads it through ``agentic_opt.task_registry``; this
adapter loads the same file directly with the repository's ``src`` directory
on ``sys.path`` and registers the module under its own name so the module's
frozen dataclasses resolve. Because the server's worker spawn re-imports the
task through the control-plane registry, the adapter runs the task's own
``_load_program``, ``run_packing()`` and ``analyze_output`` in-process instead;
the scoring code is unchanged and the common runner's timeout bounds it. No
control-plane state, database or web server is involved.

The primary score is the task's ``strict_safe_score`` (sum of radii after the
safety margin); ``valid`` is the task's own verdict. A raised ``ValueError``
carries the evaluator's rejection message.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

TASK_FILE = "tasks/circle_packing_26/task.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(program_path: str, checkout: str, expected_task_sha256: str | None = None) -> dict:
    checkout_path = Path(checkout).resolve()
    result = {"task": "circle_packing_26", "score": None, "valid": None}
    try:
        task_file = checkout_path / TASK_FILE
        digest = _sha256(task_file)
        if expected_task_sha256 and digest != expected_task_sha256:
            raise ValueError("Pinned task module differs from its recorded SHA256")
        result["task_module_sha256"] = digest
        source_root = str(checkout_path / "src")
        if source_root not in sys.path:
            sys.path.insert(0, source_root)
        name = "agentic_opt_task_circle_packing_26"
        spec = importlib.util.spec_from_file_location(name, task_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        # evaluate_entry() runs run_packing() in a spawned worker that must re-import the
        # task module by name from the control plane's registry, which is unavailable
        # outside the server. The same pipeline is run in-process here: the task's own
        # program loader, run_packing(), and analyze_output() (unchanged scoring). The
        # common runner's outer timeout replaces the worker's 180 s deadline.
        program = module._load_program(Path(program_path).resolve())
        if not callable(getattr(program, "run_packing", None)):
            raise ValueError("Candidate must define run_packing() -> (centers, radii, reported_sum)")
        diagnostics = module.analyze_output(program.run_packing())
        if not diagnostics["valid"]:
            raise ValueError(diagnostics["error"] or "evaluation failed")
        score = diagnostics["strict_safe_score"]
        if score is None:
            raise ValueError(diagnostics["strict_safe_error"] or "strict safe scoring failed")
        result.update(score=float(score), valid=True, execution_mode="in_process_analyze_output",
                      metrics={k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                               for k, v in diagnostics.items()
                               if k in ("reported_sum", "actual_sum", "strict_safe_gap", "strict_safe_min_boundary_slack",
                                        "strict_safe_min_pair_slack", "min_boundary_slack", "min_pair_slack",
                                        "num_nearly_active_boundary_constraints", "num_nearly_active_pair_constraints")})
    except ValueError as error:  # the task's own rejection (invalid geometry, sum mismatch, timeout wrapper)
        result.update(valid=False, error=f"Task evaluator rejected the candidate: {error}")
    except Exception as error:  # noqa: BLE001
        result.update(valid=False, error=f"{type(error).__name__}: {error}")
    return result
