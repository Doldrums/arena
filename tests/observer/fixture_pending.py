"""Small saved-record writers for observer tests, not an execution/recovery engine.

The shapes mirror the pinned journal/cell/wave contracts. Only test tmp directories
are written; no program, model, process controller or upstream package is loaded.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from arena.observers.sciel.compat.models import canonical_bytes, content_hash

checkpoint = SimpleNamespace(save=None)


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RunLog:
    def __init__(self, path):
        self.path = str(path)
        self.run_id, self.segment_id = 'fixture-run', 'fixture-segment'
        self.event_seq = 0
        Path(path).write_bytes(b'')

    def _emit(self, event, **fields):
        self.event_seq += 1
        row = dict(event=event, run_id=self.run_id, segment_id=self.segment_id,
                   event_seq=self.event_seq, timestamp=datetime.now(timezone.utc).isoformat(), **fields)
        with Path(self.path).open('ab') as stream:
            stream.write(canonical_bytes(row) + b'\n')

    def run_start(self, **fields):
        self._emit('run_start', **fields)

    def research_tool(self, **fields):
        self._emit('research_tool', **fields)

    def anchor(self):
        raw = Path(self.path).read_bytes()
        return dict(byte_offset=len(raw), prefix_sha256=hashlib.sha256(raw).hexdigest(),
                    event_seq=self.event_seq, segment_id=self.segment_id)

    def close(self):
        pass


class CellRegistry:
    def __init__(self, root):
        self.root = Path(root)
        self.cells = {}

    def _artifact(self, folder, value):
        ident = content_hash(value)
        _write_json(self.root / 'research_tools/cells' / folder / (ident + '.json'), value)
        return ident

    def ensure_cell(self, island, question, trigger):
        body = dict(schema='sciel-research-cell/1', question=question,
                    origin_island=island, trigger=trigger)
        ident = self._artifact('genesis', body)
        value = dict(id=ident, **body, head_revision=None, active=len(self.cells) < 4,
                     affinities=[island])
        self.cells[ident] = value
        return deepcopy(value)

    def revise(self, ident, *, phase):
        value = self.cells[ident]
        revision = dict(schema='sciel-research-cell-revision/1', cell_id=ident,
            ordinal=1, previous_revision=None, phase=phase, tool_ids=[], evidence=[],
            roles={'creator': value['origin_island']}, summary='', decision={})
        value['head_revision'] = self._artifact('revisions', revision)
        return deepcopy(value)

    def state(self):
        return dict(schema='sciel-research-cells/1', max_active=4,
                    cells={ident:{key:deepcopy(value[key]) for key in
                           ('head_revision', 'active', 'affinities')}
                           for ident, value in self.cells.items()})


class SavedWave:
    def __init__(self, engine, wave):
        self.engine = engine
        self.root = Path(engine.run_dir)
        self.main = self.root / 'sciel_events.jsonl'
        self.directory = self.root / '.parallel' / ('wave-' + str(wave))
        self.directory.mkdir(parents=True)
        self.original_path = engine.log.path
        self.original_seq = engine.log.event_seq
        self.closed = False
        anchor = engine.log.anchor()
        baseline = self.directory / ('a' * 32 + '.baseline.json')
        checkpoint.save(engine, 'baseline', path=baseline)
        (self.root / 'checkpoint.json').write_bytes(baseline.read_bytes())
        self.pending = self.directory / ('a' * 32 + '.journal.jsonl')
        self.pending.write_bytes(b'')
        self.manifest = dict(schema='sciel-wave-transaction/2', wave_id=str(wave), phase='active',
            baseline=baseline.name, baseline_sha256=_digest(baseline), journal=self.pending.name,
            base_journal_bytes=anchor['byte_offset'], base_journal_sha256=anchor['prefix_sha256'])
        _write_json(self.directory / 'transaction.json', self.manifest)
        _write_json(self.root / '.parallel/current.json',
                    dict(schema=self.manifest['schema'], wave_id=str(wave)))
        engine.log.path = str(self.pending)
        engine._parallel_transaction = self

    def commit(self):
        with self.main.open('ab') as stream:
            stream.write(self.pending.read_bytes())
        self.engine.log.path = self.original_path
        checkpoint.save(self.engine, 'committed')
        self.manifest['phase'] = 'committed'
        _write_json(self.directory / 'transaction.json', self.manifest)
        self.engine._parallel_transaction = None
        self.closed = True

    def restore_log(self):
        if not self.closed:
            self.engine.log.path = self.original_path
            self.engine.log.event_seq = self.original_seq
            self.engine._parallel_transaction = None
            self.closed = True


def begin(engine, wave):
    return SavedWave(engine, wave)
