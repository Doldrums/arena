"""Read-only, dependency-free views of ordinary SCiEL run journals.

This is an observational adapter, not a checkpoint loader or evidence validator.
It never executes sources, imports research runtimes, or follows artifact paths
from journal content. Missing/unmeasured scores stay null. Run termination means
an explicit run_end was recorded; a recent file is not proof of a live process.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
import difflib
import hashlib
import json
import math
from pathlib import Path
import re
import socket
import threading
import time
import uuid

from .architecture import architecture, start_protocol
from .benchmarks import benchmark_for
from .metric_display import project_metrics
from .population import population_view
from .parallel import parallel_view, runtime_parallel
from .parallel_cost import WaveSpendMonitor
from .effort import EffortMonitor, effort_basis
from .learning import learning_view
from .reliability import reliability_view
from .result_history import result_history_view
from .llm_calls import collect_calls, detail as llm_call_detail, metadata as llm_call_metadata, trace_manifest
from .timing import TimingMonitor
from .methods import MethodsView
from .workflow import WorkflowView
from .packings import PackingsView
from .research_tools import research_tools_view, tool_detail, artifact_detail, cell_detail, job_detail, BackgroundJobView
from .research_pending import PendingResearchView
from .compat.runtime import process_matches


SCHEMA = "sciel-dashboard/1"
_SECRET_KEYS = {"api_key", "authorization", "access_token", "refresh_token", "password", "secret"}
_CODE_KEYS = {"code", "child_code", "parent_code", "code_fragment", "_failed_code"}


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _sha(text):
    return hashlib.sha256(text.encode("utf-8", errors="surrogatepass")).hexdigest()


def _safe(value, *, compact=False, depth=0):
    """JSON-safe copies; never expose common credential fields from config."""
    if depth > 45:
        return "[nested data omitted]"
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                result[str(key)] = "[redacted]"
            elif compact and (key in _CODE_KEYS | {"prompt", "response"}
                    or key == "source" and value.get("schema") == "sciel-initialization/1") and isinstance(item, str):
                result[str(key)] = {"omitted_chars": len(item), "sha256": _sha(item)}
            else:
                result[str(key)] = _safe(item, compact=compact, depth=depth + 1)
        return result
    if isinstance(value, list):
        return [_safe(item, compact=compact, depth=depth + 1) for item in value]
    if isinstance(value, float):
        return _number(value)
    if value is None or type(value) in (str, int, bool):
        return value
    return str(value)


def _signature(path):
    try:
        stat = path.stat()
        return stat.st_ino, stat.st_size, stat.st_mtime_ns
    except OSError:
        return None


def _time(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _iteration(row):
    for value in (row.get("iteration_no"), row.get("iteration"),
                  _dict(row.get("evidence")).get("iteration"), row.get("iter_ref")):
        if type(value) is int:
            return value
    return None


def _seed_record(row):
    return (row.get("event") == "decision" and row.get("policy") == "initialization"
            and row.get("action") == "seed_program" and row.get("schema") == "sciel-initialization/1"
            and isinstance(row.get("program_id"), str))


def _bootstrap_admission(row, outcomes):
    """A portfolio/spawn decision commits admission after its evaluation."""
    if row.get("event") != "decision" or row.get("policy") != "portfolio_seed":
        return None, None
    if row.get("research") is not True:
        return (_number(row.get("score")), None) if row.get("ok", True) is True else (None, None)
    ident = _dict(row.get("meta")).get("research_id")
    record = outcomes.get(ident, {}) if isinstance(ident, str) else {}
    evaluation = _dict(record.get("evaluation"))
    score = _number(record.get("score"))
    if (row.get("ok") is not True or record.get("status") != "evaluated"
            or evaluation.get("ok") is not True or score is None
            or score != _number(evaluation.get("score"))
            or record.get("island") != row.get("island")):
        return None, None
    return score, ident


def _aux_key(row):
    return tuple(row.get(key) if type(row.get(key)) in (str, int) else None
                 for key in ("segment_id", "kind", "reference"))


def _stop_detail(checkpoint, rows):
    reason = _dict(checkpoint.get("research")).get("stopped_reason") or checkpoint.get("_accounting_stopped_reason")
    stopped = next((row for row in reversed(rows)
        if row.get("event") == "research" and row.get("phase") == "aux_stopped"), {})
    error_type = stopped.get("error_type")
    error_type = error_type if isinstance(error_type, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,79}", error_type) else None
    if isinstance(reason, str) and reason.strip():
        # Engine reasons contain exception classes, not provider bodies. Bound
        # historical free text and redact recognizable credentials defensively.
        reason = re.sub(r"(?i)\b(?:sk-[A-Za-z0-9_-]+|bearer\s+[^\s,;]+)", "[redacted]", reason)
        reason = re.sub(r"(?i)\b(?:api_key|token|password|secret)\s*[:=]\s*[^\s,;]+", "[redacted]", reason)
        reason = " ".join(reason.split())[:400]
        reason = reason[0].upper() + reason[1:]
    else:
        reason = "Research auxiliary response stopped" if stopped.get("stage") == "response" else "Research auxiliary request stopped" if stopped else None
    if error_type and reason and error_type not in reason:
        reason += ": " + error_type
    return reason


def _payload(text):
    """Decode only an explicit auxiliary JSON envelope, without repair."""
    if not isinstance(text, str):
        return {}
    text = text.strip()
    if text.startswith(("REFLECTION_JSON:", "CONCLUSION_JSON:")):
        text = text.split(":", 1)[1].strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    try:
        return _dict(json.loads(text))
    except (ValueError, RecursionError):
        return {}


class RunStore:
    """Discover only ``sciel_events.jsonl`` under explicitly allowed roots.

    IDs are opaque path digests, not user-supplied file paths. Returned objects
    are detached. A transient checkpoint rewrite uses the last readable copy,
    clearly marked stale; no checkpoint or journal is ever modified.
    """

    def __init__(self, roots: list[Path], *, timing_cache_dir=None):
        self.roots = list(dict.fromkeys(Path(root).expanduser().resolve() for root in roots))
        self._runs = {}
        self._journals = OrderedDict()
        self._checkpoints = OrderedDict()
        self._projections = OrderedDict()
        self._summaries = {}
        self._version_prefix = uuid.uuid4().hex
        self._content_version = 0
        self._lock = threading.RLock()
        self.timing_monitor = TimingMonitor(cache_dir=timing_cache_dir)
        self.wave_spend_monitor = WaveSpendMonitor()
        self.effort_monitor = EffortMonitor()
        self._timing_targets = {}
        self._timing_scan_at = -math.inf
        self._methods_views = OrderedDict()
        self._background_jobs = OrderedDict()
        self._pending_research = OrderedDict()
        self._workflow_views = OrderedDict()
        self._packings_views = OrderedDict()

    def poll_timings(self):
        """Observe live journal appends even when no browser is connected."""
        with self._lock:
            now = time.monotonic()
            if now - self._timing_scan_at >= 10:
                self._scan()
                self._timing_scan_at = now
                targets = {}
                for ident, path in self._runs.items():
                    if path.name == 'journal.jsonl':
                        continue
                    sidecar = path.parent / 'runtime.json'
                    try:
                        if sidecar.is_symlink() or sidecar.stat().st_size > 65536:
                            continue
                        runtime = json.loads(sidecar.read_bytes())
                        if isinstance(runtime, dict) and runtime.get('status') == 'running':
                            targets[ident] = (path, runtime)
                    except (OSError, ValueError, UnicodeError):
                        continue
                self._timing_targets = targets
            for ident, (path, binding) in self._timing_targets.items():
                runtime = self._runtime(path, binding)
                if runtime.get('active') is True:
                    self.timing_monitor.observe(ident, path, runtime)

    def _allowed(self, path):
        return any(path == root or path.is_relative_to(root) for root in self.roots)

    def _scan(self):
        runs = {}
        for root in self.roots:
            if root.is_file():
                candidates = [root] if root.name == "sciel_events.jsonl" or (root.name == 'journal.jsonl' and root.parent.name == 'registry') else []
            else:
                candidates = list(root.rglob("sciel_events.jsonl")) + list(root.glob('**/registry/journal.jsonl')) if root.is_dir() else []
            for candidate in candidates:
                try:
                    path = candidate.resolve(strict=True)
                    if candidate.is_symlink() or not path.is_file() or not self._allowed(path):
                        continue
                    if candidate.name == 'journal.jsonl' and any(p.is_symlink() for p in candidate.parents if p == root or p.is_relative_to(root)):
                        continue
                    ident = hashlib.sha256(str(path).encode()).hexdigest()[:20]
                    runs[ident] = path
                except (OSError, RuntimeError):
                    continue
        self._runs = runs
        present = set(runs.values())
        for cache in (self._journals, self._checkpoints, self._projections, self._summaries, self._methods_views, self._background_jobs, self._pending_research, self._workflow_views, self._packings_views):
            for path in list(cache):
                if path not in present:
                    del cache[path]

    def _path(self, run_id):
        if run_id not in self._runs:
            self._scan()
        path = self._runs.get(run_id)
        if path is None or not path.is_file() or not self._allowed(path.resolve()):
            raise KeyError("Unknown run")
        return path

    def _methods(self, path):
        if path.name != 'journal.jsonl' or path.parent.name != 'registry':
            raise KeyError('Not a methods run')
        if path not in self._methods_views:
            self._cache_put(self._methods_views, path, MethodsView(path))
        return self._methods_views[path]

    def _methods_projection(self, run_id, path):
        """Internal immutable content; public responses are detached below."""
        view = self._methods(path)
        stamp = view.signature()
        cached = self._projections.get(path)
        if cached is not None and cached[0] == stamp:
            return cached[2]
        result = view.project(run_id)
        self._content_version += 1
        result['content_version'] = f'{self._version_prefix}:{self._content_version}'
        if stamp == view.signature():
            self._cache_put(self._projections, path, (stamp, result['content_version'], result))
        return result

    def _methods_live(self, path, projection):
        view = self._methods(path)
        runtime = view.runtime(projection['methods']['identity'], projection['methods'].get('registry_started_at'))
        run = _safe(projection['run'])
        if runtime['available'] or not run.get('terminal_source'):
            run.update(status=runtime['status'] if runtime['available'] else 'historical', status_reason=runtime.get('reason'))
        return dict(kind='methods', run=run, runtime=_safe(runtime),
            timing=dict(elapsed_seconds=runtime.get('elapsed_seconds'), session=dict(elapsed_seconds=runtime.get('elapsed_seconds'))))

    def _methods_snapshot(self, run_id, path):
        projection = self._methods_projection(run_id, path)
        return dict(_safe(projection), **self._methods_live(path, projection))

    @staticmethod
    def _cache_put(cache, key, value):
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > 8:
            cache.popitem(last=False)

    def _projection_signature(self, path):
        checkpoint = path.parent / "checkpoint.json"
        summary = path.parent.parent / "summary.json"
        trace = trace_manifest(path.parent)
        return (_signature(path), _signature(checkpoint), checkpoint.is_symlink(),
                _signature(summary) if self._allowed(summary.resolve()) else None,
                summary.is_symlink(), _signature(trace) if trace is not None else None)

    def _projection(self, ident, path):
        """Reuse immutable history views until their artifact inputs change."""
        signature = self._projection_signature(path)
        cached = self._projections.get(path)
        if cached is not None and cached[0] == signature:
            self._projections.move_to_end(path)
            return cached[1], cached[2]
        projection = self._project(ident, path)
        self._content_version += 1
        version = f"{self._version_prefix}:{self._content_version}"
        projection[0]["content_version"] = version
        # A concurrent append/rewrite must trigger another read on the next poll.
        if signature == self._projection_signature(path):
            self._cache_put(self._projections, path, (signature, version, projection))
            self._summaries[path] = (signature, projection[0]["run"], projection[3])
        else:
            self._projections.pop(path, None)
            self._summaries.pop(path, None)
        return version, projection

    def _live_view(self, ident, path, metadata, *, observe_timing=True, job_base=None, research_base=None, effort_base=None):
        """Refresh only process state and age; never replay journal history."""
        start, end, modified, stop_detail = metadata
        runtime = self._runtime(path, start)
        if observe_timing:
            runtime["uncommitted_cost"] = self.wave_spend_monitor.observe(path.parent, start)
        if end:
            reason = end.get("reason")
            status = {"paused": "paused", "error": "failed", "failed": "failed",
                "interrupted": "interrupted", "stopped": "stopped",
                "research_stopped": "stopped", "repeat_stopped": "stopped",
                "accounting_stopped": "stopped",
                "cost_limit": "stopped"}.get(reason if isinstance(reason, str) else None, "completed")
        else:
            status = "historical" if time.time() - modified > 86400 else "observing"
            reason = "No run_end recorded; process state is unknown."
            if runtime["status"] in {"running", "stalled", "failed", "interrupted", "paused", "stopped"}:
                status, reason = runtime["status"], runtime["reason"]
        # Listing archives needs status only. Observing every listed journal
        # would evict the active run's timing state and replay its history.
        timing = self.timing_monitor.observe(ident, path, runtime) if observe_timing else None
        result = {"run": {"id": ident, "status": status, "status_reason": reason,
                        "stop_detail": stop_detail if status in {"stopped", "failed", "interrupted", "paused"} else None},
                "runtime": runtime, "timing": timing}
        if effort_base is not None:
            rows, _ = self._journal(path)
            result['effort'] = self.effort_monitor.observe(path.parent, start, rows, effort_base)
        if job_base is not None and job_base.get('available') is True:
            if path not in self._background_jobs:
                self._cache_put(self._background_jobs,path,BackgroundJobView(path.parent))
            result['research_tool_jobs'] = self._background_jobs[path].project(job_base)
        if research_base is not None and research_base.get('available') is True:
            pending = self._research_pending_view(path)
            rows, _ = self._journal(path)
            checkpoint, _, _ = self._checkpoint(path,rows)
            result['research_pending_cells'] = dict(pending.project(rows,research_base.get('cells',[]),checkpoint),
                run_status=status)
        return result

    def _research_pending_view(self, path):
        if path not in self._pending_research:
            self._cache_put(self._pending_research,path,PendingResearchView(path.parent))
        return self._pending_research[path]

    @staticmethod
    def _snapshot_view(projection, live):
        snapshot = _safe(projection[0])
        snapshot["run"].update(_safe(live["run"]))
        snapshot["runtime"] = _safe(live["runtime"])
        snapshot['timing'] = _safe(live['timing'])
        snapshot.pop('_effort_basis', None)
        snapshot['effort'] = _safe(live.get('effort'))
        if 'research_tool_jobs' in live:
            snapshot['research_tools']['jobs'] = _safe(live['research_tool_jobs'])
        if 'research_pending_cells' in live:
            snapshot['research_tools']['pending_cells'] = _safe(live['research_pending_cells'])
        return snapshot

    def _journal(self, path):
        signature = _signature(path)
        cached = self._journals.get(path)
        if cached and cached[0] == signature:
            self._journals.move_to_end(path)
            return cached[1], list(cached[2])
        warnings, rows = [], []
        try:
            raw = path.read_bytes()
        except OSError:
            return [], ["Journal is temporarily unavailable."]
        lines = raw.splitlines()
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            # RunLog commits records with a newline. Even syntactically complete
            # JSON at EOF can still be an in-progress write, not a durable row.
            if index == len(lines) - 1 and not raw.endswith(b"\n"):
                warnings.append("Incomplete trailing journal record; waiting for its writer.")
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("event is not an object")
            except (ValueError, UnicodeError, RecursionError):
                warnings.append(f"Unreadable journal record at line {index + 1}; skipped.")
                continue
            rows.append(row)
        # A reused output directory can contain a fresh run after an old one.
        # Do not combine its scores, sources or counters with the previous run.
        starts = [i for i, row in enumerate(rows) if row.get("event") == "run_start"]
        if starts:
            latest = rows[starts[-1]].get("run_id")
            if latest:
                first = next((i for i, row in enumerate(rows) if row.get("run_id") == latest), starts[-1])
                if first:
                    warnings.append("Earlier runs in this journal are excluded from the current run view.")
                rows = [row for row in rows[first:] if row.get("run_id") in (None, latest)]
        # A resumed segment can restore an older checkpoint after a crash. Its
        # explicit anchor supersedes the abandoned suffix, including research
        # writes and sources, not just its score counters. Keep the new segment.
        lineage = []
        for row in rows:
            if row.get("event") == "checkpoint_restore":
                anchor = _dict(_dict(row.get("provenance")).get("journal_anchor"))
                if anchor:
                    segment_start = next((i for i in range(len(lineage) - 1, -1, -1)
                        if lineage[i].get("event") == "run_start"
                        and lineage[i].get("segment_id") == row.get("segment_id")), None)
                    prior = lineage[:segment_start] if segment_start is not None else []
                    anchor_index = next((i for i in range(len(prior) - 1, -1, -1)
                        if (prior[i].get("segment_id"), prior[i].get("event_seq"))
                        == (anchor.get("segment_id"), anchor.get("event_seq"))), None)
                    if anchor_index is not None:
                        discarded = segment_start - anchor_index - 1
                        if discarded:
                            warnings.append(f"Checkpoint restore discarded {discarded} abandoned journal records from the current lineage.")
                            lineage = lineage[:anchor_index + 1] + lineage[segment_start:]
                    else:
                        warnings.append("Checkpoint restore anchor is unavailable; earlier journal ancestry could not be resolved.")
            lineage.append(row)
        rows = lineage
        # Cache only an unchanged read. Appends/replacements are read on next poll.
        if signature == _signature(path):
            self._cache_put(self._journals, path, (signature, rows, list(warnings)))
        return rows, warnings

    def _checkpoint(self, path, rows):
        checkpoint_path = path.parent / "checkpoint.json"
        signature = _signature(checkpoint_path)
        cached = self._checkpoints.get(path)
        status = "missing"
        warning = None
        value = None
        if signature is not None:
            try:
                # A sibling name is trusted; a symlink into another run is not.
                if checkpoint_path.is_symlink() or checkpoint_path.resolve().parent != path.parent:
                    raise ValueError("checkpoint escapes its run directory")
                if cached and cached[0] == signature:
                    value = cached[1]
                else:
                    value = json.loads(checkpoint_path.read_bytes())
                    if not isinstance(value, dict) or signature != _signature(checkpoint_path):
                        raise ValueError("checkpoint changed while reading")
                run_id = next((row.get("run_id") for row in reversed(rows) if row.get("run_id")), None)
                checkpoint_run = _dict(value.get("provenance")).get("run_id")
                if run_id and checkpoint_run and checkpoint_run != run_id:
                    raise ValueError("checkpoint belongs to another run")
                self._cache_put(self._checkpoints, path, (signature, value))
                status = "available"
            except (OSError, ValueError, UnicodeError, RecursionError):
                status = "updating"
                warning = "Checkpoint is unreadable or changing; journal data remains available."
                value = None
        if value is None and cached:
            candidate = cached[1]
            run_id = next((row.get("run_id") for row in reversed(rows) if row.get("run_id")), None)
            checkpoint_run = _dict(candidate.get("provenance")).get("run_id")
            if not (run_id and checkpoint_run and run_id != checkpoint_run):
                value, status = candidate, "stale"
                warning = "Showing the last readable checkpoint while the current file is unavailable."
        return value or {}, {"available": value is not None, "status": status,
                             "stale": status == "stale"}, warning

    @staticmethod
    def _runtime(path, start):
        """Observe a same-run heartbeat; an extant file alone is not liveness."""
        result = dict(available=False, status="unknown", stage=None, active=None,
            heartbeat_at=None, heartbeat_age_seconds=None, pid=None, reason=None,
            verification="unavailable", stale_after_seconds=None)
        sidecar = path.parent / "runtime.json"
        try:
            if sidecar.is_symlink() or sidecar.resolve().parent != path.parent:
                return result
            if sidecar.stat().st_size > 65536:
                raise ValueError("oversized runtime sidecar")
            record = json.loads(sidecar.read_bytes())
            if not isinstance(record, dict) or record.get("schema") != "sciel-runtime/1":
                raise ValueError("unknown runtime schema")
        except FileNotFoundError:
            return result
        except (OSError, ValueError, UnicodeError, RecursionError):
            result.update(verification="unreadable", reason="Runtime telemetry is temporarily unreadable.")
            return result
        result["available"] = True
        if not start.get("run_id") or not start.get("segment_id") or any(
                record.get(key) != start.get(key) for key in ("run_id", "segment_id")):
            result.update(verification="different_run", reason="Runtime telemetry is not bound to this journal segment.")
            return result
        for key in ("stage", "heartbeat_at", "pid", "reason", "started_at", "finished_at",
                    "runtime_id", "error_type", "stale_after_seconds"):
            result[key] = record.get(key)
        result['parallel'] = runtime_parallel(record.get('parallel'))
        status = record.get("status")
        if status in {"completed", "paused", "stopped", "failed", "interrupted"}:
            result.update(status=status, active=False, verification="terminal_recorded")
            return result
        if status != "running":
            result.update(verification="unknown_status", reason="Runtime status is not recognized.")
            return result
        try:
            heartbeat = datetime.fromisoformat(record["heartbeat_at"].replace("Z", "+00:00"))
            if heartbeat.tzinfo is None:
                raise ValueError("heartbeat needs timezone")
            age = time.time() - heartbeat.timestamp()
            if not math.isfinite(age):
                raise ValueError("invalid heartbeat age")
            result["heartbeat_age_seconds"] = max(0, age)
        except (KeyError, TypeError, AttributeError, ValueError, OverflowError):
            result.update(verification="invalid_timestamp", reason="Runtime heartbeat time is unavailable.")
            return result
        if record.get("hostname") != socket.gethostname():
            result.update(verification="different_host", reason="The writer belongs to another host; its process state is unknown.")
            return result
        same_process = process_matches(record)
        if same_process is False:
            result.update(status="interrupted", active=False, verification="process_not_running",
                          reason="The recorded writer process is no longer present; no terminal runtime record was written.")
        elif same_process is None:
            result.update(verification="process_unverified", reason="The writer process identity cannot be verified.")
        else:
            limit = _number(record.get("stale_after_seconds"))
            if limit is None or limit <= 0 or age < -2:
                result.update(verification="invalid_timestamp", reason="Runtime freshness cannot be established.")
            elif age > limit:
                result.update(status="stalled", verification="stale_heartbeat",
                              reason="The same writer process exists, but its heartbeat is stale.")
            else:
                result.update(status="running", active=True, verification="live_process", reason=None)
        return result

    @staticmethod
    def _boundary(checkpoint, rows):
        anchor = _dict(_dict(checkpoint.get("provenance")).get("journal_anchor"))
        if anchor:
            for i, row in enumerate(rows):
                if (row.get("segment_id"), row.get("event_seq")) == (anchor.get("segment_id"), anchor.get("event_seq")):
                    return i
        return None

    @staticmethod
    def _sources(checkpoint, rows):
        programs = _dict(checkpoint.get("db")).get("programs", [])
        if isinstance(programs, dict):
            programs = list(programs.values())
        result = {}
        for program in _list(programs):
            if isinstance(program, dict) and isinstance(program.get("id"), str):
                result[program["id"]] = dict(program, code_source="checkpoint")
        for row in rows:
            if _seed_record(row):
                code = row.get("source")
                if isinstance(code, str) and row.get("source_sha256") == _sha(code):
                    ident = row["program_id"]
                    result[ident] = dict(id=ident, code=code, parent_id=None,
                        score=_number(row.get("score")) if row.get("measured") is True else None,
                        island=row.get('island'), origin='seed',
                        code_source="journal.initialization.source")
            ident, code = row.get("child_id"), row.get("child_code")
            if row.get("event") == "iteration" and isinstance(ident, str) and isinstance(code, str):
                result[ident] = dict(result.get(ident, {}), id=ident, code=code, parent_id=row.get("parent_id"),
                    parent_ids=row.get('parent_ids', _dict(row.get('meta')).get('parent_ids')),
                    island=row.get('island'), score=row.get("child_score"), code_source="journal.child_code")
        return result

    @staticmethod
    def _trial(ident):
        return dict(id=ident, candidate_id=None, parent_id=None, iteration=None, island=None,
                    status="pending", score=None, actual_delta=None, forecast_verdict=None,
                    hypothesis=None, conclusion=None, source_sha256=None, code_available=False)

    @staticmethod
    def _plot_lineage(curves, trials, sources, evidence, rows):
        """Join explicit identities; never guess parents from score or iteration.

        A checkpoint-only migrant has a parent but no new evaluation coordinate.
        A research ID can alias a bootstrap storage ID only when its complete
        recorded fingerprint and ancestry identify exactly one stored program.
        """
        def parents(*records):
            result = []
            for record in records:
                if not isinstance(record, dict):
                    continue
                values = [record.get('parent_id')] + _list(record.get('parent_ids'))
                for value in values:
                    if isinstance(value, str) and value and value not in result:
                        result.append(value)
            return result

        def short_hypothesis(value):
            if isinstance(value, dict):
                value = value.get('text') or value.get('hypothesis')
            return value[:320] if isinstance(value, str) else None

        programs, fingerprints, bootstrap, seeds = {}, {}, {}, []
        for row in rows:
            if _seed_record(row) and row.get('program_id') in sources:
                seeds.append(row)
            if row.get('event') == 'decision' and row.get('policy') == 'portfolio_seed':
                research_id = _dict(row.get('meta')).get('research_id')
                if isinstance(research_id, str):
                    bootstrap[research_id] = row
        for ident, source in sources.items():
            # _trials adds research source aliases; handle them through their
            # explicit trial below instead of inventing a second stored member.
            if ident in evidence:
                continue
            origin = source.get('origin')
            programs[ident] = dict(candidate_id=ident, alias_ids=[], parent_ids=parents(source),
                experiment_id=None, iteration=None, score=_number(source.get('score')),
                best_score=None, cost_total=None, island=source.get('island'), operator=None,
                status='stored', hypothesis=short_hypothesis(source.get('card')),
                parent_score=_number(sources.get(source.get('parent_id'), {}).get('score')),
                model=None, code_available=isinstance(source.get('code'), str), origin=origin,
                llm_available=False,
                lineage_note='Migrated copy; no separate evaluation or creation time was recorded.'
                    if origin == 'migrant' else 'Stored program; evaluation position was not recorded.')
            if isinstance(source.get('code'), str):
                fingerprint = (_sha(source['code']), source.get('parent_id'), source.get('island'),
                               source.get('origin'), _number(source.get('score')))
                fingerprints.setdefault(fingerprint, []).append(ident)
        for row in seeds:
            program = programs.get(row['program_id'])
            if program is not None:
                program.update(iteration=0, status='seed' if row.get('measured') is True else 'unmeasured',
                    score=_number(row.get('score')) if row.get('measured') is True else None,
                    parent_ids=[], lineage_note='Initial source, evaluated once and copied into islands.')

        trial_programs = {}
        for trial in trials:
            ident = trial['id']
            candidate = trial.get('candidate_id') or ident
            admission = bootstrap.get(ident, {})
            aliases = [ident] if candidate != ident else []
            if trial.get('candidate_id') is None and trial.get('status') == 'evaluated':
                fingerprint = (trial.get('source_sha256'), trial.get('parent_id'), trial.get('island'),
                               admission.get('action', 'gen'), _number(trial.get('score')))
                matches = fingerprints.get(fingerprint, [])
                if len(matches) == 1:
                    aliases.append(matches[0])
            base = programs.get(candidate) or next((programs[alias] for alias in aliases if alias in programs), {})
            program = dict(base, candidate_id=candidate, alias_ids=aliases,
                experiment_id=ident if ident in evidence else None,
                parent_ids=parents(evidence.get(ident), {'parent_id':trial.get('parent_id')}, base),
                iteration=trial.get('iteration'), score=trial.get('score') if trial.get('status') == 'evaluated' else None,
                best_score=None, cost_total=None, island=trial.get('island'),
                operator=trial.get('operator'), status=trial.get('status'),
                hypothesis=short_hypothesis(trial.get('hypothesis')),
                parent_score=trial.get('parent_score'), model=trial.get('model') or admission.get('model_used'),
                code_available=trial.get('code_available') is True,
                llm_available=ident in evidence or bool(trial.get('model') or admission.get('model_used')),
                origin=admission.get('action') or base.get('origin'), lineage_note=None)
            for alias in aliases:
                programs.pop(alias, None)
            programs[candidate] = program
            trial_programs[ident] = program

        for point in curves:
            index = point.pop('_row_index')
            row = rows[index]
            point['point_id'] = f"{row.get('segment_id', 'legacy')}:{row.get('event_seq', index)}:{point.get('kind', 'iteration')}"
            point['segment_id'] = row.get('segment_id')
            research_id = (point.get('experiment_id') or _dict(row.get('meta')).get('research_id'))
            program = trial_programs.get(research_id) if isinstance(research_id, str) else None
            if point.get('kind') == 'seed':
                program = programs.get(row.get('program_id'))
                point['candidate_ids'] = [seed['program_id'] for seed in seeds
                    if seed.get('source_sha256') == row.get('source_sha256')
                    and seed.get('score') == row.get('score') and seed.get('measured') is True]
            elif program is None and isinstance(row.get('child_id'), str):
                program = programs.get(row['child_id'])
            metadata = program or dict(candidate_id=None, alias_ids=[], experiment_id=research_id,
                parent_ids=parents(row, _dict(row.get('meta'))), island=row.get('island'),
                operator=row.get('op_used'), status=row.get('reason') or 'unknown',
                hypothesis=short_hypothesis(_dict(row.get('meta')).get('hypothesis')),
                parent_score=_number(sources.get(row.get('parent_id'), {}).get('score')),
                model=row.get('model_used'), code_available=False, llm_available=False)
            for key in ('candidate_id', 'alias_ids', 'experiment_id', 'parent_ids', 'island', 'operator',
                        'status', 'hypothesis', 'parent_score', 'model', 'code_available', 'llm_available', 'origin', 'lineage_note'):
                point[key] = metadata.get(key)
            if program is not None:
                point['score'] = program['score']
                if point.get('kind') == 'bootstrap' and program.get('iteration') is not None:
                    point['iteration'] = program['iteration']
                program.update(point_id=point['point_id'], iteration=point['iteration'],
                    best_score=point['best_score'], cost_total=point['cost_total'])
                if point.get('kind') == 'seed':
                    for seed_id in point['candidate_ids']:
                        if seed_id in programs:
                            programs[seed_id].update(point_id=point['point_id'],
                                cost_total=point['cost_total'], best_score=point['best_score'])
            point['kind'] = point.get('kind', 'iteration')
        return list(programs.values())

    def _trials(self, checkpoint, rows, sources):
        trials, evidence, responses = {}, {}, {}
        research = _dict(checkpoint.get("research"))
        knowledge = _dict(research.get("knowledge"))
        for record in _list(knowledge.get("experiments")) + _list(research.get("queue")):
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                evidence[record["id"]] = dict(record)
        for record in _dict(research.get("pending")).values():
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                evidence[record["id"]] = dict(record)
        for row in rows:
            if row.get("event") == "research" and row.get("phase") in ("attempt", "hypothesis", "outcome"):
                record = _dict(row.get("evidence"))
                ident = row.get("experiment_id") or record.get("id")
                if isinstance(ident, str):
                    evidence.setdefault(ident, {}).update(record)
                    if isinstance(row.get("response"), str):
                        responses[ident] = row["response"]
        for ident, record in evidence.items():
            trial = self._trial(ident)
            for key in ("parent_id", "iteration", "island", "status", "forecast_verdict", "hypothesis", "source_sha256"):
                trial[key] = record.get(key, trial[key])
            trial.update(candidate_id=record.get("child_id"), score=_number(record.get("score")),
                         actual_delta=_number(record.get("actual_delta")),
                         parent_score=_number(record.get("parent_score")), failure=record.get("failure"),
                         operator=record.get("operator"), injected_ids=_list(record.get("injected_ids")),
                         generation_cost=_number(record.get("generation_cost")))
            # A failed evaluator's sentinel score is not a measured candidate.
            if trial["status"] != "evaluated":
                trial["score"] = trial["actual_delta"] = None
            trials[ident] = trial
        for index, row in enumerate(rows):
            if row.get("event") != "iteration":
                continue
            meta = _dict(row.get("meta"))
            ident = meta.get("research_id") or row.get("child_id")
            if not isinstance(ident, str):
                # dup_cap/no-child summaries can omit research_id, even though
                # each rejected G already has an ordinary research attempt.
                matching = [trial for trial in trials.values() if trial.get("iteration") == _iteration(row)
                            and trial.get("island") == row.get("island")]
                ident = matching[-1]["id"] if matching else f"iteration:{_iteration(row)}:{index}"
            trial = trials.setdefault(ident, self._trial(ident))
            trial.update(iteration=_iteration(row), island=row.get("island"),
                         candidate_id=row.get("child_id") or trial.get("candidate_id"),
                         parent_id=row.get("parent_id") or trial.get("parent_id"),
                         model=row.get("model_used"), operator=row.get("op_used") or meta.get("op_used"),
                         cost=_number(row.get("cost")), iteration_reason=row.get("reason"))
            if ident not in evidence:
                trial.update(status=row.get("reason") or ("evaluated" if "child_score" in row else "unknown"),
                             score=_number(row.get("child_score")), hypothesis=meta.get("hypothesis"))
            if row.get('reason') == 'remeasurement':
                trial.update(status='remeasurement', score=None, actual_delta=None,
                    measurement_program_id=row.get('measurement_program_id'),
                    measurement_score=_number(row.get('measurement_score')) if row.get('measurement_ok') is True else None,
                    measurement_ok=row.get('measurement_ok'))
            if trial["score"] is not None and trial.get("parent_score") is None:
                parent = sources.get(trial["parent_id"], {})
                trial["parent_score"] = _number(parent.get("score"))
                if trial["parent_score"] is not None:
                    trial["actual_delta"] = trial["score"] - trial["parent_score"]
        conclusions = _dict(research.get("conclusions")).copy()
        for row in rows:
            if row.get("event") == "research" and row.get("phase") == "conclusion":
                conclusions[row.get("experiment_id")] = row
        for ident, trial in trials.items():
            conclusion = _dict(conclusions.get(ident))
            trial["conclusion"] = conclusion.get("llm")
            trial["conclusion_status"] = conclusion.get("status")
            source = sources.get(trial.get("candidate_id"), {})
            code = source.get("code")
            expected = trial.get("source_sha256")
            if not isinstance(code, str):
                record = evidence.get(ident, {})
                fragment = record.get("code_fragment")
                if isinstance(fragment, str) and fragment and expected and _sha(fragment) == expected:
                    code = fragment
                    source = dict(code=code, code_source="journal.code_fragment", parent_id=trial.get("parent_id"))
                else:
                    # Full Python fence only, and only when exact evaluated SHA matches.
                    for match in re.finditer(r"^```(?:python)?[^\S\n]*\n([\s\S]*?)^```[^\S\n]*$",
                                             responses.get(ident, ""), re.MULTILINE):
                        options = (match.group(1), match.group(1).rstrip("\n"), match.group(1).strip())
                        code = next((value for value in options if expected and _sha(value) == expected), None)
                        if code is not None:
                            source = dict(code=code, code_source="journal.hash_bound_response", parent_id=trial.get("parent_id"))
                            break
            if isinstance(code, str) and (not expected or _sha(code) == expected):
                trial["code_available"] = True
                sources[ident] = source
                trial["source_sha256"] = expected or _sha(code)
            trial["change_excerpt_available"] = bool(evidence.get(ident, {}).get("change_excerpt"))
        return sorted(trials.values(), key=lambda item: (item["iteration"] if type(item["iteration"]) is int else -1, item["id"])), evidence

    @staticmethod
    def _lessons(checkpoint, rows, boundary):
        research = _dict(checkpoint.get("research"))
        known = {}
        history_complete = bool(rows and rows[0].get("event") == "run_start"
                                and rows[0].get("resumed") is False)
        saved = [lesson for lesson in _list(_dict(research.get("knowledge")).get("lessons"))
                 if isinstance(lesson, dict) and isinstance(lesson.get("id"), str)]

        def overlay_checkpoint():
            current = {lesson["id"] for lesson in saved}
            for ident, lesson in known.items():
                if ident not in current and lesson["status"] == "active":
                    # Capacity eviction is not a model-authorized retirement.
                    lesson["status"] = "not_retained"
            for lesson in saved:
                ident = lesson["id"]
                prior = known.get(ident, {})
                exposures = set(prior.get("_exposures", ()))
                exposures.update(value for value in _list(lesson.get("exposure_ids")) if isinstance(value, str))
                known[ident] = dict(prior, **lesson, status="active", data_source="checkpoint",
                    _exposures=exposures,
                    _exposures_known=prior.get("_exposures_known", False) or isinstance(lesson.get("exposure_ids"), list))

        # With no known prefix, the checkpoint's current subset is all we can
        # safely place in time. Do not apply potentially older journal writes.
        if checkpoint and boundary is None:
            overlay_checkpoint()
            replay_rows = []
        else:
            replay_rows = rows
        auxiliary = {}
        for index, row in enumerate(replay_rows):
            if row.get("event") == "research":
                phase = row.get("phase")
                if phase == "aux_result":
                    key = (row.get("segment_id"), row.get("kind"), row.get("reference"))
                    auxiliary[key] = {} if row.get("response_truncated") else _payload(row.get("response"))
                proposals, ids, retired = [], [], []
                if phase == "conclusion" and row.get("status") == "parsed":
                    proposals = _list(_dict(row.get("llm")).get("lessons"))
                    ids = _list(row.get("accepted_lesson_ids"))
                elif phase == "reflection" and isinstance(row.get("applied"), dict) and not row.get("error"):
                    key = (row.get("segment_id"), "reflection", row.get("through"))
                    proposals = _list(auxiliary.get(key, {}).get("lessons"))
                    ids = _list(row["applied"].get("lesson_ids"))
                    retired = _list(row["applied"].get("retired_ids"))
                # Only an explicit accepted ID gives a proposal a lesson identity.
                # When ordering is ambiguous, preserve that ID without claiming
                # that an arbitrary proposed text was admitted.
                for offset, ident in enumerate(ids):
                    if not isinstance(ident, str):
                        continue
                    proposal = proposals[offset] if len(ids) == len(proposals) else {}
                    if isinstance(proposal, dict):
                        prior = known.get(ident, {})
                        combined = list(dict.fromkeys(_list(prior.get("evidence_ids")) + _list(proposal.get("evidence_ids"))))
                        known[ident] = dict(prior, **proposal, id=ident, status="active", data_source="journal",
                            _exposures=set(prior.get("_exposures", ())),
                            _exposures_known=prior.get("_exposures_known", history_complete))
                        known[ident]["evidence_ids"] = combined
                        if isinstance(known[ident].get("rule"), str):
                            known[ident]["rule"] = known[ident]["rule"].strip()
                for ident in retired:
                    if isinstance(ident, str) and ident in known:
                        known[ident]["status"] = "retired"
                if phase == "outcome":
                    record = _dict(row.get("evidence"))
                    observation = row.get("experiment_id") or record.get("id")
                    if isinstance(observation, str) and record.get("generation_dispatch") != "not_dispatched":
                        for ident in _list(record.get("injected_ids")):
                            if isinstance(ident, str) and ident in known:
                                known[ident]["_exposures"].add(observation)
                                # These are known direct exposures, not source
                                # support, inherited benefit or causal effects.
                                known[ident]["_exposures_known"] = True
            if boundary == index:
                overlay_checkpoint()
        result = []
        for ident, lesson in known.items():
            result.append(dict(id=ident, rule=lesson.get("rule", ""), polarity=lesson.get("polarity"),
                scope=lesson.get("scope"), branch=lesson.get("branch"),
                evidence_ids=_list(lesson.get("evidence_ids")), confidence=_number(lesson.get("confidence")),
                exposure_count=len(lesson.get("_exposures", ())) if lesson.get("_exposures_known") else None,
                exposure_count_scope="known_direct", status=lesson["status"],
                data_source=lesson["data_source"]))
        return result

    @staticmethod
    def _geometry(trials, evidence):
        for trial in sorted(trials, key=lambda item: item.get("score") if item.get("score") is not None else -math.inf, reverse=True):
            if trial.get("status") != "evaluated" or trial.get("score") is None:
                continue
            record = evidence.get(trial["id"], {})
            geometry = _dict(_dict(record.get("evaluation")).get("native_geometry"))
            numeric = _dict(geometry.get("numeric"))
            centers, radii = numeric.get("centers"), numeric.get("radii")
            if geometry.get("source_sha256") != trial.get("source_sha256") or not trial.get("source_sha256"):
                continue
            if not isinstance(centers, list) or not isinstance(radii, list) or not centers or len(centers) != len(radii):
                continue
            if not all(isinstance(center, list) and len(center) == 2 and all(_number(x) is not None for x in center) for center in centers):
                continue
            if not all(_number(radius) is not None and radius >= 0 for radius in radii):
                continue
            return dict(candidate_id=trial["candidate_id"] or trial["id"], experiment_id=trial["id"],
                source_sha256=trial["source_sha256"], centers=centers, radii=radii,
                score=trial["score"], kind="persisted_native_geometry", verified_by_dashboard=False)
        return None

    def _project(self, ident, path):
        rows, warnings = self._journal(path)
        checkpoint, checkpoint_info, warning = self._checkpoint(path, rows)
        if warning:
            warnings.append(warning)
        boundary = self._boundary(checkpoint, rows)
        starts = [row for row in rows if row.get("event") == "run_start"]
        start = starts[-1] if starts else {}
        last_start = max((i for i, row in enumerate(rows) if row.get("event") == "run_start"), default=-1)
        ends = [row for row in rows[last_start + 1:] if row.get("event") == "run_end"]
        end = ends[-1] if ends else {}
        modified = path.stat().st_mtime
        sources = self._sources(checkpoint, rows)
        trials, evidence = self._trials(checkpoint, rows, sources)
        lessons = self._lessons(checkpoint, rows, boundary)
        metric = _dict(checkpoint.get("research")).get("metric")
        if not isinstance(metric, dict):
            metric = next((record.get("metric") for record in evidence.values() if isinstance(record.get("metric"), dict)), None)
        curves = []
        best = None
        observed_seed_score = None
        cost = None
        cost_source = "unavailable"
        cost_exact = False
        unknown_charge = (bool(checkpoint.get("_accounting_stopped_reason"))
            or any(_dict(receipt).get('unknown_cost') is True
                   for receipt in _list(checkpoint.get('provider_recoveries'))))
        outcomes, bootstrap_candidates, aux_returns = {}, [], {}
        evaluations, iterations, remeasurements = None, None, None
        for index, row in enumerate(rows):
            if row.get("event") == "research":
                key = _aux_key(row)
                if row.get("phase") == "aux_start":
                    aux_returns.pop(key, None)
                elif row.get("phase") == "aux_result" and _number(row.get("cost")) is not None and row["cost"] >= 0:
                    aux_returns[key] = row.get("call_index")
                elif (row.get("phase") == "aux_stopped" and row.get("error_type") == "LLMError"
                        and row.get("stage") != "response" and row.get("generation_returned") is not True
                        and row.get("current_call_cost_unknown") is not False
                        and _number(row.get("cost")) is None):
                    matched = key in aux_returns and (row.get("call_index") is None
                        or row["call_index"] == aux_returns[key])
                    if not matched:
                        unknown_charge = True
            if row.get("event") == "research" and row.get("phase") == "outcome":
                record = _dict(row.get("evidence"))
                research_id = row.get("experiment_id")
                if isinstance(research_id, str) and record.get("id") == research_id:
                    outcomes[research_id] = record
            bootstrap_score, bootstrap_id = _bootstrap_admission(row, outcomes)
            if (row.get("current_call_cost_unknown") is True
                    or row.get("event") == "decision" and row.get("policy") == "cost_accounting"
                    and row.get("action") == "unknown_cost"
                    or row.get("event") == "run_end" and row.get("reason") == "accounting_stopped"):
                unknown_charge = True
            if row.get("event") == "run_start":
                counters = _dict(row.get("counters"))
                if _number(counters.get("cost_total")) is not None:
                    cost = counters["cost_total"]
                    cost_source, cost_exact = "run_start.counters", True
                # Fresh run_start precedes seed evaluation; its default 0 is
                # an initialized counter, not an observed zero-quality seed.
                if row.get("resumed") is True and _number(counters.get("seed_score")) is not None:
                    seed_score = counters["seed_score"]
                    best = max(best, seed_score) if best is not None else seed_score
                if type(counters.get("iteration_no")) is int:
                    iterations = counters["iteration_no"]
                if type(counters.get("B_evals")) is int:
                    evaluations = counters["B_evals"]
                if type(counters.get('n_remeasurements')) is int and counters['n_remeasurements'] >= 0:
                    remeasurements = counters['n_remeasurements']
            if (row.get('event') == 'decision' and row.get('policy') == 'candidate_measurement'
                    and row.get('action') == 'start' and row.get('remeasurement') is True):
                remeasurements = (remeasurements or 0) + 1
            if _seed_record(row) and row.get("measured") is True:
                seed_score = _number(row.get("seed_score"))
                if seed_score is not None:
                    best = max(best, seed_score) if best is not None else seed_score
                    # One evaluated source can seed several islands. It is one
                    # baseline observation, not one evaluation per stored copy.
                    if observed_seed_score is None:
                        observed_seed_score = seed_score
                        curves.append(dict(iteration=0, evaluations=0, score=seed_score,
                            best_score=seed_score, cost_total=_number(cost),
                            event_seq=row.get("event_seq"), kind="seed", _row_index=index))
            parent_score = _number(_dict(row.get("evidence")).get("parent_score"))
            if parent_score is not None:
                best = max(best, parent_score) if best is not None else parent_score
            charge = None
            if row.get("event") == "iteration":
                charge = _number(row.get("cost"))
                iterations = _iteration(row)
                evaluations = _number(row.get("B_evals"))
            elif row.get("event") == "research" and row.get("phase") == "aux_result":
                charge = _number(row.get("cost"))
            elif row.get("event") == "decision" and row.get("policy") in {"portfolio_seed", "paradigm_validation"}:
                # Bootstrap/spawn has no ordinary iteration row. Charge its
                # decision once, never the same outcome/validation trace again.
                charge = _number(row.get("cost"))
            elif (row.get("event") == "decision" and row.get("policy") == "cost_accounting"
                    and row.get("action") == "unknown_cost"):
                # A stopped worker has no iteration row. Its earlier returned
                # calls are recorded here before the final checkpoint is saved.
                charge = _number(row.get("known_cost"))
            if charge is not None:
                cost = (cost or 0) + charge
                cost_source, cost_exact = "logged_known_charges", False
            if _number(row.get("cost_total")) is not None:
                cost, cost_source, cost_exact = row["cost_total"], "journal.cost_total", True
            if _number(row.get("pop_best")) is not None:
                best = row["pop_best"]
            elif row.get("event") == "iteration" and _number(row.get("child_score")) is not None:
                best = max(best, row["child_score"]) if best is not None else row["child_score"]
            if bootstrap_score is not None:
                best = max(best, bootstrap_score) if best is not None else bootstrap_score
                bootstrap_candidates.append((bootstrap_score, bootstrap_id))
            if boundary == index and _number(checkpoint.get("cost_total")) is not None:
                cost, cost_source, cost_exact = checkpoint["cost_total"], "checkpoint.cost_total", True
            if row.get("event") == "iteration":
                curves.append(dict(iteration=iterations, evaluations=evaluations,
                    score=_number(row.get("child_score")), best_score=_number(best),
                    cost_total=_number(cost), event_seq=row.get("event_seq"), _row_index=index))
            elif bootstrap_score is not None:
                curves.append(dict(iteration=iterations, evaluations=evaluations,
                    score=bootstrap_score, best_score=_number(best), cost_total=_number(cost),
                    event_seq=row.get("event_seq"), kind="bootstrap", experiment_id=bootstrap_id,
                    _row_index=index))
        if not end and checkpoint and boundary is None and _number(checkpoint.get("cost_total")) is not None:
            cost, cost_source, cost_exact = checkpoint["cost_total"], "checkpoint.cost_total", True
        db = _dict(checkpoint.get("db"))
        best_program = sources.get(db.get("pop_best_id"), {})
        reported_best = [_number(end.get("pop_best")), _number(best_program.get("score")), _number(best)]
        finite_best = [value for value in reported_best if value is not None]
        best = finite_best[0] if end and reported_best[0] is not None else max(finite_best) if finite_best else None
        best_candidate_id = None
        if best is not None:
            # A checkpoint can lag a newly journaled child. Never pair its old
            # program ID with a newer score belonging to a different candidate.
            if _number(best_program.get("score")) == best:
                best_candidate_id = db.get("pop_best_id")
            if best_candidate_id is None:
                best_candidate_id = next((row["child_id"] for row in rows
                    if row.get("event") == "iteration" and isinstance(row.get("child_id"), str)
                    and _number(row.get("child_score")) == best), None)
            if best_candidate_id is None:
                best_candidate_id = next((row['measurement_program_id'] for row in rows
                    if row.get('event') == 'iteration' and row.get('reason') == 'remeasurement'
                    and row.get('measurement_ok') is True and isinstance(row.get('measurement_program_id'), str)
                    and _number(row.get('measurement_score')) == best), None)
            if best_candidate_id is None:
                best_candidate_id = next((research_id for score, research_id in bootstrap_candidates
                    if score == best and research_id is not None), None)
            if best_candidate_id is None:
                best_candidate_id = next((program["id"] for program in sources.values()
                    if isinstance(program.get("id"), str) and _number(program.get("score")) == best), None)
        iterations = max((value for value in [iterations, checkpoint.get("iteration_no"), end.get("iteration_no")]
                          if type(value) is int), default=None)
        evaluations = max((value for value in [evaluations, checkpoint.get("B_evals"), end.get("B_evals")]
                           if type(value) is int), default=None)
        remeasurements = max((value for value in [remeasurements, checkpoint.get('n_remeasurements'), end.get('n_remeasurements')]
                              if type(value) is int and value >= 0), default=None)
        task = start.get("task") or _dict(checkpoint.get("identity")).get("task") or _dict(checkpoint.get("config")).get("task")
        root = next((root for root in self.roots if path.is_relative_to(root)), path.parent)
        name = str(path.parent.relative_to(root)) if root.is_dir() and path.parent != root else path.parent.name
        scope, scope_note = "recorded_run", None
        summary_path = path.parent.parent / "summary.json"
        try:
            if self._allowed(summary_path.resolve()) and not summary_path.is_symlink():
                summary = _dict(json.loads(summary_path.read_bytes()))
                if summary.get("engineering_only") is True:
                    scope = "engineering"
                    scope_note = "Engineering validation run; these scores do not establish benchmark superiority or memory benefit."
        except (OSError, ValueError, UnicodeError, RecursionError):
            pass
        run = dict(id=ident, name=name, path=str(path.parent), task=task,
            last_modified=_time(modified), event_count=len(rows),
            best_score=best, cost_total=_number(cost), run_id=start.get("run_id"),
            seed=start.get("seed"), models=_list(start.get("models")), scope=scope, scope_note=scope_note)
        events = []
        for index, row in enumerate(rows):
            phase = row.get("phase")
            summary = str(phase or row.get("event", "event"))
            for key in ("experiment_id", "child_id", "reason", "status"):
                if row.get(key) is not None:
                    summary += " · " + str(row[key])[:160]
            events.append(dict(seq=index + 1, event=row.get("event"), phase=phase,
                event_seq=row.get("event_seq"), segment_id=row.get("segment_id"),
                iteration=_iteration(row), summary=summary, data=_safe(row, compact=True)))
        reflections = sum(row.get("event") == "research" and row.get("phase") == "reflection" for row in rows)
        config = start.get("config") if isinstance(start.get("config"), dict) else _dict(checkpoint.get("config"))
        cost_status = "reported" if cost_exact else "known_logged_lower_bound" if cost is not None else "unavailable"
        if cost is not None and _dict(config.get("llm")).get("cost_reporting") == "estimated_uncached_token_rates":
            cost_status = "estimated"
            cost_source = "estimated_uncached_token_rates / " + cost_source
        if unknown_charge:
            warning = "At least one LLM charge is unknown; recorded spend excludes that call and is incomplete."
            if cost_status == "estimated":
                warning += " The recorded portion uses token-rate estimates, not provider billing."
            warnings.append(warning)
            if cost is not None:
                cost_status = "known_logged_lower_bound"
                cost_source = "unknown_charge / " + cost_source
        programs = self._plot_lineage(curves, trials, sources, evidence, rows)
        measured_results = max((value for value in (
            checkpoint.get('n_evaluation_results'), end.get('n_evaluation_results'),
            *(row.get('n_evaluation_results') for row in rows if row.get('policy') == 'output_novelty'))
            if type(value) is int and value >= 0), default=None)
        repeated_outputs = max((value for value in (
            checkpoint.get('n_output_repeats'), end.get('n_output_repeats'),
            *(row.get('n_output_repeats') for row in rows if row.get('policy') == 'output_novelty'))
            if type(value) is int and value >= 0), default=None)
        snapshot = dict(schema=SCHEMA, run=run, stats=dict(iterations=iterations, evaluations=evaluations,
            remeasurements=remeasurements,
            measured_results=measured_results, repeated_outputs=repeated_outputs,
            attempts=len(trials), hypotheses=sum(isinstance(item.get("hypothesis"), dict) for item in trials),
            lessons=sum(item["status"] == "active" for item in lessons), reflections=reflections,
            cost_total=_number(cost), cost_source=cost_source,
            cost_status=cost_status,
            best_score=best, seed_score=observed_seed_score if observed_seed_score is not None
                else _number(end.get("seed_score", checkpoint.get("seed_score")))),
            curves=curves, programs=programs, trials=trials, hypotheses=[item for item in trials if isinstance(item.get("hypothesis"), dict)],
            lessons=lessons, events=events, warnings=warnings, checkpoint=checkpoint_info, metric=metric,
            architecture=architecture(start, checkpoint, rows),
            research_tools=research_tools_view(start, checkpoint, rows),
            start_protocol=start_protocol(start, checkpoint, rows),
            population=population_view(checkpoint, rows, start, sources),
            parallel=parallel_view(start, checkpoint, rows),
            learning=learning_view(start, checkpoint, rows),
            reliability=reliability_view(start, checkpoint, rows, lessons),
            result_history=result_history_view(checkpoint, rows, sources),
            benchmark=None,
            best_candidate_id=best_candidate_id, geometry=self._geometry(trials, evidence))
        display = project_metrics(snapshot, checkpoint, rows, sources, evidence)
        snapshot['benchmark'] = benchmark_for(task, display.metric, best,
            metric_display=snapshot['stats']['best_metric_display'])
        snapshot['_effort_basis'] = effort_basis(rows, sources, best_candidate_id, best,
            _dict(checkpoint.get('identity')).get('task_hash'), iterations)
        run['committed_effort'] = dict(scope='committed_journal', ordinary_iterations=iterations,
            ordinary_successful_evaluations=evaluations, known_llm_usd=_number(cost), cost_status=cost_status,
            configured_models=_list(start.get('models')),
            note='Committed accounting only. Physical pending receipts and actual model use require the selected run view.')
        return snapshot, sources, evidence, (start, end, modified, _stop_detail(checkpoint, rows[last_start + 1:]))

    def discover(self):
        with self._lock:
            self._scan()
            result = []
            for ident, path in self._runs.items():
                try:
                    if path.name == 'journal.jsonl':
                        projection = self._methods_projection(ident, path)
                        result.append(self._methods_live(path, projection)['run'])
                        continue
                    cached = self._summaries.get(path)
                    if cached is not None and cached[0] == self._projection_signature(path):
                        _, base, metadata = cached
                    else:
                        _, projection = self._projection(ident, path)
                        base, metadata = projection[0]["run"], projection[3]
                    run = _safe(base)
                    run.update(_safe(self._live_view(ident, path, metadata, observe_timing=False)["run"]))
                    result.append(run)
                except OSError:
                    continue
            return sorted(result, key=lambda run: run["last_modified"], reverse=True)

    def snapshot(self, run_id):
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                return self._methods_snapshot(run_id, path)
            _, projection = self._projection(run_id, path)
            return self._snapshot_view(projection, self._live_view(run_id, path, projection[3],
                job_base=projection[0]['research_tools']['jobs'],research_base=projection[0]['research_tools'],
                effort_base=projection[0].get('_effort_basis')))

    def stream_update(self, run_id, previous_version=None):
        """Full content on change; tiny runtime-only frames between writes."""
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                projection = self._methods_projection(run_id, path)
                version = projection['content_version']
                live = self._methods_live(path, projection)
                if version == previous_version:
                    return version, 'runtime', live
                return version, 'snapshot', dict(_safe(projection), **live)
            version, projection = self._projection(run_id, path)
            live = self._live_view(run_id, path, projection[3],job_base=projection[0]['research_tools']['jobs'],
                research_base=projection[0]['research_tools'],effort_base=projection[0].get('_effort_basis'))
            if version == previous_version:
                # Recent hypothesis timestamps ride on content snapshots only.
                live['timing'] = {key: value for key, value in live['timing'].items()
                                  if key != 'hypotheses'}
                return version, "runtime", _safe(live)
            return version, "snapshot", self._snapshot_view(projection, live)

    def workflow(self, run_id, *, limit=60, before=None, actor='all', query=''):
        with self._lock:
            return self._workflow(run_id).page(limit=limit, before=before, actor=actor, query=query)

    def packings(self, run_id, *, offset=0, limit=120, sort='score', island='all', query=''):
        with self._lock:
            path = self._path(run_id)
            if path not in self._packings_views:
                self._cache_put(self._packings_views, path, PackingsView(path.parent))
            return self._packings_views[path].page(offset=offset, limit=limit, sort=sort,
                                                 island=island, query=query)

    def workflow_detail(self, run_id, event_id):
        with self._lock:
            return self._workflow(run_id).detail(event_id)

    def _workflow(self, run_id):
        path = self._path(run_id)
        if path not in self._workflow_views:
            self._cache_put(self._workflow_views, path, WorkflowView(self, run_id))
        return self._workflow_views[path]

    def llm_calls(self, run_id, *, offset=0, limit=50, query=''):
        with self._lock:
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
                raise ValueError('Invalid call page')
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                raise KeyError('Use methods proposal endpoint')
            rows, warnings = self._journal(path)
            calls = [llm_call_metadata(call) for call in collect_calls(path.parent, rows)]
            if query:
                needle = str(query).lower()[:256]
                calls = [call for call in calls if needle in ' '.join(str(call.get(key) or '')
                    for key in ('id', 'role', 'reference', 'experiment_id', 'model', 'status', 'iteration')).lower()]
            total = len(calls)
            return _safe(dict(calls=calls[offset:offset + limit], total=total, offset=offset,
                next_offset=offset + limit if offset + limit < total else None,
                warnings=warnings,
                note='Exact saved text only. Missing historical prompts and responses are not reconstructed.'))

    def llm_call(self, run_id, call_id):
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                return self._methods(path).proposal_detail(call_id)
            rows, _ = self._journal(path)
            call = next((call for call in collect_calls(path.parent, rows) if call['id'] == call_id), None)
            if call is None:
                raise KeyError('Unknown LLM call')
            return _safe(llm_call_detail(path.parent, call))

    def research_tool(self, run_id, tool_id):
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                raise KeyError('Not an island Engine run')
            rows, _ = self._journal(path)
            return _safe(tool_detail(path.parent, tool_id, rows))

    def research_tool_artifact(self, run_id, receipt_id):
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                raise KeyError('Not an island Engine run')
            rows, _ = self._journal(path)
            try:
                return _safe(artifact_detail(path.parent, receipt_id, rows))
            except KeyError:
                _, projection = self._projection(run_id,path)
                pending = self._research_pending_view(path)
                checkpoint, _, _ = self._checkpoint(path,rows)
                pending.project(rows,projection[0]['research_tools']['cells'],checkpoint)
                body = artifact_detail(path.parent,receipt_id,pending.rows)
                if body.get('kind')!='proposal':
                    raise KeyError('Only pending model proposals are exposed by this view')
                return _safe(dict(body,publication='pending',committed=False))

    def research_cell(self, run_id, cell_id):
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                raise KeyError('Not an island Engine run')
            rows, _ = self._journal(path)
            checkpoint, _, _ = self._checkpoint(path, rows)
            _, projection = self._projection(run_id,path)
            committed = projection[0]['research_tools']['cells']
            pending = self._research_pending_view(path)
            overlay = next((cell for cell in pending.project(rows,committed,checkpoint)['cells'] if cell['id']==cell_id),None)
            try:
                body = cell_detail(path.parent,cell_id,checkpoint,rows)
            except KeyError:
                body = None
            if overlay:
                return _safe(pending.detail(overlay,body))
            if body is None:
                raise KeyError('Cell is not recorded in the selected lineage or authenticated pending wave')
            return _safe(body)

    def research_tool_job(self, run_id, job_id):
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                raise KeyError('Not an island Engine run')
            rows, _ = self._journal(path)
            checkpoint, _, _ = self._checkpoint(path, rows)
            return _safe(job_detail(path.parent,job_id,checkpoint))

    def detail(self, run_id, candidate_id):
        with self._lock:
            path = self._path(run_id)
            if path.name == 'journal.jsonl':
                return self._methods(path).method_detail(candidate_id)
            _, projection = self._projection(run_id, self._path(run_id))
            snapshot, sources, evidence = projection[:3]
            trial = next((trial for trial in snapshot["trials"]
                          if candidate_id in (trial["id"], trial["candidate_id"])), None)
            source = sources.get(trial["id"], {}) if trial else sources.get(candidate_id, {})
            if trial is None and not source:
                raise KeyError("Unknown candidate")
            code = source.get("code")
            parent_id = trial.get("parent_id") if trial else source.get("parent_id")
            parent_code = sources.get(parent_id, {}).get("code")
            code = code if isinstance(code, str) else None
            parent_code = parent_code if isinstance(parent_code, str) else None
            excerpt = evidence.get(trial["id"], {}).get("change_excerpt") if trial else None
            if code is not None and parent_code is not None:
                diff = "".join(difflib.unified_diff(parent_code.splitlines(keepends=True), code.splitlines(keepends=True),
                    fromfile=str(parent_id), tofile=str(candidate_id), n=3))
                diff_kind = "full_sources"
            else:
                diff = excerpt if isinstance(excerpt, str) and excerpt else None
                diff_kind = "recorded_excerpt" if diff else "unavailable"
            displayed = trial or next((p for p in snapshot['programs']
                if candidate_id == p['candidate_id'] or candidate_id in p.get('alias_ids', [])), {})
            return _safe(dict(id=candidate_id, code=code, parent_code=parent_code, parent_id=parent_id,
                diff=diff, diff_kind=diff_kind, source_sha256=_sha(code) if code is not None else None,
                parent_source_sha256=_sha(parent_code) if parent_code is not None else None,
                code_source=source.get("code_source"), trial=trial,
                **{key: displayed.get(key)
                    for key in ('metric_display', 'parent_metric_display', 'display_delta')},
                result_history=snapshot["result_history"]["by_program"].get(
                    (trial.get("candidate_id") or candidate_id) if trial else candidate_id)))
