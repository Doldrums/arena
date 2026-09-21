"""A method-family link is catalog provenance, never execution compatibility."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from arena.registry import RegistryError, get_catalog
from arena.search_families import (SUPPLEMENT_FAMILIES, build_search_families, get_search_families,
                                    validate_search_families, validate_sources)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def inputs():
    return get_catalog(), json.loads((ROOT / "registry/search-family-sources.json").read_text())


def test_source_declared_families_cover_catalog_once(inputs):
    catalog, _ = inputs
    data = get_search_families()
    assert data["summary"] == {"task_count": 959, "source_group_count": 113, "corpus_paper_count": 98,
                                "group_count": 10, "unknown_family_source_count": 0, "unknown_family_task_count": 0,
                                "cross_family_task_count": 26, "executable_count": 689, "unsupported_count": 270}
    members = [ident for group in data["groups"] for ident in group["task_ids"]]
    assert len(members) == len(set(members)) == 959
    assert set(members) == {task["id"] for task in catalog["tasks"]}
    assert sum(group["paper_count"] for group in data["groups"]) == 98
    assert sum(group["source_group_count"] for group in data["groups"]) == 113
    assert sum(group["executable"] for group in data["groups"]) == 689
    assert sum(group["unsupported"] for group in data["groups"]) == 270
    assert {group["label"]: group["source_group_count"] for group in data["groups"]} == {
        "AlphaEvolve / OpenEvolve": 16, "FunSearch / EoH": 18, "DGM / ADAS": 16,
        "Eureka": 7, "LLM-SR": 4, "Promptbreeder / EvoPrompt": 13, "Other": 24, "SCiEL supplement": 1,
        "Science supplement": 13, "Community supplement": 1}


def test_secondary_family_is_preserved_without_double_counting():
    data = get_search_families()
    annotation = data["task_annotations"]["eoh-online-bin-packing"]
    assert annotation["search_family_id"] == "funsearch-eoh"
    assert annotation["primary_paper_id"] == "eoh"
    assert annotation["related_search_family_ids"] == ["alphaevolve-openevolve", "funsearch-eoh", "other"]
    assert annotation["paper_ids"] == ["eoh", "codeevolve", "eoh-s", "hsevo", "llamea-hpo", "mcts-ahd", "meoh", "redahd"]
    other = next(group for group in data["groups"] if group["id"] == "other")
    assert "eoh-online-bin-packing" in other["addressed_task_ids"]
    assert "eoh-online-bin-packing" not in other["task_ids"]
    assert "eoh-online-bin-packing" in data["paper_annotations"]["llamea-hpo"]["declared_task_ids"]
    assert "reference-sat" in data["paper_annotations"]["satlution"]["additional_catalog_task_ids"]
    assert "reference-online-bin-packing" not in data["task_annotations"]


@pytest.mark.parametrize("ident,source_count,task_count", [
    ("sciel-supplement", 1, 93), ("science-supplement", 13, 74), ("community-supplement", 1, 1),
])
def test_supplement_is_not_counted_as_a_method_paper(ident, source_count, task_count):
    data = get_search_families()
    group = next(group for group in data["groups"] if group["id"] == ident)
    assert group["classification_basis"] == "source_supplement"
    assert group["paper_count"] == 0 and group["source_group_count"] == source_count
    assert group["task_count"] == task_count
    assert "never mean" in data["methodology"]["scope"]
    assert "compatible adapter" in data["methodology"]["scope"]
    assert "corpus curator" in data["methodology"]["classification"]


def test_unknown_source_label_is_preserved_not_guessed(inputs):
    catalog, sources = deepcopy(inputs)
    paper = next(paper for paper in sources["papers"] if paper["id"] == "alphaevolve")
    paper["declared_family"] = "New unreviewed lineage"
    data = build_search_families(catalog, sources)
    assert data["summary"]["unknown_family_source_count"] == 1
    assert data["summary"]["unknown_family_task_count"] > 0
    assert data["paper_annotations"]["alphaevolve"]["declared_family"] == "New unreviewed lineage"
    assert data["task_annotations"]["alphaevolve-circle-packing-in-unit-square"]["search_family_id"] == "unknown"
    assert sum(group["task_count"] for group in data["groups"]) == 959


@pytest.mark.parametrize("mutate", [
    lambda data: data["groups"][0]["task_ids"].append(data["groups"][0]["task_ids"][0]),
    lambda data: data["task_annotations"]["adas-gpqa"].update(search_family_id="eureka"),
    lambda data: data["groups"][0].update(task_count=9999),
    lambda data: data["paper_annotations"]["alphaevolve"].update(declared_family="Eureka"),
])
def test_tampered_membership_counts_or_evidence_rejected(inputs, mutate):
    catalog, sources = inputs
    data = build_search_families(catalog, sources)
    mutate(data)
    with pytest.raises(RegistryError, match="membership"):
        validate_search_families(data, catalog, sources)


def test_catalog_and_source_changes_invalidate_snapshot(inputs):
    catalog, sources = deepcopy(inputs)
    data = build_search_families(catalog, sources)
    catalog["tasks"][0]["name"] += " revised"
    with pytest.raises(RegistryError, match="catalog digest"):
        validate_search_families(data, catalog, sources)
    catalog, sources = deepcopy(inputs)
    sources["papers"][0]["declared_family"] = "Other"
    with pytest.raises(RegistryError, match="source digest"):
        validate_search_families(data, catalog, sources)


@pytest.mark.parametrize("mutate", [
    lambda sources: sources["papers"].append(deepcopy(sources["papers"][0])),
    lambda sources: sources["files"][0].update(url="https://github.com/IMRUNya/autoresearch-tasks/blob/main/catalog/papers.json"),
    lambda sources: sources["papers"][0]["declared_task_ids"].append("nonexistent-task"),
    lambda sources: next(paper for paper in sources["papers"] if paper["id"] == "sciel-supplement").update(source_kind="corpus_paper"),
    lambda sources: next(paper for paper in sources["papers"] if paper["id"] == "science-tcs").update(source_kind="corpus_paper"),
    lambda sources: next(paper for paper in sources["papers"] if paper["id"] == "kaggle-santa-2025").update(declared_family="Science supplement"),
    lambda sources: next(paper for paper in sources["papers"] if paper["id"] == "alphaevolve").update(source_kind="supplement"),
])
def test_invalid_captured_source_rejected(inputs, mutate):
    catalog, sources = deepcopy(inputs)
    mutate(sources)
    with pytest.raises(RegistryError):
        validate_sources(sources, catalog)


def test_source_proof_is_revision_and_file_bound(inputs):
    catalog, _ = inputs
    data = get_search_families()
    commit = catalog["sources"][0]["repository"]["commit"]
    for paper in data["paper_annotations"].values():
        source = paper["source"]
        assert f"/blob/{commit}/catalog/papers.json" in source["url"]
        assert len(source["sha256"]) == 64
        assert source["locator"].endswith("field family")


@pytest.mark.parametrize("unreviewed", [False, True])
def test_capture_requires_corpus_membership_or_reviewed_supplement(inputs, monkeypatch, tmp_path, unreviewed):
    catalog, sources = inputs
    papers = [{"id": paper["id"], "name": paper["name"], "title": paper["title"],
               "family": paper["declared_family"], "paper_url": paper["paper_url"],
               "corpus_url": paper["corpus_url"], "task_ids": paper["declared_task_ids"]}
              for paper in sources["papers"]]
    corpus = [{"id": paper["id"], "family": paper["family"]}
              for paper in papers if paper["id"] not in SUPPLEMENT_FAMILIES]
    research = [{"paper_id": paper["id"]} for paper in corpus]
    funbo = next(paper for paper in papers if paper["id"] == "funbo")
    funbo["task_ids"] = funbo["task_ids"] + [funbo["task_ids"][0]]
    if unreviewed:
        # A supplement-looking family alone must not bypass corpus verification.
        papers.append({**next(paper for paper in papers if paper["id"] == "science-tcs"),
                       "id": "science-unreviewed"})
    captured = {"catalog/papers.json": papers, "catalog/corpus.json": corpus,
                "catalog/research.json": research}
    monkeypatch.setattr(subprocess, "check_output",
                        lambda command, **kwargs: json.dumps(captured[command[-1].split(":", 1)[1]]).encode())
    capture = runpy.run_path(str(ROOT / "scripts/build_search_families.py"))["capture_sources"]
    if unreviewed:
        with pytest.raises(RegistryError, match="corpus/papers"):
            capture(tmp_path, catalog)
    else:
        result = capture(tmp_path, catalog)
        assert sum(paper["source_kind"] == "corpus_paper" for paper in result["papers"]) == 98
        assert {paper["id"] for paper in result["papers"] if paper["source_kind"] == "supplement"} == set(SUPPLEMENT_FAMILIES)
        normalized = next(paper for paper in result["papers"] if paper["id"] == "funbo")["declared_task_ids"]
        assert normalized == sorted(set(funbo["task_ids"]))


def test_check_is_offline_nonmutating_and_fails_when_stale(tmp_path):
    for name in ("catalog.json", "search-family-sources.json", "search-families.json"):
        (tmp_path / name).write_bytes((ROOT / "registry" / name).read_bytes())
    command = [sys.executable, str(ROOT / "scripts/build_search_families.py"), "--registry-root", str(tmp_path), "--check"]
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    snapshot_path = tmp_path / "search-families.json"
    data = json.loads(snapshot_path.read_text())
    data["catalog_digest"] = "0" * 64
    snapshot_path.write_text(json.dumps(data))
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1 and "catalog digest" in result.stderr
