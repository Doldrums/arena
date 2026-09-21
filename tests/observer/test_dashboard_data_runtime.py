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

from _dashboard_data_helpers import DashboardDataFixture


class DashboardRuntimeDataTests(DashboardDataFixture):
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
        with patch("arena.observers.sciel.run_runtime.process_matches", return_value=True):
            snap = self.store.snapshot(self.ident())
        self.assertEqual(snap["run"]["status"], "running")
        self.assertTrue(snap["runtime"]["active"])
        self.assertEqual(snap["runtime"]["stage"], "evaluating")
        self.runtime(heartbeat_at=(datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat())
        with patch("arena.observers.sciel.run_runtime.process_matches", return_value=True):
            stale = self.store.snapshot(self.ident())
        self.assertEqual(stale["run"]["status"], "stalled")
        self.assertIsNone(stale["runtime"]["active"])
        with patch("arena.observers.sciel.run_runtime.process_matches", return_value=False):
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
                with patch("arena.observers.sciel.run_runtime.process_matches", return_value=None):
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
        with patch("arena.observers.sciel.run_runtime.process_matches", return_value=True):
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
        with patch("arena.observers.sciel.run_runtime.process_matches", return_value=True):
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


if __name__ == "__main__":
    unittest.main()
