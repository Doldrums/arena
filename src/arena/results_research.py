"""Publish only measured numeric observations from the native SCiEL observer.

This pure projection reads no files, contacts no services and executes no engine
or evaluator. Its output remains separate from canonical Arena evaluations.
The operator supplies a bounded, explicitly selected observer collection.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

from .observers.sciel.compat.measurement import validate_metric_context
from .registry import RegistryError

INPUT_SCHEMA = "arena.research-observer-input/1"
MAX_RUNS = 500
STATES = {"running", "paused", "stopped", "completed", "unknown"}
MEASUREMENTS = {"measured", "unknown", "failed", "invalid_penalty"}
WALL_SCOPE = "Elapsed since first recorded run start, including pauses"
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,95}(?:/[A-Za-z0-9][A-Za-z0-9_.+-]{0,95})?")
_HASH = re.compile(r"[a-f0-9]{64}")
_SECRET = re.compile(r"(?i)(?:sk-|arena_|gh[pousr]_|AKIA|eyJ|bearer|password|secret|token[=:])")
_DISPLAY_FIELDS = {"schema", "status", "value", "label", "units", "metric_sha256"}
_RUN_FIELDS = {"task_id", "task_name", "metric", "direction", "units", "protocol", "models",
               "state", "seed_score", "best_score", "total_wall_seconds", "to_best_wall_seconds",
               "wall_scope", "tokens", "source", "measurement_status"}


def _require(condition, message):
    if not condition:
        raise RegistryError("Research results: " + message)


def _fields(value, keys):
    _require(type(value) is dict and set(value) == set(keys), "unsupported object fields")


def _number(value, *, nullable=False, nonnegative=False):
    if value is None and nullable:
        return None
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    _require(finite and (not nonnegative or value >= 0), "invalid numeric measurement")
    return value


def _count(value):
    _require(type(value) is int and 0 <= value <= MAX_RUNS, "invalid run count")
    return value


def _identifier(value):
    _require(type(value) is str and len(value) <= 192 and bool(_IDENTIFIER.fullmatch(value))
             and not _SECRET.search(value), "invalid public identifier")
    return value


def _models(value):
    _require(type(value) is list and len(value) <= 32, "invalid actual model list")
    checked = [_identifier(model) for model in value]
    _require(len(set(checked)) == len(checked), "duplicate actual model")
    return sorted(checked)


def _task_title(task):
    return {"oe/circle_packing": "Circle packing in a unit square",
            "oe/heilbronn_triangle": "Heilbronn triangle",
            "oe/function_minimization_oracle": "Function minimization oracle"}.get(
                task, task.rsplit("/", 1)[-1].replace("_", " ").replace("-", " ").capitalize())


def _display(value, metric, label, units):
    _fields(value, _DISPLAY_FIELDS)
    _require(value["schema"] == "sciel-metric-display/1" and type(value["status"]) is str
             and value["status"] in MEASUREMENTS,
             "invalid native measurement status")
    _require(value["metric_sha256"] == metric["sha256"] and value["label"] == label
             and value["units"] == units, "native measurement does not match its metric")
    measured = value["status"] == "measured"
    _require(measured == (value["value"] is not None), "inconsistent native measurement")
    return _number(value["value"], nullable=True)


def _wall(value, scope):
    value = _number(value, nullable=True, nonnegative=True)
    # Only this known elapsed-time scope is publishable. Other clocks are not
    # silently relabelled, and missing time is not a zero-duration experiment.
    _require(scope is None or type(scope) is str, "invalid wall-time scope")
    return value if scope == WALL_SCOPE else None


def build_results_research(payload):
    """Project ``arena.research-observer-input/1`` into a public research section.

    Input rows contain only an observer identity, task/status, hash-bound native
    metric and seed/best displays, and actual-model/elapsed-time effort fields.
    Costs and tokens are deliberately unavailable: committed journal cost is not
    a complete provider bill, and observer effort does not supply a token ledger.
    """
    _fields(payload, {"schema", "source_generated_at", "total", "runs"})
    _require(payload["schema"] == INPUT_SCHEMA, "unsupported observer input schema")
    _require(_number(payload["source_generated_at"], nonnegative=True) > 0, "invalid source time")
    total = _count(payload["total"])
    _require(type(payload["runs"]) is list and len(payload["runs"]) == total,
             "incomplete observer collection")
    result = {"source_generated_at": payload["source_generated_at"], "total": total,
              "measured": 0, "runs": []}
    seen = set()
    for row in payload["runs"]:
        _fields(row, {"id", "task_id", "state", "metric", "seed", "best", "effort"})
        ident = row["id"]
        _require(type(ident) is str and 0 < len(ident) <= 128 and ident not in seen,
                 "duplicate or invalid observer identity")
        seen.add(ident)
        task = _identifier(row["task_id"])
        _require(type(row["state"]) is str and row["state"] in STATES, "invalid native run state")
        try:
            metric = validate_metric_context(row["metric"])
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            raise RegistryError("Research results: invalid native metric context") from None
        _require(metric["task_name"] == task and type(metric["task_hash"]) is str
                 and bool(_HASH.fullmatch(metric["task_hash"])), "unbound native task")
        semantics = metric["semantics"]
        _require(semantics["kind"] == "validity_gated_ratio",
                 "native physical metric semantics are unavailable")
        label = _identifier(semantics["numerator_case"])
        units = _identifier(semantics["numerator_units"])
        seed = _display(row["seed"], metric, label, units)
        best = _display(row["best"], metric, label, units)
        effort = row["effort"]
        _fields(effort, {"models", "total_wall_seconds", "total_wall_scope",
                         "to_best_wall_seconds", "to_best_wall_scope"})
        protocol = hashlib.sha256(json.dumps(
            ["arena.native-research-protocol/1", metric["task_hash"], metric["sha256"]],
            separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
        projected = dict(task_id=task, task_name=_task_title(task), metric=label,
            direction=metric["goal"], units=units, protocol=protocol,
            models=_models(effort["models"]), state=row["state"], seed_score=seed, best_score=best,
            total_wall_seconds=_wall(effort["total_wall_seconds"], effort["total_wall_scope"]),
            to_best_wall_seconds=_wall(effort["to_best_wall_seconds"], effort["to_best_wall_scope"])
                if best is not None else None,
            wall_scope="elapsed_including_pauses", tokens=None, source="native_observer",
            measurement_status=row["best"]["status"])
        result["runs"].append(projected)
        result["measured"] += best is not None
    result["runs"].sort(key=lambda row: (row["task_id"], row["protocol"], tuple(row["models"]),
                                        row["state"], str(row["best_score"]), str(row["seed_score"])))
    return validate_results_research(result)


def validate_results_research(value):
    """Validate the exact public allowlist without accepting private additions."""
    _fields(value, {"source_generated_at", "total", "measured", "runs"})
    _require(_number(value["source_generated_at"], nonnegative=True) > 0, "invalid source time")
    total, measured = _count(value["total"]), _count(value["measured"])
    _require(type(value["runs"]) is list and len(value["runs"]) == total and measured <= total,
             "invalid published coverage")
    observed = 0
    protocols = {}
    for row in value["runs"]:
        _fields(row, _RUN_FIELDS)
        task = _identifier(row["task_id"])
        _require(row["task_name"] == _task_title(task), "unreviewed task title")
        _identifier(row["metric"])
        _identifier(row["units"])
        _require(row["direction"] == "maximize", "unsupported native metric direction")
        _require(type(row["protocol"]) is str and bool(_HASH.fullmatch(row["protocol"])),
                 "invalid published protocol")
        identity = (task, row["metric"], row["direction"], row["units"])
        previous = protocols.setdefault(row["protocol"], identity)
        _require(identity == previous, "inconsistent protocol labels")
        _require(_models(row["models"]) == row["models"], "unordered actual models")
        _require(type(row["state"]) is str and row["state"] in STATES
                 and type(row["measurement_status"]) is str and row["measurement_status"] in MEASUREMENTS,
                 "invalid published observation status")
        _number(row["seed_score"], nullable=True)
        best = _number(row["best_score"], nullable=True)
        _require((row["measurement_status"] == "measured") == (best is not None),
                 "inconsistent measured result")
        total_wall = _number(row["total_wall_seconds"], nullable=True, nonnegative=True)
        best_wall = _number(row["to_best_wall_seconds"], nullable=True, nonnegative=True)
        _require(best is not None or best_wall is None, "time to an unmeasured best")
        if total_wall is not None and best_wall is not None:
            _require(best_wall <= total_wall, "time to best exceeds total elapsed time")
        _require(row["wall_scope"] == "elapsed_including_pauses" and row["tokens"] is None
                 and row["source"] == "native_observer", "unsupported effort or evidence claim")
        observed += best is not None
    _require(observed == measured, "inconsistent measured coverage")
    return value
