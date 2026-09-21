"""Scientific overview must preserve package identity, evidence and count scope."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import pytest

from arena.insights import build_insights, get_insights, validate_insights, validate_taxonomy
from arena.registry import RegistryError, get_catalog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def inputs():
    return get_catalog(), json.loads((ROOT / "registry/taxonomy.json").read_text())


def test_every_package_occurs_once_in_each_complete_partition(inputs):
    catalog, _ = inputs
    insights = get_insights()
    assert set(insights["task_annotations"]) == {task["id"] for task in catalog["tasks"]}
    assert insights["denominator"] == {"unit": "task_package", "task_count": 959}
    for group, key in [("domains", "domain_id"), ("task_types", "task_type_id")]:
        rows = insights[group]
        assert sum(row["total"] for row in rows) == 959
        assert sum(row["executable"] for row in rows) == 689
        assert sum(row["unsupported"] for row in rows) == 270
        assert sum(Decimal(str(row["percentage"])) for row in rows) == Decimal("100.0")
        for row in rows:
            assert row["total"] == row["executable"] + row["unsupported"]
            assert row["total"] == sum(a[key] == row["id"] for a in insights["task_annotations"].values())
            assert all(insights["task_annotations"][ident][key] == row["id"] for ident in row["representative_task_ids"])


def test_all_151_source_families_have_documented_defaults(inputs):
    catalog, taxonomy = inputs
    families = {task["family"] for task in catalog["tasks"] if task["family"] is not None}
    defaults = {rule["match"]["families"][0] for rule in taxonomy["rules"] if rule["id"].startswith("family-")}
    assert len(families) == 151
    assert defaults == families


def test_primary_domain_follows_candidate_target_not_topic_keyword():
    annotations = get_insights()["task_annotations"]
    assert annotations["rankevolve-biology"]["domain_id"] == "machine-learning"
    assert annotations["adas-gpqa"]["domain_id"] == "machine-learning"
    assert annotations["coevo-e-coli-growth"]["domain_id"] == "biology-health"
    assert annotations["dga2d-ode-solver-robertson"]["domain_id"] == "chemistry-materials"
    assert annotations["evoprompting-bfs"]["domain_id"] == "machine-learning"
    assert annotations["evoprompting-bfs"]["task_type_id"] == "prediction-modeling"
    assert annotations["enpire-pin-insertion"]["task_type_id"] == "control-policy"
    assert annotations["coral-frontier-cs-polyominoes-packing"]["domain_id"] == "mathematics"
    assert annotations["sciel-bench-sldbench-sft-scaling-law"]["domain_id"] == "machine-learning"


@pytest.mark.parametrize("task_id,domain_id,task_type_id", [
    ("kaggle-santa-2025-christmas-tree-packing", "mathematics", "mathematical-construction"),
    ("science-tcs-red-blue-pebbling", "mathematics", "combinatorial-optimization"),
    ("science-tcs-streaming-frequency-sketches", "mathematics", "systems-optimization"),
    ("science-biology-proteingym-fitness", "biology-health", "prediction-modeling"),
    ("science-biology-eterna-rna-design", "biology-health", "black-box-optimization"),
    ("science-biology-fmd-microscopy-denoising", "biology-health", "signal-processing"),
    ("science-materials-cantera-mechanism-reduction", "chemistry-materials", "combinatorial-optimization"),
    ("science-materials-kmcpy-ionic-transport", "chemistry-materials", "numerical-solver"),
    ("science-earth-irrigation-policies", "earth-environment", "control-policy"),
    ("science-climate-lorenz96-subgrid-closure", "earth-environment", "symbolic-regression"),
    ("science-physics-robust-transmon-control", "physics", "control-policy"),
    ("science-physics-ariel-atmospheric-posterior", "physics", "prediction-modeling"),
    ("science-quantum-ising-vqe", "physics", "black-box-optimization"),
    ("science-economics-structural-demand-estimation", "finance-economics", "prediction-modeling"),
    ("science-economics-finite-auction-design", "finance-economics", "mathematical-construction"),
])
def test_science_expansion_follows_target_and_candidate_operation(task_id, domain_id, task_type_id):
    annotation = get_insights()["task_annotations"][task_id]
    assert (annotation["domain_id"], annotation["task_type_id"]) == (domain_id, task_type_id)


def test_alias_merge_retains_reviewed_classification_without_duplicate_membership(inputs):
    catalog, taxonomy = inputs
    annotations = get_insights()["task_annotations"]
    catalog_ids = {task["id"] for task in catalog["tasks"]}
    exact_ids = {ident for rule in taxonomy["rules"] for ident in rule["match"].get("task_ids", [])}
    assert exact_ids <= catalog_ids
    assert "a2dept-ode-integration-robertson-kinetics" not in annotations
    assert "adaevolve-frontier-cs" not in annotations
    assert annotations["dga2d-ode-solver-robertson"]["domain_id"] == "chemistry-materials"
    assert annotations["evox-frontier-cs"]["domain_id"] == "unknown"


def test_opaque_or_mixed_metadata_remains_unknown():
    insights = get_insights()
    assert insights["summary"]["unknown_domain_count"] == 7
    assert insights["summary"]["unknown_task_type_count"] == 3
    assert insights["task_annotations"]["evox-frontier-cs"]["domain_id"] == "unknown"
    assert insights["task_annotations"]["drsr-lsr-synth-crk0"]["domain_id"] == "unknown"
    assert insights["task_annotations"]["drsr-lsr-synth-crk0"]["task_type_id"] == "symbolic-regression"


def test_papers_and_supplements_are_separate_and_coverage_is_not_readiness(inputs):
    insights = get_insights()
    summary = insights["summary"]
    assert summary["corpus_paper_count"] == 98
    assert summary["source_group_count"] == summary["unique_paper_count"] == 113
    catalog, taxonomy = inputs
    source_ids = {ident for task in catalog["tasks"] for ident in task["paper_ids"]}
    non_papers = set(taxonomy["non_paper_source_ids"])
    assert len(non_papers) == 15
    assert non_papers <= source_ids
    assert {"sciel-supplement", "kaggle-santa-2025", "science-earth_data", "science-physics_expansion"} <= non_papers
    assert len(source_ids - non_papers) == summary["corpus_paper_count"]
    coverage = {row["id"]: row for row in insights["coverage"]}
    assert coverage["runtime_verified"]["total"] == 0
    assert coverage["original"]["total"] == 130
    assert coverage["recreated"]["total"] == 478
    assert coverage["recorded_contract"]["total"] == 689
    assert coverage["recreated_verified"]["total"] == 81
    assert "not independently" in coverage["recreated_verified"]["description"]
    assert "editorial inference" in insights["methodology"]["classification_authority"]
    assert "not counts of unique scientific problems" in insights["methodology"]["unit"]


@pytest.mark.parametrize("change", [
    lambda value: value["domains"][0].update(total=9999),
    lambda value: value["task_annotations"]["adas-gpqa"].update(domain_id="physics"),
    lambda value: value["task_annotations"].pop("adas-gpqa"),
    lambda value: value["summary"].update(corpus_paper_count=99),
])
def test_snapshot_membership_and_counts_cannot_drift(inputs, change):
    catalog, taxonomy = inputs
    snapshot = build_insights(catalog, taxonomy)
    change(snapshot)
    with pytest.raises(RegistryError, match="membership"):
        validate_insights(snapshot, catalog, taxonomy)


def test_changed_catalog_or_taxonomy_requires_rebuild(inputs):
    catalog, taxonomy = deepcopy(inputs)
    snapshot = build_insights(catalog, taxonomy)
    catalog["tasks"][0]["description"] += " Reviewed metadata changed."
    with pytest.raises(RegistryError, match="catalog digest"):
        validate_insights(snapshot, catalog, taxonomy)
    catalog, taxonomy = deepcopy(inputs)
    taxonomy["domains"][0]["description"] += " Revised definition."
    with pytest.raises(RegistryError, match="taxonomy digest"):
        validate_insights(snapshot, catalog, taxonomy)


@pytest.mark.parametrize("change", [
    lambda value: value["rules"][0].update(domain_id="invented"),
    lambda value: value["rules"][0].update(match={"execute": ["program.py"]}),
    lambda value: value["rules"].append(deepcopy(value["rules"][0])),
    lambda value: value["domains"].append(deepcopy(value["domains"][0])),
    lambda value: value["rules"][-1].update(domain_id="physics"),
])
def test_invalid_taxonomy_rejected(inputs, change):
    taxonomy = deepcopy(inputs[1])
    change(taxonomy)
    with pytest.raises(RegistryError):
        validate_taxonomy(taxonomy)


def test_deleted_task_does_not_leave_silent_taxonomy_reference(inputs):
    catalog, taxonomy = deepcopy(inputs)
    taxonomy["rules"][0]["match"]["task_ids"] = ["does-not-exist"]
    with pytest.raises(RegistryError, match="absent task IDs"):
        build_insights(catalog, taxonomy)


def test_build_is_deterministic_and_api_values_are_detached(inputs):
    catalog, taxonomy = inputs
    assert build_insights(catalog, taxonomy) == build_insights(deepcopy(catalog), deepcopy(taxonomy))
    first = get_insights()
    first["summary"]["task_count"] = 1
    assert get_insights()["summary"]["task_count"] == 959


def test_check_command_never_rewrites_and_rejects_stale_snapshot(tmp_path):
    for filename in ["catalog.json", "taxonomy.json", "insights.json"]:
        (tmp_path / filename).write_bytes((ROOT / "registry" / filename).read_bytes())
    command = [sys.executable, str(ROOT / "scripts/build_insights.py"), "--check", "--registry-root", str(tmp_path)]
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    snapshot = json.loads((tmp_path / "insights.json").read_text())
    snapshot["catalog_digest"] = "0" * 64
    (tmp_path / "insights.json").write_text(json.dumps(snapshot))
    altered = (tmp_path / "insights.json").read_bytes()
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1 and "catalog digest" in result.stderr
    assert (tmp_path / "insights.json").read_bytes() == altered
