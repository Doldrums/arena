"""Run the original-author FunSearch pipeline with explicit provider seams.

Only an explicit invocation imports the pinned native implementation or a user
factory. Search, evaluation admission, island selection and resets remain native.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import math
from numbers import Integral, Real
from pathlib import Path
import sys
from types import ModuleType

from ._specialized import bounded_positive, load_factory, output_directory


class _SampleBudgetReached(Exception):
    pass


class _TraceLimitReached(Exception):
    pass


@contextmanager
def native_namespace(source: Path):
    """Resolve upstream's absolute imports from the isolated, pinned clone."""
    previous = {k: v for k, v in sys.modules.items()
                if k == "funsearch" or k.startswith("funsearch.")}
    for name in previous:
        del sys.modules[name]
    package = ModuleType("funsearch")
    package.__path__ = [str(source)]
    package.__package__ = "funsearch"
    sys.modules["funsearch"] = package
    try:
        yield importlib.import_module("funsearch.implementation.funsearch")
    finally:
        for name in list(sys.modules):
            if name == "funsearch" or name.startswith("funsearch."):
                del sys.modules[name]
        sys.modules.update(previous)


def _json_value(value):
    """Preserve native observations without inventing a score or validity."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else {"nonfinite": str(number)}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    raise ValueError("FunSearch inputs and observed scores must be JSON scalars or tuples")


def _scores(values):
    return [{"input": _json_value(key), "score": _json_value(value)}
            for key, value in values.items()]


def _program(value):
    if value is None:
        return None
    code = str(value)
    raw = code.encode("utf-8")
    # Final island leaders are bounded independently of the event stream.
    return {"code": raw[:65536].decode("utf-8", errors="replace"),
            "sha256": hashlib.sha256(raw).hexdigest(), "truncated": len(raw) > 65536}


class Trace:
    def __init__(self, path, byte_limit):
        self.file = path.open("x", encoding="utf-8")
        self.byte_limit = byte_limit
        self.bytes_written = 0
        self.events = 0

    def record(self, event, **payload):
        line = json.dumps({"event": event, **payload}, allow_nan=False) + "\n"
        size = len(line.encode("utf-8"))
        if self.bytes_written + size > self.byte_limit:
            raise _TraceLimitReached("Native event trace reached its configured byte limit")
        self.file.write(line)
        self.file.flush()
        self.bytes_written += size
        self.events += 1

    def close(self):
        self.file.close()


def run_native(native, specification, factory, config, output, max_samples, trace_bytes):
    """Install provider/observation wrappers and call native main exactly once."""
    required = {"draw_sample", "sandbox_factory", "inputs"}
    if (type(factory) is not dict or not required <= factory.keys()
            or set(factory) - required - {"programs_database"}
            or not callable(factory["draw_sample"])
            or not callable(factory["sandbox_factory"])):
        raise ValueError("Factory needs draw_sample, sandbox_factory, inputs and optional programs_database")
    inputs = factory["inputs"]
    if not isinstance(inputs, (list, tuple)) or not inputs or len(inputs) > 10000:
        raise ValueError("Factory inputs must contain 1 to 10000 native test inputs")
    for value in inputs:
        hash(value)  # Native scores use inputs as dictionary keys.
        _json_value(value)
    if len(set(inputs)) != len(inputs):
        raise ValueError("Duplicate native inputs would overwrite per-test scores")

    original_llm = native.sampler.LLM
    original_sandbox = native.evaluator.Sandbox
    original_database = native.programs_database.ProgramsDatabase
    databases = []
    counts = {"sample_calls": 0, "completed_samples": 0, "sandbox_calls": 0}
    trace = Trace(output / "native-trace.jsonl", trace_bytes)
    status = "error"
    error_type = None

    class BoundedLLM(original_llm):
        def _draw_sample(self, prompt):
            if counts["sample_calls"] >= max_samples:
                raise _SampleBudgetReached()
            trace.record("sample_request", index=counts["sample_calls"], prompt=prompt)
            counts["sample_calls"] += 1
            sample = factory["draw_sample"](prompt)
            if not isinstance(sample, str):
                raise ValueError("draw_sample must return a program continuation string")
            counts["completed_samples"] += 1
            trace.record("sample", index=counts["sample_calls"] - 1, continuation=sample)
            return sample

        def draw_samples(self, prompt):
            remaining = max_samples - counts["sample_calls"]
            if remaining <= 0:
                raise _SampleBudgetReached()
            # Keep native LLM.draw_samples, including the final partial batch.
            previous = self._samples_per_prompt
            self._samples_per_prompt = min(previous, remaining)
            try:
                return super().draw_samples(prompt)
            finally:
                self._samples_per_prompt = previous

    class ObservedSandbox:
        def __init__(self):
            self.delegate = factory["sandbox_factory"]()
            if not callable(getattr(self.delegate, "run", None)):
                raise ValueError("sandbox_factory must provide the native Sandbox.run interface")

        def run(self, program, function_to_run, test_input, timeout_seconds):
            trace.record("evaluation_request", index=counts["sandbox_calls"], program=program,
                         function=function_to_run, input=_json_value(test_input),
                         timeout_seconds=timeout_seconds)
            counts["sandbox_calls"] += 1
            result = self.delegate.run(program, function_to_run, test_input, timeout_seconds)
            if not isinstance(result, tuple) or len(result) != 2 or type(result[1]) is not bool:
                raise ValueError("Sandbox.run must return (native_output, boolean_runs_ok)")
            trace.record("evaluation", index=counts["sandbox_calls"] - 1,
                         native_output=_json_value(result[0]), runs_ok=result[1])
            return result

    class ObservedDatabase(original_database):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            databases.append(self)

        def get_prompt(self):
            if counts["sample_calls"] >= max_samples:
                raise _SampleBudgetReached()
            prompt = super().get_prompt()
            trace.record("database_prompt", island_id=int(prompt.island_id),
                         version_generated=int(prompt.version_generated), code=prompt.code)
            return prompt

        def _register_program_in_island(self, program, island_id, scores_per_test):
            super()._register_program_in_island(program, island_id, scores_per_test)
            trace.record("database_registration", island_id=int(island_id),
                         program=str(program), scores_per_test=_scores(scores_per_test))

    native.sampler.LLM = BoundedLLM
    native.evaluator.Sandbox = ObservedSandbox
    native.programs_database.ProgramsDatabase = ObservedDatabase
    try:
        native.main(specification, inputs, config)
        status = "returned"
    except _SampleBudgetReached:
        status = "sample_budget_reached"
    except _TraceLimitReached:
        status = "trace_limit_reached"
    except BaseException as exc:
        error_type = type(exc).__name__  # Provider messages can contain credentials.
        raise
    finally:
        native.sampler.LLM = original_llm
        native.evaluator.Sandbox = original_sandbox
        native.programs_database.ProgramsDatabase = original_database
        trace.close()
        leaders = []
        for database in databases:
            for index, program in enumerate(database._best_program_per_island):
                values = database._best_scores_per_test_per_island[index]
                leaders.append({"island_id": index, "program": _program(program),
                                "native_score": _json_value(database._best_score_per_island[index]),
                                "scores_per_test": None if values is None else _scores(values)})
        result = {"schema": "arena.funsearch-original/1", "canonical_evaluation": False,
                  "native_status": status, "error_type": error_type,
                  "max_samples": max_samples, **counts, "trace_events": trace.events,
                  "trace_bytes": trace.bytes_written, "island_leaders": leaders,
                  "limitations": ["Scores and runs_ok are supplied by the researcher's native sandbox.",
                                  "Native evaluator may register a program that succeeds on only some inputs.",
                                  "No canonical Arena fitness or universal validity is inferred."]}
        (output / "native-result.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    return 0 if status in {"sample_budget_reached", "returned"} else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factory", required=True)
    parser.add_argument("--specification", required=True)
    parser.add_argument("--max-samples", type=bounded_positive, required=True)
    parser.add_argument("--samples-per-prompt", type=bounded_positive, default=4)
    parser.add_argument("--trace-mib", type=int, choices=range(1, 257), default=32)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    path = Path(args.specification)
    if (path.is_absolute() or ".." in path.parts or path.is_symlink()
            or not path.resolve().is_relative_to(Path.cwd().resolve()) or not path.is_file()
            or path.stat().st_size > 1024 * 1024):
        raise ValueError("Specification must be a staged workspace file of at most 1 MiB")
    specification = path.read_text()
    with native_namespace(Path.cwd().resolve()) as native:
        factory = load_factory(args.factory)
        database_options = factory.get("programs_database", {})
        if type(database_options) is not dict:
            raise ValueError("programs_database must be native configuration keyword arguments")
        database_config = native.config_lib.ProgramsDatabaseConfig(**database_options)
        for field in ("num_islands", "functions_per_prompt", "cluster_sampling_temperature_period"):
            value = getattr(database_config, field)
            if type(value) is not int or not 1 <= value <= 10000:
                raise ValueError(f"Native {field} must be an integer from 1 to 10000")
        for field in ("reset_period", "cluster_sampling_temperature_init"):
            value = getattr(database_config, field)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Native {field} must be positive and finite")
        config = native.config_lib.Config(programs_database=database_config, num_samplers=1,
                                        num_evaluators=1, samples_per_prompt=args.samples_per_prompt)
        output = output_directory(args.output)
        if any((output / name).exists() for name in ("native-trace.jsonl", "native-result.json")):
            raise ValueError("Refusing to overwrite an earlier native FunSearch trace")
        return run_native(native, specification, factory, config, output, args.max_samples,
                          args.trace_mib * 1024 * 1024)


if __name__ == "__main__":
    raise SystemExit(main())
