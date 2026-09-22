#!/usr/bin/env python3
"""Fetch the pinned public SD1.4 files; no login, model execution, or admission."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import time
import urllib.request


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate_lock(value):
    if (value.get("schema") != "arena.lmx-sd-assets/1"
            or value.get("model_id") != "CompVis/stable-diffusion-v1-4"
            or value.get("revision") != "2880f2ca379f41b0226444936bb7a6766a227587"
            or value.get("gated") is not False):
        raise ValueError("Only the reviewed public SD1.4 checkpoint is accepted")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("A complete file lock is required")
    for name, row in files.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name or "\\" in name:
            raise ValueError("Unsafe asset path")
        if (set(row) != {"sha256", "size", "url"}
                or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                or type(row["size"]) is not int or not 0 < row["size"] < 2 * 1024 ** 3):
            raise ValueError("Invalid asset identity")
        model_url = ("https://huggingface.co/CompVis/stable-diffusion-v1-4/resolve/"
                     + value["revision"] + "/" + name + "?download=true")
        license_url = ("https://huggingface.co/spaces/CompVis/stable-diffusion-license/raw/"
                       "14d42d09bffd871b1666a084fc954a50cff72ac0/license.txt")
        if row["url"] != (license_url if name == "LICENSE_SD.txt" else model_url):
            raise ValueError("Unexpected asset download origin")
    return value


def prepare(lock_path, output):
    lock_path, output = Path(lock_path), Path(output)
    raw = lock_path.read_bytes()
    lock = validate_lock(json.loads(raw))
    if not output.is_absolute() or output.resolve() != output or output.exists():
        raise ValueError("Use a new absolute asset directory without symlinks")
    output.mkdir(mode=0o700, parents=True)
    started, records = time.time(), []
    for name, row in lock["files"].items():
        target = output / name
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".partial")
        # All requests are public and contain no auth headers or stored HF token.
        with urllib.request.urlopen(row["url"], timeout=90) as response:
            with temporary.open("xb") as stream:
                count = 0
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    count += len(block)
                    if count > row["size"]:
                        raise ValueError("Asset exceeds pinned size")
                    stream.write(block)
                stream.flush()
                os.fsync(stream.fileno())
        if count != row["size"] or digest(temporary) != row["sha256"]:
            raise ValueError(f"Asset integrity mismatch: {name}")
        temporary.chmod(0o444)
        temporary.rename(target)
        records.append({"path": name, "sha256": row["sha256"], "size": count})
        print(json.dumps({"downloaded": name, "bytes": count}), flush=True)
    for directory in sorted((p for p in output.rglob("*") if p.is_dir()), reverse=True):
        directory.chmod(0o555)
    output.chmod(0o555)
    receipt = {"schema": "arena.lmx-sd-asset-preparation/1", "status": "verified",
               "manifest_sha256": hashlib.sha256(raw).hexdigest(), "directory": str(output),
               "model_id": lock["model_id"], "revision": lock["revision"],
               "license": lock["license"], "files": records, "model_calls": 0,
               "gated_agreement_accepted": False, "started_at": started,
               "finished_at": time.time()}
    path = output.with_name(output.name + "-receipt.json")
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    prepare(args.lock, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
