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
                                     build_participant_catalog, code_links, ATTRIBUTIONS_FILE)
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
    paths = [REGISTRY / name for name in ("participant-corpus.json", "participant-descriptions.json",
                                         ATTRIBUTIONS_FILE, "participants.json")]
    before = {path: path.read_bytes() for path in paths}
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_participants.py"), "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["research_work_count"] == 98
    assert before == {path: path.read_bytes() for path in paths}
    assert expected_participants(REGISTRY) == get_participants()
    assert validate_registry()["valid"] is True


def build_with_attributions(attributions):
    declarations = [read(f"participants/{ident}.json") for ident in ("sciel", "shinka", "dgm")]
    return build_participant_catalog(declarations, read("participant-corpus.json"),
                                     read("participant-descriptions.json"),
                                     read("search-family-sources.json"), attributions)


def test_every_research_work_preserves_its_reviewed_attribution_exactly_once():
    sources = read(ATTRIBUTIONS_FILE)
    view = get_participants()
    participants = {p["id"]: p for p in view["participants"]}
    research = {ident: entry for ident, entry in participants.items() if entry["papers"]}
    assert len(research) == 98
    assert set(research) <= set(sources["entries"]) <= set(participants)
    assert "shinka" in sources["entries"]
    assert "shinkaevolve" not in sources["entries"]  # Paper alias is not a second participant.
    for ident, attribution in sources["entries"].items():
        assert participants[ident]["attribution"] == attribution
        assert type(attribution["organizations"]) is list
        assert type(attribution["authors"]) is list
        assert attribution["kind"] in {"organizations", "authors", "team"}
        assert attribution["source_url"].startswith("https://")
    assert "Sakana AI" in participants["shinka"]["attribution"]["organizations"]
    assert "Sakana AI" in participants["dgm"]["attribution"]["organizations"]
    assert participants["elm"]["attribution"]["organizations"] == ["OpenAI"]
    assert not {"Meta", "Amazon", "Microsoft"} & set(participants["coral"]["attribution"]["organizations"])
    author_credit = participants["agentic-optimization"]["attribution"]
    assert author_credit["kind"] == "authors"
    assert author_credit["authors"] == ["Junye Pan"]
    assert author_credit["organizations"] == []  # No institution inferred from an email domain.


@pytest.mark.parametrize("mutation,message", [
    (lambda s: s["entries"].pop("ael"), "cover every research work"),
    (lambda s: s["entries"].update(unknown=deepcopy(s["entries"]["ael"])), "unknown participant"),
    (lambda s: s["entries"].update(shinkaevolve=s["entries"].pop("shinka")), "unknown participant"),
    (lambda s: s.update(schema="arena.participant-attributions/999"), "Invalid participant attributions schema"),
])
def test_attribution_source_coverage_rejects_dropped_credits_unknown_ids_and_paper_aliases(mutation, message):
    sources = read(ATTRIBUTIONS_FILE)
    mutation(sources)
    with pytest.raises(RegistryError, match=message):
        build_with_attributions(sources)


def test_attribution_arrays_are_detached_from_reviewed_sources():
    sources = read(ATTRIBUTIONS_FILE)
    original = deepcopy(sources)
    built = build_with_attributions(sources)
    assert sources == original
    next(p for p in built["participants"] if p["id"] == "dgm")["attribution"]["organizations"].clear()
    assert sources == original
    rebuilt = build_with_attributions(sources)
    assert "Sakana AI" in next(p for p in rebuilt["participants"] if p["id"] == "dgm")["attribution"]["organizations"]


def test_declaration_only_builder_does_not_ignore_explicit_attribution():
    attribution = read(ATTRIBUTIONS_FILE)["entries"]["dgm"]
    sources = {"schema": "arena.participant-attributions/1", "entries": {"dgm": attribution}}
    built = build_participant_catalog([read("participants/dgm.json")], attributions=sources)
    assert built["participants"][0]["attribution"] == attribution
    assert built["summary"]["research_work_count"] == 0
    assert built["summary"]["integrated_count"] == 0


@pytest.mark.parametrize("change", ["changed_source", "missing_source", "missing_snapshot_credit"])
def test_declaration_only_reader_rejects_stale_or_dropped_attribution(tmp_path, change):
    registry = tmp_path / "registry"
    (registry / "participants").mkdir(parents=True)
    declaration = read("participants/dgm.json")
    (registry / "participants/dgm.json").write_text(json.dumps(declaration))
    sources = {"schema": "arena.participant-attributions/1",
               "entries": {"dgm": read(ATTRIBUTIONS_FILE)["entries"]["dgm"]}}
    source_path = registry / ATTRIBUTIONS_FILE
    source_path.write_text(json.dumps(sources))
    snapshot_path = registry / "participants.json"
    snapshot = build_participant_catalog([declaration], attributions=sources)
    snapshot_path.write_text(json.dumps(snapshot))
    assert get_participants(registry) == expected_participants(registry) == snapshot
    if change == "changed_source":
        sources["entries"]["dgm"]["source_locator"] = "Updated reviewed affiliation locator"
        source_path.write_text(json.dumps(sources))
    elif change == "missing_source":
        source_path.unlink()
    else:
        snapshot["participants"][0].pop("attribution")
        snapshot_path.write_text(json.dumps(snapshot))
    before = {path: path.read_bytes() for path in registry.rglob("*.json")}
    message = "refusing to drop research credits" if change == "missing_source" else "differs from the reviewed corpus"
    with pytest.raises(RegistryError, match=message):
        get_participants(registry)
    if change == "missing_source":
        with pytest.raises(RegistryError, match="refusing to drop research credits"):
            expected_participants(registry)
    assert before == {path: path.read_bytes() for path in registry.rglob("*.json")}


@pytest.mark.parametrize("check", [True, False])
def test_missing_attribution_capture_cannot_silently_drop_research_credits(tmp_path, check):
    copied = tmp_path / "registry"
    shutil.copytree(REGISTRY, copied)
    (copied / ATTRIBUTIONS_FILE).unlink()
    before = (copied / "participants.json").read_bytes()
    with pytest.raises(RegistryError, match="refusing to drop research credits"):
        expected_participants(copied)
    with pytest.raises(RegistryError, match="refusing to drop research credits"):
        get_participants(copied)
    command = [sys.executable, str(ROOT / "scripts/build_participants.py"), "--registry-root", str(copied)]
    result = subprocess.run(command + (["--check"] if check else []), capture_output=True, text=True)
    assert result.returncode == 1
    assert "refusing to drop research credits" in result.stderr
    assert (copied / "participants.json").read_bytes() == before


def test_changed_credit_source_requires_explicit_snapshot_rebuild(tmp_path):
    copied = tmp_path / "registry"
    shutil.copytree(REGISTRY, copied)
    sources = read(ATTRIBUTIONS_FILE)
    sources["entries"]["dgm"]["source_locator"] = "Updated review locator: p. 1 author block"
    (copied / ATTRIBUTIONS_FILE).write_text(json.dumps(sources))
    before = {path: path.read_bytes() for path in (copied / ATTRIBUTIONS_FILE, copied / "participants.json")}
    with pytest.raises(RegistryError, match="differs from the reviewed corpus"):
        get_participants(copied)
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_participants.py"),
                             "--registry-root", str(copied), "--check"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "differs from reviewed sources" in result.stderr
    assert before == {path: path.read_bytes() for path in before}


def test_initial_participant_build_without_attribution_or_prior_snapshot_still_works(tmp_path):
    copied = tmp_path / "registry"
    shutil.copytree(REGISTRY, copied)
    (copied / ATTRIBUTIONS_FILE).unlink()
    (copied / "participants.json").unlink()
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_participants.py"),
                             "--registry-root", str(copied)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    built = get_participants(copied)
    assert built["summary"]["research_work_count"] == 98
    assert all("attribution" not in entry for entry in built["participants"])
