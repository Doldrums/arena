"""Arena validity adapter; original scoring is preserved in upstream_evaluator.py."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_verified_contract import evaluate_verified


def evaluate(program_path):
    return evaluate_verified(program_path, __file__, 'turan',
                             '3e2b6d700f18f5ec51ea0b5a6b79c3c3b755c0f2f3e44a9914bd40b0105b4993')
