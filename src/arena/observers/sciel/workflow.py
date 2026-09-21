"""Paginated saved workflow activity and read-only detail inspection."""
from __future__ import annotations

from datetime import datetime
import difflib
import hashlib
import json
import math
import re

from .llm_calls import collect_calls, detail as call_detail
from .methods import registered_artifacts
from .research_tools import artifact_detail, tool_detail
from .workflow_pending import file_signature, pending_wave, read_bytes, read_json
from .workflow_records import (ACTORS, MAX_DETAIL_BYTES, MAX_PAGE, MAX_WAVE_BYTES,
    MAX_WAVE_CALLS, SCHEMA, _SECRET, call_items, clean, digest, durable_items,
    human, item, journal_item, number, obj, public, refs, stamp, text)


class WorkflowView:
    def __init__(self,store,run_id):
        self.store=store;self.run_id=run_id;self.path=store._path(run_id);self.rows=[];self.calls=[]
        self.methods=store._methods(self.path) if self.path.name=='journal.jsonl' else None
        self._binding_cache={}
        self._base_cache=None

    def signature(self):
        if self.methods is not None:
            return self.methods.signature()
        root=self.path.parent
        paths=[self.path,root/'checkpoint.json',root/'artifacts/llm_calls.jsonl',root/'.parallel/current.json']
        try:
            pointer,_=read_json(root,root/'.parallel/current.json',65536)
            wave=pointer.get('wave_id')
            if isinstance(wave,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}',wave):
                directory=root/'.parallel'/('wave-'+wave)
                paths.extend((root,root/'.parallel',directory,directory/'transaction.json',directory/'calls'))
                manifest,_=read_json(root,directory/'transaction.json',65536)
                name=manifest.get('journal')
                if isinstance(name,str) and re.fullmatch(r'[a-f0-9]{32}\.journal\.jsonl',name):paths.append(directory/name)
                calls=directory/'calls'
                if calls.is_dir() and not calls.is_symlink():
                    for index,child in enumerate(sorted(calls.iterdir())):
                        if index>=MAX_WAVE_CALLS:break
                        paths.extend((child,child/'intent.json',child/'dispatched.json',child/'receipt.json'))
        except (OSError,ValueError,TypeError,RecursionError):pass
        return tuple((str(path),file_signature(path)) for path in paths)

    def entries(self):
        signature=self.signature()
        if self._base_cache is None or self._base_cache[0]!=signature:
            base,warnings=self.base_entries()
            if signature==self.signature():self._base_cache=(signature,base,warnings)
        else:
            _,base,warnings=self._base_cache
        entries=list(base);warnings=list(warnings)
        if self.methods is not None:
            identity_row=next((r for r in self.rows if r.get('kind')=='coordinator_identity'),{})
            data=obj(identity_row.get('data'))
            runtime=self.methods.runtime(obj(data.get('identity')),data.get('started_at'))
        else:
            published,_=self.store._journal(self.path)
            start=next((r for r in reversed(published) if r.get('event')=='run_start'),{})
            runtime=self.store._runtime(self.path,start)
        if runtime.get('verification')=='terminal_recorded':
            status=runtime['status'];finished=runtime.get('finished_at')
            entries.append(item('runtime-'+digest([runtime.get('runtime_id'),status,finished])[:32],'system','runtime_terminal',
                'Session '+status,'Recorded terminal runtime status',finished,status=status,timestamp_source='runtime',
                _kind='runtime',_runtime={key:runtime.get(key) for key in ('status','stage','started_at','finished_at','verification','error_type')}))
        return entries,warnings

    def base_entries(self):
        if self.methods is not None:
            return self.method_entries()
        published,warnings=self.store._journal(self.path)
        pending,durable,more=pending_wave(self.path.parent,published,self._binding_cache);warnings+=more
        self.rows=published+pending
        entries=[journal_item(row,index,index>=len(published)) for index,row in enumerate(self.rows)]
        self.calls=collect_calls(self.path.parent,self.rows)
        pending_keys={(r.get('segment_id'),r.get('event_seq')) for r in pending}
        for call in self.calls:
            request=call.get('_request',{})
            is_pending=((request.get('segment_id'),request.get('journal_event_seq',request.get('event_seq'))) in pending_keys)
            entries.extend(call_items(call,is_pending))
        for call in durable:
            entries.extend(durable_items(call,self.calls))
        return entries,warnings

    def method_entries(self):
        self.rows,warnings=self.methods.rows()
        projection=self.store._methods_projection(self.run_id,self.path).get('methods',{})
        proposals={p['id']:p for p in projection.get('proposals',[]) if isinstance(p,dict) and p.get('id')}
        receipts={r['id']:r for r in projection.get('receipts',[]) if isinstance(r,dict) and r.get('id')}
        entries=[]
        for row in self.rows:
            data=obj(row.get('data'));kind=data.get('kind') if row.get('kind')=='artifact_registered' else row.get('kind')
            actor='tool' if kind in ('method_registered','method_status') else 'task' if kind in ('experiment','experiment_plan','solution','proposal_context') else 'system'
            title={'proposal_receipt':'Proposal receipt recorded','proposal_context':'Proposal context prepared','method_registered':'Tool registered',
                'lab_created':'Research lab created','lab_revised':'Research lab revised','call_receipt':'Invocation receipt recorded'}.get(kind,human(kind))
            status=None;cost=None
            if kind=='proposal_receipt' and data.get('id') in proposals:
                saved=proposals[data['id']];status=saved.get('status');cost=number(saved.get('cost'))
                if saved.get('dispatch_status')=='not_dispatched':
                    actor='system';title='Proposal request not sent';status='not_dispatched'
                else:
                    actor='model';title='Proposal '+str(status) if status in ('invalid','refused','failed') else 'Model proposal recorded'
            elif kind=='call_receipt' and data.get('id') in receipts:
                saved=receipts[data['id']];status=saved.get('status')
                category=saved.get('category');cost=number(obj(saved.get('actual')).get('dollars'))
                if saved.get('dispatch_status')=='not_dispatched':
                    actor='system';title='Request not dispatched';status='not_dispatched'
                elif category=='generation':actor='model';title='Model call receipt recorded'
                elif category in ('execution','replication'):actor='tool';title='Tool invocation receipt recorded'
                elif category=='measurement':actor='task';title='Measurement receipt recorded'
            summary=' · '.join(str(data[k])[:96] for k in ('lab_id','status','id') if type(data.get(k)) in (str,int))
            entries.append(item('method-'+row['id'],actor,str(kind),title,summary,row.get('at'),refs=refs(data),
                timestamp_source='registry',status=status,cost=cost,_kind='method',_row=row))
        return entries,warnings

    def page(self,*,limit=60,before=None,actor='all',query=''):
        if type(limit) is not int or not 1<=limit<=MAX_PAGE or actor not in ACTORS|{'all'}:
            raise ValueError('Invalid workflow page')
        entries,warnings=self.entries()
        # Sorting by parsed UTC makes equivalent offsets chronological; file order breaks ties.
        entries.sort(key=lambda e: datetime.fromisoformat(e['timestamp'].replace('Z','+00:00')).timestamp() if e['timestamp'] else -math.inf)
        if actor!='all':entries=[e for e in entries if e['actor']==actor]
        if query:
            needle=str(query).lower()[:256]
            entries=[e for e in entries if needle in ' '.join(str(e.get(k) or '') for k in ('title','summary','status','model','refs','iteration')).lower()]
        total=len(entries)
        if before:
            index=next((i for i,e in enumerate(entries) if e['id']==before),None)
            if index is None:
                raise KeyError('Workflow cursor is unavailable')
            entries=entries[:index]
        page=entries[-limit:];has_more=len(entries)>limit
        result=dict(schema=SCHEMA,items=[public(e) for e in page],total=total,has_more=has_more,
            next_before=page[0]['id'] if has_more else None,warnings=list(dict.fromkeys(warnings))[:20],
            note='Only saved activity. Missing timestamps and text are not reconstructed; pending wave records are not committed results.')
        result['version']=digest(result)
        return clean(result)

    def detail(self,ident):
        entries,warnings=self.entries()
        entry=next((e for e in entries if e['id']==ident),None)
        if entry is None:raise KeyError('Unknown workflow event')
        sections=[];detail_bytes=0;seen_sections=set()
        def add(label,value,fmt='json',note=None):
            nonlocal detail_bytes
            if value is None:return
            value=clean(value)
            section=dict(label=label,format=fmt,text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),**({'note':note} if note else {}))
            encoded=section['text'].encode('utf-8',errors='replace')
            section_key=(label,fmt,hashlib.sha256(encoded).hexdigest(),note)
            if section_key in seen_sections:return
            seen_sections.add(section_key)
            remaining=max(0,MAX_DETAIL_BYTES-detail_bytes)
            if len(encoded)>remaining:
                section['text']=encoded[:remaining].decode('utf-8',errors='ignore')
                section['note']=((note+' ') if note else '')+'Display truncated at the 16 MiB detail limit; saved evidence is unchanged.'
                warnings.append('Some detail text exceeds the 16 MiB inspector limit and is truncated.')
                section['truncated']=True
            detail_bytes+=len(section['text'].encode('utf-8',errors='replace'))
            sections.append(section)
        kind=entry['_kind']
        if kind=='call':
            saved=call_detail(self.path.parent,entry['_call'])
            for side,label in (('prompt','Prompt'),('response','Model response')):
                record=saved[side]
                add(label,record.get('text'),'text',record.get('note'))
                if not record.get('available'):add(label,None if not record.get('note') else record['note'],'text')
            add('Call metadata',{k:v for k,v in saved.items() if k not in ('prompt','response')})
        elif kind=='durable':
            saved=entry['_durable'];request=obj(saved['intent'].get('request'));receipt=saved['receipt'];value=obj(receipt.get('value'))
            add('Prompt',request.get('prompt'),'text');add('Model response',value.get('text'),'text')
            add('Evaluated source',request.get('source'),'code')
            parent=request.get('parent_source',request.get('parent_code'))
            source=request.get('source')
            if isinstance(parent,str) and isinstance(source,str):
                add('Code diff',''.join(difflib.unified_diff(parent.splitlines(True),source.splitlines(True),fromfile='saved parent',tofile='evaluated source',n=3)),'diff')
            add('Request',{k:v for k,v in request.items() if k not in ('prompt','source')})
            add('Receipt',{**receipt,'value':{k:v for k,v in value.items() if k!='text'}})
        elif kind=='runtime':add('Session status',entry['_runtime'])
        elif kind=='method':
            row=entry['_row'];data=obj(row.get('data'))
            try:
                if row['kind']=='artifact_registered':
                    artifact_kind=data.get('kind');artifact_id=data.get('id')
                    if artifact_kind=='proposal_receipt':
                        saved=self.methods.proposal_detail(artifact_id)
                        add('Prompt',saved.get('request'),'text' if isinstance(saved.get('request'),str) else 'json')
                        add('Model response',saved.get('response'),'text')
                        add('Proposal receipt',saved.get('receipt'));add('Research context',saved.get('context'));add('Call receipt',saved.get('call_receipt'))
                    else:add(human(artifact_kind),self.methods.artifact(artifact_kind,artifact_id,registered_artifacts(self.rows)))
                elif row['kind']=='method_registered':
                    saved=self.methods.method_detail(data.get('id'))
                    for name,source in obj(saved.get('files')).items():add(str(name),source,'code')
                    add('Diff',saved.get('diff'),'diff');add('Manifest',saved.get('manifest'))
                elif row['kind'] in ('lab_created','lab_revised'):
                    add('Lab revision',self.methods._object('revisions',data.get('revision_id')))
            except (OSError,ValueError,KeyError):warnings.append('Saved method detail is unavailable or failed verification.')
            add('Registry event',row)
        else:
            row=entry['_row']
            for key,label,fmt in (('prompt','Prompt','text'),('response','Model response','text'),('code','Code','code'),('child_code','Candidate source','code')):
                add(label,row.get(key),fmt)
            excerpt=obj(row.get('evidence')).get('change_excerpt')
            add('Recorded change',excerpt,'diff')
            if row.get('event')=='research_tool':
                try:
                    if row.get('receipt_id') and row.get('phase') in ('llm_result','invocation_result'):
                        add('Tool receipt',artifact_detail(self.path.parent,row['receipt_id'],self.rows))
                    if row.get('tool_id') and row.get('phase') in ('registered','published'):
                        saved=tool_detail(self.path.parent,row['tool_id'],self.rows)
                        for name,source in obj(saved.get('files')).items():add(str(name),source,'code')
                        for parent in saved.get('parents',[]):add('Tool diff',parent.get('diff'),'diff')
                except (OSError,ValueError,KeyError):warnings.append('Saved tool detail is unavailable or failed verification.')
            add('Recorded event',{k:v for k,v in row.items() if k not in ('prompt','response','code','child_code')})
        program=entry['refs'].get('program_id')
        if not program and entry['refs'].get('experiment_id'):
            experiment=entry['refs']['experiment_id']
            program=next((refs(r).get('program_id') for r in reversed(self.rows)
                if refs(r).get('experiment_id')==experiment and refs(r).get('program_id')),None)
        if entry['refs'].get('experiment_id') and self.methods is None:
            related=next((obj(r.get('evidence')).get('change_excerpt') for r in reversed(self.rows)
                if refs(r).get('experiment_id')==entry['refs']['experiment_id'] and isinstance(obj(r.get('evidence')).get('change_excerpt'),str)),None)
            if related is not None:add('Recorded change',related,'diff', 'Saved research excerpt; may omit portions of the full source diff.')
        if program and self.methods is None:
            try:
                saved=self.store.detail(self.run_id,program)
                add('Candidate source',saved.get('code'),'code');add('Code diff',saved.get('diff'),'diff')
            except (OSError,ValueError,KeyError):
                checkpoint,_,_=self.store._checkpoint(self.path,self.rows)
                sources=self.store._sources(checkpoint,self.rows);source=obj(sources.get(program));parent=obj(sources.get(source.get('parent_id')))
                add('Candidate source',source.get('code'),'code')
                if isinstance(source.get('code'),str) and isinstance(parent.get('code'),str):
                    add('Code diff',''.join(difflib.unified_diff(parent['code'].splitlines(True),source['code'].splitlines(True),
                        fromfile=str(source.get('parent_id')),tofile=program,n=3)),'diff')
        return clean(dict(schema=SCHEMA,item=public(entry),sections=sections,warnings=list(dict.fromkeys(warnings))[:20]))
