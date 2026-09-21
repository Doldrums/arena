"""Saved whole-run identities and exact output matches; no candidate execution.

Only checksum-bound compact observations from a coherent checkpoint are used.
This is a presentation of engine-recorded validation, not independent replay or
a claim that two programs have the same behavior on other inputs.
"""
from collections import defaultdict
import hashlib
import json
import math
import re


MATCH_LIMIT = 12
_HASH = re.compile(r'[0-9a-f]{64}\Z')


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _sha(value):
    return hashlib.sha256(value.encode('utf-8', errors='surrogatepass')).hexdigest()


def _hash(value):
    return isinstance(value, str) and _HASH.fullmatch(value) is not None


def _sealed(value, key):
    if not isinstance(value, dict) or not _hash(value.get(key)):
        return False
    try:
        body = {k: v for k, v in value.items() if k != key}
        return value[key] == _sha(json.dumps(body, sort_keys=True, separators=(',', ':'),
                                           ensure_ascii=True, allow_nan=False))
    except (ValueError, TypeError, RecursionError):
        return False


def _integer(value):
    return value if type(value) is int and value >= 0 else None


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _others(values, ident):
    # At most one self ID occurs in a group; never scan an entire repeated-output
    # or seed-copy group for each member merely to display twelve links.
    return [value for value in values[:MATCH_LIMIT + 1] if value != ident][:MATCH_LIMIT]


def _geometry(record, source_sha):
    """Accept only an ordinary, source-bound, engine-validated saved output."""
    if (record.get('schema') != 'sciel-observed-change/1' or record.get('scope') != 'unpaired'
            or not _sealed(record, 'record_sha256')
            or record.get('child_source_sha256') != source_sha):
        return None
    obs = _dict(record.get('child_observation'))
    if (obs.get('ok') is not True or obs.get('validity') is not True
            or obs.get('status') != 'valid' or obs.get('reason') != 'observed'
            or obs.get('geometry_status') != 'validated'
            or type(obs.get('confirmed')) is not bool
            or obs.get('reached') not in ('smoke', 'full', 'confirm')
            or (obs['confirmed'] and obs['reached'] != 'confirm')
            or not _finite(obs.get('score'))):
        return None
    geo = _dict(obs.get('geometry'))
    if (set(geo) != {'numeric_sha256', 'evaluator_sha256', 'centers_dtype', 'radii_dtype'}
            or not all(_hash(geo.get(k)) for k in ('numeric_sha256', 'evaluator_sha256'))
            or not all(geo.get(k) in ('float16', 'float32', 'float64')
                       for k in ('centers_dtype', 'radii_dtype'))):
        return None
    return tuple(geo[k] for k in ('evaluator_sha256', 'centers_dtype', 'radii_dtype', 'numeric_sha256'))


def result_history_view(checkpoint, rows, sources=None):
    """Project every saved program, including evicted members, not just parents.

    ``sources`` is accepted for the adapter API but current journal sources are
    deliberately not combined with an older checkpoint's observation history.
    """
    cp = _dict(checkpoint)
    programs = {}
    conflicting = set()
    for program in _list(_dict(cp.get('db')).get('programs')):
        program = _dict(program)
        ident, code = program.get('id'), program.get('code')
        if not isinstance(ident, str) or not isinstance(code, str):
            continue
        if ident in programs:
            conflicting.add(ident)
        programs[ident] = program
    for ident in conflicting:
        programs.pop(ident, None)
    source_sha = {ident: _sha(program['code']) for ident, program in programs.items()}

    registry = _dict(cp.get('candidate_novelty'))
    registry_ok = (registry.get('schema') == 'sciel-candidate-novelty/1' and _sealed(registry, 'sha256')
        and isinstance(registry.get('sources'), list) and isinstance(registry.get('records'), list))
    registered_sources, records, evaluation_by_program = {}, [], {}
    if registry_ok:
        for value in _list(registry.get('sources')):
            value = _dict(value)
            code, sha = value.get('code'), value.get('source_sha256')
            if not isinstance(code, str) or sha != _sha(code) or sha in registered_sources:
                registry_ok = False
                break
            if value.get('ast_sha256') is not None and not _hash(value['ast_sha256']):
                registry_ok = False
                break
            registered_sources[sha] = value
        seen_evaluations, seen_aliases = set(), set()
        for value in _list(registry.get('records')) if registry_ok else []:
            value = _dict(value)
            ident, sha, aliases = value.get('id'), value.get('source_sha256'), value.get('aliases')
            if (not isinstance(ident, str) or ident in seen_evaluations or not _hash(sha) or sha not in registered_sources
                    or not isinstance(aliases, list) or any(not isinstance(a, str) for a in aliases)
                    or len(set(aliases)) != len(aliases) or seen_aliases.intersection(aliases)
                    or (value.get('evaluation_ok') is not None and type(value['evaluation_ok']) is not bool)):
                registry_ok = False
                break
            seen_evaluations.add(ident)
            seen_aliases.update(aliases)
            records.append(value)
            for alias in aliases:
                if source_sha.get(alias) == sha:
                    evaluation_by_program[alias] = ident
        if seen_aliases.intersection(seen_evaluations):
            registry_ok = False
        if not registry_ok:
            registered_sources, records, evaluation_by_program = {}, [], {}

    observed = _dict(cp.get('observed_changes'))
    identity = _dict(observed.get('identity'))
    cp_identity = _dict(cp.get('identity'))
    observations_ok = (observed.get('schema') == 'sciel-observed-changes/1'
        and _sealed(observed, 'state_sha256')
        and isinstance(observed.get('records'), list) and isinstance(observed.get('aliases'), list)
        and identity.get('geometry_policy') == 'validated_native_numeric_sha256_same_evaluator_and_dtypes')
    if cp_identity.get('task_hash') is not None:
        observations_ok &= _dict(identity.get('metric')).get('task_hash') == cp_identity['task_hash']
    geometry, valid_records = {}, {}
    evaluation_status = {record['id']: record['evaluation_ok'] for record in records}
    if observations_ok:
        for record in _list(observed.get('records')):
            record = _dict(record)
            ident = record.get('child_program_id')
            if not isinstance(ident, str) or ident not in source_sha or record.get('id') != 'program:' + ident:
                continue
            evaluation = evaluation_by_program.get(ident)
            if evaluation is not None and evaluation_status.get(evaluation) is not True:
                continue
            key = _geometry(record, source_sha[ident])
            if key is not None:
                geometry[ident], valid_records[ident] = key, record
        # Explicit aliases do not represent another evaluation. Require the
        # source/cases/score/reference binding recorded by the engine.
        for alias in _list(observed.get('aliases')):
            alias = _dict(alias)
            ident, reference = alias.get('program_id'), alias.get('reference_program_id')
            if not isinstance(ident, str) or not isinstance(reference, str):
                continue
            program, original = programs.get(ident, {}), programs.get(reference, {})
            record = valid_records.get(reference)
            try:
                cases_sha = _sha(json.dumps(program.get('cases'), sort_keys=True,
                    separators=(',', ':'), ensure_ascii=True, allow_nan=False))
            except (ValueError, TypeError, RecursionError):
                continue
            if (ident not in geometry and reference in geometry and record is not None
                    and program.get('origin') == 'migrant' and program.get('parent_id') == reference
                    and source_sha.get(ident) == source_sha.get(reference) == alias.get('source_sha256')
                    and program.get('score') == original.get('score') == alias.get('score')
                    and program.get('cases') == original.get('cases')
                    and cases_sha == alias.get('cases_sha256')
                    and record.get('record_sha256') == alias.get('reference_record_sha256')):
                geometry[ident], valid_records[ident] = geometry[reference], record
                if reference in evaluation_by_program:
                    evaluation_by_program[ident] = evaluation_by_program[reference]

    ast_available = registry_ok and _dict(registry.get('identity')).get('ast_version') == 'python-ast-fields-constants/1'
    by_source, by_ast, by_geometry = defaultdict(list), defaultdict(list), defaultdict(list)
    for ident, sha in source_sha.items():
        by_source[sha].append(ident)
        ast = _dict(registered_sources.get(sha)).get('ast_sha256') if ast_available else None
        if ast is not None:
            by_ast[ast].append(ident)
        if ident in geometry:
            by_geometry[geometry[ident]].append(ident)
    evaluation_order = {r['id']: index for index, r in enumerate(records)}
    output_groups = {}
    output_representatives, output_aliases = {}, {}
    for key, members in by_geometry.items():
        groups = {}
        for ident in members:
            evaluation = evaluation_by_program.get(ident)
            if evaluation is not None and evaluation_status.get(evaluation) is True:
                groups.setdefault(evaluation, []).append(ident)
        output_groups[key] = sorted(groups.items(), key=lambda item: evaluation_order.get(item[0], len(records)))
        output_representatives[key] = [members[0] for _, members in output_groups[key]]
        output_aliases[key] = groups

    evaluation_aliases = defaultdict(list)
    for ident, evaluation in evaluation_by_program.items():
        evaluation_aliases[evaluation].append(ident)
    by_program = {}
    for ident, sha in source_sha.items():
        ast = _dict(registered_sources.get(sha)).get('ast_sha256') if ast_available else None
        evaluation = evaluation_by_program.get(ident)
        groups = output_groups.get(geometry.get(ident), [])
        own_group = output_aliases.get(geometry.get(ident), {}).get(evaluation, [])
        output_available = bool(own_group)
        representatives = output_representatives.get(geometry.get(ident), [])
        matches = _others(representatives, own_group[0]) if own_group else []
        aliases = _others(own_group, ident)
        source_matches = _others(by_source[sha], ident)
        ast_matches = _others(by_ast.get(ast, []), ident)
        all_aliases = evaluation_aliases.get(evaluation, [])
        alias_kind = ('migration_copy' if programs[ident].get('origin') == 'migrant'
                      else 'seed_copy' if programs[ident].get('origin') == 'seed' and len(all_aliases) > 1 else None)
        by_program[ident] = dict(source_matches=source_matches, source_match_count=len(by_source[sha]) - 1,
            ast_matches=ast_matches, ast_match_count=len(by_ast[ast]) - 1 if ast is not None else None,
            output_matches=matches, output_match_count=len(groups) - 1 if output_available else None,
            output_alias_matches=aliases, output_alias_count=len(own_group) - 1 if output_available else None,
            earliest_output_match=matches[0] if matches else None,
            first_output_program_id=groups[0][1][0] if groups else None,
            output_status='exact_saved_output' if ident in geometry else 'unavailable',
            output_comparison_available=output_available,
            evaluation_id=evaluation, alias_kind=alias_kind, source_sha256=sha,
            ast_sha256=ast, scope='unpaired_saved_observation')

    iteration = _integer(cp.get('iteration_no'))
    latest = max([v for row in rows if (v := _integer(_dict(row).get('iteration_no'))) is not None]
                 + ([iteration] if iteration is not None else []), default=None)
    anchor = _dict(_dict(cp.get('provenance')).get('journal_anchor'))
    boundary = next((i for i, row in enumerate(rows) if anchor and
        _dict(row).get('segment_id') == anchor.get('segment_id') and
        _dict(row).get('event_seq') == anchor.get('event_seq')), None)
    tail_changes = boundary is not None and any(_dict(row).get('event') in ('iteration', 'evaluation', 'candidate_measurement')
        or (_dict(row).get('event') == 'decision' and _dict(row).get('policy') in
            ('observed_change', 'candidate_novelty', 'evaluation', 'candidate_measurement'))
        for row in rows[boundary + 1:])
    stale = (latest > iteration or tail_changes) if iteration is not None and latest is not None else None
    repeat_count = sum(max(0, len(groups) - 1) for groups in output_groups.values())
    finished = sum(type(r.get('evaluation_ok')) is bool for r in records)
    registered_aliases = {r['id']: set(r['aliases']) for r in records}
    for ident, evaluation in evaluation_by_program.items():
        registered_aliases.setdefault(evaluation, set()).add(ident)
    return dict(schema='sciel-result-history/1', scope='whole_run_saved_history', match_limit=MATCH_LIMIT,
        coverage=dict(source='checkpoint', iteration=iteration, latest_iteration=latest, stale=stale,
            source_bound_programs=len(programs), validated_output_programs=len(geometry),
            registry_available=registry_ok, observations_available=bool(observations_ok),
            output_evaluations=sum(len(groups) for groups in output_groups.values()),
            journal_outputs_included=False),
        counts=dict(evaluations=finished if registry_ok else None,
            registered_evaluations=len(records) if registry_ok else None,
            pending_evaluations=len(records) - finished if registry_ok else None,
            unique_sources=len(registered_sources) if registry_ok else None,
            unique_asts=len({s['ast_sha256'] for s in registered_sources.values() if s.get('ast_sha256')}) if ast_available else None,
            source_aliases=sum(max(0, len(aliases) - 1) for aliases in registered_aliases.values()) if registry_ok else None,
            repeated_outputs=repeat_count if registry_ok and observations_ok else None,
            unique_outputs=len(by_geometry) if observations_ok else None), by_program=by_program,
        note='Exact source / recorded AST identity and exact saved numeric output are different comparisons. '
             'Output matches require validated source-bound observations with the same evaluator and array dtypes; '
             'score ties alone are not output matches. Seed and migrated copies do not count as repeated evaluations. '
             'Output counts cover saved admitted-program observations, not every evaluated or rejected candidate. '
             'These unpaired observations do not establish semantic equivalence or causal effectiveness.')
