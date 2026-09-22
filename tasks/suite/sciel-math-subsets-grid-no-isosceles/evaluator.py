"""Arena same-evaluation feasibility adapter; original scorer is preserved unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_construction_capture import evaluate_construction


def evaluate(program_path):
    return evaluate_construction(program_path, __file__, 'no_isosceles_grid',
                                 '014a8d90105d09dda79c6114ce79a651491a43cb9527a16d4f33cbf95d8b1110')
