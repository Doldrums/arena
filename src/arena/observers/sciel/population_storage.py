"""Storage coordinates and bounded projections of literal checkpoint vectors.

Never loads an encoder, executes a candidate, recomputes niche membership, or
mistakes a categorical niche ID for a latent coordinate. PCA is a snapshot-only
visual projection; the engine's fitted descriptor axis is a separate object.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

MAX_DIMENSIONS = 128
MAX_POINTS = 2048
MAX_FIT_POINTS = 256
MAX_CENTRES = 256
MAX_ASSIGNMENTS = 16384


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _int(value):
    return value if type(value) is int and value >= 0 else None


def _number(value):
    try:
        return float(value) if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _vector(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_DIMENSIONS:
        return None
    values = [_number(item) for item in value]
    return values if all(item is not None for item in values) else None


def _axis(key, label, kind, bins=None):
    return dict(key=key, label=label, title=label, type=kind, bins=bins)


def _kind(container, descriptor, niche):
    # ContainerDatabase replaces legacy niche_fn, even if descriptor_info still
    # names that previously configured function. Its actual store takes priority.
    if container is not None and container not in {'legacy','grid','pool','pool_novelty','cvt','vq','annealed'}:
        return 'unknown'
    if container in {'pool', 'pool_novelty'}:
        return 'pool'
    if container in {'cvt', 'vq', 'annealed'}:
        return container
    if container == 'grid':
        return 'map_elites'
    if descriptor == 'repeat_ranked_pool':
        return 'pool'
    if niche or descriptor == 'vq_niche':
        return 'vq_elites'
    known_descriptor = descriptor in {'code_length','legacy_random_raw'} or bool(re.fullmatch(r'pca[1-9][0-9]*_.+', descriptor or ''))
    return 'map_elites' if container == 'legacy' or known_descriptor else 'unknown'


def _symmetric_eigen(matrix):
    """Deterministic cyclic Jacobi diagonalization of a bounded real matrix."""
    size = len(matrix)
    values = [row[:] for row in matrix]
    vectors = [[float(i == j) for j in range(size)] for i in range(size)]
    total = math.fsum(abs(values[i][i]) for i in range(size))
    tolerance = max(1e-30, total*1e-14)
    for _ in range(48):
        if max((abs(values[p][q]) for p in range(size) for q in range(p+1,size)), default=0.) <= tolerance:
            return [values[i][i] for i in range(size)], vectors, True
        for p in range(size):
            for q in range(p+1,size):
                off = values[p][q]
                if abs(off) <= tolerance:
                    continue
                tau = (values[q][q]-values[p][p])/(2*off)
                tangent = math.copysign(1., tau)/(abs(tau)+math.hypot(1.,tau))
                cosine = 1/math.sqrt(1+tangent*tangent)
                sine = tangent*cosine
                values[p][p] -= tangent*off
                values[q][q] += tangent*off
                values[p][q] = values[q][p] = 0.
                for i in range(size):
                    if i != p and i != q:
                        left,right = values[i][p],values[i][q]
                        values[i][p] = values[p][i] = cosine*left-sine*right
                        values[i][q] = values[q][i] = sine*left+cosine*right
                    left,right = vectors[i][p],vectors[i][q]
                    vectors[i][p] = cosine*left-sine*right
                    vectors[i][q] = sine*left+cosine*right
    return [], [], False


def project_vectors(points):
    """Deterministic PCA, with bounded fitting work and no fabricated jitter.

    A complete symmetric covariance eigensolve selects the leading directions;
    no starting vector can omit an orthogonal high-variance subspace. Zero-
    variance directions are padded with zeros. ``projected_rank`` is displayed
    rank, not a claim about all latent dimensions beyond this saved fit subset.
    """
    if not points:
        return dict(available=False, reason='No literal vectors were recorded.', points=[])
    dims = len(points[0]['vector'])
    if not 1 <= dims <= MAX_DIMENSIONS or any(len(p['vector']) != dims for p in points):
        return dict(available=False, reason='Recorded vectors have inconsistent or unsupported dimensions.', points=[])
    count = min(MAX_FIT_POINTS, len(points))
    indices = [i*(len(points)-1)//(count-1) for i in range(count)] if count > 1 else [0]
    fit = [points[index]['vector'] for index in indices]
    # Global scale keeps finite but very large literal vectors from overflowing
    # covariance. Positions retain their recorded units when rescaled below.
    scale = max((abs(value) for point in points for value in point['vector']), default=0.) or 1.
    fit = [[value/scale for value in row] for row in fit]
    mean = [math.fsum(row[j] for row in fit)/count for j in range(dims)]
    centred = [[row[j]-mean[j] for j in range(dims)] for row in fit]
    covariance = [[0.]*dims for _ in range(dims)]
    for j in range(dims):
        for k in range(j, dims):
            covariance[j][k] = covariance[k][j] = math.fsum(row[j]*row[k] for row in centred)/count
    total = math.fsum(covariance[j][j] for j in range(dims))
    eigenvalues, eigenvectors, converged = _symmetric_eigen(covariance)
    if not converged:
        return dict(available=False, reason='Snapshot PCA did not converge within the bounded solve.', points=[])
    ordered = sorted(range(dims), key=lambda j: (-eigenvalues[j],j))
    basis, selected_values = [], []
    for index in ordered[:3]:
        value = eigenvalues[index]
        if value <= max(1e-28, total*1e-12):
            continue
        vector = [row[index] for row in eigenvectors]
        if vector[max(range(dims), key=lambda j: abs(vector[j]))] < 0:
            vector = [-v for v in vector]
        basis.append(vector);selected_values.append(value)
    projected = []
    for point in points:
        centred_point = [point['vector'][j]/scale-mean[j] for j in range(dims)]
        position = [math.fsum(a*b for a,b in zip(centred_point, axis))*scale for axis in basis]
        if not all(math.isfinite(value) for value in position):
            return dict(available=False, reason='Recorded vector scale cannot be projected finitely.', points=[])
        projected.append(dict(point, position=position+[0.]*(3-len(position))))
    explained = [min(1., max(0., value/total)) if total else 0. for value in selected_values]
    return dict(available=True, method='pca', algorithm='deterministic_symmetric_jacobi',
        input_dimensions=dims, output_dimensions=3, projected_rank=len(basis),
        axes=[_axis('pc'+str(i+1), 'Snapshot PC '+str(i+1), 'projected') for i in range(3)],
        explained_variance=explained+[0.]*(3-len(explained)),
        fit_count=count, fit_population_count=len(points), fit_sampled=count<len(points),
        converged=converged, points=projected,
        notes=['PCA is fitted to these saved vectors; axes can rotate when the checkpoint changes.',
               'Unused dimensions are zero; no jitter or invented program coordinates.',
               'Explained variance refers to the declared fit subset, not the encoder training corpus.'])


def _unavailable(reason, iteration=None, stale=None):
    return dict(available=False, method=None, input_dimensions=None, output_dimensions=None,
        axes=[], explained_variance=None, projected_rank=None, points=[], source='checkpoint',
        iteration=iteration, stale=stale, reason=reason, notes=[reason])


def storage_view(checkpoint, population, config, descriptor):
    """Keep current grid bindings and older checkpoint geometry explicitly apart."""
    checkpoint, population, config, descriptor = map(_dict, (checkpoint, population, config, descriptor))
    db = _dict(checkpoint.get('db'));saved_container = _dict(db.get('container'))
    raw_programs = db.get('programs', [])
    if isinstance(raw_programs, dict):
        raw_programs = list(raw_programs.values())
    scores = {program['id']: _number(program.get('score')) for program in _list(raw_programs)
              if isinstance(program, dict) and isinstance(program.get('id'), str)}
    container = _dict(saved_container.get('config')).get('kind') or _dict(config.get('container')).get('kind')
    container = container if isinstance(container, str) else None
    descriptor_kind = descriptor.get('kind') if isinstance(descriptor.get('kind'), str) else None
    niche = _dict(db.get('niche'))
    kind = _kind(container, descriptor_kind, niche)
    bins = _int(config.get('grid_bins'))
    axes, notes = [], []
    if kind == 'vq_elites':
        label = 'VQ niches × score bins'
        axes = [_axis('niche', 'VQ niche ID', 'categorical'), _axis('score_bin', 'Score bin', 'ordinal', bins)]
        notes.append('Niche IDs are insertion-order categories, not distances. The legacy VQ codebook is global across islands.')
    elif kind == 'map_elites':
        length = descriptor_kind == 'code_length'
        label = 'MAP-Elites · descriptor × score bins'
        axes = [_axis('descriptor_bin', 'Code length bin' if length else 'Recorded descriptor bin', 'ordinal', bins),
                _axis('score_bin', 'Score bin', 'ordinal', bins)]
        notes.append('The stored grid has two axes. Any island-layer display uses a categorical slice, not a third embedding coordinate.')
        if container == 'grid' and descriptor_kind == 'vq_niche':
            notes.append('Explicit grid storage overrides the configured VQ descriptor label; its descriptor function is not identified by that label.')
    elif kind in {'cvt', 'vq', 'annealed'}:
        label = {'cvt':'CVT centres', 'vq':'Adaptive VQ centres', 'annealed':'Annealed centres'}[kind]
        axes = [_axis('centre', 'Centre ID within island', 'categorical')]
        notes.append('This store keeps one elite per centre. Quality chooses elites; there is no additional score-bin axis.')
    elif kind == 'pool':
        label = 'Ranked program pool'
        notes.append('This store has no grid or geometric storage axes. Membership is separate from the global archive.')
    else:
        label = 'Storage not recorded'
        notes.append('Current defaults are not substituted for missing storage metadata.')
    assignments = []
    total_cells = 0
    for island in _list(population.get('islands')):
        total_cells += island.get('grid_cell_count') if _int(island.get('grid_cell_count')) is not None else len(_list(island.get('grid')))
        for cell in _list(island.get('grid')):
            if len(assignments) >= MAX_ASSIGNMENTS:
                break
            assignments.append(dict(island_id=island.get('id'), program_id=cell.get('candidate_id'),
                cell=[cell.get('x'), cell.get('y')], niche_id=cell.get('x') if kind in {'vq_elites', 'cvt', 'vq', 'annealed'} else None,
                score=cell.get('score'), binding='recorded_elite' if cell.get('candidate_id') is not None else 'recorded_cell'))
    cp_iteration = _int(checkpoint.get('iteration_no'))
    cp_stale = (population.get('source') != 'checkpoint' or population.get('stale') is True
                or cp_iteration != population.get('iteration'))
    projection = _unavailable('No per-program embedding vectors were saved for this storage.', cp_iteration, cp_stale)
    points, bad, total_points = [], 0, 0
    geometry_assignments = []
    global_book = kind == 'vq_elites' and bool(niche)
    if global_book:
        raw_centres = _list(niche.get('centroids'));total_points = len(raw_centres)
        for index, raw in enumerate(raw_centres[:MAX_CENTRES]):
            vector = _vector(raw)
            if vector is None:
                bad += 1;continue
            points.append(dict(id='niche:'+str(index), kind='centroid', island_id=None,
                program_id=None, niche_id=index, vector=vector))
        notes.append('Only saved grid elites have explicit program-to-niche bindings. Non-elite members are not assigned by nearest-centroid inference.')
    elif kind in {'cvt', 'vq', 'annealed'} and saved_container:
        vectors = _dict(saved_container.get('vectors'))
        for island in _list(db.get('islands')):
            island_id = _int(_dict(island).get('idx'))
            if island_id is None:
                continue
            geometry = _dict(_dict(saved_container.get('geometries')).get(str(island_id)))
            raw_centres = _list(geometry.get('centres'));ids = _list(geometry.get('centre_ids'))
            total_points += len(raw_centres)
            for index, raw in enumerate(raw_centres[:MAX_CENTRES]):
                vector = _vector(raw);niche_id = _int(ids[index]) if index < len(ids) else None
                if vector is None or niche_id is None:
                    bad += 1;continue
                if len(points) < MAX_POINTS:
                    points.append(dict(id='centre:'+str(island_id)+':'+str(niche_id), kind='centroid',
                        island_id=island_id, program_id=None, niche_id=niche_id, vector=vector))
            for program_id in _list(island.get('members')):
                total_points += 1
                vector = _vector(vectors.get(program_id)) if isinstance(program_id, str) else None
                if vector is None:
                    bad += 1;continue
                if len(points) < MAX_POINTS:
                    points.append(dict(id='program:'+str(island_id)+':'+program_id, kind='program',
                        island_id=island_id, program_id=program_id, niche_id=None, vector=vector, score=scores.get(program_id)))
        notes.append('Program points come only from vectors saved for active checkpoint members; historical db.programs entries are excluded.')
    if points:
        projection = project_vectors(points)
        projection.update(source='checkpoint.db.niche.centroids' if global_book else 'checkpoint.db.container',
            iteration=cp_iteration, stale=cp_stale, scope='global_codebook' if global_book else 'checkpoint_active_members_and_centres',
            recorded_count=total_points, projected_count=len(projection.get('points', [])),
            invalid_or_missing_vectors=bad, limited=total_points>len(points),
            limits=dict(points=MAX_POINTS, centres_per_codebook=MAX_CENTRES, dimensions=MAX_DIMENSIONS, fit_points=MAX_FIT_POINTS))
        projection['notes'] = projection.get('notes', []) + (['Some recorded vectors are missing, invalid, or outside the projection bounds.'] if total_points>len(points) else [])
        # Bind the visual receipt to exact finite vector values; no model identity
        # or semantic equivalence is inferred from this digest.
        projection['vectors_sha256'] = hashlib.sha256(json.dumps(points, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        # Projection and grid must describe the SAME checkpoint before links are
        # attached. A fresher journal's category IDs cannot bind an older cloud.
        for island in _list(db.get('islands')):
            island_id = _int(_dict(island).get('idx'))
            for cell, program_id in _dict(_dict(island).get('grid')).items():
                if not isinstance(cell, str) or not isinstance(program_id, str):
                    continue
                parts = cell.split(',')
                if len(parts) != 2 or not all(part.isdigit() for part in parts):
                    continue
                try:
                    x,y = map(int,parts)
                except ValueError:
                    continue
                if len(geometry_assignments) < MAX_ASSIGNMENTS:
                    geometry_assignments.append(dict(island_id=island_id,program_id=program_id,
                        cell=[x,y],niche_id=x,score=scores.get(program_id),binding='recorded_elite'))
        projection['assignments'] = geometry_assignments
    elif (global_book or kind in {'cvt', 'vq', 'annealed'}) and total_points:
        projection = _unavailable('Saved vectors are missing, non-finite, or outside supported dimensions.', cp_iteration, cp_stale)
        projection.update(recorded_count=total_points, invalid_or_missing_vectors=bad)
    native_dimensions = len(axes) if kind != 'unknown' else None
    return dict(schema='sciel-population-storage/1', kind=kind, label=label,
        container_kind=container if isinstance(container, str) else None,
        descriptor_kind=descriptor_kind, native_dimensions=native_dimensions,
        input_dimensions=projection.get('input_dimensions'), axes=axes,
        bins=dict(x=bins if kind=='map_elites' else None,y=bins if kind in {'map_elites','vq_elites'} else None),
        source=population.get('source'), iteration=population.get('iteration'), stale=population.get('stale'),
        assignments=assignments, assignments_count=total_cells,
        assignments_limited=total_cells>len(assignments), assignment_limit=MAX_ASSIGNMENTS,
        projection=projection, notes=notes)
