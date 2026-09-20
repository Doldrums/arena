"""Synthetic saved arrays from the pinned upstream tests; no evaluator runs."""
import hashlib
import json
import numpy as np
from arena.observers.sciel.compat.native_geometry import SCHEMA
from arena.observers.sciel.compat.repeat_support import EVALUATOR_SHA

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def fixture(dtype='float64', *, validity=True, numeric=None, confirmation=None):
    if numeric is None:
        numeric = {'centers': [[(i % 6 + .5)/6, (i//6 + .5)/5] for i in range(26)],
                   'radii': [.01]*26}
    c = np.array(numeric['centers'], dtype=dtype)
    r = np.array(numeric['radii'], dtype=dtype)
    numeric = {'centers':[[float(v) for v in row] for row in c], 'radii':[float(v) for v in r]}
    total = float(np.sum(r)) if validity else 0.
    return {'schema':SCHEMA, 'source_sha256':'1'*64, 'evaluator_sha256':EVALUATOR_SHA,
            'invocation_id':'a'*32, 'stage':'full', 'confirmation':confirmation,
            'numeric':numeric, 'numeric_sha256':digest(numeric), 'centers_dtype':str(c.dtype),
            'radii_dtype':str(r.dtype), 'native_validity':validity,
            'native_sum_radii':total, 'native_score':total/2.635}


def observation(g, *, reached=None, ok=True, confirmed=False):
    cases = {'sum_radii':g['native_sum_radii'], 'validity':float(g['native_validity']),
             'combined_score':g['native_score'], 'target_ratio':g['native_score']}
    if g['confirmation']:
        cases['n_trials'] = float(g['confirmation']['trials'])
    return {'ok':ok, 'score':g['native_score'] if ok else 0., 'cases':cases,
            'reached':reached or g['stage'], 'confirmed':confirmed, 'raw_first_score':.99}
