"""Source-derived LMX excess red; complete SD1.4 GPU image evaluation."""
from pathlib import Path
import sys

SUITE_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(SUITE_LIB) not in sys.path:
    sys.path.insert(0, str(SUITE_LIB))

from autoresearch_suite import lmx_sd, runtime

def evaluate(program_path="initial_program.py"):
    return lmx_sd.evaluate(program_path, 'r')

if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
