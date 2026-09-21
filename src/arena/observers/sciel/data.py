"""Read-only, dependency-free views of ordinary SCiEL run journals.

This is an observational adapter, not a checkpoint loader or evidence validator.
It never executes sources, imports research runtimes, or follows artifact paths
from journal content. Missing/unmeasured scores stay null. Run termination means
an explicit run_end was recorded; a recent file is not proof of a live process.
"""
from __future__ import annotations

from collections import OrderedDict
import difflib
import json
import math
from pathlib import Path
import threading
import time
import uuid

from .parallel_cost import WaveSpendMonitor
from .effort import EffortMonitor
from .llm_calls import collect_calls, detail as llm_call_detail, metadata as llm_call_metadata
from .timing import TimingMonitor
from .methods import MethodsView
from .workflow import WorkflowView
from .packings import PackingsView
from .research_tools import tool_detail, artifact_detail, cell_detail, job_detail, BackgroundJobView
from .research_pending import PendingResearchView
from .run_archive import RunArchive
from .run_lineage import source_records
from .run_projection import project_run
from .run_runtime import runtime_view
from .run_values import _dict, _safe, _sha, cache_put


class RunStore:
    """Discover only ``sciel_events.jsonl`` under explicitly allowed roots.

    IDs are opaque path digests, not user-supplied file paths. Returned objects
    are detached. A transient checkpoint rewrite uses the last readable copy,
    clearly marked stale; no checkpoint or journal is ever modified.
    """

    def __init__(self, roots: list[Path], *, timing_cache_dir=None):
        self._archive = RunArchive(roots)
        self.roots = self._archive.roots
        self._runs = {}
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
        return self._archive.allowed(path)

    def _scan(self):
        self._runs = self._archive.scan()
        present = set(self._runs.values())
        for cache in (self._projections, self._summaries, self._methods_views,
                self._background_jobs, self._pending_research, self._workflow_views, self._packings_views):
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
            cache_put(self._methods_views, path, MethodsView(path))
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
            cache_put(self._projections, path, (stamp, result['content_version'], result))
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
            cache_put(self._projections, path, (signature, version, projection))
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
                cache_put(self._background_jobs,path,BackgroundJobView(path.parent))
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
            cache_put(self._pending_research,path,PendingResearchView(path.parent))
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
                cache_put(self._packings_views, path, PackingsView(path.parent))
            return self._packings_views[path].page(offset=offset, limit=limit, sort=sort,
                                                 island=island, query=query)

    def workflow_detail(self, run_id, event_id):
        with self._lock:
            return self._workflow(run_id).detail(event_id)

    def _workflow(self, run_id):
        path = self._path(run_id)
        if path not in self._workflow_views:
            cache_put(self._workflow_views, path, WorkflowView(self, run_id))
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

    def _projection_signature(self, path):
        return self._archive.projection_signature(path)

    def _journal(self, path):
        return self._archive.journal(path)

    def _checkpoint(self, path, rows):
        return self._archive.checkpoint(path, rows)

    @staticmethod
    def _runtime(path, start):
        return runtime_view(path, start)

    @staticmethod
    def _sources(checkpoint, rows):
        return source_records(checkpoint, rows)

    def _project(self, ident, path):
        rows, warnings = self._journal(path)
        checkpoint, checkpoint_info, warning = self._checkpoint(path, rows)
        if warning:
            warnings.append(warning)
        return project_run(ident, path, rows=rows, checkpoint=checkpoint,
            checkpoint_info=checkpoint_info, warnings=warnings, **self._archive.run_metadata(path))
