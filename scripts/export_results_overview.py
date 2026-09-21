#!/usr/bin/env python3
"""Publish an allowlisted aggregate from an operator-supplied private results file.

This script is offline. It never obtains credentials, contacts the worker or
launches experiments. The output can be reviewed and deployed with the catalog.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.registry import RegistryError, _json
from arena.results_overview import build_results_overview, validate_results_overview
from arena.results_research import validate_results_research


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Private canonical results response")
    source.add_argument("--published-input", type=Path,
                        help="Existing public snapshot; refresh research while preserving canonical data and its source time")
    parser.add_argument("--research-input", type=Path,
                        help="Optional validated published observer section; never a raw native artifact")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        source_path = args.input or args.published_input
        if source_path.resolve() == args.output.resolve():
            raise RegistryError("Input and published output must be different files")
        if not source_path.is_file() or source_path.is_symlink() or source_path.stat().st_size > 32 * 1024 * 1024:
            raise RegistryError("Expected a bounded regular input file")
        research = None
        if args.research_input is not None:
            if (args.research_input.resolve() == args.output.resolve()
                    or not args.research_input.is_file() or args.research_input.is_symlink()
                    or args.research_input.stat().st_size > 4 * 1024 * 1024):
                raise RegistryError("Expected a separate bounded regular research section")
            research = _json(args.research_input)
        if args.published_input is not None:
            if research is None:
                raise RegistryError("Research refresh requires a separate validated research section")
            value = deepcopy(validate_results_overview(_json(source_path)))
            value["research"] = validate_results_research(research)
            value["generated_at"] = time.time()
            validate_results_overview(value)
        else:
            value = build_results_overview(_json(source_path), research=research)
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
