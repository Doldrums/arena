"""Exact dataset and output contracts for the pinned lexical retrieval path."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

SOURCE_COMMIT = "8f664bcd5123bac2397f0c1bfbdb347ca3233483"
SCHEMA = "arena.rankevolve-data/1"
TOKENIZER = "candidate.LuceneTokenizer"
DATA_ROOT = Path("/opt/arena-data/rankevolve")
FORUMS = ("android", "english", "gaming", "gis", "mathematica", "physics",
          "programmers", "stats", "tex", "unix", "webmasters", "wordpress")
# Corpus sizes are the pinned source's complete datasets, never sampled corpora.
DATASETS = {
    "scidocs": (25657, 1000, "38121350fc3a4d2f48850f6aff52e4a9"),
    "trec-covid": (171332, 50, "ce62140cb23feb9becf6270d0d1fe6d1"),
    "climate-fever": (5416593, 1535, "8b66f0a9126c521bae2bde127b4dc99d"),
    "fiqa": (57638, 648, "17918ed23cd04fb15047f73e6c3bd9d9"),
    "webis-touche2020": (382545, 49, "46f650ba5a527fc69e0a6521c5a23563"),
    "quora": (522931, 10000, "18fb154900ba42a600f84b839c173167"),
    "cqadupstack": (457199, 13145, "4e41456d7df8ee7760a7f866133bda78"),
    "dbpedia-entity": (4635922, 400, "c2a39eb420a3164af735795df012ac2c"),
    "nq": (2681468, 3452, "d4d3d2e48787a744b6f6e691ff534307"),
    "hotpotqa": (5233329, 7405, "f412724f78b0d91183a0e86805e16114"),
    "fever": (5416568, 6666, "5a818580227bfb4b35bb6fa46d9b6c03"),
    "dl19": (8841823, 200, None),
    "dl20": (8841823, 200, None),
}


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("Nonfinite JSON value")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def digest(path):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Dataset assets must be regular files")
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def records(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if len(line) > 16 * 1024 * 1024:
                raise ValueError("Dataset row exceeds bounded text contract")
            value = decode(line)
            if type(value) is not dict:
                raise ValueError("Dataset rows must be JSON objects")
            yield value


def verified_bundle(dataset, expected_sha256, root=None):
    if dataset not in DATASETS or type(expected_sha256) is not str or len(expected_sha256) != 64:
        raise ValueError("Dataset needs a reviewed prepared-manifest SHA-256 before execution")
    base = (DATA_ROOT if root is None else Path(root)) / dataset
    if base.resolve() != base or base.is_symlink():
        raise ValueError("Prepared data root must not traverse links")
    path = base / "manifest.json"
    if path.stat().st_size > 1024 * 1024 or digest(path) != expected_sha256:
        raise ValueError("Prepared dataset manifest differs from the task's data lock")
    manifest = decode(path.read_bytes())
    documents, queries, _ = DATASETS[dataset]
    if (manifest.get("schema") != SCHEMA or manifest.get("dataset") != dataset
            or manifest.get("source_commit") != SOURCE_COMMIT
            or manifest.get("tokenizer") != TOKENIZER
            or manifest.get("documents") != documents or manifest.get("queries") != queries
            or manifest.get("sample_queries") != 0 or manifest.get("warmup_queries") != 0
            or manifest.get("search_protocol") != "exploratory_search_on_test"):
        raise ValueError("Prepared dataset does not match the full pinned evaluation protocol")
    files = manifest.get("files")
    names = {"public/corpus.jsonl", "public/queries.jsonl", "private/qrels.jsonl"}
    if type(files) is not dict or set(files) != names:
        raise ValueError("Prepared dataset must contain exactly the public inputs and private qrels")
    for name, row in files.items():
        file = base / name
        if (file.resolve() != file or type(row) is not dict
                or file.stat().st_size != row.get("bytes") or digest(file) != row.get("sha256")):
            raise ValueError("Prepared dataset file differs from its pinned manifest")
    return base, manifest
