"""Arena same-evaluation feasibility adapter; original scorer is preserved unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_construction_capture import evaluate_construction


def evaluate(program_path):
    return evaluate_construction(program_path, __file__, 'flat_sign_polynomial',
                                 'a0801463110b1bd7a1e3c65f7cf1c01c34f27eb6d611dd212c86036d910cfea9')
