"""Candidate-only child: public text inputs in, bounded rankings out; no qrels API."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import types

from . import seed_library
from .contract import records
from .ranking import checked_ranking


def seed_namespace():
    # Keep the byte-identical upstream seed's public import contract. The
    # compatibility module contains only its original tokenizer definitions.
    for name in ("tasks", "tasks.bm25"):
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    sys.modules["tasks.bm25.library"] = seed_library


def run(candidate, data, output, documents, queries):
    corpus_ids, texts = [], []
    for row in records(data / "corpus.jsonl"):
        if set(row) != {"id", "text"} or type(row["id"]) is not str or type(row["text"]) is not str:
            raise ValueError("Invalid public corpus row")
        corpus_ids.append(row["id"])
        texts.append(row["text"])
    query_rows = list(records(data / "queries.jsonl"))
    if len(texts) != documents or len(query_rows) != queries:
        raise ValueError("Public data differs from the declared full corpus/query counts")
    seed_namespace()
    spec = importlib.util.spec_from_file_location("candidate_bm25", candidate)
    if spec is None or spec.loader is None:
        raise ValueError("Candidate must be a Python module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if any(not callable(getattr(module, name, None)) for name in ("BM25", "Corpus", "tokenize", "LuceneTokenizer")):
        raise ValueError("Candidate must export BM25, Corpus, tokenize and LuceneTokenizer")
    tokenize = module.LuceneTokenizer()
    tokens = [tokenize(text) for text in texts]
    corpus = module.Corpus(tokens, ids=corpus_ids)
    model = module.BM25(corpus)
    for name in ("vocabulary_size", "idf_array", "term_doc_matrix"):
        if hasattr(corpus, name):
            getattr(corpus, name)
    with output.open("x", encoding="utf-8") as target:
        for row in query_rows:
            indices, scores = model.rank(tokenize(row["text"]), top_k=100)
            indices, scores = checked_ranking(indices, scores, documents)
            target.write(json.dumps({"id": row["id"], "indices": indices, "scores": scores}, allow_nan=False) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--documents", type=int, required=True)
    parser.add_argument("--queries", type=int, required=True)
    args = parser.parse_args(argv)
    # Bounds accidental/malicious writes. OS isolation remains the outer
    # canonical container, not this same-UID subprocess boundary.
    cap = min(512 * 1024 * 1024, max(1024 * 1024, args.queries * 32768))
    resource.setrlimit(resource.RLIMIT_FSIZE, (cap, cap))
    os.environ["BM25_QUERY_WORKERS"] = "1"
    run(args.candidate, args.data, args.output, args.documents, args.queries)


if __name__ == "__main__":
    main()
