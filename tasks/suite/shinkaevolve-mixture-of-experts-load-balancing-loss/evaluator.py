"""Mixture-of-experts load balancing loss (ShinkaEvolve).

Protocol: unsupported (gpu).
The candidate is a load-balancing loss whose fitness is the perplexity of a mixture-of-experts model trained on GPU.

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
CATEGORY = 'gpu'
REASON = 'The candidate is a load-balancing loss whose fitness is the perplexity of a mixture-of-experts model trained on GPU.'
REQUIRES = ["hardware:gpu", "py:torch"]


def evaluate(program_path="initial_program.py"):
    return runtime.failure("unsupported in this suite: " + REASON, DIRECTION, unsupported=True, category=CATEGORY, requires=REQUIRES)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
