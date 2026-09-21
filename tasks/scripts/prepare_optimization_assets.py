#!/usr/bin/env python3
"""Fetch hash-pinned original POMO/LEHD/DevFormer inputs into ReEvo's cache.

Run ``python run.py setup reevo-tsp-gls`` first. No model API calls are made.
"""

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import cache_path
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import zipfile


def matches(filename, record):
    return (filename.is_file() and filename.stat().st_size == record["bytes"] and
            hashlib.sha256(filename.read_bytes()).hexdigest() == record["sha256"])


def download(record, directory):
    if not record["url"].startswith("https://"):
        raise ValueError("Asset source must use HTTPS")
    target = directory / record["sha256"]
    directory.mkdir(parents=True, exist_ok=True)
    if matches(target, record):
        return target
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            with urllib.request.urlopen(record["url"], timeout=60) as response:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > record["bytes"]:
                        raise ValueError("Download exceeded pinned byte size")
                    stream.write(chunk)
            stream.flush()
            if not matches(temporary, record):
                raise ValueError("Downloaded asset does not match pinned hash/size")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["pomo", "lehd", "dpp", "all"], default="all")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "adapters/recovered/optimization_assets.json").read_text())
    source = lock["checkout"]
    slug = source["repository"].split("github.com/")[-1].replace("/", "--")
    checkout = cache_path("upstreams") / slug / source["commit"]
    if not checkout.is_dir():
        raise SystemExit("Run python run.py setup reevo-tsp-gls first")
    revision = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if revision != source["commit"]:
        raise ValueError("ReEvo checkout revision differs from lock")
    cache = cache_path("downloads", "optimization")
    results = []
    for asset in lock["assets"]:
        if args.only != "all" and args.only not in asset["path"]:
            continue
        target = (checkout / asset["path"]).resolve()
        if not target.is_relative_to(checkout.resolve()):
            raise ValueError("Asset target escapes pinned checkout")
        valid = matches(target, asset)
        if not valid and not args.verify_only:
            fetched = download(asset.get("archive", asset), cache)
            if "archive_member" in asset:
                with zipfile.ZipFile(fetched) as archive:
                    info = archive.getinfo(asset["archive_member"])
                    if info.file_size != asset["bytes"]:
                        raise ValueError("Archive member exceeds pinned size")
                    data = archive.read(info)
            else:
                data = fetched.read_bytes()
            if hashlib.sha256(data).hexdigest() != asset["sha256"]:
                raise ValueError("Extracted asset hash mismatch")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                temp = Path(stream.name)
                try:
                    stream.write(data); stream.flush(); temp.replace(target)
                finally:
                    temp.unlink(missing_ok=True)
            valid = matches(target, asset)
        results.append({"path": asset["path"], "verified": valid, "sha256": asset["sha256"]})
    print(json.dumps({"verified": all(result["verified"] for result in results), "assets": results}, indent=2))
    if not all(result["verified"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
