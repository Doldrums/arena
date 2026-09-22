"""Validate candidate rankings before applying the unmodified binary metrics."""
from __future__ import annotations

import math
import numpy as np

from .metrics import ndcg_at_k, recall_at_k

NUMPY_REAL_SCALARS = frozenset(np.dtype(name).type for name in (
    "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64",
    "float16", "float32", "float64"))


def checked_ranking(indices, scores, documents):
    def plain(value, name):
        if type(value) is np.ndarray:
            if value.ndim != 1 or value.dtype.kind not in "iuf":
                raise ValueError(f"{name} must be a one-dimensional numeric array")
            return value.tolist()
        if type(value) not in (list, tuple):
            raise ValueError(f"{name} must be a plain list, tuple or numeric array")
        return [item.item() if type(item) in NUMPY_REAL_SCALARS else item for item in value]
    indices, scores = plain(indices, "indices"), plain(scores, "scores")
    if len(indices) != len(scores) or len(indices) > documents:
        raise ValueError("Rank returns paired indices and scores within the corpus size")
    # Do not cast first: bools, fractional floats, and huge integers must not
    # silently become valid document indices, unlike the original np.array cast.
    if any(type(index) is not int or not 0 <= index < documents for index in indices):
        raise ValueError("Document indices must be integers in the complete corpus range")
    if len(set(indices)) != len(indices):
        raise ValueError("Document indices must be unique before Recall/nDCG")
    for score in scores:
        try:
            valid = type(score) in (int, float) and math.isfinite(score)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("Ranking scores must be finite real numbers")
    if any(left < right for left, right in zip(scores, scores[1:])):
        raise ValueError("Rankings must be ordered by descending score")
    # The byte-identical seed returns the entire corpus for empty/out-of-vocab
    # queries despite top_k=100. Validate that entire ranking before retaining
    # the same prefix consumed by the original Recall/nDCG functions.
    return indices[:100], scores[:100]


def grade_rankings(rows, corpus_ids, query_ids, qrels):
    """Score all expected queries with original positive-qrel/binary semantics."""
    mapping = {doc: index for index, doc in enumerate(corpus_ids)}
    if len(mapping) != len(corpus_ids) or len(set(query_ids)) != len(query_ids):
        raise ValueError("Prepared corpus and query IDs must be unique")
    recalls, ndcgs, skipped = [], [], 0
    count = 0
    for count, row in enumerate(rows, 1):
        if (count > len(query_ids) or set(row) != {"id", "indices", "scores"}
                or row["id"] != query_ids[count - 1]):
            raise ValueError("Candidate rankings must cover every input query in its original order")
        indices, _ = checked_ranking(row["indices"], row["scores"], len(corpus_ids))
        relevant = [mapping[doc] for doc, relevance in qrels.get(row["id"], {}).items()
                    if relevance > 0 and doc in mapping]
        if not relevant:
            skipped += 1
            continue
        actual, expected = np.asarray(indices, dtype=np.int64), np.asarray(relevant, dtype=np.int64)
        recalls.append(float(recall_at_k(expected, actual, 100)))
        ndcgs.append(float(ndcg_at_k(expected, actual, 10)))
    if count != len(query_ids) or not recalls:
        raise ValueError("Incomplete rankings or no queries with positive in-corpus qrels")
    recall, ndcg = float(np.mean(recalls)), float(np.mean(ndcgs))
    if not (0 <= recall <= 1 and 0 <= ndcg <= 1):
        raise ValueError("Validated binary retrieval metrics must lie in [0,1]")
    return {"score": 0.8 * recall + 0.2 * ndcg, "recall_at_100": recall,
            "binary_ndcg_at_10": ndcg, "queries_scored": len(recalls),
            "queries_ranked": count, "queries_without_positive_in_corpus_qrels": skipped}
