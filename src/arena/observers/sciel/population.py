"""Bounded, read-only population views from recorded engine state.

Journal grids record bins and rounded elite scores, not elite IDs or embeddings.
Never recover those missing bindings by matching scores or recomputing models.
The caller supplies an already ancestry-filtered journal and validated checkpoint.
"""
from __future__ import annotations

import hashlib
import math

MAX_ISLANDS = 64
MAX_MEMBERS = 256
MAX_CELLS = 256
MAX_ARCHIVE = 128


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _int(value):
    return value if type(value) is int and value >= 0 else None


def _number(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _id(value):
    return value if isinstance(value, str) and 0 < len(value) <= 128 else None


def _metadata(value, depth=0):
    """Small literal JSON only; no code, model loading or unbounded vectors."""
    if depth > 3:
        return None
    if value is None or type(value) is bool:
        return value
    if type(value) in (int, float):
        return _number(value)
    if isinstance(value, str):
        return value[:2048]
    if isinstance(value, dict):
        return {str(key)[:128]: _metadata(item, depth + 1)
                for key, item in list(value.items())[:32]}
    if isinstance(value, list):
        return [_metadata(item, depth + 1) for item in value[:32]]
    return None


def _layout(config, descriptor, state, checkpoint_source):
    container = (_dict(_dict(state.get("container")).get("config"))
                 if checkpoint_source else _dict(state.get("container")))
    kind = container.get("kind") or _dict(config.get("container")).get("kind")
    descriptor_kind = descriptor.get("kind")
    kind = kind if isinstance(kind, str) else None
    descriptor_kind = descriptor_kind if isinstance(descriptor_kind, str) else None
    if kind in {"pool", "pool_novelty"} or descriptor_kind == "repeat_ranked_pool":
        layout_kind, x_label, y_label = "pool", "No grid", "No grid"
    elif kind in {"cvt", "vq", "annealed"}:
        layout_kind, x_label, y_label = "geometry", "Recorded centre ID", "Unused grid row"
    elif descriptor_kind == "vq_niche" and kind != "grid":
        layout_kind, x_label, y_label = "vq", "Recorded VQ niche ID", "Score bin"
    else:
        layout_kind = "map_elites" if descriptor_kind or kind in {"legacy", "grid"} else "unknown"
        x_label = "Code length bin" if descriptor_kind == "code_length" else "Recorded descriptor bin"
        y_label = "Score bin"
    return dict(kind=layout_kind, x_label=x_label, y_label=y_label,
                grid_bins=_int(config.get("grid_bins")), coordinates="recorded_bins",
                embedding_coordinates="unavailable")


def _retention(config):
    """Recorded capacity policy only; never manufacture slots from defaults."""
    target = _number(config.get("pop_cap"))
    kind = _dict(config.get("container")).get("kind")
    if kind == "legacy":
        limit = "soft"  # all grid elites are protected, even above pop_cap
    elif isinstance(kind, str) and kind in {"grid", "pool", "pool_novelty", "cvt", "vq", "annealed"}:
        limit = "hard"
    else:
        limit = "unknown"
    return dict(target_members_per_island=target if target is not None and target > 0 else None,
                limit_kind=limit)


def population_view(checkpoint, rows, start, sources):
    """Project one coherent snapshot; never mix stale cell IDs into newer grids."""
    checkpoint, start, sources = _dict(checkpoint), _dict(start), _dict(sources)
    rows = [row for row in _list(rows) if isinstance(row, dict)]
    db = _dict(checkpoint.get("db"))
    config = _dict(start.get("config")) or _dict(checkpoint.get("config"))
    descriptor = _metadata(_dict(start.get("descriptor")) or
                           _dict(_dict(checkpoint.get("identity")).get("descriptor")))
    snapshots = [(i, row) for i, row in enumerate(rows)
                 if row.get("event") == "population" and isinstance(row.get("islands"), list)]
    journal_index, journal = snapshots[-1] if snapshots else (-1, {})
    cp_iteration, journal_iteration = _int(checkpoint.get("iteration_no")), _int(journal.get("iteration_no"))
    anchor = _dict(_dict(checkpoint.get("provenance")).get("journal_anchor"))
    cp_index = next((i for i in range(len(rows) - 1, -1, -1)
                     if anchor.get("segment_id") is not None
                     and rows[i].get("segment_id") == anchor.get("segment_id")
                     and rows[i].get("event_seq") == anchor.get("event_seq")), None)
    cp_available = isinstance(db.get("islands"), list)
    use_cp = cp_available and (not journal or
        (cp_index is not None and cp_index >= journal_index) or
        (cp_index is None and cp_iteration is not None and journal_iteration is not None
         and cp_iteration > journal_iteration))
    state = db if use_cp else journal
    source = "checkpoint" if use_cp else "journal" if journal else "unavailable"
    iteration = cp_iteration if use_cp else journal_iteration
    evaluations = _int(checkpoint.get("B_evals") if use_cp else journal.get("B_evals"))
    counters = [value for row in rows for value in [_int(row.get("iteration_no"))] if value is not None]
    if cp_iteration is not None:
        counters.append(cp_iteration)
    latest_iteration = max(counters, default=None)
    selected_index = cp_index if use_cp else journal_index
    stale = (iteration < latest_iteration if iteration is not None and latest_iteration is not None else None)
    if selected_index is not None and selected_index >= 0:
        # Admissions and SH can alter membership within the same iteration.
        for row in rows[selected_index + 1:]:
            evidence = _dict(row.get("evidence"))
            if (row.get("event") == "sh_cut"
                    or row.get("event") == "research" and row.get("phase") == "outcome" and _id(evidence.get("child_id"))
                    or row.get("event") == "decision" and row.get("policy") == "initialization" and row.get("action") == "seed_program"
                    or row.get("event") == "decision" and row.get("policy") == "portfolio_seed" and row.get("ok") is True):
                stale = True
                break

    programs = db.get("programs", [])
    if isinstance(programs, dict):
        programs = list(programs.values())
    program_by_id = {p["id"]: p for p in _list(programs)
                     if isinstance(p, dict) and _id(p.get("id"))}
    aliases = {}
    for row in rows:
        if row.get("event") == "research" and row.get("phase") == "outcome":
            record = _dict(row.get("evidence"))
            child, research_id = _id(record.get("child_id")), _id(row.get("experiment_id"))
            if child and research_id == record.get("id"):
                aliases[child] = research_id

    def code_available(ident):
        return any(isinstance(_dict(sources.get(key)).get("code"), str)
                   for key in (ident, aliases.get(ident)) if key is not None)

    source_hashes = {}
    def source_hash(ident):
        if ident not in source_hashes:
            code = next((_dict(sources.get(key)).get('code')
                         for key in (ident, aliases.get(ident)) if key is not None
                         and isinstance(_dict(sources.get(key)).get('code'), str)), None)
            source_hashes[ident] = hashlib.sha256(code.encode('utf-8', errors='surrogatepass')).hexdigest() if code is not None else None
        return source_hashes[ident]

    # Count exact-source diversity over the complete saved membership, before
    # display caps. Missing source or membership is unknown, never unique by ID.
    known_hashes, counts, complete_membership = [], [], source != 'unavailable'
    for raw in _list(state.get('islands')):
        if not isinstance(raw, dict):
            complete_membership = False
            continue
        members = raw.get('members')
        count = len(members) if use_cp and isinstance(members, list) else _int(raw.get('n'))
        counts.append(count)
        ids = [_id(item) if use_cp else _id(item[0]) if isinstance(item, list) and item else None
               for item in _list(members)]
        complete_membership &= isinstance(members, list) and count == len(ids) and all(ids)
        known_hashes.extend(value for ident in ids if ident is not None
                            for value in [source_hash(ident)] if value is not None)
    total_members = sum(counts) if counts and all(value is not None for value in counts) else 0 if source != 'unavailable' and not counts else None
    sources_complete = bool(complete_membership and total_members is not None and len(known_hashes) == total_members)
    source_summary = dict(member_count=total_members, source_bound_members=len(known_hashes),
        known_unique_sources=len(set(known_hashes)), unique_sources=len(set(known_hashes)) if sources_complete else None,
        known_identical_source_copies=len(known_hashes) - len(set(known_hashes)), complete=sources_complete,
        iteration=iteration, source=source, scope='saved_population_membership',
        note='Exact source bytes only; seed copies and migrations are stored programs, not additional distinct sources. This does not establish behavioral diversity.')

    archive_values = _list(state.get("archive"))
    archive_ids = {ident for ident in archive_values if _id(ident)} if use_cp else None
    islands = []
    warnings = []
    if source == "journal":
        warnings.append("Journal member scores are rounded to 6 decimals; cell and archive scores to 4. Elite and archive program IDs are not recorded.")
    if stale:
        warnings.append("This population snapshot predates later recorded search activity.")
    if source == "unavailable":
        warnings.append("No population snapshot or checkpoint membership has been recorded.")
    if descriptor:
        warnings.append("Grid bins are recorded storage coordinates, not a two-dimensional embedding projection.")

    for raw in _list(state.get("islands"))[:MAX_ISLANDS]:
        if not isinstance(raw, dict):
            continue
        ident = _int(raw.get("idx"))
        if ident is None:
            continue
        cells = []
        elite_cells = {}
        raw_grid = raw.get("grid")
        if use_cp and isinstance(raw_grid, dict):
            for coordinate, candidate in raw_grid.items():
                if not isinstance(coordinate, str) or not _id(candidate):
                    continue
                parts = coordinate.split(",")
                if len(parts) != 2 or not all(part.isdigit() for part in parts):
                    continue
                try:
                    x, y = map(int, parts)
                except ValueError:
                    continue
                elite_cells[candidate] = [x, y]
                cells.append(dict(x=x, y=y, score=_number(_dict(program_by_id.get(candidate)).get("score")),
                                  candidate_id=candidate))
        elif not use_cp and isinstance(raw_grid, list):
            for cell in raw_grid:
                if isinstance(cell, list) and len(cell) >= 3 and _int(cell[0]) is not None and _int(cell[1]) is not None:
                    cells.append(dict(x=cell[0], y=cell[1], score=_number(cell[2]), candidate_id=None))
        members = []
        raw_members = raw.get("members")
        for item in _list(raw_members)[:MAX_MEMBERS]:
            candidate = _id(item) if use_cp else _id(item[0]) if isinstance(item, list) and item else None
            if candidate is None:
                continue
            program = _dict(program_by_id.get(candidate))
            score = _number(program.get("score")) if use_cp else _number(item[1]) if len(item) > 1 else None
            generation = _int(program.get("gen")) if use_cp else _int(item[2]) if len(item) > 2 else None
            members.append(dict(id=candidate, score=score, generation=generation,
                source_sha256=source_hash(candidate),
                code_available=code_available(candidate), grid_elite=candidate in elite_cells if use_cp and isinstance(raw_grid, dict) else None,
                grid_cell=elite_cells.get(candidate), archive_member=candidate in archive_ids if archive_ids is not None else None,
                parent_id=_id(program.get("parent_id")), origin=_id(program.get("origin")),
                source_island=_int(_dict(program_by_id.get(_id(program.get("parent_id")))).get("island"))
                    if program.get("origin") == "migrant" else None))
        best_id = _id(raw.get("best_id")) if use_cp else None
        best_score = _number(_dict(program_by_id.get(best_id)).get("score")) if use_cp else _number(raw.get("best"))
        islands.append(dict(id=ident, best_score=best_score, best_candidate_id=best_id,
            member_count=len(raw_members) if use_cp and isinstance(raw_members, list) else _int(raw.get("n")),
            grid_cell_count=len(raw_grid) if use_cp and isinstance(raw_grid, dict) else _int(raw.get("cells")),
            members=members, grid=cells[:MAX_CELLS], members_available=isinstance(raw_members, list),
            grid_available=isinstance(raw_grid, dict if use_cp else list),
            members_truncated=isinstance(raw_members, list) and len(raw_members) > MAX_MEMBERS,
            grid_truncated=len(cells) > MAX_CELLS))
    archive_members = []
    for item in archive_values[:MAX_ARCHIVE]:
        candidate = _id(item) if use_cp else None
        score = _number(_dict(program_by_id.get(candidate)).get("score")) if use_cp else _number(item)
        archive_members.append(dict(id=candidate, score=score, code_available=code_available(candidate)))
    layout = _layout(config, descriptor, state, use_cp)
    if not any(island["grid_available"] for island in islands):
        layout["coordinates"] = "unavailable"
    result = dict(schema="sciel-population/1", available=source != "unavailable", source=source,
        iteration=iteration, evaluations=evaluations, latest_iteration=latest_iteration, stale=stale,
        descriptor=descriptor, layout=layout, retention=_retention(config), islands=islands,
        source_summary=source_summary,
        island_count=len(_list(state.get("islands"))) if source != "unavailable" else None,
        islands_truncated=len(_list(state.get("islands"))) > MAX_ISLANDS,
        archive=dict(source="checkpoint_ids" if use_cp and isinstance(state.get("archive"), list) else
                     "journal_scores" if source == "journal" and isinstance(state.get("archive"), list) else "unavailable",
                     count=len(archive_values) if isinstance(state.get("archive"), list) else None,
                     members=archive_members, truncated=len(archive_values) > MAX_ARCHIVE), warnings=warnings)
    from .population_storage import storage_view
    result["storage"] = storage_view(checkpoint, result, config, descriptor)
    from .population_dynamics import dynamics_view
    result["dynamics"] = dynamics_view(checkpoint, rows, start, result)
    return result
