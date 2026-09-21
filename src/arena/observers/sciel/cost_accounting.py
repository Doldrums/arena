"""Read-only classification of completed subscription receipts, never pricing."""
import hashlib

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
