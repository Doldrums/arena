"""Arena validity adapter; original scoring is preserved in upstream_evaluator.py."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_verified_contract import evaluate_verified


def evaluate(program_path):
    return evaluate_verified(program_path, __file__, 'convex_polygon',
                             'bbec4c4a840a2b67e7298884ab027b561c9476465cd11f508457b9df0081cd63')
