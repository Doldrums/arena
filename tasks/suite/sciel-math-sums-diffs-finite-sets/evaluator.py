"""Same-call feasibility adapter; original numerical scorer is unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_jax_capture import evaluate_jax_construction


def evaluate(program_path):
    return evaluate_jax_construction(program_path, __file__, 'finite_sum_difference',
                                     'bf3c4ff0e11abe294b8f5d8c54090e2c701c9da25c52e693057c60f25aa96661')
