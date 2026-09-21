"""Sharing assignments are visible without inventing scientific outcomes."""
from copy import deepcopy
import hashlib
import json

import pytest

from arena.observers.sciel.research_tools import _sharing, research_tools_view, EVENT_SCHEMA


def fixture():
    cell, tool = 'a'*64, 'b'*64
    item = dict(tool_id=tool, stage='independent_replay', cell_id=cell,
        snapshot_artifact_id='c'*64, reference_receipt_id='d'*64, status='ready',
        reason='eligible_stage', queue_sequence=0, action_id=None, job_ids=[],
        receipt_id=None, completed_iteration=None)
    ident = hashlib.sha256(json.dumps({k:item[k] for k in ('tool_id','stage','cell_id')},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    state = dict(schema='sciel-research-sharing/1',next_sequence=1,last_queue='question',
        waiting_methods={},items={ident:item})
    return cell, ident, {'research_tools':{'sharing':state}}


def test_assigned_and_completed_sharing_never_manufacture_lifecycle_counts():
    cell, ident, checkpoint = fixture()
    rows = [dict(event='research_tool',schema=EVENT_SCHEMA,phase='cell_created',
        cell_id=cell,cell_revision_id='e'*64,island_id=1,question='Existing independent question')]
    before = deepcopy(checkpoint)
    view = research_tools_view({},checkpoint,rows)
    assert checkpoint == before
    assert view['sharing']['items'][0]['id'] == ident
    assert view['cells'][0]['sharing'][0]['snapshot_verified'] is False
    assert view['lifecycle']['counts']['independent_replays'] == 0
    assert view['lifecycle']['counts']['adoptions'] == 0
    assert view['lifecycle']['counts']['post_adoption_uses'] == 0
    checkpoint['research_tools']['sharing']['items'][ident].update(status='completed',
        completed_iteration=2,reason='tool_error',receipt_id='f'*64)
    completed = research_tools_view({},checkpoint,rows)
    assert completed['sharing']['summary']['completed'] == 1
    assert completed['lifecycle']['counts'] == view['lifecycle']['counts']
    assert completed['summary']['actual_invocations'] == 0


@pytest.mark.parametrize('damage', ['unknown_cell','work_id','scheduled','clock','jobs','snapshot','sequence'])
def test_malformed_or_uncommitted_assignments_do_not_grant_visibility(damage):
    cell, ident, checkpoint = fixture()
    queue = checkpoint['research_tools']['sharing']
    item = queue['items'][ident]
    if damage == 'unknown_cell': item['cell_id'] = '9'*64
    elif damage == 'work_id': queue['items'] = {'0'*64:item}
    elif damage == 'scheduled': item['status'] = 'scheduled'
    elif damage == 'clock': item['completed_iteration'] = 2
    elif damage == 'jobs': item['job_ids'] = ['../secret']
    elif damage == 'snapshot': item['snapshot_artifact_id'] = '../secret'
    elif damage == 'sequence': item['queue_sequence'] = 1
    cells = {cell:{}}
    view = _sharing(checkpoint,cells)
    assert view['summary']['invalid'] == 1
    assert not view['items']
    assert 'sharing' not in cells[cell]


def test_old_archives_and_no_recipient_wait_do_not_invent_cells_or_activity():
    cell, ident, checkpoint = fixture()
    assert _sharing({}, {})['scope'] == 'not_recorded'
    queue = checkpoint['research_tools']['sharing']
    queue['items'] = {}
    queue['waiting_methods'] = {'b'*64:'no_recipient_yet'}
    cells = {}
    view = _sharing(checkpoint,cells)
    assert view['summary']['no_recipient_yet'] == 1
    assert view['summary']['total'] == 0
    assert cells == {}
    queue['schema'] = 'future/99'
    assert not _sharing(checkpoint,cells)['available']
