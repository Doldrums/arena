"""Saved JSON only: paired measurement provenance through the public cell reader."""
from copy import deepcopy
import hashlib
import json

import pytest

from arena.observers.sciel.compat.result_projection import (
    COMPARISON_PROJECTION_SCHEMA, success_context, verify_projection,
)
from arena.observers.sciel.research_tools import cell_detail
from arena.observers.sciel.research_exchange import MARKER, _measurement
from test_dashboard_research_exchange import fixture, write


def measurements():
    # Arm-major source ordering: selecting a prefix would bias the comparison.
    return {'comparison_results': [
        dict(arm_id=arm, seed=seed, cpu_seconds=0 if arm == 'a' else .25,
             best_result={'score': seed / 10, 'detail/~雪': [False, None, 'λ']},
             conditions={'cpu_cap_seconds': 1, 'initial_state': 'same'},
             saved_state={'opaque': 'x' * 2400})
        for arm in ('a', 'b', 'c') for seed in (0, 1)],
        'candidate_source': 'inert text only ' * 1000}


def wrapper():
    return {'output': {'observations': measurements()}, 'error': None}


def paired():
    original = wrapper()
    view = json.loads(success_context(original, 6500))
    assert view['schema'] == COMPARISON_PROJECTION_SCHEMA
    return original, view


def install(root):
    """Replace fixture output by immutable paired output; rebind every saved ID."""
    cell, checkpoint, events = fixture(root)
    invocation = events[2]
    artifact_path = root / 'research_tools/artifacts' / (invocation['receipt_id'] + '.json')
    source = json.loads(artifact_path.read_text())
    source['payload']['receipt']['output']['observations'] = measurements()
    source_id = write(root, 'artifacts', source)
    invocation['receipt_id'] = source_id
    origin = invocation['cell_id']
    state = checkpoint['research_tools']['lifecycle']['cells']['cells'][origin]
    revision_path = root / 'research_tools/cells/revisions' / (state['head_revision'] + '.json')
    revision = json.loads(revision_path.read_text())
    revision['evidence'][0]['id'] = source_id
    state['head_revision'] = write(root, 'cells/revisions', revision)
    proposal_path = root / 'research_tools/artifacts' / (events[-1]['receipt_id'] + '.json')
    proposal = json.loads(proposal_path.read_text())
    data = json.JSONDecoder().raw_decode(proposal['payload']['prompt'].split(MARKER, 1)[1])[0]
    _, projection = paired()
    data['entries'][0].update(receipt_id=source_id, measurement=projection)
    events[-2]['delivered'][0].update(receipt_id=source_id, measurement_projection='partial')
    reseal(root, events, proposal, data)
    return cell, checkpoint, events, proposal, data


def reseal(root, events, proposal, data):
    proposal['payload']['prompt'] = MARKER + json.dumps(data)
    events[-1]['receipt_id'] = write(root, 'artifacts', proposal)
    events[-2]['prompt_sha256'] = hashlib.sha256(proposal['payload']['prompt'].encode()).hexdigest()


def test_public_reader_authenticates_exact_paired_measurement_without_adoption(tmp_path):
    cell, checkpoint, events, _, data = install(tmp_path)
    original = deepcopy(checkpoint)
    result = cell_detail(tmp_path, cell, checkpoint, events)
    delivery = result['related']['shared_observations'][0]
    assert delivery['verified'] is True
    assert delivery['entries'][0]['measurement'] == data['entries'][0]['measurement']
    assert 'causal benefit are not established' in delivery['scope']
    assert delivery['entries'][0]['measurement']['observations_state'] == 'partial'
    assert result['related']['invocations'] == []
    assert checkpoint == original


@pytest.mark.parametrize('damage', ['value', 'conditions', 'partial_seed', 'array_hash', 'row_hash', 'omission', 'count', 'claim', 'bool'])
def test_resealed_prompt_cannot_rewrite_source_rows_or_claim_full_delivery(tmp_path, damage):
    cell, checkpoint, events, proposal, data = install(tmp_path)
    view = data['entries'][0]['measurement']
    comp = view['comparison_projection']
    row = comp['groups'][0]['rows'][0]
    if damage == 'value': row['values']['best_result']['score'] = 1
    elif damage == 'conditions': row['values']['conditions']['cpu_cap_seconds'] = 2
    elif damage == 'partial_seed': comp['groups'][0]['rows'].pop()
    elif damage == 'array_hash': comp['original_sha256'] = 'f' * 64
    elif damage == 'row_hash': row['original_sha256'] = 'f' * 64
    elif damage == 'omission': row['omitted_values']['saved_state']['json_chars'] -= 1
    elif damage == 'count': comp['total_rows'] -= 1
    elif damage == 'claim': view['observations_state'] = 'complete'
    else: row['values']['cpu_seconds'] = False  # Original numeric zero is distinct.
    reseal(tmp_path, events, proposal, data)
    result = cell_detail(tmp_path, cell, checkpoint, events)
    assert result['related']['shared_observations'] == []
    assert result['related_coverage']['shared_observations']['verification_failed'] == 1


def test_budget_preserves_a_whole_reported_seed_or_explicitly_omits_comparison():
    original = wrapper()
    counts = set()
    for budget in (64, 500, 1200, 2000, 3000, 6500):
        text = success_context(original, budget)
        assert len(text) <= budget
        view = json.loads(text)
        verify_projection(view, original)
        _measurement(view, {'receipt': original, 'result': {'error': None}})
        if view.get('schema') == COMPARISON_PROJECTION_SCHEMA:
            comp = view['comparison_projection']
            counts.add(comp['shown_rows'])
            assert comp['shown_rows'] + comp['omitted_rows'] == 6
            for group in comp['groups']:
                assert {row['values']['arm_id'] for row in group['rows']} == {'a', 'b', 'c'}
        else:
            assert 'comparison_projection' not in view
            assert view.get('observations_state') != 'complete'
    assert counts == {3, 6}
