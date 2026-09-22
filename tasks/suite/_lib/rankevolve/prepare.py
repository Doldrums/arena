"""Prepare complete public inputs and separate qrels from official benchmark assets.

BEIR archives must match the published checksum before parsing. TREC DL uses
the exact ir-datasets 0.5.11 passage corpus; no Hugging Face fallback. This
operator tool may download through ir-datasets; evaluation never downloads.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from .contract import DATASETS, FORUMS, SCHEMA, SOURCE_COMMIT, TOKENIZER, decode, digest


def write_row(stream, row):
    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")


def archive_rows(archive, name):
    with archive.open(name) as binary, io.TextIOWrapper(binary, encoding="utf-8") as stream:
        for line in stream:
            if len(line) > 16 * 1024 * 1024:
                raise ValueError("Archive row exceeds bounded text contract")
            row = decode(line)
            if type(row) is not dict:
                raise ValueError("Expected JSON object")
            yield row


def beir_part(archive, prefix, forum, corpus, queries, judgments, seen_docs, seen_queries):
    qrels = {}
    with archive.open(prefix + "/qrels/test.tsv") as raw, io.TextIOWrapper(raw, encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        if next(reader) != ["query-id", "corpus-id", "score"]:
            raise ValueError("Unexpected BEIR test qrels header")
        for row in reader:
            if len(row) != 3:
                raise ValueError("Malformed BEIR qrel row")
            query, doc, grade = row
            entries = qrels.setdefault(query, {})
            if doc in entries:
                raise ValueError("Duplicate BEIR query/document judgment")
            entries[doc] = int(grade)
    docs = 0
    for row in archive_rows(archive, prefix + "/corpus.jsonl"):
        ident = row["_id"]
        if type(ident) is not str:
            raise ValueError("Corpus IDs must be unique strings")
        # Forums are namespaced before uniqueness checks across the merged corpus.
        key = f"{forum}_{ident}" if forum else ident
        if key in seen_docs:
            raise ValueError("Duplicate complete-corpus document ID")
        seen_docs.add(key)
        title, text = row.get("title", "") or "", row.get("text", "") or ""
        if type(title) is not str or type(text) is not str:
            raise ValueError("Corpus text/title must be strings")
        write_row(corpus, {"id": key, "text": f"{title} {text}".strip() if title else text})
        docs += 1
    query_text = {}
    for row in archive_rows(archive, prefix + "/queries.jsonl"):
        ident = row["_id"]
        if type(ident) is not str or ident in query_text or type(row["text"]) is not str:
            raise ValueError("Query IDs must be unique strings with text")
        query_text[ident] = row["text"]
    # BEIR 2.2.0 GenericDataLoader.load rebuilds queries in qrel insertion
    # order. The original RankEvolve loader preserves that order in both paths.
    order = list(qrels)
    if not set(order) <= query_text.keys():
        raise ValueError("Every test qrel query must have its original query text")
    for query in order:
        key = f"{forum}_{query}" if forum else query
        if key in seen_queries:
            raise ValueError("Duplicate complete-query ID")
        seen_queries.add(key)
        write_row(queries, {"id": key, "text": query_text[query]})
        relevance = {f"{forum}_{doc}" if forum else doc: grade for doc, grade in qrels[query].items()}
        write_row(judgments, {"id": key, "relevance": relevance})
    return docs, len(order)


def prepare_beir(dataset, archive_path, directory):
    expected = DATASETS[dataset][2]
    if expected is None:
        raise ValueError("TREC DL requires its complete ir-datasets passage corpus")
    checksum = hashlib.md5()
    with archive_path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(block)
    if checksum.hexdigest() != expected:
        raise ValueError("BEIR archive differs from its official published checksum")
    files = [directory / name for name in ("public/corpus.jsonl", "public/queries.jsonl", "private/qrels.jsonl")]
    with zipfile.ZipFile(archive_path) as archive, files[0].open("w") as corpus, files[1].open("w") as queries, files[2].open("w") as qrels:
        if len(set(archive.namelist())) != len(archive.namelist()):
            raise ValueError("Duplicate ZIP members")
        forums = FORUMS if dataset == "cqadupstack" else (None,)
        if dataset == "cqadupstack":
            actual = {name.split("/")[1] for name in archive.namelist()
                      if name.startswith(dataset + "/") and name.endswith("/corpus.jsonl")}
            if actual != set(FORUMS):
                raise ValueError("CQADupstack requires all twelve original subforums")
        counts, seen_docs, seen_queries = [0, 0], set(), set()
        for forum in forums:
            prefix = dataset + ("/" + forum if forum else "")
            docs, qs = beir_part(archive, prefix, forum, corpus, queries, qrels, seen_docs, seen_queries)
            counts[0] += docs
            counts[1] += qs
    return counts, {"kind": "official_beir_archive", "official_md5": expected,
                    "archive_sha256": digest(archive_path), "archive_bytes": archive_path.stat().st_size,
                    "url": f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{dataset}.zip"}


def prepare_trec(dataset, cache, directory):
    if dataset not in {"dl19", "dl20"} or importlib.metadata.version("ir-datasets") != "0.5.11":
        raise ValueError("TREC DL preparation requires ir-datasets==0.5.11 and dl19/dl20")
    os.environ["IR_DATASETS_HOME"] = str(cache)
    import ir_datasets
    name = "msmarco-passage/trec-dl-" + ("2019" if dataset == "dl19" else "2020")
    source = ir_datasets.load(name)
    count, seen_docs, seen_queries = 0, set(), set()
    with (directory / "public/corpus.jsonl").open("w") as output:
        for doc in source.docs_iter():
            if doc.doc_id in seen_docs:
                raise ValueError("Duplicate MS MARCO passage ID")
            seen_docs.add(doc.doc_id)
            write_row(output, {"id": doc.doc_id, "text": doc.text})
            count += 1
    with (directory / "public/queries.jsonl").open("w") as output:
        for query in source.queries_iter():
            if query.query_id in seen_queries:
                raise ValueError("Duplicate TREC DL query ID")
            seen_queries.add(query.query_id)
            write_row(output, {"id": query.query_id, "text": query.text})
    qrels = {}
    for row in source.qrels_iter():
        entries = qrels.setdefault(row.query_id, {})
        if row.doc_id in entries:
            raise ValueError("Duplicate TREC DL qrel")
        entries[row.doc_id] = row.relevance
    if not set(qrels) <= seen_queries:
        raise ValueError("TREC DL qrel query missing from complete input queries")
    with (directory / "private/qrels.jsonl").open("w") as output:
        for ident, relevance in qrels.items():
            write_row(output, {"id": ident, "relevance": relevance})
    return [count, len(seen_queries)], {"kind": "ir_datasets", "version": "0.5.11", "dataset_id": name,
        "corpus_id": "msmarco-passage", "fallback": False,
        "note": "ir-datasets verifies its source downloads; prepared output hashes below bind the frozen runtime assets"}


def prepare(dataset, destination, *, archive=None, ir_cache=None):
    destination = Path(destination).resolve()
    if dataset not in DATASETS or destination.exists():
        raise ValueError("Choose an exact registered dataset and a new output directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rankevolve-", dir=destination.parent) as temporary:
        directory = Path(temporary)
        (directory / "public").mkdir()
        (directory / "private").mkdir()
        if dataset in {"dl19", "dl20"}:
            if ir_cache is None or archive is not None:
                raise ValueError("TREC DL needs an explicit ir-datasets cache")
            counts, origin = prepare_trec(dataset, Path(ir_cache).resolve(), directory)
        else:
            if archive is None or ir_cache is not None:
                raise ValueError("BEIR requires its complete official ZIP archive")
            counts, origin = prepare_beir(dataset, Path(archive).resolve(), directory)
        if tuple(counts) != DATASETS[dataset][:2]:
            raise ValueError(f"Full dataset count mismatch: observed {counts}, expected {DATASETS[dataset][:2]}")
        files = {name: {"sha256": digest(directory / name), "bytes": (directory / name).stat().st_size}
                 for name in ("public/corpus.jsonl", "public/queries.jsonl", "private/qrels.jsonl")}
        manifest = {"schema": SCHEMA, "dataset": dataset, "source_commit": SOURCE_COMMIT,
                    "documents": counts[0], "queries": counts[1], "sample_queries": 0, "warmup_queries": 0,
                    "tokenizer": TOKENIZER, "search_protocol": "exploratory_search_on_test",
                    "qrels_semantics": "positive relevance is binary; no graded gain", "source": origin, "files": files}
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        shutil.copytree(directory, destination)
    return {"dataset": dataset, "manifest_sha256": digest(destination / "manifest.json"),
            "documents": counts[0], "queries": counts[1], "directory": str(destination)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=tuple(DATASETS), required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--ir-datasets-cache", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(prepare(args.dataset, args.destination, archive=args.archive, ir_cache=args.ir_datasets_cache), indent=2))


if __name__ == "__main__":
    main()
