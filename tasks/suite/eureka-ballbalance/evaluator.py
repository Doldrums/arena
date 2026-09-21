"""BallBalance (Eureka).

Protocol: unsupported (simulator).
Fitness requires a physics simulator or reinforcement-learning training loop (Isaac Gym) that is not bundled.

The evaluator therefore returns a failure result with ``unsupported: true``
so that harnesses can recognise the task; the interface the paper expects from
a candidate is documented in initial_program.py and README.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

SUITE_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(SUITE_LIB) not in sys.path:
    sys.path.insert(0, str(SUITE_LIB))

from autoresearch_suite import runtime  # noqa: E402

DIRECTION = "maximize"
CATEGORY = 'simulator'
REASON = 'Fitness requires a physics simulator or reinforcement-learning training loop (Isaac Gym) that is not bundled.'
REQUIRES = ["environment:Isaac Gym"]


def evaluate(program_path="initial_program.py"):
    return runtime.failure("unsupported in this suite: " + REASON, DIRECTION, unsupported=True, category=CATEGORY, requires=REQUIRES)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
