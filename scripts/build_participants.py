#!/usr/bin/env python3
"""Build/check participant bibliography from reviewed local source metadata.

--corpus captures the named source document. Without it, the checked-in capture
is sufficient. No network request, framework launch or evaluation is performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.registry import RegistryError, _json, resolve_registry_root
from arena.participant_corpus import (SOURCE_FILE, DESCRIPTIONS_FILE, ATTRIBUTIONS_FILE, capture_corpus,
                                     build_participant_catalog, native_recipes_for_participants)


def _write(path, value):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-root", type=Path)
    parser.add_argument("--corpus", type=Path, help="User-supplied human-harness-corpus.md; read without fetching anything")
    parser.add_argument("--check", action="store_true", help="Verify the committed snapshot without writing")
    args = parser.parse_args(argv)
    root = resolve_registry_root(args.registry_root)
    try:
        bibliography = _json(root / "search-family-sources.json")
        corpus = capture_corpus(args.corpus.read_bytes(), bibliography) if args.corpus else _json(root / SOURCE_FILE)
        declarations = [_json(path) for path in sorted((root / "participants").glob("*.json"))]
        attribution_path = root / ATTRIBUTIONS_FILE
        if not attribution_path.exists() and (root / "participants.json").exists() and any(item.get("attribution") for item in _json(root / "participants.json").get("participants", [])):
            raise RegistryError("Missing attribution sources; refusing to drop research credits")
        view = build_participant_catalog(declarations, corpus, _json(root / DESCRIPTIONS_FILE), bibliography,
                                         _json(attribution_path) if attribution_path.exists() else None,
                                         native_recipes=native_recipes_for_participants(root))
        if args.check:
            if corpus != _json(root / SOURCE_FILE):
                raise RegistryError("Captured corpus differs from the supplied source document")
            if view != _json(root / "participants.json"):
                raise RegistryError("Participant snapshot differs from reviewed sources; regenerate it")
        else:
            if args.corpus:
                _write(root / SOURCE_FILE, corpus)
            _write(root / "participants.json", view)
        print(json.dumps({"valid": True, **view["summary"]}, sort_keys=True))
    except (RegistryError, OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
