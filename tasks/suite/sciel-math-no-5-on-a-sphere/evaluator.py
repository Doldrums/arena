"""Arena same-evaluation feasibility adapter; original scorer is preserved unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_construction_capture import evaluate_construction


def evaluate(program_path):
    return evaluate_construction(program_path, __file__, 'no_five_sphere',
                                 '472d4e9547fa11aeea8216da7bf6136443e698c89c5584e82921a68c17700ebd')
