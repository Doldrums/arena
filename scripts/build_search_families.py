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
from arena.search_families import build_search_families, get_search_families, validate_sources


def capture_sources(checkout, catalog):
    bindings = [source for source in catalog["sources"] if source["id"] == "autoresearch-tasks"]
    if len(bindings) != 1 or len(catalog["sources"]) != 1:
        raise RegistryError("This source extractor supports the initial autoresearch-tasks collection only")
    binding = bindings[0]
    commit = binding["repository"]["commit"]
    captured, files = {}, []
    for name in ("papers", "corpus", "research"):
        path = f"catalog/{name}.json"
        content = subprocess.check_output(["git", "-C", str(checkout), "show", f"{commit}:{path}"], stderr=subprocess.PIPE)
        captured[name] = json.loads(content)
        files.append({"path": path, "url": f"{binding['repository']['url']}/blob/{commit}/{path}",
                      "sha256": hashlib.sha256(content).hexdigest()})
    corpus = {paper["id"]: paper for paper in captured["corpus"]}
    research = {paper["paper_id"]: paper for paper in captured["research"]}
    if len(corpus) != len(captured["corpus"]) or len(research) != len(captured["research"]) or set(corpus) != set(research):
        raise RegistryError("Source corpus/research paper inventories disagree or contain duplicates")
    records = []
    for paper in captured["papers"]:
        ident = paper["id"]
        if ident != "sciel-supplement":
            if ident not in corpus or paper.get("family") != corpus[ident].get("family"):
                raise RegistryError("Source corpus/papers family labels disagree")
        records.append({"id": ident, "name": paper["name"], "title": paper["title"],
                        "declared_family": paper.get("family"), "paper_url": paper.get("paper_url"),
                        "corpus_url": paper.get("corpus_url"),
                        "source_kind": "supplement" if ident == "sciel-supplement" else "corpus_paper",
                        "declared_task_ids": sorted(paper["task_ids"])})
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
    parser.add_argument("--checkout", type=Path, help="Optional existing checkout; read only the catalog's pinned committed Git blobs")
    parser.add_argument("--check", action="store_true", help="Verify committed snapshots without writing")
    args = parser.parse_args()
    root = resolve_registry_root(args.registry_root)
    try:
        catalog = _json(root / "catalog.json")
        if args.check:
            view = get_search_families(root)
            if args.checkout is not None and capture_sources(args.checkout, catalog) != _json(root / "search-family-sources.json"):
                raise RegistryError("Captured family source metadata differs from pinned Git source")
        else:
            sources = capture_sources(args.checkout, catalog) if args.checkout is not None else _json(root / "search-family-sources.json")
            view = build_search_families(catalog, sources)
            if args.checkout is not None:
                _write(root / "search-family-sources.json", sources)
            _write(root / "search-families.json", view)
        print(json.dumps({"valid": True, **view["summary"]}, sort_keys=True))
    except (RegistryError, subprocess.CalledProcessError, OSError, KeyError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
