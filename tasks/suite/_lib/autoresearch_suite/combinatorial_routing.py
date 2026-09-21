"""Guided local search and ant-colony routing evaluations."""
from __future__ import annotations

from .combinatorial import (
    _call,
    distance_matrix,
    math,
    np,
    require,
    rng_for,
    tour_length,
)

# Guided local search for TSP (EoH / ReEvo / HSEvo / MCTS-AHD / CodeEvolve)
# ---------------------------------------------------------------------------

def _two_opt(tour, d, max_passes=50):
    n = len(tour)
    tour = list(tour)
    improved, passes = True, 0
    while improved and passes < max_passes:
        improved = False
        passes += 1
        for i in range(1, n - 2):
            a, b = tour[i - 1], tour[i]
            for j in range(i + 1, n - 1):
                c, e = tour[j], tour[j + 1]
                delta = d[a, c] + d[b, e] - d[a, b] - d[c, e]
                if delta < -1e-12:
                    tour[i:j + 1] = tour[i:j + 1][::-1]
                    improved = True
                    b = tour[i]
    return tour


def _nearest_neighbour(d):
    n = len(d)
    tour, seen = [0], {0}
    while len(tour) < n:
        last = tour[-1]
        nxt = min((j for j in range(n) if j not in seen), key=lambda j: d[last, j])
        tour.append(nxt)
        seen.add(nxt)
    return tour


def tsp_gls_score(update_edge_distance, instances, iterations=30):
    """Mean tour length after guided local search with the candidate's penalty rule.

    Contract (EoH tsp_gls): ``update_edge_distance(edge_distance, local_opt_tour,
    edge_n_used) -> new_edge_distance`` returns a perturbed distance matrix used
    by the next 2-opt pass; the real distance decides the reported length.
    """
    lengths = []
    for points in instances:
        d = distance_matrix(points)
        n = len(points)
        tour = _two_opt(_nearest_neighbour(d), d)
        best_tour, best_len = list(tour), tour_length(points, tour)
        edge_used = np.zeros((n, n))
        for _ in range(iterations):
            for i in range(n):
                a, b = tour[i - 1], tour[i]
                edge_used[a, b] += 1
                edge_used[b, a] += 1
            guided = np.asarray(_call(update_edge_distance, d.copy(), np.array(tour), edge_used.copy()), dtype=float)
            require(guided.shape == d.shape and np.all(np.isfinite(guided)), "update_edge_distance must return a finite matrix of the same shape")
            tour = _two_opt(tour, guided, max_passes=10)
            tour = _two_opt(tour, d, max_passes=10)
            length = tour_length(points, tour)
            if length < best_len:
                best_tour, best_len = list(tour), length
        lengths.append(best_len)
    return float(np.mean(lengths))


# ---------------------------------------------------------------------------
# Ant colony optimization families (ReEvo / MCTS-AHD / HSEvo)
# ---------------------------------------------------------------------------

def _aco_tsp(heuristic, d, n_ants=20, n_iterations=30, alpha=1.0, beta=1.0, decay=0.9, seed=0):
    rng = rng_for(seed)
    n = len(d)
    pheromone = np.ones((n, n))
    heuristic = np.where(heuristic > 0, heuristic, 1e-9)
    best = math.inf
    for _ in range(n_iterations):
        tours, costs = [], []
        for _ in range(n_ants):
            tour = [0]
            visited = np.zeros(n, dtype=bool)
            visited[0] = True
            for _ in range(n - 1):
                cur = tour[-1]
                probs = (pheromone[cur] ** alpha) * (heuristic[cur] ** beta)
                probs[visited] = 0
                total = probs.sum()
                if total <= 0:
                    choices = np.nonzero(~visited)[0]
                    nxt = int(rng.choice(choices))
                else:
                    nxt = int(rng.choice(n, p=probs / total))
                tour.append(nxt)
                visited[nxt] = True
            cost = sum(d[tour[i - 1], tour[i]] for i in range(n))
            tours.append(tour)
            costs.append(cost)
        pheromone *= decay
        idx = int(np.argmin(costs))
        best = min(best, costs[idx])
        for tour, cost in zip(tours, costs):
            for i in range(n):
                pheromone[tour[i - 1], tour[i]] += 1.0 / cost
    return best


def tsp_aco_score(heuristics, instances, **kw):
    """Mean best tour length from ACO driven by the candidate's heuristic matrix.

    Contract (ReEvo tsp_aco): ``heuristics(distance_matrix) -> matrix`` of
    attractiveness scores (larger = more attractive), same shape as the input.
    """
    out = []
    for k, points in enumerate(instances):
        d = distance_matrix(points)
        h = np.asarray(_call(heuristics, d.copy()), dtype=float)
        require(h.shape == d.shape and np.all(np.isfinite(h)), "heuristics must return a finite matrix of the same shape as the distance matrix")
        out.append(_aco_tsp(h, d, seed=k, **kw))
    return float(np.mean(out))


def _aco_cvrp(heuristic, d, demands, capacity, n_ants=20, n_iterations=30, seed=0):
    rng = rng_for(seed)
    n = len(d)
    pheromone = np.ones((n, n))
    heuristic = np.where(heuristic > 0, heuristic, 1e-9)
    best = math.inf
    for _ in range(n_iterations):
        routes_costs = []
        for _ in range(n_ants):
            visited = np.zeros(n, dtype=bool)
            visited[0] = True
            cur, rest, cost = 0, capacity, 0.0
            while not visited.all():
                mask = (~visited) & (demands <= rest)
                if not mask.any():
                    cost += d[cur, 0]
                    cur, rest = 0, capacity
                    continue
                probs = pheromone[cur] * heuristic[cur]
                probs[~mask] = 0
                total = probs.sum()
                nxt = int(rng.choice(n, p=probs / total)) if total > 0 else int(rng.choice(np.nonzero(mask)[0]))
                cost += d[cur, nxt]
                rest -= demands[nxt]
                visited[nxt] = True
                cur = nxt
            cost += d[cur, 0]
            routes_costs.append(cost)
        pheromone *= 0.9
        best = min(best, min(routes_costs))
        pheromone += 1.0 / min(routes_costs)  # global reinforcement (simplified)
    return best


def cvrp_aco_score(heuristics, instances, **kw):
    """Mean best CVRP cost from ACO driven by ``heuristics(distance_matrix, coordinates, demands, capacity)``."""
    out = []
    for k, instance in enumerate(instances):
        coords, demands, capacity = instance["coords"], instance["demands"], instance["capacity"]
        d = distance_matrix(coords)
        h = np.asarray(_call(heuristics, d.copy(), coords.copy(), demands.astype(float).copy(), float(capacity)), dtype=float)
        require(h.shape == d.shape and np.all(np.isfinite(h)), "heuristics must return a finite matrix of the same shape as the distance matrix")
        out.append(_aco_cvrp(h, d, demands, capacity, seed=k, **kw))
    return float(np.mean(out))
