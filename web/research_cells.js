// Read-only research-cell workspace. Saved code and model text are never HTML.
const sessions = new WeakMap();
const array = value => Array.isArray(value) ? value : [];
const object = value => value && typeof value === 'object' && !Array.isArray(value) ? value : {};
const short = value => String(value ?? 'Not recorded').slice(0, 12);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const number = value => finite(value) ? String(value) : 'Not recorded';
const seconds = value => finite(value) ? value.toFixed(3) + ' s' : 'Unknown';
const money = value => finite(value) ? '$' + value.toFixed(6) : 'Unknown';
const stringify = value => typeof value === 'string' ? value : JSON.stringify(value ?? null, null, 2);
const stageLabels = {propose:'Question opened',research:'Research',independent_replay:'Independent replay',adopt_trial:'Recipient trial',adopted_for_trials:'Adopted for trials',use_again:'Later use',background_submitted:'Background submitted',background_deferred:'Background deferred'};
const label = value => stageLabels[value] || String(value || 'Not recorded').replaceAll('_', ' ');
const timestamp = value => {
  if (typeof value !== 'string') return 'Not recorded';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? 'Not recorded' : new Intl.DateTimeFormat('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false,timeZoneName:'short'}).format(date);
};
function timeNode(value) {const node=el('time','',timestamp(value));if(typeof value==='string'){node.title=value;node.dateTime=value;}return node;}
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function button(text, action, className='rc-link') {
  const node = el('button', className, text); node.type = 'button';
  node.addEventListener('click', action); return node;
}
function note(text) { return el('p', 'rc-note', text); }
function empty(title, text) { const node = el('div', 'rc-empty'); node.append(el('h3', '', title), note(text)); return node; }
function raw(text) { const node = el('pre', 'rc-raw', stringify(text)); node.tabIndex = 0; return node; }
function modelText(text) { const node=raw(text);node.classList.add('rc-model-text');return node; }
function pairs(values) {
  const node = el('dl', 'rc-facts');
  for (const [key, value] of values) { const row = el('div'),dd=el('dd');if(value instanceof Node)dd.append(value);else dd.textContent=String(value??'Not recorded');row.append(el('dt', '', key),dd);node.append(row); }
  return node;
}
function panel(key, title, content, open=false) {
  const node = el('details', 'rc-panel'); node.dataset.rcKey = key; node.open = open;
  node.append(el('summary', '', title), content); return node;
}
function outcome(row) {
  if (row.dispatch_status === 'not_dispatched') return 'Not dispatched';
  if (row.tool_result_status) return ({success:'Check completed',tool_error:'Tool error',invalid_output:'Invalid output',host_failed:'Execution failed',unknown:'Outcome unknown'}[row.tool_result_status] || label(row.tool_result_status));
  return ({pending:'Pending',unknown:'Outcome unknown',failed:'Execution failed',ok:'Execution returned',completed:'Execution completed',running:'Running',queued:'Queued'}[row.status] || label(row.status));
}
function activity(row) {
  if(row.publication==='pending')return 'Awaiting wave commit';
  return row.scheduled === true ? 'Scheduled' : ({activity_recorded:'Recorded activity',no_activity_recorded:'No activity recorded'}[row.activity_status] || 'Not scheduled');
}
function scope(row) { return row.evidence_scope ? label(row.evidence_scope) : (row.state_source === 'checkpoint' ? 'Checkpoint state' : row.state_source === 'selected_journal' ? 'Selected journal state' : 'Recorded evidence'); }
function program(view, id) { return id ? button(id, () => view.options.onProgram?.(id), 'rc-link rc-program') : el('span', 'rc-muted', 'No admitted program'); }
function restore(container, update) {
  const saved = new Map();
  for (const node of container.querySelectorAll('[data-rc-key]')) saved.set(node.dataset.rcKey, {open:node.open,top:node.scrollTop,left:node.scrollLeft});
  const active = document.activeElement;
  const focusKey = container.contains(active) ? active.closest('[data-rc-key]')?.dataset.rcKey : null;
  const top=container.scrollTop, left=container.scrollLeft;
  update();
  for (const node of container.querySelectorAll('[data-rc-key]')) {
    const old=saved.get(node.dataset.rcKey); if (!old) continue;
    if ('open' in node) node.open=old.open; node.scrollTop=old.top; node.scrollLeft=old.left;
    if (focusKey===node.dataset.rcKey) (node.matches('pre')?node:node.querySelector('summary'))?.focus({preventScroll:true});
  }
  container.scrollTop=top; container.scrollLeft=left;
}
function endpoint(view, kind, id) {
  const routes={cell:'research-cells',tool:'research-tools',artifact:'research-tool-artifacts',job:'research-tool-jobs'};
  return '/api/runs/'+encodeURIComponent(view.options.runId)+'/'+routes[kind]+'/'+encodeURIComponent(id);
}
async function fetchBody(view, kind, id, version='') {
  const key=kind+':'+id+':'+version;
  if (view.cache.has(key)) return view.cache.get(key);
  let promise=view.pending.get(key);
  if (!promise) {
    promise=Promise.resolve().then(()=>view.options.fetchJSON(endpoint(view,kind,id)));
    view.pending.set(key,promise);
  }
  try {
    const body=await promise;
    if (sessions.get(view.root)!==view) return null;
    if (body?.verified!==true) throw new Error('Saved content is unavailable or failed verification.');
    view.cache.set(key,body);
    while (view.cache.size>32) view.cache.delete(view.cache.keys().next().value);
    return body;
  } finally { if (view.pending.get(key)===promise) view.pending.delete(key); }
}
function inputSources(view, inputs) {
  const targets=inputs?.research_targets;
  if (!targets) return null;
  const node=el('div','rc-inputs');
  for (const [name, value] of [['Input source',targets.selected],['Available best reference',targets.population_best]]) {
    const line=el('div','rc-input-line'); line.append(el('span','rc-muted',name+' · '));
    if (value?.program_id) line.append(program(view,value.program_id));
    else line.append(el('span','',value?.kind==='failed_candidate'?'Failed, unadmitted source':'Not recorded'));
    if (value?.source_sha256) line.append(el('code','rc-id',' · '+short(value.source_sha256)));
    node.append(line);
    const saved=value?.saved_evaluation;
    node.append(note(saved?.status==='available'?'Saved evaluator output available · '+short(saved.reference?.sha256)+' · '+(saved.reference?.bytes??'Unknown')+' bytes':saved?.status==='unavailable'?'Saved evaluator output unavailable · '+(saved.reason||'Reason not recorded'):'Saved evaluator output was not captured in this input contract.'));
  }
  node.append(note('Available references do not establish which source was used.')); return node;
}
function artifactContent(view, body, key) {
  const node=el('div','rc-artifact'); node.append(el('p','rc-verified','Verified saved content'));
  if (body.kind==='proposal') {
    const payload=body.payload||{};
    const response=payload.response;
    const text=typeof response?.text==='string'?response.text:typeof response==='string'?response:null;
    node.append(panel(key+':prompt','Model request',typeof payload.prompt==='string'?modelText(payload.prompt):note('Request text not recorded.'),true),panel(key+':response','Model response',text!==null?modelText(text):note('Response text not recorded.'),true));
    if(response&&typeof response==='object'&&!Array.isArray(response)){
      const metadata=Object.fromEntries(Object.entries(response).filter(([key])=>key!=='text'));
      node.append(panel(key+':response-metadata','Response metadata',raw(metadata)));
    }
    if(typeof payload.prompt!=='string')node.append(panel(key+':request-exact','Exact saved request',raw(payload.prompt)));
    node.append(panel(key+':response-exact','Exact saved response',raw(response)));
  } else if(body.kind==='candidate_evaluation') {
    const payload=body.payload||{},evaluation=payload.evaluation||{},provenance=payload.provenance||{};
    node.append(pairs([['Canonical outcome',label(evaluation.status)],['Controller score',number(evaluation.score)],['Evaluation ID',evaluation.evaluation_id],['Evaluator wall time',seconds(evaluation.timing_seconds)],['Discovery tool CPU',seconds(provenance.discovery_resources?.cpu_seconds)],['Discovery model cost · known',money(provenance.known_llm_cost)]]));
    node.append(note(evaluation.scope||'One ordinary evaluation does not establish method benefit or transfer.'),panel(key+':evaluation','Canonical evaluator result',raw(evaluation),true),panel(key+':source','Exact submitted candidate source',raw(payload.source)),panel(key+':provenance','Saved tool result and discovery accounting',raw(provenance)));
  } else if (body.kind==='invocation' || body.kind==='job') {
    const payload=body.payload||{},receipt=body.kind==='job'?body.receipt:payload.receipt;
    const inputs=body.kind==='job'?body.request?.inputs:payload.inputs;
    const sources=inputSources(view,inputs); if(sources)node.append(sources);
    if (receipt) {
      const result=receipt.output||{};
      node.append(pairs([['Execution',label(receipt.status)],['Tool result',label(result.status)],['Measured CPU / requested',seconds(receipt.resources?.cpu_seconds)+' / '+seconds(receipt.limits?.cpu_seconds??body.request?.limits?.cpu_seconds)],['Measured wall / requested',seconds(receipt.resources?.wall_seconds)+' / '+seconds(receipt.limits?.wall_seconds??body.request?.limits?.wall_seconds)]]));
      if (result.error || receipt.stderr) node.append(panel(key+':error','Recorded error',raw(result.error||receipt.stderr),true));
      node.append(panel(key+':observations','Observations',raw(result.observations ?? 'No observations recorded'),true));
      if (result.diagnostics) node.append(panel(key+':diagnostics','Diagnostics',raw(result.diagnostics)));
      node.append(panel(key+':receipt','Full execution receipt',raw(receipt)));
    } else node.append(note('No terminal execution receipt is recorded. Pending work is not a measurement.'));
    node.append(panel(key+':inputs','Exact saved inputs',raw(inputs)));
    if (body.kind==='job') node.append(panel(key+':job','Job request and latest saved status',raw({request:body.request,snapshot:body.snapshot})));
  } else {
    node.append(panel(key+':source','tool.py · exact source',raw(body.files?.['tool.py'] ?? 'Source not recorded'),true));
    for (const parent of array(body.parents)) node.append(panel(key+':diff:'+parent.id,'Diff from '+short(parent.id),parent.verified?raw(parent.diff||'No source changes'):note('Parent source unavailable or failed verification.')));
    node.append(panel(key+':manifest','Manifest, dependencies and replay policy',raw(body.manifest)));
  }
  for (const pre of node.querySelectorAll('pre')) pre.dataset.rcKey=pre.parentElement.dataset.rcKey+':text';
  return node;
}
function lazyRow(view, pane, container, key, title, subtitle, kind, id, version='',stamp=null) {
  let node=pane.rows.get(key);
  if (!node) {
    node=el('details','rc-record'); node.dataset.rcKey=key;
    const summary=el('summary'),body=el('div','rc-record-body');node.append(summary,body);
    node._summary=summary;node._body=body;pane.rows.set(key,node);
    node.addEventListener('toggle',()=>{if(node.open)loadLazy(view,node);});
  }
  node._summary.replaceChildren(el('span','rc-row-title',title),el('span','rc-row-meta',subtitle));node._summary.title=stamp||'';
  node.dataset.kind=kind;node.dataset.id=id;
  const token=kind+':'+id+':'+version;
  if(node._spec?.token!==token)node._spec={kind,id,version,key,pane,token};
  if (node.open) loadLazy(view,node);
  return node;
}
async function loadLazy(view,node) {
  const spec=node._spec,token=spec.kind+':'+spec.id+':'+spec.version;
  if (node._loaded===token || node._pending===token) return;
  node._pending=token;node._body.setAttribute('aria-busy','true');
  if (!node._loaded) node._body.replaceChildren(note('Loading and verifying saved content…'));
  try {
    const body=await fetchBody(view,spec.kind,spec.id,spec.version);
    if (!body || sessions.get(view.root)!==view || node._spec!==spec) return;
    restore(node._body,()=>node._body.replaceChildren(artifactContent(view,body,spec.key)));
    node._loaded=token;
  } catch(error) {
    if(sessions.get(view.root)!==view||node._spec!==spec)return;
    if (!node._loaded) node._body.replaceChildren(empty('Saved content unavailable',error?.message||'Close and reopen to retry.'));
    else node._body.prepend(note('Refresh failed; showing the previous verified snapshot. Close and reopen to retry.'));
  } finally {if(node._pending===token){node._pending=null;node._body.removeAttribute('aria-busy');}}
}
function section(pane,key,title,count) {
  let node=pane.sections.get(key);
  if(!node){node=el('section','rc-section');node.dataset.section=key;node.append(el('h3'),el('div','rc-section-rows'));pane.sections.set(key,node);}
  node.firstChild.textContent=title+(finite(count)?' · '+count:'');if(node.parentElement!==pane.sectionsRoot)pane.sectionsRoot.append(node);
  return node.lastChild;
}
function reconcile(container,nodes) { const kept=new Set(nodes); for(const node of [...container.children])if(!kept.has(node))node.remove();nodes.forEach((node,index)=>{if(container.children[index]!==node)container.insertBefore(node,container.children[index]||null);}); }
function reconcileEvidence(container,nodes,fallback,coverage) {
  const unavailable=(coverage?.verification_failed||0)>0,omitted=(coverage?.omitted||0)>0;
  const content=nodes.length?[...nodes]:[note(unavailable?'No verified records available in this view.':omitted?'No retained records available in this view.':fallback)];
  if(unavailable)content.push(note(coverage.verification_failed+' records unavailable or failed verification; saved bodies are withheld.'));
  if(omitted)content.push(note(coverage.omitted+' older records omitted by the read bound.'));
  reconcile(container,content);
}
function related(view,row,body) {
  if(body.related)return body.related;
  const source=view.data,cell=row.id,toolIDs=new Set([...array(row.tool_ids),...array(body.revision_history).flatMap(r=>array(r.tool_ids))]);
  return {versions:array(source.versions).filter(v=>v.cell_id===cell||toolIDs.has(v.id)),invocations:array(source.invocations).filter(v=>v.cell_id===cell),jobs:array(source.jobs?.items).filter(v=>(v.cell_id||v.owner?.cell_id)===cell),llm_calls:array(source.llm_calls).filter(v=>v.cell_id===cell),child_links:array(source.child_links).filter(v=>v.cell_id===cell),events:array(source.events).filter(v=>v.cell_id===cell),lifecycle_events:array(source.lifecycle?.events).filter(v=>v.cell_id===cell),followups:[]};
}
function staticRecord(pane,key,title,subtitle,render) {
  let node=pane.rows.get(key);
  if(!node){node=el('details','rc-record');node.dataset.rcKey=key;node.append(el('summary'),el('div','rc-record-body'));pane.rows.set(key,node);}
  node.firstChild.replaceChildren(el('span','rc-row-title',title),el('span','rc-row-meta',subtitle));
  const signature=render.signature;
  if(node._signature!==signature){restore(node.lastChild,()=>node.lastChild.replaceChildren(render()));node._signature=signature;}
  return node;
}
function renderRecord(pane,key,title,subtitle,value,extra) {
  const render=()=>{const node=el('div');if(extra)node.append(extra());node.append(panel(key+':raw','Recorded evidence',raw(value)));return node;};render.signature=JSON.stringify(value);
  const node=staticRecord(pane,key,title,subtitle,render);node.firstChild.title=value?.timestamp||'';return node;
}
function currentDecision(row,body) {return body&&Object.hasOwn(body,'active_decision')?(body.active_decision||body.pending_decision):(row.active_decision||row.pending_decision);}
function currentQuestion(row,body) {
  return currentDecision(row,body)?.question||body?.research_state?.question||body?.current_question||row.research_state?.question||row.current_question||'No experiment question recorded yet';
}
function renderResearch(view,pane,row,body,data) {
  const committed=body.research_state||row.research_state,active=currentDecision(row,body);
  const state=active?{...committed,...active,current_experiment:active.experiment}:committed,root=pane.research;
  root.replaceChildren();
  if(active){const pending=section(pane,'pending','Pending decision');reconcile(pending,active.proposal_id?[lazyRow(view,pane,pending,'pending-proposal:'+active.proposal_id,'Model request & response',timestamp(active.timestamp)+' · uncommitted decision','artifact',active.proposal_id)]:[note('Exact proposal reference not recorded.')]);}
  else if(pane.sections.has('pending')){pane.sections.get('pending').remove();pane.sections.delete('pending');}
  if(!state){root.append(note(body.current_question?'The latest verified experiment question is shown above. A structured research plan was not recorded in this historical run.':'The cell has been scheduled. Its concrete experiment question will appear after a proposal is recorded.'));return;}
  const status=el('div','rc-research-status');status.append(el('span','rc-status',label(state.status)),el('span','rc-muted',active?'Uncommitted model decision':'Recorded research plan'));
  const experiment=el('div','rc-current-experiment');experiment.append(el('h3','','Current experiment'),el('p','',state.current_experiment||'Not recorded'));
  const decisions=el('div','rc-decisions');
  for(const [title,value] of [['If supported',state.decision_if_supported],['If refuted',state.decision_if_refuted]]){const node=el('div');node.append(el('h3','',title),el('p','',value||'Not recorded'));decisions.append(node);}
  const next=el('div','rc-next-decision');next.append(el('h3','','Next decision'),el('p','',state.next_decision||'Not recorded'));
  root.append(status);
  const terminal=!active&&body.terminal_decision?.verified===true?body.terminal_decision:null;
  if(terminal){
    const interpretation=el('div','rc-next-decision rc-terminal');
    interpretation.append(el('h3','','Model interpretation · '+label(terminal.conclusion)),el('p','rc-model-text',terminal.interpretation||'No explanation recorded.'),note('Saved planner interpretation. Tool execution status and canonical candidate validity are separate.'));
    if(Object.values(terminal.omitted_chars||{}).some(value=>value>0))interpretation.append(note('Excerpt shown. The complete statement is in the saved model response.'));
    root.append(interpretation);
    const source=section(pane,'terminal-decision','Interpretation source');
    reconcile(source,[lazyRow(view,pane,source,'terminal-proposal:'+terminal.proposal_id,'Saved terminal request & response',short(terminal.proposal_id),'artifact',terminal.proposal_id)]);
  }else if(pane.sections.has('terminal-decision')){pane.sections.get('terminal-decision').remove();pane.sections.delete('terminal-decision');}
  root.append(experiment,decisions,next);
  if(active)root.append(note('This is the model’s current plan. Completion and measured usage are not established until saved execution evidence arrives.'),pairs([['Requested CPU budget',seconds(active.requested_limits?.cpu_seconds)],['Requested wall budget',seconds(active.requested_limits?.wall_seconds)]]));
  if(!active&&!terminal&&state.conclusion)root.append(note('Planner conclusion: '+label(state.conclusion)+'. This is a recorded interpretation; evaluator and transfer evidence are shown separately.'));
  const usage=committed||{};
  root.append(pairs([['Scientific steps',number(usage.scientific_steps)],['Cell model cost · known',money(usage.known_llm_cost)],['Cell tool CPU',seconds(usage.resources?.cpu_seconds)],['Cell tool wall time',seconds(usage.resources?.wall_seconds)]]));
  const unknown=[];if(usage.unknown_llm_calls>0)unknown.push(usage.unknown_llm_calls+' model calls with unknown cost');if(usage.resources?.unknown_cpu_invocations>0)unknown.push(usage.resources.unknown_cpu_invocations+' executions with unknown CPU');
  root.append(note((usage.scope==='cell_cumulative'?'Usage is cumulative for committed cell work. ':'Committed usage scope: '+(usage.scope||'not recorded')+'. ')+(unknown.length?unknown.join(' · ')+'. ':'')+'CPU is measured separately from model charges; missing usage is not zero.'));
  if(state.pending_method_trial)root.append(note('Next transfer check: run method '+short(state.pending_method_trial.tool_id)+' on a source different from '+(state.pending_method_trial.source_program_id||short(state.pending_method_trial.source_sha256))+'. This check is pending; transfer benefit is not established.'));
  const steps=array(usage.steps),stepsRoot=section(pane,'steps','Research sequence',steps.length),nodes=[];
  for(const [index,step] of steps.entries()){
    const key='step:'+(step.action_id||'')+':'+(step.proposal_id||step.receipt_id||index);
    nodes.push(renderRecord(pane,key,label(step.action)+' · '+label(step.status),timestamp(step.observed_at||step.timestamp)+' · CPU '+seconds(step.resources?.cpu_seconds)+' / '+seconds(step.requested_limits?.cpu_seconds),step,()=>pairs([['Experiment',step.experiment],['Next decision',step.next_decision],['Tool version',step.tool_id?short(step.tool_id):'Not recorded']])));
    if(step.proposal_id)nodes.push(lazyRow(view,pane,stepsRoot,key+':proposal','Model request & response',short(step.proposal_id),'artifact',step.proposal_id));
    if(step.receipt_id)nodes.push(lazyRow(view,pane,stepsRoot,key+':receipt','Saved experiment input & result',short(step.receipt_id),'artifact',step.receipt_id));
    if(step.canonical_evaluation_id)nodes.push(lazyRow(view,pane,stepsRoot,key+':evaluation','Canonical evaluator record',label(step.status)+' · '+short(step.canonical_evaluation_id),'artifact',step.canonical_evaluation_id));
  }
  if(state.steps_omitted>0)nodes.push(note(state.steps_omitted+' earlier steps omitted from the retained sequence. Cumulative usage still includes them.'));
  reconcile(stepsRoot,nodes.length?nodes:[note('No completed scientific step recorded yet.')]);
}
function renderCellBody(view,pane,row,body) {
  const data=related(view,row,body);pane.body=body;pane.status.textContent='Verified cell history · '+scope(body.summary||row);
  pane.question.textContent=currentQuestion(row,body);
  if(body.publication==='pending')pane.status.textContent='Authenticated pending wave · uncommitted · '+(view.data.pending_cells?.run_status||'process status unknown');
  renderResearch(view,pane,row,body,data);renderList(view);
  const facts=[['Origin island',body.genesis?.origin_island??row.origin_island_id??'Not recorded'],['Island affinities',array(row.affinities).join(', ')||'Not recorded'],['Created',timeNode(row.created_at)],['Last activity',timeNode(row.last_activity_at)]];
  pane.facts.replaceChildren(pairs(facts));
  const revisions=array(body.revision_history),history=section(pane,'history','Recorded revisions',revisions.length);
  const historyNodes=revisions.map(revision=>renderRecord(pane,'revision:'+revision.id,'Revision '+revision.ordinal+' · '+label(revision.phase),revision.summary||short(revision.id),revision,()=>note('Immutable revision '+revision.id)));
  if(body.history_truncated)historyNodes.push(note('Older revisions omitted by the read bound. Earlier predecessor: '+(body.next_revision_id||'Not recorded')));
  reconcile(history,historyNodes.length?historyNodes:[note('No immutable revision is recorded yet.')]);

  const versions=array(data.versions),tools=section(pane,'tools','Tool versions',versions.length),toolNodes=[];
  for(const version of versions)toolNodes.push(lazyRow(view,pane,tools,'tool:'+version.id,version.name||'Tool '+short(version.id),label(version.status)+' · '+short(version.id)+' · '+(version.replay_policy?label(version.replay_policy):'Replay policy not recorded'),'tool',version.id));
  reconcileEvidence(tools,toolNodes,'No tool version recorded for this cell.',body.related_coverage?.versions);

  const invocations=array(data.invocations),executions=section(pane,'executions','Executions & results',invocations.length),executionNodes=[];
  for(const call of invocations){const key='invocation:'+(call.invocation_id||call.id||call.action_id);const title=label(call.stage)+' · '+outcome(call);const meta=timestamp(call.timestamp)+' · CPU '+seconds(call.resources?.cpu_seconds)+' / '+seconds(call.requested_limits?.cpu_seconds)+' · '+short(call.tool_id);executionNodes.push(call.receipt_id?lazyRow(view,pane,executions,key,title,meta,'artifact',call.receipt_id,'',call.timestamp):renderRecord(pane,key,title,meta,call));}
  reconcileEvidence(executions,executionNodes,'No execution receipt recorded.',body.related_coverage?.invocations);

  const jobs=array(data.jobs),background=section(pane,'jobs','Background jobs',jobs.length),jobNodes=[];
  for(const job of jobs){const id=job.id||job.job_id;const title=(job.cancel_requested?'Cancellation requested · ':'')+outcome(job);jobNodes.push(lazyRow(view,pane,background,'job:'+id,title,'Requested CPU '+seconds(job.requested?.cpu_seconds??job.requested_limits?.cpu_seconds)+' / wall '+seconds(job.requested?.wall_seconds??job.requested_limits?.wall_seconds)+' · measured CPU '+seconds(job.actual?.cpu_seconds??job.resources?.cpu_seconds),'job',id,JSON.stringify([job.status,job.phase,job.receipt_id,job.updated_at]),job.updated_at));}
  reconcileEvidence(background,jobNodes,'No background job recorded for this cell.',body.related_coverage?.jobs);

  const sharing=array(data.lifecycle_events),sharingRoot=section(pane,'sharing','Replay, adoption & later use',sharing.length);
  reconcile(sharingRoot,sharing.length?sharing.map((event,index)=>renderRecord(pane,'sharing:'+(event.receipt_id||event.event_seq||index)+':'+event.phase,label(event.phase)+' · '+short(event.tool_id),timestamp(event.timestamp),event,()=>note(event.phase==='replay_result'?(event.measurement_reproduced===true?'Recorded observations reproduced on the pinned input. This does not establish task benefit.':event.matched===true?'Independent execution passed its declared policy. Measurement reproduction and benefit are not established.':'Recorded replay did not pass its declared policy.'):'A recorded protocol transition; adoption or later execution does not establish benefit.'))):[note('No replay, adoption or later-use evidence recorded.')]);

  const calls=array(data.llm_calls),models=section(pane,'models','Model requests & responses',calls.length),modelNodes=[];
  for(const call of calls){const key='model:'+(call.id||call.action_id+':'+call.attempt);const title='Attempt '+(finite(call.attempt)?call.attempt+1:'not recorded')+' · '+label(call.status);const meta=(call.model||'Model not recorded')+' · '+timestamp(call.timestamp)+' · '+(finite(call.known_cost)?'$'+call.known_cost.toFixed(6):'Cost unknown');modelNodes.push(call.receipt_id?lazyRow(view,pane,models,key,title,meta,'artifact',call.receipt_id,'',call.timestamp):renderRecord(pane,key,title,meta,call));}
  reconcileEvidence(models,modelNodes,'No cell-planner model request recorded. Assigned replay or recipient trials may execute without a planner request.',body.related_coverage?.llm_calls);

  const followups=array(data.followups),outcomes=section(pane,'outcomes','Linked candidate outcomes',followups.length),outcomeNodes=[];
  for(const item of followups){const result=item.outcome||item;const id=item.sha256||item.followup_sha256||item.experiment_id;outcomeNodes.push(renderRecord(pane,'followup:'+id,item.experiment_id||'Recorded outcome',label(result.status||item.outcome_status)+' · iteration '+(item.iteration??'Not recorded'),item,()=>{const node=el('div');node.append(program(view,result.child_program_id??item.child_program_id),note('Chronological exposure only. Model use and causal benefit remain unknown.'));const evaluation=result.evaluation||item.canonical_evaluation;if(evaluation)node.append(pairs([['Canonical outcome',evaluation.ok===true?'Evaluation returned':evaluation.ok===false?'Evaluation failed':'Not recorded'],['Controller score',number(evaluation.score)],['Stage',label(evaluation.reached)]]));else node.append(pairs([['Generation',label(item.generation?.dispatch)],['Controller score',number(item.score)],['Recorded change',number(item.actual_delta)]]));if(item.score_scope)node.append(note(item.score_scope));if(result.failure||item.failure)node.append(raw(result.failure||item.failure));return node;}));}
  for(const link of array(data.child_links))outcomeNodes.push(renderRecord(pane,'program:'+(link.id||link.child_program_id),link.child_program_id||'Program link',label(link.link_kind),link,()=>{const node=el('div');node.append(program(view,link.child_program_id),note('Recorded association; this alone does not prove prompt delivery or causal benefit.'));return node;}));
  reconcileEvidence(outcomes,outcomeNodes,'No committed candidate followup recorded. Missing outcomes are not failed outcomes.',body.related_coverage?.followups);
  const events=array(data.events),activityRoot=section(pane,'activity','Activity log',events.length);
  reconcile(activityRoot,events.length?events.map((event,index)=>renderRecord(pane,'event:'+(event.segment_id||'')+':'+(event.event_seq??index),label(event.phase),timestamp(event.timestamp)+(event.iteration?' · G'+event.iteration:''),event)):[note('No event details retained in the selected journal window.')]);
  const origin=section(pane,'origin','Origin & evidence scope');reconcile(origin,[renderRecord(pane,'cell-genesis:'+row.id,'Verified cell origin and trigger',body.history_scope||'Recorded state and transitions',body.genesis)]);
  pane.coverage.textContent=coverageText(body.related_coverage||row.coverage);
  const retained=new Set([...pane.sectionsRoot.querySelectorAll('.rc-record[data-rc-key]')].map(node=>node.dataset.rcKey));
  for(const key of pane.rows.keys())if(!retained.has(key))pane.rows.delete(key);
}
function coverageText(value) {
  const parts=[];for(const [key,row] of Object.entries(object(value))){if(typeof row==='object'&&row?.omitted>0)parts.push(label(key)+': '+row.omitted+' older records omitted');if(row?.verification_failed>0)parts.push(label(key)+': '+row.verification_failed+' records unavailable or failed verification');}
  return parts.length?parts.join(' · '):'Details show retained evidence. Missing historical records are not reconstructed.';
}
function cellVersion(view,row) { return JSON.stringify([row.detail_version||[row,view.data.events?.at(-1),view.data.summary],view.data.jobs?.version,view.data.pending_cells?.version,view.data.pending_cells?.run_status]); }
function getPane(view,id) {
  let pane=view.panes.get(id);if(pane)return pane;
  const node=el('article','rc-detail');node.dataset.cellId=id;
  const heading=el('div','rc-detail-heading'),question=el('h2','rc-question'),badge=el('span','rc-status'),status=el('p','rc-note'),research=el('div','rc-research'),facts=el('div'),sectionsRoot=el('div'),coverage=note('');
  heading.append(el('code','rc-id',id),badge);node.append(heading,question,status,research,facts,sectionsRoot,coverage);
  pane={node,question,badge,status,research,facts,sectionsRoot,coverage,rows:new Map(),sections:new Map(),requested:null,loaded:null};view.panes.set(id,pane);
  while(view.panes.size>10){const key=[...view.panes.keys()].find(key=>key!==view.selected);if(key===undefined)break;view.panes.delete(key);}
  return pane;
}
async function refreshCell(view,row,pane) {
  const version=cellVersion(view,row);pane.question.textContent=currentQuestion(row,pane.body);pane.badge.textContent=activity(row)+' · '+label(row.stage);
  if(pane.loaded===version||pane.requested===version)return;
  pane.requested=version;pane.status.textContent=pane.body?'Refreshing saved cell evidence…':'Loading verified cell history…';pane.node.setAttribute('aria-busy','true');
  try {
    const body=await fetchBody(view,'cell',row.id,version);
    if(!body||sessions.get(view.root)!==view||pane.requested!==version)return;
    renderCellBody(view,pane,row,body);pane.loaded=version;
  } catch(error) {if(sessions.get(view.root)===view&&pane.requested===version){pane.status.textContent=(pane.body?'Refresh failed; showing the previous verified snapshot. ':'')+(error?.message||'Cell history unavailable.');if(!pane.body)pane.sectionsRoot.replaceChildren(empty('Cell history unavailable','Select another cell or retry on the next update.'));}}
  finally{if(pane.requested===version){pane.requested=null;pane.node.removeAttribute('aria-busy');}}
}
function select(view,id) {
  const row=array(view.data.cells).find(row=>row.id===id);if(!row)return;
  view.selected=id;const pane=getPane(view,id);if(view.detail.firstChild!==pane.node)view.detail.replaceChildren(pane.node);renderList(view);refreshCell(view,row,pane);
}
function matchesFilter(row,filter) {
  if(filter==='active')return row.scheduled===true;
  if(filter==='research')return ['research','propose'].includes(row.stage);
  if(filter==='sharing')return ['independent_replay','adopt_trial','adopted_for_trials','use_again'].includes(row.stage);
  if(filter==='issues')return /fail|error|defer|unknown/.test(String(row.activity_status||'')+' '+String(row.stage||''))||row.counts?.failed_invocations>0;
  return true;
}
function renderList(view) {
  const query=view.search.value.trim().toLowerCase(),filter=view.filter.value,all=array(view.data.cells);
  const rows=all.filter(row=>matchesFilter(row,filter)&&[row.id,row.question,currentQuestion(row,view.panes.get(row.id)?.body),...array(row.affinities).map(id=>'island '+id),...array(row.tool_ids)].join(' ').toLowerCase().includes(query)).slice().reverse();
  const nodes=[];for(const row of rows){let node=view.listRows.get(row.id);if(!node){node=button('',()=>select(view,row.id),'rc-cell-row');node.dataset.cellId=row.id;view.listRows.set(row.id,node);}node.setAttribute('aria-pressed',String(view.selected===row.id));node.classList.toggle('selected',view.selected===row.id);node.replaceChildren(el('span','rc-cell-row-top','Cell '+short(row.id)+' · '+(array(row.affinities).length?'Island '+array(row.affinities).join(', '):'Island not recorded')),el('span','rc-cell-question',currentQuestion(row,view.panes.get(row.id)?.body)),el('span','rc-cell-meta',activity(row)+' · '+label(row.stage)));nodes.push(node);}
  reconcile(view.list,nodes.length?nodes:[empty('No matching cells','Try a different question, cell ID, island or status.')]);view.listCount.textContent=rows.length+' of '+all.length+' cells';
  const retained=new Set(all.map(row=>row.id));for(const id of view.listRows.keys())if(!retained.has(id))view.listRows.delete(id);
}
function createView(root,identity,options) {
  root.replaceChildren();root.classList.add('research-cells');
  const heading=el('header','rc-heading'),summary=el('div','rc-summary'),notice=note(''),workspace=el('div','rc-workspace'),sidebar=el('aside','rc-sidebar'),controls=el('div','rc-controls'),search=el('input','rc-search'),filter=el('select','rc-filter'),listCount=el('p','rc-list-count'),list=el('div','rc-list'),detail=el('div','rc-detail-host'),emptyRoot=el('div');
  search.type='search';search.placeholder='Search questions, cells or islands';search.setAttribute('aria-label','Search research cells');filter.setAttribute('aria-label','Filter research cells');
  for(const [value,text] of [['all','All activity'],['active','Scheduled cells'],['research','Research'],['sharing','Replay & adoption'],['issues','Errors & deferred']]){const option=el('option','',text);option.value=value;filter.append(option);}
  heading.append(el('h2','','Research cells'),note('Durable research questions and method histories, independent of population storage.'));controls.append(search,filter);sidebar.append(controls,listCount,list);workspace.append(sidebar,detail);root.append(heading,summary,notice,emptyRoot,workspace);
  const view={root,identity,options,summary,notice,emptyRoot,workspace,search,filter,listCount,list,detail,selected:null,listRows:new Map(),panes:new Map(),cache:new Map(),pending:new Map()};sessions.set(root,view);search.addEventListener('input',()=>renderList(view));filter.addEventListener('change',()=>renderList(view));return view;
}
export function renderResearchCells(root,data={},options={}) {
  const identity=JSON.stringify([options.runId,options.identity]);let view=sessions.get(root);
  if(!view||view.identity!==identity)view=createView(root,identity,options);
  const merged=new Map(array(data.cells).map(row=>[row.id,row]));
  for(const pending of array(data.pending_cells?.cells)){const saved=merged.get(pending.id)||{};merged.set(pending.id,{...saved,...pending,current_question:pending.current_question||saved.current_question,detail_version:JSON.stringify([saved.detail_version,pending.detail_version])});}
  view.data={...data,cells:[...merged.values()]};view.options=options;const cells=array(view.data.cells),config=view.data.configuration||{},enabled=config.enabled??view.data.configured?.enabled;
  const status=config.status||(enabled===true?'enabled':enabled===false?'disabled':'not_recorded');
  root.dataset.configuration=status;
  view.summary.replaceChildren();for(const [title,value] of [['Cells',view.data.summary?.cells??array(data.cells).length],['Scheduled cells',array(data.cells).filter(row=>row.scheduled===true).length],['Tool versions',view.data.summary?.versions],['Background jobs',view.data.jobs?.summary?.total]]){const node=el('div');node.append(el('span','',title),el('strong','',number(value)));view.summary.append(node);}
  view.notice.textContent='Execution, replay, adoption and candidate outcomes are separate evidence. Model use and causal benefit are unknown unless explicitly established.';
  if(array(data.pending_cells?.cells).length)view.notice.textContent+=' Pending wave · '+(data.pending_cells.run_status||'process status unknown')+'. Questions below are uncommitted; counters and usage show committed evidence only. No running computation is implied.';
  if(array(data.pending_cells?.warnings).length)view.notice.textContent+=' '+data.pending_cells.warnings.join(' ');
  view.emptyRoot.replaceChildren();view.workspace.hidden=cells.length===0;
  if(!cells.length){const title=status==='disabled'?'Research cells are disabled for this run':status==='enabled'?'Waiting for the first research cell':'Research-cell configuration not recorded';const text=status==='disabled'?'This run has not enabled authored research tools. Population storage, VQ placement and reinforcement learning do not enable research cells by themselves.':status==='enabled'?'No cell has been recorded yet. Bootstrap or the configured scheduling gates may still be in progress. This is not evidence of a failed search.':'No recorded cell data is available for this run. Absence of metadata does not establish that the feature was disabled.';view.emptyRoot.append(empty(title,text));if(config.reason)view.emptyRoot.append(note(config.reason));return view;}
  if(status==='disabled')view.emptyRoot.append(note('Current configuration is disabled; recorded historical cells remain available below.'));
  const selected=cells.find(row=>row.id===view.selected)||cells.at(-1);select(view,selected.id);return view;
}
