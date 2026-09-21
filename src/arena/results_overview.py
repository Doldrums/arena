"""Explicitly published, read-only result aggregates; no control service access.

The operator supplies a private results response to the exporter. Only the
allowlisted measurements below cross the publication boundary. HTTP reads an
already published snapshot and never launches, scans or imports experiments.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math
import re
from statistics import median
import time

from .registry import RegistryError, _json, resolve_registry_root

SCHEMA = "arena.results-overview/1"
MAX_RUNS = 500
_IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}")
_METRIC = re.compile(r"[A-Za-z][A-Za-z0-9_. -]{0,63}")
_HASH = re.compile(r"[a-fA-F0-9]{64}")
_SECRET = re.compile(r"(?i)(?:sk-|arena_|gh[pousr]_|AKIA|eyJ|bearer|password|secret|token[=:])")
STATES = {"queued", "preparing", "running", "completed", "failed", "cancelled", "blocked"}
ACTIVE = {"queued", "preparing", "running"}
NOTES = [
    "Published snapshot of bounded integration pilots, not paper reproductions.",
    "Scores compare only within the same immutable task and evaluator cohort. Models, search procedures and budgets may still differ.",
    "Failed and cancelled runs retain their recorded evidence. Missing measurements are not zero scores.",
    "Tokens describe ended runs with complete recorded provider ledgers; they are not billed cost. Wall time is elapsed run time.",
    "Distinct valid programs are deduplicated by source identity and include seeds; only the count is published.",
    "Native results retain each framework's task and metric. They are not canonical evaluator scores or a ranking across systems or protocols.",
]


def require(condition, message):
    if not condition:
        raise RegistryError("Results overview: " + message)


def object_fields(value, keys):
    require(type(value) is dict and set(value) == set(keys), "unsupported object fields")


def integer(value):
    require(type(value) is int and 0 <= value <= 10**12, "invalid count")
    return value


def number(value, *, nullable=False, nonnegative=False):
    if value is None and nullable:
        return None
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    require(valid and (not nonnegative or value >= 0), "invalid measurement")
    return value


def identifier(value, *, metric=False):
    require(type(value) is str and bool((_METRIC if metric else _IDENT).fullmatch(value))
            and not _SECRET.search(value), "invalid public identifier")
    return value


def task_title(task_id):
    # Descriptions and user-provided labels never cross the publication boundary.
    return task_id.replace("-", " ").replace("_", " ").capitalize()


def state_counts(states):
    counts = Counter(states)
    return dict(runs=sum(counts.values()), completed=counts["completed"],
                active=sum(counts[state] for state in ACTIVE), failed=counts["failed"],
                cancelled=counts["cancelled"], other=counts["blocked"])


def native_measurement(native, *, system, model, state, wall, tokens, token_complete):
    """Publish scalar or paired outcomes only after the native API's integrity gate.

    The API verifies artifact bytes. Its nonempty digest inventory is required
    here as evidence that the explicit native projector ran; digests themselves
    are private publication input and are never copied into the snapshot.
    """
    if native is None:
        return None
    require(type(native) is dict, "invalid native projection")
    if native.get("status") not in {"recorded", "partial"}:
        return None
    best = number(native.get("best_score"), nullable=True)
    population = native.get("population_objectives", [])
    require(type(population) is list, "invalid native population")
    if best is None and not population:
        # Partial failed integrity checks deliberately clear measured outcomes.
        return None
    require(native.get("scope") == "native", "native scope not recorded")
    hashes = native.get("evidence_hashes")
    require(type(hashes) is list and 0 < len(hashes) <= 256
            and all(type(value) is str and _HASH.fullmatch(value) for value in hashes)
            and len({value.lower() for value in hashes}) == len(hashes), "native evidence identity not recorded")
    task = identifier(native.get("task"))
    metric = identifier(native.get("metric"), metric=True)
    seed = number(native.get("seed_score"), nullable=True)
    objectives = native.get("objectives", [])
    require(type(objectives) is list, "invalid native objectives")
    public_objectives, public_population = [], []
    if population:
        require(best is None and seed is None and native.get("direction") is None,
                "paired native objectives must not invent a scalar score")
        require(2 <= len(objectives) <= 8 and 0 < len(population) <= 1000, "invalid paired native bound")
        for objective in objectives:
            require(type(objective) is dict, "invalid native objective")
            name = identifier(objective.get("metric"), metric=True)
            direction = objective.get("direction")
            require(direction in {"maximize", "minimize"}, "invalid native objective direction")
            public_objectives.append(dict(metric=name, direction=direction))
        names = [objective["metric"] for objective in public_objectives]
        require(len(set(names)) == len(names), "duplicate native objective")
        for candidate in population:
            require(type(candidate) is dict and set(names) <= set(candidate), "unpaired native objectives")
            public_population.append({name: number(candidate[name]) for name in names})
        direction = None
    else:
        require(best is not None and not objectives, "missing native scalar result")
        direction = native.get("direction")
        require(direction in {"maximize", "minimize"}, "invalid native score direction")
    return dict(system=system, model=model, state=state, task_id=task, task_name=task_title(task),
                metric=metric, direction=direction, seed_score=seed, best_score=best,
                wall_seconds=wall, total_tokens=tokens, usage_complete=token_complete,
                evidence_partial=native["status"] == "partial", objectives=public_objectives,
                population_objectives=public_population)


def build_results_overview(payload, *, generated_at=None, research=None):
    require(type(payload) is dict and payload.get("schema") == "arena.results/1", "unsupported source schema")
    rows = payload.get("runs")
    require(type(rows) is list and len(rows) <= MAX_RUNS, "invalid source run bound")
    total = integer(payload.get("total"))
    require(total >= len(rows) and type(payload.get("truncated")) is bool
            and payload["truncated"] == (total > len(rows)), "inconsistent source coverage")
    source_time = number(payload.get("generated_at"), nonnegative=True)
    published_time = number(time.time() if generated_at is None else generated_at, nonnegative=True)
    require(source_time > 0 and published_time >= source_time, "invalid publication time")
    systems, cohorts, known_ids, hashes = {}, {}, set(), set()
    native_results = []
    all_states, all_models, complete_tokens = [], set(), []
    validity = dict(evaluations=0, valid=0, invalid=0, unknown=0, unique_programs=0, hash_coverage_runs=0)
    wall_count = 0
    for row in rows:
        require(type(row) is dict, "invalid source run")
        ident = row.get("id")
        require(type(ident) is str and 0 < len(ident) <= 128 and ident not in known_ids, "duplicate or invalid source run")
        known_ids.add(ident)
        system, model = identifier(row.get("framework")), identifier(row.get("model"))
        state = row.get("state")
        require(type(state) is str and state in STATES, "unsupported source state")
        metrics = row.get("metrics")
        require(type(metrics) is dict, "missing source metrics")
        c, usage = metrics.get("canonical"), metrics.get("usage")
        require(type(c) is dict and type(usage) is dict, "invalid source measurements")
        values = {key: integer(c.get(key)) for key in ("evaluations", "valid", "invalid", "unknown")}
        require(values["evaluations"] == values["valid"] + values["invalid"] + values["unknown"], "inconsistent evaluation counts")
        for key, value in values.items():
            validity[key] += value
        source_hashes = c.get("valid_candidate_hashes")
        if source_hashes is not None:
            require(type(source_hashes) is list and len(source_hashes) <= values["valid"]
                    and all(type(value) is str and _HASH.fullmatch(value) for value in source_hashes), "invalid candidate identities")
            require(len({value.lower() for value in source_hashes}) == len(source_hashes), "duplicate candidate identities")
            hashes.update(value.lower() for value in source_hashes)
            if values["evaluations"]:
                validity["hash_coverage_runs"] += 1
        wall = number(metrics.get("wall_seconds"), nullable=True, nonnegative=True)
        wall_count += wall is not None
        require(type(usage.get("complete")) is bool, "invalid usage completeness")
        tokens = usage.get("total_tokens")
        if tokens is not None:
            integer(tokens)
        token_complete = usage["complete"] and state in {"completed", "failed", "cancelled"} and tokens is not None
        if token_complete:
            complete_tokens.append(tokens)
        else:
            tokens = None
        published_native = native_measurement(metrics.get("native"), system=system, model=model,
            state=state, wall=wall, tokens=tokens, token_complete=token_complete)
        if published_native is not None:
            native_results.append(published_native)
        bucket = systems.setdefault(system, dict(states=[], models=set(), canonical_runs=0,
                                                valid=0, invalid=0, unknown=0, tokens=[]))
        bucket["states"].append(state)
        bucket["models"].add(model)
        bucket["canonical_runs"] += values["evaluations"] > 0
        for key in ("valid", "invalid", "unknown"):
            bucket[key] += values[key]
        if token_complete:
            bucket["tokens"].append(tokens)
        all_states.append(state)
        all_models.add(model)
        cohort = c.get("cohort")
        seed = number(c.get("seed_score"), nullable=True)
        best = number(c.get("best_score"), nullable=True)
        if cohort is None:
            require(seed is None and best is None, "score without evaluator identity")
            continue
        require(type(cohort) is str and bool(_HASH.fullmatch(cohort)), "invalid evaluator identity")
        task, metric, direction = identifier(c.get("task_id")), identifier(c.get("metric"), metric=True), c.get("direction")
        require(direction in {"maximize", "minimize"}, "invalid score direction")
        key = (cohort.lower(), task, metric, direction)
        group = cohorts.setdefault(key, dict(cohort=cohort.lower(), task_id=task, task_name=task_title(task),
                                            metric=metric, direction=direction, points=[]))
        group["points"].append(dict(system=system, model=model, state=state, seed_score=seed, best_score=best,
                                    wall_seconds=wall, total_tokens=tokens, usage_complete=token_complete,
                                    evidence_partial=c.get("status") != "recorded" or values["unknown"] > 0))
    validity["unique_programs"] = len(hashes) if validity["hash_coverage_runs"] else None
    result = dict(schema=SCHEMA, generated_at=published_time, source_generated_at=source_time,
                  total=total, loaded=len(rows), truncated=payload["truncated"],
                  summary={**state_counts(all_states), "systems": len(systems), "models": len(all_models)},
                  validity=validity, resources=dict(complete_token_runs=len(complete_tokens),
                  median_tokens=median(complete_tokens) if complete_tokens else None, wall_time_runs=wall_count),
                  systems=[], cohorts=[], native_results=native_results,
                  research=deepcopy(research), notes=list(NOTES))
    for system, bucket in sorted(systems.items()):
        result["systems"].append(dict(system=system, **state_counts(bucket["states"]),
            models=sorted(bucket["models"]), canonical_runs=bucket["canonical_runs"],
            valid=bucket["valid"], invalid=bucket["invalid"], unknown=bucket["unknown"],
            complete_token_runs=len(bucket["tokens"]), median_tokens=median(bucket["tokens"]) if bucket["tokens"] else None))
    for key, group in sorted(cohorts.items()):
        group["points"].sort(key=lambda point: (point["system"], point["model"], point["state"], str(point["best_score"])))
        result["cohorts"].append(group)
    validate_results_overview(result)
    return result


def validate_results_overview(value):
    """Reject unreviewed fields rather than making a private payload publishable."""
    object_fields(value, ("schema", "generated_at", "source_generated_at", "total", "loaded", "truncated", "summary", "validity", "resources", "systems", "cohorts", "native_results", "research", "notes"))
    require(value["schema"] == SCHEMA, "unsupported published schema")
    require(number(value["generated_at"]) >= number(value["source_generated_at"]) > 0, "invalid publication time")
    require(integer(value["total"]) >= integer(value["loaded"]) <= MAX_RUNS, "invalid published coverage")
    require(type(value["truncated"]) is bool and value["truncated"] == (value["total"] > value["loaded"]), "invalid truncation flag")
    summary = value["summary"]
    object_fields(summary, ("runs", "completed", "active", "failed", "cancelled", "other", "systems", "models"))
    for count in summary.values():
        integer(count)
    require(summary["runs"] == value["loaded"] == sum(summary[key] for key in ("completed", "active", "failed", "cancelled", "other")), "invalid summary counts")
    valid = value["validity"]
    object_fields(valid, ("evaluations", "valid", "invalid", "unknown", "unique_programs", "hash_coverage_runs"))
    for key, count in valid.items():
        if key != "unique_programs" or count is not None:
            integer(count)
    require(valid["evaluations"] == valid["valid"] + valid["invalid"] + valid["unknown"], "invalid validity counts")
    require(valid["hash_coverage_runs"] <= summary["runs"] and (valid["unique_programs"] is None or valid["unique_programs"] <= valid["valid"]), "invalid identity coverage")
    resources = value["resources"]
    object_fields(resources, ("complete_token_runs", "median_tokens", "wall_time_runs"))
    for key in ("complete_token_runs", "wall_time_runs"):
        require(integer(resources[key]) <= summary["runs"], "invalid resource coverage")
    number(resources["median_tokens"], nullable=True, nonnegative=True)
    require((resources["median_tokens"] is not None) == (resources["complete_token_runs"] > 0), "invalid token summary")
    require(type(value["systems"]) is list and len(value["systems"]) == summary["systems"], "invalid system list")
    seen, models, summed = set(), set(), Counter()
    for system in value["systems"]:
        object_fields(system, ("system", "runs", "completed", "active", "failed", "cancelled", "other", "models", "canonical_runs", "valid", "invalid", "unknown", "complete_token_runs", "median_tokens"))
        ident = identifier(system["system"])
        require(ident not in seen, "duplicate system")
        seen.add(ident)
        require(type(system["models"]) is list and 0 < len(system["models"]) <= system["runs"], "invalid model list")
        require(len(set(system["models"])) == len(system["models"]), "duplicate model")
        models.update(identifier(model) for model in system["models"])
        for key, count in system.items():
            if key not in {"system", "models", "median_tokens"}:
                integer(count)
                summed[key] += count
        require(system["runs"] == sum(system[key] for key in ("completed", "active", "failed", "cancelled", "other")), "invalid system states")
        require(system["canonical_runs"] <= system["runs"] and system["complete_token_runs"] <= system["runs"], "invalid system coverage")
        number(system["median_tokens"], nullable=True, nonnegative=True)
        require((system["median_tokens"] is not None) == (system["complete_token_runs"] > 0), "invalid system token summary")
    require(len(models) == summary["models"] and all(summed[key] == summary[key] for key in ("runs", "completed", "active", "failed", "cancelled", "other")), "inconsistent systems")
    require(all(summed[key] == valid[key] for key in ("valid", "invalid", "unknown")) and summed["complete_token_runs"] == resources["complete_token_runs"], "inconsistent measurements")
    require(type(value["cohorts"]) is list and len(value["cohorts"]) <= summary["runs"], "invalid cohorts")
    cohort_keys, point_count = set(), 0
    for group in value["cohorts"]:
        object_fields(group, ("cohort", "task_id", "task_name", "metric", "direction", "points"))
        require(type(group["cohort"]) is str and bool(_HASH.fullmatch(group["cohort"])), "invalid cohort digest")
        identifier(group["task_id"])
        identifier(group["metric"], metric=True)
        require(group["direction"] in {"maximize", "minimize"} and group["task_name"] == task_title(group["task_id"]), "invalid cohort labels")
        key = tuple(group[field] for field in ("cohort", "task_id", "metric", "direction"))
        require(key not in cohort_keys, "duplicate cohort")
        cohort_keys.add(key)
        require(type(group["points"]) is list and 0 < len(group["points"]) <= summary["runs"], "invalid point list")
        for point in group["points"]:
            object_fields(point, ("system", "model", "state", "seed_score", "best_score", "wall_seconds", "total_tokens", "usage_complete", "evidence_partial"))
            require(point["system"] in seen and point["model"] in models and point["state"] in STATES, "invalid point identity")
            for field in ("seed_score", "best_score", "wall_seconds"):
                number(point[field], nullable=True, nonnegative=field == "wall_seconds")
            if point["total_tokens"] is not None:
                integer(point["total_tokens"])
            require(type(point["usage_complete"]) is bool and type(point["evidence_partial"]) is bool
                    and point["usage_complete"] == (point["total_tokens"] is not None), "invalid point coverage")
            point_count += 1
    require(point_count <= summary["runs"], "too many published points")
    require(type(value["native_results"]) is list and len(value["native_results"]) <= summary["runs"], "invalid native result bound")
    model_sets = {system["system"]: set(system["models"]) for system in value["systems"]}
    native_system_counts = Counter()
    for native in value["native_results"]:
        object_fields(native, ("system", "model", "state", "task_id", "task_name", "metric", "direction", "seed_score", "best_score",
                              "wall_seconds", "total_tokens", "usage_complete", "evidence_partial", "objectives", "population_objectives"))
        require(type(native["system"]) is str and native["system"] in model_sets
                and type(native["model"]) is str and native["model"] in model_sets[native["system"]]
                and type(native["state"]) is str and native["state"] in STATES, "invalid native public identity")
        identifier(native["task_id"])
        identifier(native["metric"], metric=True)
        require(native["task_name"] == task_title(native["task_id"]), "unreviewed native task label")
        for field in ("seed_score", "best_score", "wall_seconds"):
            number(native[field], nullable=True, nonnegative=field == "wall_seconds")
        if native["total_tokens"] is not None:
            integer(native["total_tokens"])
        require(type(native["usage_complete"]) is bool and type(native["evidence_partial"]) is bool
                and native["usage_complete"] == (native["total_tokens"] is not None)
                and (not native["usage_complete"] or native["state"] in {"completed", "failed", "cancelled"}), "invalid native resource coverage")
        objectives, population = native["objectives"], native["population_objectives"]
        require(type(objectives) is list and type(population) is list, "invalid native objective arrays")
        if population:
            require(2 <= len(objectives) <= 8 and len(population) <= 1000
                    and native["best_score"] is None and native["seed_score"] is None and native["direction"] is None,
                    "invalid paired native measurement")
            names = []
            for objective in objectives:
                object_fields(objective, ("metric", "direction"))
                names.append(identifier(objective["metric"], metric=True))
                require(objective["direction"] in {"maximize", "minimize"}, "invalid published objective direction")
            require(len(set(names)) == len(names), "duplicate published native objective")
            for candidate in population:
                object_fields(candidate, names)
                for measurement in candidate.values():
                    number(measurement)
        else:
            require(not objectives and native["best_score"] is not None and native["direction"] in {"maximize", "minimize"},
                    "invalid native scalar measurement")
        native_system_counts[native["system"]] += 1
    require(all(native_system_counts[system["system"]] <= system["runs"] for system in value["systems"]), "too many native system results")
    if value["research"] is not None:
        # Independently published observer measurements. These are never added
        # to control counts, native pilot results or canonical evaluator cohorts.
        from .results_research import validate_results_research
        validate_results_research(value["research"])
        require(value["research"]["source_generated_at"] <= value["generated_at"], "research snapshot is newer than publication")
    require(value["notes"] == NOTES, "unreviewed notes")
    return value


def get_results_overview(root=None):
    path = resolve_registry_root(root) / "results-overview.json"
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024 * 1024,
            "published snapshot unavailable")
    return validate_results_overview(_json(path))
