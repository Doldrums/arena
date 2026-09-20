"""Read-only gallery of saved, source-bound evaluator layouts.

Only known native geometry contracts are supported. Validation reconstructs
saved numeric arrays; it never imports a candidate or invokes an evaluator.
Physical receipts are preferred to duplicate journal copies of one invocation.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

from .compat.native_geometry import parse_artifact, validate_binding, validate_geometry
from .compat.repeat_support import NATIVE_GEOMETRY_TASK_EVALUATORS
from .llm_calls import _open_regular

SCHEMA = 'sciel-packings/1'
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 16 * 1024 * 1024
_HASH = re.compile(r'[0-9a-f]{64}\Z')


def _dict(value):
    return value if isinstance(value, dict) else {}


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _digest(value, *, ascii=False):
    return _sha(json.dumps(value, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=ascii, allow_nan=False).encode())


def _text(value):
    return value if isinstance(value, str) and len(value) <= 512 else None


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('nonfinite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def _signature(path):
    try:
        s = path.stat()
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    except OSError:
        return None


class PackingsView:
    """Incremental journal and signature-cached receipt index for one allowed run.

    Polls are throttled; unchanged terminal receipt bodies are never reread.
    Appended journal bytes are parsed once. Replacements/truncations reset that
    index, and each page is detached from cached evidence.
    """
    def __init__(self, root, *, clock=time.monotonic, refresh_seconds=3):
        self.root = Path(root).resolve()
        self.clock, self.refresh_seconds = clock, refresh_seconds
        self._last_refresh = -math.inf
        self._physical = {}
        self._journal = {}
        self._journal_signature = None
        self._offset = 0
        self._tail = b''
        self._start = {}
        self._links = {}
        self._journal_errors = 0
        self._journal_items = {}
        self._checkpoint_signature = None
        self._checkpoint = {}
        self._items = []
        self._unavailable = Counter()
        self._pending = 0
        self._supported = False
        self._version = None
        self._islands = []
        self._alias_signature = None
        self._alias_cache = {}
        self._rebuild_signature = None
        self._checkpoint_matches = True
        self._warnings = []

    def _safe(self, path):
        try:
            relative = path.relative_to(self.root)
            current = self.root
            for part in relative.parts:
                current /= part
                if current.is_symlink():
                    return False
            return path.resolve().is_relative_to(self.root)
        except (OSError, ValueError, RuntimeError):
            return False

    def _read(self, path, maximum=MAX_JSON_BYTES):
        if not self._safe(path):
            raise ValueError('unsafe artifact path')
        before = _signature(path)
        if before is None or before[2] > maximum:
            raise ValueError('missing or oversized artifact')
        with _open_regular(path) as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns,
                    opened.st_ctime_ns) != before:
                raise ValueError('artifact replaced before open')
            raw = stream.read(maximum + 1)
        if len(raw) > maximum or before != _signature(path):
            raise ValueError('artifact changed during read')
        value = _json(raw)
        if not isinstance(value, dict):
            raise ValueError('expected object artifact')
        return value, _sha(raw)

    def _read_checkpoint(self):
        path = self.root / 'checkpoint.json'
        signature = (self._safe(path), _signature(path))
        if signature != self._checkpoint_signature:
            try:
                self._checkpoint, _ = self._read(path, maximum=128 * 1024 * 1024)
            except (OSError, ValueError, UnicodeError, RecursionError):
                self._checkpoint = {}
            self._checkpoint_signature = signature

    def _consume(self, row, offset):
        if row.get('event') == 'run_start':
            self._start = {k: row.get(k) for k in ('run_id', 'task', 'task_hash')}
        if row.get('policy') == 'evaluation' and row.get('action') == 'result':
            ident = _text(row.get('evaluation_id')) or f'journal:{offset}'
            # Identical journal replay keeps a single measurement. A conflicting
            # duplicate is withheld, rather than choosing whichever appeared last.
            projection = {k: row.get(k) for k in ('source_sha256', 'ok', 'score', 'cases',
                'reached', 'confirmed', 'artifacts', 'timestamp', 'iteration_no_before', 'evaluation_id', 'run_id')}
            projection['artifacts'] = {'native_geometry': _dict(row.get('artifacts')).get('native_geometry')}
            projection['_event_sha256'] = _digest(row)
            old = self._journal.get(ident)
            if old is not None and any(old.get(k) != projection.get(k) for k in
                    ('source_sha256', 'ok', 'score', 'cases', 'reached', 'confirmed', 'artifacts')):
                projection = {'evaluation_id': ident, '_conflict': True}
            self._journal[ident] = projection
        if row.get('event') == 'iteration':
            meta = _dict(row.get('meta'))
            ids = meta.get('evaluation_ids', [])
            if isinstance(ids, list):
                for ident in ids:
                    if isinstance(ident, str):
                        self._links[ident] = {'iteration': row.get('iteration_no'),
                            'island_id': row.get('island')}
                # Only the final accepted measurement may own this child ID.
                if ids and isinstance(row.get('child_id'), str):
                    self._links[ids[-1]]['program_id'] = row['child_id']
                    code = row.get('child_code')
                    self._links[ids[-1]]['source_sha256'] = (
                        _sha(code.encode('utf-8', errors='surrogatepass')) if isinstance(code, str) else None)

    def _read_journal(self):
        path = self.root / 'sciel_events.jsonl'
        signature = _signature(path)
        if signature is None or not self._safe(path):
            self._journal = {}; self._start = {}; self._links = {}; self._offset = 0
            self._journal_signature = None
            return
        if signature == self._journal_signature:
            return
        reset = (self._journal_signature is None or signature[:2] != self._journal_signature[:2]
                 or signature[2] < self._offset
                 or signature[2] == self._offset and signature != self._journal_signature)
        try:
            stream = _open_regular(path)
        except OSError:
            self._journal = {}; self._start = {}; self._links = {}; self._offset = 0
            self._journal_errors = 1
            self._journal_signature = signature
            return
        with stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns,
                    opened.st_ctime_ns) != signature:
                self._journal = {}; self._start = {}; self._links = {}; self._offset = 0
                self._journal_errors = 1
                self._journal_signature = None
                return
            if not reset and self._offset:
                stream.seek(max(0, self._offset - len(self._tail)))
                reset = stream.read(len(self._tail)) != self._tail
            if reset:
                self._journal = {}; self._links = {}; self._start = {}
                self._offset = 0; self._journal_errors = 0
            stream.seek(self._offset)
            while True:
                start = stream.tell()
                raw = stream.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    break
                if len(raw) > MAX_LINE_BYTES:
                    while raw and not raw.endswith(b'\n'):
                        raw = stream.readline(MAX_LINE_BYTES + 1)
                    self._journal_errors += 1
                    self._offset = stream.tell()
                    continue
                if not raw.endswith(b'\n'):
                    break  # An actively written partial line is not a failure.
                self._offset = stream.tell()
                try:
                    row = _json(raw)
                    if isinstance(row, dict):
                        self._consume(row, start)
                except (ValueError, UnicodeError, RecursionError, TypeError):
                    self._journal_errors += 1
            stream.seek(max(0, self._offset - 128))
            self._tail = stream.read(self._offset - stream.tell())
        self._journal_signature = signature

    def _geometry(self, geometry, observation, source, task_hash):
        if not isinstance(source, str) or _HASH.fullmatch(source) is None:
            raise ValueError('missing source binding')
        value = parse_artifact(geometry) if isinstance(geometry, str) else validate_geometry(geometry)
        if NATIVE_GEOMETRY_TASK_EVALUATORS.get(task_hash) != value['evaluator_sha256']:
            raise ValueError('unsupported task/evaluator binding')
        validate_binding(value, observation, source_sha256=source)
        return value

    def _item(self, geometry, observation, source, task_hash, evaluation_id, timestamp, provenance):
        value = self._geometry(geometry, observation, source, task_hash)
        identity = [task_hash, source, value['evaluator_sha256'], value['invocation_id'],
                    value['stage'], value['confirmation']]
        key = _digest(identity)
        return {'id': 'packing-' + key[:24], '_key': key,
            'evaluation_id': evaluation_id, 'program_id': None, 'program_ids': [],
            'island_id': None, 'island_ids': [], 'iteration': None,
            'timestamp': _text(timestamp), 'source_sha256': source,
            'evaluator_sha256': value['evaluator_sha256'], 'invocation_id': value['invocation_id'],
            'witness_sha256': _digest(value, ascii=True), 'numeric_sha256': value['numeric_sha256'],
            'score': value['native_sum_radii'] if value['native_validity'] else None,
            'raw_score': _number(observation.get('score')), 'valid': value['native_validity'],
            'evaluation_ok': observation['ok'], 'stage': observation['reached'],
            'confirmed': observation['confirmed'], 'centers': value['numeric']['centers'],
            'radii': value['numeric']['radii'], 'provenance': provenance}

    def _physical_result(self, directory, wave, task_hash, run_id):
        ident = None
        try:
            intent, _ = self._read(directory / 'intent.json')
            if intent.get('kind') != 'evaluation':
                return None
            key = intent.get('key')
            if not isinstance(key, str) or len(key) > 512 or directory.name != _sha(key.encode()):
                raise ValueError('call directory/key mismatch')
            ident = f'evaluation:{run_id}:wave:{wave}:{key}' if run_id else None
            request = _dict(intent.get('request'))
            request_sha = _digest({'kind': 'evaluation', 'request': request})
            if request_sha != intent.get('request_sha256') or request.get('task_hash') != task_hash:
                raise ValueError('request binding mismatch')
            if not (directory / 'receipt.json').exists():
                return {'pending': True, 'evaluation_id': ident}
            receipt, file_sha = self._read(directory / 'receipt.json')
            payload = _dict(receipt.get('payload'))
            dispatch, _ = self._read(directory / 'dispatched.json')
            if (_digest(payload) != receipt.get('sha256') or payload.get('request_sha256') != request_sha
                    or dispatch.get('request_sha256') != request_sha):
                raise ValueError('receipt/dispatch binding mismatch')
            if payload.get('status') != 'returned':
                return {'reason': 'evaluation_not_returned', 'evaluation_id': ident}
            outcome = _dict(payload.get('value')); result = _dict(outcome.get('result'))
            geometry = _dict(result.get('artifacts')).get('native_geometry')
            if geometry is None:
                return {'reason': 'missing_geometry', 'evaluation_id': ident}
            code = request.get('source')
            if not isinstance(code, str):
                raise ValueError('missing evaluated source')
            source = _sha(code.encode('utf-8', errors='surrogatepass'))
            observation = {**result, 'reached': outcome.get('reached'), 'confirmed': outcome.get('confirmed')}
            item = self._item(geometry, observation, source, task_hash, ident, payload.get('completed_at'),
                {'kind': 'physical_receipt', 'receipt_sha256': file_sha,
                 'payload_sha256': receipt['sha256'], 'request_sha256': request_sha})
            if key.startswith('portfolio:'):
                parts = key.split(':')
                if len(parts) >= 2 and parts[1].isdigit():
                    item['island_id'] = int(parts[1])
                    item['island_ids'] = [int(parts[1])]
            return {'item': item, 'evaluation_id': ident}
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
            return {'reason': 'unverifiable_evidence', 'evaluation_id': ident}

    def _scan_receipts(self, task_hash, run_id):
        base = self.root / '.parallel'
        if not self._safe(base) or not base.is_dir():
            self._physical = {}
            return
        present = set()
        for wave_path in base.iterdir():
            match = re.fullmatch(r'wave-(\d+)', wave_path.name)
            if not match or not self._safe(wave_path) or not wave_path.is_dir():
                continue
            calls = wave_path / 'calls'
            if not self._safe(calls) or not calls.is_dir():
                continue
            for directory in calls.iterdir():
                if not _HASH.fullmatch(directory.name) or not directory.is_dir():
                    continue
                present.add(directory)
                safe = self._safe(directory)
                signature = (task_hash, run_id, safe, *(_signature(directory / name) if safe else None
                             for name in ('intent.json', 'receipt.json', 'dispatched.json')))
                old = self._physical.get(directory)
                if old is None or old[0] != signature:
                    value = self._physical_result(directory, int(match[1]), task_hash, run_id)
                    self._physical[directory] = (signature, value)
        self._physical = {k: v for k, v in self._physical.items() if k in present}

    def _aliases(self, checkpoint):
        registry = _dict(checkpoint.get('candidate_novelty'))
        try:
            if registry.get('sha256') != _digest({k: v for k, v in registry.items() if k != 'sha256'}, ascii=True):
                return {}
            sources = {s['source_sha256'] for s in registry['sources']
                       if s['source_sha256'] == _sha(s['code'].encode('utf-8', errors='surrogatepass'))}
            return {r['id']: r for r in registry['records'] if r['source_sha256'] in sources
                    and isinstance(r.get('aliases'), list) and all(_text(p) for p in r['aliases'])
                    and isinstance(r.get('islands'), list) and all(
                        type(i) is int and i >= 0 or isinstance(i, str) and _text(i)
                        for i in r['islands'])}
        except (KeyError, ValueError, TypeError, UnicodeError):
            return {}

    def _rebuild(self, task_hash):
        candidates, unavailable, pending, physical_ids = [], Counter(), 0, set()
        for _, value in self._physical.values():
            if value is None:
                continue
            if value.get('evaluation_id'):
                physical_ids.add(value['evaluation_id'])
            if value.get('pending'):
                pending += 1
            elif 'reason' in value:
                unavailable[value['reason']] += 1
            else:
                candidates.append(deepcopy(value['item']))
        for ident, row in self._journal.items():
            if ident in physical_ids:
                continue
            if row.get('run_id') not in (None, self._start.get('run_id')):
                unavailable['wrong_run_journal_evidence'] += 1
                continue
            if row.get('_conflict'):
                unavailable['conflicting_journal_evidence'] += 1
                continue
            geometry = _dict(row.get('artifacts')).get('native_geometry')
            if geometry is None:
                unavailable['missing_geometry'] += 1
                continue
            signature = (task_hash, row.get('_event_sha256'))
            previous = self._journal_items.get(ident)
            if previous is None or previous[0] != signature:
                try:
                    item = self._item(geometry, row, row.get('source_sha256'), task_hash,
                        row.get('evaluation_id') or ident, row.get('timestamp'),
                        {'kind': 'journal', 'event_sha256': row['_event_sha256']})
                    item['iteration'] = row.get('iteration_no_before')
                except (ValueError, TypeError, KeyError, OverflowError):
                    item = None
                self._journal_items[ident] = (signature, item)
            item = self._journal_items[ident][1]
            if item is None:
                unavailable['unverifiable_evidence'] += 1
            else:
                candidates.append(deepcopy(item))
        self._journal_items = {k: v for k, v in self._journal_items.items() if k in self._journal}
        alias_signature = (self._checkpoint_signature, self._checkpoint_matches)
        if self._alias_signature != alias_signature:
            self._alias_cache = self._aliases(self._checkpoint) if self._checkpoint_matches else {}
            self._alias_signature = alias_signature
        aliases = self._alias_cache
        unique, conflicts = {}, set()
        for item in candidates:
            key = item.pop('_key')
            old = unique.get(key)
            if old is not None:
                if (old['witness_sha256'], old['raw_score'], old['evaluation_ok']) != (
                        item['witness_sha256'], item['raw_score'], item['evaluation_ok']):
                    conflicts.add(key)
                elif old['provenance']['kind'] == 'journal' and item['provenance']['kind'] == 'physical_receipt':
                    unique[key] = item
                continue
            unique[key] = item
        for key in conflicts:
            unique.pop(key, None)
            unavailable['conflicting_invocation_evidence'] += 1
        for item in unique.values():
            ident = item['evaluation_id'];link = self._links.get(ident, {})
            item['iteration'] = link.get('iteration', item['iteration'])
            if 'island_id' in link:
                item['island_id'] = link['island_id']
                item['island_ids'] = [link['island_id']]
            alias = aliases.get(ident)
            if alias and alias['source_sha256'] == item['source_sha256']:
                item['program_ids'] = list(alias['aliases'])
                item['island_ids'] = list(alias['islands']) or item['island_ids']
            elif (isinstance(link.get('program_id'), str)
                  and link.get('source_sha256') == item['source_sha256']):
                item['program_ids'] = [link['program_id']]
            item['program_id'] = next(iter(item['program_ids']), None)
            if len(item['island_ids']) == 1:
                item['island_id'] = item['island_ids'][0]
        self._items = list(unique.values())
        self._unavailable, self._pending = unavailable, pending
        self._islands = sorted({i for x in self._items for i in x['island_ids']
                                if type(i) is int or isinstance(i, str)}, key=lambda i: (str(type(i)), i))
        self._supported = task_hash in NATIVE_GEOMETRY_TASK_EVALUATORS
        self._version = _digest({'items': [{k: v for k, v in x.items() if k not in ('centers', 'radii')}
                                         for x in self._items], 'unavailable': dict(unavailable),
                                 'pending': pending, 'journal_read_errors': self._journal_errors,
                                 'warnings': self._warnings})

    def page(self, *, offset=0, limit=120, sort='score', island='all', query=''):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 120:
            raise ValueError('Invalid packing page')
        if sort not in ('score', 'newest', 'oldest') or not isinstance(island, (str, int)):
            raise ValueError('Invalid packing filter')
        if not isinstance(query, str) or len(query) > 256:
            raise ValueError('Invalid packing query')
        now = self.clock()
        if now - self._last_refresh >= self.refresh_seconds:
            self._read_checkpoint(); self._read_journal()
            identity = _dict(self._checkpoint.get('identity'))
            checkpoint_run = _dict(self._checkpoint.get('provenance')).get('run_id')
            self._checkpoint_matches = not (checkpoint_run and self._start.get('run_id')
                                             and checkpoint_run != self._start['run_id'])
            self._warnings = [] if self._checkpoint_matches else [
                'Checkpoint belongs to another run; its program aliases are unavailable.']
            if not self._checkpoint_matches:
                identity = {}
            task_hash = self._start.get('task_hash') or identity.get('task_hash')
            run_id = self._start.get('run_id') or _dict(self._checkpoint.get('provenance')).get('run_id')
            if identity.get('task_hash') not in (None, task_hash):
                task_hash = None
            self._scan_receipts(task_hash, run_id)
            signature = (task_hash, self._checkpoint_signature, self._checkpoint_matches, self._journal_signature,
                         tuple((str(p), v[0]) for p, v in self._physical.items()))
            if signature != self._rebuild_signature:
                self._rebuild(task_hash)
                self._rebuild_signature = signature
            self._last_refresh = now
        needle = query.casefold()
        items = [x for x in self._items if (str(island) == 'all' or str(island) in map(str, x['island_ids']))
                 and (not needle or needle in ' '.join(str(x.get(k) or '') for k in
                      ('id', 'evaluation_id', 'program_ids', 'source_sha256', 'island_ids')).casefold())]
        if sort == 'score':
            items.sort(key=lambda x: (x['score'] is None, -(x['score'] or 0), x['timestamp'] or '', x['id']))
        else:
            items.sort(key=lambda x: (x['timestamp'] or '', x['id']), reverse=sort == 'newest')
        total = len(items);available = len(self._items);unavailable = sum(self._unavailable.values())
        return deepcopy({'schema': SCHEMA, 'supported': self._supported,
            'supported_reason': None if self._supported else 'No supported saved packing geometry contract for this task.',
            'content_version': self._version, 'total': total, 'available': available,
            'unavailable': unavailable, 'unavailable_reasons': dict(self._unavailable),
            'total_evaluations': available + unavailable, 'pending': self._pending,
            'journal_read_errors': self._journal_errors, 'islands': self._islands,
            'warnings': self._warnings,
            'offset': offset, 'limit': limit, 'has_more': offset + limit < total,
            'items': items[offset:offset + limit],
            'note': 'One image per saved evaluator invocation, including evicted history. Aliases share one measurement. Invalid layouts have no native score; missing evidence is never reconstructed.'})
