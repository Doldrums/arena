"""Inert small fixtures test the boundary, never claim benchmark seed readiness."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

import numpy as np
import pytest

LIB = Path(__file__).resolve().parents[1] / "suite/_lib"
sys.path.insert(0, str(LIB))
from rankevolve import contract, evaluator, prepare, ranking
from rankevolve.metrics import ndcg_at_k, recall_at_k


@pytest.mark.parametrize("indices,scores", [
    ([0, 0], [2., 1.]), ([0.1], [1.]), ([0.0], [1.]), ([True], [1.]),
    ([3], [1.]), ([-1], [1.]), ([2**100], [1.]), ([0], [float("nan")]),
    ([0], [float("inf")]), ([0], [True]), ([0], [10**400]), ([0], []),
    ([0, 1], [1., 2.]), (np.array([0.5]), np.array([1.])),
    (np.array([[0]]), [1.]), (np.array([True]), [1.]), (np.array([0], dtype=object), [1.]),
])
def test_invalid_rankings_never_reach_binary_metrics(indices, scores):
    with pytest.raises(ValueError): ranking.checked_ranking(indices, scores, 3)


def test_duplicate_loophole_is_closed_before_the_unchanged_metric():
    relevant, repeated = np.array([0]), np.zeros(100, dtype=int)
    assert recall_at_k(relevant, repeated, 100) == 100
    assert ndcg_at_k(relevant, repeated, 10) > 1
    with pytest.raises(ValueError, match="unique"):
        ranking.checked_ranking(repeated, np.ones(100), 100)


def test_original_seed_full_corpus_fallback_is_validated_before_prefixing():
    indices = np.arange(150)
    actual, scores = ranking.checked_ranking(indices, np.zeros(150), 150)
    assert actual == list(range(100)) and scores == [0.] * 100
    indices[-1] = 0
    with pytest.raises(ValueError, match="unique"):
        ranking.checked_ranking(indices, np.zeros(150), 150)
    assert ranking.checked_ranking([np.int64(2)], [np.float32(1.)], 3) == ([2], [1.])


def test_raw_metrics_equal_original_positive_qrel_binary_functions():
    rows = [{"id": "q", "indices": [2, 0, 1], "scores": [3., 2., 1.]}]
    result = ranking.grade_rankings(rows, ["a", "b", "c"], ["q"], {"q": {"a": 3, "c": 1, "b": 0}})
    expected = np.array([0, 2]);actual = np.array([2, 0, 1])
    assert result["recall_at_100"] == recall_at_k(expected, actual, 100)
    assert result["binary_ndcg_at_10"] == ndcg_at_k(expected, actual, 10)
    assert result["score"] == 0.8 * result["recall_at_100"] + 0.2 * result["binary_ndcg_at_10"]
    assert result == ranking.grade_rankings(rows, ["a", "b", "c"], ["q"], {"q": {"a": 1, "c": 99, "b": 0}})


@pytest.mark.parametrize("rows", [[], [{"id": "wrong", "indices": [], "scores": []}],
    [{"id": "q", "indices": [], "scores": []}] * 2,
    [{"id": "q", "indices": [], "scores": [], "score": 1}]])
def test_cannot_skip_duplicate_relabel_queries_or_supply_a_score(rows):
    with pytest.raises(ValueError): ranking.grade_rankings(rows, ["a"], ["q"], {"q": {"a": 1}})


def test_empty_retrieval_is_valid_zero_and_irrelevant_queries_still_require_output():
    rows = [{"id": q, "indices": [], "scores": []} for q in ("q1", "q2")]
    result = ranking.grade_rankings(rows, ["a"], ["q1", "q2"], {"q1": {"a": 2}})
    assert result["score"] == 0 and result["queries_scored"] == 1 and result["queries_ranked"] == 2
    with pytest.raises(ValueError): ranking.grade_rankings(rows[:1], ["a"], ["q1", "q2"], {"q1": {"a": 2}})


@pytest.fixture
def small_archive(tmp_path, monkeypatch):
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("scidocs/corpus.jsonl", '\n'.join(json.dumps({"_id": str(i), "title": "T", "text": f"doc{i}"}) for i in range(3)))
        zipped.writestr("scidocs/queries.jsonl", '\n'.join(json.dumps({"_id": q, "text": q}) for q in ("q2", "q1", "train-only")))
        zipped.writestr("scidocs/qrels/test.tsv", "query-id\tcorpus-id\tscore\nq1\t0\t3\nq2\t1\t1\n")
    monkeypatch.setitem(contract.DATASETS, "scidocs", (3, 2, hashlib.md5(archive.read_bytes()).hexdigest()))
    return archive


def test_preparation_preserves_beir_220_qrel_order_not_query_file_order(small_archive, tmp_path):
    target = tmp_path / "data/scidocs"
    receipt = prepare.prepare("scidocs", target, archive=small_archive)
    assert receipt["documents"] == 3 and receipt["queries"] == 2
    assert list(contract.records(target / "public/queries.jsonl")) == [{"id": q, "text": q} for q in ("q1", "q2")]
    assert next(contract.records(target / "public/corpus.jsonl")) == {"id": "0", "text": "T doc0"}
    assert contract.verified_bundle("scidocs", receipt["manifest_sha256"], target.parent)[0] == target
    (target / "public/corpus.jsonl").write_text("tampered")
    with pytest.raises(ValueError, match="differs"):
        contract.verified_bundle("scidocs", receipt["manifest_sha256"], target.parent)


def test_bad_archive_checksum_or_incomplete_count_does_not_publish(small_archive, tmp_path, monkeypatch):
    for limits in ((3, 2, "0"*32), (4, 2, hashlib.md5(small_archive.read_bytes()).hexdigest())):
        monkeypatch.setitem(contract.DATASETS, "scidocs", limits)
        with pytest.raises(ValueError): prepare.prepare("scidocs", tmp_path / "unpublished", archive=small_archive)
        assert not (tmp_path / "unpublished").exists()


def test_missing_reviewed_lock_and_linked_assets_fail_closed(small_archive, tmp_path):
    target = tmp_path / "data/scidocs"
    receipt = prepare.prepare("scidocs", target, archive=small_archive)
    for value in (None, "0"*64):
        with pytest.raises(ValueError): contract.verified_bundle("scidocs", value, target.parent)
    original = target / "public/corpus.jsonl"
    original.rename(target / "moved.jsonl")
    original.symlink_to(target / "moved.jsonl")
    with pytest.raises(ValueError): contract.verified_bundle("scidocs", receipt["manifest_sha256"], target.parent)


def test_real_child_receives_only_public_inputs_and_parent_grades(small_archive, tmp_path, monkeypatch):
    target = tmp_path / "data/scidocs"
    receipt = prepare.prepare("scidocs", target, archive=small_archive)
    monkeypatch.setattr(contract, "DATA_ROOT", target.parent)
    here = tmp_path / "suite/rankevolve-scidocs"
    here.mkdir(parents=True)
    shutil.copytree(LIB / "rankevolve", here.parent / "_lib/rankevolve", ignore=shutil.ignore_patterns("__pycache__"))
    (here / "dataset-lock.json").write_text(json.dumps({"dataset": "scidocs", "manifest_sha256": receipt["manifest_sha256"], "candidate_timeout_seconds": 20}))
    candidate = tmp_path / "candidate.py"
    candidate.write_text('''import sys
assert all('/private/qrels' not in value and 'qrels.jsonl' not in value for value in sys.argv)
class LuceneTokenizer:
    def __call__(self, text): return text.split()
tokenize = LuceneTokenizer()
class Corpus:
    def __init__(self, documents, ids): self.ids = ids
class BM25:
    def __init__(self, corpus): pass
    def rank(self, query, top_k=100): return [0,1,2],[3.,2.,1.]
''')
    result = evaluator.evaluate(candidate, here)
    assert result["valid"] is True and result["queries_ranked"] == 2
    assert result["recall_at_100"] == 1
    assert result["search_protocol"] == "exploratory_search_on_test"
    assert "no adversarial secrecy guarantee" in result["candidate_boundary"]
    candidate.write_text(candidate.read_text().replace('[0,1,2]', '[0,0,0]'))
    with pytest.raises(ValueError, match="subprocess failed"):
        evaluator.evaluate(candidate, here)


def test_all_thirteen_seed_hashes_and_metric_source_are_pinned():
    source = json.loads((LIB / "rankevolve/source.json").read_text())
    for dataset in contract.DATASETS:
        task = LIB.parent / ("rankevolve-" + dataset)
        assert contract.digest(task / "initial_program.py") == source["files"]["tasks/bm25/seeds/freeform.py"]
        metadata = json.loads((task / "task.json").read_text())
        assert metadata["execution"]["suite"]["protocol"] == "recreated"
        assert metadata["validation"]["full_dataset_seed_verified"] is False
    assert contract.digest(LIB / "rankevolve/metrics.py") == source["files"]["tasks/_shared/metrics.py"]
