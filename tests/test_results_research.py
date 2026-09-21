"""Pure native-research publication checks; no observer or provider calls."""
from copy import deepcopy
import hashlib
import json

import pytest

from arena.registry import RegistryError
from arena.results_research import (
    INPUT_SCHEMA, WALL_SCOPE, build_results_research, validate_results_research,
)


def metric(task_hash="a" * 64):
    value = dict(schema="sciel-research-measurement/1", task_name="oe/circle_packing",
        task_hash=task_hash, primary_metric="combined_score", score_source="EvalResult.score",
        goal="maximize", semantics=dict(kind="validity_gated_ratio", score_units="dimensionless",
            numerator_case="sum_radii", numerator_units="unit_square_side_length", denominator=2.635,
            validity_case="validity", valid_value=1.0, invalid_score=0.0, invalid_numerator_value=0.0,
            invalid_numerator_semantics="penalty_sentinel_not_physical_measurement"))
    value["sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return value


def display(value, context, *, status="measured"):
    return dict(schema="sciel-metric-display/1", status=status, value=value,
                label="sum_radii", units="unit_square_side_length", metric_sha256=context["sha256"])


def run(ident="private-observer-id", *, task_hash="a" * 64, state="paused"):
    context = metric(task_hash)
    return dict(id=ident, task_id=context["task_name"], state=state, metric=context,
                seed=display(.9, context), best=display(2.6, context),
                effort=dict(models=["gpt-6-astra", "anthropic/claude-opus-5"],
                    total_wall_seconds=2000, total_wall_scope=WALL_SCOPE,
                    to_best_wall_seconds=250, to_best_wall_scope=WALL_SCOPE))


def payload(*runs):
    return dict(schema=INPUT_SCHEMA, source_generated_at=100, total=len(runs), runs=list(runs))


def test_projects_native_measurements_without_publishing_source_identity_or_cost_claims():
    source = run()
    result = build_results_research(payload(source))
    assert result["total"] == result["measured"] == 1
    row = result["runs"][0]
    assert row["task_name"] == "Circle packing in a unit square"
    assert row["seed_score"] == .9 and row["best_score"] == 2.6
    assert row["metric"] == "sum_radii" and row["units"] == "unit_square_side_length"
    assert row["models"] == ["anthropic/claude-opus-5", "gpt-6-astra"]
    assert row["state"] == "paused" and row["source"] == "native_observer"
    assert row["wall_scope"] == "elapsed_including_pauses"
    assert row["total_wall_seconds"] == 2000 and row["to_best_wall_seconds"] == 250
    assert row["tokens"] is None
    public = json.dumps(result)
    for private in (source["id"], source["metric"]["task_hash"], source["metric"]["sha256"],
                    "cost", "validity_case", "canonical", "verified", "configured_models"):
        assert private not in public
    assert validate_results_research(result) is result


def test_preserves_zero_and_negative_measurements_and_stopped_run_state():
    source = run(state="stopped")
    source["seed"]["value"] = -2
    source["best"]["value"] = 0
    result = build_results_research(payload(source))
    assert result["runs"][0]["seed_score"] == -2
    assert result["runs"][0]["best_score"] == 0
    assert result["runs"][0]["state"] == "stopped"
    assert result["measured"] == 1


def test_native_current_best_is_preserved_even_after_a_seed_regression():
    source = run()
    source["seed"]["value"] = 3
    row = build_results_research(payload(source))["runs"][0]
    assert row["seed_score"] == 3 and row["best_score"] == 2.6


@pytest.mark.parametrize("status", ["unknown", "failed", "invalid_penalty"])
def test_unknown_failed_and_penalty_results_never_become_zero_scores(status):
    source = run()
    source["best"].update(status=status, value=None)
    source["seed"].update(status="unknown", value=None)
    row = build_results_research(payload(source))["runs"][0]
    assert row["best_score"] is None and row["seed_score"] is None
    assert row["to_best_wall_seconds"] is None
    assert row["measurement_status"] == status


def test_missing_actual_models_and_unknown_time_scope_are_not_inferred():
    source = run()
    source["effort"].update(models=[], total_wall_scope="session time", to_best_wall_scope=None)
    row = build_results_research(payload(source))["runs"][0]
    assert row["models"] == []
    assert row["total_wall_seconds"] is None and row["to_best_wall_seconds"] is None
    assert row["tokens"] is None


def test_task_bound_protocols_stay_separate_and_projection_is_deterministic():
    first, second = run("private-first"), run("private-second", task_hash="b" * 64)
    result = build_results_research(payload(first, second))
    assert len({row["protocol"] for row in result["runs"]}) == 2
    assert result == build_results_research(payload(second, first))
    assert result["total"] == 2


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(prompt="do not publish"),
    lambda r: r["effort"].update(cost_total=0),
    lambda r: r["seed"].update(raw_score=1),
    lambda r: r["metric"].update(sha256="b" * 64),
    lambda r: r["best"].update(metric_sha256="b" * 64),
    lambda r: r["best"].update(label="combined_score"),
    lambda r: r["best"].update(units="dollars"),
    lambda r: r["best"].update(value=0, status="invalid_penalty"),
    lambda r: r["best"].update(value=None, status="measured"),
    lambda r: r["best"].update(value=float("nan")),
    lambda r: r["best"].update(value=True),
    lambda r: r["best"].update(status={}),
    lambda r: r.update(state=[]),
    lambda r: r["effort"].update(models=["sk-private-key"]),
    lambda r: r["effort"].update(models=["/Users/private/model"]),
    lambda r: r["effort"].update(models=["https://private.example/model"]),
    lambda r: r["effort"].update(models=["gpt-6-astra", "gpt-6-astra"]),
    lambda r: r["effort"].update(total_wall_seconds=-1),
    lambda r: r["effort"].update(to_best_wall_seconds=3000),
])
def test_rejects_unreviewed_fields_mismatched_metric_and_invalid_measurements(mutation):
    source = run()
    mutation(source)
    with pytest.raises(RegistryError):
        build_results_research(payload(source))


def test_rejects_duplicate_id_incomplete_collection_and_oversized_input():
    with pytest.raises(RegistryError):
        build_results_research(payload(run(), run()))
    source = payload(run())
    source["total"] = 2
    with pytest.raises(RegistryError):
        build_results_research(source)
    source = payload()
    source["total"] = 501
    with pytest.raises(RegistryError):
        build_results_research(source)


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(code="private program"),
    lambda r: r.update(task_name="private run label"),
    lambda r: r.update(source="canonical_evaluation"),
    lambda r: r.update(tokens=0),
    lambda r: r.update(wall_scope="cpu_time"),
    lambda r: r.update(protocol="not-a-digest"),
    lambda r: r.update(measurement_status="verified"),
    lambda r: r.update(best_score=None),
    lambda r: r.update(models=["gpt-6-astra", "anthropic/claude-opus-5"]),
])
def test_published_validator_rejects_private_extensions_and_unsupported_claims(mutation):
    result = build_results_research(payload(run()))
    mutation(result["runs"][0])
    with pytest.raises(RegistryError):
        validate_results_research(result)


def test_published_validator_rejects_protocol_collision_and_count_drift():
    result = build_results_research(payload(run("one"), run("two", task_hash="b" * 64)))
    result["measured"] = 1
    with pytest.raises(RegistryError):
        validate_results_research(result)
    result["measured"] = 2
    result["runs"][1].update(protocol=result["runs"][0]["protocol"], metric="another_metric")
    with pytest.raises(RegistryError):
        validate_results_research(result)


def test_empty_collection_is_explicit_and_inputs_are_not_modified():
    assert build_results_research(payload()) == dict(source_generated_at=100, total=0, measured=0, runs=[])
    source = payload(run())
    before = deepcopy(source)
    build_results_research(source)
    assert source == before


def physical_usage(*, complete=True):
    return dict(scope="total_physical_receipts", billing_mode="subscription_unpriced",
                prompt_tokens=1200, completion_tokens=300, token_usage_complete=complete,
                physical_llm_calls=4, unpriced_llm_calls=4)


def test_complete_subscription_tokens_are_total_usage_never_cost_to_best():
    source = run()
    source["effort"]["usage"] = physical_usage()
    original = deepcopy(source)
    result = build_results_research(payload(source))
    row = result["runs"][0]
    assert row["tokens"] == 1500
    assert row["usage"] == physical_usage()
    assert row["to_best_wall_seconds"] == 250
    assert "cost" not in json.dumps(row) and "to_best_tokens" not in row
    assert validate_results_research(result) is result
    assert source == original


def test_partial_physical_receipts_preserve_observed_subtotals_without_total_tokens():
    source = run()
    source["effort"]["usage"] = physical_usage(complete=False)
    row = build_results_research(payload(source))["runs"][0]
    assert row["tokens"] is None
    assert row["usage"]["prompt_tokens"] == 1200
    assert row["usage"]["token_usage_complete"] is False


@pytest.mark.parametrize("mutation", [
    lambda u: u.update(scope="to_best"),
    lambda u: u.update(billing_mode="free"),
    lambda u: u.update(billing_mode=None),
    lambda u: u.update(prompt_tokens=True),
    lambda u: u.update(completion_tokens=-1),
    lambda u: u.update(prompt_tokens=None),
    lambda u: u.update(physical_llm_calls=None),
    lambda u: u.update(unpriced_llm_calls=5),
    lambda u: u.update(token_usage_complete=1),
    lambda u: u.update(receipt_id="private-evidence"),
    lambda u: u.update(cost_total=0),
])
def test_physical_usage_rejects_private_fields_invalid_coverage_and_price_claims(mutation):
    source = run()
    source["effort"]["usage"] = physical_usage()
    mutation(source["effort"]["usage"])
    with pytest.raises(RegistryError):
        build_results_research(payload(source))


def test_published_tokens_must_match_complete_receipt_usage():
    source = run()
    source["effort"]["usage"] = physical_usage()
    result = build_results_research(payload(source))
    result["runs"][0]["tokens"] = 1499
    with pytest.raises(RegistryError):
        validate_results_research(result)


def with_best_receipts(source=None):
    source = source or run()
    evidence = dict(program_id="private-program", evaluation_id="private-evaluation",
                    source_sha256="c" * 64, metric_display=deepcopy(source["best"]))
    source["effort"]["best_evaluation"] = evidence
    source["effort"]["to_best"] = dict(status="complete", history_complete=True,
        physical_llm_calls=4, dispatched_llm_calls=4, pending_llm_calls=0,
        wall_seconds=250, wall_scope=WALL_SCOPE, cutoff_kind="evaluation_completed",
        cutoff_at="2026-09-20T19:53:07.574686+00:00",
        **{key: evidence[key] for key in ("program_id", "evaluation_id", "source_sha256")})
    return source


def test_publishes_only_receipt_bound_counts_through_the_same_best_evaluation():
    source = with_best_receipts()
    source["effort"]["usage"] = physical_usage()
    source["effort"]["usage"].update(physical_llm_calls=19, unpriced_llm_calls=19)
    before = deepcopy(source)
    result = build_results_research(payload(source))
    row = result["runs"][0]
    assert row["effort_to_best"] == dict(scope="current_run_through_best_evaluation",
        physical_llm_calls=4, dispatched_llm_calls=4, pending_llm_calls=0,
        history_complete=True, elapsed_seconds=250)
    assert row["usage"]["physical_llm_calls"] == 19
    assert row["tokens"] == 1500  # Full-run tokens never become tokens to best.
    encoded = json.dumps(result)
    for private in ("private-program", "private-evaluation", "c" * 64, "cutoff_at"):
        assert private not in encoded
    assert source == before


@pytest.mark.parametrize("mutation", [
    lambda r: r["effort"]["to_best"].update(program_id="different-program"),
    lambda r: r["effort"]["to_best"].update(evaluation_id="different-evaluation"),
    lambda r: r["effort"]["to_best"].update(source_sha256="d" * 64),
    lambda r: r["effort"]["best_evaluation"].update(source_sha256="not-a-hash"),
    lambda r: r["effort"]["best_evaluation"]["metric_display"].update(value=2.61),
    lambda r: r["effort"]["best_evaluation"]["metric_display"].update(metric_sha256="d" * 64),
    lambda r: r["effort"].pop("best_evaluation"),
    lambda r: r["effort"].pop("to_best"),
    lambda r: r["effort"]["to_best"].update(wall_seconds=251),
    lambda r: r["effort"]["to_best"].update(wall_scope="CPU seconds"),
    lambda r: r["effort"]["to_best"].update(cutoff_kind="program_created"),
    lambda r: r["effort"]["to_best"].update(cutoff_at="2026-09-20T19:53:07"),
    lambda r: r["effort"]["to_best"].update(cutoff_at="not-time"),
    lambda r: r["effort"]["to_best"].update(status="unverified"),
    lambda r: r["effort"]["to_best"].update(history_complete=False),
    lambda r: r["effort"]["to_best"].update(pending_llm_calls=1, dispatched_llm_calls=5),
    lambda r: r["effort"]["to_best"].update(physical_llm_calls=True),
    lambda r: r["effort"]["to_best"].update(dispatched_llm_calls=3),
    lambda r: r["effort"]["to_best"].update(pending_llm_calls=-1),
    lambda r: r["effort"]["to_best"].update(prompt="private"),
])
def test_rejects_unbound_or_inconsistent_best_receipt_evidence(mutation):
    source = with_best_receipts()
    mutation(source)
    with pytest.raises(RegistryError):
        build_results_research(payload(source))


def test_partial_receipts_keep_explicit_pending_and_history_coverage():
    source = with_best_receipts()
    source["effort"]["to_best"].update(status="partial", history_complete=False,
                                     pending_llm_calls=1, dispatched_llm_calls=5)
    row = build_results_research(payload(source))["runs"][0]
    assert row["effort_to_best"]["history_complete"] is False
    assert row["effort_to_best"]["pending_llm_calls"] == 1
    assert row["effort_to_best"]["physical_llm_calls"] == 4


@pytest.mark.parametrize("mutation", [
    lambda r: r["effort_to_best"].update(scope="all_prior_research"),
    lambda r: r["effort_to_best"].update(elapsed_seconds=251),
    lambda r: r["effort_to_best"].update(history_complete=1),
    lambda r: r["effort_to_best"].update(dispatched_llm_calls=3),
    lambda r: r["effort_to_best"].update(program_id="private"),
    lambda r: r["effort_to_best"].update(tokens=1234),
    lambda r: r.update(usage=physical_usage() | {"physical_llm_calls": 3, "unpriced_llm_calls": 3}, tokens=1500),
])
def test_public_effort_to_best_validator_rejects_unscoped_private_or_inconsistent_claims(mutation):
    result = build_results_research(payload(with_best_receipts()))
    mutation(result["runs"][0])
    with pytest.raises(RegistryError):
        validate_results_research(result)


def test_no_effort_to_best_without_a_measured_best():
    source = with_best_receipts()
    source["best"].update(status="unknown", value=None)
    source["effort"]["best_evaluation"]["metric_display"] = deepcopy(source["best"])
    with pytest.raises(RegistryError):
        build_results_research(payload(source))


def self_improvement():
    return dict(schema="sciel-self-improvement/1", scope="recorded_run", coverage="complete",
        cells_created=3, cell_revisions=5, tools_registered=2, tools_executed=1,
        tool_executions=8, shared_observation_deliveries=12)


def test_native_self_improvement_counters_remain_separate_from_search_effort():
    source = with_best_receipts()
    source["self_improvement"] = self_improvement()
    before = deepcopy(source)
    row = build_results_research(payload(source))["runs"][0]
    assert row["self_improvement"] == self_improvement()
    assert row["effort_to_best"]["physical_llm_calls"] == 4
    assert source == before


@pytest.mark.parametrize("field,value", [
    ("scope", "lifetime_research"), ("coverage", "verified"), ("cells_created", -1),
    ("tool_executions", True), ("program_id", "private-program"),
])
def test_research_projection_and_public_validator_reject_invalid_rsi_evidence(field, value):
    source = run()
    source["self_improvement"] = self_improvement()
    public = build_results_research(payload(source))
    source["self_improvement"][field] = value
    public["runs"][0]["self_improvement"][field] = value
    with pytest.raises(RegistryError):
        build_results_research(payload(source))
    with pytest.raises(RegistryError):
        validate_results_research(public)
