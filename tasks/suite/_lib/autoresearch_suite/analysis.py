"""Analytic and additive-combinatorics problems from the AlphaEvolve paper (Appendix B).

Independent implementations of the notebook's verification rules for the
autocorrelation inequalities (B.1-B.3 and the signed variant), the uncertainty
inequality (B.4, Hermite construction), Erdős' minimum overlap problem (B.5)
and the sums-and-differences problem (B.6). Each reproduces the official
notebook's printed value on the official construction.
"""
from __future__ import annotations

import math

import numpy as np

from .runtime import CandidateError, require


def _heights(values, name, nonnegative):
    try:
        h = np.asarray(values, dtype=float).ravel()
    except (TypeError, ValueError) as error:
        raise CandidateError(f"{name} must be a numeric sequence: {error}") from None
    require(h.size >= 2, f"{name} needs at least two step heights")
    require(np.all(np.isfinite(h)), f"{name} contains NaN or infinite values")
    if nonnegative:
        require(np.all(h >= 0), f"{name} must be nonnegative")
    require(abs(float(np.sum(h))) > 0, f"{name} must not sum to zero")
    return h


def first_autocorrelation_bound(heights):
    """Upper bound on C1 from nonnegative step heights on [-1/4, 1/4] (B.1). Lower is better."""
    h = _heights(heights, "heights", nonnegative=True)
    conv = np.convolve(h, h)
    return float(2 * len(h) * np.max(conv) / np.sum(h) ** 2)


def second_autocorrelation_bound(heights):
    """Lower bound on C2 from nonnegative step heights (B.2). Higher is better."""
    h = _heights(heights, "heights", nonnegative=True)
    conv = np.convolve(h, h)
    num_points = len(conv)
    x_points = np.linspace(-0.5, 0.5, num_points + 2)
    widths = np.diff(x_points)
    y = np.concatenate(([0.0], conv, [0.0]))
    l2 = 0.0
    for i in range(num_points + 1):
        y1, y2, w = y[i], y[i + 1], widths[i]
        l2 += (w / 3) * (y1 * y1 + y1 * y2 + y2 * y2)
    norm_1 = np.sum(np.abs(conv)) / (num_points + 1)
    norm_inf = np.max(np.abs(conv))
    return float(l2 / (norm_1 * norm_inf))


def third_autocorrelation_bound(heights):
    """Upper bound on C3 from signed step heights (B.3): |2N max(h*h)| / (sum h)^2. Lower is better."""
    h = _heights(heights, "heights", nonnegative=False)
    conv = np.convolve(h, h)
    return float(abs(2 * len(h) * np.max(conv) / np.sum(h) ** 2))


def signed_autocorrelation_abs_bound(heights):
    """Upper bound on C3' from signed step heights: 2N max|h*h| / (sum h)^2. Lower is better."""
    h = _heights(heights, "heights", nonnegative=False)
    conv = np.convolve(h, h)
    return float(2 * len(h) * np.max(np.abs(conv)) / np.sum(h) ** 2)


def erdos_minimum_overlap_bound(sequence):
    """Upper bound on C5 from step heights in [0,1] whose sum is exactly n/2 (B.5). Lower is better."""
    h = _heights(sequence, "sequence", nonnegative=True)
    require(np.all(h <= 1.0), "all step heights must be at most 1")
    require(abs(float(np.sum(h)) - len(h) / 2.0) <= 1e-9 * len(h), f"heights must sum to n/2 = {len(h) / 2}; got {float(np.sum(h))}")
    corr = np.correlate(h, 1 - h, mode="full")
    return float(np.max(corr) / len(h) * 2)


def sums_differences_lower_bound(values):
    """Lower bound on C6 from a finite set of nonnegative integers containing 0 (B.6). Higher is better."""
    try:
        u = sorted({int(v) for v in values})
    except (TypeError, ValueError) as error:
        raise CandidateError(f"the set must contain integers: {error}") from None
    require(len(u) >= 2, "the set needs at least two elements")
    require(u[0] == 0, "the set must be nonnegative and contain 0")
    max_u = u[-1]
    require(max_u <= 5_000_000, "elements above 5e6 are not supported by this evaluator")
    minus = np.zeros(2 * max_u + 1, dtype=bool)
    plus = np.zeros(2 * max_u + 1, dtype=bool)
    arr = np.array(u)
    for i in u:
        minus[i - arr + max_u] = True
        plus[i + arr] = True
    size_minus, size_plus = int(np.sum(minus)), int(np.sum(plus))
    return float(1 + math.log(size_minus / size_plus) / math.log(2 * max_u + 1))


def uncertainty_hermite_bound(coefficients):
    """Upper bound on C4 from a 3-coefficient Hermite combination (B.4). Lower is better.

    Reimplements the notebook's ``find_hermite_combination`` / ``get_upper_bound``
    with sympy's exact root isolation; verification checks g(0) = 0 and a
    positive limit at infinity as in the notebook.
    """
    import sympy
    coeffs = np.asarray(coefficients, dtype=float).ravel()
    require(coeffs.size == 3 and np.all(np.isfinite(coeffs)), "expected three finite coefficients")
    x = sympy.symbols("x")
    m = len(coeffs)
    rational = [sympy.Rational(float(c)) for c in coeffs]
    degrees = np.arange(0, 4 * m + 4, 4)
    hps = [sympy.polys.orthopolys.hermite_poly(n=int(i), x=x, polys=False) for i in degrees]
    partial = sum(rational[i] * hps[i] for i in range(m))
    # The last coefficient is fixed so that the combination vanishes at 0 (notebook construction).
    rational.append(sympy.Rational(-partial.subs(x, 0) / hps[-1].subs(x, 0)))
    g = sum(rational[i] * hps[i] for i in range(m + 1))
    if sympy.limit(g, x, sympy.oo) < 0:
        g = -g
    require(g.subs(x, 0) == 0, "the Hermite combination does not vanish at zero")
    gq = sympy.exquo(g, x ** 2)
    largest = 0
    for root in sympy.real_roots(gq, x):
        approx = root.eval_rational(n=200)
        plus, minus = approx + sympy.Rational(1e-198), approx - sympy.Rational(1e-198)
        if (gq.subs(x, plus) > 0 and gq.subs(x, minus) < 0) or (gq.subs(x, plus) < 0 and gq.subs(x, minus) > 0):
            largest = max(largest, approx)
    return float(largest ** 2) / (2 * math.pi)


def uncertainty_laguerre_bound(roots, m=12, n=1):
    """Upper bound on C4 from a Laguerre combination with prescribed double roots (B.4, notebook variant).

    Exact port of the notebook's ``find_laguerre_combination`` and its
    verification: the combination of Laguerre polynomials (alpha = n/2 - 1,
    degrees 0, 2, ..., 4m+2) is fixed by g(0) = 0, g'(0) = 1 and double roots at
    the given m positive locations; the bound is the largest sign change of the
    quotient divided by 2*pi. Lower is better.
    """
    import sympy
    z = np.asarray(roots, dtype=float).ravel()
    require(z.size == m and np.all(np.isfinite(z)) and np.all(z > 0), f"expected {m} finite positive double-root locations")
    require(len(set(z.tolist())) == m, "double-root locations must be distinct")
    z = np.sort(z)
    alpha = sympy.Rational(n, 2) - 1
    degrees = list(range(0, 4 * m + 4, 2))
    x = sympy.symbols("x")
    lps = [sympy.polys.orthopolys.laguerre_poly(n=i, x=x, alpha=alpha, polys=False) for i in degrees]
    num_conditions = 2 * m + 2
    A = sympy.Matrix(num_conditions, len(lps), lambda i, j: 0)
    b = sympy.Matrix(num_conditions, 1, lambda i, j: 0)
    b[1] = 1
    for j, lp in enumerate(lps):
        A[0, j] = lp.subs(x, 0)
        A[1, j] = lp.diff(x).subs(x, 0)
    for i in range(m):
        zi = sympy.Rational(float(z[i]))
        for j, lp in enumerate(lps):
            A[2 * i + 2, j] = lp.subs(x, zi)
            A[2 * i + 3, j] = lp.diff(x).subs(x, zi)
    try:
        coeffs = A.LUsolve(b)
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"the interpolation system is singular: {error}") from None
    g = sum(coeffs[i] * lps[i] for i in range(len(lps)))
    div = sympy.prod([(x - sympy.Rational(float(zz))) ** 2 for zz in z]) * x
    gq = sympy.exquo(g, div)
    largest = 0
    for root in sympy.real_roots(gq, x):
        approx = root.eval_rational(n=200)
        plus, minus = approx + sympy.Rational(1e-198), approx - sympy.Rational(1e-198)
        if (gq.subs(x, plus) > 0 and gq.subs(x, minus) < 0) or (gq.subs(x, plus) < 0 and gq.subs(x, minus) > 0):
            largest = max(largest, approx)
    return float(largest) / (2 * math.pi)
