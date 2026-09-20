#!/usr/bin/env python3
"""Create reviewed metadata from a local GitHub checkout at an exact commit.

No fetch, install, evaluator import, task execution, credentials or run results.
The generated diff must be submitted with its registration in a registry PR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.registry import (RegistryError, build_catalog, validate_registration, validate_registry)
from arena.participant_corpus import expected_participants


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _problem_files(checkout, commit, records):
    """Read all problem declarations in one Git call, without checking them out."""
    identifiers = [record.get("id") for record in records]
    if not all(isinstance(ident, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", ident) for ident in identifiers):
        raise RegistryError("Source task IDs must be safe identifiers")
    query = "".join(f"{commit}:suite/{ident}/problem.json\n" for ident in identifiers).encode()
    result = subprocess.run(["git", "-C", str(checkout), "cat-file", "--batch"], input=query,
                            capture_output=True, check=True)
    data, offset, files = result.stdout, 0, {}
    for ident in identifiers:
        end = data.find(b"\n", offset)
        if end < 0:
            raise RegistryError("Incomplete Git object response")
        header, offset = data[offset:end].split(), end + 1
        if header[-1:] == [b"missing"]:
            continue
        if len(header) != 3 or header[1] != b"blob" or not header[2].isdigit():
            raise RegistryError("Problem source must be a Git blob")
        size = int(header[2])
        if size > 2_000_000 or data[offset + size:offset + size + 1] != b"\n":
            raise RegistryError("Invalid or oversized problem declaration")
        files[ident] = data[offset:offset + size]
        offset += size + 1
    if offset != len(data):
        raise RegistryError("Unexpected trailing Git object response")
    return files


def synchronize(checkout, registration, registry_root):
    validate_registration(registration)
    registered = [json.loads(path.read_text()) for path in sorted((registry_root / "task-sources").glob("*.json"))]
    if len(registered) != 1 or registered[0] != registration:
        raise RegistryError("This initial importer supports exactly one matching task collection; multi-source merging is not implemented. No snapshots were changed.")
    commit = registration["repository"]["commit"]
    source = {"id": registration["snapshot_source_id"], "repository": registration["repository"],
              "catalog_path": registration["manifest_path"], "index_path": "suite/index.json"}
    contents = {}
    for key in ("catalog", "index"):
        # Read committed Git objects, not potentially modified working-tree files.
        content = subprocess.check_output(["git", "-C", str(checkout), "show", f"{commit}:{source[key + '_path']}"], stderr=subprocess.PIPE)
        source[key + "_sha256"] = hashlib.sha256(content).hexdigest()
        contents[key] = json.loads(content)
    problems = _problem_files(checkout, commit, contents["catalog"])
    catalog = build_catalog(contents["catalog"], contents["index"], source, problems)
    participants = expected_participants(registry_root)
    _write(registry_root / "catalog.json", catalog)
    _write(registry_root / "participants.json", participants)
    return validate_registry(registry_root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--registry-root", type=Path, default=ROOT / "registry")
    parser.add_argument("--registration", default="task-sources/autoresearch-tasks.json")
    args = parser.parse_args(argv)
    try:
        registration = json.loads((args.registry_root / args.registration).read_text())
        print(json.dumps(synchronize(args.checkout, registration, args.registry_root), indent=2))
    except (RegistryError, subprocess.SubprocessError, OSError, ValueError) as exc:
        print(f"Snapshot synchronization failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
