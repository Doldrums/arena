"""Read-only classification of receipt amounts; never introduce a tariff."""
import hashlib
import math
from types import SimpleNamespace

from .compat.llm_cost import response_cost_provenance

_ENDPOINT_SHA256 = hashlib.sha256(b'https://chatgpt.com/backend-api/codex/responses').hexdigest()


def subscription_unpriced(value):
    if not isinstance(value, dict):
        return False
    provenance = value.get('cost_provenance')
    return (value.get('cost') is None and value.get('finish_reason') == 'stop'
        and value.get('response_error') is None and isinstance(provenance, dict)
        and set(provenance) == {'schema','source','provider','response_status','endpoint_sha256'}
        and provenance.get('schema') == 'sciel-llm-cost-provenance/1'
        and provenance.get('source') == 'subscription_unpriced'
        and provenance.get('provider') == 'codex_responses'
        and provenance.get('response_status') == 'completed'
        and provenance.get('endpoint_sha256') == _ENDPOINT_SHA256)


def token_count(value):
    return value if type(value) is int and value >= 0 else None


def receipt_amounts(value):
    """Separate provider reports, historical estimates and unclassified amounts.

    A saved cost counter alone is not evidence of billing. Validate the original
    per-call provenance, including the saved rates for a token estimate, without
    applying any current or default price table.
    """
    value = value if isinstance(value, dict) else {}
    amount = value.get('cost')
    try:
        amount = amount if type(amount) in (int, float) and math.isfinite(amount) and amount >= 0 else None
    except OverflowError:
        amount = None
    provenance = response_cost_provenance(SimpleNamespace(
        cost=value.get('cost'), cost_provenance=value.get('cost_provenance'),
        prompt_tokens=value.get('prompt_tokens'), completion_tokens=value.get('completion_tokens')))
    source = provenance['source'] if provenance else None
    return dict(reported_usd=amount if source == 'provider_reported' else None,
        estimated_usd=amount if source == 'token_estimate' else None,
        unattributed_recorded_usd=amount if source not in {'provider_reported', 'token_estimate'} else None,
        recorded_usd=amount, cost_source=source or 'unspecified_recorded_cost')
