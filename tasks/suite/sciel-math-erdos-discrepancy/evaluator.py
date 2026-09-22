"""Arena validity adapter; original scoring is preserved in upstream_evaluator.py."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_verified_contract import evaluate_verified


def evaluate(program_path):
    return evaluate_verified(program_path, __file__, 'discrepancy',
                             '9a0c0bdec5d0f90f5e60c934f734c7915a28294e832e60a350114da0d6335716')
