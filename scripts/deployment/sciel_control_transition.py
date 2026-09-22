"""Validate explicit frozen append-only control transitions for a campaign.

The operator supplies a private descriptor with schema
arena.control-append-transition/1, previous/next {path, sha256, revision}, and
added_template_ids in append order. Each path identifies a separate frozen
control JSON snapshot, not the live configuration. sha256 binds its exact bytes;
revision binds the control service's canonical JSON representation.

A chain descriptor uses schema arena.control-append-chain/1 and an ordered
transitions list of {path, sha256} references to single-transition descriptors.
Every link must retain its predecessor's complete configuration. Existing
campaigns may explicitly extend a recorded chain, but never replace its prefix.
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


def _load_single(path, *, control_path, read, encode):
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
    if (encode({**new, "templates": new["templates"][:prefix]}) != encode(old) or not added
            or descriptor["added_template_ids"] != [row["id"] for row in added]):
        raise ValueError("Transition must only append the declared unique templates")
    identity = {"schema": descriptor["schema"], "sha256": sha(raw),
                "previous_revision": descriptor["previous"]["revision"],
                "next_revision": descriptor["next"]["revision"],
                "added_template_ids": descriptor["added_template_ids"]}
    return {"path": path, "control_path": control_path, "identity": identity, **configurations}


def load_transition(path, *, control_path, read, encode):
    path, control_path = Path(path), Path(control_path)
    raw = read(path, private=True)
    descriptor = decode(raw)
    if type(descriptor) is not dict or descriptor.get("schema") != "arena.control-append-chain/1":
        return _load_single(path, control_path=control_path, read=read, encode=encode)
    entries = descriptor.get("transitions")
    if (set(descriptor) != {"schema", "transitions"} or type(entries) is not list
            or not 2 <= len(entries) <= 64):
        raise ValueError("Expected a bounded ordered chain of explicit transitions")
    links, paths = [], {path, control_path}
    for entry in entries:
        if (type(entry) is not dict or set(entry) != {"path", "sha256"}
                or type(entry["path"]) is not str or type(entry["sha256"]) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])):
            raise ValueError("Every chain link needs an exact descriptor path and hash")
        child = Path(entry["path"])
        if child in paths or sha(read(child, private=True)) != entry["sha256"]:
            raise ValueError("Repeated or modified chain descriptor")
        paths.add(child)
        link = _load_single(child, control_path=control_path, read=read, encode=encode)
        if link["identity"]["sha256"] != entry["sha256"]:
            raise ValueError("Chain descriptor changed while being read")
        if links and (encode(links[-1]["next"]) != encode(link["previous"])
                      or links[-1]["identity"]["next_revision"] != link["identity"]["previous_revision"]):
            raise ValueError("Control transition chain must be contiguous")
        links.append(link)
    identity = {"schema": descriptor["schema"], "sha256": sha(raw),
                "previous_revision": links[0]["identity"]["previous_revision"],
                "next_revision": links[-1]["identity"]["next_revision"],
                "added_template_ids": [ident for link in links
                                       for ident in link["identity"]["added_template_ids"]],
                "transitions": [link["identity"] for link in links]}
    return {"path": path, "control_path": control_path, "identity": identity,
            "previous": links[0]["previous"], "next": links[-1]["next"]}


def revisions(identity):
    links = identity.get("transitions", [identity])
    return [identity["previous_revision"], *[link["next_revision"] for link in links]]


def observe_admission(transition, summary, revision):
    """A verified POST/GET receipt is also evidence of an activated revision."""
    accepted = revisions(transition["identity"])
    previous = summary.get("active_control_revision", accepted[0])
    if revision not in accepted or previous not in accepted:
        raise ValueError("Observed admission uses an unapproved control revision")
    summary["active_control_revision"] = accepted[max(accepted.index(previous), accepted.index(revision))]


def validate_resume_transition(previous, summary):
    old, new = previous.get("control_transition"), summary.get("control_transition")
    if old and old != new:
        old_links = old.get("transitions", [old])
        new_links = new.get("transitions", []) if new else []
        if len(new_links) <= len(old_links) or new_links[:len(old_links)] != old_links:
            raise ValueError("Resume requires the same explicit control transition or its chained extension")
    if new:
        accepted = revisions(new)
        prior = previous.get("active_control_revision", previous["control_revision"])
        current = summary["active_control_revision"]
        if prior not in accepted or current not in accepted or accepted.index(current) < accepted.index(prior):
            raise ValueError("Resume cannot revert an approved control append")


def current_revision(transition, live, summary, *, read, encode):
    checked = load_transition(transition["path"], control_path=transition["control_path"], read=read, encode=encode)
    if checked["identity"] != transition["identity"]:
        raise ValueError("Explicit control transition changed during admission")
    revision = sha(encode(live))
    accepted = revisions(transition["identity"])
    if revision not in accepted:
        raise ValueError("Live control revision is outside the explicit transition")
    previous = summary.get("active_control_revision", accepted[0])
    if previous not in accepted or accepted.index(revision) < accepted.index(previous):
        raise ValueError("Control revision cannot revert after the approved append")
    summary["active_control_revision"] = revision
    return revision


def snapshot_binding(row, template, transition, previous, *, read, encode):
    revision = row.get("revision")
    accepted = revisions(transition["identity"])
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
