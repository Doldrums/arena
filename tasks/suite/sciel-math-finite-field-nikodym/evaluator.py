"""Arena validity adapter; original scoring is preserved in upstream_evaluator.py."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_verified_contract import evaluate_verified


def evaluate(program_path):
    return evaluate_verified(program_path, __file__, 'nikodym',
                             '36c738891ee3795be4411f20e8be483e4e76b223fe714179522d57bdbc40da63')
