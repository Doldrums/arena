"""Same-call feasibility adapter; original numerical scorer is unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_jax_capture import evaluate_jax_construction


def evaluate(program_path):
    return evaluate_jax_construction(program_path, __file__, 'autocorrelation_c2',
                                     'ffc443c2b0c682fc636393adbaf731bd5799a0502386369bec1ca088ad868a83')
