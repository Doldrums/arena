# Independently written trivial seed for the AlphaEvolve notebook task; a valid but weak
# construction. It is not the published construction and not a reproduction of the paper.
# Contract: construct() -> integer numpy array of shape (k, 11); minimum pairwise distance must be at least the maximum norm
import itertools
import numpy as np


def construct():
    vectors = []
    for i, j in itertools.combinations(range(11), 2):
        for si in (1, -1):
            for sj in (1, -1):
                v = [0] * 11
                v[i], v[j] = si, sj
                vectors.append(v)
    return np.array(vectors, dtype=np.int64)
