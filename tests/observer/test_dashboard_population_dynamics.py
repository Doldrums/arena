"""Island-map projections are inert: no engine, provider or experiment writes."""
from copy import deepcopy
import json
from unittest.mock import patch

from arena.observers.sciel.population import population_view


def fixture():
    config = dict(num_islands=4, budget=None, schedule_horizon=80, milestone_fracs=[.5, .75],
                  schedule_policy="sh", dynamic_islands=True, max_islands=6, spawn_stall=12)
    start = dict(event="run_start", resumed=False, run_id="r", segment_id="s", event_seq=1,
                 engine_contract="espalier-3.6", config=config)
    programs = [dict(id=f"p{i}", island=i, parent_id=None, origin="seed", score=score, gen=0)
                for i, score in enumerate([1., 1., .8, .8])]
    cp = dict(config=config, iteration_no=32, B_evals=30, _last_improve_eval=20,
              identity={"engine_contract": "espalier-3.6"}, milestones_fired=[],
              provenance={"journal_anchor": {"segment_id": "s", "event_seq": 2}},
              schedule=dict(policy="sh", survivors=[0, 1, 2, 3],
                  saturation_counter={"0": 1, "1": 0, "2": 1, "3": 0},
                  dispatched={"0": 20, "1": 20, "2": 3, "3": 20},
                  cooldown={"0": 3}, min_fair_evals=16, milestones_passed=0, num_islands=4),
              db=dict(programs=programs, archive=[], islands=[dict(idx=i, best_id=f"p{i}", members=[f"p{i}"],
                      grid={"1,1": f"p{i}"}) for i in range(4)]))
    rows = [start, dict(event="checkpoint", segment_id="s", event_seq=2, iteration_no=32, B_evals=30)]
    return cp, rows, start


def view(cp, rows, start):
    return population_view(cp, rows, start, {})["dynamics"]


def test_forecast_matches_score_saturation_tie_and_dispatch_fairness():
    cp, rows, start = fixture()
    result = view(cp, rows, start)
    forecast = result["next_cut"]
    assert forecast["status"] == "conditional"
    assert forecast["ranking"] == [1, 0, 3, 2]
    assert forecast["cut"] == [3]
    assert forecast["protected"] == [2]
    assert forecast["survivors"] == [1, 0, 2]
    assert forecast["milestone_evaluations"] == 40
    assert forecast["evaluations_remaining"] == 10
    assert result["islands"][0]["status"] == "cooldown"
    assert result["islands"][0]["cooldown_dispatches"] == 3
    assert result["islands"][2]["protected"] is True
    assert result["islands"][3]["at_risk"] is True


def test_full_score_and_saturation_tie_keeps_lower_island_id_first():
    cp, rows, start = fixture()
    cp["schedule"]["saturation_counter"] = {str(i): 0 for i in range(4)}
    assert view(cp, rows, start)["next_cut"]["ranking"] == [0, 1, 2, 3]


def test_stale_forecast_retains_checkpoint_context_not_new_scores():
    cp, rows, start = fixture()
    rows.append(dict(event="iteration", iteration_no=33, B_evals=31, island=3,
                     child_id="new", child_score=9, is_pop_event=True))
    result = view(cp, rows, start)
    assert result["next_cut"]["cut"] == [3]
    assert result["next_cut"]["forecast_as_of"] == dict(iteration=32, evaluations=30, stale=True, source="checkpoint")
    assert result["spawn"]["last_reset_evaluation"] == 31
    assert result["spawn"]["stall_evaluations"] == 0


def test_recorded_cut_retires_but_does_not_delete_members_and_invalidates_old_forecast():
    cp, rows, start = fixture()
    rows.append(dict(event="sh_cut", segment_id="s", event_seq=3, milestone=40,
                     ranking=[1, 0, 3, 2], cut=[3], protected=[2], migrations=2))
    result = view(cp, rows, start)
    assert result["islands"][3]["status"] == "retired"
    assert result["islands"][3]["member_ids"] == ["p3"]
    assert result["next_cut"]["status"] == "unknown"
    assert result["migrations"] == []
    cut = result["events"][-1]
    assert cut["migration_count"] == 2 and cut["migration_targets_known"] is False
    historical = result["frames"][-2]
    assert historical["source"] == "journal_lifecycle"
    assert historical["islands"][0]["member_ids"] is None
    assert historical["islands"][0]["membership_stale"] is True


def test_all_milestones_complete_does_not_invent_periodic_cuts():
    cp, rows, start = fixture()
    cp["milestones_fired"] = [40, 60]
    cp["B_evals"] = 900
    assert view(cp, rows, start)["next_cut"]["status"] == "complete"


def test_round_robin_disables_retirement_forecast():
    cp, rows, start = fixture()
    cp["schedule"]["policy"] = "round_robin"
    assert view(cp, rows, start)["next_cut"]["status"] == "disabled"


def test_spawn_requires_threshold_stall_and_lifetime_cap_not_active_islands():
    cp, rows, start = fixture()
    result = view(cp, rows, start)["spawn"]
    assert result["stall_evaluations"] == 10 and result["remaining_evaluations"] == 2
    assert result["eligible_now"] is False
    cp["_last_improve_eval"] = 18
    assert view(cp, rows, start)["spawn"]["eligible_now"] is True
    cp["schedule"]["survivors"] = [0]
    start["config"]["max_islands"] = 4
    result = view(cp, rows, start)["spawn"]
    assert result["lifetime_islands"] == 4
    assert result["eligible_now"] is False
    assert result["guards"][1]["satisfied"] is False


def test_spawn_resets_counter_but_remeasurement_does_not():
    cp, rows, start = fixture()
    rows.extend([dict(event="iteration", iteration_no=33, B_evals=31, reason="remeasurement", measurement_ok=True),
        dict(event="decision", policy="dynamic_islands", action="spawn", island=4, n_islands=5, seeded=False, stall=11)])
    result = view(cp, rows, start)
    assert result["spawn"]["last_reset_evaluation"] == 31
    assert result["spawn"]["stall_evaluations"] == 0
    assert result["spawn"]["lifetime_islands"] == 5
    assert result["islands"][4]["born"]["kind"] == "spawn"
    result = view(cp, rows[:-1], start)
    assert result["spawn"]["last_reset_evaluation"] == 20


def test_missing_anchor_does_not_replay_uncertain_counter_history():
    cp, rows, start = fixture()
    cp.pop("provenance")
    rows.append(dict(event="iteration", iteration_no=33, B_evals=31, is_pop_event=True))
    result = view(cp, rows, start)
    assert result["spawn"]["counter_source"] == "checkpoint"
    assert result["spawn"]["last_reset_evaluation"] == 20
    assert result["as_of"]["checkpoint_stale"] is True


def test_incomplete_admission_cannot_claim_spawn_eligibility():
    cp, rows, start = fixture()
    cp["_last_improve_eval"] = 0
    rows.append(dict(event="population", iteration_no=33, B_evals=31, islands=[]))
    result = view(cp, rows, start)
    assert result["spawn"]["stall_evaluations"] is None
    assert result["spawn"]["eligible_now"] is None


def test_explicit_migrant_parent_is_required_for_migration_edge():
    cp, rows, start = fixture()
    cp["db"]["programs"].extend([dict(id="m1", parent_id="p3", island=0, origin="migrant", score=.8),
        dict(id="lookalike", parent_id="p3", island=1, origin="gen", score=.8),
        dict(id="unknown", parent_id="not-recorded", island=0, origin="migrant", score=.8)])
    cp["db"]["islands"][0]["members"].append("m1")
    result = population_view(cp, rows, start, {})
    assert result["dynamics"]["migrations"] == [dict(id="migration:m1", program_id="m1", parent_id="p3",
        from_island=3, to_island=0, source="checkpoint", at=None)]
    member = result["islands"][0]["members"][1]
    assert (member["origin"], member["parent_id"], member["source_island"]) == ("migrant", "p3", 3)


def test_archival_unknowns_do_not_inherit_installed_defaults():
    result = view({}, [], {})
    assert result["islands"] == []
    assert result["next_cut"]["status"] == "unknown"
    assert result["spawn"]["enabled"] is None
    assert result["spawn"]["max_islands"] is None
    assert result["spawn"]["eligible_now"] is None
    cp, rows, start = fixture()
    start.pop("engine_contract")
    cp.pop("identity")
    assert view(cp, rows, start)["next_cut"]["status"] == "unknown"


def test_no_checkpoint_shows_known_initial_islands_without_invented_members():
    cp, rows, start = fixture()
    result = view({}, [start], start)
    assert len(result["islands"]) == 4
    assert all(i["status"] == "active" and i["member_count"] is None for i in result["islands"])
    seed = dict(event="decision", policy="initialization", action="seed_program", island=0, program_id="p0", score=.2)
    admitted = dict(event="iteration", island=0, child_id="new", island_best=.5, B_evals=1, iteration_no=1)
    result = view({}, [start, seed, admitted], start)
    assert result["islands"][0]["member_ids"] is None
    assert result["frames"][0]["islands"][0]["member_ids"] == ["p0"]


def test_fresh_explicit_zero_counters_support_progress_before_first_checkpoint():
    _, _, start = fixture()
    start["counters"] = dict(B_evals=0, _last_improve_eval=0)
    rows = [start, dict(event="iteration", iteration_no=1, B_evals=1, child_id="p4", is_pop_event=True),
            dict(event="iteration", iteration_no=2, B_evals=2, child_id="p5", is_pop_event=False)]
    result = view({}, rows, start)
    assert result["as_of"]["evaluations"] == 2
    assert result["spawn"]["last_reset_evaluation"] == 1
    assert result["spawn"]["stall_evaluations"] == 1
    assert result["spawn"]["counter_source"] == "fresh_run_start+journal"


def test_bounded_frames_and_events_are_detached_and_stable():
    cp, rows, start = fixture()
    rows = [start] + [dict(event="population", segment_id="s", event_seq=i + 10,
        iteration_no=i, B_evals=i, islands=[dict(idx=0, n=1, best=.5, members=[[f"p{i}", .5, i]])]) for i in range(80)]
    original = deepcopy((cp, rows, start))
    with patch("arena.observers.sciel.population_dynamics.MAX_EVENTS", 4), patch("arena.observers.sciel.population_dynamics.MAX_FRAMES", 3):
        result = view(cp, rows, start)
    assert len(result["events"]) == 4 and len(result["frames"]) == 3
    assert result["history_limited"] is True
    assert result["events"][-1]["id"] == "s:89:members:0"
    result["frames"][0]["islands"][0]["member_ids"].append("mutated")
    assert (cp, rows, start) == original
    json.dumps(result, allow_nan=False)
