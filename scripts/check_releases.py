#!/usr/bin/env python3
"""Validate public release PRs offline; never resolve or execute private engines."""
import argparse
import json
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.releases import MAX_RECORD_BYTES, SYSTEM_PATTERN, ReleaseError, _decode_record, validate_public_release


def check(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ReleaseError("Public release directory must not be a symlink")
    seen = set()
    paths = []
    # Enumerate every entry, including non-JSON files and symlinks. Glob-based
    # discovery would silently ignore private bindings or linked directories.
    for entry in sorted(root.iterdir()):
        mode = entry.lstat().st_mode
        if entry.name == "README.md" and stat.S_ISREG(mode) and entry.stat().st_size <= MAX_RECORD_BYTES:
            continue
        if not stat.S_ISDIR(mode) or not re.fullmatch(SYSTEM_PATTERN, entry.name):
            raise ReleaseError("Only README.md and regular system/version.json references are permitted")
        for path in sorted(entry.iterdir()):
            if not stat.S_ISREG(path.lstat().st_mode) or path.suffix != ".json":
                raise ReleaseError("Public release directories must contain only regular version.json references")
            paths.append(path)
    for path in paths:
        relative = path.relative_to(root)
        if (len(relative.parts) != 2 or any(p.is_symlink() for p in (path, path.parent))
                or not path.is_file() or path.stat().st_size > MAX_RECORD_BYTES):
            raise ReleaseError("Public references must be bounded system/version.json files")
        with path.open("rb") as stream:
            data = stream.read(MAX_RECORD_BYTES + 1)
        if len(data) > MAX_RECORD_BYTES:
            raise ReleaseError("Public reference exceeds its size limit")
        record = validate_public_release(_decode_record(data))
        identity = record["system"], record["version"]
        if relative.as_posix() != f"{identity[0]}/{identity[1]}.json" or identity in seen:
            raise ReleaseError("Release file path must match its unique public identity")
        seen.add(identity)
    return {"valid": True, "public_references": len(seen), "private_bindings_checked": False, "execution": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "registry/releases")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(check(args.root), sort_keys=True))
        return 0
    except (OSError, ValueError):
        parser.exit(1, "Invalid public release reference; use only schema, system and version.\n")


if __name__ == "__main__":
    raise SystemExit(main())
