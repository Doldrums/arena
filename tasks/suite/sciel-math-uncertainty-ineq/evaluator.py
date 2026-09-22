"""Same-call feasibility adapter; original numerical scorer is unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_jax_capture import evaluate_jax_construction


def evaluate(program_path):
    return evaluate_jax_construction(program_path, __file__, 'sign_uncertainty',
                                     '4f2b51dc876777dfbc50f3ec75d278e974fc76e1ad4f2a42daa790b374062f45')
