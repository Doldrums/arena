"""Offline, read-only catalog contracts. This module never imports task code.

GitHub declarations and endpoint-ready JSON snapshots are reviewed together in
registry PRs. Availability describes the source package, not this host's runtime.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit


PROTOCOLS = ("original", "recreated_verified", "recreated", "unsupported")
CAPABILITIES = ("native_run", "canonical_evaluation", "pause", "resume")
_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_LOCAL = re.compile(r"(?:/Users/|/home/|/private/var/|/tmp/)[^\s\"'<>]*")


class RegistryError(ValueError):
    """A declaration or snapshot violates the catalog contract."""


def _require(condition, message):
    if not condition:
        raise RegistryError(message)


def _object(value, required, label, optional=()):
    _require(type(value) is dict, f"{label}: expected object")
    _require(set(required) <= value.keys(), f"{label}: missing fields {sorted(set(required) - value.keys())}")
    _require(not value.keys() - set(required) - set(optional), f"{label}: unsupported fields")
    return value


def _text(value, label, *, nullable=False):
    if nullable and value is None:
        return
    _require(type(value) is str and bool(value.strip()), f"{label}: expected nonempty text")
    _require("\x00" not in value and _LOCAL.search(value) is None, f"{label}: local path is not public metadata")


def _strings(value, label, *, unique=False):
    _require(type(value) is list, f"{label}: expected list")
    for item in value:
        _text(item, label)
    _require(not unique or len(set(value)) == len(value), f"{label}: duplicate values")


def _identifier(value, label):
    _require(type(value) is str and _ID.fullmatch(value) is not None, f"{label}: invalid identifier")


def _hash(value, pattern, label):
    _require(type(value) is str and pattern.fullmatch(value) is not None, f"{label}: immutable digest required")


def _relative(value, label):
    _text(value, label)
    path = Path(value)
    _require(not path.is_absolute() and ".." not in path.parts and "\\" not in value,
             f"{label}: expected contained relative path")


def _url(value, label, *, github=False):
    _text(value, label)
    parsed = urlsplit(value)
    _require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password,
             f"{label}: expected credential-free HTTPS URL")
    _require(not {key.lower() for key, _ in parse_qsl(parsed.query)} &
             {"token", "access_token", "api_key", "password", "secret", "signature"},
             f"{label}: credential query parameters are not metadata")
    if github:
        _require(parsed.hostname == "github.com" and re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", parsed.path)
                 and not parsed.query and not parsed.fragment, f"{label}: expected GitHub repository URL")


def _repository(value):
    _object(value, ("url", "commit"), "repository")
    _url(value["url"], "repository.url", github=True)
    _hash(value["commit"], _COMMIT, "repository.commit")


def _json(path):
    def reject_duplicates(pairs):
        out = {}
        for key, value in pairs:
            _require(key not in out, f"{path.name}: duplicate JSON key {key}")
            out[key] = value
        return out
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates,
                          parse_constant=lambda value: (_ for _ in ()).throw(RegistryError(f"nonfinite JSON: {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"Cannot read registry document {path.name}: {type(exc).__name__}") from exc


def resolve_registry_root(root=None):
    if root is not None:
        return Path(root).expanduser().resolve()
    repository = Path(__file__).resolve().parents[2] / "registry"
    return repository if repository.is_dir() else Path(__file__).resolve().parent / "_assets" / "registry"


def validate_source(source):
    _object(source, ("id", "repository", "catalog_path", "catalog_sha256", "index_path", "index_sha256"), "source")
    _identifier(source["id"], "source.id")
    _repository(source["repository"])
    for key in ("catalog_path", "index_path"):
        _relative(source[key], key)
    for key in ("catalog_sha256", "index_sha256"):
        _hash(source[key], _SHA256, key)


def validate_task(task, source_ids):
    required = ("id", "name", "description", "family", "protocol", "executable", "declared_status",
                "runtime_readiness", "metric", "direction", "requirements", "paper_ids", "source_id", "provenance",
                "unsupported_reason", "unsupported_category", "contract", "contract_source")
    _object(task, required, "task")
    _identifier(task["id"], "task.id")
    for field in ("name", "description"):
        _text(task[field], f"task.{field}")
    for field in ("family", "metric", "unsupported_reason", "unsupported_category"):
        _text(task[field], f"task.{field}", nullable=True)
    _text(task["contract"], "task.contract", nullable=True)
    contract_source = task["contract_source"]
    if contract_source is not None:
        _object(contract_source, ("url", "path", "sha256"), "contract_source")
        _url(contract_source["url"], "contract_source.url")
        _relative(contract_source["path"], "contract_source.path")
        _hash(contract_source["sha256"], _SHA256, "contract_source.sha256")
    _require(task["contract"] is None or contract_source is not None, "declared contract needs pinned source")
    protocol = task["protocol"]
    _require(protocol in PROTOCOLS, "task.protocol: unsupported value")
    _require(type(task["executable"]) is bool and task["executable"] == (protocol != "unsupported"),
             "task.executable contradicts declared protocol")
    _require(task["declared_status"] in ("ready", "blocked", "requires_setup"), "invalid declared status")
    _require((task["declared_status"] == "ready") == task["executable"], "task declared status contradicts executable route")
    _require(task["runtime_readiness"] == "not_verified", "snapshot cannot attest runtime readiness")
    _require(task["direction"] in ("maximize", "minimize", None), "invalid objective direction")
    _require(not task["executable"] or task["direction"] is not None, "executable task needs objective direction")
    _require(protocol != "unsupported" or task["unsupported_reason"] is not None, "unsupported task needs a reason")
    _strings(task["requirements"], "task.requirements", unique=True)
    _strings(task["paper_ids"], "task.paper_ids", unique=True)
    _require(task["paper_ids"], "task.paper_ids must not be empty")
    _identifier(task["source_id"], "task.source_id")
    _require(task["source_id"] in source_ids, "task refers to an unknown source")
    provenance = _object(task["provenance"], ("kind", "sources", "limitations", "validation_level",
        "upstream_reproduction", "benchmark", "paper_metric", "paper_direction", "upstream_repository",
        "index_requirements", "metadata_notes"), "provenance")
    _require(provenance["kind"] in ("native", "upstream", "specification"), "invalid provenance kind")
    _strings(provenance["limitations"], "limitations")
    _strings(provenance["metadata_notes"], "metadata_notes")
    if provenance["index_requirements"] is not None:
        _strings(provenance["index_requirements"], "index_requirements", unique=True)
    for key in ("validation_level", "benchmark", "paper_metric"):
        _text(provenance[key], key, nullable=True)
    _require(provenance["paper_direction"] in ("maximize", "minimize", None), "invalid paper direction")
    _require(type(provenance["upstream_reproduction"]) is bool, "invalid reproduction flag")
    if provenance["upstream_repository"] is not None:
        _repository(provenance["upstream_repository"])
    _require(type(provenance["sources"]) is list and provenance["sources"], "provenance needs sources")
    for source in provenance["sources"]:
        _object(source, ("url", "type", "locator"), "provenance source")
        _url(source["url"], "source.url")
        _text(source["type"], "source.type")
        _text(source["locator"], "source.locator", nullable=True)


def catalog_summary(tasks):
    counts = Counter(task["protocol"] for task in tasks)
    return {"task_count": len(tasks), "executable_count": sum(task["executable"] for task in tasks),
            "unsupported_count": counts["unsupported"], "protocol_counts": {p: counts[p] for p in PROTOCOLS},
            "runtime_readiness": "not_verified"}


def validate_catalog(value):
    _object(value, ("schema", "sources", "summary", "tasks"), "catalog")
    _require(value["schema"] == "arena.catalog/1", "unsupported catalog schema")
    _require(type(value["sources"]) is list and value["sources"], "catalog needs sources")
    ids = set()
    for source in value["sources"]:
        validate_source(source)
        _require(source["id"] not in ids, "duplicate source id")
        ids.add(source["id"])
    _require(type(value["tasks"]) is list, "tasks must be a list")
    task_ids = set()
    for task in value["tasks"]:
        validate_task(task, ids)
        if task["contract_source"] is not None:
            source = next(s for s in value["sources"] if s["id"] == task["source_id"])
            expected_path = f"suite/{task['id']}/problem.json"
            expected_url = f"{source['repository']['url']}/blob/{source['repository']['commit']}/{expected_path}"
            _require(task["contract_source"]["path"] == expected_path and task["contract_source"]["url"] == expected_url,
                     "contract source must match task and pinned repository version")
        _require(task["id"] not in task_ids, "duplicate task id")
        task_ids.add(task["id"])
    _require(value["summary"] == catalog_summary(value["tasks"]), "catalog summary disagrees with tasks")
    return value


def validate_participant(value):
    _object(value, ("id", "name", "description", "repository", "registration_status", "adapter_status",
                   "capabilities", "supported_protocols", "limitations"), "participant")
    _identifier(value["id"], "participant.id")
    for key in ("name", "description"):
        _text(value[key], key)
    _repository(value["repository"])
    _require(value["registration_status"] == "planned", "v1 participant registration must be planned")
    _require(value["adapter_status"] == "not_implemented", "native adapters are not implemented in registry v1")
    _object(value["capabilities"], CAPABILITIES, "capabilities")
    _require(all(value["capabilities"][key] is False for key in CAPABILITIES), "unimplemented adapter cannot advertise capabilities")
    _strings(value["supported_protocols"], "supported_protocols", unique=True)
    _require(not value["supported_protocols"], "unimplemented adapter cannot advertise compatible task protocols")
    _strings(value["limitations"], "limitations")


def participant_view(participants):
    return {"schema": "arena.participants/1", "summary": {"participant_count": len(participants), "integrated_count": 0},
            "participants": participants}


def validate_participants(value):
    _object(value, ("schema", "summary", "participants"), "participants catalog")
    _require(value["schema"] == "arena.participants/1", "unsupported participant catalog schema")
    _require(type(value["participants"]) is list, "participants must be a list")
    ids = set()
    for participant in value["participants"]:
        validate_participant(participant)
        _require(participant["id"] not in ids, "duplicate participant id")
        ids.add(participant["id"])
    _require(value["summary"] == participant_view(value["participants"])["summary"], "participant summary disagrees with records")
    return value


def validate_registration(value):
    _object(value, ("schema", "id", "kind", "repository", "manifest_path", "tracked_ref", "access",
                   "admission", "refresh", "snapshot_source_id"), "registration")
    _require(value["schema"] == "arena.registration/1", "unsupported registration schema")
    _identifier(value["id"], "registration.id")
    _require(value["kind"] == "task_collection", "unsupported registration kind")
    _repository(value["repository"])
    _relative(value["manifest_path"], "manifest_path")
    _text(value["tracked_ref"], "tracked_ref")
    _require(value["access"] in ("github_app_private", "github_app_public"), "invalid repository access mode")
    _require(value["admission"] == "team_registry_pr", "registration requires team registry PR")
    _require(value["refresh"] == "manual_pinned_snapshot", "remote refresh/build is not implemented")
    _identifier(value["snapshot_source_id"], "snapshot_source_id")
    return value


def get_catalog(registry_root=None):
    """Return catalog metadata; executable never implies installed or runnable here."""
    return deepcopy(validate_catalog(_json(resolve_registry_root(registry_root) / "catalog.json")))


def get_participants(registry_root=None):
    return deepcopy(validate_participants(_json(resolve_registry_root(registry_root) / "participants.json")))


def validate_registry(root=None):
    root = resolve_registry_root(root)
    catalog, participants = get_catalog(root), get_participants(root)
    registrations = [validate_registration(_json(path)) for path in sorted((root / "task-sources").glob("*.json"))]
    _require(registrations, "registry has no task-source registrations")
    _require(len({r["id"] for r in registrations}) == len(registrations), "duplicate registration id")
    source_ids = {s["id"] for s in catalog["sources"]}
    _require({r["snapshot_source_id"] for r in registrations} == source_ids, "source registrations and catalog differ")
    for registration in registrations:
        source = next(s for s in catalog["sources"] if s["id"] == registration["snapshot_source_id"])
        _require(registration["repository"] == source["repository"] and registration["manifest_path"] == source["catalog_path"],
                 "source registration revision/path differs from snapshot")
    declarations = [_json(path) for path in sorted((root / "participants").glob("*.json"))]
    for participant in declarations:
        validate_participant(participant)
    _require(sorted(declarations, key=lambda p: p["id"]) == sorted(participants["participants"], key=lambda p: p["id"]),
             "participant declarations and aggregate differ")
    return {"valid": True, "catalog": catalog["summary"], "participants": participants["summary"],
            "remote_refresh": "not_implemented", "native_runners": "not_implemented"}


def sanitized_text(value):
    """Omit machine-local paths from selected, public-facing upstream metadata."""
    return _LOCAL.sub("[local path omitted]", value) if isinstance(value, str) else value


def build_catalog(records, index, source, problem_files=None):
    """Project allowlisted metadata from a pinned catalog, without loading code."""
    validate_source(source)
    _require(type(records) is list and type(index) is dict and type(index.get("tasks")) is list,
             "invalid source catalog/index shape")
    indexed = {}
    for row in index["tasks"]:
        _require(type(row) is dict, "malformed source index task")
        _identifier(row.get("id"), "source index task.id")
        _require(row["id"] not in indexed, "duplicate source index task")
        _strings(row.get("requires"), "source index requires")
        indexed[row["id"]] = row
    _require(index.get("count") == len(indexed), "source index count differs")
    tasks = []
    for record in records:
        tid = record["id"]
        _identifier(tid, "source task.id")
        _require(tid in indexed, "source index omits catalog task")
        suite = record["execution"]["suite"]
        row = indexed[tid]
        for key in ("protocol", "family"):
            _require(suite.get(key) == row.get(key), f"source index differs: {tid}/{key}")
        ev, validation, execution = record["evaluation"], record["validation"], record["execution"]
        upstream = None
        if execution.get("repository") and _COMMIT.fullmatch(execution.get("commit") or ""):
            upstream = {"url": execution["repository"].removesuffix(".git"), "commit": execution["commit"]}
        contract, contract_source = None, None
        problem_bytes = (problem_files or {}).get(tid)
        if problem_bytes is not None:
            _require(type(problem_bytes) is bytes, "problem source must be bytes from pinned Git objects")
            problem = json.loads(problem_bytes)
            _require(type(problem) is dict and problem.get("id") == tid, "problem file task identity differs")
            _require(problem.get("protocol") == suite["protocol"], "problem file protocol differs")
            contract = sanitized_text(problem.get("contract"))
            path = f"suite/{tid}/problem.json"
            contract_source = {"url": f"{source['repository']['url']}/blob/{source['repository']['commit']}/{path}",
                               "path": path, "sha256": hashlib.sha256(problem_bytes).hexdigest()}
        tasks.append({
            "id": tid, "name": sanitized_text(record["name"]), "description": sanitized_text(record["description"]),
            "family": suite.get("family"), "protocol": suite["protocol"], "executable": suite["protocol"] != "unsupported",
            "declared_status": record["status"], "runtime_readiness": "not_verified", "metric": ev.get("metric"),
            "direction": ev.get("direction"), "requirements": sorted(set(suite.get("requires", []))),
            "paper_ids": record["paper_ids"], "source_id": source["id"],
            "unsupported_reason": sanitized_text(suite.get("unsupported_reason")),
            "unsupported_category": suite.get("unsupported_category"),
            "contract": contract, "contract_source": contract_source,
            "provenance": {"kind": record["kind"],
                "sources": [{"url": item["url"], "type": item["type"], "locator": sanitized_text(item.get("locator"))}
                            for item in record["sources"]],
                "limitations": [sanitized_text(item) for item in record["limitations"]],
                "validation_level": validation.get("level"), "upstream_reproduction": validation["upstream_reproduction"],
                "benchmark": sanitized_text(ev.get("benchmark")), "paper_metric": sanitized_text(ev.get("paper_metric")),
                "paper_direction": ev.get("paper_direction"), "upstream_repository": upstream,
                "index_requirements": sorted(set(row["requires"])) if set(row["requires"]) != set(suite["requires"]) else None,
                "metadata_notes": ["The source suite index lists different requirements; catalog/tasks.json execution.suite.requires is preserved as authoritative, and index_requirements retains the alternate declaration."]
                    if set(row["requires"]) != set(suite["requires"]) else []}})
    _require(len(records) == len(indexed), "source catalog and index task counts differ")
    tasks.sort(key=lambda task: task["id"])
    return validate_catalog({"schema": "arena.catalog/1", "sources": [deepcopy(source)],
                             "summary": catalog_summary(tasks), "tasks": tasks})


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate/read the offline GitHub registry; never executes tasks")
    parser.add_argument("command", choices=("validate", "catalog", "participants"))
    parser.add_argument("--root", type=Path, help="Registry directory (default: repository/registry)")
    args = parser.parse_args(argv)
    try:
        result = {"validate": validate_registry, "catalog": get_catalog, "participants": get_participants}[args.command](args.root)
    except RegistryError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
