#!/usr/bin/env python3
"""Offline join of scholarly participants and reviewed native interfaces.

This does not install/import a framework, fetch sources or run an experiment.
Multiple engines can reference one paper; engine counts are not paper counts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.recipes import load_recipes

DIRECT = {"sciel": "sciel.py", "shinka": "shinka.py", "dgm": "dgm.py"}


def audit(root: Path = ROOT) -> dict:
    registry = root / "registry"
    document = json.loads((registry / "participants.json").read_text())
    participants = document["participants"]
    ids = [p["id"] for p in participants]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate scholarly participant identity")
    recipes = load_recipes(registry)
    associated = {identity: [] for identity in ids}
    extras = []
    for recipe in recipes.values():
        unknown = set(recipe["participant_ids"]) - associated.keys()
        if unknown:
            raise ValueError(f"Unknown recipe participant identities: {sorted(unknown)}")
        record = {"id": recipe["id"], "status": recipe["status"],
                  "repository": recipe["repository"], "profile_count": len(recipe["profiles"]),
                  "reason": recipe["blocked_reason"], "basis": recipe["setup"]}
        if not recipe["participant_ids"]:
            extras.append(record)
        for identity in recipe["participant_ids"]:
            associated[identity].append(record)
    for identity, filename in DIRECT.items():
        if identity not in associated:
            raise ValueError(f"Missing direct participant {identity}")
        module = root / "src/arena/frameworks" / filename
        if not module.is_file():
            raise ValueError(f"Missing native adapter module for {identity}")
        participant = next(p for p in participants if p["id"] == identity)
        associated[identity].append({
            "id": identity, "status": "source_verified", "repository": participant["repository"],
            "profile_count": 1, "reason": None,
            "basis": [f"src/arena/frameworks/{filename}; SHA256 {hashlib.sha256(module.read_bytes()).hexdigest()}"]})
    rows = []
    for participant in sorted(participants, key=lambda p: p["id"]):
        implementations = sorted(associated[participant["id"]], key=lambda r: r["id"])
        if any(r["status"] == "source_verified" and r["profile_count"] for r in implementations):
            status = "native_interface"
        elif any(r["status"] == "artifact_only" for r in implementations):
            status = "artifact_only"
        elif implementations:
            status = "recorded_blocker"
        else:
            status = "unaccounted"
        rows.append({"id": participant["id"], "name": participant["name"], "status": status,
                     "papers": participant.get("papers", []), "interfaces": implementations})
    counts = dict(sorted(Counter(r["status"] for r in rows).items()))
    bindings = {"registry/participants.json": hashlib.sha256((registry / "participants.json").read_bytes()).hexdigest()}
    for path in sorted((registry / "framework-recipes").glob("*.json")):
        bindings[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"schema": "arena.framework-coverage/1",
            "summary": {"participants": len(rows), "paper_ids": len({p["id"] for r in rows for p in r["papers"]}),
                        "participant_status_counts": counts,
                        "recipe_engines": len(recipes), "direct_adapters": len(DIRECT),
                        "additional_engines_without_paper_assignment": len(extras)},
            "bindings": bindings, "participants": rows, "additional_engines": extras}




def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path, help="Write the verified inventory as JSON")
    args = parser.parse_args(argv)
    report = audit()
    if report["summary"]["participant_status_counts"].get("unaccounted", 0):
        print("Unaccounted participant identities remain", file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.check:
        print("Framework coverage: all participants accounted for")
    else:
        print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
