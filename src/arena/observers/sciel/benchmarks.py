"""Selected dated references, with separate tolerance and evidence contracts.

Verified against the linked primary audit and paper on 2026-09-19. Values are
stored as decimal strings for display; floats are only for chart arithmetic.
The board neither fetches sources nor certifies records while serving a run.
"""
from __future__ import annotations

import math
from copy import deepcopy
from decimal import Decimal

from .compat.repeat_support import KNOWN_CIRCLE_TASK_HASHES
from .compat.measurement import validate_metric_context

_AUDIT_URL = "https://www.gotherlabs.com/results/circle-packing-26-unit-square/"
_SHINKA_URL = "https://openreview.net/pdf?id=lKEdGCoDNC"
_SHINKA_METHOD_URL = "https://sakana.ai/shinka-evolve/"
_GOTHER_METHOD_URL = "https://github.com/juan-fernandez-gotherlabs/circle-packing-tolerance-audit"
_THETA_METHOD_URL = "https://arxiv.org/html/2511.23473v1"
_THETA_ARTIFACT_URL = "https://raw.githubusercontent.com/ypwang61/ThetaEvolve/7c12898f5d7627af403e3aca643af76199fb5c20/README.md"
_STRICT_GOTHER = ("2.6359830849176077831865694854434817303966767982744748577457711298607038493344723396767997365079")
_RUN_TOLERANCE = 1e-6
_COMPARISON_CONTRACT = "circle-packing-26-unit-square/sum-of-radii/maximize"

# These are published campaign settings, not a replay of the discovery trace.
# A training step, a generation and an evaluator call are different units.
_PUBLISHED_EFFORT = {
    "shinka": dict(
        steps=dict(value=150, unit="evolutionary generations", scope="reported campaign budget"),
        models=[dict(name=name, role="generator") for name in (
            "claude-sonnet-4", "o4-mini", "gpt-4.1-nano", "gpt-4.1", "gpt-4.1-mini")]
            + [dict(name="gpt-5-nano", role="meta / novelty")],
        model_count=6,
        auxiliary_models=[dict(name="text-embedding-3-small", role="code embedding")],
        source_url="https://arxiv.org/html/2509.19349v1#S4.SS1",
        locator="§4.1 and Appendix B.1, Table 1",
        note="150 generations is the reported campaign budget, not 150 total LLM calls. "
             "The six LLMs are the configured pool; per-model usage and dollar spend are not recorded here. "
             "Postprocessing and the later artifact audit have no separately bound cost trace."),
    "theta-8b-rl": dict(
        steps=dict(value=65, unit="RL training steps", scope="reported budget per seed; 3 seeds"),
        generated_programs=dict(value=33280, unit="sampled responses per seed", status="derived",
            derivation="65 steps × 32 parent prompts × 16 responses; not successful evaluations"),
        models=[dict(name="DeepSeek-R1-0528-Qwen3-8B", role="generator / test-time RL")],
        model_count=1, auxiliary_models=[],
        source_url="https://arxiv.org/html/2511.23473v1#S4.SS1",
        locator="Table 2 and §4.1 Pipeline / Multi-Seed",
        note="Training budget, not the first step attaining this exact audited witness. "
             "The paper reports three seeds; 33,280 sampled responses per seed is derived from the batch settings. "
             "Dollar spend and time to this record are unknown here."),
}


def _published_effort(method_id):
    result = dict(schema="arena-reference-effort/1", status="unknown", steps=None,
        generated_programs=None, usd=None, llm_calls=None, wall_seconds=None,
        cpu_seconds=None, models=[], model_count=None, auxiliary_models=[],
        source_url=None, locator=None,
        note="No discovery-effort trace is bound to this reference. Unknown does not mean zero.")
    if method_id in _PUBLISHED_EFFORT:
        result.update(deepcopy(_PUBLISHED_EFFORT[method_id]), status="reported")
    return result

# Classification is about the documented method, not its name or leaderboard
# position. An AI-assisted audit is not evidence of an autonomous AI search.
_METHODS = {
    "gother": dict(classification="ai_assisted", source_url=_GOTHER_METHOD_URL,
        basis="The audit documents internally coordinated agents with human responsibility; it does not establish an autonomous search framework."),
    "shinka": dict(classification="ai_search_framework", source_url=_SHINKA_METHOD_URL,
        basis="Sakana describes ShinkaEvolve as an LLM-driven evolutionary framework."),
    "theta-8b-rl": dict(classification="ai_search_framework", source_url=_THETA_METHOD_URL,
        basis="ThetaEvolve describes automated program evolution with test-time reinforcement learning; the formal result shrinks the same method's output."),
    "theta-alphaevolve": dict(classification="ai_search_framework", source_url=_THETA_ARTIFACT_URL,
        basis="The pinned ThetaEvolve author repository identifies this artifact as its AlphaEvolve baseline, not a separate Theta method."),
    "alphaevolve": dict(classification="ai_search_framework",
        source_url="https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/",
        basis="Google DeepMind describes an evolutionary coding agent combining LLM proposals with automated evaluators."),
    "station": dict(classification="ai_search_framework", source_url="https://arxiv.org/abs/2511.06309",
        basis="The Station paper describes an autonomous LLM-agent research system."),
}

# Göther v1.2.1 (2026-08-22), corpus frozen 2026-08-08, sections 1 and 2.
# These are the audit's rechecks, not claims that every original author reported
# this value. Do not merge the Shinka paper's two values with its audited artifact.
_REFERENCES = (
    ("gother-relaxed", "gother", "Göther Labs / Evölther 2.0", "2.63599872089287514", 1e-6, "audited", "Göther corpus audit", _AUDIT_URL),
    ("theta-8b-rl-relaxed", "theta-8b-rl", "Theta 8B-RL", "2.63598566124089912", 1e-6, "audited", "Göther corpus audit", _AUDIT_URL),
    ("shinka-reported-relaxed", "shinka", "ShinkaEvolve — reported relaxed", "2.635983099011548", 1e-6, "reported", "Sakana AI · ICLR 2026 §B.1", _SHINKA_URL),
    ("hyra-relaxed", "hyra", "Hyra", "2.63598309510684482", 1e-6, "audited", "Göther corpus audit", _AUDIT_URL),
    ("gother-1e-10", "gother", "Göther Labs / Evölther 2.0", "2.63598308647338795", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("packomania-1e-10", "packomania", "Packomania", "2.635983084919", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("alphaevolve-v2-1e-10", "alphaevolve", "AlphaEvolve v2", "2.6359830849176068", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("station-1e-10", "station", "Station", "2.63598308491754725", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("gother-strict", "gother", "Göther Labs / Evölther 2.0 — strict", _STRICT_GOTHER, 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("jason-liang-strict", "jason-liang", "Jason Liang", "2.635983084893", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("theta-8b-rl-formal-strict", "theta-8b-rl", "Theta 8B-RL Formal", "2.63598307738811934", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("shinka-reported-shrink", "shinka", "ShinkaEvolve — reported radius shrink", "2.6359828390115476", 0.0, "reported", "Sakana AI · ICLR 2026 §B.1", _SHINKA_URL),
    ("shinka-audited-strict", "shinka", "ShinkaEvolve — audited artifact", "2.63598282664580639", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("theta-alphaevolve-strict", "theta-alphaevolve", "AlphaEvolve — Theta-hosted artifact", "2.63586275641369812", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
)


def _references(current):
    result = []
    for ident, method_id, name, literal, tolerance, status, source_name, source_url in _REFERENCES:
        value = float(literal)
        method = _METHODS.get(method_id, {})
        comparable = tolerance == _RUN_TOLERANCE
        result.append(dict(id=ident, method_id=method_id, name=name, value=value, value_label=literal,
            tolerance=tolerance, status=status, source_name=source_name, source_url=source_url,
            method_classification=method.get("classification", "unknown"),
            classification_source_url=method.get("source_url"), classification_basis=method.get("basis"),
            comparison_contract=_COMPARISON_CONTRACT,
            effort=_published_effort(method_id),
            comparison_status="same_contract" if comparable else "different_tolerance",
            gap_percent=(value - current) / value * 100 if current is not None and comparable else None))
    return result


def _best_comparison(references, current, *, ai_only=False):
    label = "Best AI search" if ai_only else "Best known"
    eligible = [row for row in references if row["comparison_status"] == "same_contract"
        and (not ai_only or row["method_classification"] == "ai_search_framework")]
    result = dict(status="unavailable", label=label, reference_id=None, name=None,
        value=None, value_label=None, tolerance=_RUN_TOLERANCE, current_value=current,
        gap_percent=None, source_name=None, source_url=None, method_classification=None,
        evidence_status=None, effort=_published_effort(None),
        classification_source_url=None, classification_basis=None,
        comparison_contract=_COMPARISON_CONTRACT, scope="selected_published_references",
        ai_scope="ai_search_framework" if ai_only else None,
        reason="No documented AI search result at this tolerance." if ai_only else "No compatible reference.")
    if eligible:
        best = max(eligible, key=lambda row: Decimal(row["value_label"]))
        result.update(status="known", reference_id=best["id"], evidence_status=best["status"], reason=None,
            **{key: best[key] for key in ("name", "value", "value_label", "gap_percent", "source_name", "effort",
                "source_url", "method_classification", "classification_source_url", "classification_basis")})
    return result


def benchmark_for(task, metric, best_score, *, metric_display=None):
    if task != "oe/circle_packing" or not isinstance(metric, dict):
        return None
    try:
        metric = validate_metric_context(metric)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None
    semantics = metric.get("semantics")
    if (metric.get("task_name") != task
            or metric.get("task_hash") not in KNOWN_CIRCLE_TASK_HASHES
            or metric.get("primary_metric") != "combined_score"
            or metric.get("goal") != "maximize"
            or not isinstance(semantics, dict)
            or semantics.get("kind") != "validity_gated_ratio"
            or semantics.get("numerator_case") != "sum_radii"
            or semantics.get("numerator_units") != "unit_square_side_length"
            or semantics.get("denominator") != 2.635
            or semantics.get("validity_case") != "validity"
            or semantics.get("valid_value") != 1.0
            or semantics.get("invalid_score") != 0.0
            or semantics.get("invalid_numerator_value") != 0.0):
        return None
    # Reference data may exist without a current measured numerator. Never
    # convert an unqualified score (including a penalty) to a physical value.
    current = (metric_display.get('value') if isinstance(metric_display, dict)
        and metric_display.get('schema') == 'sciel-metric-display/1'
        and metric_display.get('status') == 'measured'
        and isinstance(metric.get('sha256'), str)
        and metric_display.get('metric_sha256') == metric.get('sha256')
        and metric_display.get('raw_score') == best_score else None)
    try:
        if type(current) not in (int, float) or not math.isfinite(current) or current < 0:
            current = None
    except OverflowError:
        current = None
    references = _references(current)
    best_known = _best_comparison(references, current)
    best_ai_method = _best_comparison(references, current, ai_only=True)
    reference = next(row.copy() for row in references if row["id"] == best_known["reference_id"])
    value = reference["value"]
    return {
        "label": "Tolerance-matched reference", "value": value,
        "value_label": reference["value_label"], "metric": "Sum of radii",
        "score": value / 2.635, "current_value": current,
        "gap": value - current if current is not None else None,
        "percent_of_reference": current / value * 100 if current is not None else None,
        "task_target": 2.635, "target_metric": "Sum of radii",
        "source_label": "Göther Labs · τ = 1e-6 witness",
        "source_url": _AUDIT_URL,
        "checked_at": "2026-09-20", "reference_tolerance": _RUN_TOLERANCE,
        "run_tolerance": _RUN_TOLERANCE,
        "reference": reference, "references": references,
        "best_known": best_known, "best_ai_method": best_ai_method,
        "comparison_contract": _COMPARISON_CONTRACT,
        "audit_corpus_date": "2026-08-08", "audit_release_date": "2026-08-22",
        "note": "Selected references, not an exhaustive world ranking. The main reference matches "
                "this run's τ = 1e-6; other tolerances are separate contracts. Audited rows use "
                "Göther's exact-rational recheck; reported Shinka rows come from its paper. "
                "Best AI search includes documented AI search frameworks, not all AI-assisted work. "
                "Unknown method classifications are excluded from that subset. "
                "Matching task, metric and tolerance do not imply identical numerical verification. "
                "Numerical gaps do not certify a record, global optimality or equal compute budgets.",
    }
