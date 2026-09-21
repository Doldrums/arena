"""Run ShinkaEvolve's original n=26 validator without its search dependencies."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile


def evaluate(candidate_path, *, checkout):
    source = Path(checkout) / "examples/circle_packing/evaluate.py"
    tree = ast.parse(source.read_text())
    names = {"adapted_validate_packing", "aggregate_circle_packing_metrics", "format_centers_string"}
    body = [node for node in tree.body if
            isinstance(node, (ast.Import, ast.ImportFrom)) and not (isinstance(node, ast.ImportFrom) and node.module == "shinka.core")
            or isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(source), "exec"), namespace)
    spec = importlib.util.spec_from_file_location("_shinka_candidate", candidate_path)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    output = candidate.run_packing()
    valid, message = namespace["adapted_validate_packing"](output)
    if not valid:
        raise ValueError(message)
    with tempfile.TemporaryDirectory(prefix="shinka-circle-") as directory:
        metrics = namespace["aggregate_circle_packing_metrics"]([output], directory)
    return {"score": float(metrics["combined_score"]), "validity": True,
            "validation_scope": "original independent geometry validator, default tolerances",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "profile": "original_circle_packing_26"}
