"""Arena same-evaluation feasibility adapter; original scorer is preserved unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_construction_capture import evaluate_construction


def evaluate(program_path):
    return evaluate_construction(program_path, __file__, 'sarkozy_subset',
                                 '8082024ed4ee95096b9bbc331a76d5e3f9d55f94d29cedaebbfb5cdac2e58c50')
