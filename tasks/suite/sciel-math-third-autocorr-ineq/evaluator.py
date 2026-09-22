"""Same-call feasibility adapter; original numerical scorer is unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_jax_capture import evaluate_jax_construction


def evaluate(program_path):
    return evaluate_jax_construction(program_path, __file__, 'autocorrelation_c3',
                                     'a5f2a99d7e13c99d85201b4f0ebbef6839c4816ef7e0456b5bcfc4ccce3fe222')
