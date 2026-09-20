"""Scholarly coverage never grants execution capability or fabricates source code."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from arena.participant_corpus import (capture_corpus, validate_corpus, expected_participants,
                                     build_participant_catalog, code_links)
from arena.registry import RegistryError, get_participants, validate_participant, validate_registry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry"


def read(name):
    return json.loads((REGISTRY / name).read_text())


def test_every_corpus_work_has_one_scholarly_entry_and_exact_paper_link():
    view = get_participants()
    corpus = read("participant-corpus.json")
    bibliography = {p["id"]: p for p in read("search-family-sources.json")["papers"] if p["source_kind"] == "corpus_paper"}
    works = {w["paper_id"]: w for w in corpus["works"]}
    linked = [(entry, paper) for entry in view["participants"] for paper in entry["papers"]]
    assert len(linked) == len(works) == len(bibliography) == 98
    assert {paper["id"] for _, paper in linked} == set(works) == set(bibliography)
    for entry, paper in linked:
        work = works[paper["id"]]
        assert paper["url"] == bibliography[paper["id"]]["paper_url"]
        assert paper["title"] == bibliography[paper["id"]]["title"]
        assert paper["year"] == work["year"]
        assert paper["venue"] == work["venue"]
        assert entry["search_family"]["label"] == work["family"]
        assert entry["provenance"]["sha256"] == corpus["source"]["sha256"]
        assert entry["provenance"]["section_sha256"] == work["section_sha256"]
        assert entry["provenance"]["line_start"] == work["line_start"]
        assert "/blob/995768fc462b8e327f90e6762846cc6ccb06cc2c/" in entry["provenance"]["metadata_source"]["url"]
    assert {paper["id"] for _, paper in linked if paper["kind"] == "technical_report"} == {"agentic-optimization", "darwinian-evolver"}


def test_pinned_systems_are_enriched_without_duplicate_entries_or_revision_changes():
    entries = {p["id"]: p for p in get_participants()["participants"]}
    for ident in ("sciel", "shinka", "dgm"):
        declaration = read(f"participants/{ident}.json")
        assert {key: entries[ident][key] for key in declaration} == declaration
    assert entries["shinka"]["papers"][0]["id"] == "shinkaevolve"
    assert "shinkaevolve" not in entries
    assert entries["dgm"]["papers"][0]["year"] == 2025  # source preprint year, not silently replaced by venue year
    assert entries["dgm"]["papers"][0]["venue"] == "ICLR 2026"
    assert entries["sciel"]["papers"] == []  # no invented SCiEL paper
    assert entries["sciel"]["provenance"] is None
    assert all(p["repository"] is None for p in entries.values() if p["record_kind"] == "research_work")


def test_code_links_keep_artifacts_and_project_pages_separate_from_search_implementations():
    entries = {p["id"]: p for p in get_participants()["participants"]}
    assert entries["alphaevolve"]["code_links"][0]["kind"] == "artifact"
    assert entries["alphaevolve"]["code_links"][0]["label"] == "Result notebook"
    assert {link["kind"] for link in entries["meta-harness"]["code_links"]} == {"artifact", "project"}
    assert entries["mipro"]["code_links"] == [{"url": "http://dspy.ai", "kind": "project", "label": "Project page"}]
    for ident in ("funbo", "avo", "elm", "flowscout", "codeevolve-salesforce", "algoevolve"):
        assert entries[ident]["code_links"] == []
    assert all("openevolve" not in link["url"] for link in entries["rankevolve"]["code_links"])
    assert entries["llm-flowrepair"]["code_links"][0]["url"] == "https://doi.org/10.5281/zenodo.21976165"


def test_corpus_import_is_heading_based_and_omits_forensic_notes():
    metadata = read("search-family-sources.json")
    metadata["papers"] = [p for p in metadata["papers"] if p["id"] == "ael"]
    raw = ("## FunSearch / EoH\n\n"
           "#### Algorithm Evolution Using Large Language Model (AEL) - 2023 - arXiv preprint\n"
           "- что делали: Language models vary algorithm descriptions and code.\n"
           "- ссылки на код: не дают\n"
           "- v2-блок: private audit verdict and unrelated notes\n").encode()
    corpus = capture_corpus(raw, metadata)
    assert corpus["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert corpus["source"]["work_count"] == 1
    assert corpus["works"][0]["paper_id"] == "ael"
    work = corpus["works"][0]
    selected = b"".join(raw.splitlines(keepends=True)[work["line_start"] - 1:work["line_end"]])
    assert work["section_sha256"] == hashlib.sha256(selected).hexdigest()
    assert "private audit verdict" not in json.dumps(corpus)
    with pytest.raises(RegistryError, match="no exact bibliography match"):
        capture_corpus(raw.replace(b"Algorithm Evolution Using", b"Different Study Using"), metadata)
    with pytest.raises(RegistryError, match="Duplicate"):
        capture_corpus(raw + raw, metadata)


@pytest.mark.parametrize("mutation, message", [
    (lambda source: source["works"].pop(), "entire pinned research bibliography"),
    (lambda source: source["works"][1].update(line_start=source["works"][0]["line_start"]), "line spans"),
    (lambda source: source["works"][0].update(year=2099), "bibliography disagrees"),
    (lambda source: source.update(bibliography_digest="0" * 64), "digest is stale"),
    (lambda source: source["works"][0].update(code_links=[{"url": "https://github.com/invented/code", "kind": "implementation", "label": "Code"}]), "code-link scope"),
])
def test_corpus_validation_rejects_omissions_relabeling_and_invented_links(mutation, message):
    corpus = read("participant-corpus.json")
    mutation(corpus)
    with pytest.raises(RegistryError, match=message):
        validate_corpus(corpus, read("search-family-sources.json"))


@pytest.mark.parametrize("mutate", [
    lambda item: item.update(registration_status="evaluation_in_progress"),
    lambda item: item.update(repository={"url": "https://github.com/example/work", "commit": "a" * 40}),
    lambda item: item["capabilities"].update(native_run=True),
    lambda item: item.update(papers=[]),
    lambda item: item["papers"][0].update(url="javascript:alert(1)"),
    lambda item: item.update(code_links=[{"url": "https://example.org/?token=secret", "label": "Code", "kind": "implementation"}]),
])
def test_literature_metadata_cannot_grant_readiness_or_active_links(mutate):
    item = next(p for p in get_participants()["participants"] if p["record_kind"] == "research_work")
    mutate(item)
    with pytest.raises(RegistryError):
        validate_participant(item)


def test_stale_scholarly_snapshot_is_rejected_by_the_api_reader(tmp_path):
    copied = tmp_path / "registry"
    shutil.copytree(REGISTRY, copied)
    changed = read("participants.json")
    next(item for item in changed["participants"] if item["id"] == "ael")["papers"][0]["url"] = "https://example.org/wrong-paper"
    (copied / "participants.json").write_text(json.dumps(changed))
    with pytest.raises(RegistryError, match="differs from the reviewed corpus"):
        get_participants(copied)


def test_missing_corpus_capture_cannot_silently_discard_literature_entries(tmp_path):
    copied = tmp_path / "registry"
    shutil.copytree(REGISTRY, copied)
    (copied / "participant-corpus.json").unlink()
    with pytest.raises(RegistryError, match="corpus capture is required"):
        get_participants(copied)
    with pytest.raises(RegistryError, match="refusing to drop scholarly"):
        expected_participants(copied)


def test_all_source_descriptions_are_present_and_no_local_paths_or_verdicts_enter_the_api():
    view = get_participants()
    corpus = read("participant-corpus.json")
    descriptions = read("participant-descriptions.json")["descriptions"]
    assert set(descriptions) == {work["paper_id"] for work in corpus["works"]}
    assert all(15 <= len(description.split()) <= 90 for description in descriptions.values())
    text = json.dumps(view, ensure_ascii=False)
    for forbidden in ("/Users/", "/tmp/", "private audit verdict", "v2-блок", '"gap"', '"honoured residual"'):
        assert forbidden not in text


def test_participant_build_check_is_offline_deterministic_and_does_not_mutate_sources():
    paths = [REGISTRY / name for name in ("participant-corpus.json", "participant-descriptions.json", "participants.json")]
    before = {path: path.read_bytes() for path in paths}
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_participants.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["research_work_count"] == 98
    assert before == {path: path.read_bytes() for path in paths}
    assert expected_participants(REGISTRY) == get_participants()
    assert validate_registry()["valid"] is True
