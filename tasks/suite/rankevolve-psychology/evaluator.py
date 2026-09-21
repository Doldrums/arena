"""psychology (RankEvolve).

Protocol: original. This task is evaluated by the paper's own pinned evaluator
through the repository's upstream adapter (original evaluator); the suite evaluator only
forwards to it. Fetch the pinned source once with

    python3 run.py setup rankevolve-psychology

The BRIGHT split is downloaded from the Hugging Face Hub (xlangai/BRIGHT) by the pinned loader at run time. Requirements are listed in problem.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUITE_LIB = ROOT / "suite" / "_lib"
for entry in (SUITE_LIB, ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))
from autoresearch_suite import runtime  # noqa: E402

DIRECTION = "maximize"
TIMEOUT = 1800


def evaluate(program_path="initial_program.py"):
    from autoresearch_tasks.runner import evaluate_upstream
    task = json.loads((HERE / "task.json").read_text())
    try:
        result = evaluate_upstream(ROOT, task, Path(program_path).resolve(), python=sys.executable, timeout=TIMEOUT)
    except Exception as error:  # noqa: BLE001
        return runtime.failure(f"{type(error).__name__}: {error}", DIRECTION)
    if result.get("status") != "completed" or result.get("score") is None:
        return runtime.failure(result.get("error") or result.get("status") or "upstream evaluation failed", DIRECTION, upstream=result.get("upstream_result"))
    out = runtime.success(float(result["score"]), DIRECTION, upstream=result.get("upstream_result"), implementation_label=result.get("implementation_label"))
    out["valid"] = result.get("valid")
    return out


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
