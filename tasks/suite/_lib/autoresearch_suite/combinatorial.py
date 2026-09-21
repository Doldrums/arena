"""Combinatorial-optimization heuristic-design families (recreated protocols).

Each family defines a documented candidate contract in the style of FunSearch,
EoH, ReEvo and LLM4AD (a small heuristic function that the search evolves), a
deterministic instance generator seeded per task, and a scorer. Instances are
generated locally and are **not** the papers' benchmark instances, so scores
are comparable between runs of this suite, not with published numbers. Where a
paper's contract is known it is followed (``priority(item, bins)`` for online
bin packing, ``select_next_node`` for constructive TSP/CVRP, ``heuristics(...)``
for ACO, ``update_edge_distance`` for guided local search).
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from .runtime import CandidateError, require


def rng_for(seed):
    return np.random.default_rng(seed)


def _call(function, *args):
    try:
        return function(*args)
    except CandidateError:
        raise
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"candidate heuristic raised {type(error).__name__}: {error}") from None


# ---------------------------------------------------------------------------
# Online bin packing (FunSearch / EoH / MCTS-AHD / ReEvo / MEoH / EoH-S / RedAHD / HSEvo)
# ---------------------------------------------------------------------------

def weibull_bin_packing_instances(n_instances=5, n_items=1000, capacity=100, seed=0):
    """Weibull(k=3, scale=45) item sizes rounded up and clipped to [1, capacity], as in FunSearch."""
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        items = np.clip(np.ceil(rng.weibull(3.0, size=n_items) * 45.0), 1, capacity).astype(int)
        out.append({"capacity": capacity, "items": items.tolist(), "num_items": n_items})
    return out


def online_bin_packing_score(priority, instances):
    """Mean excess of bins used over the L1 lower bound (percent). Lower is better."""
    excess = []
    for instance in instances:
        capacity, items = instance["capacity"], instance["items"]
        bins = np.full(len(items), float(capacity))
        for item in items:
            valid = np.nonzero(bins - item >= 0)[0]
            require(len(valid) > 0, "no bin can hold an item (internal error)")
            scores = np.asarray(_call(priority, float(item), bins[valid]), dtype=float).ravel()
            require(scores.shape == (len(valid),), f"priority must return one score per valid bin ({len(valid)}), got shape {scores.shape}")
            require(np.all(np.isfinite(scores)), "priority returned NaN or infinite scores")
            best = valid[int(np.argmax(scores))]
            bins[best] -= item
        used = int(np.sum(bins != capacity))
        lower = math.ceil(sum(items) / capacity)
        excess.append((used - lower) / lower * 100.0)
    return float(np.mean(excess))


# ---------------------------------------------------------------------------
# Constructive TSP / CVRP / knapsack (EoH / LLM4AD / MCTS-AHD / AEL / MEoH)
# ---------------------------------------------------------------------------

def euclidean_instances(n_instances, n_nodes, seed, dim=2):
    rng = rng_for(seed)
    return [rng.random((n_nodes, dim)) for _ in range(n_instances)]


def distance_matrix(points):
    diff = points[:, None, :] - points[None, :, :]
    return np.sqrt(np.sum(diff * diff, axis=2))


def tour_length(points, tour):
    d = distance_matrix(points)
    return float(sum(d[tour[i - 1], tour[i]] for i in range(len(tour))))


def tsp_constructive_score(select_next_node, instances):
    """Mean tour length of the nearest-neighbourhood construction driven by the candidate.

    Contract (LLM4AD/EoH): ``select_next_node(current_node, destination_node,
    unvisited_nodes, distance_matrix) -> int`` where ``unvisited_nodes`` is a
    numpy array of node ids.
    """
    lengths = []
    for points in instances:
        n = len(points)
        d = distance_matrix(points)
        route = [0]
        unvisited = set(range(1, n))
        current = 0
        while unvisited:
            candidates = np.array(sorted(unvisited))
            nxt = _call(select_next_node, current, 0, candidates, d)
            require(isinstance(nxt, (int, np.integer)) and int(nxt) in unvisited, "select_next_node must return an unvisited node id")
            nxt = int(nxt)
            route.append(nxt)
            unvisited.remove(nxt)
            current = nxt
        lengths.append(tour_length(points, route))
    return float(np.mean(lengths))


def cvrp_instances(n_instances, n_customers, seed, capacity=50):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        coords = rng.random((n_customers + 1, 2))  # node 0 is the depot
        demands = np.concatenate(([0], rng.integers(1, 10, size=n_customers)))
        out.append({"coords": coords, "demands": demands, "capacity": capacity})
    return out


def cvrp_constructive_score(select_next_node, instances):
    """Mean total route length of a capacity-aware construction driven by the candidate.

    Contract (LLM4AD cvrp_construct): ``select_next_node(current_node, depot,
    unvisited_nodes, rest_capacity, demands, distance_matrix) -> int``. Returning
    the depot (0) closes the current route.
    """
    totals = []
    for instance in instances:
        coords, demands, capacity = instance["coords"], instance["demands"], instance["capacity"]
        d = distance_matrix(coords)
        unvisited = set(range(1, len(coords)))
        current, rest, total = 0, capacity, 0.0
        steps = 0
        while unvisited:
            feasible = np.array(sorted(i for i in unvisited if demands[i] <= rest))
            if len(feasible) == 0:
                total += d[current, 0]
                current, rest = 0, capacity
                continue
            nxt = _call(select_next_node, current, 0, feasible, rest, demands, d)
            require(isinstance(nxt, (int, np.integer)), "select_next_node must return an integer node id")
            nxt = int(nxt)
            if nxt == 0:
                require(current != 0, "returned to the depot while already there")
                total += d[current, 0]
                current, rest = 0, capacity
            else:
                require(nxt in unvisited and demands[nxt] <= rest, "select_next_node must return a feasible unvisited customer")
                total += d[current, nxt]
                rest -= demands[nxt]
                unvisited.remove(nxt)
                current = nxt
            steps += 1
            require(steps < 10 * len(coords), "construction did not terminate")
        total += d[current, 0]
        totals.append(total)
    return float(np.mean(totals))


def knapsack_instances(n_instances, n_items, seed):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        weights = rng.random(n_items)
        values = rng.random(n_items)
        out.append({"weights": weights, "values": values, "capacity": 12.5})
    return out


def knapsack_constructive_score(select_next_item, instances):
    """Mean total value of a greedy construction driven by the candidate. Higher is better.

    Contract (MCTS-AHD kp_construct): ``select_next_item(remaining_capacity,
    remaining_weights, remaining_values) -> int`` returns the index (into the
    remaining arrays) of the next item to pack or -1 to stop.
    """
    totals = []
    for instance in instances:
        weights, values, capacity = instance["weights"].copy(), instance["values"].copy(), instance["capacity"]
        value = 0.0
        while len(weights):
            fits = weights <= capacity
            if not np.any(fits):
                break
            index = _call(select_next_item, float(capacity), weights[fits], values[fits])
            require(isinstance(index, (int, np.integer)), "select_next_item must return an integer index or -1")
            index = int(index)
            if index < 0:
                break
            require(0 <= index < int(np.sum(fits)), "index out of range of the feasible items")
            real = np.nonzero(fits)[0][index]
            capacity -= weights[real]
            value += values[real]
            weights = np.delete(weights, real)
            values = np.delete(values, real)
        totals.append(value)
    return float(np.mean(totals))


# ---------------------------------------------------------------------------
from .combinatorial_routing import (
    _aco_cvrp,
    _aco_tsp,
    _nearest_neighbour,
    _two_opt,
    cvrp_aco_score,
    tsp_aco_score,
    tsp_gls_score,
)


from .combinatorial_packing import (
    mkp_aco_score,
    mkp_instances,
    offline_bin_packing_aco_score,
    offline_bin_packing_instances,
    orienteering_aco_score,
    orienteering_instances,
)


from .combinatorial_scheduling import (
    flow_shop_instances,
    flow_shop_makespan,
    flow_shop_score,
    job_shop_instances,
    job_shop_score,
    rcpsp_instances,
    rcpsp_score,
    salbp_instances,
    salbp_score,
)


from .combinatorial_constructions import (
    _primes_up_to,
    admissible_tuple_size,
    cap_set_greedy,
    graph_instances,
    maxcut_score,
    mis_greedy_score,
    no_isosceles_maximal,
    no_isosceles_size,
    sat_instances,
    sat_score,
    verify_cap_set,
)


from .combinatorial_resources import (
    _check_placements,
    bin_packing_3d_score,
    box_instances,
    container_loading_score,
    evrptw_instances,
    evrptw_score,
    facility_location_instances,
    facility_location_score,
    onemax_score,
    quadratic_instances,
    quadratic_program_score,
)
