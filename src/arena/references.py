"""Read and validate source-bound scientific reference metadata, offline.

This module never executes task code or promotes a source report to an Arena
evaluation result. All current-SOTA fields intentionally remain not_assessed.
"""
from __future__ import annotations

from .task_sources import source_url

import argparse
from collections import Counter
import json
import math

from .registry import (RegistryError, _json, _relative, _require, _text, _url,
                       _hash, _SHA256, get_catalog, resolve_registry_root)


def summarize(tasks):
    published = [task for task in tasks if any(a["kind"] == "published_reference" for a in task["anchors"])]
    baselines = [a for task in tasks for a in task["anchors"] if a["kind"] == "recorded_seed_baseline"]
    return {
        "task_count": len(tasks),
        "tasks_with_references": sum(bool(task["anchors"]) for task in tasks),
        "tasks_with_published_reference": len(published),
        "tasks_with_recorded_baseline": len(baselines),
        "tasks_without_numeric_reference": sum(not task["anchors"] for task in tasks),
        "tasks_without_published_reference": len(tasks) - len(published),
        "tasks_with_recorded_reproduction": sum(any(a["reproduction"] == "recorded_upstream" for a in task["anchors"]) for task in tasks),
        "arena_reproduced_references": 0,
        "valid_recorded_baselines": sum(a["validity"] is True for a in baselines),
        "validity_unknown_baselines": sum(a["validity"] is None for a in baselines),
        "verified_current_sota": 0,
        "current_sota_status": "not_assessed",
        "tasks_with_evaluation_size": sum(task["evaluation"]["case_count"] is not None for task in tasks),
        "evaluation_size_kinds": dict(sorted(Counter(task["evaluation"]["case_count_kind"] for task in tasks).items())),
    }


def _finite(value, label):
    _require(type(value) in (int, float) and math.isfinite(value), f"{label}: finite numeric value required")


def _evidence(source, binding):
    _require(type(source) is dict and {"url", "path", "sha256", "locator"} == source.keys(), "reference source: exact evidence fields required")
    _relative(source["path"], "source.path")
    _hash(source["sha256"], _SHA256, "source.sha256")
    _text(source["locator"], "source.locator")
    expected = source_url(binding, source["path"])
    _require(source["url"] == expected, "reference source: URL must bind the same repository revision and path")


def _evaluation(evaluation, binding):
    _require(type(evaluation) is dict, "evaluation: expected object")
    count = evaluation.get("case_count")
    _require(count is None or (type(count) is int and count > 0), "evaluation case_count: positive integer or null required")
    kinds = {"not_recorded", "declared_generated_instances", "declared_public_cases", "configured_cap",
             "candidate_construction", "named_initial_value_problem", "configured_default", "test_id_rows", "historical_smoke"}
    kind = evaluation.get("case_count_kind")
    _require(kind in kinds and ((count is None) == (kind == "not_recorded")), "evaluation count and kind disagree")
    if "source" in evaluation:
        _evidence(evaluation["source"], binding)
    if "evaluator_source" in evaluation:
        _evidence(evaluation["evaluator_source"], binding)
    if "splits" in evaluation:
        _require(set(evaluation["splits"]) == {"train", "test_id", "test_ood"}, "evaluation: distinct train/test-ID/OOD splits required")
        for split in evaluation["splits"].values():
            _require(type(split["row_count"]) is int and split["row_count"] > 0, "split: positive row count required")
            _evidence(split["source"], binding)
        _require(kind == "test_id_rows" and count == evaluation["splits"]["test_id"]["row_count"], "scored split size mismatch")


def validate_references(data, catalog):
    """Validate a complete inert snapshot against its offline catalog binding."""
    _require(type(data) is dict and data.get("schema") == "arena.references/1", "references schema: expected arena.references/1")
    binding = data.get("catalog_binding")
    _require(binding in catalog["sources"], "references: catalog revision/digest binding mismatch")
    _text(data.get("as_of"), "references.as_of")
    by_id = {task["id"]: task for task in catalog["tasks"]}
    _require(type(data.get("tasks")) is list, "references.tasks: expected list")
    seen = set()
    anchor_ids = set()
    for task in data["tasks"]:
        task_id = task.get("task_id")
        _require(task_id in by_id and task_id not in seen, "references: unknown or duplicate task")
        seen.add(task_id)
        declared = by_id[task_id]
        for field in ("metric", "direction", "protocol"):
            _require(task.get(field) == declared[field], f"references {task_id}: {field} differs from catalog")
        _evaluation(task["evaluation"], binding)
        _require(type(task.get("anchors")) is list, "anchors: expected list")
        kinds = set()
        for anchor in task["anchors"]:
            anchor_id = anchor.get("id")
            _require(type(anchor_id) is str and anchor_id.startswith(task_id + ":") and anchor_id not in anchor_ids, "anchor: unknown or duplicate id")
            anchor_ids.add(anchor_id)
            kind = anchor.get("kind")
            _require(kind in {"published_reference", "recorded_seed_baseline"} and kind not in kinds, "anchor: invalid or repeated kind")
            _require(anchor.get("code_verification") in (None, "historical_code_changed"),
                     "reference code verification cannot claim current execution")
            _require("historical_code" not in anchor or anchor.get("code_verification") == "historical_code_changed",
                     "historical code evidence requires an explicit verification state")
            _require(anchor.get("code_verification") is None or kind == "recorded_seed_baseline",
                     "historical code state applies only to recorded execution")
            kinds.add(kind)
            _finite(anchor.get("value"), "anchor.value")
            _require(anchor.get("metric") == "score", "anchor.metric: expected source report score, not combined_score or paper metric")
            _text(anchor.get("metric_label"), "anchor.metric_label")
            _require(anchor.get("direction") == task["direction"], "anchor.direction: task mismatch")
            _require(anchor.get("status") == "source_reference", "anchor.status: source reports are not Arena-verified results")
            _require(anchor.get("current_sota") == "not_assessed", "current SOTA cannot be established by this pinned snapshot")
            _require(anchor.get("automatic_comparison") is False, "reference metadata cannot authorize automatic metric comparison")
            _require(anchor.get("reproduction") in {"not_recorded", "recorded_upstream"}, "reference reproduction: unsupported claim")
            _require(anchor.get("validity") is None or anchor.get("validity") is True, "reference validity must be explicit true or unknown")
            _evidence(anchor["source"], binding)
            _evaluation(anchor["evaluation"], binding)
            for source in anchor.get("primary_sources", []):
                _url(source["url"], "primary source")
            if anchor["reproduction"] == "recorded_upstream":
                _require(kind == "published_reference" and task_id.startswith("alphaevolve-"), "recorded artifact check is bound only to the checked AlphaEvolve task")
                _evidence(anchor["reproduction_source"], binding)
            else:
                _require("reproduction_source" not in anchor, "unrecorded reproduction must not carry a receipt")
            if kind == "published_reference":
                _require(anchor["comparison"] == "same_task_protocol_reference" and anchor["score_space"] == "raw_task_metric", "published reference must bind raw task metric")
                _require(anchor["validity"] is None, "published reference is not a candidate validity result")
                _require(anchor["source"]["path"] == f"suite/{task_id}/problem.json" and anchor["source"]["locator"] == "#/parameters/published", "published anchor: exact source parameter required")
                _require(anchor["source"]["sha256"] == declared["contract_source"]["sha256"], "published anchor: problem digest differs from catalog contract")
            else:
                _require(anchor["comparison"] == "historical_smoke_only", "seed smoke cannot authorize benchmark comparisons")
                _require(anchor.get("recorded_status") == "ok", "seed baseline: successful recorded execution required")
                report_path = anchor["source"]["path"]
                _require(report_path in {"validation/suite-report.json", "validation/science-expansion-report.json"}, "baseline requires a reviewed pinned execution report")
                historical = anchor.get("code_verification") == "historical_code_changed"
                if historical:
                    _require(binding.get("kind") == "bundled" and report_path == "validation/science-expansion-report.json",
                             "changed historical code must identify an imported science receipt")
                    _require("execution_identity" not in anchor, "changed historical code cannot claim current execution identity")
                    old = anchor.get("historical_code", {})
                    _require(type(old) is dict, "historical code requires an identity object")
                    _require(old.get("code_verification") == "historical_code_changed"
                             and type(old.get("changed_paths")) is list and old["changed_paths"],
                             "changed historical code requires the affected artifact paths")
                    for path in old["changed_paths"]:
                        _relative(path, "historical artifact")
                    for key in ("candidate_sha256", "evaluator_sha256"):
                        _hash(old.get(key), _SHA256, key)
                    _evidence(old.get("import_source"), binding)
                    _require(old["import_source"]["path"] == "import-receipt.json"
                             and old["import_source"]["locator"] == "#/upstream_hashes",
                             "changed historical code requires the preserved import identities")
                    _require(anchor["validity"] is True, "science baseline requires explicit historical validity")
                elif report_path == "validation/science-expansion-report.json":
                    identity = anchor.get("execution_identity", {})
                    _require(type(identity) is dict, "science baseline requires an execution identity object")
                    _require(identity.get("source_execution") is True and identity.get("fixture_only") is False,
                             "science baseline requires source execution, not fixture-only validation")
                    _require(anchor["validity"] is True, "science baseline requires explicit validity")
                    for key, filename in (("candidate", "initial_program.py"), ("evaluator", "evaluator.py")):
                        source = identity.get(f"{key}_source")
                        _evidence(source, binding)
                        _hash(identity.get(f"{key}_sha256"), _SHA256, f"science baseline {key} digest")
                        _require(source["path"] == f"suite/{task_id}/{filename}" and source["sha256"] == identity[f"{key}_sha256"],
                                 f"science baseline {key} evidence mismatch")
                    _require(identity["evaluator_source"] == task["evaluation"]["evaluator_source"],
                             "science baseline evaluator differs from current task evaluator")
                else:
                    _require("execution_identity" not in anchor, "legacy suite report cannot claim checked expansion execution identity")
                if anchor.get("reported_combined_score") is not None:
                    _finite(anchor["reported_combined_score"], "anchor.reported_combined_score")
        _require(task.get("status") == ("source_reference" if task["anchors"] else "missing"), "reference status and anchors disagree")
        _require(task["protocol"] != "unsupported" or not task["anchors"], "unsupported package cannot have an executable reference")
    _require(seen == set(by_id), "references must explicitly cover every catalog task, including missing evidence")
    _require(data.get("summary") == summarize(data["tasks"]), "references summary does not match evidence")
    for highlight in data.get("highlights", []):
        _require(highlight.get("task_id") in by_id, "unknown reference highlight")
        _text(highlight.get("reason"), "highlight.reason")
    # Never distribute source workstation paths or credentials embedded in metadata.
    def walk(value):
        if isinstance(value, str):
            _text(value, "reference metadata")
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(key)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(data)
    return data


def get_references(registry_root=None):
    root = resolve_registry_root(registry_root)
    return validate_references(_json(root / "references.json"), get_catalog(root))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--registry")
    args = parser.parse_args()
    try:
        result = get_references(args.registry)
    except (RegistryError, KeyError, TypeError) as exc:
        parser.exit(1, f"Invalid references: {exc}\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
