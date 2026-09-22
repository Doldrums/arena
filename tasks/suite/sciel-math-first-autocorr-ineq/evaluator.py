"""Same-call feasibility adapter; original numerical scorer is unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_jax_capture import evaluate_jax_construction


def evaluate(program_path):
    return evaluate_jax_construction(program_path, __file__, 'autocorrelation_c1',
                                     'abfaec6dec20c41242f89c8561a952e27c3d8ee52a28e64f662b48580bcefa51')
