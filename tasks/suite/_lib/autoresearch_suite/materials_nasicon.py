"""Pinned NASICON LCE transport, with exact finite-event tagged-ion moments.

Numerical inputs belong to kMCpy. The algorithms below are independent
implementations; no upstream implementation code is copied. Species states are
Na=0, vacancy=1 and Si=0, P=1, as in kmcpy.active_site_order.v1.
"""
from __future__ import annotations

import copy
import functools
import itertools
import json
import math
import time

import numpy as np

KB_MEV_K = 8.617333262145e-2


def lce_scalar(block, local_states):
    """Independent literal sum of decorated cluster products (NOT means)."""
    lce, parameters = block["lce"], block["parameters"]
    value = float(parameters["empty_cluster"])
    for coefficient, orbit, basis_orbit in zip(parameters["keci"], lce["cluster_site_indices"], lce["correlation_basis_indices"], strict=True):
        correlation = 0.0
        for cluster, basis in zip(orbit, basis_orbit, strict=True):
            product = 1.0
            for site, basis_index in zip(cluster, basis, strict=True):
                product *= lce["site_basis_values"][site][local_states[site]][basis_index]
            correlation += product
        value += coefficient * correlation
    return value


def rates_scalar(model, states, temperature):
    """Literal source equation, evaluated separately from vectorized seed rates."""
    result = np.zeros(len(model["edges"]))
    for event_id, event in enumerate(model["events"]):
        a, b = event["mobile_ion_indices"]
        if states[a] == states[b]:
            continue
        direction = 1 if (states[a], states[b]) == (0, 1) else -1
        local = [int(states[i]) for i in event["local_env_indices"]]
        barrier = lce_scalar(model["kra"], local) + direction * lce_scalar(model["site"], local) / 2
        if not math.isfinite(barrier) or barrier <= 0:
            raise ValueError("Source LCE produces an invalid barrier")
        result[2 * event_id + (direction < 0)] = model["attempt_hz"] * math.exp(-barrier / (KB_MEV_K * temperature))
    return result


def mobile_states(model):
    n = model["mobile_count"]
    for vacancies in itertools.combinations(range(n), model["vacancy_count"]):
        state = np.zeros(n, dtype=int)
        state[list(vacancies)] = 1
        yield tuple(state.tolist())


@functools.lru_cache(maxsize=8)
def rate_table(model_json, temperature, scalar=False):
    model = json.loads(model_json)
    mobile = list(mobile_states(model))
    states = np.array([list(s) + model["framework_states"] for s in mobile], dtype=int)
    if scalar:
        rates = np.array([rates_scalar(model, row, temperature) for row in states])
    else:
        local = states[:, np.array([e["local_env_indices"] for e in model["events"]])]
        energies = []
        for name in ("kra", "site"):
            block = model[name]; lce = block["lce"]
            energy = np.full(local.shape[:2], float(block["parameters"]["empty_cluster"]))
            basis = np.array(lce["site_basis_values"])
            for k, orbit, decorations in zip(block["parameters"]["keci"], lce["cluster_site_indices"], lce["correlation_basis_indices"], strict=True):
                if k == 0:
                    continue
                indices, decorated = np.array(orbit), np.array(decorations)
                products = np.prod(basis[indices, local[:, :, indices], decorated], axis=-1)
                energy += k * products.sum(axis=-1)
            energies.append(energy)
        pairs = np.array([e["mobile_ion_indices"] for e in model["events"]])
        rates = np.zeros((len(states), len(model["edges"])))
        for orientation, sign in ((0, 1), (1, -1)):
            allowed = (states[:, pairs[:, 0]] == orientation) & (states[:, pairs[:, 1]] == 1 - orientation)
            barriers = energies[0] + sign * energies[1] / 2
            if np.any(barriers[allowed] <= 0):
                raise ValueError("Source LCE produces an invalid barrier")
            rates[:, orientation::2] = np.where(allowed, model["attempt_hz"] * np.exp(-barriers / (KB_MEV_K * temperature)), 0)
    return mobile, {s: i for i, s in enumerate(mobile)}, rates


def nasicon_seed(lattice, occupancies, barrier_model, temperature, budget):
    model = barrier_model["nasicon_lce"]
    _, indices, rates = rate_table(json.dumps(model, sort_keys=True), temperature)
    state = list(occupancies[:model["mobile_count"]])
    rng = np.random.default_rng(budget["seed"])
    history = []
    for _ in range(budget["events"]):
        r = rates[indices[tuple(state)]]; total = r.sum()
        wait = float(rng.exponential(1 / total))
        edge_id = int(np.searchsorted(np.cumsum(r), rng.random() * total, side="right"))
        edge = model["edges"][edge_id]
        state[edge["from"]], state[edge["to"]] = 1, 0
        history.append([wait, edge_id])
    return history


def exact_moments(model, initial_states, temperature, event_counts):
    """Exact embedded-chain first/second displacement moments and mean time.

    Enumerates every two-vacancy configuration and every occupied tagged site.
    Sparse propagation includes periodic winding vectors on individual hops.
    It uses scalar LCE rates, independently from the seed's vectorized rates.
    No sampling or fitted diffusion constant enters this reference.
    """
    from scipy.sparse import csr_matrix
    mobile, mobile_index, all_rates = rate_table(json.dumps(model, sort_keys=True), temperature, True)
    tagged = [(s, tag) for s in mobile for tag, state in enumerate(s) if state == 0]
    index = {state: i for i, state in enumerate(tagged)}
    rows, cols, probability, increments = [], [], [], []
    expected_wait = np.zeros(len(tagged))
    for i, (states, tag) in enumerate(tagged):
        rates = all_rates[mobile_index[states]]; total = rates.sum()
        expected_wait[i] = 1 / total
        for edge_id in np.flatnonzero(rates):
            edge = model["edges"][edge_id]
            updated = list(states); updated[edge["from"]], updated[edge["to"]] = 1, 0
            moved = tag == edge["from"]
            next_tag = edge["to"] if moved else tag
            rows.append(i); cols.append(index[(tuple(updated), next_tag)])
            probability.append(rates[edge_id] / total)
            increments.append(edge["displacement_angstrom"] if moved else [0., 0., 0.])
    probability = np.array(probability); increments = np.array(increments)
    shape = (len(tagged), len(tagged))
    transition = csr_matrix((probability, (rows, cols)), shape=shape).T.tocsr()
    derivative = [csr_matrix((probability * increments[:, k], (rows, cols)), shape=shape).T.tocsr() for k in range(3)]
    square = csr_matrix((probability * np.sum(increments ** 2, axis=1), (rows, cols)), shape=shape).T.tocsr()
    mass = np.zeros(len(tagged))
    start = tuple(initial_states[:model["mobile_count"]])
    for tag, state in enumerate(start):
        if state == 0:
            mass[index[(start, tag)]] = 1 / start.count(0)
    first = np.zeros((len(tagged), 3)); second = np.zeros(len(tagged)); duration = 0.
    result = {}
    for step in range(1, max(event_counts) + 1):
        duration += float(mass @ expected_wait)
        second_new = transition @ second + square @ mass
        first_new = transition @ first
        for axis in range(3):
            second_new += 2 * (derivative[axis] @ first[:, axis])
            first_new[:, axis] += derivative[axis] @ mass
        mass, first, second = transition @ mass, first_new, second_new
        if step in event_counts:
            result[str(step)] = {"mean_msd_angstrom2": float(second.sum()), "mean_duration_s": duration,
                "apparent_diffusivity_m2_s": float(second.sum() * 1e-20 / (6 * duration)),
                "probability_mass_error": abs(float(mass.sum()) - 1), "tagged_states": len(tagged)}
    return result


def nasicon_score(fn, case, params):
    from scipy.stats import kstest
    model = case["nasicon_lce"]
    events_count = params.get("events", case["reference_event_count"])
    if events_count != case["reference_event_count"]:
        raise ValueError("NASICON event budget must match its exact finite-horizon reference")
    mobile, state_indices, rates = rate_table(json.dumps(model, sort_keys=True), case["temperature_k"], True)
    seeds = params.get("seeds", list(range(130, 194)))
    waits, quantiles, msds, durations = [], [], [], []
    elapsed = 0.
    for seed in seeds:
        budget = {"events": events_count, "seed": seed}
        started = time.perf_counter()
        history = np.asarray(fn(copy.deepcopy(case["lattice"]), list(case["occupancies"]), {"kind": "nasicon_lce", "nasicon_lce": copy.deepcopy(model)}, case["temperature_k"], budget), float)
        elapsed += time.perf_counter() - started
        if history.shape != (events_count, 2) or not np.isfinite(history).all():
            raise ValueError("Invalid NASICON kMC history shape or nonfinite event")
        state = list(case["occupancies"][:model["mobile_count"]])
        labels = np.full(model["mobile_count"], -1, int); labels[np.array(state) == 0] = np.arange(state.count(0))
        displacement = np.zeros((state.count(0), 3)); duration = 0.
        rng = np.random.default_rng(seed + 99000)
        for wait, edge_id in history:
            if wait <= 0 or edge_id != int(edge_id) or not 0 <= edge_id < len(model["edges"]):
                raise ValueError("Invalid NASICON waiting time or edge index")
            edge_id = int(edge_id)
            r = rates[state_indices[tuple(state)]]; total = r.sum()
            if r[edge_id] <= 0:
                raise ValueError("NASICON move violates species encoding, exclusion or adjacency")
            quantiles.append(float((r[:edge_id].sum() + rng.random() * r[edge_id]) / total))
            waits.append(float(wait * total))
            edge = model["edges"][edge_id]
            displacement[labels[edge["from"]]] += edge["displacement_angstrom"]
            labels[edge["to"]], labels[edge["from"]] = labels[edge["from"]], -1
            state[edge["from"]], state[edge["to"]] = 1, 0
            duration += wait
        durations.append(duration); msds.append(float(np.mean(np.sum(displacement ** 2, axis=1))))
    if kstest(waits, "expon").pvalue <= 1e-5 or kstest(quantiles, "uniform").pvalue <= 1e-5:
        raise ValueError("NASICON event selection or waiting-time law disagrees with the occupation-dependent LCE")
    durations, msds = np.array(durations), np.array(msds)
    ratio = float(msds.mean() / (6 * durations.mean()))
    standard_error = float(np.std(msds - 6 * ratio * durations, ddof=1) / (6 * durations.mean() * math.sqrt(len(seeds)))) * 1e-20
    reference = case["exact_reference"][str(events_count)]
    estimate = ratio * 1e-20
    if abs(estimate - reference["apparent_diffusivity_m2_s"]) > 4 * standard_error + 1e-12 * reference["apparent_diffusivity_m2_s"]:
        raise ValueError("NASICON transport disagrees with exact finite-state displacement moments")
    # Independently check the clock against an exact mean, not only its local law.
    clock_se = float(durations.std(ddof=1) / math.sqrt(len(seeds)))
    if abs(durations.mean() - reference["mean_duration_s"]) > 4 * clock_se:
        raise ValueError("NASICON duration disagrees with exact finite-state residence times")
    score = elapsed * (standard_error / reference["apparent_diffusivity_m2_s"]) ** 2
    return score, {"finite_horizon_diffusivity_m2_s": estimate, "standard_error_m2_s": standard_error,
        "exact_reference_diffusivity_m2_s": reference["apparent_diffusivity_m2_s"], "events_per_replica": events_count,
        "replicas": len(seeds), "reference_tagged_states": reference["tagged_states"], "candidate_seconds": elapsed,
        "scope": "Source NASICON 2x1x1 fixed-Si framework; finite-event tagged-ion MSD/(6 E[time]); not bulk or asymptotic conductivity"}
