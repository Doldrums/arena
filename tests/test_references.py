"""Scientific evidence semantics, using only the shipped offline snapshot."""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from arena.references import get_references, summarize, validate_references
from arena.registry import RegistryError, get_catalog


@pytest.fixture(scope="module")
def catalog():
    return get_catalog()


@pytest.fixture(scope="module")
def snapshot():
    return get_references()


def task(snapshot, task_id):
    return next(row for row in snapshot["tasks"] if row["task_id"] == task_id)


def anchor(snapshot, task_id, kind="published_reference"):
    return next(row for row in task(snapshot, task_id)["anchors"] if row["kind"] == kind)


def test_full_coverage_and_honest_evidence_counts(snapshot, catalog):
    assert {row["task_id"] for row in snapshot["tasks"]} == {row["id"] for row in catalog["tasks"]}
    summary = snapshot["summary"]
    assert summary["task_count"] == 1138
    assert summary["tasks_with_published_reference"] == 122
    assert summary["tasks_with_recorded_baseline"] == 697
    assert summary["valid_recorded_baselines"] == 603
    assert summary["validity_unknown_baselines"] == 94
    assert summary["tasks_without_numeric_reference"] == 441
    assert summary["tasks_with_recorded_reproduction"] == 34
    assert summary["arena_reproduced_references"] == 0
    assert summary["current_sota_status"] == "not_assessed"


def test_missing_is_empty_not_zero_and_zero_is_a_real_score(snapshot):
    missing = [row for row in snapshot["tasks"] if row["status"] == "missing"]
    assert missing and all(row["anchors"] == [] for row in missing)
    zeros = [a for row in snapshot["tasks"] for a in row["anchors"] if a["value"] == 0]
    assert zeros and all(a["kind"] == "recorded_seed_baseline" for a in zeros)
    assert all(a["source"]["path"] == "validation/suite-report.json" for a in zeros)


def test_complex_tensor_rank_and_raw_minimization(snapshot):
    row = task(snapshot, "alphaevolve-matrix-multiplication-4-4-4")
    assert row["evaluation"]["parameters"]["coefficient_domain"] == "gaussian_half_integers"
    published = anchor(snapshot, row["task_id"])
    baseline = anchor(snapshot, row["task_id"], "recorded_seed_baseline")
    assert (published["value"], published["direction"]) == (48, "minimize")
    assert baseline["value"] == 64
    assert baseline["reported_combined_score"] == -64
    assert published["reproduction"] == "recorded_upstream"
    assert published["reproduction_source"]["path"] == "validation/tensor-exact.json"


def test_geometry_metric_transforms_are_explicit(snapshot):
    distance = anchor(snapshot, "adaevolve-min-max-distance-dimension-3")
    assert "Squared" in distance["metric_label"]
    assert distance["value"] == 4.1658497672256525
    triangle = next(a for row in snapshot["tasks"] for a in row["anchors"]
                    if a["kind"] == "published_reference" and "enclosing equilateral" in a["metric_label"])
    assert " / " in triangle["metric_label"]
    circle = anchor(snapshot, "alphaevolve-circle-packing-in-unit-square")
    assert circle["value"] == 2.6358627564136983
    assert any("strict" in note for note in circle["notes"])


def test_notebook_variants_are_not_merged(snapshot):
    third = anchor(snapshot, "alphaevolve-third-autocorrelation-inequality")
    absolute = anchor(snapshot, "alphaevolve-signed-autocorrelation-maximum-absolute-value-variant")
    assert third["value"] == 1.4556427953745406
    assert absolute["value"] == 1.4687620697410226
    assert third["metric_label"] != absolute["metric_label"]


def test_llm_historical_smoke_and_configured_default_are_distinct(snapshot):
    row = task(snapshot, "promptbreeder-gsm8k")
    baseline = anchor(snapshot, row["task_id"], "recorded_seed_baseline")
    assert row["evaluation"]["case_count"] == 10
    assert row["evaluation"]["case_count_kind"] == "configured_default"
    assert baseline["evaluation"]["case_count"] == 5
    assert baseline["evaluation"]["case_count_kind"] == "historical_smoke"
    assert baseline["value"] == 1.0
    assert baseline["comparison"] == "historical_smoke_only"
    assert any("full named benchmark" in note for note in baseline["notes"])
    assert all(a["kind"] != "published_reference" for a in row["anchors"])


def test_regression_split_denominator_and_ode_score(snapshot):
    row = task(snapshot, "coevo-oscillation-1")
    assert row["evaluation"]["case_count"] == 10000
    assert set(row["evaluation"]["splits"]) == {"train", "test_id", "test_ood"}
    assert all(split["source"]["sha256"] for split in row["evaluation"]["splits"].values())
    baseline = anchor(snapshot, row["task_id"], "recorded_seed_baseline")
    assert baseline["metric_label"] == "NMSE on the in-distribution test split"
    assert baseline["value"] == 0.09591592602181821
    ode = anchor(snapshot, "a2dept-ode-integration-van-der-pol-oscillator", "recorded_seed_baseline")
    assert "function evaluations" in ode["metric_label"]


def test_wrapper_score_is_not_presented_as_paper_cost(snapshot):
    baseline = anchor(snapshot, "coral-cloudcast", "recorded_seed_baseline")
    assert "Wrapper fitness" in baseline["metric_label"]
    assert baseline["score_space"] == "reported_score_or_selected_fitness"
    assert baseline["automatic_comparison"] is False
    assert baseline["direction"] == "maximize"


@pytest.mark.parametrize("mutation", [
    lambda d: d["catalog_binding"]["repository"].update(commit="0" * 40),
    lambda d: d["catalog_binding"].update(catalog_sha256="0" * 64),
    lambda d: d["tasks"].pop(),
    lambda d: d["tasks"].append(deepcopy(d["tasks"][0])),
    lambda d: d["summary"].update(valid_recorded_baselines=697),
    lambda d: d["tasks"][0].update(direction="maximize"),
])
def test_tampered_coverage_or_binding_rejected(snapshot, catalog, mutation):
    data = deepcopy(snapshot)
    mutation(data)
    with pytest.raises(RegistryError):
        validate_references(data, catalog)


@pytest.mark.parametrize("field,value", [
    ("value", float("nan")), ("value", True), ("metric", "combined_score"),
    ("direction", "minimize"), ("current_sota", "verified_current_sota"),
    ("automatic_comparison", True), ("reproduction", "arena_reproduced"),
    ("validity", False),
])
def test_unsupported_claims_and_metric_mismatch_rejected(snapshot, catalog, field, value):
    data = deepcopy(snapshot)
    item = anchor(data, "alphaevolve-circle-packing-in-unit-square")
    item[field] = value
    with pytest.raises(RegistryError):
        validate_references(data, catalog)


def test_isolated_snapshot_return_and_offline_cli(snapshot):
    data = get_references()
    data["tasks"].clear()
    assert len(get_references()["tasks"]) == 1138
    result = subprocess.run([sys.executable, "-m", "arena.references", "validate"],
                            text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == snapshot["summary"]


def test_no_local_workstation_paths_or_unpinned_source_links(snapshot):
    raw = json.dumps(snapshot)
    assert not any(path in raw for path in ("/Users/", "/home/", "/tmp/", "OPENROUTER_API_KEY="))
    commit = snapshot["catalog_binding"]["repository"]["commit"]
    for row in snapshot["tasks"]:
        for item in row["anchors"]:
            assert f"/blob/{commit}/" in item["source"]["url"]
            assert len(item["source"]["sha256"]) == 64
