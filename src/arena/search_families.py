"""Source-declared research-family links, never framework execution claims."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from arena.insights import canonical_digest
from arena.registry import (RegistryError, _json, _hash, _SHA256, _text, _url,
                            resolve_registry_root, validate_catalog)


FAMILIES = (
    ("alphaevolve-openevolve", "AlphaEvolve / OpenEvolve", "The corpus groups these works under the AlphaEvolve / OpenEvolve lineage.", "Explore the tasks attached to this program-search lineage, from mathematical constructions to systems optimization."),
    ("funsearch-eoh", "FunSearch / EoH", "The corpus groups these works under the FunSearch / EoH lineage.", "Connect heuristic and algorithm-design research with its routing, packing, optimizer and numerical-method tasks."),
    ("dgm-adas", "DGM / ADAS", "The corpus groups these works under the DGM / ADAS lineage.", "Explore how agent and workflow evolution is studied through coding, reasoning and tool-use tasks."),
    ("eureka", "Eureka", "The corpus groups these works under the Eureka lineage.", "Connect reward, learning and control research with the embodied environments used to evaluate it."),
    ("llm-sr", "LLM-SR", "The corpus groups these works under the LLM-SR lineage.", "Trace symbolic-regression research to the scientific equations and synthetic relationships it models."),
    ("promptbreeder-evoprompt", "Promptbreeder / EvoPrompt", "The corpus groups these works under the Promptbreeder / EvoPrompt lineage.", "Connect prompt and language-agent optimization with the benchmark tasks used in the source works."),
    ("other", "Other", "The corpus assigns these works to Other; this is a mixed source category, not a single search algorithm.", "Keep research outside the named lineages visible without inventing a common method or compatibility claim."),
    ("sciel-supplement", "SCiEL supplement", "Additional SCiEL task examples recorded by the source repository; this is not a research-paper method family.", "Expose the supplementary examples alongside the paper-derived catalog while preserving their separate provenance."),
    ("science-supplement", "Science supplement", "Scientific task collections added by the source repository; these collections are not research-paper method families.", "Explore the added scientific tasks while keeping their collection provenance separate from the research corpus."),
    ("community-supplement", "Community supplement", "Community benchmark collections added by the source repository; these collections are not research-paper method families.", "Explore community tasks with their original benchmark provenance."),
    ("unknown", "Unmapped source family", "The captured source label has no reviewed display mapping.", "Preserve new or missing source labels explicitly until their grouping is reviewed."),
)
FAMILY_IDS = {label: ident for ident, label, _, _ in FAMILIES[:-1]}
SUPPLEMENT_FAMILIES = {
    "sciel-supplement": "SCiEL supplement",
    "kaggle-santa-2025": "Community supplement",
    **{ident: "Science supplement" for ident in (
        "science-tcs", "science-cosmology", "science-particle", "science-quantum",
        "science-climate", "science-chemistry", "science-biology_expansion",
        "science-materials_expansion", "science-earth_expansion", "science-earth_data",
        "science-physics_expansion", "science-economics_expansion", "science-tcs_expansion",
    )},
}
SUPPLEMENT_GROUPS = {FAMILY_IDS[label] for label in SUPPLEMENT_FAMILIES.values()}


def _require(condition, message):
    if not condition:
        raise RegistryError(message)


def validate_sources(data, catalog):
    _require(type(data) is dict and data.get("schema") == "arena.search-family-sources/1", "Unsupported search-family source schema")
    _require(data.get("catalog_binding") in catalog["sources"], "Search-family source revision differs from catalog")
    binding = data["catalog_binding"]
    files = data.get("files")
    paths = {"catalog/papers.json", "catalog/corpus.json", "catalog/research.json"}
    _require(type(files) is list and len(files) == len(paths), "Missing source-file evidence")
    _require(all(type(source) is dict for source in files) and {source.get("path") for source in files} == paths, "Invalid source-file evidence paths")
    for source in files:
        _require(set(source) == {"path", "url", "sha256"}, "Invalid source-file evidence fields")
        _hash(source["sha256"], _SHA256, "search-family source SHA256")
        expected = f"{binding['repository']['url']}/blob/{binding['repository']['commit']}/{source['path']}"
        _require(source["url"] == expected, "Search-family evidence URL must match pinned source")
    papers = data.get("papers")
    _require(type(papers) is list and bool(papers), "Missing captured paper records")
    ids, source_task_ids = set(), {task["id"] for task in catalog["tasks"]}
    for paper in papers:
        _require(type(paper) is dict and set(paper) == {"id", "name", "title", "declared_family", "paper_url", "corpus_url", "source_kind", "declared_task_ids"}, "Invalid captured paper fields")
        for key in ("id", "name", "title"):
            _text(paper[key], "search-family paper " + key)
        _require(paper["id"] not in ids, "Duplicate source paper ID")
        ids.add(paper["id"])
        _text(paper["declared_family"], "declared family", nullable=True)
        for key in ("paper_url", "corpus_url"):
            if paper[key] is not None:
                _url(paper[key], key)
        _require(paper["source_kind"] in ("corpus_paper", "supplement"), "Invalid source kind")
        _require((paper["id"] in SUPPLEMENT_FAMILIES) == (paper["source_kind"] == "supplement"), "Supplement is not a research paper")
        if paper["source_kind"] == "supplement":
            _require(paper["declared_family"] == SUPPLEMENT_FAMILIES[paper["id"]], "Supplement family differs from reviewed source identity")
        declared = paper["declared_task_ids"]
        _require(type(declared) is list and all(type(ident) is str for ident in declared)
                 and len(set(declared)) == len(declared), "Invalid declared task links")
        _require(set(declared) <= source_task_ids, "Source paper references an absent task")
        for task in catalog["tasks"]:
            if task["id"] in declared:
                _require(paper["id"] in task["paper_ids"], "Source paper/task association contradicts catalog")
    _require(ids == {paper for task in catalog["tasks"] for paper in task["paper_ids"]}, "Captured paper IDs do not cover catalog source groups")
    return data


def build_search_families(catalog, source_data):
    validate_catalog(catalog)
    validate_sources(source_data, catalog)
    papers = {paper["id"]: paper for paper in source_data["papers"]}
    families = {ident: FAMILY_IDS.get(paper["declared_family"], "unknown") for ident, paper in papers.items()}
    tasks = sorted(catalog["tasks"], key=lambda task: task["id"])
    annotations = {}
    for task in tasks:
        _require(bool(task["paper_ids"]), "Task has no source paper association")
        primary = task["paper_ids"][0]
        related = sorted({families[paper] for paper in task["paper_ids"]})
        annotations[task["id"]] = {
            "search_family_id": families[primary], "primary_paper_id": primary,
            "paper_ids": list(task["paper_ids"]), "related_search_family_ids": related,
            "rationale": "Placed once using the first catalog paper ID; all source-paper and family associations are retained. This placement is for display, not a scientific-priority claim.",
        }
    groups = []
    for ident, label, description, why in FAMILIES:
        member_papers = sorted(paper for paper, family in families.items() if family == ident)
        if not member_papers:
            continue
        members = [task for task in tasks if annotations[task["id"]]["search_family_id"] == ident]
        addressed = [task["id"] for task in tasks if ident in annotations[task["id"]]["related_search_family_ids"]]
        examples, seen = [], set()
        for task in sorted(members, key=lambda item: (not item["executable"], item["id"])):
            key = task["family"] or task["paper_ids"][0]
            if key not in seen:
                seen.add(key)
                examples.append(task["id"])
            if len(examples) == 4:
                break
        groups.append({"id": ident, "label": label, "description": description, "why_it_matters": why,
                       "classification_basis": "source_supplement" if ident in SUPPLEMENT_GROUPS else "unmapped_source_family" if ident == "unknown" else "corpus_declared_family",
                       "paper_ids": member_papers,
                       "paper_count": sum(papers[paper]["source_kind"] == "corpus_paper" for paper in member_papers),
                       "source_group_count": len(member_papers),
                       "task_ids": [task["id"] for task in members], "task_count": len(members), "total": len(members),
                       "executable": sum(task["executable"] for task in members),
                       "unsupported": sum(not task["executable"] for task in members),
                       "addressed_task_ids": addressed, "addressed_task_count": len(addressed),
                       "representative_task_ids": examples})
    paper_evidence = next(source for source in source_data["files"] if source["path"] == "catalog/papers.json")
    paper_annotations = {}
    for ident, paper in sorted(papers.items()):
        linked = [task["id"] for task in tasks if ident in task["paper_ids"]]
        paper_annotations[ident] = {"name": paper["name"], "title": paper["title"],
                                    "search_family_id": families[ident], "declared_family": paper["declared_family"],
                                    "source_kind": paper["source_kind"], "paper_url": paper["paper_url"],
                                    "corpus_url": paper["corpus_url"], "source": {**paper_evidence, "locator": f"record id={ident}; field family"},
                                    "task_ids": linked, "declared_task_ids": paper["declared_task_ids"],
                                    "additional_catalog_task_ids": sorted(set(linked) - set(paper["declared_task_ids"]))}
    summary = {"task_count": len(tasks), "source_group_count": len(papers),
               "corpus_paper_count": sum(paper["source_kind"] == "corpus_paper" for paper in papers.values()),
               "group_count": len(groups), "unknown_family_source_count": sum(value == "unknown" for value in families.values()),
               "unknown_family_task_count": sum(a["search_family_id"] == "unknown" for a in annotations.values()),
               "cross_family_task_count": sum(len(a["related_search_family_ids"]) > 1 for a in annotations.values()),
               "executable_count": sum(task["executable"] for task in tasks),
               "unsupported_count": sum(not task["executable"] for task in tasks)}
    return {"schema": "arena.search-families/1", "catalog_digest": canonical_digest(catalog),
            "source_digest": canonical_digest(source_data), "sources": deepcopy(source_data["files"]),
            "summary": summary, "groups": groups, "task_annotations": annotations, "paper_annotations": paper_annotations,
            "methodology": {
                "classification": "Family labels are copied from the pinned task repository's catalog/papers.json. Research papers are cross-checked against catalog/corpus.json; supplementary collections require a reviewed source ID and matching supplement label. Research families are the corpus curator's grouping, not a classification invented by Arena or necessarily claimed by every paper author. Descriptions are editorial navigation text.",
                "scope": "Edges mean a catalog task is associated with a source paper or supplementary collection in that family. They never mean a registered framework solved it, ran it, supports its runtime or has a compatible adapter.",
                "partition": "Each task is placed exactly once under the family of its first catalog paper ID. The order is a deterministic display convention; it is not a hierarchy of scientific credit. All paper IDs and related families remain visible.",
                "secondary_links": "related_search_family_ids includes the primary family. addressed_task_ids includes every linked paper family and can overlap across groups; it must not be summed as a unique-task count. task_ids/task_count is the nonoverlapping layout partition.",
                "task_links": "Task-level catalog.paper_ids is authoritative. The source paper inventories omit some reference-* examples; these additional links are retained separately as additional_catalog_task_ids, not represented as reported paper experiments.",
                "counts": "Counts are canonical task packages, including parameter variants. Upstream merged duplicate packages retain all source-paper associations. paper_count counts corpus papers; source_group_count also includes the SCiEL, Science and Community supplements. Other is the source's mixed bucket; supplements are not research-method families.",
                "unknown": "Missing or previously unseen family labels map to an explicit unknown group while retaining their original value. Empty unknown groups are omitted; summary records zero unknown counts.",
                "provenance": "The source extraction records exact Git revision, file paths and SHA256 of original committed bytes. Offline validation checks the captured source records, catalog associations, snapshot digests and every derived group.",
            }}


def validate_search_families(data, catalog, source_data):
    _require(type(data) is dict and data.get("schema") == "arena.search-families/1", "Unsupported search-families schema")
    _require(data.get("catalog_digest") == canonical_digest(catalog), "Stale search families: catalog digest differs")
    _require(data.get("source_digest") == canonical_digest(source_data), "Stale search families: source digest differs")
    expected = build_search_families(catalog, source_data)
    _require(canonical_digest(data) == canonical_digest(expected), "Search-family membership, evidence or totals differ from deterministic build")
    return data


def get_search_families(registry_root: str | Path | None = None):
    root = resolve_registry_root(registry_root)
    return validate_search_families(_json(root / "search-families.json"), _json(root / "catalog.json"),
                                    _json(root / "search-family-sources.json"))
