"""Reviewed literature entries, separate from pinned execution registrations.

The importer reads a supplied document and existing pinned bibliography only.
It performs no network requests, code imports, builds or evaluations.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlsplit

from arena.registry import (CAPABILITIES, RegistryError, _json, _object, _require,
                            _text, _hash, _SHA256, validate_participant,
                            participant_view, validate_participants)


SOURCE_FILE = "participant-corpus.json"
DESCRIPTIONS_FILE = "participant-descriptions.json"
ALIASES = {"shinkaevolve": "shinka", "dgm": "dgm"}
FAMILIES = {"FunSearch / EoH": "funsearch-eoh", "AlphaEvolve / OpenEvolve": "alphaevolve-openevolve",
            "DGM / ADAS": "dgm-adas", "Promptbreeder / EvoPrompt": "promptbreeder-evoprompt",
            "Eureka": "eureka", "LLM-SR": "llm-sr", "Other": "other"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def normalized_title(value):
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", ascii_value.lower())


def _match_heading(heading, papers):
    match = re.fullmatch(r"(.+) - (20\d\d) - (.+)", heading)
    _require(match is not None, "Corpus work heading needs title, year and venue")
    title, year, venue = match.groups()
    keys = [normalized_title(title), normalized_title(re.sub(r" \([^()]*\)$", "", title))]
    for key in keys:
        matches = [p for p in papers if p["source_kind"] == "corpus_paper" and normalized_title(p["title"]) == key]
        _require(len(matches) <= 1, "Ambiguous corpus title; review the bibliography before importing")
        if matches:
            return matches[0], int(year), venue
    raise RegistryError(f"Corpus title has no exact bibliography match: {title}")


def code_links(paper_id, note):
    """Keep only work-related links, with explicit artifact/project scope.

    These exceptions are reviewed against the supplied code-link sentences;
    inherited frameworks and benchmark/baseline repositories are not presented
    as the implementation of a different research work.
    """
    if paper_id in {"funbo", "avo", "codeevolve-salesforce", "elm", "algoevolve", "flowscout"}:
        return []
    urls = re.findall(r"https?://[^\s;)\]]+", note)
    urls = list(dict.fromkeys(url.rstrip(".,#") for url in urls))
    if paper_id in {"rankevolve", "ahe", "qdaif", "llamea-hpo"}:
        urls = urls[:1]
    links = []
    for index, url in enumerate(urls):
        host = urlsplit(url).hostname
        kind = "implementation" if host in {"github.com", "anonymous.4open.science"} else "project"
        label = "Code" if kind == "implementation" else "Project page"
        if paper_id == "alphaevolve":
            kind, label = "artifact", "Result notebook"
        elif paper_id == "meta-harness" and host == "github.com":
            kind, label = "artifact", "Harness artifact"
        elif paper_id == "the-station" and index == 1:
            kind, label = "artifact", "Experiment artifacts"
        elif paper_id in {"llamea-hpo", "llm-flowrepair"}:
            kind, label = "artifact", "Replication package"
        elif paper_id == "llamea-mobo":
            kind, label = "artifact", "Algorithm code"
        links.append({"url": url, "label": label, "kind": kind})
    return links


def capture_corpus(raw, source_metadata):
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    entries, family, active = [], None, None

    def finish(end):
        nonlocal active
        if active is None:
            return
        start, heading, group = active
        paper, year, venue = _match_heading(heading, source_metadata["papers"])
        _require(group == paper["declared_family"], "Corpus family differs from pinned bibliography")
        section = "".join(lines[start:end])
        def field(label):
            values = [line.strip()[len(label):].strip() for line in lines[start:end] if line.strip().startswith(label)]
            _require(len(values) == 1, f"Corpus work needs one {label} field")
            return values[0]
        mechanism, notes = field("- что делали:"), field("- ссылки на код:")
        entries.append({"paper_id": paper["id"], "heading": heading, "year": year, "venue": venue,
                        "family": group, "line_start": start + 1, "line_end": end,
                        "section_sha256": hashlib.sha256(section.encode()).hexdigest(),
                        "mechanism": mechanism, "code_note": notes,
                        "code_links": code_links(paper["id"], notes)})
        active = None

    for index, line in enumerate(lines):
        if line.startswith("## "):
            finish(index)
            family = line[3:].strip()
        elif line.startswith("#### "):
            finish(index)
            _require(family in FAMILIES, "Corpus work has an unreviewed family")
            active = (index, line[5:].strip(), family)
    finish(len(lines))
    result = {"schema": "arena.participant-corpus/1",
              "source": {"id": "human-harness-corpus", "filename": "human-harness-corpus.md",
                         "sha256": hashlib.sha256(raw).hexdigest(), "line_count": len(lines), "work_count": len(entries)},
              "bibliography_digest": digest(source_metadata), "works": entries}
    validate_corpus(result, source_metadata)
    return result


def validate_corpus(value, source_metadata):
    _object(value, ("schema", "source", "bibliography_digest", "works"), "participant corpus")
    _require(value["schema"] == "arena.participant-corpus/1", "Unknown participant corpus schema")
    _require(value["bibliography_digest"] == digest(source_metadata), "Participant corpus bibliography digest is stale")
    source = _object(value["source"], ("id", "filename", "sha256", "line_count", "work_count"), "corpus source")
    _require(source["id"] == "human-harness-corpus" and source["filename"] == "human-harness-corpus.md", "Unexpected corpus source identity")
    _hash(source["sha256"], _SHA256, "corpus SHA256")
    _require(type(source["line_count"]) is int and source["line_count"] > 0, "Invalid corpus line count")
    _require(type(value["works"]) is list and bool(value["works"]), "Missing corpus works")
    seen, previous_end = set(), 0
    for work in value["works"]:
        _object(work, ("paper_id", "heading", "year", "venue", "family", "line_start", "line_end",
                       "section_sha256", "mechanism", "code_note", "code_links"), "corpus work")
        paper, year, venue = _match_heading(work["heading"], source_metadata["papers"])
        _require(work["paper_id"] == paper["id"] and work["paper_id"] not in seen, "Duplicate or mismatched corpus work")
        seen.add(work["paper_id"])
        _require(type(work["year"]) is int and work["year"] == year and work["venue"] == venue, "Corpus bibliography disagrees with heading")
        _require(work["family"] in FAMILIES and work["family"] == paper["declared_family"], "Corpus family disagrees with bibliography")
        _require(type(work["line_start"]) is int and type(work["line_end"]) is int
                 and previous_end < work["line_start"] <= work["line_end"] <= source["line_count"], "Overlapping or invalid corpus line spans")
        previous_end = work["line_end"]
        _hash(work["section_sha256"], _SHA256, "corpus section SHA256")
        for key in ("heading", "venue", "family", "mechanism", "code_note"):
            _text(work[key], f"corpus {key}")
        _require(work["code_links"] == code_links(work["paper_id"], work["code_note"]), "Corpus code-link scope differs from reviewed extraction")
    expected = {p["id"] for p in source_metadata["papers"] if p["source_kind"] == "corpus_paper"}
    _require(seen == expected, "Corpus works must cover the entire pinned research bibliography exactly once")
    _require(type(source["work_count"]) is int and source["work_count"] == len(seen), "Corpus work count disagrees with entries")
    return value


def build_participant_catalog(declarations, corpus=None, descriptions=None, bibliography=None):
    records = {}
    for declaration in declarations:
        validate_participant(declaration)
        _require(declaration["repository"] is not None, "Pinned declarations require an immutable repository")
        _require(declaration["id"] not in records, "Duplicate participant declaration")
        records[declaration["id"]] = deepcopy(declaration)
    if corpus is None:
        return validate_participants(participant_view(sorted(records.values(), key=lambda p: p["id"])))
    validate_corpus(corpus, bibliography)
    _object(descriptions, ("schema", "descriptions"), "participant descriptions")
    _require(descriptions["schema"] == "arena.participant-descriptions/1" and type(descriptions["descriptions"]) is dict,
             "Invalid participant descriptions schema")
    _require(set(descriptions["descriptions"]) == {w["paper_id"] for w in corpus["works"]}, "Descriptions must cover every corpus work exactly once")
    papers = {p["id"]: p for p in bibliography["papers"]}
    metadata_source = next(f for f in bibliography["files"] if f["path"] == "catalog/papers.json")
    for record in records.values():
        record.update(record_kind="system_registration", papers=[], search_family=None,
                      code_links=[{"url": record["repository"]["url"], "label": "Code", "kind": "implementation"}], provenance=None)
    for work in corpus["works"]:
        paper_id = work["paper_id"]
        paper, ident = papers[paper_id], ALIASES.get(paper_id, paper_id)
        description = descriptions["descriptions"][paper_id]
        _text(description, "participant research description")
        _require(len(description) <= 700, "Participant research descriptions must be concise")
        if ident in records:
            _require(records[ident]["repository"]["url"] in {link["url"] for link in work["code_links"]},
                     "A literature work collides with a different pinned system")
            record = records[ident]
        else:
            record = {"id": ident, "name": paper["name"], "description": description, "repository": None,
                      "record_kind": "research_work", "registration_status": "literature", "adapter_status": "not_implemented",
                      "capabilities": {name: False for name in CAPABILITIES}, "supported_protocols": [], "limitations": []}
        record.update(papers=[{"id": paper_id, "title": paper["title"], "url": paper["paper_url"],
                               "year": work["year"], "venue": work["venue"],
                               "kind": "technical_report" if work["venue"].startswith("self-hosted") else "paper"}],
                      search_family={"id": FAMILIES[work["family"]], "label": work["family"]},
                      code_links=deepcopy(work["code_links"]),
                      provenance={"source_id": corpus["source"]["id"], "filename": corpus["source"]["filename"],
                                  "sha256": corpus["source"]["sha256"], "line_start": work["line_start"], "line_end": work["line_end"],
                                  "heading": work["heading"], "section_sha256": work["section_sha256"],
                                  "metadata_source": deepcopy(metadata_source),
                                  "description_basis": "Pinned system declaration; corpus supplies the bibliography." if record["record_kind"] == "system_registration"
                                                       else "Arena editorial summary of the source mechanism; not an execution result."})
        records[ident] = record
    return validate_participants(participant_view(sorted(records.values(), key=lambda p: (p["name"].casefold(), p["id"]))))


def expected_participants(root):
    declarations = [_json(path) for path in sorted((root / "participants").glob("*.json"))]
    if not (root / SOURCE_FILE).exists():
        if (root / "participants.json").exists():
            old = _json(root / "participants.json")
            _require(not any(item.get("papers") or item.get("record_kind") == "research_work" for item in old.get("participants", [])),
                     "Missing corpus capture; refusing to drop scholarly participant entries")
        return build_participant_catalog(declarations)
    return build_participant_catalog(declarations, _json(root / SOURCE_FILE), _json(root / DESCRIPTIONS_FILE),
                                     _json(root / "search-family-sources.json"))
