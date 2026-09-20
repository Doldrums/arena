const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite = value => typeof value === 'number' && Number.isFinite(value);
const sessions = new WeakMap();
const roles = {G:'Generation',C:'Conclusion',R:'Reflection',idea:'Idea proposal',unknown:'Role not recorded'};
const labels = {returned:'Response recorded',failed:'Failed',response_not_recorded:'Response not recorded'};
const duration = value => finite(value)?value.toFixed(2)+' s':'Not recorded';
const timestamp = value => {if(typeof value!=='string')return 'Not recorded';const date=new Date(value);return Number.isNaN(date.valueOf())?'Not recorded':new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false,timeZone:'UTC'}).format(date).replace(',',' ·')+' UTC';};

function textPanel(side, payload) {
  const title=side==='prompt'?'LLM request':'LLM response';
  const state=payload?.available?(payload.truncated?'Recorded prefix · truncated':'Full recorded text'):'Not recorded';
  return '<details class="llm-text" data-text-part="'+side+'"><summary>'+title+' <span>'+escape(state)+'</span></summary>'+
    (payload?.note?'<p class="llm-note">'+escape(payload.note)+'</p>':'')+
    (payload?.sha256?'<div class="llm-digest">SHA-256 <code>'+escape(payload.sha256)+'</code></div>':'')+
    (typeof payload?.text==='string'?'<button class="inline-link llm-copy" data-copy="'+side+'">Copy '+(side==='prompt'?'request':'response')+'</button><pre class="llm-raw" tabindex="0">'+escape(payload.text)+'</pre>':'<p class="llm-missing">Original text is unavailable. The monitor does not reconstruct it.</p>')+'</details>';
}

function detailsHTML(call) {
  const latency=call.latency_source==='recorded_call'?'Recorded call duration':call.latency_source==='journal_event_interval'?'Journal event interval (includes local processing)':'Duration not recorded';
  const provenance=call.cost_provenance;
  const costSource=provenance?.source==='provider_reported'?'Provider reported':provenance?.source==='token_estimate'?'Token estimate':provenance?.source==='unavailable'?'Unavailable':'Not recorded';
  const fields=[['Model',call.model||'Not recorded'],['Started',timestamp(call.started_at)],['Ended',timestamp(call.ended_at)],[latency,duration(call.elapsed_seconds)],['Recorded cost',finite(call.cost)?'$'+call.cost.toFixed(6):'Unknown'],['Cost source',costSource],['Outcome',call.outcome_status||'Not recorded']];
  if(provenance?.source==='token_estimate')fields.push(['Saved estimate rates',provenance.pricing_key+' · input $'+provenance.prompt_usd_per_1k+' / output $'+provenance.completion_usd_per_1k+' per 1K tokens']);
  return '<dl class="llm-metadata">'+fields.map(([key,value])=>'<div><dt>'+escape(key)+'</dt><dd>'+escape(value)+'</dd></div>').join('')+'</dl>'+
    (call.current_call_cost_unknown===true?'<p class="llm-note">This call may have incurred a charge. Its billed cost is unknown.</p>':'')+
    (call.error?'<div class="llm-error"><strong>Recorded error</strong><pre>'+escape(JSON.stringify(call.error,null,2))+'</pre></div>':'')+
    (Object.keys(call.request_options||{}).length?'<details class="llm-text" data-text-part="options"><summary>Recorded request options</summary><pre class="llm-raw">'+escape(JSON.stringify(call.request_options,null,2))+'</pre></details>':'')+
    textPanel('prompt',call.prompt)+textPanel('response',call.response);
}

function bodyView(body){
  const active=body.ownerDocument.activeElement,part=active?.closest('[data-text-part]');
  return {parts:[...body.querySelectorAll('[data-text-part]')].map(node=>({
    key:node.dataset.textPart,open:node.open,top:node.querySelector('.llm-raw')?.scrollTop||0,
    left:node.querySelector('.llm-raw')?.scrollLeft||0})),
    focus:part&&body.contains(active)?{part:part.dataset.textPart,
      selector:active.matches('summary')?'summary':active.matches('[data-copy]')?'[data-copy]':'.llm-raw'}:null};
}
function restoreBody(body,view){
  for(const saved of view.parts){
    const part=body.querySelector('[data-text-part="'+saved.key+'"]');if(!part)continue;
    part.open=saved.open;const text=part.querySelector('.llm-raw');
    if(text){text.scrollTop=saved.top;text.scrollLeft=saved.left;}
  }
  if(view.focus)body.querySelector('[data-text-part="'+view.focus.part+'"] '+view.focus.selector)?.focus({preventScroll:true});
}

async function expand(session, element) {
  if(!element.open)return;
  const id=element.dataset.callId,body=element.querySelector('.llm-call-body');
  const version=session.version,key=JSON.stringify([session.identity,version,id]);
  if(body.dataset.loadedKey===key||body.dataset.pendingKey===key)return;
  body.dataset.pendingKey=key;body.setAttribute('aria-busy','true');
  if(!body.dataset.loadedKey)body.textContent='Loading saved request and response…';
  const current=()=>sessions.get(session.container)===session&&session.version===version;
  try {
    let call=session.cache.get(key);
    if(!call){
      let pending=session.pending.get(key);
      if(!pending){
        pending=session.fetchJSON('/api/runs/'+encodeURIComponent(session.runId)+'/llm-calls/'+encodeURIComponent(id));
        session.pending.set(key,pending);
      }
      try{call=await pending;}finally{if(session.pending.get(key)===pending)session.pending.delete(key);}
      if(!current())return;
      session.cache.set(key,call);
      while(session.cache.size>12)session.cache.delete(session.cache.keys().next().value);
    }
    if(!current()||!session.container.contains(element))return;
    const view=bodyView(body);
    body.innerHTML=detailsHTML(call);body.dataset.loadedKey=key;
    restoreBody(body,view);
    body.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{
      try{await navigator.clipboard.writeText(call[button.dataset.copy].text);button.textContent='Copied';}
      catch{button.textContent='Select text to copy';}
    }));
  }catch{if(current()&&session.container.contains(element)&&!body.dataset.loadedKey)body.textContent='Unable to load saved text. Close and reopen this call to retry.';}
  finally{if(body.dataset.pendingKey===key){delete body.dataset.pendingKey;body.removeAttribute('aria-busy');}}
}

async function load(session) {
  const epoch=++session.epoch;
  const list=session.container.querySelector('.llm-call-list');
  if(!list)return;
  list.setAttribute('aria-busy','true');
  try {
    const params=new URLSearchParams({offset:String(session.offset),limit:'50',q:session.query});
    const result=await session.fetchJSON('/api/runs/'+encodeURIComponent(session.runId)+'/llm-calls?'+params);
    if(epoch!==session.epoch||!session.container.querySelector('.llm-call-list'))return;
    session.container.querySelector('.llm-call-count').textContent=result.total+' recorded '+(result.total===1?'call':'calls');
    const existing=new Map([...list.querySelectorAll('details.llm-call')].map(node=>[node.dataset.callId,node]));
    const focus=list.contains(list.ownerDocument.activeElement)?list.ownerDocument.activeElement:null;
    const elements=(result.calls||[]).map(call=>{
      let element=existing.get(call.id);
      if(!element){
        element=list.ownerDocument.createElement('details');element.className='llm-call';element.dataset.callId=call.id;
        element.innerHTML='<summary></summary><div class="llm-call-body"></div>';
        element.addEventListener('toggle',event=>{if(event.target===element)expand(session,element);});
      }
      element.querySelector('summary').innerHTML='<span class="llm-role">'+escape(call.role==='unknown'?'?':call.role==='idea'?'I':call.role)+'</span><span class="llm-call-title"><strong>'+escape(roles[call.role]||call.role)+' · '+escape(call.reference||call.id)+'</strong><small>'+escape(call.iteration===null||call.iteration===undefined?'Iteration not recorded':'Iteration '+call.iteration)+' · '+escape(call.model||'Model not recorded')+'</small></span><span class="llm-call-state '+(call.status==='failed'?'negative-text':'')+'">'+escape(labels[call.status]||call.status)+'</span><span class="llm-call-time" title="'+escape(call.started_at||'')+'">'+escape(timestamp(call.started_at))+'</span>';
      return element;
    });
    list.replaceChildren(...elements);
    if(!elements.length)list.innerHTML='<div class="empty-panel"><strong>No recorded calls match</strong>Try a different experiment, role or iteration.</div>';
    if(focus&&list.contains(focus))focus.focus({preventScroll:true});
    list.removeAttribute('aria-busy');
    for(const element of list.querySelectorAll('details.llm-call')){
      if(element.open)expand(session,element);
    }
    const pager=session.container.querySelector('.llm-pagination');
    pager.innerHTML='<button class="button" data-page="previous"'+(session.offset===0?' disabled':'')+'>Newer calls</button><span>'+escape(result.total?session.offset+1:0)+'–'+escape(Math.min(session.offset+50,result.total))+' of '+escape(result.total)+'</span><button class="button" data-page="next"'+(result.next_offset===null?' disabled':'')+'>Older calls</button>';
    pager.querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>{session.offset=button.dataset.page==='previous'?Math.max(0,session.offset-50):result.next_offset;load(session);}));
  }catch{if(epoch===session.epoch){list.removeAttribute('aria-busy');list.textContent='Unable to read LLM calls. Refresh to try again.';}}
}

export function renderLLMCalls(container,{runId,identity=runId,version,query='',fetchJSON}) {
  let session=sessions.get(container);
  const changedRun=!session||session.runId!==runId||session.identity!==identity;
  if(changedRun&&session)session.epoch++;
  if(changedRun){session={container,runId,identity,version,query,offset:0,epoch:0,cache:new Map(),pending:new Map(),fetchJSON};sessions.set(container,session);}
  if(session.query!==query){session.query=query;session.offset=0;}
  if(session.version!==version){session.version=version;session.cache.clear();}
  session.fetchJSON=fetchJSON;
  if(!container.querySelector('.llm-inspector')||changedRun){
    container.innerHTML='<div class="llm-inspector"><div class="table-toolbar"><span class="llm-call-count">Loading calls…</span><input id="content-search" type="search" placeholder="Search role, experiment, iteration or model" aria-label="Search LLM calls" value="'+escape(query)+'"></div><p class="llm-intro">Expand a call to inspect its saved request, raw response and error. Historical hashes are not reconstructed. Full text loads only when opened.</p><div class="llm-call-list"></div><div class="llm-pagination"></div></div>';
  }
  container.querySelector('#content-search').value=query;
  load(session);
}
