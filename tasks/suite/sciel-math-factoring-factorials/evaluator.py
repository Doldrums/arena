"""Arena same-evaluation feasibility adapter; original scorer is preserved unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_construction_capture import evaluate_construction


def evaluate(program_path):
    return evaluate_construction(program_path, __file__, 'factorial_assignment',
                                 '3bf731604c7f0a689d067b8fba365e23ff357610769a3821735f6da1005e1662')
