"""Read-only, bounded projection of paid calls in the current unpublished wave.

This is observational, never transaction recovery. Nothing is repaired or replayed.
No engine/model modules are imported. Scientific counters remain unchanged.
"""
from collections import OrderedDict
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA = 'sciel-wave-transaction/2'
MAX_CALLS = 4096
TOOL_KINDS = frozenset({'tool_execution', 'tool_job_submit', 'tool_job_poll', 'tool_job_cancel'})
IO_KINDS = frozenset({'llm', 'evaluation'}) | TOOL_KINDS


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def _signature(path):
    if path.is_symlink():
        raise ValueError('Symlink is not a wave receipt')
    stat = path.stat()
    if not path.is_file():
        raise ValueError('Wave artifact is not a file')
    return stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _read(path, limit=8*1024*1024):
    sig = _signature(path)
    if sig[1] > limit:
        raise ValueError('Wave artifact exceeds projection limit')
    raw = path.read_bytes()
    if sig != _signature(path):
        raise ValueError('Wave artifact changed while reading')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Wave artifact is not an object')
    return value, hashlib.sha256(raw).hexdigest()


def _directory(path):
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Unsafe wave directory')
    return path


class WaveSpendMonitor:
    """Caches compact authenticated facts, never source/prompt payloads."""
    def __init__(self):
        self._cache = OrderedDict()

    def _memo(self, key, compute):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        result = compute()
        self._cache[key] = result
        while len(self._cache) > MAX_CALLS + 32:
            self._cache.popitem(last=False)
        return result

    def _checkpoint(self, path):
        def read():
            value, digest = _read(path, 128*1024*1024)
            provenance = value.get('provenance') or {}
            return dict(sha256=digest, cost=_number(value.get('cost_total')),
                run_id=provenance.get('run_id'), anchor=provenance.get('journal_anchor'))
        return self._memo(('checkpoint', str(path), _signature(path)), read)

    def _prefix(self, journal, boundary):
        def read():
            digest, remaining = hashlib.sha256(), boundary
            with journal.open('rb') as stream:
                while remaining:
                    chunk = stream.read(min(1024*1024, remaining))
                    if not chunk:
                        raise ValueError('Journal prefix is incomplete')
                    digest.update(chunk)
                    remaining -= len(chunk)
            return digest.hexdigest()
        return self._memo(('prefix', str(journal), _signature(journal), boundary), read)

    def _call(self, directory):
        paths = [directory/name for name in ('intent.json', 'dispatched.json', 'receipt.json')]
        signatures = tuple(_signature(p) if p.exists() or p.is_symlink() else None for p in paths)
        def read():
            intent, _ = _read(paths[0])
            key, kind = intent.get('key'), intent.get('kind')
            if (intent.get('schema') != 'sciel-parallel-call/1' or not isinstance(key, str)
                    or hashlib.sha256(key.encode()).hexdigest() != directory.name
                    or kind not in IO_KINDS or not isinstance(intent.get('request'), dict)):
                raise ValueError('Call intent identity mismatch')
            expected = _digest(dict(kind=kind, request=intent.get('request')))
            if intent.get('request_sha256') != expected:
                raise ValueError('Call request hash mismatch')
            dispatched = signatures[1] is not None
            if dispatched and _read(paths[1])[0].get('request_sha256') != expected:
                raise ValueError('Dispatch request hash mismatch')
            if signatures[2] is None:
                return dict(kind=kind, cost=0., unknown=0, pending=int(dispatched))
            envelope, _ = _read(paths[2]);payload = envelope.get('payload')
            if (not isinstance(payload, dict) or envelope.get('sha256') != _digest(payload)
                    or payload.get('request_sha256') != expected or not dispatched):
                raise ValueError('Receipt binding mismatch')
            if payload.get('status') not in {'returned', 'error'}:
                raise ValueError('Unknown receipt status')
            if kind in TOOL_KINDS:
                # These leaf calls return JSON objects, not LLMResponse values.
                # Authenticate their transport envelope without interpreting a
                # tool's observations, CPU usage or arbitrary `cost` as dollars.
                field = 'value' if payload['status'] == 'returned' else 'error'
                if not isinstance(payload.get(field), dict):
                    raise ValueError('Invalid tool call receipt')
                return dict(kind=kind, cost=0., unknown=0, pending=0)
            if kind == 'evaluation':
                return dict(kind=kind, cost=0., unknown=0, pending=0)
            if payload['status'] == 'error':
                return dict(kind=kind, cost=0., unknown=int(payload.get('not_dispatched') is not True), pending=0)
            value = payload.get('value')
            cost = _number(value.get('cost')) if isinstance(value, dict) else None
            return dict(kind=kind, cost=cost or 0., unknown=int(cost is None), pending=0)
        return self._memo(('call', str(directory), signatures), read)

    def observe(self, run_dir, start):
        root = Path(run_dir)/'.parallel'
        if not root.exists() and not root.is_symlink():
            return None
        try:
            _directory(root)
            pointer, _ = _read(root/'current.json')
            wave = pointer.get('wave_id')
            if (pointer.get('schema') != SCHEMA or not isinstance(wave, str)
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}', wave)):
                raise ValueError('Invalid wave pointer')
            directory = _directory(root/('wave-'+wave))
            manifest_path = directory/'transaction.json'
            manifest, manifest_hash = _read(manifest_path)
            if manifest.get('schema') != SCHEMA or manifest.get('wave_id') != wave:
                raise ValueError('Wave manifest identity mismatch')
            if manifest.get('phase') == 'committed':
                return None
            if manifest.get('phase') not in {'active', 'prepared'}:
                raise ValueError('Wave baseline is not published yet')
            name = manifest.get('baseline')
            if not isinstance(name, str) or not re.fullmatch(r'[a-f0-9]{32}\.baseline\.json', name):
                raise ValueError('Unsafe wave baseline filename')
            baseline = self._checkpoint(directory/name)
            if (baseline['sha256'] != manifest.get('baseline_sha256')
                    or not start.get('run_id') or baseline['run_id'] != start['run_id']):
                raise ValueError('Wave baseline identity mismatch')
            main = self._checkpoint(Path(run_dir)/'checkpoint.json')
            if manifest['phase'] == 'prepared' and main['sha256'] == manifest.get('candidate_sha256'):
                return None  # Already included in the published scientific checkpoint.
            if main['sha256'] != baseline['sha256']:
                raise ValueError('Published checkpoint is not the wave baseline')
            boundary = manifest.get('base_journal_bytes');anchor = baseline['anchor']
            if (type(boundary) is not int or boundary < 0 or not isinstance(anchor, dict)
                    or anchor.get('byte_offset') != boundary
                    or anchor.get('prefix_sha256') != manifest.get('base_journal_sha256')
                    or self._prefix(Path(run_dir)/'sciel_events.jsonl', boundary) != manifest.get('base_journal_sha256')):
                raise ValueError('Wave journal binding mismatch')
            calls = directory/'calls';facts = []
            if calls.exists() or calls.is_symlink():
                _directory(calls)
                for item in calls.iterdir():
                    if len(facts) >= MAX_CALLS:
                        raise ValueError('Wave call projection limit reached')
                    _directory(item)
                    if not re.fullmatch('[a-f0-9]{64}', item.name):
                        raise ValueError('Invalid call directory')
                    facts.append(self._call(item))
            # Do not mix receipts from an in-progress commit/new current wave.
            if _read(manifest_path)[1] != manifest_hash or _read(root/'current.json')[0] != pointer:
                raise ValueError('Wave changed while reading')
            llm = [fact for fact in facts if fact['kind'] == 'llm']
            known = math.fsum(fact['cost'] for fact in llm)
            unknown = sum(fact['unknown'] for fact in llm)
            pending = sum(fact['pending'] for fact in llm)
            return dict(schema='sciel-uncommitted-spend/1', available=True, wave=wave,
                phase=manifest['phase'], known_cost=known, unknown_call_count=unknown,
                pending_call_count=pending, baseline_cost=baseline['cost'],
                known_spend=(baseline['cost']+known if baseline['cost'] is not None else None),
                status='partial' if unknown or pending else 'known',
                source='Checksum-bound current wave receipts', included_in_stats=False)
        except (OSError, ValueError, TypeError, OverflowError, RecursionError, KeyError):
            return dict(schema='sciel-uncommitted-spend/1', available=False,
                status='unavailable', reason='Current wave receipts cannot yet be authenticated.',
                known_cost=None, unknown_call_count=None, pending_call_count=None,
                baseline_cost=None, known_spend=None, included_in_stats=False)
