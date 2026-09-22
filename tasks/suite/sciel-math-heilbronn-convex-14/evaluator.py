"""Same-call feasibility adapter; original numerical scorer is unchanged."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
from arena_jax_capture import evaluate_jax_construction


def evaluate(program_path):
    return evaluate_jax_construction(program_path, __file__, 'heilbronn_convex_14',
                                     '98bdc3cfb2bc462aac552aed0d4d454d86ee8fb808d913c11f1d440b1f8ff85d')
