"""Read-only journal compatibility extracted from sciel.engine.llm.client.

SCiEL source commit: 0d67f813dd4ac21dee304f2b0de0b0ce59bf4157.
Only dependency-reachable validators/readers/constants are retained.
"""
from __future__ import annotations

import math


PRICE_PER_1K = {
    # Uncached token estimate, verified 2026-09-19 against
    # https://developers.openai.com/api/docs/models/gpt-4.1-mini
    "gpt-4.1-mini": (0.0004, 0.0016),
    "gemini-2.5-flash-lite": (0.0001, 0.0004),
    # Fallback only. Verified against /api/v1/models on 2026-09-14;
    # provider usage.cost is authoritative whenever supplied.
    "gemini-2.5-flash": (0.0003, 0.0025),
}


def known_cost(response) -> float:
    """Require a known charge before accepting a response or accumulating cost."""
    value = getattr(response, "cost", None)
    if type(value) not in (int, float):
        raise ValueError("LLM response cost is unknown or invalid")
    try:
        cost = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("LLM response cost is unknown or invalid") from exc
    if not math.isfinite(cost) or cost < 0:
        raise ValueError("LLM response cost is unknown or invalid")
    return cost


def _tokens(value):
    # SDK token usage is integral. Missing, partial or malformed usage is not
    # evidence of a free call and must not enter the pricing fallback as zero.
    return value if type(value) is int and 0 <= value <= 10**9 else None


COST_PROVENANCE_SCHEMA = 'sciel-llm-cost-provenance/1'


def response_cost_provenance(response):
    """Detach only bounded pricing facts consistent with the returned amount.

    Missing/invalid optional metadata never changes accounting or invents a
    provider charge. In particular old receipts remain unannotated. The rates
    stored for an estimate are historical inputs, not today's price table.
    """
    try:
        value = getattr(response, 'cost_provenance', None)
        if type(value) is not dict or value.get('schema') != COST_PROVENANCE_SCHEMA:
            return None
        try:
            cost = known_cost(response)
        except ValueError:
            cost = None
        source = value.get('source')
        base = {'schema': COST_PROVENANCE_SCHEMA, 'source': source}
        if source == 'unavailable':
            return base if set(value) == set(base) and cost is None else None
        if source == 'provider_reported':
            amount = value.get('reported_cost')
            if (set(value) != {*base, 'reported_cost'} or type(amount) not in (int, float)
                    or not math.isfinite(amount) or amount < 0 or cost is None or amount != cost):
                return None
            return {**base, 'reported_cost': amount}
        if source != 'token_estimate' or set(value) != {
                *base, 'pricing_key', 'prompt_usd_per_1k', 'completion_usd_per_1k'}:
            return None
        key = value['pricing_key']
        if type(key) is not str or key not in {*PRICE_PER_1K, 'default'}:
            return None
        pin, pout = value['prompt_usd_per_1k'], value['completion_usd_per_1k']
        if any(type(rate) not in (int, float) or not math.isfinite(rate) or rate < 0
               for rate in (pin, pout)):
            return None
        pt, ct = (_tokens(getattr(response, field, None))
                  for field in ('prompt_tokens', 'completion_tokens'))
        if pt is None or ct is None or cost is None or (pt / 1000.0) * pin + (ct / 1000.0) * pout != cost:
            return None
        return {**base, 'pricing_key': key, 'prompt_usd_per_1k': pin,
                'completion_usd_per_1k': pout}
    except Exception:
        return None
