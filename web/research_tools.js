// Ordinary Engine tools: metadata comes from the journal; immutable bodies load on demand.
const views=new WeakMap();
const array=value=>Array.isArray(value)?value:[];
const short=value=>String(value??'—').slice(0,12);
const finite=value=>typeof value==='number'&&Number.isFinite(value);
const number=value=>finite(value)?String(value):'—';
const seconds=value=>finite(value)?value.toFixed(3)+'s':'Unknown';
const jobLabel=row=>row.cancel_requested&&['queued','running'].includes(row.status)?'Cancellation requested':({queued:'Queued',running:'Running',cancel_requested:'Cancellation requested',completed:'Completed',failed:'Failed',cancelled:'Cancelled',unknown:'Outcome unknown'}[row.status]||'Status unavailable');
const jobKey=row=>'job:'+row.id+':'+(row.receipt_id||'pending');
const island=value=>value===null||value===undefined?'Island not recorded':'Island '+value;
const text=value=>typeof value==='string'?value:JSON.stringify(value??null,null,2);
function el(tag,className,content){const node=document.createElement(tag);if(className)node.className=className;if(content!==undefined)node.textContent=String(content);return node;}
function button(label,fn,className='tool-link'){const node=el('button',className,label);node.type='button';node.addEventListener('click',fn);return node;}
function blank(title,detail){const box=el('div','tools-empty');box.append(el('strong','',title),el('p','',detail));return box;}
function panel(title,body,open=false){const node=el('details','tool-detail-panel'),pre=el('pre','tool-raw',text(body));pre.tabIndex=0;node.open=open;node.append(el('summary','',title),pre);return node;}
function inputLabel(binding){return binding.target_kind==='failed_candidate'?'Failed candidate':binding.candidate_id||'Input ID unavailable';}
function inputSummary(inputs){
  const targets=inputs?.research_targets;if(!['sciel-research-targets/1','sciel-research-targets/2'].includes(targets?.schema))return null;
  const box=el('section','tool-input-sources'),selected=targets.selected||{},best=targets.population_best;
  box.append(el('h4','','Input source'),el('p','tools-note',(selected.kind==='failed_candidate'?'Failed candidate · no admitted program ID':selected.program_id||'Input ID unavailable')+' · SHA256 '+short(selected.source_sha256)),el('p','tools-note','Ancestry parent '+(targets.ancestry_parent?.program_id||'unrecorded')));
  box.append(el('h4','','Available best reference'),el('p','tools-note',best?(best.program_id+' · SHA256 '+short(best.source_sha256)):'No population best recorded'));
  for(const [name,target] of [['Selected',selected],['Best',best]]){if(!target)continue;const saved=target.saved_evaluation;box.append(el('p','tools-note',name+' saved evaluator output: '+(saved?.status==='available'?'available · '+short(saved.reference?.sha256):saved?.status==='unavailable'?'unavailable · '+(saved.reason||'Reason not recorded'):'not captured in this input contract')));}
  box.append(el('p','tools-note','Frozen inputs from this run. Availability does not prove which source the tool used or establish benefit.'),panel('Source, measurements & frozen identities',targets));return box;
}
function resultLabel(row){
  if(row.phase==='invocation_started'&&!row.receipt_id)return 'Pending · dispatch unconfirmed';
  if(row.dispatch_status==='not_dispatched')return 'Not dispatched · no actual use';
  if(row.result_schema==='sciel-tool-result/1')return ({success:'Check completed',tool_error:'Tool error · check failed',invalid_output:'Invalid tool result',host_failed:'Execution failed',unknown:'Outcome unknown'}[row.tool_result_status]||'Tool outcome not recorded');
  if(row.status==='unknown')return 'Outcome unknown';
  if(row.status==='pending')return 'Pending';
  return row.status||'Outcome not recorded';
}
const cellStage=value=>({propose:'Question opened',research:'Local trial & repair',background_submitted:'Background job submitted',background_deferred:'Background job deferred · not submitted',independent_replay:'Independent replay',adopt_trial:'Recipient trial',adopted_for_trials:'Adopted for trials',use_again:'Post-adoption use'}[value]||'Not recorded');
function current(view){if(view.tab==='jobs')return array(view.data.jobs?.items).slice(-200).reverse();if(view.tab==='lifecycle')return array(view.data.lifecycle?.events).slice(-200).reverse();const source=view.tab==='cells'?'cells':view.tab==='versions'?'versions':view.tab==='calls'?'llm_calls':view.tab==='links'?'child_links':'invocations';return array(view.data[source]).slice(-200).reverse();}
function select(view,kind,id,row){
  const key=kind==='job'?jobKey(row):kind+':'+id+(kind==='cell'?':'+(row.head_revision||row.cell_revision_id||'unrecorded'):'');
  view.selection={key,kind,id,row};
  view.inspector.hidden=false;
  renderInspector(view);
  renderRows(view);
}
function bodyDetail(view,body){
  const holder=el('div','tool-immutable');
  if(body.verified!==true){holder.append(blank('Artifact not verified','Saved content failed verification and is not displayed.'));return holder;}
  holder.append(el('p','tool-verified',body.kind==='job'?'Verified job request · recorded status':'Hash verified · saved artifact'));
  if(body.kind==='job'){
    const sources=inputSummary(body.request?.inputs);if(sources)holder.append(sources);
    holder.append(panel('Exact submitted job',body.request,true));
    if(body.receipt)holder.append(panel('Verified result · full output and execution receipt',body.receipt,true));
    else holder.append(el('p','tools-note','No final execution receipt is available. Missing resource measurements remain unknown.'));
    holder.append(el('p','tools-note','Requested limits are not measured usage. Cancellation is requested by the model; it does not prove that execution has stopped.'));
  }else if(body.kind==='cell'){
    holder.append(el('h4','tool-question',body.current_question||body.research_state?.question||'No experiment question recorded yet'),panel('Origin & recorded scheduling trigger',body.genesis));
    const terminal=!body.active_decision&&!body.pending_decision&&body.terminal_decision?.verified===true?body.terminal_decision:null;
    if(terminal){
      holder.append(el('h4','','Model interpretation · '+terminal.conclusion),el('p','tools-note',terminal.interpretation||'No explanation recorded.'),el('p','tools-note','Next decision: '+terminal.next_decision),el('p','tools-note','Saved planner interpretation, separate from execution status and canonical candidate validity.'));
      if(Object.values(terminal.omitted_chars||{}).some(value=>value>0))holder.append(el('p','tools-note','Excerpt shown; the complete statement is in the saved model response.'));
      holder.append(button('Saved terminal request & response',()=>select(view,'artifact',terminal.proposal_id,{id:terminal.proposal_id})));
    }
    for(const revision of array(body.revision_history)){
      const item=el('section','cell-revision');item.append(el('h4','',String(revision.ordinal)+' · '+String(revision.phase||'Recorded revision')),el('p','tool-id',revision.id),el('p','tools-note',revision.summary||''));
      const links=el('div','cell-evidence-links');
      for(const id of array(revision.tool_ids))links.append(button('Tool '+short(id),()=>select(view,'tool',id,{id})));
      for(const ref of array(revision.evidence)){if(ref.kind==='tool_invocation')links.append(button('Receipt '+short(ref.id),()=>select(view,'artifact',ref.id,ref)));if(ref.kind==='tool_job')links.append(button('Job '+short(ref.id),()=>select(view,'job',ref.id,array(view.data.jobs?.items).find(row=>row.id===ref.id)||{id:ref.id})));}
      item.append(links,panel('Roles, evidence and decision',revision));holder.append(item);
    }
    holder.append(el('p','tools-note',body.history_scope||'Recorded research-cell revisions.'));
    if(body.history_truncated)holder.append(el('p','tools-note','Older revisions omitted by the read bound. Next predecessor: '+body.next_revision_id));
  }else if(body.kind==='proposal'){
    const payload=body.payload||{};
    holder.append(panel('Exact saved request',payload.prompt,true),panel('Exact saved response',payload.response,true));
  }else if(body.kind==='invocation'){
    const payload=body.payload||{},receipt=payload.receipt||{};
    const sources=inputSummary(payload.inputs);if(sources)holder.append(sources);
    if(payload.result?.schema==='sciel-tool-result-assessment/1')holder.append(panel('Tool outcome · separate from Python execution',payload.result,true));
    holder.append(panel('Exact inputs',payload.inputs,true),panel('Execution receipt · output, status and resources',receipt,true));
    holder.append(el('p','tools-note','Executor source hashes cover the file bundle. The tool source SHA256 covers UTF-8 tool.py only.'));
  }else{
    holder.append(panel('tool.py · verified source',body.files?.['tool.py']??'Source unavailable',true));
    for(const parent of array(body.parents))holder.append(parent.verified?panel('Diff from '+short(parent.id),parent.diff||'No source changes'):blank('Parent '+short(parent.id),'Parent artifact unavailable or failed verification.'));
    holder.append(panel('Verified manifest',body.manifest));
    holder.append(el('p','tools-note',body.source_hash_scope||'Source SHA256 covers UTF-8 tool.py only.'));
  }
  return holder;
}
async function load(view,selection,slot){
  const cacheKey=selection.key;
  if(view.cache.has(cacheKey)){slot.replaceChildren(view.cache.get(cacheKey));return;}
  slot.replaceChildren(el('p','tools-note','Verifying saved artifact…'));
  const endpoint=selection.kind==='tool'?'research-tools':selection.kind==='cell'?'research-cells':selection.kind==='job'?'research-tool-jobs':'research-tool-artifacts';
  try{
    const detail=await view.options.fetchJSON('/api/runs/'+encodeURIComponent(view.options.runId)+'/'+endpoint+'/'+encodeURIComponent(selection.id));
    if(views.get(view.root)!==view||view.selection?.key!==selection.key)return;
    const content=bodyDetail(view,detail);view.cache.set(cacheKey,content);if(view.cache.size>12)view.cache.delete(view.cache.keys().next().value);slot.replaceChildren(content);
  }catch(error){if(views.get(view.root)===view&&view.selection?.key===selection.key)slot.replaceChildren(blank('Artifact unavailable',error?.message||'No verified saved body is available.'));}
}
function renderInspector(view){
  const selection=view.selection;if(!selection)return;
  // Mutable counters refresh independently; immutable source DOM keeps scroll, focus and open state.
  if(view.inspector.dataset.selection===selection.key)return;
  view.inspector.dataset.selection=selection.key;view.inspector.replaceChildren();
  const head=el('div','tool-inspector-heading');head.append(el('h3','',selection.kind==='tool'?'Tool version':selection.kind==='cell'?'Research cell history':selection.kind==='job'?'Background job':selection.kind==='link'?'Program receipt links':'Saved tool call'),button('Close',()=>{view.inspector.hidden=true;view.selection=null;view.inspector.dataset.selection='';renderRows(view);}));
  view.inspector.append(head,el('p','tool-id',selection.id));
  if(selection.kind==='job'){
    view.inspector.append(el('p','tool-job-status',jobLabel(selection.row)),el('p','tool-job-resources','Measured CPU '+seconds(selection.row.actual?.cpu_seconds)+' · wall '+seconds(selection.row.actual?.wall_seconds)));
    if(selection.row.parent_job_id)view.inspector.append(button('Continuation of '+short(selection.row.parent_job_id),()=>{const parent=array(view.data.jobs?.items).find(row=>row.id===selection.row.parent_job_id);if(parent)select(view,'job',parent.id,parent);else select(view,'job',selection.row.parent_job_id,{id:selection.row.parent_job_id});}));
  }
  if(selection.kind==='link'){
    view.inspector.append(el('p','tools-note','This link associates a candidate with preceding tool calls. It is not proof of prompt delivery or a causal score improvement.'),panel('Recorded link',selection.row,true));return;
  }
  const slot=el('div','tool-artifact');view.inspector.append(slot);load(view,selection,slot);
}
function table(headers,rows,view){
  const wrap=el('div','tools-table-wrap'),table=el('table','tools-table'),head=el('thead'),tr=el('tr'),body=el('tbody');
  for(const header of headers)tr.append(el('th','',header));head.append(tr);table.append(head,body);wrap.append(table);
  for(const [key,cells] of rows){const row=el('tr');row.dataset.rowKey=key;row.classList.toggle('selected',view.selection?.key===key);for(const cell of cells){const td=el('td');td.append(typeof cell==='object'&&cell?.nodeType?cell:el('span','',cell??'—'));row.append(td);}body.append(row);}
  return wrap;
}
function artifactButton(view,row,label){return row.receipt_id?button(label||short(row.receipt_id),()=>select(view,'artifact',row.receipt_id,row)):el('span','tools-muted','No saved receipt');}
function renderRows(view){
  const focus=document.activeElement?.closest('[data-row-key]')?.dataset.rowKey;
  view.tabs.querySelectorAll('button').forEach(node=>{const active=node.dataset.view===view.tab;node.setAttribute('aria-pressed',String(active));node.classList.toggle('active',active);});
  const rows=current(view);
  let content;
  if(!rows.length){
    const titles={jobs:'No background jobs recorded',cells:'No research cells recorded',lifecycle:'No replay or adoption transitions recorded',versions:'No tool versions recorded',invocations:'No tool invocations recorded',calls:'No tool model requests recorded',links:'No linked programs recorded'};
    content=blank(titles[view.tab],view.data.available===false?'Executable research tools were not enabled or recorded for this run.':view.tab==='links'?'Native Programs remain in the Programs tab. A tool link appears only after an actual child is recorded.':'Only recorded events appear here; availability does not imply execution.');
  }else if(view.tab==='jobs'){
    content=table(['Job / caller','Status','Requested CPU / wall','Measured CPU / wall','Result'],rows.map(row=>{
      const who=el('div','tool-name');who.append(button(short(row.id),()=>select(view,'job',row.id,row)),el('span','tools-muted',island(row.island_id)+' · ancestry '+(row.parent_program_id||'unrecorded')));
      if(row.parent_job_id)who.append(el('span','tools-muted','Continues '+short(row.parent_job_id)));
      const status=el('div','tool-name');status.append(el('span','tool-job-state '+(row.status||'unknown'),jobLabel(row)));if(row.updated_at)status.append(el('time','tools-muted',row.updated_at));if(row.error)status.append(el('span','tools-muted',typeof row.error==='string'?row.error:text(row.error)));
      return [jobKey(row),[who,status,seconds(row.requested?.cpu_seconds)+' / '+seconds(row.requested?.wall_seconds),seconds(row.actual?.cpu_seconds)+' / '+seconds(row.actual?.wall_seconds),button(row.receipt_id?'Open full result':'Inspect request',()=>select(view,'job',row.id,row))]];
    }),view);
  }else if(view.tab==='cells'){
    content=table(['Research question','Origin','Recorded stage','Tool versions','History'],rows.map(row=>{
      const question=el('div','tool-name');question.append(button(row.question||'Open recorded question',()=>select(view,'cell',row.id,row)),el('span','tool-id',short(row.id)));
      return ['cell:'+row.id+':'+(row.head_revision||'unrecorded'),[question,island(row.origin_island_id),cellStage(row.stage)+(row.scheduled===true?' · scheduled':''),array(row.tool_ids).length,button('Revisions & evidence',()=>select(view,'cell',row.id,row))]];
    }),view);
  }else if(view.tab==='lifecycle'){
    content=table(['Transition','Cell / island','Tool','Recorded result','Evidence'],rows.map(row=>{
      const label=row.phase==='replay_result'?'Independent replay':row.phase==='adopted'?'Adoption trial':row.phase==='post_adoption_attempt'?'Post-adoption attempt':'Post-adoption use';
      const result=row.phase==='replay_result'?(row.matched===true?(row.replay_policy==='independent_execution'?'Independent execution verified · measurements may differ':'Exact observations reproduced'):row.matched===false?'Replay criterion not met':'Match unknown'):row.phase==='adopted'?'Adopted for trials · benefit not established':resultLabel(row);
      const who=el('div','tool-name');who.append(button(short(row.cell_id),()=>select(view,'cell',row.cell_id,row)),el('span','tools-muted',island(row.island_id)));
      const proof=el('div','cell-evidence-links');proof.append(artifactButton(view,row,'Open receipt'));if(row.reference_receipt_id)proof.append(button('Reference receipt',()=>select(view,'artifact',row.reference_receipt_id,row)));
      return ['artifact:'+row.receipt_id,[label,who,button(short(row.tool_id),()=>select(view,'tool',row.tool_id,row)),result,proof]];
    }),view);
  }else if(view.tab==='versions'){
    content=table(['Version','Author','Availability','Executions','Other islands','Used by'],rows.map(row=>{
      const name=el('div','tool-name');name.append(button(row.name||short(row.id),()=>select(view,'tool',row.id,row)),el('span','tool-id',short(row.id)));if(row.description)name.append(el('span','tools-muted',row.description));
      return ['tool:'+row.id,[name,island(row.author_island_id),row.status==='published'?(row.availability==='owner_only'||view.data.configured?.share_between_islands===false?'Owner only':row.availability==='shared'||view.data.configured?.share_between_islands===true?'Shared · next wave':'Published · scope unrecorded'):'Registered · unpublished',number(row.invocations),number(row.foreign_invocations),array(row.used_by).map(island).join(', ')||'No recorded use']];
    }),view);
  }else if(view.tab==='invocations'){
    content=table(['Caller / input source','Tool version','Result','CPU / wall','Receipt'],rows.map(row=>{
      const who=el('div','tool-name'),binding=row.target_binding;who.append(el('span','',island(row.island_id)));
      if(binding){who.append(el('span','',inputLabel(binding)+' · '+short(binding.target_source_sha256)),el('span','tools-muted','Ancestry '+(binding.ancestry_parent_id||'unrecorded')));}
      else who.append(el('span','tools-muted','Recorded parent '+(row.parent_program_id||'unrecorded')));
      return ['artifact:'+row.receipt_id,[who,button(short(row.tool_id),()=>select(view,'tool',row.tool_id,row)),resultLabel(row),(finite(row.resources?.cpu_seconds)?row.resources.cpu_seconds.toFixed(3)+'s':'—')+' / '+(finite(row.resources?.wall_seconds)?row.resources.wall_seconds.toFixed(3)+'s':'—'),artifactButton(view,row,'Open exact inputs & output')]];
    }),view);
  }else if(view.tab==='calls'){
    content=table(['Episode / attempt','Caller','Result','Known cost','Request & response'],rows.map(row=>['artifact:'+row.receipt_id,[short(row.action_id)+' · '+(row.attempt??'—'),island(row.island_id),row.phase==='llm_start'?'Pending':row.status||'Response recorded',finite(row.known_cost)?'$'+row.known_cost.toFixed(4):'Unknown',artifactButton(view,row,'Open saved exchange')]]),view);
  }else{
    content=table(['Program','Record kind','Island','Executed tools','Associated receipts','Link'],rows.map(row=>['link:'+(row.id||row.child_program_id),[button(row.child_program_id,()=>view.options.onProgram?.(row.child_program_id)),row.link_kind==='remeasurement'?'Remeasurement':row.link_kind==='mutation'?'Mutation':'Not recorded',island(row.island_id),array(row.tool_ids).map(short).join(', ')||'None recorded',array(row.receipt_ids).length,button('Inspect',()=>select(view,'link',row.id||row.child_program_id,row))]]),view);
  }
  view.list.replaceChildren(content);
  if(focus){const row=[...view.list.querySelectorAll('[data-row-key]')].find(node=>node.dataset.rowKey===focus);row?.querySelector('button')?.focus({preventScroll:true});}
}
export function renderResearchTools(root,data={},options={}){
  const identity=JSON.stringify([options.runId,options.identity]);let view=views.get(root);
  if(!view||view.identity!==identity){
    root.replaceChildren();root.className='research-tools';
    const summary=el('div','tools-summary'),jobs=el('section','tools-jobs'),lifecycle=el('section','tools-lifecycle'),tabs=el('div','tools-tabs'),list=el('div','tools-records'),inspector=el('aside','tool-inspector'),columns=el('div','tools-columns'),note=el('p','tools-note');
    tabs.setAttribute('aria-label','Tool records');inspector.hidden=true;
    view={root,identity,summary,jobs,lifecycle,tabs,list,inspector,note,tab:array(data?.jobs?.items).length?'jobs':array(data?.cells).length?'cells':'versions',cache:new Map(),selection:null};views.set(root,view);
    for(const [id,label] of [['jobs','Background jobs'],['cells','Research cells'],['lifecycle','Replay & adoption'],['versions','Versions'],['invocations','Executions'],['calls','Model requests'],['links','Program links']]){const node=button(label,()=>{view.tab=id;renderRows(view);},'tools-tab');node.dataset.view=id;tabs.append(node);}
    columns.append(list,inspector);root.append(summary,jobs,lifecycle,tabs,columns,note);
  }
  view.data=data||{};view.options=options;
  const s=view.data.summary||{};
  view.summary.replaceChildren();
  for(const [label,value] of [['Published versions',s.published],['Actual executions',s.actual_invocations],['Cross-island executions',s.foreign_invocations],['Linked programs',s.linked_programs]]){const item=el('div');item.append(el('span','',label),el('strong','',number(value)));view.summary.append(item);}
  const jobs=view.data.jobs||{},js=jobs.summary||{};view.jobs.hidden=!jobs.available;view.jobs.replaceChildren();
  if(jobs.available){const head=el('div','tools-jobs-heading');head.append(el('h3','','Background research'),button('View jobs · '+number(js.total),()=>{view.tab='jobs';renderRows(view);}));view.jobs.append(head,el('p','tools-jobs-status',number(js.running)+' running · '+number(js.queued)+' queued · '+number(js.cancel_requested)+' cancellation requested · '+number(js.unknown)+' unknown'),el('p','tools-note','Ordinary search can continue while these jobs run. The model requests work, polls results and requests cancellation. Recorded job status refreshes independently of search events.'),el('p','tools-note','Measured CPU '+seconds(js.observed_cpu_seconds)+' across '+number(js.observed_cpu_jobs)+' jobs; '+number(js.unknown_cpu_jobs)+' have unknown CPU. Requested limits and reservations are separate from measured usage.'+(js.omitted?' Showing '+number(js.visible)+' of '+number(js.total)+' committed jobs; usage totals cover the visible window.':'')));}
  if(view.selection?.kind==='job'){
    const row=array(jobs.items).find(row=>row.id===view.selection.id);
    if(row){const key=jobKey(row);view.selection={...view.selection,key,row};renderInspector(view);const status=view.inspector.querySelector('.tool-job-status'),resources=view.inspector.querySelector('.tool-job-resources');if(status)status.textContent=jobLabel(row);if(resources)resources.textContent='Measured CPU '+seconds(row.actual?.cpu_seconds)+' · wall '+seconds(row.actual?.wall_seconds);}
  }
  const lifecycle=view.data.lifecycle||{},counts=lifecycle.counts||{};view.lifecycle.hidden=lifecycle.recorded!==true;view.lifecycle.replaceChildren();
  if(lifecycle.recorded===true){
    const head=el('div','tools-lifecycle-heading');head.append(el('h3','','From question to later use'),el('span','tools-muted','Recorded transitions · counts are not a conversion funnel'));
    const stages=el('ol','cell-stage-counts');for(const [label,value] of [['Questions opened',counts.proposed_cells],['Local invocations',counts.local_trials],['Replay checks passed',counts.matched_replays],['Adopted for trials',counts.adoptions],['Later invocations',counts.post_adoption_uses]]){const item=el('li');item.append(el('strong','',number(value)),el('span','',label));stages.append(item);}
    view.lifecycle.append(head,stages,el('p','tools-note','Research cells retain questions, methods and evidence across program generations. They are separate from candidate programs and population storage. Each tool version fixes its replay criterion: exact observations, excluding diagnostics, or independent execution without a claim that measurements match. Adoption admits further trials and does not establish task benefit.'));
  }
  const omissions=(view.data.coverage?.omitted_versions||0)+(view.data.coverage?.omitted_invocations||0)+(view.data.coverage?.omitted_cells||0);
  view.note.textContent='Immutable tool library · '+number(s.prepared_contexts)+' prepared contexts · '+number(s.failed_invocations)+' failed checks or executions · up to 200 recent records per view'+(omissions?' · older rows omitted':'')+'. A completed background job means execution ended; its saved tool outcome shows whether the check succeeded. Prepared Snapshot context does not prove prompt delivery. Child links do not establish causal utility. Tool LLM costs are already in Engine spend; measured CPU excludes Docker daemon and VM overhead.';
  renderRows(view);
  return view;
}
