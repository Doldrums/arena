"""Copy pinned JAX scalar outputs without broadening plain-data capture elsewhere.

The reviewed JAX 0.4.38 runtime returns concrete ArrayImpl scalars for some
reported ratios. Only its already-loaded concrete type is supported. This is
cooperative same-process observation, not protection against runtime tampering.
"""
from __future__ import annotations

import sys

import numpy as np

from arena_construction_capture import UNSUPPORTED, _snapshot as plain_snapshot


def snapshot(value, depth=0):
    if depth > 5:
        return UNSUPPORTED
    if type(value) in (list, tuple):
        return type(value)(snapshot(item, depth + 1) for item in value)
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: snapshot(item, depth + 1) for key, item in value.items()}
    extension = sys.modules.get("jaxlib.xla_extension")
    concrete_type = getattr(extension, "ArrayImpl", None)
    if concrete_type is not None and type(value) is concrete_type:
        # Avoid importing JAX for NumPy-only candidates and do not accept
        # arbitrary __array__, __float__, subclass, vector, bool or complex data.
        if value.ndim != 0 or value.dtype.kind not in "iuf":
            return UNSUPPORTED
        copied = np.asarray(value).copy()
        return copied if copied.shape == () and copied.dtype.kind in "iuf" else UNSUPPORTED
    return plain_snapshot(value, depth)
