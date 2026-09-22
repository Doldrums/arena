"""Arena same-evaluation feasibility adapter; original scorer is preserved unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_construction_capture import evaluate_construction


def evaluate(program_path):
    return evaluate_construction(program_path, __file__, 'pipeline_config',
                                 '4f31a4306589d94e8e21e98437e8045b6b1d8a4e5977944d183ee2b31c68fb43')
