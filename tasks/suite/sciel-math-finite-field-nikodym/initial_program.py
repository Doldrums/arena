# EVOLVE-BLOCK-START
import numpy as np


def nikodym_set() -> np.ndarray:
    """
    Construct a Nikodym set in F_q^2 with q = p^2 and p = 7. A set N is a Nikodym
    set if, for every point x in F_q^2, there exists a direction v != 0 such that
    the punctured line {x + t*v : t in F_q, t != 0} is fully contained in N. The
    goal is to make N as SMALL as possible, equivalently to make its complement
    (the excluded set) as LARGE as possible.

    Field model: F_q is built as F_p[alpha] with alpha^2 = k, where k is the
    smallest quadratic non-residue mod p. An element of F_q is the pair (a, b)
    standing for a + b*alpha, with a, b in {0, ..., p-1}.

    Baseline construction (the "skip step 2.5" construction from the AlphaEvolve
    notebook, of size p^4 - p^2*(p+1)/2): take the Hermitian unital
        U = {(x, y) : Trace(x) + Norm(y) = 0},  with Trace((a,b)) = 2a,
        Norm((a,b)) = a^2 - b^2*k.
    Build the blocking set B = points of U whose y-coordinate lies in the special
    set Y = {(u^2 mod p, v) : u, v in F_p}. The excluded set is S = U \\ B, and the
    Nikodym set is everything else: N = (F_q^2) \\ S.

    Returns:
        points: np.ndarray of shape (k, 2, 2) integer array. Each of the k points
        is [[x_a, x_b], [y_a, y_b]] with the F_q coordinates x = (x_a, x_b) and
        y = (y_a, y_b), all entries in [0, p).
    """
    p = 7

    # Smallest quadratic non-residue mod p (the alpha^2 = k constant).
    k = None
    for c in range(2, p):
        if pow(c, (p - 1) // 2, p) == p - 1:
            k = c
            break

    # Special y-coordinate set Y = {(u^2 mod p, v)}: y_a must be a square mod p.
    y_special = set()
    for u in range(p):
        for v in range(p):
            y_special.add(((u * u) % p, v))

    # A point (x, y) is EXCLUDED iff it is in the unital U and its y is NOT in Y.
    # Keep every other point of F_q^2.
    points = []
    for xa in range(p):
        for xb in range(p):
            for ya in range(p):
                for yb in range(p):
                    in_unital = (2 * xa + ya * ya - yb * yb * k) % p == 0
                    in_y_special = (ya, yb) in y_special
                    if in_unital and not in_y_special:
                        continue  # excluded point (belongs to S)
                    points.append([[xa, xb], [ya, yb]])

    return np.array(points, dtype=np.int64)


# EVOLVE-BLOCK-END
