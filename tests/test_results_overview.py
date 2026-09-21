"""Publication boundary checks using inert private response fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from arena.registry import RegistryError
from arena.results_overview import build_results_overview, get_results_overview, validate_results_overview


def run(ident="private-run-a", framework="sciel-release", model="gpt-5.6-sol", state="completed", cohort="a" * 64):
    return dict(id=ident, framework=framework, model=model, state=state,
        owner="private-owner", label="sk-do-not-publish", engine="/srv/private/engine", version="private-v42",
        metrics=dict(wall_seconds=20, canonical=dict(evaluations=3, valid=2, invalid=1, unknown=0,
            valid_candidate_hashes=["b" * 64, "c" * 64], seed_score=-2, best_score=0,
            cohort=cohort, task_id="reference-sat", task_name="secret original description", metric="score",
            direction="maximize", status="recorded"), usage=dict(complete=True, total_tokens=120),
            native=dict(prompt="private prompt", source="private source")))


def payload(*runs, total=None):
    return dict(schema="arena.results/1", generated_at=100, total=len(runs) if total is None else total,
                truncated=total is not None and total > len(runs), runs=list(runs), notes=["private notes"])


def project(*runs, total=None):
    return build_results_overview(payload(*runs, total=total), generated_at=101)


def native_run(ident="private-native-run", *, state="completed", framework="native-framework"):
    row = run(ident, framework=framework, state=state)
    row["metrics"]["canonical"].update(evaluations=0, valid=0, invalid=0, unknown=0,
        valid_candidate_hashes=[], seed_score=None, best_score=None, cohort=None, metric=None,
        direction=None, task_id=None, task_name=None, status="missing")
    row["metrics"]["native"] = dict(scope="native", status="recorded", evidence_hashes=["d" * 64],
        task="gsm8k", metric="heldout_accuracy", direction="maximize", seed_score=0, best_score=.875,
        source="private native source", task_name="private task label", prompt="private prompt")
    return row


def paired_run(ident="private-paired-run", *, state="completed"):
    row = native_run(ident, framework="meoh", state=state)
    row["metrics"]["native"].update(task="online-bin-packing", metric="native_two_objective_population",
        best_score=None, seed_score=None, direction=None,
        objectives=[dict(metric="negative_mean_bins", direction="maximize"),
                    dict(metric="negative_mean_evaluation_seconds", direction="maximize")],
        population_objectives=[dict(negative_mean_bins=-16, negative_mean_evaluation_seconds=-.8, candidate="private-candidate-id"),
                               dict(negative_mean_bins=-18, negative_mean_evaluation_seconds=-.1)])
    return row


def research_section():
    return dict(source_generated_at=100, total=1, measured=1, runs=[dict(
        task_id="oe/circle_packing", task_name="Circle packing in a unit square", metric="sum_radii",
        direction="maximize", units="unitless", protocol="e" * 64, models=["gpt-5.6-sol"],
        state="completed", seed_score=2, best_score=2.5, total_wall_seconds=100,
        to_best_wall_seconds=80, wall_scope="elapsed_including_pauses", tokens=None,
        source="native_observer", measurement_status="measured")])


def test_publication_uses_allowlisted_measurements_and_keeps_zero_negative_scores():
    result = project(run())
    serialized = json.dumps(result)
    for secret in ("private-run-a", "private-owner", "sk-do-not-publish", "/srv/private/engine", "private-v42",
                   "secret original description", "private prompt", "private source", "private notes", "b" * 64, "c" * 64):
        assert secret not in serialized
    assert result["summary"] == dict(runs=1, completed=1, active=0, failed=0, cancelled=0, other=0, systems=1, models=1)
    assert result["cohorts"][0]["task_name"] == "Reference sat"
    point = result["cohorts"][0]["points"][0]
    assert point["seed_score"] == -2 and point["best_score"] == 0
    assert result["validity"]["unique_programs"] == 2
    assert result["resources"] == dict(complete_token_runs=1, median_tokens=120, wall_time_runs=1)


def test_cohorts_preserve_evaluator_task_metric_direction_and_every_state():
    rows = []
    for i, state in enumerate(("completed", "failed", "cancelled", "queued", "preparing", "running", "blocked")):
        row = run(str(i), state=state)
        row["metrics"]["usage"]["total_tokens"] = i * 10
        if i % 2:
            row["metrics"]["canonical"]["direction"] = "minimize"
        if i >= 3:
            row["metrics"]["canonical"]["cohort"] = "d" * 64
        if i == 6:
            row["metrics"]["canonical"]["task_id"] = "another-task"
        rows.append(row)
    result = project(*rows, total=20)
    assert result["total"] == 20 and result["loaded"] == 7 and result["truncated"]
    assert result["summary"]["active"] == 3
    assert result["summary"]["failed"] == result["summary"]["cancelled"] == result["summary"]["other"] == 1
    assert len(result["cohorts"]) == 5
    assert result["validity"]["unique_programs"] == 2
    assert result["resources"]["complete_token_runs"] == 3
    assert result["resources"]["median_tokens"] == 10
    points = [p for c in result["cohorts"] for p in c["points"]]
    assert {p["state"] for p in points} == {r["state"] for r in rows}
    assert all(p["total_tokens"] is None for p in points if p["state"] in {"queued", "preparing", "running", "blocked"})


def test_partial_evidence_incomplete_usage_and_missing_scores_stay_explicit():
    first = run()
    first["metrics"]["canonical"].update(status="partial", valid=1, unknown=1, valid_candidate_hashes=["b" * 64])
    first["metrics"]["usage"]["complete"] = False
    second = run("second", framework="native-system")
    second["metrics"]["canonical"].update(evaluations=0, valid=0, invalid=0, unknown=0, valid_candidate_hashes=[],
                                         cohort=None, seed_score=None, best_score=None, task_id=None, metric=None, direction=None)
    second["metrics"]["wall_seconds"] = None
    second["metrics"]["usage"] = dict(complete=False, total_tokens=None)
    result = project(first, second)
    assert result["resources"]["median_tokens"] is None
    assert result["resources"]["wall_time_runs"] == 1
    assert result["cohorts"][0]["points"][0]["evidence_partial"]
    assert result["cohorts"][0]["points"][0]["total_tokens"] is None
    assert next(s for s in result["systems"] if s["system"] == "native-system")["canonical_runs"] == 0
    empty = project()
    assert empty["validity"]["unique_programs"] is None
    assert empty["systems"] == empty["cohorts"] == []


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(schema="unexpected"),
    lambda p: p.update(total=0),
    lambda p: p.update(truncated=True),
    lambda p: p.update(generated_at=float("nan")),
    lambda p: p["runs"].append(deepcopy(p["runs"][0])),
    lambda p: p["runs"][0].update(framework="../../private"),
    lambda p: p["runs"][0].update(model="sk-abcdef"),
    lambda p: p["runs"][0].update(state="unknown"),
    lambda p: p["runs"][0]["metrics"]["canonical"].update(valid=True),
    lambda p: p["runs"][0]["metrics"]["canonical"].update(best_score=float("inf")),
    lambda p: p["runs"][0]["metrics"]["canonical"].update(cohort=None),
    lambda p: p["runs"][0]["metrics"]["canonical"].update(valid_candidate_hashes=["not-a-hash"]),
    lambda p: p["runs"][0]["metrics"].update(wall_seconds=-1),
    lambda p: p["runs"][0]["metrics"]["usage"].update(complete="yes"),
])
def test_invalid_source_fails_closed(mutate):
    source = payload(run())
    mutate(source)
    with pytest.raises(RegistryError):
        build_results_overview(source, generated_at=101)


def test_snapshot_rejects_unreviewed_fields_in_every_layer(tmp_path):
    baseline = project(run())
    for selector in (lambda p: p, lambda p: p["summary"], lambda p: p["resources"], lambda p: p["systems"][0],
                     lambda p: p["cohorts"][0], lambda p: p["cohorts"][0]["points"][0]):
        value = deepcopy(baseline)
        selector(value)["private"] = "secret"
        with pytest.raises(RegistryError):
            validate_results_overview(value)
    target = tmp_path / "results-overview.json"
    target.write_text(json.dumps(baseline))
    assert get_results_overview(tmp_path) == baseline
    target.unlink()
    with pytest.raises(RegistryError):
        get_results_overview(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(baseline))
    target.symlink_to(outside)
    with pytest.raises(RegistryError):
        get_results_overview(tmp_path)


def test_offline_export_is_atomic_and_does_not_echo_private_values(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source, target = tmp_path / "private.json", tmp_path / "published.json"
    source.write_text(json.dumps(payload(run())))
    command = [sys.executable, str(root / "scripts/export_results_overview.py"), "--input", str(source), "--output", str(target)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
    published = target.read_bytes()
    assert json.loads(published)["summary"]["runs"] == 1
    source.write_text('{"secret":"sk-do-not-publish","schema":"wrong"}')
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode != 0 and "sk-do-not-publish" not in failed.stderr + failed.stdout
    assert target.read_bytes() == published


def test_native_scalar_results_are_published_without_rankings_or_private_metadata():
    first = native_run()
    second = native_run("second", framework="other-native-framework", state="failed")
    second["metrics"]["native"].update(status="partial", metric="training_loss", direction="minimize", seed_score=-2, best_score=0)
    second["metrics"]["usage"]["complete"] = False
    result = project(first, second)
    assert result["cohorts"] == []
    assert len(result["native_results"]) == 2
    scalar, partial = result["native_results"]
    assert scalar == dict(system="native-framework", model="gpt-5.6-sol", state="completed", task_id="gsm8k", task_name="Gsm8k",
        metric="heldout_accuracy", direction="maximize", seed_score=0, best_score=.875, wall_seconds=20,
        total_tokens=120, usage_complete=True, evidence_partial=False, objectives=[], population_objectives=[])
    assert partial["state"] == "failed" and partial["evidence_partial"] is True
    assert partial["seed_score"] == -2 and partial["best_score"] == 0
    assert partial["direction"] == "minimize" and partial["metric"] == "training_loss"
    assert partial["total_tokens"] is None and partial["usage_complete"] is False
    serialized = json.dumps(result)
    for forbidden in ("private-native-run", "private native source", "private task label", "private prompt", "evidence_hashes", "d" * 64):
        assert forbidden not in serialized
    assert "rank" not in scalar and "cohort" not in scalar and "profile" not in scalar


def test_native_paired_objectives_preserve_points_without_fabricated_scalar_best():
    result = project(paired_run())
    native = result["native_results"][0]
    assert native["seed_score"] is native["best_score"] is native["direction"] is None
    assert native["objectives"] == [dict(metric="negative_mean_bins", direction="maximize"),
                                    dict(metric="negative_mean_evaluation_seconds", direction="maximize")]
    assert native["population_objectives"] == [dict(negative_mean_bins=-16, negative_mean_evaluation_seconds=-.8),
                                               dict(negative_mean_bins=-18, negative_mean_evaluation_seconds=-.1)]
    assert "private-candidate-id" not in json.dumps(result)
    assert native["population_objectives"][0] != dict(negative_mean_bins=-16, negative_mean_evaluation_seconds=-.1)


def test_missing_unverified_and_failed_integrity_projections_do_not_become_results():
    rows = [native_run(str(i)) for i in range(4)]
    for row, status in zip(rows, (None, "unsupported", "missing", "partial")):
        row["metrics"]["native"].update(status=status)
    rows[3]["metrics"]["native"].update(best_score=None, seed_score=None)
    result = project(*rows)
    assert result["native_results"] == []
    assert result["summary"]["runs"] == 4


def test_native_and_canonical_results_keep_independent_scopes():
    canonical = run()
    native = native_run()
    result = project(canonical, native)
    assert len(result["cohorts"]) == len(result["native_results"]) == 1
    assert result["cohorts"][0]["points"][0]["system"] == "sciel-release"
    assert result["native_results"][0]["system"] == "native-framework"
    assert result["validity"]["valid"] == 2


@pytest.mark.parametrize("mutate", [
    lambda native: native.update(evidence_hashes=[]),
    lambda native: native.update(evidence_hashes=["invalid"]),
    lambda native: native.update(evidence_hashes=["d" * 64, "d" * 64]),
    lambda native: native.update(scope="canonical"),
    lambda native: native.update(task="../../private/path"),
    lambda native: native.update(metric="sk-private"),
    lambda native: native.update(direction="unknown"),
    lambda native: native.update(best_score=float("nan")),
    lambda native: native.update(best_score=True),
])
def test_invalid_measured_native_projection_fails_closed(mutate):
    row = native_run()
    mutate(row["metrics"]["native"])
    with pytest.raises(RegistryError):
        project(row)


@pytest.mark.parametrize("mutate", [
    lambda native: native.update(best_score=0),
    lambda native: native.update(seed_score=0),
    lambda native: native.update(direction="maximize"),
    lambda native: native["objectives"].pop(),
    lambda native: native["objectives"][1].update(metric="negative_mean_bins"),
    lambda native: native["population_objectives"][0].pop("negative_mean_bins"),
    lambda native: native["population_objectives"][0].update(negative_mean_bins=float("inf")),
])
def test_invalid_or_unpaired_native_objectives_fail_closed(mutate):
    row = paired_run()
    mutate(row["metrics"]["native"])
    with pytest.raises(RegistryError):
        project(row)


def test_published_native_rows_reject_extra_fields_and_unrelated_models():
    baseline = project(paired_run())
    for select in (lambda value: value["native_results"][0],
                   lambda value: value["native_results"][0]["objectives"][0],
                   lambda value: value["native_results"][0]["population_objectives"][0]):
        value = deepcopy(baseline)
        select(value)["private"] = "unreviewed"
        with pytest.raises(RegistryError):
            validate_results_overview(value)
    value = deepcopy(baseline)
    value["native_results"][0]["model"] = "unrelated-model"
    with pytest.raises(RegistryError):
        validate_results_overview(value)
    value = deepcopy(baseline)
    value["native_results"].append(deepcopy(value["native_results"][0]))
    with pytest.raises(RegistryError):
        validate_results_overview(value)


def test_research_observations_are_separate_from_control_and_canonical_counts():
    source = research_section()
    result = build_results_overview(payload(run()), generated_at=101, research=source)
    assert result["research"] == source
    assert result["research"]["total"] == result["research"]["measured"] == 1
    assert result["summary"]["runs"] == result["total"] == result["loaded"] == 1
    assert len(result["cohorts"]) == 1 and result["native_results"] == []
    assert result["validity"]["evaluations"] == 3
    assert result["resources"]["median_tokens"] == 120
    result["research"]["runs"][0]["best_score"] = 3
    assert source["runs"][0]["best_score"] == 2.5, "publisher must not alias mutable research input"
    assert project(run())["research"] is None


def test_research_publication_rejects_raw_private_fields_and_future_measurements():
    for selector in (lambda value: value, lambda value: value["runs"][0]):
        research = research_section()
        selector(research)["private_source"] = "sk-do-not-publish"
        with pytest.raises(RegistryError):
            build_results_overview(payload(run()), generated_at=101, research=research)
    research = research_section()
    research["source_generated_at"] = 102
    with pytest.raises(RegistryError):
        build_results_overview(payload(run()), generated_at=101, research=research)
    with pytest.raises(RegistryError):
        build_results_overview(payload(run()), generated_at=101, research={"schema": "arena.research-observer-input/1"})


def test_export_accepts_safe_research_section_and_rejects_raw_or_linked_input(tmp_path):
    root = Path(__file__).resolve().parents[1]
    control, research, target = tmp_path / "private.json", tmp_path / "research.json", tmp_path / "published.json"
    control.write_text(json.dumps(payload(run())))
    research.write_text(json.dumps(research_section()))
    command = [sys.executable, str(root / "scripts/export_results_overview.py"), "--input", str(control),
               "--research-input", str(research), "--output", str(target)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
    published = target.read_bytes()
    assert json.loads(published)["research"] == research_section()
    research.write_text('{"schema":"arena.research-observer-input/1","source":"sk-do-not-publish"}')
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode != 0 and "sk-do-not-publish" not in failed.stdout + failed.stderr
    assert target.read_bytes() == published
    research.unlink()
    research.symlink_to(control)
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode != 0 and target.read_bytes() == published
