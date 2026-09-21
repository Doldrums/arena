"""Exact matrix multiplication tensor benchmark derived from AlphaEvolve Appendix A.

This evaluator is an independent reimplementation, not AlphaEvolve's search code.
Candidate factors U,V,W have shape (n*m,rank),(m*p,rank),(p*n,rank).
W uses trace order: element k*n+i represents output C[i,k]. Each coefficient
is an integer or half-integer JSON number, or [real,imag] for permitted complex
instances. Exact Python integer arithmetic validates *every* tensor entry.
No floating-point tolerance or randomized matrix checks are used.
"""
from __future__ import annotations
import math

COMPLEX_SHAPES = {(3, 4, 7), (4, 4, 4), (4, 4, 8)}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _dimensions(instance):
    dims = instance.get("dimensions")
    _require(isinstance(dims, (list, tuple)) and len(dims) == 3,
             "dimensions must be [n,m,p]")
    _require(all(type(d) is int and d > 0 for d in dims),
             "dimensions must be positive integers")
    return tuple(dims)


def _twice_real(value):
    """Return 2*value exactly; reject booleans, NaN and non-half-integers."""
    if type(value) is int:
        return value * 2
    _require(type(value) is float and math.isfinite(value),
             "coefficients must be finite JSON numbers")
    numerator, denominator = value.as_integer_ratio()
    _require(denominator <= 2, "coefficients must be integers or half-integers")
    return numerator * (2 // denominator)


def _coefficient(value, allow_complex):
    if isinstance(value, list):
        _require(len(value) == 2, "complex coefficients must be [real,imag]")
        real, imag = (_twice_real(x) for x in value)
        _require(allow_complex or imag == 0,
                 "this task permits real half-integer coefficients only")
        return real, imag
    return _twice_real(value), 0


def _multiply(a, b):
    return a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]


def solve(instance, seed=0):
    """Return the deterministic rank n*m*p schoolbook decomposition."""
    n, m, p = _dimensions(instance)
    rank = n * m * p
    U = [[0] * rank for _ in range(n * m)]
    V = [[0] * rank for _ in range(m * p)]
    W = [[0] * rank for _ in range(p * n)]
    column = 0
    for i in range(n):
        for j in range(m):
            for k in range(p):
                U[i*m+j][column] = 1
                V[j*p+k][column] = 1
                W[k*n+i][column] = 1
                column += 1
    return {"U": U, "V": V, "W": W}


def score(instance, output):
    """Validate exact identity and return rank (lower is better).

    Invalid candidates raise ValueError. Runtime/resource limits belong in the
    caller's isolated worker; they are not additional mathematical constraints.
    """
    n, m, p = _dimensions(instance)
    domain = instance.get("coefficient_domain", "real_half_integers")
    _require(domain in ("real_half_integers", "gaussian_half_integers"),
             "unknown coefficient domain")
    allow_complex = domain == "gaussian_half_integers"
    _require(not allow_complex or (n, m, p) in COMPLEX_SHAPES,
             "complex coefficients are documented only for three paper shapes")
    _require(isinstance(output, dict), "candidate must be an object")
    matrices = [output.get(key) for key in ("U", "V", "W")]
    sizes = (n*m, m*p, p*n)
    _require(all(isinstance(matrix, list) and len(matrix) == size
                 for matrix, size in zip(matrices, sizes)),
             "factor row counts must be n*m, m*p and p*n")
    _require(isinstance(matrices[0][0], list), "factor rows must be lists")
    rank = len(matrices[0][0])
    _require(rank > 0, "rank must be positive")
    _require(all(isinstance(row, list) and len(row) == rank
                 for matrix in matrices for row in matrix),
             "all factor rows must have the same rank")
    # Store each column sparsely, scaling each factor by 2; tensor scale is 8.
    factors = []
    for matrix in matrices:
        columns = [[] for _ in range(rank)]
        for row_index, row in enumerate(matrix):
            for column, entry in enumerate(row):
                value = _coefficient(entry, allow_complex)
                if value != (0, 0):
                    columns[column].append((row_index, value))
        factors.append(columns)
    tensor = {}
    for column in range(rank):
        for a, u in factors[0][column]:
            for b, v in factors[1][column]:
                uv = _multiply(u, v)
                for c, w in factors[2][column]:
                    product = _multiply(uv, w)
                    key = (a, b, c)
                    old = tensor.get(key, (0, 0))
                    new = (old[0] + product[0], old[1] + product[1])
                    if new == (0, 0):
                        tensor.pop(key, None)
                    else:
                        tensor[key] = new
    # The only nonzero entries of the exact target tensor have value 8.
    for i in range(n):
        for j in range(m):
            for k in range(p):
                key = (i*m+j, j*p+k, k*n+i)
                _require(tensor.pop(key, None) == (8, 0),
                         f"tensor identity failed at target coordinate {key}")
    _require(not tensor, "tensor has nonzero entries outside the target support")
    return rank
