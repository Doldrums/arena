"""Validate one explicit frozen append-only control transition for a campaign.

The operator supplies a private descriptor with schema
arena.control-append-transition/1, previous/next {path, sha256, revision}, and
added_template_ids in append order. Each path identifies a separate frozen
control JSON snapshot, not the live configuration. sha256 binds its exact bytes;
revision binds the control service's canonical JSON representation.

This helper never writes configuration, reloads a service or admits a task.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from arena.control_config import validate_config


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        value = {}
        for key, child in items:
            if key in value:
                raise ValueError("Duplicate transition input fields are not allowed")
            value[key] = child
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite transition input")))


def load_transition(path, *, control_path, read, encode):
    path, control_path = Path(path), Path(control_path)
    raw = read(path, private=True)
    descriptor = decode(raw)
    if (type(descriptor) is not dict
            or set(descriptor) != {"schema", "previous", "next", "added_template_ids"}
            or descriptor["schema"] != "arena.control-append-transition/1"):
        raise ValueError("Expected one explicit frozen control append transition")
    configurations, paths = {}, set()
    for key in ("previous", "next"):
        item = descriptor[key]
        if (type(item) is not dict or set(item) != {"path", "sha256", "revision"}
                or type(item["path"]) is not str
                or any(type(item[field]) is not str or not re.fullmatch(r"[a-f0-9]{64}", item[field])
                       for field in ("sha256", "revision"))):
            raise ValueError("Transition snapshots need exact paths, file hashes and revisions")
        snapshot_path = Path(item["path"])
        if snapshot_path in {path, control_path} or snapshot_path in paths:
            raise ValueError("Transition snapshots must be separate frozen files")
        paths.add(snapshot_path)
        content = read(snapshot_path)
        config = validate_config(decode(content))
        if sha(content) != item["sha256"] or sha(encode(config)) != item["revision"]:
            raise ValueError("Frozen transition snapshot identity changed")
        configurations[key] = config
    old, new = configurations["previous"], configurations["next"]
    prefix = len(old["templates"])
    added = new["templates"][prefix:]
    if (any(new[key] != value for key, value in old.items() if key != "templates")
            or new["templates"][:prefix] != old["templates"] or not added
            or descriptor["added_template_ids"] != [row["id"] for row in added]):
        raise ValueError("Transition must only append the declared unique templates")
    identity = {"schema": descriptor["schema"], "sha256": sha(raw),
                "previous_revision": descriptor["previous"]["revision"],
                "next_revision": descriptor["next"]["revision"],
                "added_template_ids": descriptor["added_template_ids"]}
    return {"path": path, "control_path": control_path, "identity": identity, **configurations}


def current_revision(transition, live, summary, *, read, encode):
    checked = load_transition(transition["path"], control_path=transition["control_path"], read=read, encode=encode)
    if checked["identity"] != transition["identity"]:
        raise ValueError("Explicit control transition changed during admission")
    revision = sha(encode(live))
    old = transition["identity"]["previous_revision"]
    new = transition["identity"]["next_revision"]
    if revision not in {old, new}:
        raise ValueError("Live control revision is outside the explicit transition")
    if summary.get("active_control_revision") == new and revision != new:
        raise ValueError("Control revision cannot revert after the approved append")
    summary["active_control_revision"] = revision
    return revision


def snapshot_binding(row, template, transition, previous, *, read, encode):
    revision = row.get("revision")
    accepted = {transition["identity"]["previous_revision"], transition["identity"]["next_revision"]}
    if revision not in accepted or previous and previous.get("revision") != revision:
        raise ValueError("Run admission revision changed or was never explicitly approved")
    state_dir = Path(transition["previous"]["state_dir"])
    raw = read(state_dir / "runs" / row["id"] / "snapshot.json")
    expected = {"revision": revision, "template": template,
                "cgroup_root": transition["previous"]["cgroup_root"]}
    if raw != encode(expected) + b"\n":
        raise ValueError("Run snapshot differs from its immutable reviewed admission")
    binding = {"revision": revision, "snapshot_sha256": sha(raw)}
    if previous and previous.get("snapshot_sha256", binding["snapshot_sha256"]) != binding["snapshot_sha256"]:
        raise ValueError("Run snapshot bytes changed since the previous admission check")
    return binding
