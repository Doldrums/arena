"""Read-only run discovery and stable journal/checkpoint caches."""
from collections import OrderedDict
import hashlib
import json
from pathlib import Path

from .llm_calls import trace_manifest
from .run_values import _dict, _signature, cache_put


class RunArchive:
    def __init__(self, roots):
        self.roots = list(dict.fromkeys(Path(root).expanduser().resolve() for root in roots))
        self._journals = OrderedDict()
        self._checkpoints = OrderedDict()

    def allowed(self, path):
        return any(path == root or path.is_relative_to(root) for root in self.roots)

    def scan(self):
        runs = {}
        for root in self.roots:
            if root.is_file():
                candidates = [root] if root.name == "sciel_events.jsonl" or (root.name == 'journal.jsonl' and root.parent.name == 'registry') else []
            else:
                candidates = list(root.rglob("sciel_events.jsonl")) + list(root.glob('**/registry/journal.jsonl')) if root.is_dir() else []
            for candidate in candidates:
                try:
                    path = candidate.resolve(strict=True)
                    if candidate.is_symlink() or not path.is_file() or not self.allowed(path):
                        continue
                    if candidate.name == 'journal.jsonl' and any(p.is_symlink() for p in candidate.parents if p == root or p.is_relative_to(root)):
                        continue
                    ident = hashlib.sha256(str(path).encode()).hexdigest()[:20]
                    runs[ident] = path
                except (OSError, RuntimeError):
                    continue
        present = set(runs.values())
        for cache in (self._journals, self._checkpoints):
            for path in list(cache):
                if path not in present:
                    del cache[path]
        return runs

    def projection_signature(self, path):
        checkpoint = path.parent / "checkpoint.json"
        summary = path.parent.parent / "summary.json"
        trace = trace_manifest(path.parent)
        return (_signature(path), _signature(checkpoint), checkpoint.is_symlink(),
                _signature(summary) if self.allowed(summary.resolve()) else None,
                summary.is_symlink(), _signature(trace) if trace is not None else None)

    def journal(self, path):
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
            cache_put(self._journals, path, (signature, rows, list(warnings)))
        return rows, warnings

    def checkpoint(self, path, rows):
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
                cache_put(self._checkpoints, path, (signature, value))
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

    def run_metadata(self, path):
        modified = path.stat().st_mtime
        root = next((root for root in self.roots if path.is_relative_to(root)), path.parent)
        name = str(path.parent.relative_to(root)) if root.is_dir() and path.parent != root else path.parent.name
        engineering_only = False
        summary_path = path.parent.parent / "summary.json"
        try:
            if self.allowed(summary_path.resolve()) and not summary_path.is_symlink():
                summary = _dict(json.loads(summary_path.read_bytes()))
                engineering_only = summary.get("engineering_only") is True
        except (OSError, ValueError, UnicodeError, RecursionError):
            pass
        return dict(modified=modified, name=name, engineering_only=engineering_only)
