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


class DashboardDataFixture(unittest.TestCase):
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
