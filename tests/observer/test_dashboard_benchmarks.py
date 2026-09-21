from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from arena.observers.sciel.benchmarks import benchmark_for
from arena.observers.sciel.compat.repeat_support import CANONICAL_TASK_HASH
from arena.observers.sciel.compat.measurement import metric_context


METRIC = metric_context(SimpleNamespace(
    qualified_name="oe/circle_packing", task_hash=CANONICAL_TASK_HASH,
    primary_metric="combined_score",
    research_metric={"kind": "validity_gated_ratio", "numerator_case": "sum_radii",
                  "denominator": 2.635, "validity_case": "validity",
                  "valid_value": 1.0, "invalid_score": 0.0,
                  "score_units": "dimensionless", "numerator_units": "unit_square_side_length",
                  "invalid_numerator_value": 0.0,
                  "invalid_numerator_semantics": "penalty_sentinel_not_physical_measurement"}))


def observed(score, numerator):
    return benchmark_for('oe/circle_packing', METRIC, score, metric_display=dict(
        schema='sciel-metric-display/1', status='measured', value=numerator,
        raw_score=score, metric_sha256=METRIC['sha256']))


def test_reference_uses_recorded_score_units_and_keeps_target_separate():
    result = observed(.9929002955631129, 2.6162922788088023)
    assert result["current_value"] == pytest.approx(2.6162922788088023)
    assert result["value"] > result["task_target"]
    assert result["score"] == pytest.approx(result["value"] / 2.635)
    assert result["gap"] == pytest.approx(result["value"] - result["current_value"])
    assert result["reference_tolerance"] == 1e-6
    assert result["run_tolerance"] == 1e-6
    assert result["source_url"].startswith("https://")


@pytest.mark.parametrize("field,value", [
    ("task_hash", "unregistered"), ("goal", "minimize"),
    ("primary_metric", "sum_radii"), ("task_name", "different"),
])
def test_different_measurement_does_not_receive_circle_reference(field, value):
    metric = deepcopy(METRIC)
    metric[field] = value
    assert benchmark_for("oe/circle_packing", metric, .9) is None


def test_unknown_or_renormalized_task_does_not_get_an_invented_reference():
    assert benchmark_for("oe/heilbronn_triangle", METRIC, .9) is None
    assert benchmark_for("oe/circle_packing", None, .9) is None
    metric = deepcopy(METRIC)
    metric["semantics"]["denominator"] = 3.0
    assert benchmark_for("oe/circle_packing", metric, .9) is None


@pytest.mark.parametrize('field,value', [
    ('numerator_units', 'millimetres'), ('valid_value', 2.), ('invalid_numerator_value', -1.),
])
def test_valid_but_different_metric_contract_has_no_reference(field, value):
    semantics = {**METRIC['semantics'], field: value}
    metric = metric_context(SimpleNamespace(qualified_name='oe/circle_packing',
        task_hash=CANONICAL_TASK_HASH, primary_metric='combined_score', research_metric=semantics))
    assert benchmark_for('oe/circle_packing', metric, .9) is None


@pytest.mark.parametrize("score", [None, float("nan"), float("inf"), True, -.1, 10**1000, 1e308])
def test_unknown_current_score_is_not_zero(score):
    result = benchmark_for("oe/circle_packing", METRIC, score)
    assert result["current_value"] is result["gap"] is result["percent_of_reference"] is None
    assert all(row["gap_percent"] is None for row in result["references"])
    json.dumps(result, allow_nan=False)


def test_main_reference_matches_native_tolerance_and_preserves_published_digits():
    result = benchmark_for("oe/circle_packing", METRIC, 1.)
    assert result["value_label"] == "2.63599872089287514"
    assert result["reference"] == result["references"][0]
    assert result["reference"]["tolerance"] == result["run_tolerance"]
    strict = next(row for row in result["references"]
                  if row["name"].startswith("Göther") and row["tolerance"] == 0)
    assert strict["value_label"].startswith("2.635983084917607783186569485")
    assert strict["value"] < result["value"]
    assert result["audit_corpus_date"] == "2026-08-08"
    assert "not an exhaustive" in result["note"]


def test_shinka_paper_values_are_distinct_from_audited_artifact():
    rows = benchmark_for("oe/circle_packing", METRIC, 1.)["references"]
    shinka = {row["value_label"]: row for row in rows if row["name"].startswith("ShinkaEvolve")}
    assert set(shinka) == {"2.635983099011548", "2.6359828390115476", "2.63598282664580639"}
    assert shinka["2.635983099011548"]["status"] == "reported"
    assert shinka["2.635983099011548"]["tolerance"] == 1e-6
    assert shinka["2.6359828390115476"]["tolerance"] == 0
    assert shinka["2.63598282664580639"]["status"] == "audited"
    assert "openreview.net" in shinka["2.635983099011548"]["source_url"]
    assert "gotherlabs.com" in shinka["2.63598282664580639"]["source_url"]
    alpha = next(row for row in rows if row["name"] == "AlphaEvolve v2")
    assert alpha["value_label"] == "2.6359830849176068"
    assert alpha["tolerance"] == 1e-10
    assert alpha["method_classification"] == "ai_search_framework"
    assert "deepmind.google" in alpha["classification_source_url"]


def test_every_reference_has_attributable_contract_and_only_comparable_gaps():
    result = observed(1., 2.635)
    assert len(result["references"]) == 14
    for row in result["references"]:
        assert row["value"] == float(row["value_label"])
        assert row["tolerance"] in (0., 1e-10, 1e-6)
        assert row["status"] in {"reported", "audited"}
        assert row["source_name"] and row["source_url"].startswith("https://")
        assert row["comparison_contract"] == result["comparison_contract"]
        if row["tolerance"] == result["run_tolerance"]:
            assert row["comparison_status"] == "same_contract"
            assert row["gap_percent"] == pytest.approx((row["value"] - 2.635) / row["value"] * 100)
        else:
            assert row["comparison_status"] == "different_tolerance"
            assert row["gap_percent"] is None
    # A run numerically above a reference has a negative gap, not an automatic record claim.
    above = observed(1.01, 2.66135)
    assert all(row["gap_percent"] < 0 for row in above["references"]
               if row["comparison_status"] == "same_contract")


def test_reference_results_are_detached_between_snapshots():
    result = benchmark_for("oe/circle_packing", METRIC, 1.)
    result["references"][0]["value_label"] = "changed"
    assert result["reference"]["value_label"] == "2.63599872089287514"
    assert benchmark_for("oe/circle_packing", METRIC, 1.)["references"][0]["value_label"] == "2.63599872089287514"


def test_effort_preserves_published_units_and_unknown_record_costs():
    result = observed(1., 2.635)
    rows = {row['id']: row for row in result['references']}
    assert all(row['effort']['usd'] is None for row in rows.values())
    assert rows['gother-relaxed']['effort']['model_count'] is None
    theta = rows['theta-8b-rl-relaxed']['effort']
    assert theta['steps']['value'] == 65
    assert theta['steps']['unit'] == 'RL training steps'
    assert theta['generated_programs']['value'] == 65 * 32 * 16
    assert theta['llm_calls'] is None  # sampled responses are not physical API calls
    assert result['best_ai_method']['effort'] == theta
    shinka = rows['shinka-reported-relaxed']['effort']
    assert shinka['model_count'] == len(shinka['models']) == 6
    assert shinka['auxiliary_models'][0]['role'] == 'code embedding'
    shinka['models'].clear()
    fresh = observed(1., 2.635)
    assert len(next(row for row in fresh['references'] if row['id'] == 'shinka-reported-relaxed')['effort']['models']) == 6


def test_reference_without_observation_never_converts_raw_score_to_native_value():
    for score in (0., .9, 1.):
        result = benchmark_for('oe/circle_packing', METRIC, score)
        assert result['references']
        assert result['current_value'] is result['gap'] is result['percent_of_reference'] is None
    assert observed(.9, 2.4000000000000004)['current_value'] == 2.4000000000000004


@pytest.mark.parametrize('status', ['invalid_penalty', 'failed', 'unknown'])
def test_unmeasured_display_never_gets_a_benchmark_gap(status):
    result = benchmark_for('oe/circle_packing', METRIC, 0., metric_display=dict(
        schema='sciel-metric-display/1', status=status, value=None,
        raw_score=0., metric_sha256=METRIC['sha256']))
    assert result['current_value'] is result['gap'] is None
    assert all(result[key]['gap_percent'] is None for key in ('best_known', 'best_ai_method'))


def test_best_known_and_ai_search_have_separate_source_backed_scopes():
    result = observed(1., 2.635)
    known, ai = result['best_known'], result['best_ai_method']
    assert known['status'] == ai['status'] == 'known'
    assert known['reference_id'] == 'gother-relaxed'
    assert known['method_classification'] == 'ai_assisted'
    assert known['evidence_status'] == 'audited'
    assert ai['reference_id'] == 'theta-8b-rl-relaxed'
    assert ai['value_label'] == '2.63598566124089912'
    assert ai['method_classification'] == ai['ai_scope'] == 'ai_search_framework'
    assert ai['evidence_status'] == 'audited'
    assert known['value'] > ai['value']
    for reference in (known, ai):
        assert reference['tolerance'] == result['run_tolerance']
        assert reference['classification_source_url'].startswith('https://')
        assert reference['classification_basis']
        assert reference['scope'] == 'selected_published_references'
        assert reference['gap_percent'] == pytest.approx(
            (reference['value'] - 2.635) / reference['value'] * 100)


def test_unknown_method_is_not_inferred_from_a_name_or_high_score(monkeypatch):
    from arena.observers.sciel import benchmarks
    monkeypatch.delitem(benchmarks._METHODS, 'theta-8b-rl')
    result = observed(1., 2.635)
    theta = next(row for row in result['references'] if row['id'] == 'theta-8b-rl-relaxed')
    assert theta['value'] > result['best_ai_method']['value']
    assert theta['method_classification'] == 'unknown'
    assert theta['classification_source_url'] is None


def test_ai_subset_without_documented_same_contract_reference_is_unavailable():
    from arena.observers.sciel.benchmarks import _best_comparison
    references = observed(1., 2.635)['references']
    # Strict documented AI methods and a stronger AI-assisted result cannot
    # stand in for an absent documented AI search result at the run tolerance.
    references = [row for row in references if not (
        row['method_classification'] == 'ai_search_framework'
        and row['comparison_status'] == 'same_contract')]
    result = _best_comparison(references, 2.635, ai_only=True)
    assert result['status'] == 'unavailable'
    assert result['reference_id'] is result['value'] is result['gap_percent'] is None
    assert result['reason']


def test_dual_comparisons_never_borrow_an_unbound_native_measurement():
    result = benchmark_for('oe/circle_packing', METRIC, 1., metric_display=dict(
        schema='sciel-metric-display/1', status='measured', value=2.635,
        raw_score=.99, metric_sha256=METRIC['sha256']))
    for key in ('best_known', 'best_ai_method'):
        assert result[key]['current_value'] is result[key]['gap_percent'] is None
    valid = observed(0., 0.)
    assert valid['current_value'] == 0.
    assert valid['best_known']['gap_percent'] == valid['best_ai_method']['gap_percent'] == 100.


def test_theta_hosted_alphaevolve_artifact_is_not_a_separate_theta_method():
    rows = observed(1., 2.635)['references']
    hosted = next(row for row in rows if row['id'] == 'theta-alphaevolve-strict')
    assert hosted['name'] == 'AlphaEvolve — Theta-hosted artifact'
    assert hosted['value_label'] == '2.63586275641369812'
    assert hosted['method_classification'] == 'ai_search_framework'
    assert '/7c12898f5d7627af403e3aca643af76199fb5c20/' in hosted['classification_source_url']
    assert hosted['comparison_status'] == 'different_tolerance'
    hyra = next(row for row in rows if row['id'] == 'hyra-relaxed')
    assert hyra['method_classification'] == 'unknown'


def test_dual_comparisons_are_detached_from_rows_and_subsequent_snapshots():
    result = observed(1., 2.635)
    result['best_known']['value_label'] = 'changed'
    result['best_ai_method']['classification_basis'] = 'changed'
    assert result['references'][0]['value_label'] == '2.63599872089287514'
    fresh = observed(1., 2.635)
    assert fresh['best_known']['value_label'] == '2.63599872089287514'
    assert fresh['best_ai_method']['classification_basis'] != 'changed'
