"""Same-call feasibility adapter; original numerical scorer is unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_jax_capture import evaluate_jax_construction


def evaluate(program_path):
    return evaluate_jax_construction(program_path, __file__, 'matmul_2_4_5',
                                     '9fd059997380c4240c6eef3cdf502581f29c731963dc3b0448bca2416122c086')
