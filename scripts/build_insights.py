#!/usr/bin/env python3
"""Build/check scientific metadata from the local pinned catalog, entirely offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.insights import build_insights, get_insights
from arena.registry import RegistryError, _json, resolve_registry_root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-root", type=Path)
    parser.add_argument("--check", action="store_true", help="Fail if the committed snapshot is stale; never write")
    args = parser.parse_args()
    root = resolve_registry_root(args.registry_root)
    try:
        if args.check:
            insights = get_insights(root)
        else:
            insights = build_insights(_json(root / "catalog.json"), _json(root / "taxonomy.json"))
            target = root / "insights.json"
            temporary = target.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(insights, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            temporary.replace(target)
        print(json.dumps({"valid": True, **insights["summary"]}, sort_keys=True))
    except RegistryError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
