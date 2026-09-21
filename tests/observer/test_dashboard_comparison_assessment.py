"""Saved declarations, execution status and comparison validity remain separate."""
from copy import deepcopy
import json

import pytest

from arena.observers.sciel.compat.models import canonical_bytes, content_hash
from arena.observers.sciel.research_tools import EVENT_SCHEMA, _compact, artifact_detail


def fixture(root, *, conditions_match=False, declared=True, damage=None):
    scope = dict(action_id='a' * 64, cell_id='c' * 64, cell_revision_id='d' * 64)
    tool = 'e' * 64
    protocol = dict(question_key='Does the alternative improve the measured objective?',
        new_uncertainty='Compare two methods on matched seeds.', budget_reason='Initial comparison.',
        saved_state_plan='Save best output and seed for each arm.', conditions_json='{"inputs":"fixed"}',
        kind='controlled_comparison', budget_action='initial', prior_receipt_ids=[],
        arms=[dict(id='base', method='baseline'), dict(id='other', method='alternative')],
        matched_seeds=[0, 1], cpu_seconds_per_arm=1)
    action = dict(action='use', tool_id=tool, experimental_protocol=protocol)
    proposal = dict(scope, attempt=0, response={'text': json.dumps(action)})
    if damage == 'foreign_scope':
        proposal['cell_id'] = 'f' * 64
    elif damage == 'wrong_attempt':
        proposal['attempt'] = 1

    def save(kind, payload):
        record = dict(schema='sciel-research-tool-artifact/1', kind=kind, payload=payload)
        ident = content_hash(record)
        target = root / 'research_tools' / 'artifacts' / (ident + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_bytes(record))
        return ident

    proposal_id = save('proposal', proposal)
    rows = [dict(arm_id=arm, seed=seed, cpu_seconds=.2, best_result=score,
                 saved_state={'seed': seed}, conditions={'inputs': 'fixed'} if conditions_match else {})
            for arm, score in [('base', 10), ('other', 12)] for seed in [0, 1]]
    payload = dict(scope, tool_id=tool,
        receipt=dict(invocation_id=content_hash(dict(action_id=scope['action_id'], attempt=0, tool_id=tool)),
            status='ok', output=dict(status='success', observations={'comparison_results': rows})))
    if declared:
        payload['experiment_proposal_id'] = proposal_id
    # Authored claims cannot overwrite host assessment.
    payload['comparison_assessment'] = {'status': 'verified', 'report_shape': 'complete'}
    ident = save('invocation', payload)
    events = [dict(event='research_tool', schema=EVENT_SCHEMA, phase='invocation_result',
        receipt_id=ident, **scope, tool_id=tool)]
    return ident, proposal_id, events


@pytest.mark.parametrize('conditions_match', [False, True])
def test_successful_execution_keeps_exact_comparison_warning_and_unverified_adherence(tmp_path, conditions_match):
    ident, proposal_id, events = fixture(tmp_path, conditions_match=conditions_match)
    detail = artifact_detail(tmp_path, ident, events)
    assert detail['verified'] and detail['payload']['receipt']['output']['status'] == 'success'
    envelope = detail['comparison_assessment']
    assert envelope['receipt_id'] == ident and envelope['proposal_id'] == proposal_id
    assert envelope['status'] == 'assessed'
    assessment = envelope['assessment']
    assert assessment['report_shape'] == ('complete' if conditions_match else 'invalid')
    assert assessment['problems'] == ([] if conditions_match else ['reported conditions differ'])
    assert assessment['adherence'] == 'tool_reported_unverified'
    assert detail['payload']['receipt']['output']['observations']['comparison_results'][0]['best_result'] == 10


@pytest.mark.parametrize('damage', ['foreign_scope', 'wrong_attempt'])
def test_declared_comparison_cannot_be_borrowed_from_another_invocation(tmp_path, damage):
    ident, _, events = fixture(tmp_path, damage=damage)
    with pytest.raises(ValueError, match='comparison proposal differs'):
        artifact_detail(tmp_path, ident, events)


def test_old_receipt_without_a_declaration_has_no_invented_validity(tmp_path):
    ident, _, events = fixture(tmp_path, declared=False)
    detail = artifact_detail(tmp_path, ident, events)
    assert detail['comparison_assessment']['status'] == 'unavailable'
    assert detail['comparison_assessment']['assessment'] is None


def test_research_step_preserves_bounded_recorded_warning_without_inventing_adherence(tmp_path):
    ident, proposal_id, events = fixture(tmp_path)
    a = artifact_detail(tmp_path, ident, events)['comparison_assessment']['assessment']
    step = dict(receipt_id=ident, proposal_id=proposal_id, status='success', comparison_report_assessment=a)
    assert _compact(step)['comparison_report_assessment'] == a
    forged = deepcopy(step)
    forged['comparison_report_assessment']['adherence'] = 'verified'
    assert 'comparison_report_assessment' not in _compact(forged)
