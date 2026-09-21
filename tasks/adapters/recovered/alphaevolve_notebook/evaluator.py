"""Run the official AlphaEvolve result-notebook verification cells on a candidate.

The pinned ``google-deepmind/alphaevolve_results`` notebook publishes, for each
mathematical problem, a *data* cell that binds the discovered construction to a
named variable and a *verification* cell that checks the construction and
prints the resulting bound. This adapter executes those exact cells with the
notebook's data variable rebound to the candidate's construction:

1. The notebook file and every executed cell are checked against the SHA256
   digests recorded in ``problems.json``; any drift aborts the evaluation.
2. The candidate module is imported and ``construct()`` is called. Its return
   value is bound to the notebook variable(s) listed under
   ``candidate_variables`` (a tuple in that order when there are several).
3. The recorded cells are executed in order. Top-level assignments to the
   candidate variables are removed from the cell ASTs so the notebook's own
   data does not overwrite the candidate; everything else, including derived
   quantities such as ``convolution_2`` and all ``assert`` checks, runs
   unchanged. ``matplotlib`` is replaced by a no-op stub and functions named
   ``plot_*`` are neutralized, because plotting is not part of verification.
4. The score is the notebook's own result variable or expression.

A failed notebook assertion is reported as ``valid: false`` with the original
message and no score. The published value is echoed as ``published_value`` for
reference only; it is not a target and is never used to score.

``reference(checkout, problem)`` runs the same cells on the notebook's own data
and returns the published value, which the build script uses to cross-check
that the adapter reproduces the notebook's printed bounds.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
PROBLEMS_FILE = HERE / "problems.json"
NOTEBOOK = "mathematical_results.ipynb"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_problems() -> dict:
    return json.loads(PROBLEMS_FILE.read_text())


def _cells(checkout: Path, expected_notebook_sha: str) -> list:
    path = checkout / NOTEBOOK
    raw = path.read_bytes()
    if _sha256(raw) != expected_notebook_sha:
        raise ValueError("Pinned notebook bytes differ from the recorded SHA256; refusing to evaluate")
    return json.loads(raw)["cells"]


def _cell_source(cells: list, index: int, expected_sha: str) -> str:
    source = "".join(cells[index]["source"])
    if _sha256(source.encode()) != expected_sha:
        raise ValueError(f"Notebook cell {index} differs from its recorded SHA256")
    return source


def _strip_assignments(source: str, names: set[str], index: int):
    tree = ast.parse(source)
    kept = []
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id in names for t in targets):
            continue
        kept.append(node)
    tree.body = kept
    return compile(tree, f"<notebook cell {index}>", "exec")


class _NoOp:
    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return self

    def __iter__(self):
        return iter(())


def _install_matplotlib_stub() -> None:
    if "matplotlib" in sys.modules and not getattr(sys.modules["matplotlib"], "_alphaevolve_stub", False):
        return
    stub = types.ModuleType("matplotlib")
    stub._alphaevolve_stub = True
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot._alphaevolve_stub = True
    pyplot.__getattr__ = lambda name: _NoOp()
    stub.pyplot = pyplot
    stub.__getattr__ = lambda name: _NoOp()
    sys.modules["matplotlib"] = stub
    sys.modules["matplotlib.pyplot"] = pyplot


def _neutralize_plots(namespace: dict) -> None:
    for key, value in list(namespace.items()):
        if key.startswith("plot_") and callable(value):
            namespace[key] = _NoOp()


def _load_candidate(program_path: str):
    path = Path(program_path).resolve()
    spec = importlib.util.spec_from_file_location("alphaevolve_candidate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["alphaevolve_candidate"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "construct"):
        raise ValueError("Candidate must define construct()")
    return module.construct()


def _run(cells: list, spec: dict, bindings: dict | None) -> dict:
    """Execute the recorded cells; bindings rebinds candidate variables (None = notebook data)."""
    _install_matplotlib_stub()
    names = set(spec["candidate_variables"])
    namespace = {"__name__": "alphaevolve_notebook_verification"}
    if bindings is not None:
        namespace.update(bindings)
    with contextlib.redirect_stdout(sys.stderr):
        if bindings is None:
            # Reference mode only: large data cells that candidates never see.
            for index, expected in spec.get("reference_cells", []):
                exec(compile(_cell_source(cells, index, expected), f"<notebook cell {index}>", "exec"), namespace)  # noqa: S102
        for index, expected in spec["cells"]:
            source = _cell_source(cells, index, expected)
            code = _strip_assignments(source, names, index) if bindings is not None else compile(source, f"<notebook cell {index}>", "exec")
            exec(code, namespace)  # noqa: S102 - pinned, hash-checked notebook cells
            _neutralize_plots(namespace)
    if spec.get("result_variable"):
        value = namespace[spec["result_variable"]]
    else:
        value = eval(spec["result_expression"], namespace)  # noqa: S307 - recorded notebook expression
    return {"value": float(value), "namespace": namespace}


def _bind(spec: dict, construction) -> dict:
    names = spec["candidate_variables"]
    if len(names) == 1:
        return {names[0]: construction}
    if not isinstance(construction, (tuple, list)) or len(construction) != len(names):
        raise ValueError(f"construct() must return {len(names)} values in the order {names}")
    return dict(zip(names, construction))


def evaluate(program_path: str, checkout: str, problem: str) -> dict:
    problems = load_problems()
    if problem not in problems:
        raise ValueError(f"Unknown notebook problem: {problem}")
    spec = problems[problem]
    checkout_path = Path(checkout).resolve()
    result = {"problem": problem, "notebook": NOTEBOOK, "notebook_sha256": problems["_notebook_sha256"],
              "cells": [index for index, _ in spec["cells"]], "score_direction": spec["direction"],
              "published_value": spec["published_value"], "score": None, "valid": None}
    try:
        cells = _cells(checkout_path, problems["_notebook_sha256"])
        construction = _load_candidate(program_path)
        outcome = _run(cells, spec, _bind(spec, construction))
        value = outcome["value"]
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Verification produced a nonfinite value")
        result.update(score=value, valid=True)
    except AssertionError as error:  # a notebook verification check rejected the construction
        result.update(valid=False, error=f"Notebook verification failed: {error}")
    except Exception as error:  # noqa: BLE001 - report every failure as an invalid evaluation
        result.update(valid=False, error=f"{type(error).__name__}: {error}")
    return result


def reference(checkout: str, problem: str) -> float:
    problems = load_problems()
    spec = problems[problem]
    cells = _cells(Path(checkout).resolve(), problems["_notebook_sha256"])
    return _run(cells, spec, None)["value"]
