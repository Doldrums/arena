"""Lennard-Jones cluster global optimisation (computational chemistry).

Energy of ``n`` identical atoms interacting by the Lennard-Jones potential in
reduced units (pair well depth 1, sigma 1)::

    E = 4 * sum_{i<j} (r_ij^-12 - r_ij^-6)

The putative global minima of the Cambridge Cluster Database (Wales and Doye)
are the references; ``tests/test_science_chemistry.py`` reconstructs the
icosahedral (13, 55) and truncated-octahedral (38) minima from lattice
geometry, relaxes them locally and reproduces the published energies to 1e-6.
A lower energy than the database value would be a new putative minimum and
must be checked independently.
"""
from __future__ import annotations

import numpy as np

from .runtime import CandidateError, require


def lj_energy(positions):
    x = np.asarray(positions, dtype=float)
    d = x[:, None, :] - x[None, :, :]
    r2 = np.sum(d * d, axis=-1)
    iu = np.triu_indices(len(x), 1)
    inv6 = 1.0 / r2[iu] ** 3
    return float(4.0 * np.sum(inv6 * inv6 - inv6))


def lj_gradient(flat):
    x = np.asarray(flat, dtype=float).reshape(-1, 3)
    d = x[:, None, :] - x[None, :, :]
    r2 = np.sum(d * d, axis=-1)
    np.fill_diagonal(r2, np.inf)
    inv6 = 1.0 / r2 ** 3
    f = 24.0 * (2.0 * inv6 * inv6 - inv6) / r2
    return (-(f[..., None] * d).sum(axis=1)).ravel()


def relax(positions, maxiter=5000):
    """Local L-BFGS relaxation; returns (energy, positions). Used by tests and available to candidates."""
    from scipy.optimize import minimize
    x0 = np.asarray(positions, dtype=float).ravel()
    result = minimize(lambda z: lj_energy(z.reshape(-1, 3)), x0, jac=lj_gradient, method="L-BFGS-B", options={"maxiter": maxiter, "gtol": 1e-12, "ftol": 1e-15})
    return float(result.fun), result.x.reshape(-1, 3)


def cluster_score(positions, n, min_distance=0.5):
    """Lennard-Jones energy of exactly ``n`` atoms; lower is better."""
    try:
        x = np.asarray(positions, dtype=float)
    except (TypeError, ValueError):
        raise CandidateError("construct() must return an (n, 3) numeric array") from None
    require(x.shape == (n, 3), f"expected {n} atoms as rows (x, y, z); got shape {x.shape}")
    require(bool(np.all(np.isfinite(x))), "positions contain NaN or infinite values")
    d = x[:, None, :] - x[None, :, :]
    r = np.sqrt(np.sum(d * d, axis=-1))
    iu = np.triu_indices(n, 1)
    closest = float(np.min(r[iu]))
    require(closest >= min_distance, f"two atoms are {closest:.4f} apart; the minimum allowed separation is {min_distance}")
    energy = lj_energy(x)
    return energy, {"closest_pair": closest, "diameter": float(np.max(r)), "atoms": n}
