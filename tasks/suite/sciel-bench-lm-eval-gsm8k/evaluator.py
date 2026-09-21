"""SCiEL: lm-evaluation-harness GSM8K adapter (SCiEL example driven by a command line, no evaluate() entry point).

The upstream example is a CLI driver (see README.upstream.md and the copied
files); it runs a prompt search against a model endpoint and grades with
lm-eval. Upstream command, from the example README:

    python3 examples/lm_eval/lm-eval.py --tasks gsm8k --limit 10 --iterations 1

This stub records that fact for harnesses; it makes no model call.
"""
from __future__ import annotations

import sys
from pathlib import Path

SUITE_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(SUITE_LIB) not in sys.path:
    sys.path.insert(0, str(SUITE_LIB))
from autoresearch_suite import runtime  # noqa: E402

COMMAND = 'python3 examples/lm_eval/lm-eval.py --tasks gsm8k --limit 10 --iterations 1'


def evaluate(program_path="initial_content_stub.txt"):
    return runtime.failure("command-line example; run the upstream driver: " + COMMAND, "maximize", command=COMMAND, requires=["service:llm_api", "py:lm_eval"])


if __name__ == "__main__":
    sys.exit(runtime.main(evaluate))
