"""Read-only terminal interpretation projection; fake execution leaves only."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from arena.observers.sciel.research_tools import artifact_detail, cell_detail


def closed_cell(tmp_path):
    """Saved fake-provider evidence; the observer tests never construct an engine."""
    root = tmp_path / 'run'
    shutil.copytree(Path(__file__).with_name('fixtures') / 'terminal_decision', root)
    view = json.loads((root / 'view.json').read_text())
    return root, view['cell_id'], view['checkpoint'], view['events']


def test_cell_shows_authenticated_finish_separate_from_successful_execution(tmp_path):
    root, ident, checkpoint, events = closed_cell(tmp_path)
    detail = cell_detail(root, ident, checkpoint, events)
    decision = detail['terminal_decision']
    assert decision['verified'] and decision['conclusion'] == 'inconclusive'
    assert decision['interpretation'] == 'The returned geometry is invalid.'
    assert decision['next_decision'] == 'Repair the feasibility check.'
    assert 'not canonical' in decision['scope']
    assert detail['related']['invocations'][0]['tool_result_status'] == 'success'
    proposal = artifact_detail(root, decision['proposal_id'], events)
    assert json.loads(proposal['payload']['response']['text'])['reason'] == decision['interpretation']


@pytest.mark.parametrize('damage', ['rewrite_interpretation', 'foreign_action', 'proposal_file', 'reopened'])
def test_changed_or_stale_terminal_interpretation_is_not_presented(tmp_path, damage):
    root, ident, checkpoint, events = closed_cell(tmp_path)
    original = deepcopy(checkpoint)
    lifecycle = checkpoint['research_tools']['lifecycle']
    closure = lifecycle['cards'][ident]['decision']
    if damage == 'rewrite_interpretation':
        closure['interpretation'] = 'The returned geometry is VALID!!'
    elif damage == 'foreign_action':
        closure['action_id'] = 'f' * 64
    elif damage == 'proposal_file':
        path = root / 'research_tools/artifacts' / (closure['proposal_id'] + '.json')
        data = json.loads(path.read_text())
        data['payload']['cell_id'] = 'f' * 64
        path.write_text(json.dumps(data))
    else:
        lifecycle['research_state'][ident]['status'] = 'open'
    assert cell_detail(root, ident, checkpoint, events)['terminal_decision'] is None
    assert original['research_tools']['lifecycle']['cards'][ident]['observations']['status'] == 'success'


def test_historical_observation_card_has_no_invented_terminal_interpretation(tmp_path):
    root, ident, checkpoint, events = closed_cell(tmp_path)
    card = checkpoint['research_tools']['lifecycle']['cards'][ident]
    card['schema'] = 'sciel-research-check/3'
    del card['decision']
    assert cell_detail(root, ident, checkpoint, events)['terminal_decision'] is None
