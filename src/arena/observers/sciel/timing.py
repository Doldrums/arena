"""Bounded, passive journal timing; never writes experiment artifacts.

Call ``observe`` from a server-owned poller, independently of browser clients.
Old untimestamped records are counted but never assigned invented event times.
Optional cache files preserve observations; appends during monitor downtime are
a coverage gap unless the writer itself recorded their timestamps.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import threading
import time
import uuid


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _seconds(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def _stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _difference(end, start):
    a, b = _seconds(end), _seconds(start)
    return a - b if a is not None and b is not None and a >= b else None


class TimingMonitor:
    def __init__(self, *, max_runs=8, max_hypotheses=200, cache_dir=None, clock=time.time):
        self.max_runs = max(1, int(max_runs))
        self.max_hypotheses = max(1, int(max_hypotheses))
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.clock = clock
        self._monitor_id = uuid.uuid4().hex
        self._states = OrderedDict()
        self._lock = threading.RLock()

    def _cache_path(self, key):
        return self.cache_dir / (hashlib.sha256(str(key).encode()).hexdigest() + ".json")

    def _new(self, path, stat, now):
        return dict(schema="sciel-timing-state/1", monitor_id=self._monitor_id,
            path=str(path), inode=[stat.st_dev, stat.st_ino],
            offset=0, baseline_offset=stat.st_size, discarding=False,
            observed_since=now, last_observed_at=None, observation_epoch=uuid.uuid4().hex,
            run_id=None, segment_id=None, phase=None, current_cycle=None, runtime_stage=None,
            session_start=None, session_end=None, hypotheses=[], timed_hypotheses=0,
            untimed_hypotheses=0, last_hypothesis_timed=None, gaps=[])

    def _load(self, key, path, stat, now):
        state = None
        if self.cache_dir is not None:
            try:
                cached = self._cache_path(key)
                if cached.stat().st_size <= 524288:
                    value = json.loads(cached.read_bytes())
                    if (isinstance(value, dict) and value.get("schema") == "sciel-timing-state/1"
                            and value.get("path") == str(path)
                            and value.get("inode") == [stat.st_dev, stat.st_ino]
                            and type(value.get("offset")) is int and 0 <= value["offset"] <= stat.st_size
                            and isinstance(value.get("hypotheses"), list)
                            and isinstance(value.get("gaps"), list)
                            and type(value.get("timed_hypotheses")) is int
                            and type(value.get("untimed_hypotheses")) is int):
                        state = value
            except (OSError, ValueError, TypeError, RecursionError):
                pass
        if state is None:
            return self._new(path, stat, now)
        state["hypotheses"] = state["hypotheses"][-self.max_hypotheses:]
        # Repair only demonstrably cross-session intervals in older monitor
        # caches. Preserve recorded/observed arrivals; never rewrite journals.
        for prior, item in zip(state["hypotheses"], state["hypotheses"][1:]):
            if item.get("segment_id") != prior.get("segment_id"):
                item["interval_seconds"] = item["interval_source"] = None
        for item in state["hypotheses"]:
            elapsed, interval = _number(item.get("segment_elapsed_seconds")), _number(item.get("interval_seconds"))
            if item.get("interval_source") == "recorded_wall" and elapsed is not None and interval is not None and interval > elapsed:
                # Also covers a boundary whose predecessor fell out of the
                # retained window: the interval cannot predate this session.
                item["interval_seconds"] = item["interval_source"] = None
        if state["hypotheses"] and state["hypotheses"][-1].get("segment_id") != state.get("segment_id"):
            state["last_hypothesis_timed"] = None
        same_monitor = state.get("monitor_id") == self._monitor_id
        if not state.get("monitor_id"):
            # Old caches could label LRU reloads as restarts. Their provenance
            # cannot distinguish the two; retain only the honest coverage gap.
            for gap in state["gaps"]:
                if isinstance(gap, dict) and gap.get("reason") == "monitor_restart":
                    gap["reason"] = "legacy_observation_gap"
        state["monitor_id"] = self._monitor_id
        if same_monitor and state["offset"] == stat.st_size:
            return state  # no missed journal data: retain phase/cycle clocks
        state["gaps"] = (state["gaps"] + [dict(
            **{"from": state.get("last_observed_at"), "to": now},
            reason="cache_eviction" if same_monitor else "monitor_restart")])[-10:]
        state["baseline_offset"] = stat.st_size
        state["observation_epoch"] = uuid.uuid4().hex
        # A phase could have changed while the monitor was away.
        state["phase"] = state["current_cycle"] = None
        state["runtime_stage"] = None
        return state

    def _save(self, key, state):
        if self.cache_dir is None:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_path(key)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, allow_nan=False), encoding="utf-8")
            temporary.replace(path)
        except (OSError, ValueError):
            # Observational persistence must never interrupt a run or the board.
            pass

    def _consume(self, state, row, observed, now, batch):
        recorded = row.get("timestamp")
        at = recorded if _seconds(recorded) is not None else now if observed else None
        source = "recorded" if at == recorded and at is not None else "observed" if at else None
        event, phase = row.get("event"), row.get("phase")
        if event == "run_start":
            if state["run_id"] is not None and row.get("run_id") != state["run_id"]:
                state["hypotheses"] = []
                state["timed_hypotheses"] = state["untimed_hypotheses"] = 0
                state["last_hypothesis_timed"] = None
            state["run_id"], state["segment_id"] = row.get("run_id"), row.get("segment_id")
            state["session_start"], state["session_end"] = at, None
            # A resumed session starts a new interval series. The wall-clock
            # pause is not time spent generating the next hypothesis.
            state["last_hypothesis_timed"] = None
            state["phase"] = state["current_cycle"] = None
            state["runtime_stage"] = None
        if at is not None:
            state["last_event_at"] = at
        if event == "run_end":
            state["session_end"] = at
            state["current_cycle"] = None
        if event != "research":
            return
        name = {"attempt": "generating", "hypothesis": "evaluating", "outcome": "research",
                "aux_start": "research", "conclusion": "research", "reflection": "research"}.get(phase)
        if name and (state["phase"] is None or state["phase"]["name"] != name):
            state["phase"] = dict(name=name, started_at=at, source=source)
        ident = row.get("experiment_id")
        if phase == "attempt":
            state["current_cycle"] = dict(experiment_id=ident, started_at=at, source=source)
        elif phase in {"conclusion", "conclusion_rejected"}:
            if state["current_cycle"] and state["current_cycle"].get("experiment_id") == ident:
                state["current_cycle"] = None
        if phase != "hypothesis":
            return
        if at is None:
            state["untimed_hypotheses"] += 1
            state["last_hypothesis_timed"] = False
            return
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        item = dict(experiment_id=ident, at=at, source=source, interval_seconds=None,
            interval_source=None, iteration=row.get("iteration", evidence.get("iteration")),
            segment_id=row.get("segment_id"), event_seq=row.get("event_seq"),
            segment_elapsed_seconds=_number(row.get("segment_elapsed_seconds")),
            observation_epoch=state["observation_epoch"], batch=batch)
        prior = state["hypotheses"][-1] if state["hypotheses"] and state.get("last_hypothesis_timed") else None
        if prior and item["segment_id"] == prior.get("segment_id"):
            a, b = item["segment_elapsed_seconds"], prior.get("segment_elapsed_seconds")
            both_recorded = source == prior.get("source") == "recorded"
            if both_recorded and item["segment_id"] is not None and item["segment_id"] == prior.get("segment_id") and a is not None and b is not None and a >= b:
                item["interval_seconds"], item["interval_source"] = a - b, "recorded_monotonic"
            elif both_recorded:
                item["interval_seconds"] = _difference(at, prior.get("at"))
                item["interval_source"] = "recorded_wall"
            elif (source == prior.get("source") == "observed"
                    and prior.get("observation_epoch") == state["observation_epoch"]
                    and prior.get("batch") != batch):
                item["interval_seconds"] = _difference(at, prior.get("at"))
                item["interval_source"] = "observed"
        state["hypotheses"].append(item)
        del state["hypotheses"][:-self.max_hypotheses]
        state["timed_hypotheses"] += 1
        state["last_hypothesis_timed"] = True

    def observe(self, run_key, journal_path, runtime=None):
        """Poll committed new records; call even when no browser is connected."""
        with self._lock:
            path, now = Path(journal_path).resolve(), _stamp(self.clock())
            stat = path.stat()
            state = self._states.get(run_key)
            if state is None:
                state = self._load(run_key, path, stat, now)
                self._states[run_key] = state
            elif state["inode"] != [stat.st_dev, stat.st_ino] or stat.st_size < state["offset"]:
                state = self._new(path, stat, now)
                state["gaps"] = [dict(reason="journal_reset", **{"from": None, "to": now})]
                self._states[run_key] = state
            self._states.move_to_end(run_key)
            while len(self._states) > self.max_runs:
                self._states.popitem(last=False)
            batch, consumed = uuid.uuid4().hex, 0
            with path.open("rb") as stream:
                stream.seek(state["offset"])
                while consumed < 4 * 1024 * 1024:
                    raw = stream.readline(2 * 1024 * 1024)
                    if not raw:
                        break
                    consumed += len(raw)
                    if not raw.endswith(b"\n"):
                        if len(raw) < 2 * 1024 * 1024:
                            break  # uncommitted trailing record
                        state["discarding"] = True
                        state["offset"] = stream.tell()
                        continue
                    state["offset"] = stream.tell()
                    if state["discarding"]:
                        state["discarding"] = False
                        continue
                    try:
                        row = json.loads(raw)
                        if isinstance(row, dict):
                            self._consume(state, row, state["offset"] > state["baseline_offset"], now, batch)
                    except (ValueError, UnicodeError, TypeError, RecursionError):
                        continue
            runtime = runtime if isinstance(runtime, dict) else {}
            stage = runtime.get("stage")
            if isinstance(stage, str) and stage != state.get("runtime_stage"):
                if not state["phase"] or state["phase"]["name"] != stage:
                    known = state.get("runtime_stage") is not None and runtime.get("active") is True
                    state["phase"] = dict(name=stage, started_at=now if known else None,
                                          source="observed" if known else None)
                state["runtime_stage"] = stage
            state["last_observed_at"] = now
            self._save(run_key, state)
            return self.snapshot(run_key, runtime)

    def snapshot(self, run_key, runtime=None):
        with self._lock:
            state = self._states.get(run_key)
            if state is None:
                return None
            now = _stamp(self.clock())
            runtime = runtime if isinstance(runtime, dict) else {}
            # Only a verified live writer advances clocks past its heartbeat.
            # Terminal and interrupted writers freeze at the last recorded
            # boundary; loading an archive must not manufacture execution time.
            live = runtime.get("active") is True and not runtime.get("finished_at") and not state.get("session_end")
            terminal = runtime.get("finished_at") or state.get("session_end")
            as_of = now if live else (terminal or runtime.get("heartbeat_at") or
                     (state.get("last_event_at") if "available" in runtime else now))
            start = runtime.get("started_at")
            end = as_of if live else runtime.get("finished_at") or runtime.get("heartbeat_at")
            session_source = "runtime"
            if _seconds(start) is None or _seconds(end) is None:
                start, end = state.get("session_start"), as_of
                session_source = "journal" if start and end else None
            session = dict(started_at=start, as_of=end, elapsed_seconds=_difference(end, start), source=session_source)
            latest = state["hypotheses"][-1] if state["hypotheses"] and state.get("last_hypothesis_timed") else None
            intervals = [item["interval_seconds"] for item in state["hypotheses"]
                         if _number(item.get("interval_seconds")) is not None]
            sources = {item["interval_source"] for item in state["hypotheses"]
                       if item.get("interval_seconds") is not None}
            phase, cycle = deepcopy(state["phase"]), deepcopy(state["current_cycle"])
            for item in (phase, cycle):
                if item is not None:
                    item["elapsed_seconds"] = _difference(as_of, item.get("started_at"))
            hypotheses = [{key: value for key, value in item.items()
                           if key not in {"batch", "observation_epoch"}} for item in state["hypotheses"]]
            return dict(schema="sciel-timing/1", observed_since=state["observed_since"],
                as_of=as_of, live=bool(live), last_hypothesis_id=latest.get("experiment_id") if latest else None,
                last_observed_at=state["last_observed_at"],
                coverage=dict(timed_hypotheses=state["timed_hypotheses"],
                    untimed_hypotheses=state["untimed_hypotheses"], retained_hypotheses=len(hypotheses),
                    gaps=deepcopy(state["gaps"])), session=session, phase=phase, current_cycle=cycle,
                last_hypothesis_age_seconds=_difference(as_of, latest["at"]) if latest else None,
                intervals=dict(last_seconds=latest.get("interval_seconds") if latest else None,
                    median_seconds=statistics.median(intervals) if intervals else None,
                    mean_seconds=statistics.mean(intervals) if intervals else None,
                    count=len(intervals), source=next(iter(sources)) if len(sources) == 1 else "mixed" if sources else None),
                hypotheses=hypotheses)
