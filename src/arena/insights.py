"""Deterministic scientific overview of catalog metadata, never task execution.

Domains are one primary application area per package; task types describe what
the candidate changes. They are separate, exhaustive partitions, not rankings.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from arena.registry import RegistryError, _json, resolve_registry_root, validate_catalog


def _require(condition, message):
    if not condition:
        raise RegistryError(message)


def canonical_digest(value):
    """SHA256 of UTF-8 JSON with sorted keys, compact separators, no NaN."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_taxonomy(taxonomy):
    _require(type(taxonomy) is dict and taxonomy.get("schema") == "arena.taxonomy/1", "Unsupported taxonomy schema")
    for group in ("domains", "task_types"):
        values = taxonomy.get(group)
        _require(type(values) is list and values, f"Missing {group}")
        ids = []
        for item in values:
            _require(type(item) is dict and set(item) == {"id", "label", "description", "why_it_matters"}, f"Invalid {group} definition")
            _require(all(type(value) is str and value.strip() for value in item.values()), f"Invalid {group} text")
            ids.append(item["id"])
        _require(len(set(ids)) == len(ids) and "unknown" in ids, f"Duplicate IDs or missing unknown in {group}")
    domains = {item["id"] for item in taxonomy["domains"]}
    types = {item["id"] for item in taxonomy["task_types"]}
    rules = taxonomy.get("rules")
    _require(type(rules) is list and bool(rules), "Missing classification rules")
    seen = set()
    for rule in rules:
        _require(type(rule) is dict and set(rule) == {"id", "match", "domain_id", "task_type_id", "rationale"}, "Invalid classification rule")
        _require(type(rule["id"]) is str and rule["id"] not in seen, "Duplicate rule ID")
        seen.add(rule["id"])
        _require(rule["domain_id"] in domains and rule["task_type_id"] in types, "Unknown classification target")
        _require(type(rule["rationale"]) is str and bool(rule["rationale"].strip()), "Missing rule rationale")
        match = rule["match"]
        _require(type(match) is dict and bool(match) and not set(match) - {"families", "task_ids", "id_prefixes", "paper_ids", "name_contains", "family_is_null", "fallback"}, "Invalid match selector")
        for key, value in match.items():
            if key in ("family_is_null", "fallback"):
                _require(value is True, "Boolean selectors must be true")
            else:
                _require(type(value) is list and bool(value) and all(type(v) is str and bool(v.strip()) for v in value), "Selectors require nonempty string lists")
                _require(len(set(value)) == len(value), "Duplicate selector values")
        _require("fallback" not in match or match == {"fallback": True}, "Fallback cannot have conditions")
    _require(rules[-1]["match"] == {"fallback": True} and
             sum(rule["match"].get("fallback", False) for rule in rules) == 1,
             "Exactly one final fallback rule required")
    _require(rules[-1]["domain_id"] == rules[-1]["task_type_id"] == "unknown", "Fallback must be unknown")
    _require(type(taxonomy.get("methodology")) is dict and bool(taxonomy["methodology"]), "Missing methodology")
    non_papers = taxonomy.get("non_paper_source_ids")
    _require(type(non_papers) is list and all(type(value) is str for value in non_papers)
             and len(set(non_papers)) == len(non_papers), "Invalid non-paper source IDs")
    return taxonomy


def _matches(task, match):
    """Conditions are AND; alternatives within one condition are OR."""
    for key, values in match.items():
        if key == "families" and task["family"] not in values:
            return False
        if key == "task_ids" and task["id"] not in values:
            return False
        if key == "id_prefixes" and not any(task["id"].startswith(v) for v in values):
            return False
        if key == "paper_ids" and not set(task["paper_ids"]).intersection(values):
            return False
        if key == "name_contains" and not any(v.casefold() in task["name"].casefold() for v in values):
            return False
        if key == "family_is_null" and task["family"] is not None:
            return False
    return True


def _percentages(counts, total):
    """Largest remainder at 0.1 percentage point; stable ties by definition order."""
    if not total:
        return [0.0] * len(counts)
    units = [count * 1000 // total for count in counts]
    order = sorted(range(len(counts)), key=lambda i: (-(counts[i] * 1000 % total), i))
    for index in order[:1000 - sum(units)]:
        units[index] += 1
    return [unit / 10 for unit in units]


def build_insights(catalog, taxonomy):
    validate_catalog(catalog)
    validate_taxonomy(taxonomy)
    tasks = sorted(catalog["tasks"], key=lambda task: task["id"])
    non_papers = set(taxonomy["non_paper_source_ids"])
    task_ids = {task["id"] for task in tasks}
    for rule in taxonomy["rules"]:
        _require(set(rule["match"].get("task_ids", [])) <= task_ids,
                 f"Rule {rule['id']} references absent task IDs")
    annotations = {}
    used_rules = Counter()
    for task in tasks:
        rule = next(rule for rule in taxonomy["rules"] if _matches(task, rule["match"]))
        used_rules[rule["id"]] += 1
        evidence = {"task_name": task["name"], "description": task["description"],
                    "family": task["family"], "paper_ids": task["paper_ids"], "metric": task["metric"]}
        annotations[task["id"]] = {"domain_id": rule["domain_id"], "task_type_id": rule["task_type_id"],
                                   "rule_id": rule["id"], "rationale": rule["rationale"], "evidence": evidence}
    total = len(tasks)
    def distribution(definitions, key):
        rows = []
        for definition in definitions:
            members = [task for task in tasks if annotations[task["id"]][key] == definition["id"]]
            # Prefer available definitions, then distinct families/source papers.
            examples, seen = [], set()
            for task in sorted(members, key=lambda t: (not t["executable"], t["id"])):
                group = task["family"] or tuple(task["paper_ids"])
                if group not in seen:
                    seen.add(group)
                    examples.append(task["id"])
                if len(examples) == 3:
                    break
            rows.append({**definition, "total": len(members),
                         "executable": sum(task["executable"] for task in members),
                         "unsupported": sum(not task["executable"] for task in members),
                         "paper_count": len({paper for task in members for paper in task["paper_ids"]} - non_papers),
                         "source_group_count": len({paper for task in members for paper in task["paper_ids"]}),
                         "family_count": len({task["family"] for task in members if task["family"] is not None}),
                         "representative_task_ids": examples})
        for row, percentage in zip(rows, _percentages([row["total"] for row in rows], total)):
            row["percentage"] = percentage
        return rows
    summary = {key: catalog["summary"][key] for key in ("task_count", "executable_count", "unsupported_count")}
    summary.update(unique_paper_count=len({paper for task in tasks for paper in task["paper_ids"]}),
                   source_group_count=len({paper for task in tasks for paper in task["paper_ids"]}),
                   corpus_paper_count=len({paper for task in tasks for paper in task["paper_ids"]} - non_papers),
                   family_count=len({task["family"] for task in tasks if task["family"] is not None}),
                   unknown_domain_count=sum(a["domain_id"] == "unknown" for a in annotations.values()),
                   unknown_task_type_count=sum(a["task_type_id"] == "unknown" for a in annotations.values()))
    coverage = []
    def item(ident, label, count, description):
        coverage.append({"id": ident, "label": label, "total": count,
                         "percentage": round(count * 100 / total, 1) if total else 0,
                         "description": description})
    item("executable", "Executable definitions", summary["executable_count"], "Packages with source-declared executable evaluators; environments and runtime are not verified by Arena.")
    item("unsupported", "Unsupported definitions", summary["unsupported_count"], "Catalogued packages whose source marks evaluation unsupported; they remain included in domain totals.")
    item("original", "Original protocol", catalog["summary"]["protocol_counts"]["original"], "Source labels the evaluator protocol original; this is not Arena conformance or runtime verification.")
    item("recreated_verified", "Source-declared verified reconstruction", catalog["summary"]["protocol_counts"]["recreated_verified"], "Source labels these reconstructions verified. Arena has not independently rerun that verification.")
    item("recreated", "Recreated protocol", catalog["summary"]["protocol_counts"]["recreated"], "Recreated evaluators without the source's recreated_verified designation.")
    item("recorded_contract", "Recorded I/O contract", sum(task["contract"] is not None for task in tasks), "Non-null problem.json contract text; may point to evaluator documentation rather than a complete machine-readable signature.")
    item("runtime_verified", "Arena runtime verification recorded", 0, "No package in this pinned catalog carries Arena runtime verification. This does not mean its evaluator fails.")
    return {"schema": "arena.insights/1", "catalog_digest": canonical_digest(catalog),
            "taxonomy_digest": canonical_digest(taxonomy), "sources": catalog["sources"],
            "denominator": {"unit": "task_package", "task_count": total}, "summary": summary,
            "domains": distribution(taxonomy["domains"], "domain_id"),
            "task_types": distribution(taxonomy["task_types"], "task_type_id"),
            "coverage": coverage, "task_annotations": annotations, "methodology": taxonomy["methodology"],
            "rule_usage": dict(sorted(used_rules.items()))}


def validate_insights(insights, catalog, taxonomy):
    """Recompute every membership and total: stale or hand-edited snapshots fail."""
    _require(type(insights) is dict and insights.get("schema") == "arena.insights/1", "Unsupported insights schema")
    _require(insights.get("catalog_digest") == canonical_digest(catalog), "Stale insights: catalog digest differs")
    _require(insights.get("taxonomy_digest") == canonical_digest(taxonomy), "Stale insights: taxonomy digest differs")
    expected = build_insights(catalog, taxonomy)
    _require(insights == expected, "Insights membership, evidence or aggregate totals differ from deterministic build")
    return insights


def get_insights(registry_root: str | Path | None = None):
    root = resolve_registry_root(registry_root)
    return validate_insights(_json(root / "insights.json"), _json(root / "catalog.json"),
                             _json(root / "taxonomy.json"))
