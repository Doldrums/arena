"""Shared runtime for suite evaluators: program loading, result envelopes, limits.

Every suite ``evaluator.py`` exposes ``evaluate(program_path) -> dict`` in the
SCiEL/OpenEvolve convention. The dictionary always contains:

``combined_score``  the number SCiEL maximizes (raw score for maximizing tasks,
                    its negation for minimizing tasks, ``FAILURE_SCORE`` when
                    the candidate is invalid or crashed);
``score``           the task's own metric in its own direction, or ``None``;
``direction``       ``"maximize"`` or ``"minimize"``;
``valid``           ``True`` when the evaluator's own checks accepted the
                    candidate, ``False`` when they rejected it, ``None`` when
                    the task has no independent validity notion;
``error``           a message when the candidate was rejected or crashed.

Extra fields are task specific. Nothing here calls a model or the network.
"""
from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import signal
import sys
import time
import traceback
from pathlib import Path

FAILURE_SCORE = -sys.float_info.max


class CandidateError(ValueError):
    """Raised when a candidate violates the task contract; recorded as invalid."""


class Deadline:
    """POSIX alarm-based deadline for candidate code (best effort, main thread only)."""

    def __init__(self, seconds):
        self.seconds = int(math.ceil(seconds)) if seconds else 0

    def __enter__(self):
        if self.seconds and hasattr(signal, "SIGALRM"):
            def handler(signum, frame):
                raise TimeoutError(f"candidate exceeded {self.seconds} s")
            self._previous = signal.signal(signal.SIGALRM, handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, *args):
        if self.seconds and hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            signal.signal(signal.SIGALRM, self._previous)
        return False


def load_program(program_path, name="candidate_program"):
    """Import a candidate file as a module, with its directory on sys.path."""
    path = Path(program_path).resolve()
    if not path.is_file():
        raise CandidateError(f"candidate file not found: {path}")
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition:
        raise CandidateError(message)


def finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def success(score, direction, *, valid=True, **extra):
    score = float(score)
    if not math.isfinite(score):
        return failure("evaluator produced a nonfinite score", direction, **extra)
    combined = score if direction == "maximize" else -score
    return {"combined_score": combined, "score": score, "direction": direction, "valid": valid, "error": None, **extra}


def failure(error, direction, **extra):
    return {"combined_score": FAILURE_SCORE, "score": None, "direction": direction, "valid": False, "error": str(error)[:2000], **extra}


def run(program_path, task, *, timeout=None):
    """Load the candidate and hand it to ``task(module) -> result``; never raises."""
    started = time.time()
    try:
        with Deadline(timeout):
            module = load_program(program_path)
            result = task(module)
    except CandidateError as error:
        result = failure(error, "maximize")
    except TimeoutError as error:
        result = failure(error, "maximize")
    except Exception as error:  # noqa: BLE001 - any crash of candidate or evaluator is a failed evaluation
        result = failure(f"{type(error).__name__}: {error}", "maximize", traceback=traceback.format_exc()[-1500:])
    result.setdefault("elapsed_seconds", round(time.time() - started, 6))
    return result


def main(evaluate, argv=None):
    """Standard ``__main__`` for suite evaluators: print JSON for the given program."""
    argv = list(sys.argv[1:] if argv is None else argv)
    program = argv[0] if argv else str(Path(__file__).with_name("initial_program.py"))
    result = evaluate(program)
    print(json.dumps(result, allow_nan=False, default=str))
    return 0 if result.get("valid") is not False and result.get("score") is not None else 1
