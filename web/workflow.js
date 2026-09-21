/** Read-only, bounded activity stream. Large saved evidence loads on disclosure. */
const sessions = new WeakMap();
const ACTORS = {all:'All activity', model:'Model', tool:'Tool', task:'Task', system:'System'};
const ICONS = {model:'M', tool:'↗', task:'◇', system:'·'};
const finite = value => typeof value === 'number' && Number.isFinite(value);
const make = (s, tag, cls, text) => {
  const node=s.root.ownerDocument.createElement(tag);
  if(cls)node.className=cls;
  if(text!==undefined)node.textContent=String(text);
  return node;
};
const button = (s,cls,text,fn) => {const b=make(s,'button',cls,text);b.type='button';b.addEventListener('click',fn);return b;};
const dateOf = item => {const d=item.timestamp?new Date(item.timestamp):null;return d&&Number.isFinite(d.getTime())?d:null;};
const clock = d => d?d.toISOString().slice(11,19):'Time not recorded';
const day = d => d?new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(d):'Time not recorded';
const elapsed = seconds => {
  if(!finite(seconds)||seconds<0)return null;
  const n=Math.floor(seconds),h=Math.floor(n/3600),m=Math.floor(n%3600/60),sec=n%60;
  return 'T+'+[h,m,sec].map(v=>String(v).padStart(2,'0')).join(':');
};
const duration = value => value<1?Math.round(value*1000)+' ms':value<60?value.toFixed(1)+' s':Math.floor(value/60)+'m '+Math.round(value%60)+'s';
const digest = item => JSON.stringify([item.detail_version,item.timestamp,item.status,item.summary,item.commit_state,item.duration_seconds,item.cost,item.refs]);
const active = s => !s.dead&&sessions.get(s.root)===s;
const endpoint = s => '/api/runs/'+encodeURIComponent(s.runId)+'/workflow';
const nearBottom = s => s.stream.scrollHeight-s.stream.clientHeight-s.stream.scrollTop<64;
const reasonClass = status => /fail|error|invalid|reject|unknown|stopp/i.test(status||'')?'attention':/pending|running|start|dispatch/i.test(status||'')?'pending':'';

function build(s) {
  s.panel=make(s,'section','workflow');s.panel.setAttribute('aria-label','Work Flow');
  const head=make(s,'header','wf-heading'),heading=make(s,'div');
  heading.append(make(s,'span','wf-eyebrow','EXPERIMENT ACTIVITY'),make(s,'h2','','Work Flow'),make(s,'p','','A conversation between the model, its tools and the search.'));
  const controls=make(s,'div','wf-heading-controls');
  s.connection=make(s,'span','wf-connection');
  s.refresh=button(s,'wf-refresh','Refresh',()=>load(s,{force:true}));s.refresh.setAttribute('aria-label','Refresh Work Flow');
  controls.append(s.connection,s.refresh);head.append(heading,controls);
  const toolbar=make(s,'div','wf-toolbar'),filters=make(s,'div','wf-filters');filters.setAttribute('role','group');filters.setAttribute('aria-label','Filter activity by actor');
  for(const [key,label] of Object.entries(ACTORS)){
    const b=button(s,'wf-filter',label,()=>{s.actor=key;resetPage(s);updateFilters(s);load(s,{force:true,reset:true});});
    b.dataset.actor=key;filters.append(b);
  }
  const search=make(s,'label','wf-search');search.append(make(s,'span','wf-search-icon','⌕'));
  s.search=make(s,'input');s.search.type='search';s.search.placeholder='Search activity…';s.search.setAttribute('aria-label','Search Work Flow activity');
  s.search.addEventListener('input',()=>{clearTimeout(s.searchTimer);s.searchTimer=setTimeout(()=>{if(!active(s))return;s.query=s.search.value;resetPage(s);load(s,{force:true,reset:true});},220);});
  search.append(s.search);toolbar.append(filters,search);
  const strip=make(s,'div','wf-strip');s.count=make(s,'span','wf-count','Loading recorded activity…');s.count.setAttribute('role','status');
  strip.append(s.count,make(s,'span','wf-order','UTC · Oldest → newest'));
  s.notice=make(s,'p','wf-notice');s.notice.hidden=true;
  s.error=make(s,'div','wf-error');s.error.hidden=true;s.error.setAttribute('role','status');
  s.pageBar=make(s,'div','wf-pagebar');
  s.older=button(s,'wf-page-link','↑ Older activity',()=>{if(s.nextBefore==null)return;s.history.push(s.before);s.before=s.nextBefore;load(s,{force:true,reset:true});});
  s.newer=button(s,'wf-page-link','Newer activity ↓',()=>{s.before=s.history.pop()??null;load(s,{force:true,reset:true});});
  s.pageBar.append(s.older,s.newer);
  s.stream=make(s,'div','wf-stream');s.stream.tabIndex=0;s.stream.setAttribute('aria-label','Chronological activity. Expand a message to inspect its evidence.');
  s.stream.addEventListener('scroll',()=>{if(nearBottom(s)&&s.waiting)applyWaiting(s);},{passive:true});
  s.messages=make(s,'div','wf-messages');s.stream.append(s.messages);
  s.newActivity=button(s,'wf-new-activity','New activity ↓',()=>applyWaiting(s));s.newActivity.hidden=true;
  const footer=make(s,'footer','wf-footer');s.footerText=make(s,'span','','Only saved events appear here.');
  s.latest=button(s,'wf-page-link','Back to latest ↓',()=>{resetPage(s);load(s,{force:true,reset:true});});s.latest.hidden=true;
  footer.append(s.footerText,s.latest);
  s.panel.append(head,toolbar,strip,s.notice,s.error,s.pageBar,s.stream,s.newActivity,footer);
  s.root.replaceChildren(s.panel);updateFilters(s);
}
function updateFilters(s){for(const b of s.panel.querySelectorAll('.wf-filter'))b.setAttribute('aria-pressed',String(b.dataset.actor===s.actor));}
function resetPage(s){s.before=null;s.history=[];s.waiting=null;s.newActivity.hidden=true;}
function connection(s){
  const polling=s.follow&&s.connected&&s.live;
  s.connection.textContent=!s.follow?'Updates paused':!s.connected?'Connection paused':s.live?'Following live':'Recorded history';
  s.connection.classList.toggle('is-live',!!polling);
  clearInterval(s.timer);s.timer=null;
  if(polling)s.timer=setInterval(()=>{if(active(s)&&s.root.isConnected&&!s.loading&&s.before===null)load(s);},3000);
}
function message(s,item){
  const actor=ACTORS[item.actor]?item.actor:'system';
  const node=make(s,'article','wf-message wf-'+actor);node.dataset.eventId=item.id;
  const avatar=make(s,'span','wf-avatar',ICONS[actor]);avatar.setAttribute('aria-hidden','true');
  const wrap=make(s,'div','wf-message-wrap'),meta=make(s,'div','wf-message-meta');
  const actorName=make(s,'strong','wf-actor'),model=make(s,'span','wf-model-name'),time=make(s,'time','wf-time');
  meta.append(actorName,model,time);
  const bubble=make(s,'div','wf-bubble'),title=make(s,'h3','wf-title'),summary=make(s,'p','wf-summary'),facts=make(s,'div','wf-facts');
  const inspect=make(s,'details','wf-inspect'),toggle=make(s,'summary');
  toggle.append(make(s,'span','wf-chevron','›'),make(s,'span','wf-inspect-label','View saved details'));
  const content=make(s,'div','wf-evidence');inspect.append(toggle,content);
  const row={node,actorName,model,time,bubble,title,summary,facts,inspect,content,item,signature:null,cache:null,request:0};
  inspect.addEventListener('toggle',()=>{if(inspect.open)expand(s,row);});
  bubble.append(title,summary,facts,inspect);wrap.append(meta,bubble);node.append(avatar,wrap);return row;
}
function updateMessage(s,row,item){
  const previous=row.signature;row.item=item;row.signature=digest(item);
  const d=dateOf(item);row.actorName.textContent=item.actor_label||ACTORS[item.actor]||'System';
  row.model.textContent=item.model||'';row.model.hidden=!item.model;row.model.title=item.model||'';
  row.time.textContent=clock(d);if(d){row.time.dateTime=d.toISOString();row.time.title=day(d)+' · '+clock(d)+' UTC';}else row.time.removeAttribute('datetime');
  row.title.textContent=item.title||'Recorded activity';row.summary.textContent=item.summary||'';row.summary.hidden=!item.summary;
  const facts=[];
  if(item.status)facts.push(make(s,'span','wf-status '+reasonClass(item.status),String(item.status).replaceAll('_',' ')));
  if(item.commit_state==='pending'||item.committed===false)facts.push(make(s,'span','wf-pending-commit','Pending commit'));
  const refs=item.refs||{};
  for(const text of [finite(item.iteration)?'Step '+item.iteration:null,refs.experiment_id,refs.program_id,refs.tool_id]){
    if(text){const chip=make(s,'span','wf-reference',text);chip.title=String(text);facts.push(chip);}
  }
  const offset=elapsed(item.elapsed_seconds);if(offset)facts.push(make(s,'span','wf-elapsed',offset));
  if(finite(item.duration_seconds)&&item.duration_seconds>=0)facts.push(make(s,'span','wf-duration',duration(item.duration_seconds)));
  if(finite(item.cost))facts.push(make(s,'span','wf-cost','$'+item.cost.toFixed(item.cost>0&&item.cost<.0001?6:4)));
  if(item.cost_unknown)facts.push(make(s,'span','wf-status attention','Cost unknown'));
  row.facts.replaceChildren(...facts);row.facts.hidden=!facts.length;
  row.inspect.hidden=item.details_available===false;
  if(previous&&previous!==row.signature&&row.cache){
    let refresh=row.content.querySelector('.wf-evidence-refresh');
    if(!refresh){refresh=button(s,'wf-evidence-refresh','Saved details updated · reload',()=>expand(s,row,true));row.content.prepend(refresh);}
  }
}
function paint(s,result,{reset=false}={}){
  const top=s.stream.scrollTop,bottom=nearBottom(s),focus=s.root.ownerDocument.activeElement;
  const rows=new Map(),nodes=[];let previousDay=null;
  for(const item of result.items||[]){
    if(!item||typeof item.id!=='string'||rows.has(item.id))continue;
    const d=day(dateOf(item));if(d!==previousDay){nodes.push(make(s,'div','wf-day',d));previousDay=d;}
    const row=s.rows.get(item.id)||message(s,item);updateMessage(s,row,item);rows.set(item.id,row);nodes.push(row.node);
  }
  if(!rows.size){const empty=make(s,'div','wf-empty');empty.append(make(s,'strong','',s.query||s.actor!=='all'?'No matching activity':'The conversation starts here'),make(s,'p','',s.query||s.actor!=='all'?'Try another actor or search term.':'Model calls, tool checks and search events appear as they are recorded.'));nodes.push(empty);}
  s.messages.replaceChildren(...nodes);s.rows=rows;s.loaded=true;s.total=result.total??rows.size;s.nextBefore=result.next_before??null;
  s.older.disabled=!result.has_more||s.nextBefore===null;s.newer.hidden=s.before===null;s.latest.hidden=s.before===null;
  s.count.textContent=(s.before===null?'Latest ':'Earlier ')+rows.size+' of '+s.total+' events';
  const warnings=(result.warnings||[]).map(x=>typeof x==='string'?x:x.message||x.reason||'Some activity is unavailable.');
  s.notice.textContent=warnings.join(' ');s.notice.hidden=!warnings.length;
  s.footerText.textContent=s.before===null?'You are viewing the latest recorded activity.':'Browsing earlier activity. Live updates will not move this page.';
  if(focus&&s.root.contains(focus))focus.focus({preventScroll:true});
  s.stream.scrollTop=reset?(s.before===null?s.stream.scrollHeight:0):bottom?s.stream.scrollHeight:top;
}
function applyWaiting(s){if(!s.waiting)return;const result=s.waiting;s.waiting=null;s.newActivity.hidden=true;paint(s,result,{reset:true});}
async function load(s,{force=false,reset=false}={}){
  if(!active(s)||s.loading&&!force)return;
  const request=++s.listRequest;s.loading=true;s.refresh.disabled=true;
  const query=new URLSearchParams({limit:'60',actor:s.actor});if(s.query)query.set('q',s.query);if(s.before!==null)query.set('before',s.before);
  try{
    const result=await s.fetchJSON(endpoint(s)+'?'+query);
    if(!active(s)||request!==s.listRequest)return;
    if(!result||!Array.isArray(result.items))throw new Error('Invalid activity response');
    s.error.hidden=true;
    const fresh=result.items.filter(item=>!s.rows.has(item.id)).length;
    if(s.loaded&&s.before===null&&!reset&&!force&&fresh&&!nearBottom(s)){
      s.waiting=result;s.newActivity.textContent=fresh+' new event'+(fresh===1?'':'s')+' ↓';s.newActivity.hidden=false;
    }else{paint(s,result,{reset:reset||!s.loaded});s.waiting=null;s.newActivity.hidden=true;}
  }catch(error){if(active(s)&&request===s.listRequest){s.error.textContent='Unable to load activity. Saved messages remain visible. Use Refresh to try again.';s.error.hidden=false;if(!s.loaded)s.count.textContent='Activity unavailable';}}
  finally{if(active(s)&&request===s.listRequest){s.loading=false;s.refresh.disabled=false;}}
}
function section(s,data,index){
  const node=make(s,'details','wf-section');node.open=index===0;
  const head=make(s,'summary'),name=make(s,'span','wf-section-name',data.label||'Saved evidence');
  head.append(make(s,'span','wf-chevron','›'),name);
  const raw=data.text==null?'':typeof data.text==='string'?data.text:JSON.stringify(data.text,null,2);
  head.append(make(s,'span','wf-section-size',raw.length.toLocaleString('en-US')+' chars'));
  const body=make(s,'div','wf-section-body');
  if(data.note)body.append(make(s,'p','wf-section-note',data.note));
  const format=['diff','code','json'].includes(data.format)?data.format:'text';
  if(raw){
    const actions=make(s,'div','wf-evidence-actions'),wrap=make(s,'label','wf-wrap');
    const check=make(s,'input');check.type='checkbox';check.checked=format==='text';wrap.append(check,make(s,'span','','Wrap lines'));
    const pre=make(s,'pre','wf-raw wf-format-'+format);pre.classList.toggle('is-wrapped',check.checked);pre.tabIndex=0;pre.setAttribute('aria-label',data.label||'Saved evidence');
    const renderRaw=()=>{
      if(format==='diff'&&raw.length<180000){const fragment=s.root.ownerDocument.createDocumentFragment();for(const line of raw.split('\n')){const cls=line.startsWith('@@')?'hunk':line.startsWith('+')&&!line.startsWith('+++')?'added':line.startsWith('-')&&!line.startsWith('---')?'removed':'context';fragment.append(make(s,'span','wf-diff-line '+cls,line+'\n'));}pre.append(fragment);}else pre.textContent=raw;
    };
    // Do not create thousands of diff nodes before their disclosure is opened.
    let rendered=false;const ensure=()=>{if(node.open&&!rendered){rendered=true;renderRaw();}};
    node.addEventListener('toggle',ensure);
    check.addEventListener('change',()=>pre.classList.toggle('is-wrapped',check.checked));
    const copy=button(s,'wf-copy','Copy',async()=>{try{await s.root.ownerDocument.defaultView.navigator.clipboard.writeText(raw);copy.textContent='Copied';}catch{copy.textContent='Select text to copy';}});
    copy.setAttribute('aria-label','Copy '+(data.label||'saved evidence'));actions.append(wrap,copy);body.append(actions,pre);ensure();
  }else if(!data.note)body.append(make(s,'p','wf-section-note','No text was recorded.'));
  node.append(head,body);return node;
}
async function expand(s,row,force=false){
  if(!active(s)||row.inspect.hidden)return;
  if(row.cache&&!force)return;
  if(row.pending&&!force)return;
  const request=++row.request;row.pending=true;row.content.setAttribute('aria-busy','true');
  if(!row.cache)row.content.replaceChildren(make(s,'p','wf-section-note','Loading saved evidence…'));
  try{
    const result=await s.fetchJSON(endpoint(s)+'/'+encodeURIComponent(row.item.id));
    if(!active(s)||s.rows.get(row.item.id)!==row||request!==row.request)return;
    if(!Array.isArray(result.sections))throw new Error('Evidence unavailable');
    row.cache=result;row.content.replaceChildren(...result.sections.map((data,i)=>section(s,data,i)));
    const warnings=(result.warnings||[]).map(value=>typeof value==='string'?value:value.message||value.reason||'Some saved evidence is unavailable.');
    if(warnings.length)row.content.prepend(make(s,'p','wf-section-note wf-evidence-warning',warnings.join(' ')));
    if(!result.sections.length)row.content.append(make(s,'p','wf-section-note','No additional evidence was recorded for this event.'));
  }catch{
    if(active(s)&&request===row.request){row.content.replaceChildren(make(s,'p','wf-section-note','Saved details are unavailable.'),button(s,'wf-page-link','Try again',()=>expand(s,row,true)));}
  }finally{if(active(s)&&request===row.request){row.pending=false;row.content.removeAttribute('aria-busy');}}
}
export function destroyWorkFlow(container){
  const s=sessions.get(container);if(!s)return;s.dead=true;s.listRequest++;clearInterval(s.timer);clearTimeout(s.searchTimer);sessions.delete(container);
}
export function renderWorkFlow(container,{runId,identity=runId,version,fetchJSON,follow=true,connected=true,live=false}={}){
  if(!container||!runId||typeof fetchJSON!=='function')return;
  let s=sessions.get(container);
  if(!s||s.runId!==runId||s.identity!==identity||!container.contains(s.panel)){
    destroyWorkFlow(container);s={root:container,runId,identity,version,fetchJSON,follow,connected,live,rows:new Map(),actor:'all',query:'',before:null,history:[],listRequest:0,loaded:false,dead:false};
    sessions.set(container,s);build(s);connection(s);load(s,{reset:true});return;
  }
  const changed=s.version!==version,connectChanged=s.follow!==follow||s.connected!==connected||s.live!==live;
  s.fetchJSON=fetchJSON;s.version=version;s.follow=follow;s.connected=connected;s.live=live;
  if(connectChanged)connection(s);
  if(changed||connectChanged&&follow&&connected)load(s);
}
