"""Ant-colony orienteering, knapsack and offline packing evaluations."""
from __future__ import annotations

from .combinatorial import (
    _call,
    distance_matrix,
    np,
    require,
    rng_for,
)

def orienteering_instances(n_instances, n_nodes, seed, max_len=3.0):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        coords = rng.random((n_nodes, 2))
        prizes = rng.random(n_nodes)
        prizes[0] = 0.0
        out.append({"coords": coords, "prizes": prizes, "max_len": max_len})
    return out


def orienteering_aco_score(heuristics, instances, n_ants=20, n_iterations=30):
    """Mean best collected prize from ACO driven by ``heuristics(prizes, distance_matrix, max_len)``. Higher is better."""
    out = []
    for k, instance in enumerate(instances):
        coords, prizes, max_len = instance["coords"], instance["prizes"], instance["max_len"]
        d = distance_matrix(coords)
        h = np.asarray(_call(heuristics, prizes.copy(), d.copy(), float(max_len)), dtype=float)
        require(h.shape == d.shape and np.all(np.isfinite(h)), "heuristics must return a finite matrix of the same shape as the distance matrix")
        h = np.where(h > 0, h, 1e-9)
        rng = rng_for(k)
        n = len(d)
        pheromone = np.ones((n, n))
        best = 0.0
        for _ in range(n_iterations):
            results = []
            for _ in range(n_ants):
                visited = np.zeros(n, dtype=bool)
                visited[0] = True
                cur, used, prize = 0, 0.0, 0.0
                while True:
                    mask = (~visited) & (used + d[cur] + d[:, 0] <= max_len)
                    if not mask.any():
                        break
                    probs = pheromone[cur] * h[cur]
                    probs[~mask] = 0
                    total = probs.sum()
                    nxt = int(rng.choice(n, p=probs / total)) if total > 0 else int(rng.choice(np.nonzero(mask)[0]))
                    used += d[cur, nxt]
                    prize += prizes[nxt]
                    visited[nxt] = True
                    cur = nxt
                results.append(prize)
            pheromone *= 0.9
            best = max(best, max(results))
            pheromone += max(results) / 10.0
        out.append(best)
    return float(np.mean(out))


def mkp_instances(n_instances, n_items, n_constraints, seed):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        prizes = rng.random(n_items)
        weights = rng.random((n_constraints, n_items))
        out.append({"prizes": prizes, "weights": weights, "capacities": np.full(n_constraints, n_items * 0.25)})
    return out


def mkp_aco_score(heuristics, instances, n_ants=20, n_iterations=30):
    """Mean best prize of multi-dimensional knapsack from ACO driven by ``heuristics(prizes, weights)``. Higher is better."""
    out = []
    for k, instance in enumerate(instances):
        prizes, weights, caps = instance["prizes"], instance["weights"], instance["capacities"]
        h = np.asarray(_call(heuristics, prizes.copy(), weights.copy()), dtype=float).ravel()
        require(h.shape == prizes.shape and np.all(np.isfinite(h)), "heuristics must return one finite score per item")
        h = np.where(h > 0, h, 1e-9)
        rng = rng_for(k)
        n = len(prizes)
        pheromone = np.ones(n)
        best = 0.0
        for _ in range(n_iterations):
            results = []
            for _ in range(n_ants):
                chosen = np.zeros(n, dtype=bool)
                used = np.zeros(len(caps))
                while True:
                    mask = (~chosen) & np.all(used[:, None] + weights <= caps[:, None], axis=0)
                    if not mask.any():
                        break
                    probs = pheromone * h
                    probs[~mask] = 0
                    total = probs.sum()
                    item = int(rng.choice(n, p=probs / total)) if total > 0 else int(rng.choice(np.nonzero(mask)[0]))
                    chosen[item] = True
                    used += weights[:, item]
                results.append(float(prizes[chosen].sum()))
            pheromone *= 0.9
            best = max(best, max(results))
            pheromone += max(results) / 10.0
        out.append(best)
    return float(np.mean(out))


def offline_bin_packing_instances(n_instances, n_items, seed, capacity=150):
    rng = rng_for(seed)
    return [{"demands": rng.integers(20, 100, size=n_items), "capacity": capacity} for _ in range(n_instances)]


def offline_bin_packing_aco_score(heuristics, instances, n_ants=20, n_iterations=30):
    """Mean best number of bins from ACO driven by ``heuristics(demands, capacity) -> item-item matrix``. Lower is better."""
    out = []
    for k, instance in enumerate(instances):
        demands, capacity = instance["demands"], instance["capacity"]
        n = len(demands)
        h = np.asarray(_call(heuristics, demands.astype(float).copy(), float(capacity)), dtype=float)
        require(h.shape == (n, n) and np.all(np.isfinite(h)), "heuristics must return a finite item-by-item matrix")
        h = np.where(h > 0, h, 1e-9)
        rng = rng_for(k)
        pheromone = np.ones((n, n))
        best = n
        for _ in range(n_iterations):
            results = []
            for _ in range(n_ants):
                remaining = set(range(n))
                bins = 0
                while remaining:
                    bins += 1
                    load = 0
                    cur = None
                    while True:
                        fits = [i for i in remaining if load + demands[i] <= capacity]
                        if not fits:
                            break
                        if cur is None:
                            item = fits[int(rng.integers(len(fits)))]
                        else:
                            probs = np.array([pheromone[cur, i] * h[cur, i] for i in fits])
                            total = probs.sum()
                            item = fits[int(rng.choice(len(fits), p=probs / total))] if total > 0 else fits[int(rng.integers(len(fits)))]
                        load += demands[item]
                        remaining.remove(item)
                        cur = item
                results.append(bins)
            pheromone *= 0.9
            best = min(best, min(results))
            pheromone += 1.0 / min(results)
        out.append(best)
    return float(np.mean(out))
