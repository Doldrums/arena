"""Cheap temporary-artifact checks for cached history and runtime-only SSE."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arena.observers.sciel.data import RunStore


class DashboardCacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "run"
        self.run.mkdir()
        self.log = self.run / "sciel_events.jsonl"
        self.append(event="run_start", run_id="r", segment_id="s")
        self.store = RunStore([self.root])

    def append(self, **row):
        with self.log.open("a") as stream:
            stream.write(json.dumps(row) + "\n")

    def test_runtime_frame_does_not_rebuild_or_copy_history(self):
        with patch.object(self.store, "_project", wraps=self.store._project) as project:
            ident = self.store.discover()[0]["id"]
            version, event, full = self.store.stream_update(ident)
            self.assertEqual(event, "snapshot")
            self.assertEqual(full["content_version"], version)
            full["run"]["name"] = "mutated response"
            full["events"].clear()
            for _ in range(3):
                got, kind, small = self.store.stream_update(ident, version)
                self.assertEqual((got, kind), (version, "runtime"))
                self.assertEqual(set(small), {"run", "runtime", "timing", "effort"})
                self.assertEqual(small['effort']['schema'], 'arena-run-effort/1')
                self.assertNotIn('_effort_basis', small)
                self.assertNotIn("hypotheses", small["timing"])
                self.assertLess(len(json.dumps({k:v for k,v in small.items() if k != 'effort'})), 1000)
                self.assertLess(len(json.dumps(small['effort'])), 3000)
            (self.run / "runtime.json").write_text(json.dumps(dict(
                schema="sciel-runtime/1", run_id="r", segment_id="s", status="paused")))
            _, kind, small = self.store.stream_update(ident, version)
            self.assertEqual((kind, small["run"]["status"]), ("runtime", "paused"))
            snapshot = self.store.snapshot(ident)
            self.assertNotEqual(snapshot["run"]["name"], "mutated response")
            self.assertEqual(len(snapshot["events"]), 1)
            self.assertEqual(project.call_count, 1)

    def test_journal_append_and_checkpoint_creation_invalidate_content(self):
        ident = self.store.discover()[0]["id"]
        first, _, _ = self.store.stream_update(ident)
        self.append(event="iteration", iteration_no=1, child_score=.2)
        second, kind, snapshot = self.store.stream_update(ident, first)
        self.assertNotEqual(first, second)
        self.assertEqual((kind, len(snapshot["curves"])), ("snapshot", 1))
        (self.run / "checkpoint.json").write_text(json.dumps(dict(cost_total=.1)))
        third, kind, snapshot = self.store.stream_update(ident, second)
        self.assertNotEqual(second, third)
        self.assertEqual(kind, "snapshot")
        self.assertEqual(snapshot["stats"]["cost_total"], .1)

    def test_unreadable_checkpoint_stays_stale_until_signature_changes(self):
        checkpoint = self.run / "checkpoint.json"
        checkpoint.write_text(json.dumps(dict(cost_total=.1)))
        ident = self.store.discover()[0]["id"]
        first, _, _ = self.store.stream_update(ident)
        checkpoint.write_text('{"cost_total":')
        second, kind, snapshot = self.store.stream_update(ident, first)
        self.assertNotEqual(first, second)
        self.assertEqual(kind, "snapshot")
        self.assertTrue(snapshot["checkpoint"]["stale"])
        self.assertEqual(snapshot["stats"]["cost_total"], .1)
        with patch.object(self.store, "_project", wraps=self.store._project) as project:
            self.assertEqual(self.store.stream_update(ident, second)[1], "runtime")
            self.assertEqual(project.call_count, 0)
        checkpoint.write_text(json.dumps(dict(cost_total=.25)))
        third, kind, snapshot = self.store.stream_update(ident, second)
        self.assertNotEqual(second, third)
        self.assertEqual(kind, "snapshot")
        self.assertFalse(snapshot["checkpoint"]["stale"])
        self.assertEqual(snapshot["stats"]["cost_total"], .25)

    def test_termination_reasons_keep_pause_stop_and_failure_distinct(self):
        ident = self.store.discover()[0]["id"]
        for reason, expected in [("paused", "paused"), ("research_stopped", "stopped"),
                ("repeat_stopped", "stopped"), ("cost_limit", "stopped"),
                ("accounting_stopped", "stopped"),
                ("error", "failed"), ("budget", "completed")]:
            with self.subTest(reason=reason):
                self.append(event="run_end", reason=reason)
                self.assertEqual(self.store.snapshot(ident)["run"]["status"], expected)

    def test_archive_cache_is_bounded_without_replaying_evicted_summaries(self):
        for index in range(12):
            run = self.root / str(index)
            run.mkdir()
            (run / "sciel_events.jsonl").write_text(self.log.read_text())
        with patch.object(self.store, "_project", wraps=self.store._project) as project:
            self.assertEqual(len(self.store.discover()), 13)
            self.assertEqual(project.call_count, 13)
            self.assertEqual(len(self.store.discover()), 13)
            self.assertEqual(project.call_count, 13)
            for cache in (self.store._projections, self.store._journals, self.store._checkpoints):
                self.assertLessEqual(len(cache), 8)

    def test_archive_discovery_does_not_observe_or_evict_selected_run_timing(self):
        with patch.object(self.store.timing_monitor, "observe", wraps=self.store.timing_monitor.observe) as observe:
            ident = self.store.discover()[0]["id"]
            observe.assert_not_called()
        self.store.snapshot(ident)
        self.append(event="research", phase="attempt", experiment_id="current")
        selected = self.store.snapshot(ident)["timing"]
        self.assertIsNotNone(selected["current_cycle"]["started_at"])
        for index in range(12):
            run = self.root / str(index)
            run.mkdir()
            (run / "sciel_events.jsonl").write_text(self.log.read_text())
        with patch.object(self.store.timing_monitor, "observe", wraps=self.store.timing_monitor.observe) as observe:
            self.assertEqual(len(self.store.discover()), 13)
            self.store.discover()
            observe.assert_not_called()
        retained = self.store.timing_monitor.snapshot(ident)
        self.assertEqual(retained["current_cycle"]["started_at"], selected["current_cycle"]["started_at"])
        self.assertEqual(retained["coverage"]["gaps"], [])
        self.assertEqual(list(self.store.timing_monitor._states), [ident])

    def test_summary_change_invalidates_scope_and_known_path_does_not_rescan(self):
        ident = self.store.discover()[0]["id"]
        first, _, _ = self.store.stream_update(ident)
        (self.root / "summary.json").write_text('{"engineering_only":true}')
        with patch.object(self.store, "_scan", wraps=self.store._scan) as scan:
            second, kind, snapshot = self.store.stream_update(ident, first)
            self.assertNotEqual(first, second)
            self.assertEqual(kind, "snapshot")
            self.assertEqual(snapshot["run"]["scope"], "engineering")
            self.assertEqual(scan.call_count, 0)


if __name__ == "__main__":
    unittest.main()
