"""Stop the pinned EoH-S singleton retry loop with an explicit partial result."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path

from .eohs_gateway import DATASET, MODELS, configuration
from ._tls import configure_ca

COMMIT = "8310b056ab0d4ea83d194f1d9e8c7873c0a3b892"
SOURCE_HASHES = {
    "code/llm4ad/method/eohs/eohs.py": "96ca5020c831ed0f4a87fba67f1c8346f62d56fe18d9cb4faee03580fda81b2f",
    "code/llm4ad/method/eohs/population.py": "242a2b4813d529ff75214dd6a0d2e8a348bf9cfae14e15e277815b1887c3063b",
}
PAIR_ERROR = "Need at least 2 valid functions to select a pair"


class NativePairUnavailable(BaseException):
    """Escape the native catch-and-retry loop without inventing a selection."""


def verify_source(root):
    for name, expected in SOURCE_HASHES.items():
        path = root / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("EoH-S guard source mismatch: " + name)


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def valid_score(score):
    # Exactly the pinned select_complementary_pair eligibility predicate.
    return score is not None and ((isinstance(score, list) and not any(math.isinf(x) for x in score))
                                  or (not isinstance(score, list) and not math.isinf(score)))


def recorded_score(value):
    if isinstance(value, list):
        return [recorded_score(item) for item in value]
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return {"native_nonfinite": str(value)}
    return value


class GuardRecord:
    def __init__(self, path):
        self.path = path
        self.event = None
        self.status = "prepared"

    def save(self):
        write_json(self.path, {"schema": "arena.eohs-selection-guard/2", "status": self.status,
            "native_completed": self.status == "native_returned", "canonical_evaluation": False,
            "event": self.event,
            "scope": "Stop only an impossible native complementary-pair selection. Native scores, duplicate handling, population management and selection are unchanged."})


@contextmanager
def guard_native_selection(population_class, method_class, record):
    original_pair = population_class.select_complementary_pair
    original_loop = method_class._iteratively_use_eoh_operator

    def select_pair(population):
        try:
            return original_pair(population)
        except ValueError as error:
            if str(error) != PAIR_ERROR:
                raise
            valid = [f for f in population.population if valid_score(f.score)]
            if len(valid) >= 2:
                raise
            record.status = "partial_insufficient_population"
            record.event = {"native_error": str(error), "generation": population.generation,
                "population_size": len(population.population), "valid_population_size": len(valid),
                "population": [{"code_sha256": hashlib.sha256(str(f).encode()).hexdigest(),
                                "native_score": recorded_score(f.score)} for f in population.population]}
            record.save()
            raise NativePairUnavailable(str(error)) from error

    def run_loop(method, *args, **kwargs):
        try:
            return original_loop(method, *args, **kwargs)
        except NativePairUnavailable:
            # Native sampling uses Thread, whose exceptions do not propagate to
            # run(). Persist the stop and let its normal join finish; main then
            # returns 75. Release the idle evaluator just as the native loop does.
            record.event["registered_samples"] = method._tot_sample_nums
            record.save()
            method._evaluation_executor.shutdown(cancel_futures=True)
            return None

    population_class.select_complementary_pair = select_pair
    method_class._iteratively_use_eoh_operator = run_loop
    try:
        yield
    finally:
        population_class.select_complementary_pair = original_pair
        method_class._iteratively_use_eoh_operator = original_loop


def execute_native(method, population_class, method_class, record):
    record.status = "running"
    record.save()
    try:
        with guard_native_selection(population_class, method_class, record):
            method.run()
    except BaseException:
        record.status = "native_error"
        record.save()
        raise
    if record.event is not None:
        return 75
    record.status = "native_returned"
    record.save()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--samples", type=int, choices=[8], default=8)
    parser.add_argument("--tls-ca", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    verify_source(Path.cwd())
    configure_ca(args.tls_ca)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(output / ".matplotlib")
    dataset = Path(DATASET).absolute()
    kwargs = configuration(args.model, output, dataset, args.samples)
    write_json(output / "provider-seam-v2.json", {
        "schema": "arena.native-provider-seam/2", "framework": "eoh-s-gateway-v2",
        "source_commit": COMMIT, "source_hashes": SOURCE_HASHES, "model": args.model,
        "endpoint": "https://127.0.0.1:8790/v1", "canonical_evaluation": False,
        "dataset_path": DATASET, "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "max_registered_samples": 8, "max_generations": 4, "population": 2,
        "evaluation_concurrency": 1, "numeric_threads": 1,
        "pilot_hook": "Exit 75 with partial_insufficient_population when native complementary selection cannot choose two valid functions; no fallback, extra proposals or padded population.",
        "provider_controls_unenforced": ["temperature", "top_p", "max_tokens"],
        "limits": "Native parse/transport retries remain native; outer wall timeout remains authoritative. Native return is distinct from scientific improvement."})
    from llm4ad.method.eohs import EoHS
    from llm4ad.method.eohs.population import Population
    return execute_native(EoHS(**kwargs), Population, EoHS, GuardRecord(output / "selection-guard-v2.json"))


if __name__ == "__main__":
    raise SystemExit(main())
