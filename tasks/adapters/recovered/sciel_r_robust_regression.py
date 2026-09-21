"""Explicit CSV transport repair for the pinned SCiEL R example.

The original scientific data generator, R candidate, metrics, weighting and
efficiency bonus are retained. Only script/file transport and per-case temporary
file isolation change. This is a repository repair, not an upstream revision.
"""

import hashlib
from pathlib import Path
import shutil
import sys
import types


def repaired_source(source):
    """Apply narrowly checked transport edits, leaving scoring code untouched."""
    csv_start = source.index("            # Save test data to temporary CSV files")
    csv_end = source.index("            # Run the R script", csv_start)
    csv = source[csv_start:csv_end]
    source = source[:csv_start] + source[csv_end:]
    marker = "            # Create a temporary R script that sources the program and runs it"
    if source.count(marker) != 1:
        raise ValueError("The original R evaluator transport structure changed")
    source = source.replace(marker, "            case_directory = tempfile.TemporaryDirectory(prefix='sciel-r-case-')\n" + csv + marker)
    replacements = {
        'source("{program_path}")': 'source({json.dumps(str(Path(program_path).resolve()))})',
        'read.csv("{X}", header=FALSE)': 'read.csv("{X_file.name}", header=FALSE)',
        'read.csv("{y}", header=FALSE)': 'read.csv("{y_file.name}", header=FALSE)',
        'suffix=".r", delete=False': 'suffix=".r", delete=False, dir=case_directory.name',
        'suffix=".csv", delete=False': 'suffix=".csv", delete=False, dir=case_directory.name',
    }
    for old, new in replacements.items():
        expected = 2 if 'suffix=".csv"' in old else 1
        if source.count(old) != expected:
            raise ValueError(f"The original R evaluator transport marker changed: {old}")
        source = source.replace(old, new)
    cleanup = '                    os.unlink(os.path.join(os.path.dirname(test_script), "results.json"))'
    if source.count(cleanup) != 1:
        raise ValueError("The original R evaluator cleanup structure changed")
    return source.replace(cleanup, cleanup + "\n                case_directory.cleanup()")


async def evaluate(candidate_path, *, checkout, expected_source_sha256):
    if not shutil.which("Rscript"):
        raise RuntimeError("Rscript is required; install R and its jsonlite package before evaluating the repaired R task")
    source_path = Path(checkout).resolve() / "examples/r_robust_regression/evaluator.py"
    raw = source_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_source_sha256:
        raise ValueError("Original SCiEL R evaluator differs from the registered source hash")
    sys.path[:0] = [str(Path(checkout).resolve() / "engine"), str(Path(checkout).resolve())]
    original = types.ModuleType("sciel_r_robust_regression_transport_repair")
    original.__file__ = str(source_path)
    exec(compile(repaired_source(raw.decode()), str(source_path) + " [CSV transport repair]", "exec"), original.__dict__)
    result = await original.evaluate(str(Path(candidate_path).resolve()))
    result.artifacts["repository_repair"] = {
        "changes": ["Create CSV files before rendering R script", "Pass CSV file paths", "Quote candidate path", "Isolate each case's temporary output"],
        "original_source_sha256": expected_source_sha256,
        "scoring_changed": False,
        "independent_verification": False,
    }
    # EvaluationResult.to_dict() drops artifacts in this SCiEL revision. Keep
    # them explicitly, including per-case errors and the repair provenance.
    return {"metrics": result.metrics, "artifacts": result.artifacts}
