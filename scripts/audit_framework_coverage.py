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
    return {"schema": "arena.framework-coverage/1", "as_of": "2026-09-21",
            "summary": {"participants": len(rows), "paper_ids": len({p["id"] for r in rows for p in r["papers"]}),
                        "participant_status_counts": counts,
                        "recipe_engines": len(recipes), "direct_adapters": len(DIRECT),
                        "additional_engines_without_paper_assignment": len(extras)},
            "bindings": bindings, "participants": rows, "additional_engines": extras}


def render(report: dict) -> str:
    summary = report["summary"]
    lines = ["# Framework coverage audit — 2026-09-21", "",
             "This is a source/interface inventory, not a leaderboard or a statement that research runs have completed. "
             "All joins use explicit participant IDs. A task evaluator, baseline repository, result notebook and search engine are different artifacts.", "",
             f"The registry contains **{summary['participants']} participant records** and **{summary['paper_ids']} distinct paper IDs**. "
             f"It has **{summary['direct_adapters']} direct adapters** and **{summary['recipe_engines']} recipe records** "
             "(including explicit blockers and artifact interfaces). Multiple recipe records can belong to one work.", "",
             "| Participant coverage | Count |", "| --- | ---: |"]
    labels = {"native_interface": "Native source interface present", "artifact_only": "Artifact interface only",
              "recorded_blocker": "Recorded implementation/integration blocker", "unaccounted": "Unaccounted"}
    for key in ("native_interface", "artifact_only", "recorded_blocker", "unaccounted"):
        lines.append(f"| {labels[key]} | {summary['participant_status_counts'].get(key, 0)} |")
    lines += ["", "## Scope and source basis", "",
              "- `source_verified` means a concrete, pinned native interface was inspected and adapter preparation was checked. "
              "It does not establish that its dependencies, credentials, hardware or native evaluation currently work.",
              "- Canonical evaluator bridges currently exist for the documented SCiEL/Shinka profiles. "
              "All other recipe evaluations retain native metrics and do not assert shared-task compatibility, held-out validity or comparable cost accounting.",
              "- The primary source inventory is [autoresearch-tasks/catalog/papers.json at 5729caa7](https://github.com/IMRUNya/autoresearch-tasks/blob/5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935/catalog/papers.json). "
              "Its task/benchmark source relationships are preserved rather than reinterpreted as engine releases.",
              "- Additional paper-link discovery covered 35 initially unassigned works: 32 arXiv HTML retrievals succeeded; DrSR, ReDAHD and RQGM HTML retrievals failed. "
              "Successful retrieval hashes and URLs are retained in the relevant blocker records. A missing implementation in this audit is not proof that none exists.",
              "- EoB, EvoOR-Agent, DrEureka and LaSR were found as genuine source implementations and have concrete native profiles. "
              "EvoOR has an explicitly recorded configuration-only portability patch; LaSR uses a separately fingerprinted Julia executable.",
              "- AlphaEvolve's official results repository excludes its search engine. DrSR's CoEvo link is a benchmark source; "
              "FunBO's MetaBO link is a comparison/objective source. These links do not supply those papers' search loops.",
              "- READY links an anonymous project that could not be retrieved and pinned in this audit. "
              "Community reimplementations, when present, retain their own repository identity and are not attributed to the original paper authors.",
              "", "## Every participant", "", "| Participant / research source | Coverage | Native interfaces or blocker |",
              "| --- | --- | --- |"]
    def clean(text):
        return str(text).replace("|", "\\|").replace("\n", " ")
    for row in report["participants"]:
        paper = row["papers"][0] if row["papers"] else None
        name = f"[{clean(row['name'])}]({paper['url']})" if paper else clean(row["name"])
        descriptions = []
        for interface in row["interfaces"]:
            repository = interface["repository"]
            ref = f"`{interface['id']}`"
            if repository:
                ref = f"[{ref}]({repository['url']}/tree/{repository['commit']})"
            descriptions.append(ref + (": " + clean(interface["reason"]) if interface["reason"] else
                                       f" ({interface['status']}; {interface['profile_count']} profile(s))"))
        lines.append(f"| {name} (`{row['id']}`) | {labels[row['status']]} | {'; '.join(descriptions)} |")
    if report["additional_engines"]:
        lines += ["", "## Additional engines without a corpus-paper assignment", ""]
        for engine in report["additional_engines"]:
            repo = engine["repository"]
            link = f"[{engine['id']}]({repo['url']}/tree/{repo['commit']})" if repo else engine["id"]
            lines.append(f"- {link}: {engine['status']}, {engine['profile_count']} profile(s).")
    lines += ["", "## Offline validation and reproducibility", "",
              "`python scripts/audit_framework_coverage.py --check` validates registered recipe shapes, identity joins, "
              "direct adapter presence, complete participant accounting and this committed report. `--json` emits the same inventory as JSON. "
              "The command reads local metadata only; it never imports native packages, launches evaluators or contacts a provider.",
              "", "Snapshot bindings:", ""]
    for path, digest in report["bindings"].items():
        lines.append(f"- `{path}`: `{digest}`")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/framework-coverage-20260921.md")
    args = parser.parse_args(argv)
    report = audit()
    if report["summary"]["participant_status_counts"].get("unaccounted", 0):
        print("Unaccounted participant identities remain", file=sys.stderr)
        return 1
    text = render(report)
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.check:
        if not args.output.is_file() or args.output.read_text() != text:
            print("Framework coverage report is stale; rebuild with scripts/audit_framework_coverage.py", file=sys.stderr)
            return 1
        print("Framework coverage: all participants accounted for; report current")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
