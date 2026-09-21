"""Recorded island lifecycle and conditional scheduler forecasts, without an engine.

Membership is storage state; retirement only removes an island from scheduling.
This projection never invents geometry, dispatches, migration edges or future births.
"""
from __future__ import annotations

from collections import deque
import math

MAX_EVENTS = 120
MAX_FRAMES = 60
MAX_ISLANDS = 64
MAX_FRAME_MEMBERS = 512
MAX_MIGRATIONS = 120
SUPPORTED_CONTRACTS = {f"espalier-3.{version}" for version in range(2, 7)}


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _int(value):
    return value if type(value) is int and value >= 0 else None


def _number(value):
    if type(value) in (int, float):
        try:
            return value if math.isfinite(value) else None
        except OverflowError:
            pass
    return None


def _id(value):
    return value if isinstance(value, str) and 0 < len(value) <= 128 else None


def _ids(value):
    return list(dict.fromkeys(item for item in _list(value) if _int(item) is not None))[:MAX_ISLANDS]


def _counter(mapping, island):
    mapping = _dict(mapping)
    return _int(mapping.get(str(island), mapping.get(island)))


def _event_id(row, index):
    segment, sequence = _id(row.get("segment_id")), _int(row.get("event_seq"))
    return f"{segment}:{sequence}" if segment and sequence is not None else f"legacy:{index}"


def _at(row):
    value = row.get("timestamp")
    return value if isinstance(value, str) and len(value) <= 64 else None


def _programs(checkpoint):
    value = _dict(checkpoint.get("db")).get("programs")
    return {p["id"]: p for p in (value.values() if isinstance(value, dict) else _list(value))
            if isinstance(p, dict) and _id(p.get("id"))}


def _checkpoint_index(checkpoint, rows):
    anchor = _dict(_dict(checkpoint.get("provenance")).get("journal_anchor"))
    if not _id(anchor.get("segment_id")) or _int(anchor.get("event_seq")) is None:
        return None
    return next((i for i in range(len(rows) - 1, -1, -1)
                 if (rows[i].get("segment_id"), rows[i].get("event_seq")) ==
                    (anchor["segment_id"], anchor["event_seq"])), None)


def _spawn_counters(checkpoint, rows, anchor_index, supported):
    """Only replay the explicitly recorded counter transitions after an anchor."""
    evaluations = _int(checkpoint.get("B_evals"))
    reset = _int(checkpoint.get("_last_improve_eval"))
    source = "checkpoint" if evaluations is not None else "unavailable"
    pending = False
    if anchor_index is not None and supported and evaluations is not None:
        for row in rows[anchor_index + 1:]:
            event = row.get("event")
            count = _int(row.get("B_evals"))
            if event == "population" and count is not None and count > evaluations:
                pending = True  # admission precedes its iteration outcome
            elif event == "iteration":
                if count is None or count < evaluations:
                    reset = None
                    continue
                evaluations, pending, source = count, False, "checkpoint+journal"
                if row.get("is_pop_event") is True:
                    reset = evaluations
                elif _id(row.get("child_id")) and row.get("is_pop_event") is not False:
                    reset = None
            elif event == "decision" and row.get("policy") == "dynamic_islands" and row.get("action") == "spawn":
                # Spawn logs only after resetting this counter. B has not changed
                # during the auxiliary portfolio evaluation.
                reset, source = (None if pending else evaluations), "checkpoint+journal"
        if pending:
            reset = None
    if reset is not None and evaluations is not None and reset > evaluations:
        reset = None
    return evaluations, reset, source


def _next_cut(checkpoint, config, programs, supported, stale):
    schedule = _dict(checkpoint.get("schedule"))
    context = dict(iteration=_int(checkpoint.get("iteration_no")),
                   evaluations=_int(checkpoint.get("B_evals")), stale=stale,
                   source="checkpoint")
    result = dict(status="unknown", milestone_evaluations=None, evaluations_remaining=None,
        ranking=[], cut=[], protected=[], survivors=[], min_fair_dispatches=None,
        forecast_as_of=context, reason="A complete saved scheduler state is required.")
    policy = schedule.get("policy") or config.get("schedule_policy")
    if policy == "round_robin":
        result.update(status="disabled", reason="Round-robin scheduling does not retire islands.")
        return result
    if policy != "sh" or not supported:
        return result
    horizon = config.get("schedule_horizon") if config.get("budget") is None else config.get("budget")
    fractions = config.get("milestone_fracs")
    if _number(horizon) is None or horizon <= 0 or not isinstance(fractions, list) or any(
            _number(f) is None or f <= 0 or f > 1 for f in fractions):
        return result
    fired = checkpoint.get("milestones_fired")
    if not isinstance(fired, list) or any(_int(item) is None for item in fired):
        return result
    milestones = sorted(set(max(1, int(round(f * horizon))) for f in fractions))
    remaining = [m for m in milestones if m not in fired]
    if not remaining:
        result.update(status="complete", reason="All configured SH milestones have fired; no later cut is scheduled.")
        return result
    result["milestone_evaluations"] = remaining[0]
    if context["evaluations"] is not None:
        result["evaluations_remaining"] = max(0, remaining[0] - context["evaluations"])
    alive = _ids(schedule.get("survivors"))
    fair = _int(schedule.get("min_fair_evals"))
    raw_islands = {i.get("idx"): i for i in _list(_dict(checkpoint.get("db")).get("islands"))
                   if isinstance(i, dict) and _int(i.get("idx")) is not None}
    best = {i: _number(_dict(programs.get(_id(_dict(raw_islands.get(i)).get("best_id")))).get("score"))
            for i in alive}
    if (not alive or fair is None or any(best[i] is None or _counter(schedule.get("saturation_counter"), i) is None
            or _counter(schedule.get("dispatched"), i) is None for i in alive)):
        return result
    ranking = sorted(sorted(alive), key=lambda i: (best[i], -_counter(schedule.get("saturation_counter"), i)), reverse=True)
    split = (len(ranking) + 1) // 2
    proposed = ranking[split:]
    protected = [i for i in proposed if _counter(schedule.get("dispatched"), i) < fair]
    result.update(status="conditional", ranking=ranking, cut=[i for i in proposed if i not in protected],
        protected=protected, survivors=ranking[:split] + protected, min_fair_dispatches=fair,
        reason="If saved scores and dispatch counts were unchanged at the milestone. Higher score wins, then fewer saturation events, then island ID. Fairness uses dispatches, not successful evaluations.")
    return result


def dynamics_view(checkpoint, rows, start, population):
    checkpoint, start = _dict(checkpoint), _dict(start)
    rows = [r for r in _list(rows) if isinstance(r, dict)]
    config = _dict(start.get("config")) or _dict(checkpoint.get("config"))
    contract = start.get("engine_contract") or _dict(checkpoint.get("identity")).get("engine_contract")
    supported = contract in SUPPORTED_CONTRACTS if isinstance(contract, str) else False
    schedule, programs = _dict(checkpoint.get("schedule")), _programs(checkpoint)
    anchor_index = _checkpoint_index(checkpoint, rows)
    cp_iteration, cp_evals = _int(checkpoint.get("iteration_no")), _int(checkpoint.get("B_evals"))
    later_rows = rows[anchor_index + 1:] if anchor_index is not None else rows
    changed = any(r.get("event") in {"iteration", "population", "sh_cut"}
        or r.get("event") == "decision" and r.get("policy") in {"dynamic_islands", "controller", "preset_weights"}
        for r in later_rows)
    stale = changed if anchor_index is not None else (True if cp_iteration is not None and
        any((_int(r.get("iteration_no")) or 0) > cp_iteration for r in rows) else None)
    evaluations, reset, counter_source = _spawn_counters(checkpoint, rows, anchor_index, supported)
    if evaluations is None and supported:
        for index, row in enumerate(rows):
            counters = _dict(row.get("counters"))
            if (row.get("event") == "run_start" and row.get("resumed") is False
                    and _int(counters.get("B_evals")) == 0 and _int(counters.get("_last_improve_eval")) == 0):
                evaluations, reset, _ = _spawn_counters(counters, rows, index, supported)
                counter_source = "fresh_run_start+journal"
                break
    initial = _int(config.get("num_islands"))
    fresh = any(r.get("event") == "run_start" and r.get("resumed") is False for r in rows)
    islands, born, retired, statuses = {}, {}, {}, {}
    if fresh and initial is not None:
        for i in range(min(initial, MAX_ISLANDS)):
            islands[i] = dict(id=i, best_score=None, member_count=None, member_ids=None)
            born[i] = dict(kind="initial", event_id=None)
            statuses[i] = "active"
    events, frames = deque(maxlen=MAX_EVENTS), deque(maxlen=MAX_FRAMES)
    event_count = frame_count = 0
    last_iteration = last_evals = None

    def add_event(item):
        nonlocal event_count
        events.append(item)
        event_count += 1

    def frame(row, index, source):
        nonlocal frame_count
        remaining = MAX_FRAME_MEMBERS
        content = []
        for i in sorted(islands)[:MAX_ISLANDS]:
            item = dict(islands[i], status=statuses.get(i, "unknown"))
            members = item.get("member_ids")
            if isinstance(members, list):
                item["member_ids"] = members[:remaining]
                item["members_truncated"] = len(members) > remaining
                remaining = max(0, remaining - len(item["member_ids"]))
            content.append(item)
        frames.append(dict(id=_event_id(row, index), at=_at(row), iteration=last_iteration,
            evaluations=last_evals, source=source, islands=content))
        frame_count += 1

    for index, row in enumerate(rows):
        ident, event = _event_id(row, index), row.get("event")
        if _int(row.get("iteration_no")) is not None:
            last_iteration = row["iteration_no"]
        if _int(row.get("B_evals")) is not None:
            last_evals = row["B_evals"]
        common = dict(id=ident, at=_at(row), iteration=last_iteration, evaluations=last_evals, source="journal")
        if event == "population" and isinstance(row.get("islands"), list):
            for raw in row["islands"][:MAX_ISLANDS]:
                if not isinstance(raw, dict) or _int(raw.get("idx")) is None:
                    continue
                i = raw["idx"]
                members = ([_id(m[0]) for m in raw["members"] if isinstance(m, list) and m and _id(m[0])]
                           if isinstance(raw.get("members"), list) else None)
                previous = islands.get(i, {}).get("member_ids")
                if members is not None and previous is not None:
                    before, after = set(previous), set(members)
                    arrived, departed = sorted(after - before), sorted(before - after)
                    if arrived or departed:
                        add_event(dict(common, id=ident + f":members:{i}", type="membership", island=i,
                            arrived_ids=arrived[:32], departed_ids=departed[:32],
                            arrived_count=len(arrived), departed_count=len(departed)))
                islands[i] = dict(id=i, best_score=_number(raw.get("best")), member_count=_int(raw.get("n")), member_ids=members)
            frame(row, index, "journal_population")
        elif event == "sh_cut":
            cuts, protected = _ids(row.get("cut")), _ids(row.get("protected"))
            for i in _ids(row.get("ranking")):
                islands.setdefault(i, dict(id=i, best_score=None, member_count=None, member_ids=None))
                statuses[i] = "retired" if i in cuts else "active"
                if i in cuts:
                    retired[i] = ident
                elif (_int(row.get("migrations")) or 0) > 0:
                    # SH logs after copying elites. Its aggregate count cannot
                    # reveal which survivor received which new program IDs.
                    islands[i].update(member_ids=None, member_count=None,
                                      membership_stale=True, best_score_stale=True)
            add_event(dict(common, type="sh_cut", cut=cuts, protected=protected,
                ranking=_ids(row.get("ranking")), milestone_evaluations=_int(row.get("milestone")),
                migration_count=_int(row.get("migrations")), migration_targets_known=False))
            frame(row, index, "journal_lifecycle")
        elif event == "decision" and row.get("policy") == "dynamic_islands" and row.get("action") == "spawn":
            i = _int(row.get("island"))
            if i is not None and len(islands) < MAX_ISLANDS:
                islands.setdefault(i, dict(id=i, best_score=None, member_count=None, member_ids=None))
                born[i], statuses[i] = dict(kind="spawn", event_id=ident), "active"
                add_event(dict(common, type="spawn", island=i, lifetime_islands=_int(row.get("n_islands")),
                    seeded=row.get("seeded") if type(row.get("seeded")) is bool else None,
                    stall_evaluations=_int(row.get("stall"))))
                frame(row, index, "journal_lifecycle")
        elif event == "decision" and row.get("policy") == "initialization" and row.get("action") == "seed_program":
            i, pid = _int(row.get("island")), _id(row.get("program_id"))
            if i is not None and pid and len(islands) <= MAX_ISLANDS:
                islands[i] = dict(id=i, best_score=_number(row.get("score")), member_count=1, member_ids=[pid])
                born[i] = dict(kind="initial", event_id=ident)
                statuses[i] = "active"
                add_event(dict(common, type="seed", island=i, program_id=pid))
                frame(row, index, "journal_initialization")
        elif (event == "iteration" and (_id(row.get("child_id")) or _id(row.get("measurement_program_id")))
              or event == "decision" and row.get("policy") == "portfolio_seed" and row.get("ok") is True):
            i = _int(row.get("island"))
            if i in islands:
                # An admission may also evict another member. Without a recorded
                # membership snapshot, seed IDs alone are not the current set.
                islands[i]["member_count"] = islands[i]["member_ids"] = None
                if _number(row.get("island_best")) is not None:
                    islands[i]["best_score"] = row["island_best"]

    # Use the membership snapshot selected by population_view for the current
    # frame. Lifecycle state can be newer; its separate provenance stays visible.
    for item in _list(population.get("islands"))[:MAX_ISLANDS]:
        i = item["id"]
        islands[i] = dict(id=i, best_score=item.get("best_score"), member_count=item.get("member_count"),
            member_ids=[m["id"] for m in item.get("members", [])] if item.get("members_available") else None)
    checkpoint_ids = {_int(i.get("idx")) for i in _list(_dict(checkpoint.get("db")).get("islands")) if isinstance(i, dict)} - {None}
    survivors = set(_ids(schedule.get("survivors")))
    for i in checkpoint_ids:
        islands.setdefault(i, dict(id=i, best_score=None, member_count=None, member_ids=None))
        if isinstance(schedule.get("survivors"), list):
            statuses[i] = "retired" if i not in survivors else "cooldown" if (_counter(schedule.get("cooldown"), i) or 0) > 0 else "active"
    # Explicit later cuts/births supersede the saved scheduler lifecycle only.
    if anchor_index is not None:
        for row in rows[anchor_index + 1:]:
            if row.get("event") == "sh_cut":
                cut = set(_ids(row.get("cut")))
                for i in _ids(row.get("ranking")):
                    statuses[i] = "retired" if i in cut else "active"
            elif row.get("event") == "decision" and row.get("policy") == "dynamic_islands" and row.get("action") == "spawn":
                if _int(row.get("island")) is not None:
                    statuses[row["island"]] = "active"
    next_cut = _next_cut(checkpoint, config, programs, supported, stale)
    later_cuts = [r for r in rows[anchor_index + 1:] if r.get("event") == "sh_cut"] if anchor_index is not None else []
    if later_cuts and next_cut["status"] == "conditional":
        next_cut.update(status="unknown", ranking=[], cut=[], protected=[], survivors=[],
            milestone_evaluations=None, evaluations_remaining=None,
            reason="A newer SH decision is recorded; a consistent scheduler checkpoint is required for the next forecast.")
    lifetime = len(_list(_dict(checkpoint.get("db")).get("islands"))) if checkpoint_ids else initial if fresh else None
    for row in rows:
        if row.get("event") == "decision" and row.get("policy") == "dynamic_islands" and row.get("action") == "spawn":
            count = _int(row.get("n_islands"))
            if count is not None:
                lifetime = max(lifetime or 0, count)
    maximum, window = _int(config.get("max_islands")), _int(config.get("spawn_stall"))
    stall = evaluations - reset if evaluations is not None and reset is not None else None
    enabled = config.get("dynamic_islands") if type(config.get("dynamic_islands")) is bool else None
    guards = [dict(label="Dynamic islands enabled", satisfied=enabled),
        dict(label="Lifetime island count below cap", satisfied=lifetime < maximum if lifetime is not None and maximum is not None else None),
        dict(label="Successful evaluation counter reaches threshold", satisfied=evaluations >= window if evaluations is not None and window is not None else None),
        dict(label="No population record or spawn reset within stall window", satisfied=stall >= window if stall is not None and window is not None else None)]
    eligible = False if any(g["satisfied"] is False for g in guards) else True if all(g["satisfied"] is True for g in guards) else None
    spawn = dict(enabled=enabled, conditional=True, lifetime_islands=lifetime, max_islands=maximum,
        stall_evaluations=stall, stall_threshold=window, last_reset_evaluation=reset,
        remaining_evaluations=max(0, window - stall, window - evaluations) if stall is not None and window is not None and evaluations is not None else None,
        eligible_now=eligible, guards=guards, counter_source=counter_source,
        reason="Conditional at the next dispatch if search continues. The cap counts every island ever created, including retired islands. Both a population record and a spawn reset the stall counter.")
    migrations = []
    for pid, program in programs.items():
        parent = programs.get(_id(program.get("parent_id")))
        if program.get("origin") != "migrant" or not parent:
            continue
        source_island, target = _int(parent.get("island")), _int(program.get("island"))
        if source_island is not None and target is not None:
            migrations.append(dict(id="migration:" + pid, program_id=pid, parent_id=parent["id"],
                from_island=source_island, to_island=target, source="checkpoint", at=None))
    migration_count = len(migrations)
    migrations = migrations[-MAX_MIGRATIONS:]
    current = []
    for i in sorted(islands)[:MAX_ISLANDS]:
        current.append(dict(islands[i], status=statuses.get(i, "unknown"),
            membership_stale=population.get("stale") if population.get("available") else islands[i].get("membership_stale"),
            status_source="checkpoint+journal" if schedule else "journal" if i in statuses else "unavailable",
            status_stale=stale if schedule and i in checkpoint_ids else None,
            dispatched=_counter(schedule.get("dispatched"), i), saturation_count=_counter(schedule.get("saturation_counter"), i),
            cooldown_dispatches=(_counter(schedule.get("cooldown"), i) or 0) if isinstance(schedule.get("cooldown"), dict) else None,
            at_risk=i in next_cut["cut"] if next_cut["status"] == "conditional" else None,
            protected=i in next_cut["protected"] if next_cut["status"] == "conditional" else None,
            forecast_as_of=next_cut["forecast_as_of"], born=born.get(i, dict(kind="unknown", event_id=None)), retired_at=retired.get(i)))
    anchor = _dict(_dict(checkpoint.get("provenance")).get("journal_anchor"))
    current_id = f"current:{_id(anchor.get('segment_id')) or 'journal'}:{population.get('iteration')}:{last_iteration}"
    frames.append(dict(id=current_id, at=None, iteration=population.get("iteration"), evaluations=population.get("evaluations"),
        source=population.get("source"), islands=current, migrations=migrations, stale=population.get("stale")))
    return dict(schema="sciel-island-dynamics/1", state_source="checkpoint+journal" if schedule else "journal",
        as_of=dict(iteration=last_iteration if last_iteration is not None else cp_iteration, evaluations=evaluations,
            checkpoint_iteration=cp_iteration, checkpoint_stale=stale), islands=current, next_cut=next_cut, spawn=spawn,
        events=list(events), frames=list(frames), active_frame_id=current_id, migrations=migrations,
        history_limited=event_count > MAX_EVENTS or frame_count + 1 > MAX_FRAMES or migration_count > MAX_MIGRATIONS,
        coverage=dict(recorded_events=event_count, retained_events=len(events), recorded_frames=frame_count + 1,
            retained_frames=len(frames), recorded_migrations=migration_count, checkpoint_anchor_found=anchor_index is not None),
        notes=["Territory is a display layout, not the engine's embedding geometry.",
            "Forecasts are conditional at the saved checkpoint; status_stale marks scheduler data that may have advanced.",
            "Retired islands remain stored; SH copies unique elites and does not delete or conquer the source island.",
            "Cooldown is counted in dispatch decisions and can clear early when every eligible island is cooling down.",
            "SH forecasts use saved scores, saturation tie-breaks and dispatch fairness; future results can change them.",
            "Journal SH migration counts have no endpoints. Only explicit checkpoint migrant ancestry supplies links."])
