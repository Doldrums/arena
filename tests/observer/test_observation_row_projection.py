"""Read-only observer accepts exact whole rows and rejects resealed forgeries."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from arena.observers.sciel.compat.result_projection import success_context, verify_projection
from arena.observers.sciel.research_tools import cell_detail
import test_paired_measurement_projection as shared_fixture


FIXTURE = Path(__file__).parent / 'fixtures/observation_measurement_heilbronn_v4.json'


def observations():
    return json.loads(FIXTURE.read_text())['output']['observations']


def projected():
    original = {'output': {'observations': observations()}, 'error': None}
    view = json.loads(success_context(original, 4669))
    assert view['schema'] == 'sciel-tool-result-projection/3'
    assert len(json.dumps(view, ensure_ascii=True, sort_keys=True, separators=(',', ':'))) <= 4669
    verify_projection(view, original)
    return original, view


def install(root, monkeypatch):
    monkeypatch.setattr(shared_fixture, 'measurements', observations)
    monkeypatch.setattr(shared_fixture, 'paired', projected)
    return shared_fixture.install(root)


def test_public_reader_authenticates_exact_observation_rows_without_engine_or_adoption(tmp_path, monkeypatch):
    cell, checkpoint, events, _, data = install(tmp_path, monkeypatch)
    before = deepcopy(checkpoint)
    result = cell_detail(tmp_path, cell, checkpoint, events)
    delivery = result['related']['shared_observations'][0]
    assert delivery['verified'] is True
    view = delivery['entries'][0]['measurement']
    assert view == data['entries'][0]['measurement']
    arrays = view['observation_rows']['arrays']
    checks = next(item for item in arrays if item['path'] == '/output/observations/checks')
    assert checks['shown_rows'] >= 1
    assert checks['total_rows'] == len(observations()['checks']) == 3
    assert checks['shown_rows'] + checks['omitted_rows'] == 3
    for row in checks['rows']:
        assert row['value'] == observations()['checks'][row['index']]
    assert view['observations_state'] == 'partial'
    assert result['related']['invocations'] == []
    assert checkpoint == before


@pytest.mark.parametrize('damage', ['gain', 'partial_row', 'array_hash', 'row_hash',
                                    'index', 'count', 'complete_claim'])
def test_resealed_prompt_cannot_forge_measurement_row_or_coverage(tmp_path, monkeypatch, damage):
    cell, checkpoint, events, proposal, data = install(tmp_path, monkeypatch)
    view = data['entries'][0]['measurement']
    block = view['observation_rows']
    array = next(item for item in block['arrays'] if item['path'] == '/output/observations/checks')
    row = array['rows'][0]
    if damage == 'gain':
        row['value']['max_first_order_gain'] = 42
    elif damage == 'partial_row':
        row['value'].pop(next(iter(row['value'])))
    elif damage == 'array_hash':
        array['original_sha256'] = 'f' * 64
    elif damage == 'row_hash':
        row['original_sha256'] = 'f' * 64
    elif damage == 'index':
        row['index'] = False
    elif damage == 'count':
        block['omitted_rows'] += 1
    else:
        view['observations_state'] = 'complete'
    shared_fixture.reseal(tmp_path, events, proposal, data)
    result = cell_detail(tmp_path, cell, checkpoint, events)
    assert result['related']['shared_observations'] == []
    assert result['related_coverage']['shared_observations']['verification_failed'] == 1
