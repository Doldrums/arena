"""Project recorded native metrics without loading participant code."""
from __future__ import annotations

import csv
from .results_native_evidence import (
    HASH,
    INTEGER,
    NUMBER,
    _Artifacts,
)
from .results_native_prompt import (
    GSM8K_DATASET,
    GSM8K_METRIC,
    PENGUINS_DATASET,
    _aflow,
    _prompt_gsm8k,
    _promptagent,
)
from .results_native_search import (
    _base,
    _codeevolve,
    _coevo,
    _darwinian,
    _eoh,
    _loongflow,
    _meoh,
    _sky,
    _validation,
)


SUPPORTED = {'adaevolve', 'evox', 'openevolve', 'base', 'eoh', 'meoh',
             'reevo', 'hsevo', 'loongflow', 'codeevolve', 'coevo', 'coevo-observed-v2',
             'darwinian-evolver-gateway', 'aflow-gateway-gsm8k-v1',
             'promptagent-penguins-gateway', 'gepa-gateway-gsm8k', 'miprov2-gateway-gsm8k'}


def project_native(evidence, framework, native_result):
    """Read only listed, hash-matching files through the caller's bounded reader."""
    result = dict(best_score=None, seed_score=None, metric=None, direction=None, task=None,
                  scope='native', evaluations=None, candidates=None, iterations=None, status='unsupported')
    if framework not in SUPPORTED:
        return result
    result['status'] = 'missing'
    try:
        if (type(native_result) is not dict or native_result.get('schema') != 'arena.native-result/1'
                or native_result.get('framework') != framework or native_result.get('canonical_evaluation') is not False):
            raise ValueError('Native identity/scope mismatch')
        art = _Artifacts(evidence, native_result)
        if framework in {'adaevolve','evox','openevolve'}:
            _sky(art,framework,result)
        elif framework == 'base': _base(art,result)
        elif framework == 'eoh': _eoh(art,result)
        elif framework == 'meoh': _meoh(art,result)
        elif framework in {'reevo','hsevo'}: _validation(art,framework,result)
        elif framework == 'loongflow': _loongflow(art,result)
        elif framework == 'codeevolve': _codeevolve(art,result)
        elif framework == 'darwinian-evolver-gateway': _darwinian(art,result)
        elif framework in {'gepa-gateway-gsm8k', 'miprov2-gateway-gsm8k'}: _prompt_gsm8k(art,framework,result)
        elif framework == 'aflow-gateway-gsm8k-v1': _aflow(art,result)
        elif framework == 'promptagent-penguins-gateway': _promptagent(art,result)
        else: _coevo(art,framework,result)
        result.update(status='partial' if native_result.get('status') != 'recorded' else 'recorded',
                      evidence_hashes=sorted(set(art.used)))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, OverflowError, RecursionError, csv.Error):
        # A failed required integrity/contract check must not leave a previously
        # read best score behind as if the overall projection had succeeded.
        result.update(best_score=None, seed_score=None, status='partial', candidates=None, iterations=None)
        result.pop('population_objectives',None)
        result.pop('named_metrics',None)
        evidence.issues.add('Native metric evidence is missing, incompatible, or failed integrity checks.')
    return result
