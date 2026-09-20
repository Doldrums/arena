"""Authenticated active-wave plans, separate from committed research evidence.

Only scheduling/question metadata crosses this boundary. Scientific state,
receipts, usage, revisions, adoption and candidate outcomes remain committed-only.
"""
from pathlib import Path
import re

from .workflow import digest, file_signature, pending_wave, read_json
from .research_tools import (
    HASH, LIMIT, _cell_events, _cells_view, _compact, _DetailReader, _events, _obj,
)


class PendingResearchView:
    def __init__(self, run_dir):
        self.root = Path(run_dir)
        self._binding_cache = {}
        self._cached = None
        self._artifact_paths = []
        self.rows = []

    def signature(self):
        root = self.root
        paths = [root, root/'.parallel', root/'sciel_events.jsonl',
                 root/'checkpoint.json', root/'.parallel/current.json', *self._artifact_paths]
        try:
            pointer, _ = read_json(root, root/'.parallel/current.json', 65536)
            wave = pointer.get('wave_id')
            if isinstance(wave,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}',wave):
                directory = root/'.parallel'/('wave-'+wave)
                paths += [directory, directory/'transaction.json']
                manifest, _ = read_json(root, directory/'transaction.json', 65536)
                for key, suffix in (('baseline',r'\.baseline\.json'),('journal',r'\.journal\.jsonl')):
                    name = manifest.get(key)
                    if isinstance(name,str) and re.fullmatch(r'[a-f0-9]{32}'+suffix,name):
                        paths.append(directory/name)
        except (OSError,ValueError,TypeError,RecursionError):
            pass
        return tuple((str(path),file_signature(path)) for path in paths)

    def project(self, published, committed_cells, checkpoint=None):
        signature = self.signature()
        # The selected lineage can change on checkpoint restore, even when the
        # last row belongs to the same journal. It is part of the cache binding.
        lineage = [(row.get('run_id'),row.get('segment_id'),row.get('event_seq'))
                   for row in published if row.get('event') in ('run_start','checkpoint_restore')]
        identity = digest([lineage,[(c['id'],c.get('detail_version')) for c in committed_cells]])
        if self._cached and self._cached[:2] == (signature,identity):
            return self._cached[2]
        pending, _, warnings = pending_wave(self.root,published,self._binding_cache,include_calls=False)
        # The dashboard list is a bounded window, not the authority for older
        # cell IDs. A resumed/rotated journal may retain them only in checkpoint.
        committed = _cells_view(checkpoint or {},published)
        committed.update((cell['id'],cell) for cell in committed_cells)
        events = _events(pending)
        scoped = _cell_events(events)
        owners = {}
        for row in events:
            if row.get('action_id') and row.get('cell_id'):
                owners.setdefault(row['action_id'],set()).add(row['cell_id'])
        reader = _DetailReader(self.root)
        cells, artifacts, artifact_signatures, allowed_proposals = [], [], {}, set()
        for ident, rows in list(scoped.items())[-LIMIT:]:
            if ident not in committed:
                created = next((row for row in rows if row.get('phase')=='cell_created'),None)
                if created is None:
                    continue
                try:
                    revision_id = created.get('cell_revision_id')
                    if not isinstance(revision_id,str) or not HASH.fullmatch(revision_id):
                        raise ValueError('Invalid pending cell revision')
                    paths=[self.root/'research_tools/cells/genesis'/(ident+'.json'),
                           self.root/'research_tools/cells/revisions'/(revision_id+'.json')]
                    artifact_signatures.update((path,file_signature(path)) for path in paths)
                    genesis = reader('cells/genesis',ident,256*1024)
                    revision = reader('cells/revisions',revision_id,256*1024)
                    if (genesis.get('schema')!='sciel-research-cell/1'
                            or not isinstance(genesis.get('question'),str)
                            or genesis['question']!=created.get('question')
                            or str(genesis.get('origin_island'))!=str(created.get('origin_island_id',created.get('island_id')))
                            or revision.get('schema')!='sciel-research-cell-revision/1'
                            or revision.get('cell_id')!=ident or revision.get('ordinal')!=1
                            or revision.get('previous_revision') is not None):
                        raise ValueError('Pending cell genesis differs from its journal binding')
                except (OSError,ValueError,TypeError,KeyError):
                    warnings.append('A pending research cell is unavailable or failed verification.')
                    continue
                artifacts += paths
                cell = dict(id=ident,question=genesis['question'],origin_island_id=genesis['origin_island'],
                    affinities=[created.get('island_id')],created_at=created.get('timestamp'),
                    head_revision=None,stage='propose',scheduled=False,genesis=genesis)
            else:
                cell = {key:committed[ident][key] for key in ('id','affinities','origin_island_id',
                    'stage','head_revision','question','created_at') if key in committed[ident]}
            decision = None
            for row in rows:
                action = row.get('action_id')
                if row.get('phase')=='research_decision':
                    proposal = row.get('proposal_id')
                    if (not isinstance(proposal,str) or not HASH.fullmatch(proposal)
                            or owners.get(action)!={ident}
                            or not any(r.get('phase')=='llm_result' and r.get('receipt_id')==proposal
                                and r.get('action_id')==action and r.get('cell_id')==ident for r in rows)):
                        continue
                    fields = ('action_id','action','proposal_id','question','experiment','decision_if_supported',
                        'decision_if_refuted','next_decision','requested_limits','timestamp','event_seq','segment_id')
                    compact = _compact(row)
                    decision = {key:compact[key] for key in fields if key in compact}
                    decision.update(status='planned',committed=False,evidence_scope='authenticated_pending_wave')
                    allowed_proposals.add(proposal)
                elif decision and action==decision['action_id']:
                    if row.get('phase')=='invocation_started':
                        decision['status']='awaiting_execution_receipt'
                    elif row.get('phase')=='invocation_result':
                        decision['status']='result_recorded_uncommitted'
                    elif row.get('phase')=='episode_finished' or (row.get('phase')=='research_step'
                            and row.get('proposal_id')==decision['proposal_id']):
                        decision['status']='awaiting_wave_commit'
            cell.update(publication='pending',committed=ident in committed,
                pending_decision=decision,active_decision=decision if decision and decision['status']!='awaiting_wave_commit' else None,
                current_question=_obj(decision).get('question'),state_source='authenticated_pending_wave',
                last_activity_at=rows[-1].get('timestamp'),pending_status='uncommitted')
            cell['detail_version']=digest(cell)
            cells.append(cell)
        if len(scoped)>LIMIT:
            warnings.append('Pending research display is limited to the latest 200 cells.')
        # Never serve a mixed snapshot across publication/rollback/replacement.
        if signature!=self.signature() or any(file_signature(path)!=saved for path,saved in artifact_signatures.items()):
            self.rows=[];self._cached=None
            return self._result([],['Pending wave changed during observation; awaiting a stable read.'])
        self.rows=[r for r in events if r.get('phase')=='llm_result' and r.get('receipt_id') in allowed_proposals]
        self._artifact_paths=artifacts
        result=self._result(cells,warnings)
        self._cached=(self.signature(),identity,result)
        return result

    @staticmethod
    def _result(cells,warnings):
        result=dict(cells=cells,warnings=warnings,
            scope='Authenticated active-wave metadata only; uncommitted. This does not establish running CPU, measured usage, adoption or candidate benefit.')
        result['version']=digest(result)
        return result

    @staticmethod
    def detail(overlay, committed=None):
        """Keep committed history intact; a first cell has only a pending genesis."""
        body = dict(committed or dict(id=overlay['id'],kind='cell',verified=True,
            genesis=overlay.get('genesis'),head_revision=None,revision_history=[],history_truncated=False,
            summary={},related={},related_coverage={},research_state=None))
        body.update(publication='pending',pending_decision=overlay.get('pending_decision'),
            active_decision=overlay.get('active_decision'),
            current_question=overlay.get('current_question') or body.get('current_question'),
            question_scope='Authenticated pending wave; uncommitted',
            detail_scope='Pending question metadata is separate from committed cell history and usage. It is not proof that computation is currently running.')
        return body
