#!/usr/bin/env python3
"""Build/check the source-declared research-family map without task execution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.registry import RegistryError, _json, resolve_registry_root
from arena.task_source_reader import TaskSourceReader
from arena.search_families import (SUPPLEMENT_FAMILIES, build_search_families,
                                   get_search_families, validate_sources)


def capture_sources(checkout, catalog, *, registry_root=None):
    if len(catalog["sources"]) != 1:
        raise RegistryError("This source extractor requires one reviewed task collection")
    binding = catalog["sources"][0]
    reader = TaskSourceReader(checkout, binding, registry_root=registry_root, require_clean=False)
    captured, files = {}, []
    for name in ("papers", "corpus", "research"):
        path = f"catalog/{name}.json"
        captured[name] = json.loads(reader.read(path))
        files.append(reader.evidence(path))
    corpus = {paper["id"]: paper for paper in captured["corpus"]}
    research = {paper["paper_id"]: paper for paper in captured["research"]}
    if len(corpus) != len(captured["corpus"]) or len(research) != len(captured["research"]) or set(corpus) != set(research):
        raise RegistryError("Source corpus/research paper inventories disagree or contain duplicates")
    records = []
    for paper in captured["papers"]:
        ident = paper["id"]
        if ident in SUPPLEMENT_FAMILIES:
            if ident in corpus or paper.get("family") != SUPPLEMENT_FAMILIES[ident]:
                raise RegistryError("Supplement identity or family differs from reviewed source")
        else:
            if ident not in corpus or paper.get("family") != corpus[ident].get("family"):
                raise RegistryError("Source corpus/papers family labels disagree")
        records.append({"id": ident, "name": paper["name"], "title": paper["title"],
                        "declared_family": paper.get("family"), "paper_url": paper.get("paper_url"),
                        "corpus_url": paper.get("corpus_url"),
                        "source_kind": "supplement" if ident in SUPPLEMENT_FAMILIES else "corpus_paper",
                        # Several source rows can merge into one canonical task.
                        "declared_task_ids": sorted(set(paper["task_ids"]))})
    if {paper["id"] for paper in records if paper["source_kind"] == "corpus_paper"} != set(corpus):
        raise RegistryError("Source papers do not cover the corpus exactly")
    result = {"schema": "arena.search-family-sources/1", "catalog_binding": binding,
              "files": files, "papers": sorted(records, key=lambda paper: paper["id"])}
    validate_sources(result, catalog)
    return result


def _write(path, value):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-root", type=Path)
    parser.add_argument("--checkout", type=Path, help="Task library directory; bundled tasks are the default")
    parser.add_argument("--check", action="store_true", help="Verify committed snapshots without writing")
    args = parser.parse_args()
    root = resolve_registry_root(args.registry_root)
    try:
        catalog = _json(root / "catalog.json")
        checkout = args.checkout
        if checkout is None and not args.check and catalog["sources"][0].get("kind") == "bundled":
            checkout = root.parent / catalog["sources"][0]["root_path"]
        if args.check:
            view = get_search_families(root)
            if checkout is not None and capture_sources(checkout, catalog, registry_root=root) != _json(root / "search-family-sources.json"):
                raise RegistryError("Captured family source metadata differs from pinned Git source")
        else:
            sources = capture_sources(checkout, catalog, registry_root=root) if checkout is not None else _json(root / "search-family-sources.json")
            view = build_search_families(catalog, sources)
            if checkout is not None:
                _write(root / "search-family-sources.json", sources)
            _write(root / "search-families.json", view)
        print(json.dumps({"valid": True, **view["summary"]}, sort_keys=True))
    except (RegistryError, subprocess.CalledProcessError, OSError, KeyError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
