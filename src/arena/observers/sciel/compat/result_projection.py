"""Budgeted presentation of saved tool results, without semantic summaries.

A projection contains exact JSON Pointer/value pairs. Nonempty dictionaries
are traversed, while arrays, strings, scalars and empty containers remain whole.
Schema /2 additionally reserves exact standard comparison rows grouped by seed.
Schema /3 reserves whole dictionary rows under arbitrary observation array keys.
Counts refer to original atomic fields, not the number of scientific findings.
The immutable receipt and the surrounding research card retain source identity.
"""
import hashlib
import json


PROJECTION_SCHEMA = 'sciel-tool-result-projection/1'
COMPARISON_PROJECTION_SCHEMA = 'sciel-tool-result-projection/2'
ROW_PROJECTION_SCHEMA = 'sciel-tool-result-projection/3'
PROJECTION_SCHEMAS = frozenset((PROJECTION_SCHEMA, COMPARISON_PROJECTION_SCHEMA, ROW_PROJECTION_SCHEMA))
_ROW_SCOPE = ('Exact whole tool-reported observation rows in source path/index order; not verified scientific claims. '
    'Counts cover eligible arrays not already delivered whole in fields. Array and row hashes bind the receipt. '
    'Omitted rows remain there; atomic field counts still count '
    'each supplementary array as an omitted field.')
_COMPARISON_PATH = '/output/observations/comparison_results'
_CORE = ('arm_id', 'seed', 'cpu_seconds', 'best_result', 'conditions')
_COMPARISON_SCOPE = ('Exact tool-reported rows, grouped by reported seed; not verified adherence or benefit. '
    'Omitted values remain in the original receipt. Generic field counts treat the array as one omitted field.')
_MAX_OMITTED_PATHS = 16
_STATE_CONTAINERS = frozenset(('continuation_state', 'saved_state'))
_COMPACT_SCALAR_CHARS = 256


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


_OMITTED = _json({'schema': PROJECTION_SCHEMA, 'omitted': True})
MIN_CONTEXT_CHARS = len(_OMITTED)


def _fields(item):
    """Iteratively enumerate exact atomic fields; never truncate a value."""
    pending = [((), item)]
    while pending:
        parts, value = pending.pop()
        if type(value) is dict and value:
            pending.extend((parts + (key,), child) for key, child in value.items())
            continue
        path = ''.join('/' + key.replace('~', '~0').replace('/', '~1') for key in parts)
        observation = parts[:2] == ('output', 'observations')
        diagnostic = parts[:2] == ('output', 'diagnostics') or parts[:1] == ('diagnostic',)
        field = {'path': path, 'value': value}
        yield (0 if observation else 2 if diagnostic else 1,
               len(_json(field)), path, observation, field)


def _legacy_context(item, limit):
    """Return valid ASCII JSON of at most ``limit`` characters.

The full wrapper is returned unchanged semantically when it fits. Otherwise
small observation fields have priority, including fields in nested dictionaries;
metadata follows, then diagnostics. Large arrays and strings are omitted whole.
No selected value is interpreted, rounded, reworded, or mutated.

Below the exported minimum an explicit omission marker cannot fit, so callers
must omit the enclosing card rather than cut this string. At small supported
limits a versioned whole-result omission marker is returned. More detailed
omission counts and paths are included only when their own JSON fits.
"""
    if type(limit) is not int or limit < MIN_CONTEXT_CHARS:
        raise ValueError('result context limit must be an integer >= ' + str(MIN_CONTEXT_CHARS))
    if type(item) is not dict:
        raise ValueError('result context must be a JSON object')
    original = _json(item)
    if len(original) <= limit:
        return original

    original_sha256 = hashlib.sha256(original.encode('ascii')).hexdigest()
    candidates = sorted(_fields(item), key=lambda row: row[:3])
    total = len(candidates)
    observation_total = sum(row[3] for row in candidates)
    observations = item.get('output', {}).get('observations') if type(item.get('output')) is dict else None
    selected = []
    selected_paths = set()
    shown_observations = 0

    def render(paths=()):
        if type(observations) is not dict:
            state = 'not_present'
        elif not observations:
            state = 'originally_empty'
        elif not shown_observations:
            state = 'all_omitted'
        elif shown_observations == observation_total:
            state = 'complete'
        else:
            state = 'partial'
        omitted = total - len(selected)
        return _json({'schema': PROJECTION_SCHEMA,
            'original_sha256': original_sha256,
            'fields': selected, 'observations_state': state,
            'omitted_fields': omitted,
            'omitted_observation_fields': observation_total - shown_observations,
            'omitted_paths': list(paths), 'omitted_paths_omitted': omitted - len(paths)})

    if len(render()) > limit:
        marker = {'schema': PROJECTION_SCHEMA, 'omitted': True}
        for key, value in (('omitted_fields', total),
                           ('omitted_observation_fields', observation_total)):
            proposed = {**marker, key: value}
            if len(_json(proposed)) <= limit:
                marker = proposed
        return _json(marker)

    for _, size, path, observation, field in candidates:
        if size > limit:
            continue
        selected.append(field)
        shown_observations += observation
        if len(render()) <= limit:
            selected_paths.add(path)
        else:
            selected.pop()
            shown_observations -= observation

    # Path names are explanatory overhead; they cannot evict selected data.
    omitted_paths = sorted((row[2] for row in candidates if row[2] not in selected_paths),
                           key=lambda path: (len(_json(path)), path))
    paths = []
    for path in omitted_paths[:_MAX_OMITTED_PATHS]:
        if len(render(paths + [path])) <= limit:
            paths.append(path)
        else:
            break
    return render(paths)


def _hash(value):
    return hashlib.sha256(_json(value).encode('ascii')).hexdigest()


def _comparison_catalog(item):
    output = item.get('output')
    observations = output.get('observations') if type(output) is dict else None
    rows = observations.get('comparison_results') if type(observations) is dict else None
    if type(rows) is not list or not rows:
        return None
    by_seed = {}
    for index, row in enumerate(rows):
        if type(row) is dict and type(row.get('seed')) is int:
            by_seed.setdefault(row['seed'], []).append((index, row))
    groups = []
    for seed, members in sorted(by_seed.items()):
        # Never keep only the cheap arm of one reported seed. A malformed or
        # oversized member makes its whole seed group unavailable at this budget.
        if any(not all(key in row for key in _CORE) or type(row['arm_id']) is not str
               for _, row in members):
            continue
        projected = []
        for index, row in members:
            omitted = {key: {'sha256': _hash(value), 'json_chars': len(_json(value))}
                       for key, value in sorted(row.items()) if key not in _CORE}
            projected.append({'index': index, 'path': _COMPARISON_PATH + '/' + str(index),
                'original_sha256': _hash(row),
                'values': {key: row[key] for key in _CORE}, 'omitted_values': omitted})
        groups.append({'seed': seed, 'rows': projected})
    return rows, groups


def _comparison_metadata(rows, groups):
    shown = sum(len(group['rows']) for group in groups)
    return {'path': _COMPARISON_PATH, 'original_sha256': _hash(rows),
        'total_rows': len(rows), 'shown_rows': shown, 'omitted_rows': len(rows) - shown,
        'groups': groups, 'scope': _COMPARISON_SCOPE}


def _paired_context(item, limit):
    """Exact bounded /1 projection, with /2 paired rows before bulky saved state.

    /2 never modifies the saved output. Each group contains every original row
    for one reported seed, including duplicate arm IDs if the tool reported them.
    It preserves all five core values wholesale, even invalid/null values. This
    proves delivery, not completeness of the declared experiment. Oversized or
    malformed groups are omitted as a whole. The original array remains an
    omitted atomic field; supplementary row groups cannot claim full output.
    """
    legacy = _legacy_context(item, limit)
    if len(_json(item)) <= limit:
        return legacy
    legacy_value = json.loads(legacy)
    if any(field.get('path') == _COMPARISON_PATH for field in legacy_value.get('fields', [])):
        return legacy  # Already retains the complete array, including saved state.
    catalog = _comparison_catalog(item)
    if catalog is None:
        return legacy
    rows, groups = catalog
    if not groups:
        return legacy
    candidates = sorted(_fields(item), key=lambda row: row[:3])
    observation_total = sum(row[3] for row in candidates)
    selected, selected_groups, selected_paths = [], [], set()

    def render(paths=(_COMPARISON_PATH,)):
        observed = sum(path.startswith('/output/observations/') for path in selected_paths)
        omitted = len(candidates) - len(selected)
        return _json({'schema': COMPARISON_PROJECTION_SCHEMA, 'original_sha256': _hash(item),
            'fields': selected, 'observations_state': 'partial',
            'omitted_fields': omitted, 'omitted_observation_fields': observation_total - observed,
            'omitted_paths': list(paths), 'omitted_paths_omitted': omitted - len(paths),
            'comparison_projection': _comparison_metadata(rows, selected_groups)})

    # Keep whole matched-seed groups before optional audits, geometry, prose,
    # metadata and diagnostics. Original row indices retain the source ordering.
    for group in groups:
        selected_groups.append(group)
        if len(render()) > limit:
            selected_groups.pop()
    if not selected_groups:
        return legacy
    for _, size, path, observation, field in candidates:
        if path == _COMPARISON_PATH or size > limit:
            continue
        selected.append(field)
        selected_paths.add(path)
        if len(render()) > limit:
            selected.pop()
            selected_paths.remove(path)
    omitted = sorted((row[2] for row in candidates if row[2] not in selected_paths),
                     key=lambda path: (len(_json(path)), path))
    paths = [_COMPARISON_PATH]
    for path in (path for path in omitted if path != _COMPARISON_PATH):
        if len(paths) >= _MAX_OMITTED_PATHS:
            break
        if len(render(paths + [path])) > limit:
            break
        paths.append(path)
    return render(paths)


def _state_path(path):
    return any(part in _STATE_CONTAINERS for part in path.split('/')[3:])


def _row_catalog(item):
    """Only arrays of objects are records; numerical/mixed arrays stay atomic.

    Do not descend inside a record or reinterpret comparison_results: a record
    must remain whole and standard paired comparisons keep their seed groups.
    """
    arrays = []
    for _, _, path, observation, field in sorted(_fields(item), key=lambda row: row[2]):
        rows = field['value']
        if (not observation or path == _COMPARISON_PATH or _state_path(path) or type(rows) is not list
                or not rows or any(type(row) is not dict for row in rows)):
            continue
        arrays.append({'path': path, 'original_sha256': _hash(rows), 'total_rows': len(rows),
            'rows': [{'index': index, 'path': path + '/' + str(index),
                      'original_sha256': _hash(row), 'value': row}
                     for index, row in enumerate(rows)]})
    return arrays


def _row_metadata(catalog, selected):
    arrays = []
    for array in catalog:
        rows = selected.get(array['path'], [])
        if rows:
            arrays.append({**array, 'rows': rows, 'shown_rows': len(rows),
                           'omitted_rows': array['total_rows'] - len(rows)})
    total = sum(array['total_rows'] for array in catalog)
    shown = sum(len(array['rows']) for array in arrays)
    return {'total_arrays': len(catalog), 'shown_arrays': len(arrays),
        'omitted_arrays': len(catalog) - len(arrays), 'total_rows': total,
        'shown_rows': shown, 'omitted_rows': total - shown,
        'arrays': arrays, 'scope': _ROW_SCOPE}


def success_context(item, limit):
    """Retain exact complete results, or bounded authenticated observations.

    Paired seed groups take precedence. Other observation arrays of dictionary
    records receive one whole source-order row per array, then compact scalar
    summaries and more rows, before optional state/source. No sorting by
    reported results, rounding, or inferred semantics.
    Historical /1 and /2 formats remain unchanged when no generic row is needed
    or can fit; all arrays still count as atomic fields in omission accounting.
    """
    previous = _paired_context(item, limit)  # validates input and legacy budget
    if len(_json(item)) <= limit:
        return previous
    catalog = _row_catalog(item)
    if not catalog:
        return previous
    previous_value = json.loads(previous)
    complete = {field['path'] for field in previous_value.get('fields', [])}
    if all(array['path'] in complete for array in catalog):
        return previous
    candidates = sorted(_fields(item), key=lambda row: row[:3])
    total_observations = sum(row[3] for row in candidates)
    paired = _comparison_catalog(item)
    protected = {array['path'] for array in catalog if array['path'] in complete}
    # Increasing a card's allowance must not replace already delivered compact
    # measurements with row-index metadata. Small vectors are atomic summaries
    # too; protecting them is based on structure/size, never their values.
    protected.update(path for _, size, path, observation, _ in candidates
                     if path in complete and observation and not _state_path(path)
                     and size <= _COMPACT_SCALAR_CHARS)
    if _COMPARISON_PATH in complete:
        protected.add(_COMPARISON_PATH)
    # Supplementary metadata covers only arrays not already delivered whole.
    catalog = [array for array in catalog if array['path'] not in protected]
    selected = [row[4] for row in candidates if row[2] in protected]
    selected_paths, rows = set(protected), {}
    prior_comparison = previous_value.get('comparison_projection')
    groups = list(prior_comparison['groups']) if prior_comparison else []
    array_paths = {array['path'] for array in catalog}
    reserved_paths = ([_COMPARISON_PATH] if groups else []) + [array['path'] for array in catalog]
    reserved_paths = reserved_paths[:_MAX_OMITTED_PATHS]

    def render(paths=None):
        paths = reserved_paths if paths is None else paths
        observed = sum(row[3] for row in candidates if row[2] in selected_paths)
        omitted = len(candidates) - len(selected)
        return _json({'schema': ROW_PROJECTION_SCHEMA, 'original_sha256': _hash(item),
            'fields': selected, 'observations_state': 'partial',
            'omitted_fields': omitted, 'omitted_observation_fields': total_observations - observed,
            'omitted_paths': list(paths), 'omitted_paths_omitted': omitted - len(paths),
            'comparison_projection': _comparison_metadata(paired[0], groups) if groups else None,
            'observation_rows': _row_metadata(catalog, rows)})

    # /3 overhead may itself be too expensive: never trade an already
    # delivered paired group or complete array for unrelated generic rows.
    if len(render()) > limit:
        return previous

    def add_row(array, row):
        kept = rows.setdefault(array['path'], [])
        if any(existing['index'] == row['index'] for existing in kept):
            return False
        kept.append(row)
        if len(render()) <= limit:
            return True
        kept.pop()
        return False

    # One whole row per array precedes small exact summaries. This prevents one
    # long row array from consuming all space before other observed records.
    for array in catalog:
        for row in array['rows']:
            if add_row(array, row):
                break
    if not any(rows.values()):
        return previous

    def add_field(candidate):
        _, size, path, _, field = candidate
        if (path in selected_paths or path in array_paths
                or path == _COMPARISON_PATH and groups or size > limit):
            return
        selected.append(field)
        selected_paths.add(path)
        if len(render()) > limit:
            selected.pop()
            selected_paths.remove(path)

    # Preserve compact atomic observations (including short summary vectors)
    # before additional rows. Bulky vectors, echoed source and continuation
    # state cannot occupy this reservation. No value's sign or score is used.
    for candidate in candidates:
        _, size, path, observation, field = candidate
        if observation and not _state_path(path) and size <= _COMPACT_SCALAR_CHARS:
            add_field(candidate)
    for array in catalog:
        for row in array['rows']:
            add_row(array, row)
    for candidate in candidates:
        add_field(candidate)
    omitted = sorted((row[2] for row in candidates if row[2] not in selected_paths),
                     key=lambda path: (len(_json(path)), path))
    paths = list(reserved_paths)
    for path in omitted:
        if path in paths:
            continue
        if len(paths) >= _MAX_OMITTED_PATHS or len(render(paths + [path])) > limit:
            break
        paths.append(path)
    return render(paths)


def verify_projection(value, original):
    """Authenticate full output, historical /1, paired /2 and whole-row /3 views.

    Pure saved-JSON verification, reusable by observers without Engine imports.
    A successful check authenticates provenance and exact values, not claims.
    """
    if _json(value) == _json(original):
        return
    if type(value) is not dict:
        raise ValueError('Invalid measurement excerpt')
    candidates = list(_fields(original))
    fields = {row[2]: (row[4]['value'], row[3]) for row in candidates}
    total_observations = sum(flag for _, flag in fields.values())
    if value.get('omitted') is True:
        if (set(value) - {'schema', 'omitted', 'omitted_fields', 'omitted_observation_fields'}
                or value.get('schema') not in (None, PROJECTION_SCHEMA)
                or type(value.get('omitted_fields', len(fields))) is not int
                or value.get('omitted_fields', len(fields)) != len(fields)
                or type(value.get('omitted_observation_fields', total_observations)) is not int
                or value.get('omitted_observation_fields', total_observations) != total_observations):
            raise ValueError('Omitted measurement fields differ')
        return
    schema = value.get('schema')
    if type(schema) is not str:
        raise ValueError('Invalid measurement projection schema')
    expected_keys = {'schema', 'original_sha256', 'fields', 'observations_state',
        'omitted_fields', 'omitted_observation_fields', 'omitted_paths', 'omitted_paths_omitted'}
    if schema in (COMPARISON_PROJECTION_SCHEMA, ROW_PROJECTION_SCHEMA):
        expected_keys.add('comparison_projection')
    if schema == ROW_PROJECTION_SCHEMA:
        expected_keys.add('observation_rows')
    if (schema not in PROJECTION_SCHEMAS or set(value) != expected_keys
            or value.get('original_sha256') != _hash(original)
            or type(value.get('fields')) is not list):
        raise ValueError('Measurement projection identity differs from receipt')
    shown = set()
    for field in value['fields']:
        if type(field) is not dict or set(field) != {'path', 'value'} or type(field['path']) is not str:
            raise ValueError('Invalid measurement projection field')
        path = field['path']
        if path in shown or path not in fields or _json(field['value']) != _json(fields[path][0]):
            raise ValueError('Measurement projection changes a saved value')
        shown.add(path)
    observed = sum(fields[path][1] for path in shown)
    output = original.get('output')
    observations = output.get('observations') if type(output) is dict else None
    state = ('not_present' if type(observations) is not dict else 'originally_empty' if not observations
        else 'all_omitted' if not observed else 'complete' if observed == total_observations else 'partial')
    if schema == COMPARISON_PROJECTION_SCHEMA or (schema == ROW_PROJECTION_SCHEMA
            and value['comparison_projection'] is not None):
        catalog = _comparison_catalog(original)
        comp = value['comparison_projection']
        if (catalog is None or type(comp) is not dict or type(comp.get('groups')) is not list
                or not comp['groups'] or _COMPARISON_PATH in shown):
            raise ValueError('Invalid paired measurement projection')
        rows, available = catalog
        by_seed = {group['seed']: group for group in available}
        prior = None
        for group in comp['groups']:
            if (type(group) is not dict or type(group.get('seed')) is not int
                    or prior is not None and group['seed'] <= prior
                    or group['seed'] not in by_seed
                    or _json(group) != _json(by_seed[group['seed']])):
                raise ValueError('Paired measurement group differs from receipt')
            prior = group['seed']
        if _json(comp) != _json(_comparison_metadata(rows, comp['groups'])):
            raise ValueError('Paired measurement coverage differs from receipt')
        state = 'partial'  # Core rows are not the complete saved observations.
    if schema == ROW_PROJECTION_SCHEMA:
        catalog = [array for array in _row_catalog(original) if array['path'] not in shown]
        actual = value['observation_rows']
        if type(actual) is not dict or type(actual.get('arrays')) is not list or not actual['arrays']:
            raise ValueError('Invalid whole-row measurement projection')
        available = {array['path']: array for array in catalog}
        selected = {}
        prior_path = None
        for array in actual['arrays']:
            path = array.get('path') if type(array) is dict else None
            if (type(path) is not str or path not in available or path in shown
                    or prior_path is not None and path <= prior_path
                    or type(array.get('rows')) is not list or not array['rows']):
                raise ValueError('Invalid observation array identity')
            prior_path = path
            prior_index = -1
            for row in array['rows']:
                index = row.get('index') if type(row) is dict else None
                if (type(index) is not int or index <= prior_index
                        or index >= available[path]['total_rows']
                        or _json(row) != _json(available[path]['rows'][index])):
                    raise ValueError('Observation row differs from receipt')
                prior_index = index
            selected[path] = array['rows']
        if _json(actual) != _json(_row_metadata(catalog, selected)):
            raise ValueError('Observation row coverage differs from receipt')
        state = 'partial'
    omitted = set(fields) - shown
    paths = value.get('omitted_paths')
    counts = {'omitted_fields': len(omitted), 'omitted_observation_fields': total_observations-observed,
              'omitted_paths_omitted': len(omitted)-len(paths) if type(paths) is list else None}
    if (value.get('observations_state') != state or type(paths) is not list
            or any(type(path) is not str for path in paths) or len(paths) != len(set(paths))
            or not set(paths) <= omitted
            or any(type(value.get(key)) is not int or value[key] != count for key, count in counts.items())):
        raise ValueError('Measurement projection accounting differs from receipt')
