#!/usr/bin/env python3
"""Wait for reviewed seed/pilot evidence, then launch a bounded private campaign.

Preview does not write, prepare, reload or submit. Admission remains an explicit
operator action. No process started here performs evaluation before the existing
authorized worker claims a queued template.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "src"))
import prepare_sciel_catalog_campaign as prepare
import submit_sciel_catalog as submit
import sciel_catalog_preflight as preflight
from arena.control_config import validate_config
from arena.insights import get_insights
from arena.registry import get_catalog

PRIORITY = ("physics", "chemistry-materials", "biology-health", "robotics-control")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    raw = submit.read_bytes(path, 32 * 1024 * 1024)
    return json.loads(raw), digest(raw)


def eligible_task_ids(args, role):
    return {row["task_id"] for row in preflight.inventory(get_catalog()["tasks"], args.tasks_root, role)
            if row["status"] == "seed_check_pending"}


def load_conformance(args, inventory, templates, source):
    from sciel_catalog_conformance import validate_conformance
    return validate_conformance(args.pilot_conformance, pilot_inventory=inventory,
        pilot_templates=templates, model=args.model, task_source=source)


def gate_inputs(args):
    qualified = getattr(args, "pilot_conformance", None)
    paths = [*args.preflight, args.pilot_inventory, args.pilot_status,
             args.pilot_inventory.parent / "templates.json"]
    if any(not path.exists() for path in paths) or qualified and not qualified.exists():
        return None
    loaded = [read_json(path) for path in paths]
    manifests = [item[0] for item in loaded[:2]]
    inventory, status, templates = [item[0] for item in loaded[2:]]
    roles = [item.get("group") or ("base" if path == getattr(args, "base_preflight", None) else None)
             for path, item in zip(args.preflight, manifests)]
    if (any(item.get("schema") != "arena.sciel-catalog-preflight/1" for item in manifests)
            or set(roles) != {"base", "extended"}):
        raise ValueError("Exactly one base and one extended CPU preflight are required")
    for item, role in zip(manifests, roles):
        observed = {row["task_id"] for row in item["tasks"]
                    if row["status"] in {"seed_verified", "seed_check_pending", "seed_check_failed"}}
        if observed != eligible_task_ids(args, role):
            raise ValueError("Preflight eligible task IDs differ from the declared CPU profile")
        item["group"] = role
    if status.get("schema") != "arena.sciel-catalog-admission/1":
        raise ValueError("Pilot admission evidence is missing")
    if not qualified and status.get("state", "").startswith("paused"):
        raise ValueError("Pilot admission paused; resolve its recorded evidence before launching")
    if any("finished_at" not in item for item in manifests) or not qualified and status.get("state") != "completed":
        return None
    if any(type(item["finished_at"]) not in (int, float) or not math.isfinite(item["finished_at"])
           or item["finished_at"] <= 0 for item in manifests):
        raise ValueError("Finished preflights need a finite completion timestamp")
    if (inventory.get("schema") != "arena.sciel-catalog-campaign/1"
            or inventory.get("campaign") != status.get("campaign")
            or inventory.get("model") != args.model
            or status.get("models") != [args.model]
            or any(item.get("task_source") != inventory.get("task_source") for item in manifests)
            or status.get("templates_sha256") != loaded[-1][1]):
        raise ValueError("Pilot and seed evidence do not identify the same reviewed inputs")
    by_template = {row["id"]: row for row in templates}
    rows = [row for batch in status["batches"] for row in batch["runs"]]
    if (not rows or len(rows) != len(by_template) or len(rows) != status.get("planned")
            or len({row["template"] for row in rows}) != len(rows)
            or {row["template"] for row in rows} != set(by_template)
            or not qualified and (any(row["state"] != "completed" for row in rows)
                                  or any(batch.get("native_issues") for batch in status["batches"]))):
        raise ValueError("Every pilot template needs a distinct completed run without native issues")
    completed = {row["task_id"] for row in inventory["tasks"] if row.get("template_id") in by_template}
    if len(completed) != len(rows):
        raise ValueError("Pilot task identities are incomplete or duplicated")
    verified_sets = [{row["task_id"] for row in item["tasks"] if row["status"] == "seed_verified"}
                     for item in manifests]
    if verified_sets[0] & verified_sets[1]:
        raise ValueError("Base and extended preflight groups overlap")
    hashes = dict(zip(map(str, paths), [x[1] for x in loaded]))
    conformance = load_conformance(args, inventory, templates, manifests[0]["task_source"]) if qualified else None
    if conformance:
        if set(conformance["run_ids"]) != {row["id"] for row in rows} or set(conformance["task_ids"]) != completed:
            raise ValueError("Runtime conformance must cover every exact pilot run and task")
        hashes.pop(str(args.pilot_status))  # Active monitor timestamps are not a scientific input.
        hashes[str(qualified)] = conformance["sha256"]
    return {"manifests": manifests, "pilot": status, "pilot_templates": by_template,
            "excluded": sorted(completed), "input_sha256": hashes, "conformance": conformance}


def verify_pilot(gates, control, live):
    allowed = {}
    for batch in gates["pilot"]["batches"]:
        for evidence in batch["runs"]:
            run = control.call("/api/queue/" + evidence["id"])["run"]
            submit.verify_run(run, gates["pilot_templates"][evidence["template"]],
                              batch["batch_id"], gates["pilot"]["control_revision"])
            states = {"running", "completed"} if gates.get("conformance") else {"completed"}
            if run["state"] not in states or run.get("cancel_requested") or submit.native_issue(run, Path(live["state_dir"])):
                raise ValueError("Pilot completion is not supported by current native run evidence")
            if gates.get("conformance"):
                proof = next(row for row in gates["conformance"]["runs"] if row["run_id"] == run["id"])
                if (proof["control_revision"] != run["revision"] or proof["batch_id"] != run["batch_id"]
                        or proof["template_id"] != run["template"]):
                    raise ValueError("Observed pilot conformance differs from the admitted queue identity")
                allowed[run["id"]] = {key: run[key] for key in ("template", "model", "revision")}
                allowed[run["id"]]["snapshot_sha256"] = proof["snapshot_sha256"]
    return allowed


def research_order(records, annotations):
    """Round-robin authoritative domains, with scientific dynamics domains first."""
    queues = defaultdict(deque)
    for row in sorted(records, key=lambda row: row["task_id"]):
        domain = annotations.get(row["task_id"], {}).get("domain_id")
        if not domain:
            raise ValueError("A prepared task is missing its authoritative scientific domain")
        row["domain_id"] = domain
        queues[domain].append(row)
    domains = [domain for domain in PRIORITY if domain in queues]
    domains += sorted(set(queues) - set(domains))
    ordered = []
    while any(queues.values()):
        for domain in domains:
            if queues[domain]:
                ordered.append(queues[domain].popleft())
    return ordered


def grant_worker_read(root, group):
    for path in (root, *root.rglob("*")):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError("Generated campaign files must be regular and must not contain symlinks")
        os.chown(path, os.geteuid(), group)
        path.chmod(0o750 if path.is_dir() else 0o640)


def prepare_all(args, gates, live):
    """Materialize inert reviewed outputs once; no model, reload or queue calls."""
    destination, native = args.config_destination, args.native_tasks
    protected = [args.tasks_root, args.pilot_inventory.parent, *(path.parent for path in args.preflight)]
    if (destination.is_relative_to(native) or native.is_relative_to(destination)
            or any(output.is_relative_to(root) or root.is_relative_to(output)
                   for output in (destination, native) for root in protected)):
        raise ValueError("Campaign destinations must be separate from source and evidence trees")
    if destination.exists() or native.exists():
        raise ValueError("Preparation requires new destinations or a complete recorded launch plan")
    destination.mkdir(parents=True, mode=0o750)
    native.mkdir(parents=True, mode=0o750)
    inventories, templates = [], {}
    for path, manifest in sorted(zip(args.preflight, gates["manifests"]), key=lambda pair: pair[1]["group"]):
        group = manifest["group"]
        target = destination / group
        prepare.prepare(tasks_root=args.tasks_root, config_destination=target,
            native_tasks=native / group, preflight_manifest=path, deployment=args.deployment,
            approval=args.approval, campaign=args.campaign, python=args.python, model=args.model,
            exclude_tasks=gates["excluded"])
        inventory, _ = read_json(target / "campaign-inventory.json")
        planned, _ = read_json(target / "templates.json")
        inventories.append(inventory)
        for row in planned:
            if row["id"] in templates:
                raise ValueError("Prepared template identifiers overlap")
            templates[row["id"]] = row
    by_task = defaultdict(list)
    for inventory in inventories:
        for row in inventory["tasks"]:
            by_task[row["task_id"]].append(row)
    records = []
    for task_id, rows in sorted(by_task.items()):
        selected = [row for row in rows if row["status"] == "prepared"]
        if len(selected) > 1:
            raise ValueError("A task was prepared by more than one CPU profile")
        evidence_rank = {"seed_verified": 5, "seed_check_failed": 4, "seed_check_pending": 3,
                         "runtime_integration_pending": 2, "environment_preparation_pending": 1}
        row = dict(selected[0] if selected else max(rows, key=lambda item: evidence_rank.get(item["preflight_status"], 0)))
        row["preflight_profiles"] = [{"group": group, "status": item["preflight_status"],
                                     "reason": item.get("reason")}
                                    for group, item in zip(("base", "extended"), rows)]
        if task_id in gates["excluded"]:
            qualified = bool(gates.get("conformance"))
            row.update(status="pilot_qualified" if qualified else "pilot_completed",
                       reason="Reserved for the receipt-qualified pilot; not resubmitted." if qualified
                       else "Completed in the verified pilot; not resubmitted.")
        records.append(row)
    ordered = research_order([row for row in records if row["status"] == "prepared"],
                             get_insights()["task_annotations"])
    combined = [templates[row["template_id"]] for row in ordered]
    candidate = {**live, "templates": list(live["templates"])}
    old_ids = {row["id"] for row in live["templates"]}
    if any(row["id"] in old_ids for row in combined):
        raise ValueError("New campaign templates collide with existing control templates")
    candidate["templates"].extend(combined)
    validate_config(candidate)
    submit.validate_templates(combined, candidate)
    prepare.write(destination / "templates.json", combined)
    prepare.write(destination / "campaign-inventory.json", {
        "schema": "arena.sciel-catalog-campaign/1", "campaign": args.campaign, "model": args.model,
        "task_source": inventories[0]["task_source"], "tasks": records,
        "counts": dict(Counter(row["status"] for row in records)), "model_calls": 0,
        "ordering": {"kind": "research-diverse", "priority_domains": list(PRIORITY),
                     "task_ids": [row["task_id"] for row in ordered]},
        "excluded_pilot_tasks": gates["excluded"], "input_sha256": gates["input_sha256"]})
    prepare.write(destination / "control-prepared.json", candidate)
    grant_worker_read(destination, args.worker_gid)
    grant_worker_read(native, args.worker_gid)
    return candidate


@contextmanager
def queue_identity(path):
    """Create SQLite sidecars as the queue owner, never as the root operator."""
    original, owner = os.geteuid(), path.stat().st_uid
    if original not in {0, owner}:
        raise ValueError("Queue storage belongs to a different operator")
    try:
        if original != owner:
            os.seteuid(owner)
        yield
    finally:
        if os.geteuid() != original:
            os.seteuid(original)


@contextmanager
def idle_queue(state_dir, allowed=None):
    """Serialize the empty-queue gate with all worker claims and admissions."""
    path = state_dir / "queue.sqlite"
    for item in (state_dir, path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if item.is_symlink() or item.resolve() != item:
            raise ValueError("Queue storage must not traverse symlinks")
    if not path.is_file() or state_dir.stat().st_mode & 0o022:
        raise ValueError("Expected an existing private queue")
    with queue_identity(path):
        db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=10, isolation_level=None)
        try:
            db.execute("BEGIN IMMEDIATE")
        except BaseException:
            db.close()
            raise
    try:
        if allowed:
            db.row_factory = sqlite3.Row
            for run_id, expected in allowed.items():
                row = db.execute("SELECT id,template,model,revision,snapshot_sha256,state FROM runs WHERE id=?", (run_id,)).fetchone()
                if (row is None or row["state"] not in {"running", "completed"}
                        or any(row[key] != value for key, value in expected.items())):
                    raise ValueError("Qualified pilot identity or state changed before installation")
            placeholders = ",".join("?" for _ in allowed)
            count = db.execute(f"SELECT COUNT(*) FROM runs WHERE (held=1 OR state NOT IN ('completed','failed','cancelled','blocked')) AND id NOT IN ({placeholders})", tuple(allowed)).fetchone()[0]
        else:
            count = db.execute("SELECT COUNT(*) FROM runs WHERE held=1 OR state NOT IN ('completed','failed','cancelled','blocked')").fetchone()[0]
        if count:
            raise ValueError("Queue must be idle before installing campaign templates")
        yield
        with queue_identity(path):
            db.commit()
    finally:
        with queue_identity(path):
            if db.in_transaction:
                db.rollback()
            db.close()


def replace_config(path, raw, info):
    temporary = path.with_name(path.name + f".{os.getpid()}.pending")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fchown(stream.fileno(), info.st_uid, info.st_gid)
            os.fchmod(stream.fileno(), stat.S_IMODE(info.st_mode))
            os.fsync(stream.fileno())
        temporary.replace(path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def install_control(args, before, candidate, admin, reader, allowed=None):
    validate_config(candidate)
    if (any(candidate[key] != value for key, value in before.items() if key != "templates")
            or candidate["templates"][:len(before["templates"])] != before["templates"]):
        raise ValueError("Installation must only append templates and preserve all existing limits and templates")
    planned = json.loads(submit.read_bytes(args.config_destination / "templates.json"))
    submit.validate_templates(planned, candidate)
    revision = digest(submit.encoded(candidate))
    current = submit.read_bytes(args.control_config)
    if json.loads(current) == candidate:
        admin.call("/api/control/reload", {})
        return revision
    with idle_queue(Path(candidate["state_dir"]), allowed):
        if json.loads(submit.read_bytes(args.control_config)) != before:
            raise ValueError("Control configuration changed before the atomic installation")
        info = args.control_config.stat()
        backup = args.config_destination / "control-backup.json"
        if backup.exists():
            if json.loads(submit.read_bytes(backup)) != before:
                raise ValueError("Existing backup does not match the original control configuration")
        else:
            descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(current)
                stream.flush()
                os.fsync(stream.fileno())
        try:
            replace_config(args.control_config, submit.encoded(candidate) + b"\n", info)
            if admin.call("/api/control/reload", {}).get("revision") != revision:
                raise ValueError("Control service did not load the prepared revision")
            submit.verify_live(reader, args.control_config, planned, revision)
        except Exception:
            replace_config(args.control_config, current, info)
            admin.call("/api/control/reload", {})
            raise
    return revision


def verify_worker(config):
    result = subprocess.run(["systemctl", "show", "arena-worker.service", "--property=MainPID", "--value"],
                            capture_output=True, text=True, timeout=10, check=True)
    pid = result.stdout.strip()
    if not pid.isdigit() or int(pid) <= 0:
        raise ValueError("The authorized worker service is not running")
    command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    if b"arena.control" not in command or b"worker" not in command or b"--config" not in command:
        raise ValueError("The live service is not the Arena control worker")
    if command[command.index(b"--config") + 1] != os.fsencode(config):
        raise ValueError("Worker and board must load the same control configuration")
    # ControlService.claim() reloads this exact file before each queue claim.


def request_identity(args, gates):
    names = ("tasks_root", "config_destination", "native_tasks", "deployment", "approval",
             "control_config", "campaign", "model", "python", "worker_gid", "batch_size")
    return {"arguments": {key: str(getattr(args, key)) for key in names},
            "input_sha256": gates["input_sha256"],
            "deployment_sha256": read_json(args.deployment)[1], "approval_sha256": read_json(args.approval)[1]}


def launch(args, gates):
    reader = submit.Control(submit.read_key(args.key_file))
    admin = submit.Control(submit.read_key(args.admin_key_file))
    reader.timeout = admin.timeout = 3  # Keep reload/rollback below the worker's lease interval.
    live = validate_config(json.loads(submit.read_bytes(args.control_config)))
    allowed = verify_pilot(gates, reader, live)
    verify_worker(args.control_config)
    identity = request_identity(args, gates)
    plan_path = args.config_destination / "launch-plan.json"
    if plan_path.exists():
        plan, _ = read_json(plan_path)
        if plan.get("request") != identity:
            raise ValueError("Resume requires the same reviewed launch inputs")
        before = plan["control_before"]
        candidate, _ = read_json(args.config_destination / "control-prepared.json")
        if (digest(submit.encoded(candidate)) != plan["control_revision"]
                or read_json(args.config_destination / "templates.json")[1] != plan["templates_sha256"]):
            raise ValueError("Prepared control configuration changed")
    else:
        before = live
        candidate = prepare_all(args, gates, live)
        if gate_inputs(args)["input_sha256"] != gates["input_sha256"]:
            raise ValueError("Pilot or preflight evidence changed during preparation")
        prepare.write(plan_path, {"schema": "arena.sciel-catalog-launch/1", "request": identity,
            "control_before": before, "control_revision": digest(submit.encoded(candidate)),
            "templates_sha256": read_json(args.config_destination / "templates.json")[1]})
        plan_path.chmod(0o600)
    install_control(args, before, candidate, admin, reader, allowed)
    return submit.main(["--templates", str(args.config_destination / "templates.json"),
        "--control-config", str(args.control_config), "--key-file", str(args.key_file),
        "--campaign", args.campaign, "--status", str(args.status),
        "--batch-size", str(args.batch_size), "--admit"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--preflight", type=Path, action="append")
    parser.add_argument("--base-preflight", type=Path)
    parser.add_argument("--extended-preflight", type=Path)
    parser.add_argument("--pilot-conformance", type=Path,
                        help="Explicit receipt-qualified pilot gate; otherwise require completed pilot admission")
    for name in ("tasks-root", "config-destination", "native-tasks", "deployment", "approval",
                 "python", "pilot-inventory", "pilot-status", "control-config", "key-file", "admin-key-file", "status"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--worker-gid", type=int, default=998)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--wait-seconds", type=int, default=86400)
    parser.add_argument("--admit", action="store_true")
    args = parser.parse_args(argv)
    if args.base_preflight or args.extended_preflight:
        if args.preflight or not args.base_preflight or not args.extended_preflight:
            parser.error("Use either both explicit CPU roles or two --preflight arguments")
        args.preflight = [args.base_preflight, args.extended_preflight]
    if (not args.preflight or len(args.preflight) != 2 or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.campaign)
            or not 1 <= args.batch_size <= 16 or not 1 <= args.wait_seconds <= 604800 or args.worker_gid < 0):
        parser.error("Use two preflights, a short campaign ID, batches of 1–16 and a bounded wait")
    for name, value in vars(args).items():
        for path in value if type(value) is list else [value]:
            if isinstance(path, Path) and name != "python":
                prepare.exact_path(path)
    if args.admit and os.geteuid() != 0:
        parser.error("Live orchestration requires the authorized root operator")
    deadline = time.monotonic() + args.wait_seconds
    while (gates := gate_inputs(args)) is None:
        if not args.admit:
            print(json.dumps({"state": "waiting_for_preflight_and_pilot", "mutated": False}))
            return 0
        if time.monotonic() >= deadline:
            raise ValueError("Timed out waiting for both preflights and completed pilot evidence")
        time.sleep(min(15, max(0, deadline - time.monotonic())))
    if not args.admit:
        print(json.dumps({"state": "ready", "excluded_pilot_tasks": gates["excluded"], "mutated": False}))
        return 0
    with submit.campaign_lock(args.status.with_name(args.status.name + ".launch")):
        return launch(args, gates)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, IndexError, subprocess.SubprocessError):
        print("Catalog launch stopped; inspect private evidence and configuration before retrying.", file=sys.stderr)
        raise SystemExit(2)
