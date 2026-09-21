"""Read-only content-addressed methods registry and public observer API."""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
import difflib
from pathlib import Path
import socket
import time

from .compat.runtime import process_matches
from .methods_projection import build_methods_projection
from .methods_records import (HASH, MAX_ARTIFACT, MAX_JOURNAL, MAX_ROWS,
    MAX_PROJECTION_BYTES, MAX_PROJECTION_OBJECTS, RESOURCES, SECRET,
    _read, clean, decode, digest, number, obj, observability,
    registered_artifacts, seq, signature, validate_shape)


class MethodsView:
    def __init__(self, journal):
        journal = Path(journal)
        self.root = journal.parent.parent.resolve()
        self.registry = self.root / journal.parent.name
        self.journal = self.registry / journal.name
        self._cache = OrderedDict()

    def signature(self):
        return tuple(signature(p) for p in (self.journal, self.root / 'resources.jsonl',
            self.root / 'acceptance.json', self.root / 'run-report.json', self.root / 'checkpoint.json', self.root / 'run-config.json'))

    def _json(self, path, limit=MAX_ARTIFACT):
        return decode(_read(self.root, path, limit))

    def rows(self, *, ledger=False):
        path = self.root / 'resources.jsonl' if ledger else self.journal
        warnings, rows = [], []
        try:
            raw = _read(self.root, path, MAX_JOURNAL)
        except (OSError, ValueError):
            return [], ['Resource ledger unavailable.' if ledger else 'Registry journal unavailable.']
        previous = '0' * 64
        for index, line in enumerate(raw.splitlines(keepends=True)):
            if index >= MAX_ROWS:
                warnings.append('Journal display limit reached; later records are not projected.')
                break
            if not line.endswith(b'\n'):
                warnings.append('Incomplete trailing record; waiting for its writer.')
                break
            try:
                row = decode(line)
                hash_key, prev_key = ('sha256', 'prev_sha256') if ledger else ('id', 'prev')
                expected_schema = 'sciel-resource-ledger/1' if ledger else 'sciel-method-event/1'
                if (not isinstance(row, dict) or row.get('schema') != expected_schema
                        or type(row.get('seq')) is not int or row.get('seq') != index + 1 or row.get(prev_key) != previous
                        or row.get(hash_key) != digest({k: v for k, v in row.items() if k != hash_key})
                        or not isinstance(row.get('data'), dict)
                        or not isinstance(row.get('op' if ledger else 'kind'), str)):
                    raise ValueError('unverified journal record')
                previous = row[hash_key]
                rows.append(row)
            except (ValueError, UnicodeError, RecursionError, TypeError):
                warnings.append(f'Journal integrity unavailable at record {index + 1}; showing verified prefix only.')
                break
        return rows, warnings

    def _object(self, directory, ident):
        if not isinstance(ident, str) or not HASH.fullmatch(ident):
            raise KeyError('Invalid artifact ID')
        key = (directory, ident)
        path = self.registry / directory / (ident + '.json')
        stamp = signature(path)
        cached = self._cache.get(key)
        if cached and cached[0] == stamp:
            self._cache.move_to_end(key)
            return cached[1]
        value = self._json(path)
        if not isinstance(value, dict) or digest(value) != ident:
            raise ValueError('Artifact integrity mismatch')
        self._cache[key] = (stamp, value)
        while len(self._cache) > 256 or sum(v[0][1] for v in self._cache.values() if v[0]) > 16 * 1024 * 1024:
            self._cache.popitem(last=False)
        return value

    def artifact(self, kind, ident, registered=None):
        if registered is None:
            rows, _ = self.rows()
            registered = registered_artifacts(rows)
        if registered.get(ident) != kind:
            raise KeyError('Artifact is not committed in this run')
        value = self._object('artifacts', ident)
        if value.get('schema') != 'sciel-method-artifact/1' or value.get('kind') != kind:
            raise ValueError('Artifact kind mismatch')
        return validate_shape(obj(value.get('body')))

    def budget(self):
        rows, warnings = self.rows(ledger=True)
        accounts, reservations, limits = {}, {}, {}
        for row in rows:
            data = row['data']
            try:
                validate_shape(data)
            except ValueError:
                warnings.append('Malformed resource metadata; showing its prior prefix.')
                break
            if row.get('op') == 'init':
                limits = obj(data.get('limits'))
            elif row.get('op') == 'account' and isinstance(data.get('account_id'), str):
                accounts[data['account_id']] = obj(data.get('limits'))
            elif row.get('op') == 'reserve' and isinstance(data.get('id'), str):
                reservations[data['id']] = dict(data, status='reserved', actual={})
            elif row.get('op') in ('settle', 'resolve') and data.get('id') in reservations:
                reservations[data['id']].update(data)
        def balance(selected, ceiling):
            spent, held = dict.fromkeys(RESOURCES, 0.), dict.fromkeys(RESOURCES, 0.)
            for r in selected:
                for key in RESOURCES:
                    actual = number(obj(r.get('actual')).get(key)) or 0
                    spent[key] += actual
                    if r.get('status') in ('reserved', 'unknown'):
                        held[key] += max(0, (number(obj(r.get('bounds')).get(key)) or 0) - actual)
            remaining = {}
            for key in RESOURCES:
                if key not in ceiling:
                    continue  # Missing metadata is unknown, never an unlimited grant.
                if ceiling[key] is None:
                    remaining[key] = None
                elif number(ceiling[key]) is not None:
                    remaining[key] = max(0, number(ceiling[key]) - spent[key] - held[key])
            return dict(limits=ceiling, spent=spent, reserved=held,
                remaining=remaining,
                unknown_reservations=[r['id'] for r in selected if r.get('status') == 'unknown'],
                pending_reservations=[r['id'] for r in selected if r.get('status') == 'reserved'])
        values = list(reservations.values())
        result = balance(values, limits)
        result['accounts'] = {a: balance([r for r in values if r.get('account_id') == a], cap)
            for a, cap in accounts.items()}
        result['by_category'] = {category: balance([r for r in values if r.get('category') == category], limits)['spent']
            for category in sorted({str(r.get('category')) for r in values})}
        result['measurement_scope'] = 'Charged operation resources. Summed wall time is not elapsed time; storage is cumulative charged bytes.'
        result['current_operations'] = [{k:r.get(k) for k in ('id', 'account_id', 'category', 'status')}
            for r in values if r.get('status') in ('reserved', 'unknown')]
        result['complete'] = not warnings
        return result, warnings

    def runtime(self, identity, registry_started_at=None):
        return clean(self._runtime(identity, registry_started_at))

    def terminal_report(self, rows, identity, registered):
        """Only a terminal report bound to the exact current journal checkpoint."""
        try:
            checkpoint = self._json(self.root / 'checkpoint.json')
            anchor = obj(checkpoint.get('journal'))
            if (not rows or anchor.get('count') != len(rows) or anchor.get('head') != rows[-1]['id']
                    or checkpoint.get('id') != digest({k:v for k,v in checkpoint.items() if k != 'id'})):
                return None
            for filename in ('run-report.json', 'acceptance.json'):
                try:
                    report = self._json(self.root / filename)
                except FileNotFoundError:
                    continue
                if report.get('checkpoint_id') != checkpoint['id']:
                    continue
                if filename == 'run-report.json':
                    if (report.get('schema') != 'sciel-method-run-report/1'
                            or report.get('coordinator_identity') != identity):
                        continue
                    status = {'completed':'completed', 'budget_exhausted':'stopped',
                        'accounting_stopped':'unknown', 'failed':'failed', 'stopped':'stopped'}.get(report.get('status'))
                    if status:
                        return dict(status=status, source=filename, reason=report.get('reason'), classification=report.get('classification'),
                            accounting_coverage=report.get('accounting_coverage'), accounting_note=report.get('accounting_note'),
                            quality=report.get('quality'))
                elif (report.get('schema') == 'sciel-method-technical-acceptance/1'
                        and report.get('status') == 'passed' and report.get('technical_only') is True
                        and obj(identity.get('generator')).get('kind') == 'scripted_fixture'
                        and registered.get(report.get('adoption_id')) == 'adoption'
                        and registered.get(report.get('release_id')) == 'method_evidence'
                        and all(registered.get(i) == 'experiment' for i in obj(report.get('experiments')).values())):
                    return dict(status='completed', source=filename, reason='Technical acceptance completed; no scientific benefit claim.',
                        technical_only=True, limitations=report.get('limitations'))
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            pass
        return None

    def _runtime(self, identity, registry_started_at):
        result = dict(available=False, active=None, status='unknown', stage=None,
            verification='unavailable', heartbeat_age_seconds=None, elapsed_seconds=None,
            reason='No process-bound runtime heartbeat is available.')
        try:
            value = self._json(self.root / 'runtime.json', 65536)
            if not isinstance(value, dict) or value.get('schema') != 'sciel-method-runtime/1':
                return result
        except (OSError, ValueError, UnicodeError, RecursionError):
            return result
        result['available'] = True
        binding = value.get('registry_identity_sha256')
        if (not binding or binding != digest(identity) or registry_started_at is None
                or value.get('registry_started_at') != registry_started_at):
            result.update(verification='different_run', reason='Runtime telemetry is not bound to this registry identity.')
            return result
        result.update({k: value.get(k) for k in ('stage', 'heartbeat_at', 'started_at', 'finished_at',
            'pid', 'stale_after_seconds', 'overhead', 'runtime_id', 'reason', 'run_name')})
        def timestamp(v):
            parsed = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError('timezone required')
            return parsed.timestamp()
        try:
            started = timestamp(value['started_at'])
            heartbeat = timestamp(value['heartbeat_at'])
            end = timestamp(value['finished_at']) if value.get('finished_at') else heartbeat
            result['heartbeat_age_seconds'] = max(0, time.time() - heartbeat)
            result['elapsed_seconds'] = max(0, end - started)
        except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
            result.update(verification='invalid_timestamp', reason='Runtime timestamp is unavailable.')
            return result
        if value.get('status') in ('completed', 'failed', 'stopped', 'interrupted', 'unknown'):
            result.update(status=value['status'], active=False, verification='terminal_recorded')
            return result
        if value.get('status') != 'running' or value.get('hostname') != socket.gethostname():
            result.update(verification='unverified_host')
            return result
        matches = process_matches(value)
        if matches is False:
            result.update(status='interrupted', active=False, verification='process_not_running',
                reason='Recorded controller process is no longer running.')
        elif matches is None:
            result.update(verification='process_unverified')
        elif (number(value.get('stale_after_seconds')) or 0) <= 0 or heartbeat > time.time() + 2:
            result.update(verification='invalid_timestamp')
        elif time.time() - heartbeat > float(value['stale_after_seconds']):
            result.update(status='stalled', active=False, verification='stale_heartbeat',
                reason='Controller exists but runtime heartbeat is stale.')
        else:
            result.update(status='running', active=True, verification='live_process', reason=None)
        return result

    def project(self, run_id):
        return build_methods_projection(self, run_id)

    def method_detail(self, ident):
        rows, warnings = self.rows()
        registered = {r['data']['id'] for r in rows if r.get('kind') == 'method_registered' and isinstance(r['data'].get('id'), str)}
        if ident not in registered:
            raise KeyError('Unknown method')
        body = self._object('methods', ident)
        manifest = obj(body.get('manifest'))
        parents = []
        for parent in seq(manifest.get('parents'))[:16]:
            if parent not in registered:
                continue
            old = self._object('methods', parent)
            diffs = []
            for name in sorted(set(obj(old.get('files'))) | set(obj(body.get('files')))):
                before, after = obj(old.get('files')).get(name, ''), obj(body.get('files')).get(name, '')
                if isinstance(before, str) and isinstance(after, str):
                    diffs.append(''.join(difflib.unified_diff(before[:100_000].splitlines(True), after[:100_000].splitlines(True),
                        fromfile=parent[:12] + '/' + name, tofile=ident[:12] + '/' + name)))
            parents.append(dict(id=parent, name=obj(old.get('manifest')).get('name'), diff=''.join(diffs)[:500_000]))
        return clean(dict(id=ident, manifest=manifest, files=body.get('files'), parents=parents,
            diff=parents[0]['diff'] if parents else None, source_sha256=digest(obj(body.get('files'))), warnings=warnings))

    def proposal_detail(self, ident):
        rows, warnings = self.rows()
        registered = registered_artifacts(rows)
        body = self.artifact('proposal_receipt', ident, registered)
        context = self.artifact('proposal_context', body.get('context_id'), registered)
        call = self.artifact('call_receipt', body.get('call_receipt_id'), registered)
        # A dispatch intent is saved before the request. Never reconstruct a
        # missing historical prompt from today's procedure implementation.
        request = None
        if isinstance(call.get('key'), str) and isinstance(call.get('account'), str):
            directory = digest(dict(key=call['key'], account=call['account']))
            try:
                intent = self._json(self.registry / 'dispatch' / directory / 'intent.json')
                if (intent.get('sha256') == digest({k:v for k,v in intent.items() if k != 'sha256'})
                        and intent.get('reservation_id') == call.get('reservation_id')
                        and intent.get('request_sha256') == call.get('request_sha256')):
                    request = intent.get('request')
            except (ValueError, OSError, UnicodeError, RecursionError):
                warnings.append('Saved generation request is unavailable.')
        return clean(dict(id=ident, receipt=body, context=context, request=request,
            response=obj(call.get('result')).get('text'), call_receipt=call, warnings=warnings,
            note='Exact saved request/response only; no historical text reconstructed.'))
