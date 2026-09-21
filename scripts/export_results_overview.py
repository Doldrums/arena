#!/usr/bin/env python3
"""Publish an allowlisted aggregate from an operator-supplied private results file.

This script is offline. It never obtains credentials, contacts the worker or
launches experiments. The output can be reviewed and deployed with the catalog.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.registry import RegistryError, _json
from arena.results_overview import build_results_overview


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise RegistryError("Input and published output must be different files")
        if not args.input.is_file() or args.input.is_symlink() or args.input.stat().st_size > 32 * 1024 * 1024:
            raise RegistryError("Expected a bounded regular input file")
        value = build_results_overview(_json(args.input))
        # Atomic replacement; never leave a half-published snapshot on disk.
        temporary = args.output.with_name(args.output.name + ".tmp")
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        temporary.replace(args.output)
        print(json.dumps({"published": True, "loaded": value["loaded"], "truncated": value["truncated"], **value["summary"]}))
    except (RegistryError, OSError) as error:
        # Do not echo private input values or paths.
        parser.exit(1, "Results overview export failed: invalid input or output unavailable.\n")


if __name__ == "__main__":
    main()
