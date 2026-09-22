"""Pinned RankEvolve candidate runner and independent binary-qrel grading."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_lib"))
from autoresearch_suite import runtime
from rankevolve.evaluator import evaluate as run_evaluation


def evaluate(program_path="initial_program.py"):
    try:
        return run_evaluation(program_path, HERE)
    except Exception as error:
        return runtime.failure(f"{type(error).__name__}: {error}", "maximize", valid=None)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
