"""Arena same-evaluation feasibility adapter; original scorer is preserved unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_construction_capture import evaluate_construction


def evaluate(program_path):
    return evaluate_construction(program_path, __file__, 'squarefree_subset',
                                 '09a43e81f00e2f2304abd3c195ccff8db160b7d7e80b51c136098a7578fa63cb')
