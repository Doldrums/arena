"""Arena validity adapter; original scoring is preserved in upstream_evaluator.py."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_verified_contract import evaluate_verified


def evaluate(program_path):
    return evaluate_verified(program_path, __file__, 'sidon',
                             'eef0349b2d83332f6a048f9f87ee03937076fae732afbe8a7ff980dfe8e53bb4')
