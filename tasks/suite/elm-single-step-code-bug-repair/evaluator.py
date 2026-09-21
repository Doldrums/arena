"""Single-step code bug repair (ELM).

Protocol: unsupported (llm_api).
Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the Single-step code bug repair benchmark. The suite embeds neither model calls nor the benchmark data.

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
CATEGORY = 'llm_api'
REASON = 'Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the Single-step code bug repair benchmark. The suite embeds neither model calls nor the benchmark data.'
REQUIRES = ["service:llm_api", "env:OPENROUTER_API_KEY", "dataset:Single-step code bug repair"]


def evaluate(program_path="initial_program.py"):
    return runtime.failure("unsupported in this suite: " + REASON, DIRECTION, unsupported=True, category=CATEGORY, requires=REQUIRES)


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
