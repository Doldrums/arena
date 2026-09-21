#!/usr/bin/env python3
"""Admit a prepared SCiEL campaign in bounded, resumable queue batches.

Uses only the private loopback control API. No token, prompt, private binding or
upstream response is logged. Stop on control drift or a failed batch; resume uses
the same idempotency keys and never silently retries scientific experiments.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

TERMINAL = {"completed", "failed", "cancelled", "blocked"}
STATES = TERMINAL | {"queued", "preparing", "running"}
CONTROL_ORIGIN = "http://127.0.0.1:8080"
MAX_RESPONSE = 8 * 1024 * 1024


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read_bytes(path, maximum=MAX_RESPONSE, *, private=False):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or path.resolve() != path:
        raise ValueError("Input path must be absolute and must not traverse symlinks")
    descriptors = []
    try:
        parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        descriptors.append(parent)
        for part in path.parts[1:-1]:
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            descriptors.append(parent)
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        descriptors.append(descriptor)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_size > maximum
                or private and (info.st_mode & 0o077 or info.st_uid not in {0, os.geteuid()})):
            raise ValueError("Input must be a bounded owned private regular file")
        chunks, size = [], 0
        while chunk := os.read(descriptor, min(65536, maximum + 1 - size)):
            chunks.append(chunk)
            size += len(chunk)
            if size > maximum:
                raise ValueError("Input exceeds the size limit")
        after = os.fstat(descriptor)
        if any(getattr(info, key) != getattr(after, key) for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")):
            raise ValueError("Input changed while being read")
        return b"".join(chunks)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def read_key(path):
    try:
        value = json.loads(read_bytes(path, 8192, private=True))["token"]
    except (ValueError, OSError, KeyError, TypeError):
        raise ValueError("Control key must be a bounded owned private credential file") from None
    if type(value) is not str or not re.fullmatch(r"arena_[A-Za-z0-9_-]{20,100}", value):
        raise ValueError("Invalid private control credential")
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Control:
    def __init__(self, token):
        self.token = token
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def call(self, path, body=None):
        if not re.fullmatch(r"/api/(?:control/(?:templates|reload)|queue(?:/[a-f0-9]{32})?)(?:\?limit=200&offset=[0-9]+)?", path):
            raise ValueError("Only fixed private control routes are allowed")
        if path == "/api/control/reload" and body != {}:
            raise ValueError("Reload requires an explicit empty object")
        request = Request(CONTROL_ORIGIN + path,
                          data=None if body is None else encoded(body),
                          headers={"Authorization": "Bearer " + self.token,
                                   "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise RuntimeError("Private control response exceeds its limit")
                value = json.loads(raw)
                if type(value) is not dict:
                    raise ValueError("Invalid control response shape")
                return value
        except HTTPError as error:
            error.close()
            raise RuntimeError(f"Private control returned HTTP {error.code}") from None
        except (URLError, OSError, ValueError):
            raise RuntimeError("Private control returned no usable response") from None

    def runs(self):
        first = self.call("/api/queue?limit=200&offset=0")
        if type(first.get("total")) is not int or not 0 <= first["total"] <= 200000:
            raise ValueError("Private queue inventory exceeds inspection limits")
        rows = list(first["runs"])
        for offset in range(200, first["total"], 200):
            rows.extend(self.call(f"/api/queue?limit=200&offset={offset}")["runs"])
        return list({row["id"]: row for row in rows}.values())


def validate_templates(planned, live):
    if (type(live.get("limits")) is not dict or type(live["limits"].get("max_active")) is not int
            or not 1 <= live["limits"]["max_active"] <= 4):
        raise ValueError("Live queue must limit admission to at most four active experiments")
    by_id = {row["id"]: row for row in live["templates"]}
    if not planned or len({row["id"] for row in planned}) != len(planned):
        raise ValueError("Campaign needs a nonempty list of unique prepared templates")
    for row in planned:
        if (row != by_id.get(row["id"]) or row["framework"] != "sciel-release"
                or row["status"] != "ready" or "astra" in row["model"].lower()):
            raise ValueError("Prepared template differs from the live reviewed configuration")


def submission(template, campaign, batch):
    return {"schema": "arena.control-submit/1", "template": template["id"],
            "model": template["model"], "label": template["name"][:128],
            "batch_id": f"{campaign}-b{batch:03d}",
            "idempotency_key": campaign + "-" + hashlib.sha256(template["id"].encode()).hexdigest()[:20]}


def batch_state(runs, templates, batch_id):
    ids = {row["id"] for row in templates}
    selected = [row for row in runs if row["template"] in ids and row.get("batch_id") == batch_id]
    by_template = {row["template"]: row for row in selected}
    if len(selected) != len(by_template):
        raise ValueError("Duplicate experiments exist for this campaign batch")
    if any(row["state"] not in STATES for row in selected):
        raise ValueError("Unknown queue state; campaign admission must stop")
    counts = dict(Counter(row["state"] for row in selected))
    finished = len(selected) == len(templates) and all(row["state"] in TERMINAL for row in selected)
    failures = sum(row["state"] != "completed" for row in selected)
    return selected, counts, finished, finished and failures >= math.ceil(len(templates) / 4)


def verify_run(row, template, batch_id, revision):
    if (type(row.get("id")) is not str or not re.fullmatch(r"[a-f0-9]{32}", row["id"])
            or row.get("template") != template["id"] or row.get("model") != template["model"]
            or row.get("framework") != "sciel-release" or row.get("label") != template["name"][:128]
            or row.get("batch_id") != batch_id or row.get("revision") != revision):
        raise ValueError("Admitted experiment differs from its reviewed request")


def native_issue(row, state_dir):
    """A zero CLI exit code alone does not establish a completed research run."""
    if row["state"] != "completed":
        return None
    path = state_dir / "runs" / row["id"] / "artifacts/.arena/native-result.json"
    try:
        native = json.loads(read_bytes(path, 2 * 1024 * 1024))
    except (OSError, ValueError):
        return "native_evidence_unavailable"
    if (type(native) is not dict or native.get("schema") != "arena.native-result/1"
            or native.get("framework") != "sciel-release" or native.get("status") != "recorded"):
        return "native_completion_unverified"
    details = native.get("native")
    if type(details) is not dict or type(details.get("reason")) is not str or not details["reason"].strip():
        return "native_stop_reason_unavailable"
    reason = details["reason"].lower()
    if any(word in reason for word in ("research_stopped", "provider", "error", "failed", "recovery")):
        return "native_research_stopped"
    return None


def verify_live(control, path, planned, revision):
    live = json.loads(read_bytes(path))
    validate_templates(planned, live)
    if hashlib.sha256(encoded(live)).hexdigest() != revision:
        raise ValueError("Control configuration changed during campaign admission")
    runtime = control.call("/api/control/templates")
    if runtime.get("revision") != revision or runtime.get("limits") != live["limits"]:
        raise ValueError("Running control service differs from its reviewed configuration")


@contextmanager
def campaign_lock(path):
    lock = path.with_name(path.name + ".lock")
    if lock.resolve() != lock:
        raise ValueError("Campaign lock must not traverse symlinks")
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                or info.st_uid not in {0, os.geteuid()}):
            raise ValueError("Campaign lock must be an owned private regular file")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another process is admitting this campaign") from None
        yield
    finally:
        os.close(descriptor)


def write_status(path, value):
    if path.resolve() != path:
        raise ValueError("Status must not traverse symlinks")
    temporary = path.with_name(path.name + f".{os.getpid()}.pending")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded(value) + b"\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_resume(path, summary):
    if path.exists():
        previous = json.loads(read_bytes(path, private=True))
        for key in ("schema", "campaign", "templates_sha256", "batch_size", "models", "control_revision"):
            if previous.get(key) != summary[key]:
                raise ValueError("Resume requires the same campaign, templates, model, batch size and control revision")


def admit(args, planned, summary, live):
    control = Control(read_key(args.key_file))
    revision = summary["control_revision"]
    state_dir = Path(live["state_dir"])
    verify_live(control, args.control_config, planned, revision)
    existing = control.runs()
    assignments = {row["id"]: f"{args.campaign}-b{index:03d}"
        for index, start in enumerate(range(0, len(planned), args.batch_size), 1)
        for row in planned[start:start + args.batch_size]}
    for row in existing:
        batch = row.get("batch_id") or ""
        if batch.startswith(args.campaign + "-b") and assignments.get(row["template"]) != batch:
            raise ValueError("Existing campaign runs have a different batch assignment")
    summary.update(state="running", updated_at=time.time())
    write_status(args.status, summary)
    for index, start in enumerate(range(0, len(planned), args.batch_size), 1):
        wave = planned[start:start + args.batch_size]
        batch_id = f"{args.campaign}-b{index:03d}"
        verify_live(control, args.control_config, planned, revision)
        rows, _, _, _ = batch_state(existing, wave, batch_id)
        admitted = {row["template"]: row for row in rows}
        for template in wave:
            run = admitted.get(template["id"])
            if run is None:
                run = control.call("/api/queue", submission(template, args.campaign, index))["run"]
            verify_run(run, template, batch_id, revision)
            admitted[template["id"]] = run
        previous = None
        while True:
            verify_live(control, args.control_config, planned, revision)
            rows = []
            for template in wave:
                row = control.call("/api/queue/" + admitted[template["id"]]["id"])["run"]
                verify_run(row, template, batch_id, revision)
                rows.append(row)
            rows, counts, finished, failed = batch_state(rows, wave, batch_id)
            issues = {row["id"]: problem for row in rows if (problem := native_issue(row, state_dir))}
            record = {"batch_id": batch_id, "counts": counts, "native_issues": issues, "runs": [
                {key: row[key] for key in ("id", "template", "model", "state")} for row in rows]}
            state = "paused_native_evidence" if issues else "paused_after_failures" if failed else "running"
            summary.update(state=state, updated_at=time.time())
            summary["batches"] = summary["batches"][:index - 1] + [record]
            write_status(args.status, summary)
            if counts != previous:
                print(json.dumps({"batch_id": batch_id, "counts": counts}), flush=True)
                previous = counts
            if failed or issues:
                return 2
            if finished:
                break
            time.sleep(15)
    summary.update(state="completed", updated_at=time.time())
    write_status(args.status, summary)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--templates", type=Path, required=True)
    parser.add_argument("--control-config", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--admit", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.campaign) or not 1 <= args.batch_size <= 16:
        parser.error("Use a short campaign name and batches of 1–16 experiments")
    if not args.status.is_absolute() or args.status.resolve() != args.status:
        parser.error("Status must use an absolute private path without symlinks")
    raw = read_bytes(args.templates)
    planned = json.loads(raw)
    live = json.loads(read_bytes(args.control_config))
    validate_templates(planned, live)
    summary = {"schema": "arena.sciel-catalog-admission/1", "campaign": args.campaign,
               "templates_sha256": hashlib.sha256(raw).hexdigest(), "planned": len(planned),
               "batch_size": args.batch_size, "models": sorted({row["model"] for row in planned}),
               "control_revision": hashlib.sha256(encoded(live)).hexdigest(),
               "batches": [], "state": "preview", "updated_at": time.time()}
    print(json.dumps({key: summary[key] for key in ("campaign", "planned", "batch_size", "models")}), flush=True)
    if not args.admit:
        return 0
    with campaign_lock(args.status):
        validate_resume(args.status, summary)
        try:
            return admit(args, planned, summary, live)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            summary.update(state="paused_control_error", updated_at=time.time())
            write_status(args.status, summary)
            print("Campaign admission paused; verify private control and recorded configuration.", flush=True)
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
