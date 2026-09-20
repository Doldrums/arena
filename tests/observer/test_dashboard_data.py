"""Dashboard adapter checks, runnable with Python's standard-library unittest.

No provider, evaluator, candidate source, archive extraction or NumPy import.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arena.observers.sciel.data import RunStore


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / "study" / "run"
        self.run.mkdir(parents=True)
        self.log = self.run / "sciel_events.jsonl"
        self.rows = []
        self.store = RunStore([self.root])

    def append(self, **row):
        row = dict(run_id="run-a", segment_id="segment-a", event_seq=len(self.rows) + 1, **row)
        self.rows.append(row)
        with self.log.open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        return row

    def start(self):
        return self.append(event="run_start", task="test/task", seed=17, models=["fake"], resumed=False,
            counters=dict(cost_total=0, seed_score=0, iteration_no=0, B_evals=0))

    def ident(self):
        runs = self.store.discover()
        self.assertEqual(len(runs), 1)
        return runs[0]["id"]

    def checkpoint(self, **changes):
        value = dict(iteration_no=0, B_evals=0, cost_total=0, seed_score=0,
            db=dict(pop_best_id="p1", programs=[dict(id="p1", code="value = 0\n", score=0, parent_id=None)]),
            research=dict(knowledge=dict(experiments=[], lessons=[])),
            provenance=dict(run_id="run-a", journal_anchor=dict(segment_id="segment-a", event_seq=len(self.rows))))
        value.update(changes)
        (self.run / "checkpoint.json").write_text(json.dumps(value))
        return value

    def runtime(self, **changes):
        value = dict(schema="sciel-runtime/1", run_id="run-a", segment_id="segment-a",
            status="running", stage="evaluating", pid=os.getpid(), hostname=socket.gethostname(),
            heartbeat_at=datetime.now(timezone.utc).isoformat(), stale_after_seconds=10,
            process_identity=dict(kind="test-token", value="fixture"))
        value.update(changes)
        (self.run / "runtime.json").write_text(json.dumps(value))

    def test_discovery_is_limited_to_native_journals_and_allowed_roots(self):
        self.start()
        (self.root / "unrelated.jsonl").write_text('{"event":"run_start"}\n')
        external = self.root.parent / (self.root.name + "-outside")
        external.mkdir()
        self.addCleanup(lambda: external.rmdir())
        foreign = external / "sciel_events.jsonl"
        foreign.write_text('{"event":"run_start"}\n')
        self.addCleanup(foreign.unlink)
        linked = self.root / "linked"
        linked.mkdir()
        (linked / "sciel_events.jsonl").symlink_to(foreign)
        self.assertEqual(len(self.store.discover()), 1)
        with self.assertRaises(KeyError):
            self.store.snapshot("../../outside")
        with self.assertRaises(KeyError):
            self.store.detail(self.ident(), "../../checkpoint.json")

    def test_partial_tail_and_bad_middle_record_do_not_hide_valid_append(self):
        self.start()
        with self.log.open("a") as stream:
            stream.write('broken record\n{"event":"iteration","iteration_no":1,')
        ident = self.ident()
        first = self.store.snapshot(ident)
        self.assertEqual(len(first["events"]), 1)
        self.assertEqual(len(first["warnings"]), 2)
        with self.log.open("a") as stream:
            stream.write('"child_id":"p2","child_score":0,"B_evals":1,"cost":0}\n')
        second = self.store.snapshot(ident)
        self.assertEqual(len(second["events"]), 2)
        self.assertEqual(second["trials"][0]["score"], 0)
        self.assertEqual(len(second["warnings"]), 1)
        self.assertNotEqual(second["run"]["status"], "completed")

    def test_checkpoint_rewrite_keeps_last_good_copy_and_recovers(self):
        self.start()
        self.checkpoint()
        ident = self.ident()
        self.assertEqual(self.store.snapshot(ident)["checkpoint"]["status"], "available")
        path = self.run / "checkpoint.json"
        path.write_text('{"db":')
        stale = self.store.snapshot(ident)
        self.assertTrue(stale["checkpoint"]["available"])
        self.assertEqual(stale["checkpoint"]["status"], "stale")
        self.assertEqual(self.store.detail(ident, "p1")["code"], "value = 0\n")
        self.checkpoint(iteration_no=2, B_evals=2)
        current = self.store.snapshot(ident)
        self.assertEqual(current["checkpoint"]["status"], "available")
        self.assertEqual(current["stats"]["iterations"], 2)

    def test_valid_json_tail_waits_for_commit_newline(self):
        self.start()
        with self.log.open("a") as stream:
            stream.write(json.dumps(dict(event="run_end", reason="budget", cost_total=.4, pop_best=.7)))
        ident = self.ident()
        pending = self.store.snapshot(ident)
        self.assertEqual(pending["run"]["event_count"], 1)
        self.assertNotEqual(pending["run"]["status"], "completed")
        self.assertIn("Incomplete trailing", pending["warnings"][0])
        with self.log.open("a") as stream:
            stream.write("\n")
        committed = self.store.snapshot(ident)
        self.assertEqual(committed["run"]["event_count"], 2)
        self.assertEqual(committed["run"]["status"], "completed")
        self.assertEqual(committed["stats"]["best_score"], .7)
        self.assertFalse(committed["warnings"])

    def test_initially_partial_checkpoint_does_not_invent_zero_score(self):
        self.append(event="run_start", task="unknown/task")
        (self.run / "checkpoint.json").write_text("{")
        snap = self.store.snapshot(self.ident())
        self.assertFalse(snap["checkpoint"]["available"])
        self.assertIsNone(snap["stats"]["best_score"])
        self.assertIsNone(snap["stats"]["cost_total"])
        self.assertEqual(snap["stats"]["cost_status"], "unavailable")

    def test_fresh_initialized_seed_zero_is_unknown_until_measurement(self):
        self.start()
        ident = self.ident()
        initial = self.store.snapshot(ident)
        self.assertIsNone(initial["stats"]["best_score"])
        self.assertEqual(initial["stats"]["iterations"], 0)
        self.assertEqual(initial["stats"]["evaluations"], 0)
        self.append(event="research", phase="attempt", experiment_id="r1",
                    evidence=dict(id="r1", status="pending", iteration=1, parent_score=0))
        self.assertEqual(self.store.snapshot(ident)["stats"]["best_score"], 0)

    def test_seed_source_and_single_baseline_are_available_before_checkpoint(self):
        self.start()
        source = "value = 0.25\n"
        for island, ident in enumerate(("p1", "p2")):
            self.append(event="decision", policy="initialization", action="seed_program",
                schema="sciel-initialization/1", program_id=ident, source=source,
                source_sha256=sha(source), island=island, measured=True, score=.25,
                seed_score=.25, iteration_no=0, B_evals=0)
        ident = self.ident()
        seeded = self.store.snapshot(ident)
        self.assertFalse(seeded["checkpoint"]["available"])
        self.assertEqual(seeded["stats"]["seed_score"], .25)
        self.assertEqual(seeded["stats"]["best_score"], .25)
        self.assertEqual(seeded["stats"]["evaluations"], 0)
        self.assertEqual(seeded["best_candidate_id"], "p1")
        self.assertEqual(len(seeded["curves"]), 1)
        self.assertEqual(seeded["curves"][0]["iteration"], 0)
        self.assertEqual(seeded["curves"][0]["kind"], "seed")
        self.assertEqual(self.store.detail(ident, "p1")["code"], source)
        self.assertEqual(seeded["events"][1]["data"]["source"],
            dict(omitted_chars=len(source), sha256=sha(source)))
        self.append(event="iteration", iteration_no=1, B_evals=1, child_id="p3",
            parent_id="p1", child_code="value = 0.5\n", child_score=.5, cost=.01)
        detail = self.store.detail(ident, "p3")
        self.assertEqual(detail["parent_code"], source)
        self.assertEqual(detail["diff_kind"], "full_sources")
        self.assertIn("-value = 0.25", detail["diff"])

    def test_unmeasured_seed_keeps_zero_unknown_and_requires_source_hash(self):
        self.start()
        source = "value = 0\n"
        self.append(event="decision", policy="initialization", action="seed_program",
            schema="sciel-initialization/1", program_id="p1", source=source,
            source_sha256=sha(source), island=0, measured=False, score=None,
            seed_score=None, iteration_no=0, B_evals=0)
        ident = self.ident()
        snap = self.store.snapshot(ident)
        self.assertIsNone(snap["stats"]["best_score"])
        self.assertIsNone(snap["stats"]["seed_score"])
        self.assertFalse(snap["curves"])
        self.assertEqual(self.store.detail(ident, "p1")["code"], source)
        self.append(event="decision", policy="initialization", action="seed_program",
            schema="sciel-initialization/1", program_id="bad", source="changed",
            source_sha256=sha(source), island=1, measured=False, score=None, seed_score=None)
        with self.assertRaises(KeyError):
            self.store.detail(ident, "bad")

    def test_measured_zero_seed_has_a_real_baseline(self):
        self.start()
        source = "value = 0\n"
        self.append(event="decision", policy="initialization", action="seed_program",
            schema="sciel-initialization/1", program_id="p1", source=source,
            source_sha256=sha(source), island=0, measured=True, score=0, seed_score=0)
        snap = self.store.snapshot(self.ident())
        self.assertEqual(snap["stats"]["best_score"], 0)
        self.assertEqual(snap["stats"]["seed_score"], 0)
        self.assertEqual(snap["curves"][0]["score"], 0)

    def test_architecture_preserves_model_weights_and_actual_descriptor_fallback(self):
        self.append(event="run_start", descriptor=dict(kind="code_length"),
            config=dict(llm=dict(models=["generator", "critic"], weights=[1.0, 0.0], max_tokens=123),
                embed_grid=True, research=dict(enabled=True, inject_lessons=False,
                    model="critic", reflection_interval=2, max_aux_calls=10), dynamic_islands=False,
                schedule_policy="round_robin", op_fixed="diff", budget=7))
        self.append(event="iteration", iteration_no=1, model_used="generator")
        self.append(event="research", phase="aux_start", kind="conclusion", model="critic")
        view = self.store.snapshot(self.ident())["architecture"]
        fields = {field["key"]: field for section in view["sections"] for field in section["fields"]}
        stages = {stage["id"]: stage["status"] for stage in view["stages"]}
        self.assertEqual(view["source"], "run_start.config")
        self.assertEqual(fields["generation_models"]["value"],
            [dict(model="generator", weight=1.0), dict(model="critic", weight=0.0)])
        self.assertEqual(fields["descriptor"]["value"], dict(kind="code_length"))
        self.assertEqual(fields["descriptor"]["source"], "run_start.descriptor")
        self.assertEqual(fields["observed_generation"]["value"], ["generator"])
        self.assertEqual(fields["observed_auxiliary"]["value"], ["critic"])
        self.assertEqual(fields["dynamic_islands"]["value"], False)
        self.assertEqual(fields["dynamic_islands"]["status"], "recorded")
        self.assertEqual(fields["evaluator"]["status"], "unknown")
        self.assertEqual(stages["conclusion"], "enabled")
        self.assertEqual(stages["reflection"], "enabled")
        self.assertEqual(stages["retrieval"], "disabled")

    def test_architecture_unknown_history_does_not_apply_current_defaults(self):
        self.append(event="run_start", task="old/task", models=["historic"])
        view = self.store.snapshot(self.ident())["architecture"]
        self.assertFalse(view["recorded"])
        self.assertEqual(view["source"], "unavailable")
        fields = {field["key"]: field for section in view["sections"] for field in section["fields"]}
        self.assertEqual(fields["models"]["value"], ["historic"])
        self.assertEqual(fields["dynamic_islands"]["status"], "unknown")
        self.assertIsNone(fields["dynamic_islands"]["value"])
        self.assertTrue(all(stage["status"] == "unknown" for stage in view["stages"]))

    def test_architecture_checkpoint_fallback_and_explicit_research_off(self):
        self.start()
        self.checkpoint(config=dict(research=dict(enabled=False, inject_lessons=True),
            llm=dict(models=["only"]), budget=3), identity=dict(descriptor=dict(kind="learned")))
        view = self.store.snapshot(self.ident())["architecture"]
        fields = {field["key"]: field for section in view["sections"] for field in section["fields"]}
        stages = {stage["id"]: stage["status"] for stage in view["stages"]}
        self.assertEqual(view["source"], "checkpoint.config")
        self.assertEqual(fields["generation_models"]["value"], [dict(model="only", weight=None)])
        self.assertEqual(fields["descriptor"]["source"], "checkpoint.identity.descriptor")
        self.assertEqual(stages["conclusion"], "disabled")
        self.assertEqual(stages["reflection"], "disabled")
        self.assertEqual(stages["retrieval"], "disabled")

    def test_architecture_latest_recorded_config_wins_over_checkpoint(self):
        self.append(event="run_start", config=dict(research=dict(enabled=True, inject_lessons=True)))
        self.checkpoint(config=dict(research=dict(enabled=False)))
        view = self.store.snapshot(self.ident())["architecture"]
        self.assertEqual(view["source"], "run_start.config")
        self.assertEqual(next(stage for stage in view["stages"] if stage["id"] == "retrieval")["status"], "enabled")

    def test_runtime_requires_matching_fresh_live_writer(self):
        self.start()
        self.runtime()
        with patch("arena.observers.sciel.data.process_matches", return_value=True):
            snap = self.store.snapshot(self.ident())
        self.assertEqual(snap["run"]["status"], "running")
        self.assertTrue(snap["runtime"]["active"])
        self.assertEqual(snap["runtime"]["stage"], "evaluating")
        self.runtime(heartbeat_at=(datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat())
        with patch("arena.observers.sciel.data.process_matches", return_value=True):
            stale = self.store.snapshot(self.ident())
        self.assertEqual(stale["run"]["status"], "stalled")
        self.assertIsNone(stale["runtime"]["active"])
        with patch("arena.observers.sciel.data.process_matches", return_value=False):
            dead = self.store.snapshot(self.ident())
        self.assertEqual(dead["run"]["status"], "interrupted")
        self.assertFalse(dead["runtime"]["active"])

    def test_runtime_wrong_segment_foreign_host_and_unverified_pid_are_unknown(self):
        self.start()
        for changes, verification in [
            (dict(segment_id="old-segment"), "different_run"),
            (dict(hostname="some-other-host"), "different_host"),
            ({}, "process_unverified"),
        ]:
            with self.subTest(verification=verification):
                self.runtime(**changes)
                with patch("arena.observers.sciel.data.process_matches", return_value=None):
                    snap = self.store.snapshot(self.ident())
                self.assertEqual(snap["run"]["status"], "observing")
                self.assertEqual(snap["runtime"]["verification"], verification)
                self.assertIsNone(snap["runtime"]["active"])

    def test_runtime_invalid_read_and_future_time_do_not_claim_running(self):
        self.start()
        (self.run / "runtime.json").write_text("{")
        snap = self.store.snapshot(self.ident())
        self.assertFalse(snap["runtime"]["available"])
        self.assertEqual(snap["runtime"]["verification"], "unreadable")
        self.runtime(heartbeat_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
        with patch("arena.observers.sciel.data.process_matches", return_value=True):
            future = self.store.snapshot(self.ident())
        self.assertEqual(future["run"]["status"], "observing")
        self.assertEqual(future["runtime"]["verification"], "invalid_timestamp")

    def test_runtime_terminal_failure_is_explicit_and_journal_completion_wins(self):
        self.start()
        self.runtime(status="failed", stage="finished", reason="ValueError", error_type="ValueError")
        snap = self.store.snapshot(self.ident())
        self.assertEqual(snap["run"]["status"], "failed")
        self.assertEqual(snap["runtime"]["verification"], "terminal_recorded")
        self.runtime(status="completed", stage="finished")
        self.assertNotEqual(self.store.snapshot(self.ident())["run"]["status"], "completed")
        self.append(event="run_end", reason="budget", cost_total=0)
        self.runtime()
        with patch("arena.observers.sciel.data.process_matches", return_value=True):
            complete = self.store.snapshot(self.ident())
        self.assertEqual(complete["run"]["status"], "completed")

    def test_explicit_token_rate_costs_are_estimated_not_provider_billing(self):
        self.append(event="run_start", config=dict(llm=dict(cost_reporting="estimated_uncached_token_rates")))
        self.append(event="run_end", cost_total=.125)
        stats = self.store.snapshot(self.ident())["stats"]
        self.assertEqual(stats["cost_total"], .125)
        self.assertEqual(stats["cost_status"], "estimated")
        self.assertEqual(stats["cost_source"], "estimated_uncached_token_rates / journal.cost_total")

    def test_checkpoint_unknown_charge_overrides_exact_cost_counter(self):
        self.start()
        self.checkpoint(cost_total=.125, _accounting_stopped_reason="LLM charge is unknown")
        snapshot = self.store.snapshot(self.ident())
        self.assertEqual(snapshot["stats"]["cost_total"], .125)
        self.assertEqual(snapshot["stats"]["cost_status"], "known_logged_lower_bound")
        self.assertTrue(any("charge is unknown" in warning for warning in snapshot["warnings"]))

    def test_journal_unknown_charge_is_partial_before_checkpoint(self):
        self.start()
        self.append(event="decision", policy="cost_accounting", action="unknown_cost",
                    cost=None, known_cost=.125)
        stats = self.store.snapshot(self.ident())["stats"]
        self.assertEqual(stats["cost_total"], .125)
        self.assertEqual(stats["cost_status"], "known_logged_lower_bound")

    def test_accounting_run_end_is_stopped_with_incomplete_spend(self):
        self.start()
        self.append(event="run_end", reason="accounting_stopped", cost_total=.125)
        snapshot = self.store.snapshot(self.ident())
        self.assertEqual(snapshot["run"]["status"], "stopped")
        self.assertEqual(snapshot["run"]["status_reason"], "accounting_stopped")
        self.assertEqual(snapshot["stats"]["cost_status"], "known_logged_lower_bound")

    def test_unknown_aux_charge_keeps_estimate_qualification(self):
        self.append(event="run_start", config=dict(llm=dict(cost_reporting="estimated_uncached_token_rates")))
        self.append(event="research", phase="aux_stopped", current_call_cost_unknown=True, cost=None)
        self.append(event="run_end", reason="research_stopped", cost_total=.125)
        snapshot = self.store.snapshot(self.ident())
        self.assertEqual(snapshot["stats"]["cost_total"], .125)
        self.assertEqual(snapshot["stats"]["cost_status"], "known_logged_lower_bound")
        self.assertIn("estimated_uncached_token_rates", snapshot["stats"]["cost_source"])
        self.assertTrue(any("token-rate estimates" in warning for warning in snapshot["warnings"]))

    def test_unknown_charge_without_any_counter_stays_unavailable(self):
        self.append(event="run_start")
        self.append(event="decision", policy="cost_accounting", action="unknown_cost", cost=None)
        stats = self.store.snapshot(self.ident())["stats"]
        self.assertIsNone(stats["cost_total"])
        self.assertEqual(stats["cost_status"], "unavailable")

    def test_portfolio_admission_updates_best_and_cost_before_first_iteration(self):
        self.start()
        source = "value = 7\n"
        for ident, score, cost, action in [("boot1", .75, .1, "portfolio"), ("boot2", .6, .2, "spawn")]:
            self.append(event="research", phase="outcome", experiment_id=ident, evidence=dict(
                id=ident, status="evaluated", parent_score=.5, island=0, iteration=0,
                score=score, evaluation=dict(ok=True, score=score), generation_cost=cost,
                source_sha256=sha(source), code_fragment=source))
            self.append(event="decision", policy="portfolio_seed", action=action, research=True,
                ok=True, island=0, cost=cost, meta=dict(research_id=ident,
                validation_trace=dict(attempts=[dict(cost=cost)])))
        self.append(event="research", phase="aux_result", cost=.05)
        ident = self.ident()
        snapshot = self.store.snapshot(ident)
        self.assertAlmostEqual(snapshot["stats"]["cost_total"], .35)
        self.assertEqual(snapshot["stats"]["best_score"], .75)
        self.assertEqual(snapshot["stats"]["iterations"], 0)
        self.assertEqual(snapshot["stats"]["evaluations"], 0)
        self.assertEqual(snapshot["best_candidate_id"], "boot1")
        self.assertEqual(self.store.detail(ident, "boot1")["code"], source)
        self.assertEqual([point["kind"] for point in snapshot["curves"]], ["bootstrap", "bootstrap"])
        self.assertEqual([point["best_score"] for point in snapshot["curves"]], [.75, .75])
        # Absolute checkpoint counters and subsequent ordinary iterations must
        # not charge the same bootstrap outcomes/decisions a second time.
        self.checkpoint(cost_total=.35, db=dict(programs=[], pop_best_id=None))
        self.append(event="iteration", iteration_no=1, B_evals=1, cost=.4,
                    child_id="ordinary", child_score=.7, pop_best=.75)
        continued = self.store.snapshot(ident)
        self.assertAlmostEqual(continued["stats"]["cost_total"], .75)
        self.assertEqual(continued["stats"]["best_score"], .75)

    def test_bootstrap_does_not_admit_missing_rejected_or_inconsistent_outcomes(self):
        self.start()
        for ident, accepted, evaluated in [("rejected", False, True), ("failed", True, False)]:
            self.append(event="research", phase="outcome", experiment_id=ident, evidence=dict(
                id=ident, status="evaluated" if evaluated else "eval_failed", parent_score=.5,
                island=0, score=10, evaluation=dict(ok=evaluated, score=10)))
            self.append(event="decision", policy="portfolio_seed", research=True,
                        ok=accepted, island=0, cost=.1, meta=dict(research_id=ident))
        self.append(event="decision", policy="portfolio_seed", research=True,
                    ok=True, island=0, cost=.1, meta=dict(research_id="later"))
        self.append(event="research", phase="outcome", experiment_id="later", evidence=dict(
            id="later", status="evaluated", island=0, score=20, evaluation=dict(ok=True, score=20)))
        self.append(event="research", phase="outcome", experiment_id="mismatch", evidence=dict(
            id="mismatch", status="evaluated", island=0, score=30, evaluation=dict(ok=True, score=3)))
        self.append(event="decision", policy="portfolio_seed", research=True,
                    ok=True, island=0, cost=.1, meta=dict(research_id="mismatch"))
        snapshot = self.store.snapshot(self.ident())
        self.assertEqual(snapshot["stats"]["best_score"], .5)
        self.assertAlmostEqual(snapshot["stats"]["cost_total"], .4)
        self.assertEqual(snapshot["curves"], [])

    def test_legacy_bootstrap_scores_and_failed_proposal_costs_are_separate(self):
        self.start()
        self.append(event="decision", policy="paradigm_validation", action="eval_failed",
                    score=99, cost=.1)
        self.append(event="decision", policy="portfolio_seed", action="spawn", score=.6, cost=.2)
        self.append(event="decision", policy="portfolio_seed", action="portfolio", ok=False, score=99, cost=.3)
        snapshot = self.store.snapshot(self.ident())
        self.assertEqual(snapshot["stats"]["best_score"], .6)
        self.assertAlmostEqual(snapshot["stats"]["cost_total"], .6)
        self.assertEqual(len(snapshot["curves"]), 1)
        self.assertEqual(snapshot["curves"][0]["kind"], "bootstrap")

    def test_completion_requires_latest_segment_run_end(self):
        self.start()
        self.checkpoint(milestone="final")
        ident = self.ident()
        self.assertNotEqual(self.store.snapshot(ident)["run"]["status"], "completed")
        self.append(event="run_end", reason="budget", cost_total=0, pop_best=0)
        self.assertEqual(self.store.snapshot(ident)["run"]["status"], "completed")
        with self.log.open("a") as stream:
            stream.write(json.dumps(dict(event="run_start", run_id="run-a", segment_id="segment-b",
                event_seq=1, resumed=True, counters=dict(cost_total=0))) + "\n")
        self.assertNotEqual(self.store.snapshot(ident)["run"]["status"], "completed")
        os.utime(self.log, (1, 1))
        snap = self.store.snapshot(ident)
        self.assertEqual(snap["run"]["status"], "historical")
        self.assertIn("unknown", snap["run"]["status_reason"])

    def test_new_run_in_same_file_does_not_inherit_old_score_or_checkpoint(self):
        self.start()
        self.append(event="run_end", cost_total=2, pop_best=5)
        self.checkpoint()
        ident = self.ident()
        with self.log.open("a") as stream:
            stream.write(json.dumps(dict(event="run_start", run_id="run-b", segment_id="b", event_seq=1)) + "\n")
        snap = self.store.snapshot(ident)
        self.assertEqual(snap["run"]["event_count"], 1)
        self.assertIsNone(snap["stats"]["best_score"])
        self.assertFalse(snap["checkpoint"]["available"])

    def test_restore_anchor_excludes_abandoned_scores_sources_and_lessons(self):
        self.start()
        self.append(event="iteration", iteration_no=1, B_evals=1, child_id="p2",
                    child_score=2, child_code="value = 2\n", parent_id="p1", cost=.1)
        saved = self.checkpoint(iteration_no=1, B_evals=1, cost_total=.1,
            db=dict(pop_best_id="p2", programs=[
                dict(id="p1", code="value = 0\n", score=0),
                dict(id="p2", code="value = 2\n", score=2, parent_id="p1")]))
        self.append(event="iteration", iteration_no=2, B_evals=2, child_id="p3",
                    child_score=99, child_code="value = 99\n", parent_id="p2", cost=.4)
        self.append(event="research", phase="conclusion", status="parsed", experiment_id="lost",
                    accepted_lesson_ids=["abandoned"], llm=dict(lessons=[dict(rule="Lost branch")]))
        ident = self.ident()
        self.assertEqual(self.store.snapshot(ident)["best_candidate_id"], "p3")
        resumed = [
            dict(event="run_start", event_seq=1, resumed=True,
                 counters=dict(iteration_no=1, B_evals=1, seed_score=0, cost_total=.1)),
            dict(event="checkpoint_restore", event_seq=2, provenance=saved["provenance"]),
        ]
        with self.log.open("a") as stream:
            for row in resumed:
                stream.write(json.dumps(dict(run_id="run-a", segment_id="segment-b", **row)) + "\n")
        snap = self.store.snapshot(ident)
        self.assertEqual(snap["stats"]["best_score"], 2)
        self.assertEqual(snap["best_candidate_id"], "p2")
        self.assertEqual(snap["stats"]["evaluations"], 1)
        self.assertEqual(snap["stats"]["iterations"], 1)
        self.assertEqual(snap["stats"]["cost_total"], .1)
        self.assertEqual(len(snap["curves"]), 1)
        self.assertFalse(snap["lessons"])
        self.assertEqual(snap["events"][-1]["event"], "checkpoint_restore")
        self.assertTrue(any("discarded 2 abandoned" in warning for warning in snap["warnings"]))
        with self.assertRaises(KeyError):
            self.store.detail(ident, "p3")
        with self.log.open("a") as stream:
            stream.write(json.dumps(dict(event="iteration", run_id="run-a", segment_id="segment-b",
                event_seq=3, iteration_no=2, B_evals=2, child_id="p3", child_score=1,
                child_code="value = 1\n", parent_id="p2", cost=.2)) + "\n")
        continued = self.store.snapshot(ident)
        self.assertEqual(continued["stats"]["best_score"], 2)
        self.assertEqual(continued["curves"][-1]["best_score"], 2)
        self.assertEqual(self.store.detail(ident, "p3")["code"], "value = 1\n")
        self.assertAlmostEqual(continued["stats"]["cost_total"], .3)

    def test_trial_join_failure_score_and_costs_have_no_duplicate_credit(self):
        self.start()
        code = "value = 1\n"
        record = dict(id="r1", iteration=1, island=0, parent_id="p1", parent_score=0,
            status="pending", score=None, actual_delta=None, generation_cost=.1,
            source_sha256=sha(code), hypothesis=dict(text="Change value", predicted_low=0,
                predicted_high=1, reasoning="fixture", confidence=.5))
        self.append(event="research", phase="attempt", experiment_id="r1", evidence=record)
        self.append(event="research", phase="hypothesis", experiment_id="r1", evidence=record,
                    response="HYPOTHESIS_JSON: {}\n```python\n" + code + "```\n")
        failed = dict(record, status="eval_failed", evaluation=dict(ok=False, score=0))
        self.append(event="research", phase="outcome", experiment_id="r1", evidence=failed)
        self.append(event="iteration", iteration_no=1, island=0, B_evals=0, child=None,
                    parent_id="p1", reason="eval_failed", cost=.1, meta=dict(research_id="r1"))
        self.append(event="research", phase="aux_result", kind="conclusion", reference="r1", cost=.2,
                    response='{"lessons":[]}')
        self.append(event="research", phase="conclusion", experiment_id="r1", status="parsed",
                    llm=dict(verdict="INCONCLUSIVE", explanation="No measured result", lessons=[]),
                    accepted_lesson_ids=[])
        snap = self.store.snapshot(self.ident())
        self.assertEqual(len(snap["trials"]), 1)
        self.assertIsNone(snap["trials"][0]["score"])
        self.assertIsNone(snap["trials"][0]["actual_delta"])
        self.assertEqual(snap["trials"][0]["conclusion"]["explanation"], "No measured result")
        self.assertAlmostEqual(snap["stats"]["cost_total"], .3)
        self.assertEqual(snap["stats"]["cost_status"], "known_logged_lower_bound")
        self.append(event="run_end", reason="backstop", cost_total=.3, pop_best=0)
        self.assertAlmostEqual(self.store.snapshot(self.ident())["stats"]["cost_total"], .3)
        self.assertEqual(self.store.detail(self.ident(), "r1")["code"], code)

    def test_nochild_iteration_without_research_id_joins_last_attempt(self):
        self.start()
        for attempt in (1, 2):
            self.append(event="research", phase="outcome", experiment_id=f"r1a{attempt}",
                evidence=dict(id=f"r1a{attempt}", iteration=1, island=0, status="duplicate", score=None))
        self.append(event="iteration", iteration_no=1, island=0, reason="dup_cap", cost=.2)
        snap = self.store.snapshot(self.ident())
        self.assertEqual(snap["stats"]["attempts"], 2)
        self.assertEqual(snap["trials"][-1]["iteration_reason"], "dup_cap")

    def test_details_use_persisted_sources_and_reject_unbound_response(self):
        self.start()
        self.checkpoint()
        self.append(event="iteration", iteration_no=1, B_evals=1, child_id="p2", parent_id="p1",
                    child_code="value = 2\n", child_score=2, cost=.1)
        detail = self.store.detail(self.ident(), "p2")
        self.assertEqual(detail["code_source"], "journal.child_code")
        self.assertEqual(detail["diff_kind"], "full_sources")
        self.assertIn("-value = 0", detail["diff"])
        self.assertIn("+value = 2", detail["diff"])
        self.append(event="research", phase="hypothesis", experiment_id="r2",
                    evidence=dict(id="r2", iteration=2, status="pending", source_sha256="a" * 64),
                    response="```python\nraise RuntimeError('must never execute')\n```\n")
        self.assertIsNone(self.store.detail(self.ident(), "r2")["code"])

    def test_live_accepted_lessons_and_retirement_are_not_just_proposals(self):
        self.start()
        rule = dict(rule="Use a smaller step", polarity="positive", scope="branch", branch="p1", evidence_ids=["r1"])
        self.append(event="research", phase="conclusion", experiment_id="r1", status="parsed",
                    llm=dict(lessons=[rule]), accepted_lesson_ids=["l1"])
        self.append(event="research", phase="conclusion", experiment_id="r2", status="parsed",
                    llm=dict(lessons=[dict(rule, rule="Rejected suggestion")]), accepted_lesson_ids=[])
        self.append(event="research", phase="aux_result", kind="reflection", reference=2, cost=.1,
                    response="REFLECTION_JSON: " + json.dumps(dict(lessons=[dict(rule, rule="Replacement")], retire_ids=["l1"])))
        self.append(event="research", phase="reflection", through=2, status="parsed", error=None,
                    applied=dict(lesson_ids=["l2"], retired_ids=["l1"]))
        snap = self.store.snapshot(self.ident())
        self.assertEqual([(x["id"], x["status"]) for x in snap["lessons"]], [("l1", "retired"), ("l2", "active")])
        self.assertEqual(snap["stats"]["lessons"], 1)

    def test_checkpoint_cost_anchor_and_only_later_lesson_changes(self):
        self.start()
        self.append(event="iteration", iteration_no=1, child_id="p2", child_score=1, cost=.1)
        rule = dict(id="l1", rule="Old", polarity="positive", scope="branch", branch="p1", evidence_ids=["r1"])
        self.checkpoint(cost_total=.5, research=dict(knowledge=dict(lessons=[rule], experiments=[])))
        self.append(event="iteration", iteration_no=2, child_id="p3", child_score=2, cost=.2)
        self.append(event="research", phase="aux_result", kind="conclusion", reference="r2", cost=.3)
        snap = self.store.snapshot(self.ident())
        self.assertAlmostEqual(snap["stats"]["cost_total"], 1)
        self.assertEqual(snap["lessons"][0]["id"], "l1")

    def test_live_best_candidate_replaces_lagging_checkpoint_id(self):
        self.start()
        self.checkpoint()
        self.append(event="iteration", iteration_no=1, B_evals=1, child_id="p2", parent_id="p1",
                    child_code="value = 2\n", child_score=2, pop_best=2, cost=.1)
        ident = self.ident()
        snap = self.store.snapshot(ident)
        self.assertEqual(snap["stats"]["best_score"], 2)
        self.assertEqual(snap["best_candidate_id"], "p2")
        self.assertEqual(self.store.detail(ident, snap["best_candidate_id"])["code"], "value = 2\n")
        self.append(event="run_end", pop_best=99, cost_total=.1)
        self.assertIsNone(self.store.snapshot(ident)["best_candidate_id"])

    def test_checkpoint_overlay_distinguishes_eviction_and_unknown_exposures(self):
        self.start()
        rule = dict(rule="Accepted", polarity="positive", scope="branch", evidence_ids=["r1"])
        self.append(event="research", phase="conclusion", experiment_id="r1", status="parsed",
                    llm=dict(lessons=[rule]), accepted_lesson_ids=["l1"])
        # l1 is absent from authoritative memory, but no R retired it. l2 has
        # no retained exposure field, so its initial count is unknown, not zero.
        self.checkpoint(research=dict(knowledge=dict(lessons=[dict(rule, id="l2")], experiments=[])))
        ident = self.ident()
        before = self.store.snapshot(ident)
        lessons = {item["id"]: item for item in before["lessons"]}
        self.assertEqual(lessons["l1"]["status"], "not_retained")
        self.assertIsNone(lessons["l2"]["exposure_count"])
        for eid, dispatch in [("unissued", "not_dispatched"), ("seen", "returned"), ("seen", "returned")]:
            self.append(event="research", phase="outcome", experiment_id=eid,
                        evidence=dict(id=eid, status="generation_stopped", injected_ids=["l2"], generation_dispatch=dispatch))
        after = {item["id"]: item for item in self.store.snapshot(ident)["lessons"]}
        self.assertEqual(after["l2"]["exposure_count"], 1)
        self.assertEqual(after["l2"]["exposure_count_scope"], "known_direct")

    def test_unanchored_checkpoint_does_not_replay_ambiguous_lesson_history(self):
        self.start()
        rule = dict(rule="Possibly old", polarity="positive", scope="branch", evidence_ids=["r1"])
        self.append(event="research", phase="conclusion", experiment_id="r1", status="parsed",
                    llm=dict(lessons=[rule]), accepted_lesson_ids=["l1"])
        self.checkpoint(provenance={}, research=dict(knowledge=dict(lessons=[dict(rule, id="current")], experiments=[])))
        snap = self.store.snapshot(self.ident())
        self.assertEqual([item["id"] for item in snap["lessons"]], ["current"])
        self.assertIsNone(snap["lessons"][0]["exposure_count"])

    def test_ambiguous_reflection_mapping_never_labels_unaccepted_text_as_lesson(self):
        self.start()
        self.append(event="research", phase="aux_result", kind="reflection", reference=2,
                    response=json.dumps(dict(lessons=[dict(rule="Unbound first"), dict(rule="Unbound second")], retire_ids=[])))
        self.append(event="research", phase="reflection", through=2, status="parsed", error=None,
                    applied=dict(lesson_ids=["accepted-id"], retired_ids=[]))
        lesson = self.store.snapshot(self.ident())["lessons"][0]
        self.assertEqual(lesson["id"], "accepted-id")
        self.assertEqual(lesson["rule"], "")

    def test_json_is_finite_credentials_redacted_and_returned_data_detached(self):
        self.append(event="run_start", task="test", config=dict(llm=dict(api_key="do-not-expose")),
                    strange=float("nan"), pop_best=float("inf"))
        snap = self.store.snapshot(self.ident())
        encoded = json.dumps(snap, allow_nan=False)
        self.assertNotIn("do-not-expose", encoded)
        snap["events"][0]["data"]["config"]["llm"]["api_key"] = "changed"
        self.assertEqual(self.store.snapshot(self.ident())["events"][0]["data"]["config"]["llm"]["api_key"], "[redacted]")

    def test_attributable_geometry_and_engineering_scope_are_only_saved_data(self):
        self.start()
        (self.run.parent / "summary.json").write_text('{"engineering_only": true}')
        source = "x" * 64
        self.append(event="research", phase="outcome", experiment_id="r1",
            evidence=dict(id="r1", status="evaluated", score=1, source_sha256=source,
                evaluation=dict(native_geometry=dict(source_sha256=source,
                    numeric=dict(centers=[[.5, .5]], radii=[.1])))))
        snap = self.store.snapshot(self.ident())
        self.assertEqual(snap["run"]["scope"], "engineering")
        self.assertEqual(snap["geometry"]["experiment_id"], "r1")
        self.assertFalse(snap["geometry"]["verified_by_dashboard"])
        self.rows[-1]["evidence"]["evaluation"]["native_geometry"]["source_sha256"] = "another source"
        self.log.write_text("".join(json.dumps(row) + "\n" for row in self.rows))
        self.assertIsNone(self.store.snapshot(self.ident())["geometry"])

    def test_real_s04_fixture_is_read_only_and_has_seven_attempts(self):
        repo = Path(__file__).resolve().parents[2]
        root = repo / "autoresearch" / "research_cycle_20260916" / "s04_r2_cycle"
        log = root / "run" / "sciel_events.jsonl"
        if not log.is_file():
            self.skipTest("Historical S04 fixture not included in this checkout")
        before = hashlib.sha256(log.read_bytes()).hexdigest()
        store = RunStore([root])
        run = store.discover()[0]
        snap = store.snapshot(run["id"])
        self.assertEqual(snap["stats"]["attempts"], 7)
        self.assertEqual(snap["stats"]["evaluations"], 4)
        self.assertEqual(snap["run"]["scope"], "engineering")
        self.assertAlmostEqual(snap["stats"]["cost_total"], .1156776)
        lessons = {item["id"]: item for item in snap["lessons"]}
        self.assertEqual(len(lessons), 7)
        self.assertEqual(snap["stats"]["lessons"], 1)
        self.assertEqual(lessons["l000007"]["status"], "active")
        self.assertEqual(sum(item["status"] == "retired" for item in lessons.values()), 6)
        self.assertEqual(lessons["l000003"]["exposure_count"], 2)
        self.assertEqual(lessons["l000006"]["exposure_count"], 2)
        self.assertEqual(lessons["l000007"]["exposure_count"], 1)
        self.assertTrue(store.detail(run["id"], "p3")["code"])
        self.assertEqual(before, hashlib.sha256(log.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
