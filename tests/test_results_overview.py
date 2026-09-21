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
