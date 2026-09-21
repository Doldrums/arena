"""Small, deterministic statevector benchmarks; no quantum service is used.

Qubit q is bit q (little endian). Circuit quality is recomputed here, never
accepted from a candidate. These are reduced method benchmarks, not evidence
of quantum advantage. Equations and adaptations are in catalog/science/quantum.json.
"""
from __future__ import annotations

import numpy as np

from .runtime import CandidateError


def angles(value, shape):
    raw = np.asarray(value)
    if np.iscomplexobj(raw) or raw.dtype.kind not in "fiu":
        raise CandidateError("Angles must be a real numeric array")
    result = np.asarray(raw, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise CandidateError(f"Expected finite angles of shape {shape}")
    if np.max(np.abs(result), initial=0) > 1e6:
        raise CandidateError("Angle magnitude must be <= 1e6 radians")
    return result


def cut_diagonal(n, edges):
    states = np.arange(1 << n, dtype=np.int64)
    cost = np.zeros(len(states))
    for u, v in edges:
        cost += ((states >> int(u)) ^ (states >> int(v))) & 1
    return cost


def qaoa_state(n, edges, gamma_beta):
    """Farhi et al. Eq. (6): each row is gamma,beta; exp(-i beta X)."""
    cost = cut_diagonal(n, edges)
    state = np.ones(1 << n, dtype=complex) / np.sqrt(1 << n)
    indices = np.arange(1 << n)
    for gamma, beta in gamma_beta:
        state *= np.exp(-1j * gamma * cost)
        for q in range(n):
            state = np.cos(beta) * state - 1j * np.sin(beta) * state[indices ^ (1 << q)]
    return state


def graph_cases(seed=713):
    rng = np.random.default_rng(seed)
    for n in (6, 8, 10):
        for density in (0.25, 0.55):
            # A cycle guarantees a connected, nonempty simple graph.
            edges = {(min(q, (q + 1) % n), max(q, (q + 1) % n)) for q in range(n)}
            edges.update((u, v) for u in range(n) for v in range(u + 1, n) if rng.random() < density)
            yield n, np.asarray(sorted(edges), dtype=np.int64)


def qaoa_score(candidate, parameters):
    p = parameters.get("layers", 2)
    cases = []
    for n, edges in graph_cases(parameters.get("seed", 713)):
        # Copy graph data; a candidate cannot change the evaluator's instance.
        theta = angles(candidate(n, edges.copy(), p), (p, 2))
        state = qaoa_state(n, edges, theta)
        cost = cut_diagonal(n, edges)
        expectation = float(np.dot(np.abs(state) ** 2, cost))
        optimum = float(cost.max())  # exhaustive classical reference
        ratio = expectation / optimum
        if not np.isfinite(ratio) or not -1e-10 <= ratio <= 1 + 1e-10:
            raise CandidateError("Invalid circuit expectation")
        cases.append({"n": n, "edges": len(edges), "expectation": expectation,
                      "exact_maxcut": optimum, "ratio": ratio})
    return float(np.mean([c["ratio"] for c in cases])), {"per_case": cases}


def ry_cz_state(n, theta):
    """L layers of Ry rotations, CZ on open-chain edges after layers 0..L-2."""
    state = np.zeros(1 << n)
    state[0] = 1.0
    indices = np.arange(1 << n)
    for layer, row in enumerate(theta):
        for q, angle in enumerate(row):
            zero = indices[(indices & (1 << q)) == 0]
            one = zero | (1 << q)
            a, b = state[zero].copy(), state[one].copy()
            c, s = np.cos(angle / 2), np.sin(angle / 2)
            state[zero], state[one] = c * a - s * b, s * a + c * b
        if layer < len(theta) - 1:
            for q in range(n - 1):
                both = ((indices >> q) & 1) & ((indices >> (q + 1)) & 1)
                state *= 1 - 2 * both
    return state


def ising_hamiltonian(n, coupling, field):
    """Open chain H=-J sum Z_q Z_(q+1)-h sum X_q; energy units J."""
    indices = np.arange(1 << n)
    z = 1 - 2 * ((indices[:, None] >> np.arange(n)) & 1)
    hamiltonian = np.diag(-coupling * np.sum(z[:, :-1] * z[:, 1:], axis=1).astype(float))
    for q in range(n):
        hamiltonian[indices, indices ^ (1 << q)] -= field
    return hamiltonian


def vqe_score(candidate, parameters):
    layers = parameters.get("layers", 3)
    cases = []
    for n in parameters.get("qubits", [4, 6]):
        for field in parameters.get("fields", [0.45, 1.0, 1.65]):
            theta = angles(candidate(n, 1.0, field, layers), (layers, n))
            state = ry_cz_state(n, theta)
            hamiltonian = ising_hamiltonian(n, 1.0, field)
            energy = float(state @ hamiltonian @ state)
            ground = float(np.linalg.eigvalsh(hamiltonian)[0])
            gap = (energy - ground) / n
            if not np.isfinite(gap) or gap < -1e-9:
                raise CandidateError("Energy violates the variational lower bound")
            cases.append({"n": n, "field": field, "energy": energy,
                          "ground_energy": ground, "gap_per_spin": max(0.0, gap)})
    return float(np.mean([c["gap_per_spin"] for c in cases])), {"per_case": cases}
