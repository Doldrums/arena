"""Selected dated references, with separate tolerance and evidence contracts.

Verified against the linked primary audit and paper on 2026-09-19. Values are
stored as decimal strings for display; floats are only for chart arithmetic.
The board neither fetches sources nor certifies records while serving a run.
"""
from __future__ import annotations

import math

from .compat.repeat_support import KNOWN_CIRCLE_TASK_HASHES
from .compat.measurement import validate_metric_context

_AUDIT_URL = "https://www.gotherlabs.com/results/circle-packing-26-unit-square/"
_SHINKA_URL = "https://openreview.net/pdf?id=lKEdGCoDNC"
_STRICT_GOTHER = ("2.6359830849176077831865694854434817303966767982744748577457711298607038493344723396767997365079")

# Göther v1.2.1 (2026-08-22), corpus frozen 2026-08-08, sections 1 and 2.
# These are the audit's rechecks, not claims that every original author reported
# this value. Do not merge the Shinka paper's two values with its audited artifact.
_REFERENCES = (
    ("Göther Labs / Evölther 2.0", "2.63599872089287514", 1e-6, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Theta 8B-RL", "2.63598566124089912", 1e-6, "audited", "Göther corpus audit", _AUDIT_URL),
    ("ShinkaEvolve — reported relaxed", "2.635983099011548", 1e-6, "reported", "Sakana AI · ICLR 2026 §B.1", _SHINKA_URL),
    ("Hyra", "2.63598309510684482", 1e-6, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Göther Labs / Evölther 2.0", "2.63598308647338795", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Packomania", "2.635983084919", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("AlphaEvolve v2", "2.6359830849176068", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Station", "2.63598308491754725", 1e-10, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Göther Labs / Evölther 2.0 — strict", _STRICT_GOTHER, 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Jason Liang", "2.635983084893", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Theta 8B-RL Formal", "2.63598307738811934", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("ShinkaEvolve — reported radius shrink", "2.6359828390115476", 0.0, "reported", "Sakana AI · ICLR 2026 §B.1", _SHINKA_URL),
    ("ShinkaEvolve — audited artifact", "2.63598282664580639", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
    ("Theta AlphaEvolve", "2.63586275641369812", 0.0, "audited", "Göther corpus audit", _AUDIT_URL),
)


def _references(current):
    result = []
    for name, literal, tolerance, status, source_name, source_url in _REFERENCES:
        value = float(literal)
        result.append(dict(name=name, value=value, value_label=literal,
            tolerance=tolerance, status=status, source_name=source_name, source_url=source_url,
            gap_percent=(value - current) / value * 100 if current is not None else None))
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
            or semantics.get("denominator") != 2.635
            or semantics.get("validity_case") != "validity"
            or semantics.get("valid_value") != 1.0
            or semantics.get("invalid_score") != 0.0):
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
    reference = references[0].copy()
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
        "checked_at": "2026-09-19", "reference_tolerance": 1e-6,
        "run_tolerance": 1e-6,
        "reference": reference, "references": references,
        "audit_corpus_date": "2026-08-08", "audit_release_date": "2026-08-22",
        "note": "Selected references, not an exhaustive world ranking. The main reference matches "
                "this run's τ = 1e-6; other tolerances are separate contracts. Audited rows use "
                "Göther's exact-rational recheck; reported Shinka rows come from its paper. "
                "Numerical gaps do not certify a record, global optimality or equal compute budgets.",
    }
