"""Passive monitor timings use inert temporary journals and an injected clock."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from arena.observers.sciel.timing import TimingMonitor


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


class TimingMonitorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / "sciel_events.jsonl"
        self.now = 1000.
        self.monitor = TimingMonitor(clock=lambda: self.now)
        self.append(event="run_start", run_id="r", segment_id="s")

    def append(self, **row):
        with self.log.open("a") as stream:
            stream.write(json.dumps(row) + "\n")

    def hypothesis(self, ident, **extra):
        self.append(event="research", phase="hypothesis", experiment_id=ident, segment_id="s", **extra)

    def test_historical_untimestamped_hypotheses_are_not_backfilled(self):
        self.hypothesis("old")
        before = self.log.read_bytes()
        result = self.monitor.observe("run", self.log)
        self.assertEqual(result["hypotheses"], [])
        self.assertEqual(result["coverage"]["untimed_hypotheses"], 1)
        self.assertIsNone(result["last_hypothesis_age_seconds"])
        self.assertEqual(self.log.read_bytes(), before)
        self.now += 10
        self.hypothesis("new")
        first = self.monitor.observe("run", self.log)
        self.assertEqual(first["hypotheses"][0]["source"], "observed")
        self.now += 15
        self.hypothesis("next")
        second = self.monitor.observe("run", self.log)
        self.assertEqual(second["intervals"]["last_seconds"], 15)
        self.assertEqual(second["intervals"]["source"], "observed")
        self.now += 3
        self.assertEqual(self.monitor.snapshot("run")["last_hypothesis_age_seconds"], 3)

    def test_recorded_intervals_use_monotonic_time_even_if_wall_clock_moves_back(self):
        self.hypothesis("one", timestamp=stamp(100), segment_elapsed_seconds=2)
        self.hypothesis("two", timestamp=stamp(90), segment_elapsed_seconds=14)
        result = self.monitor.observe("run", self.log)
        self.assertEqual(result["intervals"]["last_seconds"], 12)
        self.assertEqual(result["intervals"]["source"], "recorded_monotonic")
        self.assertEqual(result["hypotheses"][0]["source"], "recorded")

    def test_same_poll_burst_has_no_fabricated_zero_interval(self):
        self.monitor.observe("run", self.log)
        self.now += 20
        self.hypothesis("one")
        self.hypothesis("two")
        result = self.monitor.observe("run", self.log)
        self.assertEqual(len(result["hypotheses"]), 2)
        self.assertIsNone(result["intervals"]["last_seconds"])
        self.assertEqual(result["intervals"]["count"], 0)

    def test_restart_preserves_records_but_skips_untimestamped_downtime_appends(self):
        cache = self.root / "monitor-cache"
        self.monitor = TimingMonitor(cache_dir=cache, clock=lambda: self.now)
        self.monitor.observe("run", self.log)
        self.now += 10
        self.hypothesis("observed")
        self.monitor.observe("run", self.log)
        self.hypothesis("during-downtime")
        self.now += 100
        restarted = TimingMonitor(cache_dir=cache, clock=lambda: self.now)
        result = restarted.observe("run", self.log)
        self.assertEqual([row["experiment_id"] for row in result["hypotheses"]], ["observed"])
        self.assertEqual(result["coverage"]["untimed_hypotheses"], 1)
        self.assertEqual(result["coverage"]["gaps"][-1]["reason"], "monitor_restart")
        self.assertIsNone(result["last_hypothesis_age_seconds"])
        self.hypothesis("after-restart")
        result = restarted.observe("run", self.log)
        self.assertIsNone(result["intervals"]["last_seconds"])

    def test_runtime_session_uses_heartbeat_then_terminal_time(self):
        runtime = dict(started_at=stamp(100), heartbeat_at=stamp(160), stage="generating")
        result = self.monitor.observe("run", self.log, runtime)
        self.assertEqual(result["session"]["elapsed_seconds"], 60)
        self.assertIsNone(result["phase"]["elapsed_seconds"])
        runtime["finished_at"] = stamp(175)
        self.now += 1000
        self.assertEqual(self.monitor.snapshot("run", runtime)["session"]["elapsed_seconds"], 75)

    def test_cache_eviction_without_appends_preserves_phase_and_is_not_a_restart(self):
        self.monitor = TimingMonitor(max_runs=1, cache_dir=self.root / "cache", clock=lambda: self.now)
        self.monitor.observe("run", self.log)
        self.append(event="research", phase="attempt", experiment_id="current")
        before = self.monitor.observe("run", self.log)
        self.monitor.observe("archive", self.log)
        self.now += 10
        after = self.monitor.observe("run", self.log)
        self.assertEqual(after["coverage"]["gaps"], [])
        self.assertEqual(after["current_cycle"]["started_at"], before["current_cycle"]["started_at"])
        self.assertEqual(after["current_cycle"]["elapsed_seconds"], 10)

    def test_evicted_monitor_skips_unseen_appends_with_an_eviction_gap(self):
        self.monitor = TimingMonitor(max_runs=1, cache_dir=self.root / "cache", clock=lambda: self.now)
        self.monitor.observe("run", self.log)
        self.monitor.observe("archive", self.log)
        self.hypothesis("while-evicted")
        after = self.monitor.observe("run", self.log)
        self.assertEqual(after["coverage"]["gaps"][-1]["reason"], "cache_eviction")
        self.assertEqual(after["coverage"]["untimed_hypotheses"], 1)
        self.assertEqual(after["hypotheses"], [])

    def test_partial_record_waits_for_newline_and_does_not_duplicate(self):
        self.monitor.observe("run", self.log)
        with self.log.open("a") as stream:
            stream.write(json.dumps(dict(event="research", phase="hypothesis", experiment_id="partial")))
        self.assertEqual(self.monitor.observe("run", self.log)["hypotheses"], [])
        with self.log.open("a") as stream:
            stream.write("\n")
        self.assertEqual(len(self.monitor.observe("run", self.log)["hypotheses"]), 1)
        self.assertEqual(len(self.monitor.observe("run", self.log)["hypotheses"]), 1)

    def test_records_are_bounded_stats_describe_retained_window_and_response_is_detached(self):
        self.monitor = TimingMonitor(max_hypotheses=3, max_runs=1, clock=lambda: self.now)
        for index, seconds in enumerate([100, 110, 130, 160]):
            self.hypothesis(str(index), timestamp=stamp(seconds), segment_elapsed_seconds=seconds)
        result = self.monitor.observe("run", self.log)
        self.assertEqual(result["coverage"]["timed_hypotheses"], 4)
        self.assertEqual(result["coverage"]["retained_hypotheses"], 3)
        self.assertEqual(result["intervals"]["mean_seconds"], 20)
        result["hypotheses"][0]["at"] = "mutated"
        self.assertNotEqual(self.monitor.snapshot("run")["hypotheses"][0]["at"], "mutated")
        self.monitor.observe("other", self.log)
        self.assertIsNone(self.monitor.snapshot("run"))

    def test_cycle_starts_only_from_a_recorded_or_observed_attempt(self):
        self.monitor.observe("run", self.log)
        self.now += 10
        self.append(event="research", phase="attempt", experiment_id="cycle")
        self.monitor.observe("run", self.log)
        self.now += 7
        result = self.monitor.snapshot("run")
        self.assertEqual(result["current_cycle"]["elapsed_seconds"], 7)
        self.assertEqual(result["current_cycle"]["source"], "observed")
        self.append(event="research", phase="conclusion", experiment_id="cycle")
        self.assertIsNone(self.monitor.observe("run", self.log)["current_cycle"])

    def test_recorded_session_and_phase_freeze_at_journal_end_without_runtime(self):
        self.append(event="run_start", run_id="r", segment_id="s2", timestamp=stamp(100))
        self.append(event="research", phase="attempt", experiment_id="cycle", timestamp=stamp(110))
        self.append(event="run_end", timestamp=stamp(125))
        result = self.monitor.observe("run", self.log)
        self.assertEqual(result["session"]["elapsed_seconds"], 25)
        self.assertEqual(result["phase"]["elapsed_seconds"], 15)
        self.now += 10000
        self.assertEqual(self.monitor.snapshot("run")["phase"]["elapsed_seconds"], 15)

    def test_stopped_hypothesis_age_freezes_at_terminal_time(self):
        self.hypothesis("last", timestamp=stamp(150))
        runtime = dict(available=True, active=False, started_at=stamp(100),
                       finished_at=stamp(175), heartbeat_at=stamp(176))
        result = self.monitor.observe("run", self.log, runtime)
        self.assertEqual(result["last_hypothesis_age_seconds"], 25)
        self.assertEqual(result["session"]["elapsed_seconds"], 75)
        self.assertFalse(result["live"])
        self.now += 10000
        self.assertEqual(self.monitor.snapshot("run", runtime)["last_hypothesis_age_seconds"], 25)

    def test_dead_or_stale_writer_freezes_at_heartbeat_without_invented_stop_time(self):
        self.hypothesis("last", timestamp=stamp(150))
        for active, status in [(False, "interrupted"), (None, "stalled")]:
            with self.subTest(status=status):
                runtime = dict(available=True, active=active, status=status,
                               started_at=stamp(100), heartbeat_at=stamp(165))
                result = self.monitor.observe("run", self.log, runtime)
                self.assertEqual(result["last_hypothesis_age_seconds"], 15)
                self.assertEqual(result["session"]["elapsed_seconds"], 65)
                self.assertFalse(result["live"])

    def test_verified_live_writer_advances_between_heartbeats(self):
        self.hypothesis("last", timestamp=stamp(150))
        runtime = dict(available=True, active=True, started_at=stamp(100), heartbeat_at=stamp(160))
        self.now = 163
        result = self.monitor.observe("run", self.log, runtime)
        self.assertEqual(result["session"]["elapsed_seconds"], 63)
        self.assertEqual(result["last_hypothesis_age_seconds"], 13)
        self.assertTrue(result["live"])

    def test_resume_excludes_pause_and_waits_for_current_session_hypothesis(self):
        self.hypothesis("before-pause", timestamp=stamp(110), segment_elapsed_seconds=10)
        self.append(event="run_end", timestamp=stamp(120))
        self.append(event="run_start", run_id="r", segment_id="resumed", timestamp=stamp(500))
        result = self.monitor.observe("run", self.log)
        self.assertIsNone(result["last_hypothesis_age_seconds"])
        self.assertIsNone(result["last_hypothesis_id"])
        self.append(event="research", phase="hypothesis", experiment_id="after-resume",
                    segment_id="resumed", timestamp=stamp(520), segment_elapsed_seconds=20)
        result = self.monitor.observe("run", self.log)
        self.assertIsNone(result["intervals"]["last_seconds"])
        self.append(event="research", phase="hypothesis", experiment_id="next",
                    segment_id="resumed", timestamp=stamp(550), segment_elapsed_seconds=50)
        result = self.monitor.observe("run", self.log)
        self.assertEqual(result["intervals"]["last_seconds"], 30)
        self.assertEqual(result["intervals"]["mean_seconds"], 30)
        self.assertEqual(result["intervals"]["count"], 1)

    def test_old_cache_cross_session_interval_is_removed_without_losing_arrivals(self):
        cache = self.root / "cache"
        self.monitor = TimingMonitor(cache_dir=cache, clock=lambda: self.now)
        self.hypothesis("before", timestamp=stamp(110))
        self.append(event="run_start", run_id="r", segment_id="resumed", timestamp=stamp(500))
        self.append(event="research", phase="hypothesis", experiment_id="after",
                    segment_id="resumed", timestamp=stamp(520))
        self.monitor.observe("run", self.log)
        path = self.monitor._cache_path("run")
        old = json.loads(path.read_text())
        old["hypotheses"][-1].update(interval_seconds=410, interval_source="recorded_wall")
        path.write_text(json.dumps(old))
        restarted = TimingMonitor(cache_dir=cache, clock=lambda: self.now)
        result = restarted.observe("run", self.log)
        self.assertEqual([item["experiment_id"] for item in result["hypotheses"]], ["before", "after"])
        self.assertEqual(result["intervals"]["count"], 0)
        self.assertIsNone(result["intervals"]["mean_seconds"])

        # The same invalid legacy interval is identifiable even when its
        # predecessor was evicted from the bounded hypothesis window.
        old["hypotheses"] = old["hypotheses"][-1:]
        old["hypotheses"][0]["segment_elapsed_seconds"] = 20
        path.write_text(json.dumps(old))
        restarted = TimingMonitor(cache_dir=cache, clock=lambda: self.now)
        self.assertEqual(restarted.observe("run", self.log)["intervals"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
