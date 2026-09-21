"""Bounded views of recorded memory delivery and research-format outcomes.

No current renderer or validator is applied to historical records. In particular,
guarded selection's provisional candidates are never treated as delivered advice.
"""
from __future__ import annotations

from collections import Counter


HISTORY_LIMIT = 120


def _dict(value):
    return value if isinstance(value, dict) else {}


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _ids(value):
    if not isinstance(value, list):
        return None
    ids = [item.get('id') if isinstance(item, dict) else item for item in value]
    return ids if all(isinstance(item, str) and item for item in ids) and len(set(ids)) == len(ids) else None


def _diagnostic(row):
    diagnostic = _dict(row.get('diagnostic'))
    if not diagnostic and isinstance(row.get('diagnostics'), list):
        diagnostic = _dict(next(iter(row['diagnostics']), None))
    return {key: (value[:320] if isinstance(value, str) else value)
            for key, value in diagnostic.items()
            if key in ('code', 'path', 'actual', 'maximum', 'minimum', 'kind', 'field', 'length')
            and (isinstance(value, str) or type(value) in (int, float))}


def _reason(row):
    value = row.get('reason') or row.get('error_type')
    return value[:320] if isinstance(value, str) else None


def reliability_view(start, checkpoint, rows, lessons):
    """Summaries span the journal; histories retain only the latest 120 records."""
    config = _dict(start.get('config')) or _dict(checkpoint.get('config'))
    research_config = _dict(config.get('research'))
    research = _dict(checkpoint.get('research'))
    knowledge = _dict(research.get('knowledge'))
    stored_known = isinstance(knowledge.get('lessons'), list) or any(
        row.get('event') == 'research' and isinstance(row.get('accepted_lesson_ids'), list)
        for row in rows)
    stored = sum(lesson.get('status') == 'active' for lesson in lessons) if stored_known else None
    attempts, conclusions, ideas = {}, {}, {}
    repairs = 0
    for row in rows:
        if row.get('event') != 'research':
            continue
        phase = row.get('phase')
        ident = row.get('experiment_id')
        if phase == 'attempt' and isinstance(ident, str):
            evidence = _dict(row.get('evidence'))
            metadata = _dict(row.get('lesson_presentation'))
            shown = _ids(metadata.get('presented'))
            injected = _ids(evidence.get('injected_ids'))
            consistent = (shown == injected if shown is not None and injected is not None else None)
            delivered = len(shown) if shown is not None and consistent is not False else None
            omitted = metadata.get('omitted')
            omissions_known = isinstance(omitted, list) and all(isinstance(item, dict) for item in omitted)
            size_drops = [item for item in omitted if item.get('reason') in
                          ('card_char_limit', 'memory_char_limit')] if omissions_known else None
            attempts[ident] = dict(experiment_id=ident, iteration=evidence.get('iteration'),
                stored_active=_count(metadata.get('stored_active_count')),
                ranked=_count(metadata.get('ranked_count')), selected=_count(metadata.get('selected_count')),
                delivered=delivered, dropped_by_size=len(size_drops) if size_drops is not None else None,
                delivered_ids=(shown or [])[:16], delivery_consistent=consistent,
                metadata_recorded=bool(metadata), rendered_chars=_count(metadata.get('rendered_chars')),
                omission_reasons=dict(Counter(item.get('reason', 'unknown') for item in omitted))
                    if omissions_known else None)
        if phase in ('aux_start', 'conclusion_rejected', 'conclusion_repair', 'conclusion'):
            if phase == 'aux_start':
                if row.get('kind') != 'conclusion':
                    continue
                ident = row.get('reference')
            if not isinstance(ident, str):
                continue
            item = conclusions.setdefault(ident, dict(experiment_id=ident, status='pending',
                reason=None, diagnostic={}, repairs=0))
            if phase == 'conclusion_rejected':
                item.update(reason=_reason(row), diagnostic=_diagnostic(row))
            elif phase == 'conclusion_repair':
                repairs += 1
                item['repairs'] += 1
                item.update(reason=_reason(row) or item['reason'], diagnostic=_diagnostic(row) or item['diagnostic'])
            elif phase == 'conclusion':
                status = row.get('status')
                item['status'] = status if status in ('parsed', 'invalid', 'skipped') else 'unknown'
                if status == 'skipped':
                    item['reason'] = _reason(row) or row.get('skip_reason')
        if phase == 'idea' and isinstance(row.get('idea_id'), str):
            ident = row['idea_id']
            item = ideas.setdefault(ident, dict(idea_id=ident, status='pending', iteration=None,
                card_requested=False, code_requested=False, terminal=False, reason=None, diagnostic={},
                card_rejections=0))
            action = row.get('action')
            if action == 'request_start':
                if row.get('stage') == 'card':
                    item['card_requested'] = True
                elif row.get('stage') == 'code':
                    item['code_requested'] = True
                item['iteration'] = row.get('iteration', item['iteration'])
            elif action == 'card_rejected':
                item.update(reason=_reason(row), diagnostic=_diagnostic(row))
                item['card_rejections'] += 1
            elif action == 'finish':
                item.update(status=row.get('status', 'unknown'), terminal=True)
            elif action == 'stopped':
                item.update(status='stopped', reason=_reason(row))
    memory_history = list(attempts.values())
    known = [item for item in memory_history if item['delivered'] is not None]
    zero_size = sum(item['ranked'] is not None and item['ranked'] > 0 and item['delivered'] == 0
                    and item['dropped_by_size'] is not None and item['dropped_by_size'] > 0
                    for item in memory_history)
    conclusion_history = list(conclusions.values())
    c = Counter(item['status'] for item in conclusion_history)
    idea_history = list(ideas.values())
    completed = [item for item in idea_history if item['terminal']]
    i = Counter(item['status'] for item in completed)
    before_code = sum(item['card_requested'] and not item['code_requested'] and
                      item['status'] in ('idea_card_invalid', 'idea_card_duplicate', 'idea_card_repair_exhausted')
                      for item in completed)
    return dict(schema='sciel-research-reliability/1', history_limit=HISTORY_LIMIT,
        enabled=research_config.get('enabled') if type(research_config.get('enabled')) is bool else None,
        memory=dict(stored_active=stored, attempts=len(attempts), metadata_known=len(known),
            metadata_unknown=len(attempts)-len(known), zero_delivered_due_size=zero_size if known else None,
            delivered_attempts=sum(item['delivered'] > 0 for item in known) if known else None,
            latest=memory_history[-1] if memory_history else None, history=memory_history[-HISTORY_LIMIT:],
            history_truncated=len(memory_history)>HISTORY_LIMIT),
        conclusions=dict(recorded=bool(conclusions), parsed=c['parsed'], rejected=c['invalid'],
            skipped=c['skipped'], pending=c['pending'], unknown=c['unknown'], repairs=repairs,
            history=conclusion_history[-HISTORY_LIMIT:], history_truncated=len(conclusions)>HISTORY_LIMIT),
        ideas=dict(recorded=bool(ideas), attempts=len(ideas), finished=len(completed),
            rejected_before_code=before_code, invalid_cards=i['idea_card_invalid'], duplicates=i['idea_card_duplicate'],
            repair_exhausted=i['idea_card_repair_exhausted'],
            evaluated=i['evaluated'], eval_failed=i['eval_failed'],
            history=idea_history[-HISTORY_LIMIT:], history_truncated=len(ideas)>HISTORY_LIMIT),
        notes=['Delivered means recorded in the prepared generation prompt, not proof of provider consumption or model use.',
               'Selected is the recorded final admitted lesson set. A scheduled conclusion correction can still be skipped by the auxiliary-call budget.',
               'Historical retrieval counts come only from recorded metadata; missing counts remain unknown.',
               'Conclusion and idea totals use final outcomes; intermediate validation failures may be repaired.',
               'Summary counts cover retained journal history; detail tables show the latest 120 records.'])
