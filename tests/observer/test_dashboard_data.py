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


class DashboardDataTests(DashboardDataFixture):
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
