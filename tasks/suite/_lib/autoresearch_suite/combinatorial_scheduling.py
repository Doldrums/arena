"""Flow-shop, job-shop and resource-constrained scheduling evaluations."""
from __future__ import annotations

from .combinatorial import (
    _call,
    np,
    require,
    rng_for,
)

# ---------------------------------------------------------------------------
# Scheduling (EoH flow shop, DGA2D job/flow/open shop, RCPSP, SALBP)
# ---------------------------------------------------------------------------

def flow_shop_instances(n_instances, n_jobs, n_machines, seed):
    rng = rng_for(seed)
    return [rng.integers(1, 100, size=(n_jobs, n_machines)) for _ in range(n_instances)]


def flow_shop_makespan(processing, order):
    n_machines = processing.shape[1]
    end = np.zeros(n_machines)
    for job in order:
        for m in range(n_machines):
            end[m] = max(end[m], end[m - 1] if m else 0) + processing[job, m]
    return float(end[-1])


def flow_shop_score(order_jobs, instances):
    """Mean makespan of the permutation returned by ``order_jobs(processing_times) -> sequence``. Lower is better."""
    out = []
    for processing in instances:
        order = _call(order_jobs, processing.copy())
        order = [int(j) for j in np.asarray(order).ravel()]
        require(sorted(order) == list(range(len(processing))), "order_jobs must return a permutation of all job indices")
        out.append(flow_shop_makespan(processing, order))
    return float(np.mean(out))


def job_shop_instances(n_instances, n_jobs, n_machines, seed, flexible=False, open_shop=False):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        jobs = []
        for _ in range(n_jobs):
            machines = rng.permutation(n_machines)
            ops = []
            for m in machines:
                if flexible:
                    k = int(rng.integers(1, min(3, n_machines) + 1))
                    options = rng.choice(n_machines, size=k, replace=False)
                    ops.append({"machines": {int(mm): int(rng.integers(1, 100)) for mm in options}})
                else:
                    ops.append({"machines": {int(m): int(rng.integers(1, 100))}})
            jobs.append(ops)
        out.append({"jobs": jobs, "n_machines": n_machines, "open_shop": open_shop})
    return out


def job_shop_score(dispatch, instances):
    """Mean makespan of an event-driven schedule driven by the candidate. Lower is better.

    Contract: ``dispatch(ready_operations, time) -> index`` chooses among ready
    operations, each a dict ``{"job", "op", "machine_options": {machine:
    duration}, "remaining_ops", "remaining_work"}`` whose listed machines are
    idle; the chosen operation runs on its cheapest idle machine option unless the
    candidate also returns ``(index, machine)``. Open-shop instances make every
    unscheduled operation of a job ready in any order.
    """
    out = []
    for instance in instances:
        jobs, n_machines, open_shop = instance["jobs"], instance["n_machines"], instance["open_shop"]
        machine_free = [0.0] * n_machines
        job_free = [0.0] * len(jobs)
        done = [set() for _ in jobs]
        remaining_work = [sum(min(op["machines"].values()) for op in job) for job in jobs]
        time_now = 0.0
        total_ops = sum(len(job) for job in jobs)
        scheduled = 0
        guard = 0
        while scheduled < total_ops:
            guard += 1
            require(guard < 20 * total_ops + 100, "schedule did not converge")
            ready = []
            for j, job in enumerate(jobs):
                if job_free[j] > time_now:
                    continue
                candidates = [k for k in range(len(job)) if k not in done[j]] if open_shop else ([len(done[j])] if len(done[j]) < len(job) else [])
                for k in candidates:
                    options = {m: dur for m, dur in job[k]["machines"].items() if machine_free[m] <= time_now}
                    if options:
                        ready.append({"job": j, "op": k, "machine_options": options, "remaining_ops": len(job) - len(done[j]), "remaining_work": remaining_work[j]})
            if not ready:
                future = [t for t in machine_free + job_free if t > time_now]
                require(future, "deadlock in schedule simulation")
                time_now = min(future)
                continue
            choice = _call(dispatch, ready, time_now)
            machine = None
            if isinstance(choice, (tuple, list)) and len(choice) == 2:
                choice, machine = choice
            require(isinstance(choice, (int, np.integer)) and 0 <= int(choice) < len(ready), "dispatch must return a ready-operation index")
            op = ready[int(choice)]
            if machine is None:
                machine = min(op["machine_options"], key=op["machine_options"].get)
            require(machine in op["machine_options"], "dispatch chose a machine that is not an idle option")
            duration = op["machine_options"][machine]
            finish = time_now + duration
            machine_free[machine] = finish
            job_free[op["job"]] = finish
            done[op["job"]].add(op["op"])
            remaining_work[op["job"]] -= min(jobs[op["job"]][op["op"]]["machines"].values())
            scheduled += 1
        out.append(max(machine_free))
    return float(np.mean(out))


def rcpsp_instances(n_instances, n_activities, n_resources, seed):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        durations = rng.integers(1, 10, size=n_activities)
        demands = rng.integers(0, 4, size=(n_activities, n_resources))
        capacities = np.full(n_resources, 6)
        predecessors = [sorted(set(int(p) for p in rng.choice(i, size=min(i, int(rng.integers(0, 3))), replace=False))) if i else [] for i in range(n_activities)]
        out.append({"durations": durations, "demands": demands, "capacities": capacities, "predecessors": predecessors})
    return out


def rcpsp_score(priority, instances):
    """Mean makespan of a serial schedule-generation scheme driven by ``priority(instance) -> scores``. Lower is better."""
    out = []
    for instance in instances:
        durations, demands, caps, preds = instance["durations"], instance["demands"], instance["capacities"], instance["predecessors"]
        n = len(durations)
        scores = np.asarray(_call(priority, {k: (v.copy() if hasattr(v, "copy") else list(v)) for k, v in instance.items()}), dtype=float).ravel()
        require(scores.shape == (n,) and np.all(np.isfinite(scores)), "priority must return one finite score per activity")
        horizon = int(np.sum(durations)) + 1
        usage = np.zeros((horizon + 1, len(caps)))
        start = [None] * n
        scheduled = set()
        while len(scheduled) < n:
            eligible = [i for i in range(n) if i not in scheduled and all(p in scheduled for p in preds[i])]
            i = max(eligible, key=lambda k: scores[k])
            earliest = max([start[p] + durations[p] for p in preds[i]] + [0])
            t = earliest
            while True:
                if np.all(usage[t:t + durations[i]] + demands[i] <= caps):
                    break
                t += 1
            usage[t:t + durations[i]] += demands[i]
            start[i] = t
            scheduled.add(i)
        out.append(max(start[i] + durations[i] for i in range(n)))
    return float(np.mean(out))


def salbp_instances(n_instances, n_tasks, seed):
    rng = rng_for(seed)
    out = []
    for _ in range(n_instances):
        times = rng.integers(1, 20, size=n_tasks)
        preds = [sorted(set(int(p) for p in rng.choice(i, size=min(i, int(rng.integers(0, 2))), replace=False))) if i else [] for i in range(n_tasks)]
        out.append({"times": times, "predecessors": preds, "cycle_time": 40})
    return out


def salbp_score(priority, instances):
    """Mean number of stations opened by a station-oriented assignment driven by ``priority(instance) -> scores``. Lower is better."""
    out = []
    for instance in instances:
        times, preds, cycle = instance["times"], instance["predecessors"], instance["cycle_time"]
        n = len(times)
        scores = np.asarray(_call(priority, {"times": times.copy(), "predecessors": [list(p) for p in preds], "cycle_time": cycle}), dtype=float).ravel()
        require(scores.shape == (n,) and np.all(np.isfinite(scores)), "priority must return one finite score per task")
        assigned = set()
        stations = 0
        while len(assigned) < n:
            stations += 1
            load = 0
            while True:
                eligible = [i for i in range(n) if i not in assigned and all(p in assigned for p in preds[i]) and load + times[i] <= cycle]
                if not eligible:
                    break
                i = max(eligible, key=lambda k: scores[k])
                assigned.add(i)
                load += times[i]
        out.append(stations)
    return float(np.mean(out))
