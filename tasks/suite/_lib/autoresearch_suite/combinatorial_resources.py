"""Three-dimensional packing, facility location and constrained resource evaluations."""
from __future__ import annotations

from .combinatorial import (
    CandidateError,
    _call,
    distance_matrix,
    itertools,
    np,
    require,
    rng_for,
)

# ---------------------------------------------------------------------------
# Three-dimensional bin packing and container loading (DGA2D)
# ---------------------------------------------------------------------------

def box_instances(n_instances, n_boxes, seed, container=(100, 100, 100)):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        boxes = rng.integers(10, 50, size=(n_boxes, 3)).tolist()
        out.append({"boxes": [[int(v) for v in b] for b in boxes], "container": list(container)})
    return out


def _check_placements(placements, boxes, container):
    """Validate placements [(bin, x, y, z, w, h, d)] against the boxes; returns bins used and filled volume."""
    require(isinstance(placements, (list, tuple)) and len(placements) == len(boxes), "return one placement per box, in box order")
    W, H, D = container
    parsed = []
    for i, (p, box) in enumerate(zip(placements, boxes)):
        require(len(p) == 7, "each placement is (bin, x, y, z, w, h, d)")
        b, x, y, z, w, h, d = (int(p[0]),) + tuple(float(v) for v in p[1:])
        require(sorted([w, h, d]) == sorted(float(v) for v in box), f"box {i} dimensions must be a rotation of {box}")
        require(b >= 0 and x >= -1e-9 and y >= -1e-9 and z >= -1e-9 and x + w <= W + 1e-9 and y + h <= H + 1e-9 and z + d <= D + 1e-9, f"box {i} lies outside its container")
        parsed.append((b, x, y, z, w, h, d))
    for (b1, x1, y1, z1, w1, h1, d1), (b2, x2, y2, z2, w2, h2, d2) in itertools.combinations(parsed, 2):
        if b1 == b2 and x1 < x2 + w2 - 1e-9 and x2 < x1 + w1 - 1e-9 and y1 < y2 + h2 - 1e-9 and y2 < y1 + h1 - 1e-9 and z1 < z2 + d2 - 1e-9 and z2 < z1 + d1 - 1e-9:
            raise CandidateError("two boxes overlap inside the same container")
    bins = len({p[0] for p in parsed})
    volume = sum(p[4] * p[5] * p[6] for p in parsed)
    return bins, volume


def bin_packing_3d_score(pack, instances):
    """Mean number of containers used by ``pack(boxes, container) -> placements``. Lower is better."""
    counts = []
    for inst in instances:
        placements = _call(pack, [list(b) for b in inst["boxes"]], tuple(inst["container"]))
        bins, _ = _check_placements(placements, inst["boxes"], inst["container"])
        counts.append(bins)
    return float(np.mean(counts))


def container_loading_score(load, instances):
    """Mean fraction of the single container's volume filled by ``load(boxes, container) -> placements`` (bin index -1 = not loaded). Higher is better."""
    fractions = []
    for inst in instances:
        placements = _call(load, [list(b) for b in inst["boxes"]], tuple(inst["container"]))
        require(isinstance(placements, (list, tuple)) and len(placements) == len(inst["boxes"]), "return one placement per box (bin -1 to leave a box out)")
        loaded = [(p, b) for p, b in zip(placements, inst["boxes"]) if int(p[0]) >= 0]
        require(all(int(p[0]) == 0 for p, _ in loaded), "container loading uses a single container (bin 0)")
        _, volume = _check_placements([p for p, _ in loaded], [b for _, b in loaded], inst["container"]) if loaded else (0, 0.0)
        W, H, D = inst["container"]
        fractions.append(volume / (W * H * D))
    return float(np.mean(fractions))


# ---------------------------------------------------------------------------
# Capacitated facility location (A2DEPT)
# ---------------------------------------------------------------------------

def facility_location_instances(n_instances, n_facilities, n_customers, seed):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        f = rng.random((n_facilities, 2))
        c = rng.random((n_customers, 2))
        demands = rng.integers(5, 36, size=n_customers)
        capacities = rng.integers(int(demands.sum() / n_facilities * 1.5), int(demands.sum() / n_facilities * 3.0) + 1, size=n_facilities)
        open_cost = rng.uniform(50, 150, size=n_facilities)
        assign_cost = 100 * np.linalg.norm(c[:, None, :] - f[None, :, :], axis=2)
        out.append({"demands": demands, "capacities": capacities, "open_cost": open_cost, "assign_cost": assign_cost})
    return out


def facility_location_score(assign, instances):
    """Mean total cost of ``assign(demands, capacities, open_cost, assign_cost) -> facility index per customer``. Lower is better."""
    costs = []
    for inst in instances:
        a = _call(assign, inst["demands"].copy(), inst["capacities"].copy(), inst["open_cost"].copy(), inst["assign_cost"].copy())
        a = np.asarray(a).ravel()
        n_c, n_f = inst["assign_cost"].shape
        require(a.shape == (n_c,) and np.issubdtype(a.dtype, np.integer) and np.all((a >= 0) & (a < n_f)), "return one facility index per customer")
        load = np.bincount(a, weights=inst["demands"], minlength=n_f)
        require(np.all(load <= inst["capacities"] + 1e-9), "a facility's capacity is exceeded")
        opened = np.unique(a)
        costs.append(float(inst["open_cost"][opened].sum() + inst["assign_cost"][np.arange(n_c), a].sum()))
    return float(np.mean(costs))


# ---------------------------------------------------------------------------
# Electric vehicle routing with time windows (A2DEPT)
# ---------------------------------------------------------------------------

def evrptw_instances(n_instances, n_customers, n_stations, seed, capacity=100, battery=300.0, speed=1.0, recharge_rate=0.5):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        coords = rng.random((1 + n_customers + n_stations, 2)) * 100
        demands = np.concatenate([[0], rng.integers(5, 26, size=n_customers), np.zeros(n_stations, dtype=int)])
        ready = np.concatenate([[0.0], rng.uniform(0, 400, size=n_customers), np.zeros(n_stations)])
        due = np.concatenate([[1000.0], ready[1:1 + n_customers] + rng.uniform(100, 300, size=n_customers), np.full(n_stations, 1000.0)])
        service = np.concatenate([[0.0], np.full(n_customers, 10.0), np.zeros(n_stations)])
        out.append({"coords": coords, "demands": demands, "ready": ready, "due": due, "service": service,
                    "n_customers": n_customers, "stations": list(range(1 + n_customers, 1 + n_customers + n_stations)),
                    "capacity": capacity, "battery": battery, "speed": speed, "recharge_rate": recharge_rate, "horizon": 1000.0})
    return out


def evrptw_score(plan, instances):
    """Mean total distance of ``plan(instance) -> list of routes`` (node ids; depot 0 implicit; stations may be revisited). Lower is better."""
    totals = []
    for inst in instances:
        routes = _call(plan, {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in inst.items()})
        require(isinstance(routes, (list, tuple)), "return a list of routes")
        d = distance_matrix(inst["coords"])
        stations = set(inst["stations"])
        visited, total = [], 0.0
        for route in routes:
            route = [int(v) for v in route]
            require(all(0 < v < len(d) for v in route), "route nodes must be customers or stations (depot is implicit)")
            load = sum(inst["demands"][v] for v in route if v not in stations)
            require(load <= inst["capacity"], "vehicle capacity exceeded")
            time, energy, prev = 0.0, inst["battery"], 0
            for v in route:
                dist = d[prev, v]
                energy -= dist
                require(energy >= -1e-9, "battery depleted between nodes")
                time += dist / inst["speed"]
                if v in stations:
                    time += (inst["battery"] - energy) * inst["recharge_rate"]
                    energy = inst["battery"]
                else:
                    require(v not in visited, f"customer {v} served twice")
                    visited.append(v)
                    time = max(time, inst["ready"][v])
                    require(time <= inst["due"][v] + 1e-9, f"time window of customer {v} missed")
                    time += inst["service"][v]
                total += dist
                prev = v
            dist = d[prev, 0]
            require(energy - dist >= -1e-9, "battery depleted returning to the depot")
            require(time + dist / inst["speed"] <= inst["horizon"] + 1e-9, "route exceeds the planning horizon")
            total += dist
        require(len(visited) == inst["n_customers"], "every customer must be served exactly once")
        totals.append(total)
    return float(np.mean(totals))


# ---------------------------------------------------------------------------
# Box-constrained quadratic programs (CAE)
# ---------------------------------------------------------------------------

def quadratic_instances(n_instances, dim, seed):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        A = rng.standard_normal((dim, dim))
        Q = A @ A.T / dim + np.diag(rng.uniform(-1, 1, dim))  # indefinite in general
        out.append({"Q": (Q + Q.T) / 2, "c": rng.standard_normal(dim), "bounds": (-1.0, 1.0)})
    return out


def quadratic_program_score(optimize, instances, max_evals=20000):
    """Mean objective 0.5 x'Qx + c'x reached by ``optimize(Q, c, bounds, objective)`` within the evaluation budget. Lower is better."""
    values = []
    for inst in instances:
        Q, c, (lo, hi) = inst["Q"], inst["c"], inst["bounds"]
        counter = {"n": 0}

        def objective(x, Q=Q, c=c):
            counter["n"] += 1
            require(counter["n"] <= max_evals, "objective evaluation budget exhausted")
            x = np.asarray(x, dtype=float)
            return float(0.5 * x @ Q @ x + c @ x)

        x = np.asarray(_call(optimize, Q.copy(), c.copy(), (lo, hi), objective), dtype=float).ravel()
        require(x.shape == c.shape and np.all(np.isfinite(x)) and np.all(x >= lo - 1e-9) and np.all(x <= hi + 1e-9), "return a feasible point of the right dimension")
        values.append(float(0.5 * x @ Q @ x + c @ x))
    return float(np.mean(values))


def onemax_score(bits, n):
    """Number of ones in a binary string of length n (LMX OneMax). Higher is better."""
    try:
        s = "".join(str(int(b)) for b in (bits if not isinstance(bits, str) else list(bits)))
    except (TypeError, ValueError) as error:
        raise CandidateError(f"expected a binary sequence: {error}") from None
    require(len(s) == n and set(s) <= {"0", "1"}, f"expected a binary string of length {n}")
    return float(s.count("1"))
