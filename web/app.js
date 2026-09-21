import {renderResearchTools} from './research_tools.js';
import {renderResearchCells} from './research_cells.js';
import {renderPackings, suspendPackings, destroyPackings} from './packings.js';
import {renderChart} from './chart.js';
import {renderMethodsDashboard, updateMethodsTiming, destroyMethodsDashboard} from './methods.js';
import {renderPopulationMap, destroyPopulationMap} from './population.js';
import {renderStorageSpace} from './storage-view.js';
import {renderPopulationPreview, destroyPopulationPreview} from './population-preview.js';
import {learningHTML} from './learning.js';
import {renderLLMCalls} from './llm_calls.js';
import {renderWorkFlow, destroyWorkFlow} from './workflow.js';
import {architectureGraphHTML, bindArchitectureGraph, updateArchitectureGraphPhase} from './architecture.js';
import {renderEffort, effortDetailsHTML, publishedEffortHTML} from './effort.js';

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numeric = value => typeof value === 'number' && Number.isFinite(value);
const format = (value,digits=6) => numeric(value) ? value.toFixed(digits) : '—';
const percent = value => Math.abs(value).toFixed(Math.abs(value)>0&&Math.abs(value)<.01?6:2);
const toleranceLabel = value => numeric(value)?(value===0?'τ = 0 (strict)':'τ = '+value.toExponential().replace('e-0','e-')):String(value||'Not specified');
const sourceLink = (url,label) => {try{const parsed=new URL(url);if(['https:','http:'].includes(parsed.protocol))return '<a href="'+esc(parsed.href)+'" target="_blank" rel="noopener noreferrer">'+esc(label||'Source')+' ↗</a>';}catch{}return esc(label||'Source unavailable');};
const delta = value => numeric(value) ? (value>0?'+':'')+(Math.abs(value)<.00001&&value!==0?value.toExponential(3):value.toFixed(6)) : '—';
const short = (value,n=12) => String(value ?? '').slice(0,n);
const plural = (n,forms) => forms[n===1?0:1];
const MAX_ROWS = 600;
const state = {runs:[],runId:null,snapshot:null,contentVersion:null,tab:'trials',axis:'iteration',selected:null,follow:true,stream:null,query:'',limit:60,codeMode:'diff',detail:null,detailKey:null,detailPending:null,detailRequest:0,refreshing:false,listRequest:0,listUnavailable:false,runRequest:0,timingReceivedAt:null,timingAdvance:0,timingConnected:false};
const scientificIdentity = snapshot => JSON.stringify([snapshot?.run?.id,snapshot?.run?.run_id,snapshot?.run?.task_hash]);
const sourceIdentity = () => JSON.stringify([scientificIdentity(state.snapshot),state.contentVersion,state.selected]);
const statuses = {running:['Running','success'],starting:['Starting','blue'],stale:['Heartbeat stale','warning'],stalled:['Heartbeat stale','warning'],interrupted:['Interrupted','warning'],completed:['Completed','neutral'],historical:['Archive · unfinished','neutral'],observing:['Waiting for events','blue'],success:['Evaluated','success'],evaluated:['Evaluated','success'],pending:['In progress','blue'],eval_fail:['Evaluation failed','negative'],timeout:['Timed out','warning'],nochild:['No candidate','neutral'],duplicate:['Duplicate','neutral'],failed:['Failed','negative'],invalid:['Rejected','negative'],SUPPORTED:['Supported','success'],CONFIRMED:['Forecast within interval','success'],REFUTED:['Forecast outside interval','negative'],INCONCLUSIVE:['Inconclusive','neutral'],active:['Active','success'],retired:['Retired','neutral']};
statuses.paused=['Paused','neutral'];statuses.stopped=['Stopped','neutral'];
statuses.remeasurement=['Remeasurement','blue'];
const phaseNames = {attempt:'Generation started',hypothesis:'Hypothesis recorded',outcome:'Evaluation received',conclusion:'Conclusion recorded',reflection:'Reflection recorded',reflection_context:'Context prepared',aux_start:'Analysis started',aux_result:'Analysis received',run_start:'Run started',run_end:'Run completed',iteration:'Candidate evaluated',checkpoint:'Checkpoint saved',checkpoint_restore:'Checkpoint restored',decision:'Strategy selected',population:'Population updated',sh_cut:'Islands updated',postmortem:'Failure analyzed',repeat_search:'Repeat evaluation'};
const badge = value => {const [label,kind]=statuses[value]||[value||'No data','neutral'];return '<span class="badge '+kind+'">'+esc(label)+'</span>';};
const key = trial => String(trial.candidate_id || trial.id);
const empty = (title,body='') => '<div class="empty-panel"><strong>'+esc(title)+'</strong>'+esc(body)+'</div>';
const hypothesisText = hypothesis => typeof hypothesis==='string'?hypothesis:(hypothesis?.text || hypothesis?.hypothesis || '');
const currentTrial = () => state.snapshot?.trials.find(t=>key(t)===state.selected);
const taskName = task => ({'oe/circle_packing':'Circle packing','oe/heilbronn_triangle':'Heilbronn triangle','oe/function_minimization_oracle':'Function minimization'}[task] || task || 'Experiment');
const runEffort = run => {const value=run.committed_effort;if(!value)return '<span class="run-effort">Effort not recorded</span>';const models=new Set(value.configured_models||[]);return '<span class="run-effort" title="'+esc(value.note)+'">'+esc(value.ordinary_iterations??'—')+' iterations · '+(numeric(value.known_llm_usd)?(value.cost_status==='known_logged_lower_bound'?'≥ ':'')+'$'+value.known_llm_usd.toFixed(2):'USD unknown')+' committed · '+(models.size||'unknown')+' configured LLMs</span>';};
const nameOf = run => {
  const path=run.path || run.name;
  const known=[['s04_r2_cycle','Research cycle · S04 r2'],['s04_cycle','Research cycle · S04'],['s05_r2_pair','Memory · S05 r2'],['s05_pair','Memory · S05'],['circle_body_engine_r2','Circle body · r2'],['circle_body_engine','Circle body']];
  const found=known.find(([part])=>path.includes(part));
  let name=found?found[1]:(run.name||'Experiment');
  if(path.includes('cards_off')) name+=' / OFF';
  if(path.includes('cards_on')) name+=' / ON';
  return name;
};

async function getJSON(url, options={}) {
  const response=await fetch(url,{...options,cache:'no-store'});
  if(!response.ok) throw new Error('Data is currently unavailable ('+response.status+').');
  return response.json();
}
function connection(text,kind) { state.timingConnected=kind==='connected';$('connection').textContent=text;$('connection-dot').className='connection-dot '+(kind||'');updatePopulationPreview();if(state.tab==='population')updatePopulationMap();if(state.tab==='workflow'&&state.snapshot?.kind!=='methods'&&state.snapshot?.run.kind!=='methods')renderWorkflow(); }
function showError(message) { $('error-banner').hidden=!message;$('error-banner').textContent=message||''; }
function preferredRun(runs) {
  const rank=run=>['running','starting','active'].includes(run.status)?2:/(^|\/)outputs\//.test(run.path||'')?1:0;
  return runs.slice().sort((a,b)=>rank(b)-rank(a)||String(b.last_modified||'').localeCompare(String(a.last_modified||'')))[0];
}

function renderRuns() {
  if(state.listUnavailable&&!state.runs.length){$('run-list').innerHTML='<div class="sidebar-empty">Run list unavailable. Retrying automatically.</div>';return;}
  const query=$('run-search').value.toLowerCase();
  const runs=state.runs.filter(run=>(nameOf(run)+' '+run.task+' '+run.path).toLowerCase().includes(query));
  $('run-count').textContent=state.runs.length;
  $('run-list').innerHTML=runs.map(run=>'<button class="run-item'+(run.id===state.runId?' selected':'')+'" data-run="'+esc(run.id)+'" '+(run.id===state.runId?'aria-current="true"':'')+'><span class="run-icon" aria-hidden="true">↗</span><span class="run-info"><span class="run-name">'+esc(nameOf(run))+'</span><span class="run-meta"><span class="run-state-dot '+(['running','starting'].includes(run.status)?'live':'')+'"></span>'+esc(statuses[run.status]?.[0]||'Archive')+' · '+(run.kind==='methods'?'Research labs':numeric(run.best_score)?format(run.best_score,4):'—')+'</span>'+runEffort(run)+'</span></button>').join('') || '<div class="sidebar-empty">'+(query?'No matching runs':'No runs yet')+'</div>';
}

function renderEmptyState(unavailable=false) {
  $('empty-title').textContent=unavailable?'Experiments are temporarily unavailable':'Watch your search unfold';
  $('empty-message').textContent=unavailable?'We could not reach the run monitor. We will keep trying, or you can retry now.':'Waiting for the first experiment log. New runs appear automatically.';
  $('empty-help').hidden=unavailable;
  $('empty-retry').hidden=!unavailable;
}

async function refreshRuns(initial=false) {
  const request=++state.listRequest;
  try {
    const result=await getJSON('/api/runs');
    if(request!==state.listRequest)return;
    if(state.listUnavailable){showError('');if(state.snapshot&&!state.follow)connection('Updates paused','');}
    state.listUnavailable=false;
    renderEmptyState();
    state.runs=result.runs;
    renderRuns();
    if(!state.runId && state.runs.length) {
      const requested=new URL(location.href).searchParams.get('run');
      const selected=state.runs.find(r=>r.id===requested)||preferredRun(state.runs);
      await selectRun(selected.id);
    }
    $('empty-state').hidden=!!state.runs.length;
    if(!state.runs.length){$('dashboard').hidden=true;connection('Waiting for a run','connected');}
  } catch(error) {
    if(request!==state.listRequest)return;
    state.listUnavailable=true;
    if(!state.runs.length&&!state.snapshot){
      renderRuns();renderEmptyState(true);
      $('dashboard').hidden=true;$('empty-state').hidden=false;
    }
    connection('Disconnected','error');
    showError('Unable to connect to the monitor. Reconnecting automatically.');
  }
}

async function selectRun(id) {
  const request=++state.runRequest;
  if(state.stream)state.stream.close();
  state.stream=null;
  state.detailRequest++;
  state.runId=id;state.snapshot=null;state.selected=null;state.detail=null;state.query='';state.limit=60;
  const url=new URL(location.href);url.searchParams.set('run',id);history.replaceState(null,'',url);
  renderRuns();
  showError('');
  $('dashboard').hidden=false;$('empty-state').hidden=true;
  destroyPopulation();
  destroyWorkflow();
  if(packingsMount){destroyPackings(packingsMount);packingsMount=null;}
  if($('methods-dashboard'))destroyMethodsDashboard($('methods-dashboard'));
  resetRunDisplay();
  $('run-title').textContent=nameOf(state.runs.find(r=>r.id===id)||{name:id,path:''});
  $('tab-content').innerHTML='<div class="loading">Loading run events…</div>';
  try {
    const snapshot=await getJSON('/api/runs/'+encodeURIComponent(id));
    if(state.runId!==id||state.runRequest!==request)return;
    applySnapshot(snapshot);
    showError('');
    if(state.follow)connectStream();
    else connection('Updates paused','');
  } catch(error) {if(state.runId===id&&state.runRequest===request){showError(error.message);$('tab-content').innerHTML=empty('Unable to load this run','Refresh to try again.');$('score-chart').innerHTML=empty('Run data unavailable');connection('No data','error');}}
}

function resetRunDisplay() {
  destroyPopulationPreview($('population-preview'));
  $('dashboard').dataset.kind='engine';
  if($('methods-dashboard'))$('methods-dashboard').hidden=true;
  for(const id of ['best-score','evaluations','lessons-count','cost','trials-tab-count','hypotheses-tab-count','lessons-tab-count','tools-tab-count','cells-tab-count','event-count']){$(id).textContent='—';$(id).removeAttribute('title');}
  for(const id of ['run-subtitle','score-gain','attempts','hypotheses-count','cost-note','run-path','selected-point-label','chart-start','chart-end'])$(id).textContent='';
  $('run-task').textContent='EXPERIMENT';$('run-status').innerHTML=badge('pending');
  $('best-score-label').textContent='Best score';$('best-score-comparison').hidden=true;
  $('best-score-comparison').textContent='';document.querySelector('.metrics').classList.remove('has-reference');
  $('run-note').hidden=true;$('runtime-bar').hidden=true;
  $('timing-bar').hidden=true;
  if($('benchmark-comparison'))$('benchmark-comparison').hidden=true;
  $('score-chart').innerHTML=empty('Loading run data…');if($('chart-outcomes')){$('chart-outcomes').replaceChildren();$('chart-outcomes').hidden=true;}$('activity-feed').innerHTML=empty('Loading events…');
  $('chart-subtitle').textContent='Score by iteration';
}

function connectStream() {
  if(state.stream)state.stream.close();
  if(!state.follow||!state.runId)return;
  const runId=state.runId;
  connection('Connecting…','');
  const source=new EventSource('/api/stream?run='+encodeURIComponent(runId));state.stream=source;
  source.onopen=()=>{if(state.stream===source){connection('Connected','connected');showError('');}};
  source.addEventListener('snapshot',event=>{
    if(state.stream!==source||state.runId!==runId||!state.follow)return;
    try{applySnapshot(JSON.parse(event.data));connection('Connected','connected');showError('');}
    catch(error){showError('Unable to display the update. Previous data is still available.');console.error(error);}
  });
  source.addEventListener('runtime',event=>{
    if(state.stream!==source||state.runId!==runId||!state.follow)return;
    try{applyRuntime(JSON.parse(event.data));connection('Connected','connected');showError('');}
    catch(error){console.error(error);}
  });
  source.addEventListener('unavailable',()=>{if(state.stream!==source||state.runId!==runId||!state.follow)return;connection('Journal unavailable','error');showError('The run journal is no longer available. Refresh the run list.');source.close();});
  source.onerror=()=>{if(state.stream===source&&state.follow){connection('Reconnecting…','error');}};
}

function applySnapshot(snapshot) {
  const previous=state.snapshot;
  // New servers send runtime separately. A bounded signature also accommodates
  // older heartbeat snapshots without serializing the full journal twice.
  const content=data=>data.content_version??JSON.stringify([data.run?.run_id,data.stats,
    ...['trials','hypotheses','lessons','events','curves'].map(k=>[data[k]?.length,data[k]?.at(-1)]),data.architecture,data.research_tools?.summary,data.research_tools?.events?.at(-1)]);
  const changed=!previous||content(previous)!==content(snapshot)||JSON.stringify(previous.stats)!==JSON.stringify(snapshot.stats)||JSON.stringify(previous.benchmark)!==JSON.stringify(snapshot.benchmark);
  const changedIdentity=previous&&scientificIdentity(previous)!==scientificIdentity(snapshot);
  const jobsChanged=previous?.research_tools?.jobs?.version!==snapshot.research_tools?.jobs?.version;
  const cellsChanged=previous?.research_tools?.pending_cells?.version!==snapshot.research_tools?.pending_cells?.version||previous?.research_tools?.pending_cells?.run_status!==snapshot.research_tools?.pending_cells?.run_status;
  if(changed||changedIdentity){state.detail=null;state.detailKey=null;state.detailPending=null;state.detailRequest++;}
  if(changedIdentity){state.selected=null;state.query='';}
  const phaseChanged=previous?.runtime?.stage!==snapshot.runtime?.stage||previous?.runtime?.active!==snapshot.runtime?.active;
  state.snapshot=snapshot;
  state.timingReceivedAt=performance.now();state.timingAdvance=0;
  state.contentVersion=content(snapshot);
  const index=state.runs.findIndex(r=>r.id===snapshot.run.id);
  if(index>=0){state.runs[index]=snapshot.run;renderRuns();}
  const methods=snapshot.kind==='methods'||snapshot.run.kind==='methods';
  $('dashboard').dataset.kind=methods?'methods':'engine';
  if($('methods-dashboard'))$('methods-dashboard').hidden=!methods;
  if(methods){destroyPopulationPreview($('population-preview'));destroyWorkflow();if(packingsMount)suspendPackings(packingsMount);renderMethodsRun();return;}
  if(!state.selected) {
    const evaluated=snapshot.trials.filter(t=>numeric(t.score)&&t.code_available);
    const best=evaluated.reduce((a,b)=>!a||b.score>a.score?b:a,null);
    state.selected=best?key(best):(snapshot.trials[0]?key(snapshot.trials[0]):null);
  }
  renderSummary();renderRuntime();renderTiming();renderBenchmark();
  updatePopulationPreview();
  if(changed||changedIdentity){renderActivity();renderTab();}
  else if(state.tab==='workflow')renderWorkflow();
  else if(state.tab==='tools'&&jobsChanged)renderTools();
  else if(state.tab==='research-cells'&&(jobsChanged||cellsChanged))renderCells();
  else if(state.tab==='architecture'&&phaseChanged)renderArchitecturePhase();
  else if(state.tab==='population')updatePopulationMap();
  if(changed||changedIdentity)renderPlot();
}

function applyRuntime(update) {
  if(!state.snapshot||update.run?.id!==state.runId)return;
  if(state.snapshot.kind==='methods'||state.snapshot.run.kind==='methods'){
    Object.assign(state.snapshot.run,update.run);state.snapshot.runtime=update.runtime;
    if(update.timing)state.snapshot.timing=update.timing;
    renderMethodsRun();return;
  }
  const changed=state.snapshot.run.status!==update.run.status||state.snapshot.run.status_reason!==update.run.status_reason||state.snapshot.run.stop_detail!==update.run.stop_detail;
  Object.assign(state.snapshot.run,{status:update.run.status,status_reason:update.run.status_reason,stop_detail:update.run.stop_detail});
  state.snapshot.runtime=update.runtime;
  if(update.effort){state.snapshot.effort=update.effort;renderBenchmark();}
  if(update.research_tool_jobs&&state.snapshot.research_tools){
    const changed=state.snapshot.research_tools.jobs?.version!==update.research_tool_jobs.version;
    state.snapshot.research_tools.jobs=update.research_tool_jobs;
    if(changed&&state.tab==='tools')renderTools();
    if(changed&&state.tab==='research-cells')renderCells();
  }
  if(update.research_pending_cells&&state.snapshot.research_tools){
    const prior=state.snapshot.research_tools.pending_cells,next=update.research_pending_cells;
    state.snapshot.research_tools.pending_cells=next;
    if((prior?.version!==next.version||prior?.run_status!==next.run_status)&&state.tab==='research-cells')renderCells();
  }
  if(update.timing){state.snapshot.timing={...state.snapshot.timing,...update.timing};state.timingReceivedAt=performance.now();state.timingAdvance=0;}
  if(changed){
    const run=state.runs.find(r=>r.id===state.runId);
    if(run)Object.assign(run,{status:update.run.status,status_reason:update.run.status_reason});
    renderSummary();renderRuns();
  }else renderSpend();
  renderRuntime();renderTiming();
  // Runtime-only status changes can end the live pulse without rebuilding the
  // graph, its pinned program card, or the source inspector.
  $('score-chart').querySelector('svg')?.classList.toggle('is-live',update.runtime?.active===true);
  if(state.tab==='architecture')renderArchitecturePhase();
  if(state.tab==='population')updatePopulationMap();
  if(state.tab==='workflow')renderWorkflow();
}

function renderMethodsRun() {
  const snapshot=state.snapshot,run=snapshot.run;
  $('run-title').textContent=nameOf(run);
  $('run-task').textContent='RESEARCH PRACTICES / LABORATORIES';
  $('run-status').innerHTML=badge(run.status);
  $('run-subtitle').textContent=[run.task||'Research campaign',snapshot.methods?.identity?.generator?.model||run.models?.[0],run.status_reason].filter(Boolean).join(' · ');
  $('run-path').textContent=run.path||'';
  const warnings=(snapshot.warnings||[]).map(value=>typeof value==='string'?value:value.message||JSON.stringify(value));
  $('run-note').hidden=!warnings.length;$('run-note').textContent=warnings.join(' ');
  let root=$('methods-dashboard');
  if(!root){root=document.createElement('section');root.id='methods-dashboard';root.className='methods-dashboard';root.setAttribute('aria-label','Research labs dashboard');document.querySelector('.page-heading').after(root);}
  root.hidden=false;
  renderMethodsDashboard(root,snapshot,{fetchJSON:getJSON,follow:state.follow,connected:state.timingConnected});
}

function metricLabel() {
  const label=state.snapshot?.benchmark?.metric||state.snapshot?.metric_display?.label||'Score';
  // Keep recorded identifiers untouched; captions turn generic case keys into
  // readable labels without rewriting acronyms or assigning task semantics.
  const words=String(label).replace(/_/g,' ').trim();
  return words?words[0].toUpperCase()+words.slice(1):'Score';
}
function metricDisplay(row,field='metric_display',scoreKey='score') {
  const view=row?.[field];
  if(view?.schema==='sciel-metric-display/1'){
    if(numeric(row?.[scoreKey])&&numeric(view.raw_score)&&row[scoreKey]!==view.raw_score)
      return {...view,status:'unknown',value:null,reason:'Score and measurement binding differ'};
    return view;
  }
  // An older response may expose only controller scores. Never reinterpret
  // those as a physical measurement just because a benchmark is configured.
  const raw=row?.[scoreKey];
  const rawOnly=!state.snapshot?.metric_display&&!state.snapshot?.benchmark;
  return {status:rawOnly&&numeric(raw)?'measured':'unknown',value:rawOnly&&numeric(raw)?raw:null,
    label:rawOnly?'Score':metricLabel(),raw_score:numeric(raw)?raw:null,
    metric_sha256:rawOnly?'legacy-raw-score':null,reason:'Measurement metadata not recorded'};
}
function measuredValue(view) {return view?.status==='measured'&&numeric(view.value)?view.value:null;}
function metricStatus(view) {return {invalid_penalty:'Invalid result',failed:'Evaluation failed',unknown:'Not measured'}[view?.status]||'Measured';}
function metricText(view,digits=6) {
  if(measuredValue(view)!==null)return format(view.value,digits);
  const raw=numeric(view?.raw_score)?' ('+(view.status==='invalid_penalty'?'penalty score ':'raw score ')+format(view.raw_score,digits)+')':'';
  return metricStatus(view)+raw;
}
function metricHTML(view,digits=6) {
  if(measuredValue(view)!==null)return esc(format(view.value,digits));
  const raw=numeric(view?.raw_score)?'<small>'+(view.status==='invalid_penalty'?'Penalty score ':'Raw score ')+esc(format(view.raw_score,digits))+'</small>':'';
  return '<span class="metric-outcome '+(view?.status==='invalid_penalty'||view?.status==='failed'?'negative-text':'')+'" title="'+esc(view?.reason||'')+'">'+esc(metricStatus(view))+raw+'</span>';
}
function metricDifference(child,parent) {
  return measuredValue(child)!==null&&measuredValue(parent)!==null&&child.metric_sha256&&child.metric_sha256===parent.metric_sha256?child.value-parent.value:null;
}
function trialDifference(row) {return metricDifference(metricDisplay(row),metricDisplay(row,'parent_metric_display','parent_score'));}
function metricBadge(row) {
  const view=metricDisplay(row);
  return view.status==='invalid_penalty'?'<span class="badge negative">Invalid result · penalty</span>':view.status==='failed'?badge('eval_fail'):view.status==='unknown'&&row.status==='evaluated'?'<span class="badge neutral">Measurement unavailable</span>':badge(row.status);
}

function renderSummary() {
  const {run,stats,warnings=[]}=state.snapshot;
  $('run-title').textContent=nameOf(run);
  $('run-task').textContent=taskName(run.task).toUpperCase()+' / EXPERIMENT';
  $('run-status').innerHTML=badge(run.status);
  const start=state.snapshot.events.find(e=>e.event==='run_start')?.data || {};
  const models=run.models || start.models || [];
  const seed=run.seed ?? start.seed;
  const parts=[taskName(run.task),...(seed!==undefined?['seed '+seed]:[]),...(models.length?[models[0].split('/').at(-1)]:[])];
  $('run-subtitle').textContent=parts.join('  ·  ');
  const reference=state.snapshot.benchmark;
  const bestDisplay=metricDisplay(stats,'best_metric_display','best_score'),value=measuredValue(bestDisplay);
  $('best-score-label').textContent=metricLabel();
  $('best-score').textContent=numeric(value)?format(value):metricStatus(bestDisplay);
  $('best-score').title=numeric(value)?String(value):metricText(bestDisplay);
  const comparison=$('best-score-comparison');
  const gaps=[reference?.best_known,reference?.best_ai_method].filter(item=>item?.status==='known'&&item.current_value===value&&numeric(value)&&numeric(item.value)&&item.value>0&&numeric(reference?.run_tolerance)&&item.tolerance===reference.run_tolerance);
  comparison.hidden=!gaps.length;
  document.querySelector('.metrics').classList.toggle('has-reference',!comparison.hidden);
  comparison.textContent='';
  if(!comparison.hidden){
    comparison.innerHTML=gaps.map(item=>{const gap=(item.value-value)/item.value*100;return '<span class="benchmark-reference-gap">| '+percent(gap)+'% '+(gap>=0?'below':'above')+' '+esc(item.label||'Published reference')+' · '+esc(item.name)+'</span>';}).join('');
    comparison.title='Comparable published values at the recorded task tolerance. '+(reference.note||'');
  }
  const gain=metricDifference(bestDisplay,metricDisplay(stats,'seed_metric_display','seed_score'));
  $('score-gain').textContent=numeric(gain)?(gain>0?'↗ ':'')+delta(gain)+' from initial program':'Measured gain unavailable';
  $('score-gain').className='metric-foot'+(gain>0?' positive':'');
  $('evaluations').textContent=stats.evaluations ?? '—';
  $('evaluations').title='Successful ordinary search evaluations, including successful remeasurements. Excludes seed, bootstrap and failed evaluations.';
  const attempts=stats.attempts ?? stats.iterations ?? 0,iterations=stats.iterations ?? 0,hypotheses=stats.hypotheses ?? 0,reflections=stats.reflections ?? 0;
  $('attempts').textContent=attempts+' '+plural(attempts,['attempt','attempts'])+' · '+iterations+' '+plural(iterations,['iteration','iterations'])+
    (numeric(stats.remeasurements)?' · '+stats.remeasurements+' '+plural(stats.remeasurements,['remeasurement','remeasurements']):'')+
    (numeric(stats.measured_results)?' · '+stats.measured_results+' measured results':'')+
    (numeric(stats.repeated_outputs)?' · '+stats.repeated_outputs+' exact output repeats':'');
  $('attempts').title='Measured results include seeds, bootstrap, failed evaluations and evaluated retries. Exact output repeats compare saved outputs under a compatible protocol; they do not prove equivalent algorithms.';
  const memory=state.snapshot.reliability?.memory,stored=memory?memory.stored_active:stats.lessons;
  $('lessons-count').textContent=stored ?? '—';
  $('lessons-unit').textContent=plural(stored,['lesson','lessons']);
  const researchCounts=hypotheses+' '+plural(hypotheses,['hypothesis','hypotheses'])+' · '+reflections+' '+plural(reflections,['reflection attempt','reflection attempts']);
  $('hypotheses-count').textContent=researchCounts+(memory?.latest?' · '+(numeric(memory.latest.delivered)?memory.latest.delivered+' delivered in latest prompt':'Latest delivery not recorded'):'');
  renderSpend();
  $('trials-tab-count').textContent=state.snapshot.trials.length;
  $('tools-tab-count').textContent=state.snapshot.research_tools?.summary?.versions??0;
  $('cells-tab-count').textContent=state.snapshot.research_tools?.summary?.cells??0;
  $('hypotheses-tab-count').textContent=state.snapshot.hypotheses.length;
  $('lessons-tab-count').textContent=state.snapshot.lessons.length;
  $('event-count').textContent=state.snapshot.events.length;
  $('run-path').textContent=run.path;
  const notes=[];
  const protocol=state.snapshot.start_protocol;
  if(protocol?.label)notes.push(protocol.label+(protocol.portfolio_seed===true?' · portfolio seeding enabled':'')+(protocol.source_candidate?' · source '+protocol.source_candidate:'')+'.');
  if(run.stop_detail)notes.push('Stopped: '+run.stop_detail);
  if(run.engineering_only || run.scope==='engineering' || (run.path||'').includes('s04_'))notes.push('Engineering run: validating the research cycle. These results are not a comparison of method performance.');
  if(warnings.length)notes.push(warnings.map(w=>typeof w==='string'?w:(w.message||JSON.stringify(w))).join(' '));
  $('run-note').hidden=!notes.length;$('run-note').textContent=notes.join(' ');
}

function renderSpend() {
  const {stats,runtime}=state.snapshot, pending=runtime?.uncommitted_cost;
  const physical=state.snapshot.effort?.total;
  if(physical){
    const partial=physical.status!=='complete';
    $('cost').textContent=(partial&&numeric(physical.reported_usd)?'≥ ':'')+(numeric(physical.reported_usd)?'$'+physical.reported_usd.toFixed(4):'Unknown');
    $('cost-note').textContent=String(physical.physical_llm_calls)+' completed physical LLM calls'+(physical.pending_llm_calls?' · '+physical.pending_llm_calls+' pending':'')+(physical.unknown_cost_calls?' · '+physical.unknown_cost_calls+' charges unknown':'');
    $('cost').title='Receipt-backed cumulative run spend. '+state.snapshot.effort.note;
    return;
  }
  let value=stats.cost_total,partial=stats.cost_status==='known_logged_lower_bound';
  let note=stats.cost_status==='estimated'?'Estimated from token rates':partial?'Partial recorded spend':'Generation and analysis';
  let title=stats.cost_status==='estimated'?'Estimated LLM spend from uncached token rates; actual billed cost may differ.':'Recorded LLM spend; excludes compute infrastructure costs.';
  if(pending?.available===true){
    value=pending.known_spend;
    partial ||= pending.unknown_call_count>0||pending.pending_call_count>0;
    const money=n=>numeric(n)?'$'+n.toFixed(4):'unknown';
    note=money(pending.baseline_cost)+' committed + '+money(pending.known_cost)+' uncommitted';
    if(pending.unknown_call_count>0)note+=' · '+pending.unknown_call_count+' unknown-cost calls';
    if(pending.pending_call_count>0)note+=' · '+pending.pending_call_count+' awaiting receipts';
    if(stats.cost_status==='estimated')note+=' · token-rate estimate';
    title='Known spend includes authenticated receipts from unpublished wave '+pending.wave+'. Scientific progress remains at the committed checkpoint. Unknown and pending charges are not estimated.';
  }else if(pending?.available===false){
    partial=true;note='Committed spend · current wave cost unavailable';title=pending.reason||'Current wave receipts are not yet verifiable.';
  }
  $('cost').textContent=(partial&&numeric(value)?'≥ ':'')+(numeric(value)?'$'+value.toFixed(4):'—');
  $('cost-note').textContent=note;$('cost').title=title;
}

function elapsed(seconds) {
  if(!numeric(seconds))return 'Not recorded';
  const value=Math.max(0,Math.floor(seconds));
  return value<60?value+'s':value<3600?Math.floor(value/60)+'m '+value%60+'s':Math.floor(value/3600)+'h '+Math.floor(value%3600/60)+'m';
}
function clockDuration(seconds) {
  if(!numeric(seconds))return '—';
  const total=Math.max(0,Math.floor(seconds)),h=Math.floor(total/3600),m=Math.floor(total%3600/60),s=total%60;
  return [h,m,s].map(value=>String(value).padStart(2,'0')).join(':');
}
function renderTiming() {
  if(state.snapshot?.kind==='methods'||state.snapshot?.run.kind==='methods'){updateMethodsTiming($('methods-dashboard'),{follow:state.follow,connected:state.timingConnected});return;}
  const timing=state.snapshot?.timing,bar=$('timing-bar');
  bar.hidden=!timing;
  if(!timing)return;
  const runtime=state.snapshot.runtime;
  if(timing.live===true&&runtime?.active===true&&state.follow&&state.timingConnected&&numeric(state.timingReceivedAt)){
    // Interpolate between small SSE frames using the browser's monotonic clock,
    // and stop at the heartbeat freshness boundary if updates disappear.
    const freshness=numeric(runtime.stale_after_seconds)&&numeric(runtime.heartbeat_age_seconds)?Math.max(0,runtime.stale_after_seconds-runtime.heartbeat_age_seconds):0;
    state.timingAdvance=Math.max(state.timingAdvance,Math.min(freshness,Math.max(0,(performance.now()-state.timingReceivedAt)/1000)));
  }
  const advance=timing.live===true?state.timingAdvance:0;
  $('run-elapsed').textContent=clockDuration(numeric(timing.session?.elapsed_seconds)?timing.session.elapsed_seconds+advance:null);
  $('hypothesis-age').textContent=clockDuration(numeric(timing.last_hypothesis_age_seconds)?timing.last_hypothesis_age_seconds+advance:null);
  $('hypothesis-interval').textContent=clockDuration(timing.intervals?.last_seconds);
  $('hypothesis-median').textContent=clockDuration(timing.intervals?.median_seconds);
  $('hypothesis-interval-count').textContent=(timing.intervals?.count||0)+' measured intervals';
  const last=timing.hypotheses?.at(-1);
  $('last-hypothesis-id').textContent=('last_hypothesis_id' in timing?timing.last_hypothesis_id:last?.experiment_id)||'Not recorded in this session';
  const observed=!String(timing.intervals?.source||'').startsWith('recorded')&&last?.source!=='recorded';
  const start=timing.observed_since?new Date(timing.observed_since).toLocaleTimeString():null;
  $('timing-note').textContent=(observed?'Hypothesis arrival times observed by the monitor'+(start?' since '+start:'')+'. Polling resolution: about 2 seconds.':'Hypothesis intervals use recorded engine timestamps.')+' Intervals exclude pauses between sessions.'+(timing.live===false?' Timers are frozen at the last recorded boundary.':'')+((timing.coverage?.untimed_hypotheses||0)>0?' Earlier hypothesis timings were not recorded.':'')+((timing.coverage?.gaps?.length||0)>0?' Gaps in monitoring are excluded.':'');
}
function renderRuntime() {
  if(!state.snapshot)return;
  if(state.snapshot.kind==='methods'||state.snapshot.run.kind==='methods')return;
  const runtime=state.snapshot.runtime,bar=$('runtime-bar');
  bar.hidden=false;
  if(!runtime?.available){bar.innerHTML='<span class="runtime-indicator"></span><span class="runtime-label">Runtime not recorded</span><span class="runtime-detail">This journal has no verified engine heartbeat.</span>';return;}
  const stages={starting:'Starting engine',seeding:'Evaluating seed programs',generating:'Generating a candidate',evaluating:'Evaluating a candidate',research:'Updating research knowledge',checkpointing:'Saving checkpoint',finished:'Run finished'};
  const fresh=runtime.active===true;
  const parallelStages={bootstrap:'Initializing portfolio wave',generation:'Generating candidate wave',conclusion:'Writing conclusions',reflection:'Reflecting on wave evidence',commit:'Committing wave',paused:'Parallel wave paused'};
  const portfolio=runtime.parallel?.portfolio;
  const interleavedPhase=portfolio?.policy==='interleaved'&&['bootstrap','generation'].includes(runtime.parallel?.phase)?({canonical_seed:'Evaluating seed programs',portfolio:portfolio.attempted===0?'Creating the initial search batch':'Adding fresh starts',evolution:'Evolving initialized islands'}[portfolio.wave_kind]):null;
  const phase=interleavedPhase||parallelStages[runtime.parallel?.phase]||stages[runtime.stage]||runtime.stage||'Stage not recorded';
  const heartbeat=runtime.heartbeat_at?new Date(runtime.heartbeat_at).toLocaleString():'Not recorded';
  const observed=state.follow?'':'<span class="badge warning">View paused</span>';
  bar.innerHTML='<span class="runtime-indicator '+(fresh?'live':'')+'"></span><span class="runtime-label">'+esc(phase)+'</span>'+observed+'<span class="runtime-detail" title="'+esc(heartbeat)+'">Heartbeat '+(numeric(runtime.heartbeat_age_seconds)?esc(elapsed(runtime.heartbeat_age_seconds))+' ago':esc(heartbeat))+'</span>'+(runtime.pid?'<span class="runtime-detail mono">PID '+esc(runtime.pid)+'</span>':'')+'<span class="runtime-reason">'+esc(runtime.reason||'')+'</span>';
  const parallel=runtime.parallel;
  if(parallel?.schema==='sciel-parallel-runtime/1'){
    const count=value=>numeric(value)?String(value):'unknown';
    const detail=document.createElement('span');detail.className='runtime-detail runtime-parallel';
    detail.title='Submitted calls include host-queued work; these are not measured executing slots.';
    detail.textContent=(fresh?'':'Recorded · ')+'Wave '+count(parallel.wave)+' · '+(parallel.phase||'phase unknown')+' · '+count(parallel.workers)+' workers · pending LLM '+count(parallel.pending_llm_calls)+' / evaluation '+count(parallel.pending_evaluations)+(Object.hasOwn(parallel,'pending_tool_calls')?' / tool '+count(parallel.pending_tool_calls):'');
    bar.append(detail);
    if(portfolio?.policy==='interleaved'){
      const progress=document.createElement('span');progress.className='runtime-detail runtime-portfolio';
      progress.title=portfolio.scope||'Committed attempts include failed fresh starts; they are not successful candidates.';
      progress.textContent=(fresh?'':'Recorded · ')+({canonical_seed:'Seed evaluation · ',portfolio:'Fresh-start wave · ',evolution:'Evolution wave · '}[portfolio.wave_kind]||'')+'Initial batch '+count(portfolio.initial_batch_attempted)+'/'+count(portfolio.initial_batch_total)+' attempted · Fresh starts '+count(portfolio.attempted)+'/'+count(portfolio.total)+' · '+count(portfolio.remaining)+' remaining'+(numeric(portfolio.eligible_islands)?' · '+count(portfolio.eligible_islands)+' islands eligible for evolution':'')+(parallel.phase==='commit'&&portfolio.next_kind?' · Next '+(portfolio.next_kind==='portfolio'?'fresh starts':'evolution'):'');
      bar.append(progress);
    }
  }
}

function renderBenchmark() {
  let panel=$('benchmark-comparison');
  if(!panel){panel=document.createElement('section');panel.id='benchmark-comparison';panel.className='benchmark-comparison';panel.setAttribute('aria-label','Published reference and effort comparison');document.querySelector('.metrics').after(panel);}
  const reference=state.snapshot.benchmark,effort=state.snapshot.effort;
  const start=state.snapshot.events.find(e=>e.event==='run_start')?.data||{};
  const target=reference?.task_target??start.known_best;
  panel.hidden=!reference&&!numeric(target)&&!effort;
  const referenceOpen=panel.querySelector('.benchmark-disclosure')?.open===true;
  const disclosureKey=node=>JSON.stringify([node.closest('tr')?.querySelector('td')?.textContent||node.closest('section')?.querySelector('.effort-title')?.textContent||'reference',node.querySelector('summary')?.textContent]);
  const openDetails=new Set([...panel.querySelectorAll('details[open]')].map(disclosureKey));
  const current=measuredValue(metricDisplay(state.snapshot.stats,'best_metric_display','best_score'));
  const bound=reference?.current_value===current&&numeric(current)&&numeric(reference?.run_tolerance);
  let html='';
  if(reference&&numeric(reference.value)){
    const comparable=bound&&reference.reference_tolerance===reference.run_tolerance;
    const gap=comparable?current-reference.value:null;
    html='<div class="benchmark-heading"><strong>'+esc(reference.label||'Published reference')+'</strong>'+sourceLink(reference.source_url,reference.source_label||'Published source')+'</div><div class="benchmark-values"><div>This run<strong>'+format(current,9)+'</strong></div><div>'+esc(reference.metric||'Reference value')+'<strong>'+format(reference.value,9)+'</strong></div><div>Gap to reference<strong>'+delta(gap)+'</strong></div><div>Of reference<strong>'+(comparable&&reference.value!==0?(current/reference.value*100).toFixed(4)+'%':'—')+'</strong></div></div>';
    if(reference.note)html+='<p class="benchmark-note">'+esc(reference.note)+'</p>';
    const rows=(reference.references||[]).map(row=>({...row}));
    if(bound)rows.push({current:true,name:'Current solution · '+(state.snapshot.best_candidate_id||'ID not recorded'),value:current,tolerance:reference.run_tolerance});
    // Only the tolerance-matched group is ordered together. Other protocols
    // remain visibly separate; this table is not a cross-protocol ranking.
    const comparableRows=rows.filter(row=>row.tolerance===reference.run_tolerance).sort((a,b)=>(numeric(b.value)?b.value:-Infinity)-(numeric(a.value)?a.value:-Infinity));
    const otherRows=rows.filter(row=>row.tolerance!==reference.run_tolerance);
    const renderRow=row=>{
      if(row.current)return '<tr class="benchmark-current" data-program-id="'+esc(state.snapshot.best_candidate_id||'')+'"><td>'+esc(row.name)+'<small>Canonical evaluator · current best</small></td><td class="number published-value">'+esc(String(current))+'</td><td>'+esc(toleranceLabel(row.tolerance))+'</td><td>This run</td><td>'+effortDetailsHTML(effort?.to_best)+'</td><td>Saved measurement<small>Effort cutoff: evaluation completion</small></td></tr>';
      const match=bound&&row.tolerance===reference.run_tolerance;
      const kind={ai_search_framework:'AI search',ai_assisted:'AI-assisted',unknown:'Method not classified'}[row.method_classification]||'Method not classified';
      return '<tr><td>'+esc(row.name)+'<small>'+kind+'</small></td><td class="number published-value">'+esc(row.value_label||String(row.value))+'</td><td>'+esc(toleranceLabel(row.tolerance))+'</td><td class="number">'+(match&&numeric(row.gap_percent)?percent(row.gap_percent)+'% '+(row.gap_percent>=0?'below':'above'):'Different tolerance / comparison unavailable')+'</td><td>'+publishedEffortHTML(row.effort)+'</td><td>'+sourceLink(row.source_url,row.source_name)+'<small>'+esc(row.status||'')+'</small>'+(row.effort?.source_url?sourceLink(row.effort.source_url,'Effort source'):'')+'</td></tr>';
    };
    if(rows.length)html+='<div class="table-wrap benchmark-table"><table><thead><tr><th>Result</th><th>'+esc(reference.metric||'Native metric')+'</th><th>Constraint tolerance</th><th>This run vs reference</th><th>Discovery effort</th><th>Evidence</th></tr></thead><tbody>'+comparableRows.map(renderRow).join('')+otherRows.map(renderRow).join('')+'</tbody></table></div>';
  }
  if(html)html='<details class="benchmark-disclosure"'+(referenceOpen?' open':'')+'><summary>'+esc(reference.label||'Tolerance-matched reference')+'</summary>'+html+'</details>';
  if(effort)html+=renderEffort(effort);
  if(numeric(target))html+='<div class="benchmark-target"><span>Task target'+(reference?.target_metric?' · '+esc(reference.target_metric):'')+'</span><strong>'+esc(target)+'</strong><span>Recorded task target; separate from the published reference.</span></div>';
  panel.innerHTML=html;
  panel.querySelectorAll('details').forEach(node=>{if(openDetails.has(disclosureKey(node)))node.open=true;});
}

function renderArchitecturePhase() {
  const runtime=state.snapshot?.runtime;
  if(document.querySelector('.architecture-map')){
    updateArchitectureGraphPhase($('tab-content'),runtime);
    return;
  }
  const current=runtime?.active===true?({generating:'generation',evaluating:'evaluation'}[runtime.stage]):null;
  document.querySelectorAll('.architecture-stage').forEach(node=>{
    const active=node.dataset.stage===current;
    node.classList.toggle('current',active);
    const status=node.querySelector('.stage-status');
    if(status)status.textContent=active?'Current phase':node.classList.contains('enabled')?'Enabled':node.classList.contains('disabled')?'Disabled':'Not recorded';
  });
}

function architectureValue(field) {
  if(field.status==='unknown'||field.value===undefined)return '<span class="architecture-unknown">Not recorded</span>';
  if(field.value===null&&['budget','max_iterations','research.max_aux_calls'].includes(field.key))return '<span>Unlimited</span>';
  if(field.value===null)return '<span class="architecture-unknown">Not set</span>';
  const value=field.value;
  if(typeof value==='boolean')return '<span class="configuration-flag '+(value?'enabled':'disabled')+'">'+(value?'Enabled':'Disabled')+'</span>';
  const display=item=>item&&typeof item==='object'?(item.model?item.model+(item.weight!==undefined?' (weight '+item.weight+')':''):Object.entries(item).map(([key,value])=>key+': '+(value&&typeof value==='object'?JSON.stringify(value):String(value))).join(' · ')):String(item);
  const text=Array.isArray(value)?(value.length?value.map(display).join(' · '):'None'):display(value);
  return '<span>'+esc(text)+'</span>';
}
function renderArchitecture() {
  const architecture=state.snapshot.architecture;
  if(!architecture){$('tab-content').innerHTML=empty('Architecture not recorded','This run has no saved configuration. Current defaults are not substituted for missing values.');return;}
  const previousSelection=document.querySelector('.architecture-map')?.dataset.selectedNode;
  const configurationOpen=document.querySelector('.architecture-configuration')?.open;
  const inactiveOpen=document.querySelector('.graph-inactive')?.open;
  const stages=architecture.stages||[],primary=stages.filter(stage=>!['conclusion','reflection','retrieval'].includes(stage.id)),feedback=stages.filter(stage=>['conclusion','reflection','retrieval'].includes(stage.id));
  const runtimeStage=state.snapshot.runtime?.active===true?({generating:'generation',evaluating:'evaluation'}[state.snapshot.runtime.stage]):null;
  const stageHTML=(stage,index)=>{
    const status=['enabled','disabled'].includes(stage.status)?stage.status:'unknown';
    const statusText={enabled:'Enabled',disabled:'Disabled',unknown:'Not recorded'}[status];
    return '<li class="architecture-stage '+status+(runtimeStage===stage.id?' current':'')+'" data-stage="'+esc(stage.id)+'"><div class="stage-top"><span class="stage-number">'+String(index+1).padStart(2,'0')+'</span><span class="stage-status">'+(runtimeStage===stage.id?'Current phase':statusText)+'</span></div><h3>'+esc(stage.label)+'</h3><p>'+esc(stage.description||'')+'</p></li>';
  };
  let html='<div class="architecture"><div class="architecture-heading"><div><h2>Architecture of this run</h2><p>'+esc(architecture.graph?'What runs at each step, and what changes after an experiment.':architecture.summary||'Configuration saved with the selected experiment.')+'</p></div><span class="badge '+(architecture.recorded?'success':'neutral')+'">'+(architecture.recorded?'Recorded configuration':'Configuration unavailable')+'</span></div>';
  if(architecture.graph)html+=architectureGraphHTML(architecture.graph);
  else{
    html+='<div class="architecture-diagram" aria-label="Recorded engine pipeline"><div class="architecture-lane-label">Program evolution</div><ol class="architecture-flow">'+primary.map(stageHTML).join('')+'</ol>';
    if(feedback.length)html+='<div class="architecture-lane-label feedback-label"><span>Research feedback</span><span class="feedback-return">'+(feedback.every(stage=>stage.status==='disabled')?'Disabled for this run':feedback.every(stage=>stage.status==='unknown')?'Not recorded':'Evidence → knowledge → next proposal')+'</span></div><ol class="architecture-flow architecture-feedback">'+feedback.map(stageHTML).join('')+'</ol>';
    if(architecture.edges?.length)html+='<div class="architecture-edges" aria-label="Pipeline connections">'+architecture.edges.map(edge=>{const from=stages.find(s=>s.id===edge.from)?.label||edge.from,to=stages.find(s=>s.id===edge.to)?.label||edge.to;return '<span>'+esc(from)+' <span aria-hidden="true">→</span> '+esc(to)+(edge.label?' <small>'+esc(edge.label)+'</small>':'')+'</span>';}).join('')+'</div>';
    html+='</div>';
  }
  html+='<details class="architecture-configuration"'+(configurationOpen?' open':'')+'><summary>Recorded configuration <span>Models, limits and provenance</span></summary><div class="architecture-sections">'+(architecture.sections||[]).map(section=>'<article class="configuration-card" data-section="'+esc(section.id)+'"><h3>'+esc(section.title)+'</h3><dl>'+(section.fields||[]).map(field=>'<div class="configuration-row" data-field="'+esc(field.key)+'"><dt>'+esc(field.label)+'</dt><dd'+(field.source?' title="Recorded in '+esc(field.source)+'"':'')+'>'+architectureValue(field)+(field.note?'<small>'+esc(field.note)+'</small>':'')+'</dd></div>').join('')+'</dl></article>').join('')+'</div></details>';
  if(architecture.warnings?.length)html+='<div class="architecture-notes">'+architecture.warnings.map(note=>'<p>'+esc(note)+'</p>').join('')+'</div>';
  html+='<div class="architecture-source">Source: <code>'+esc(architecture.source||'unavailable')+'</code><span>Missing values remain unknown; current defaults are not substituted.</span></div></div>';
  $('tab-content').innerHTML=html;
  if(architecture.graph){
    bindArchitectureGraph($('tab-content'),architecture.graph,previousSelection);
    if(inactiveOpen&&document.querySelector('.graph-inactive'))document.querySelector('.graph-inactive').open=true;
    renderArchitecturePhase();
  }
}

function researchOutcome(event) {
  const phase=event.phase||event.event,data=event.data||{};
  if(!['conclusion','reflection'].includes(phase))return null;
  const name=phase==='conclusion'?'Conclusion':'Reflection';
  const error=data.error!=null||data.lesson_error!=null;
  if(error||['rejected','failed','error'].includes(data.status))return {title:name+' rejected',color:'negative-text',icon:'!'};
  if(data.status==='invalid')return {title:name+' invalid',color:'negative-text',icon:'!'};
  if(data.status==='skipped')return {title:name+' skipped',color:'',icon:'−'};
  if(data.status!=='parsed')return {title:name+' recorded',color:'',icon:'·'};
  if(phase==='reflection') {
    if(!data.applied||typeof data.applied!=='object')return {title:'Reflection not applied',color:'',icon:'·'};
    const changed=data.changed===true||data.comparison_reviews_changed===true;
    return {title:changed?'Knowledge revised':data.changed===false?'Reflection accepted · no change':'Reflection accepted',color:'green',icon:'✓'};
  }
  if(data.lesson_admission?.status==='suppressed')return {title:'Conclusion recorded · lessons suppressed',color:'',icon:'·'};
  if(data.verdict_matches_observation===false)return {title:'Conclusion recorded · verdict mismatch',color:'yellow',icon:'!'};
  return {title:'Conclusion recorded',color:data.llm?'green':'',icon:data.llm?'✓':'·'};
}
function eventTitle(event) {
  if(event.event==='research_tool'){
    const phase=event.data?.phase||event.phase;
    const data=event.data||event;
    if(phase==='invocation_result'&&data.result_schema==='sciel-tool-result/1')return 'Tool check · '+(data.tool_result_status||'outcome unrecorded');
    if(phase==='replay_result'&&data.replay_policy==='independent_execution')return 'Independent execution · '+(data.matched===true?'verified; measurements may differ':data.matched===false?'criterion not met':'result recorded');
    const labels={registered:'Tool version registered',published:'Tool published for sharing',llm_start:'Tool model request started',llm_result:'Tool model response recorded',invocation_started:'Tool invocation pending',invocation_result:'Tool execution · '+(event.data?.status||'outcome unrecorded'),context_prepared:'Tool context prepared',child_link:'Tool receipts linked to program',episode_finished:'Tool episode finished',rejected:'Tool proposal rejected',cell_created:'Research question opened',cell_activated:'Research cell scheduled',cell_revision:'Research cell revision recorded',replay_result:'Independent replay · '+(event.data?.matched===true?'reproduced':event.data?.matched===false?'not reproduced':'result recorded'),adopted:'Tool adopted for further trials',post_adoption_use:'Tool invoked after adoption',post_adoption_attempt:'Post-adoption tool attempt'};
    return labels[phase]||'Tool event recorded';
  }
  if(event.event==='decision'&&event.data?.policy==='candidate_novelty'){
    const data=event.data;
    return 'Candidate novelty · '+(data.remeasurement===true?'eligible remeasurement':data.accept===false?'duplicate rejected':data.accept===true?'candidate accepted':'decision recorded');
  }
  if(event.event==='decision'&&event.data?.policy==='output_novelty'){
    const data=event.data;
    return data.status==='exact_recorded_repeat'?'Exact recorded output repeated'+(data.remeasurement?' · remeasurement':' · mutation not admitted'):
      data.status==='unsupported'?'Output identity unavailable · evaluation retained':'New recorded output';
  }
  return researchOutcome(event)?.title||phaseNames[event.phase]||phaseNames[event.event]||event.summary||event.phase||event.event;
}
function renderActivity() {
  const relevant=state.snapshot.events.filter(e=>['hypothesis','outcome','conclusion','reflection'].includes(e.phase)||['run_end','run_start','sh_cut','checkpoint_restore'].includes(e.event)||(e.event==='research_tool'&&['registered','published','invocation_result','child_link','cell_created','replay_result','adopted','post_adoption_use'].includes(e.data?.phase||e.phase)));
  $('activity-feed').innerHTML=relevant.slice(-7).reverse().map(e=>{
    const phase=e.phase||e.event;
    const outcome=researchOutcome(e);
    const color=outcome?.color||(phase==='hypothesis'?'blue':'');
    const icon=outcome?.icon||(phase==='hypothesis'?'?':'·');
    const label=e.data?.experiment_id || (numeric(e.iteration)?'Iteration '+e.iteration:'Event '+e.seq);
    const detail=e.data?.error_detail||e.data?.lesson_error_detail;
    const subtitle=label+(detail?' · '+detail:'');
    return '<div class="activity-item" data-event-seq="'+esc(e.seq)+'"><span class="activity-icon '+color+'">'+icon+'</span><div class="activity-copy"><div class="activity-title">'+esc(eventTitle(e))+'</div><div class="activity-subtitle" title="'+esc(subtitle)+'">'+esc(subtitle)+'</div></div><span class="activity-seq">'+esc(e.seq)+'</span></div>';
  }).join('') || empty('Waiting for events');
}

let plotProjection=null;
function renderPlot() {
  if(state.snapshot?.kind==='methods'||state.snapshot?.run.kind==='methods')return;
  if(!state.snapshot)return;
  const trial=currentTrial();
  $('selected-point-label').textContent=trial?'Iteration '+trial.iteration:'';
  const displayPoint=point=>{
    const view=metricDisplay(point),parent=metricDisplay(point,'parent_metric_display','parent_score');
    return {...point,score:measuredValue(view),best_score:measuredValue(metricDisplay(point,'best_metric_display','best_score')),
      parent_score:measuredValue(parent),display_delta:metricDifference(view,parent),
      metric_display:view,metric_text:view.status==='measured'?null:metricText(view,9),metric_note:view.status==='measured'?null:view.reason,
      display_status:view.status==='invalid_penalty'?'Invalid result · penalty':view.status==='failed'?'Evaluation failed':view.status==='unknown'?'Measurement unavailable':point.status};
  };
  if(plotProjection?.snapshot!==state.snapshot)plotProjection={snapshot:state.snapshot,
    points:state.snapshot.curves.map(displayPoint),programs:(state.snapshot.programs||state.snapshot.curves).map(displayPoint)};
  const {points,programs}=plotProjection;
  const pointIdentity=point=>point.candidate_id||point.experiment_id||null;
  const selectPoint=point=>{
    const id=pointIdentity(point);
    if(!id)return;
    state.selected=id;state.detail=null;
  };
  const shown=renderChart($('score-chart'),points,state.axis,trial?.iteration,point=>{
    if(pointIdentity(point)){selectPoint(point);renderPlot();renderTab();}
  },metricLabel(),{
    runKey:state.runId+':'+(state.snapshot.run.run_id||''), dataVersion:state.snapshot.content_version, live:state.snapshot.runtime?.active===true,
    selectedCandidateId:state.selected, programs,
    onInspect:point=>{if(point.code_available===false||!pointIdentity(point))return;selectPoint(point);switchTab('code');renderPlot();},
    onLLM:point=>{if(point.llm_available===false)return;const query=point.experiment_id||point.candidate_id;if(query)switchTab('llm',query);},
  });
  $('chart-subtitle').textContent=metricLabel()+' · measured outcomes only';
  $('chart-metric-label').textContent='Best '+metricLabel().toLowerCase();
  $('chart-start').textContent='Initial '+metricText(metricDisplay(state.snapshot.stats,'seed_metric_display','seed_score'),4);
  $('chart-end').title='Successful ordinary search evaluations. Excludes seed, bootstrap and failed evaluations.';
  $('chart-end').textContent=(state.snapshot.stats.iterations ?? 0)+' iterations · '+(state.snapshot.stats.evaluations ?? 0)+' search evaluations'+(shown.total>shown.displayed?' · '+shown.displayed+' of '+shown.total+' chart samples':'');
  renderUnmeasuredOutcomes();
}

function renderUnmeasuredOutcomes() {
  let mount=$('chart-outcomes');
  if(!mount){
    mount=document.createElement('div');mount.id='chart-outcomes';mount.className='chart-outcomes';$('score-chart').after(mount);
    mount.addEventListener('click',event=>{
      const llm=event.target.closest('[data-llm-experiment]');
      if(llm){switchTab('llm',llm.dataset.llmExperiment);return;}
      const code=event.target.closest('[data-candidate]');
      if(code){state.selected=code.dataset.candidate;state.detail=null;renderPlot();switchTab('code');}
    });
  }
  const open=mount.querySelector('details')?.open===true;
  const rows=state.snapshot.trials.filter(row=>measuredValue(metricDisplay(row))===null);
  const counts={invalid_penalty:0,failed:0,unknown:0};
  for(const row of rows){const status=metricDisplay(row).status;counts[status in counts?status:'unknown']++;}
  mount.hidden=!rows.length;
  mount.innerHTML=rows.length?'<details'+(open?' open':'')+'><summary>Not on the measured-value axis · '+counts.invalid_penalty+' invalid · '+counts.failed+' failed · '+counts.unknown+' unavailable or pending</summary><p>Penalty scores are not physical measurements. Valid zero measurements remain on the chart. All attempts remain in Programs.</p><div class="chart-outcome-list">'+rows.slice(-60).reverse().map(row=>'<div data-outcome-id="'+esc(row.candidate_id||row.id)+'" data-metric-status="'+esc(metricDisplay(row).status)+'"><span class="mono">'+esc(row.candidate_id||row.id)+'</span><span>'+metricHTML(metricDisplay(row))+'</span><span class="card-actions">'+(row.code_available?'<button class="inline-link" data-candidate="'+esc(key(row))+'">Code &amp; diff ↗</button>':'')+'<button class="inline-link" data-llm-experiment="'+esc(row.id)+'">LLM ↗</button></span></div>').join('')+'</div>'+(rows.length>60?'<p>Latest 60 of '+rows.length+' outcomes shown; use Programs to inspect the complete history.</p>':'')+'</details>':'';
}

function switchTab(tab, query='') {
  state.tab=tab;state.query=query;state.limit=60;
  const url=new URL(location.href);url.searchParams.set('tab',tab);history.replaceState(null,'',url);
  document.querySelectorAll('[data-tab]').forEach(button=>{const active=button.dataset.tab===tab;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
  $('tab-content').setAttribute('aria-labelledby','tab-'+tab);
  renderTab();
}

function toolbar(description,placeholder) {
  return '<div class="table-toolbar"><span>'+esc(description)+'</span>'+(placeholder?'<input id="content-search" type="search" placeholder="'+esc(placeholder)+'" aria-label="'+esc(placeholder)+'" value="'+esc(state.query)+'">':'')+'</div>';
}
function more(total) {return total>state.limit?(state.limit>=MAX_ROWS?'<p class="display-limit">Showing the latest '+MAX_ROWS+' matching records of '+total+'. Use search to narrow the history.</p>':'<button class="load-more" data-more>Show more · '+(total-state.limit)+'</button>'):'';}
function matches(value) {return !state.query||JSON.stringify(value).toLowerCase().includes(state.query.toLowerCase());}

let toolsMount=null,toolsIdentity=null;
function renderTools() {
  const identity=scientificIdentity(state.snapshot);
  if(!toolsMount||toolsIdentity!==identity){toolsMount=document.createElement('div');toolsIdentity=identity;}
  if(toolsMount.parentNode!==$('tab-content'))$('tab-content').replaceChildren(toolsMount);
  renderResearchTools(toolsMount,state.snapshot.research_tools,{runId:state.runId,identity,fetchJSON:getJSON,onProgram:id=>{state.selected=id;state.detail=null;switchTab('code');}});
}

let cellsMount=null,cellsIdentity=null;
function renderCells() {
  const identity=scientificIdentity(state.snapshot);
  if(!cellsMount||cellsIdentity!==identity){cellsMount=document.createElement('div');cellsIdentity=identity;}
  if(cellsMount.parentNode!==$('tab-content'))$('tab-content').replaceChildren(cellsMount);
  renderResearchCells(cellsMount,state.snapshot.research_tools,{runId:state.runId,identity,fetchJSON:getJSON,
    onProgram:id=>{state.selected=id;state.detail=null;switchTab('code');}});
}

let packingsMount=null;
function renderPackingGallery() {
  if(!packingsMount)packingsMount=document.createElement('div');
  if(packingsMount.parentNode!==$('tab-content'))$('tab-content').replaceChildren(packingsMount);
  renderPackings(packingsMount,{runId:state.runId,identity:scientificIdentity(state.snapshot),
    version:state.contentVersion,fetchJSON:getJSON,
    onProgram:id=>{state.selected=id;state.detail=null;switchTab('code');}});
}

let workflowMount=null;
function destroyWorkflow() {
  if(workflowMount)destroyWorkFlow(workflowMount);
  workflowMount=null;
}
function renderWorkflow() {
  if(!state.snapshot)return;
  if(!workflowMount)workflowMount=document.createElement('div');
  if(workflowMount.parentNode!==$('tab-content'))$('tab-content').replaceChildren(workflowMount);
  renderWorkFlow(workflowMount,{runId:state.runId,identity:scientificIdentity(state.snapshot),version:state.contentVersion,fetchJSON:getJSON,follow:state.follow,connected:state.timingConnected,live:state.snapshot.runtime?.active===true});
}

function renderTab() {
  if(!state.snapshot)return;
  if(state.snapshot.kind==='methods'||state.snapshot.run.kind==='methods')return;
  if(state.tab!=='population')destroyPopulation();
  if(state.tab!=='workflow')destroyWorkflow();
  if(state.tab!=='packings'&&packingsMount)suspendPackings(packingsMount);
  const focused=document.activeElement?.id;
  const selection=focused==='content-search'?document.activeElement.selectionStart:null;
  const opened=[...$('tab-content').querySelectorAll('details[open]')].map(d=>d.dataset.seq);
  const researchOpened=[...$('tab-content').querySelectorAll('details[data-reliability-panel][open]')].map(d=>d.dataset.reliabilityPanel);
  const researchFocused=document.activeElement?.tagName==='SUMMARY'?document.activeElement.parentElement?.dataset.reliabilityPanel:null;
  if(state.tab==='trials')renderTrials();
  else if(state.tab==='hypotheses')renderHypotheses();
  else if(state.tab==='lessons')renderLessons();
  else if(state.tab==='events')renderEvents();
  else if(state.tab==='workflow')renderWorkflow();
  else if(state.tab==='tools')renderTools();
  else if(state.tab==='research-cells')renderCells();
  else if(state.tab==='packings')renderPackingGallery();
  else if(state.tab==='llm')renderLLMCalls($('tab-content'),{runId:state.runId,identity:scientificIdentity(state.snapshot),version:state.contentVersion,query:state.query,fetchJSON:getJSON});
  else if(state.tab==='population')renderPopulation();
  else if(state.tab==='learning')$('tab-content').innerHTML=learningHTML(state.snapshot.learning);
  else if(state.tab==='architecture')renderArchitecture();
  else renderCode();
  if(focused==='content-search'&&$('content-search')){$('content-search').focus({preventScroll:true});$('content-search').setSelectionRange(selection,selection);}
  if(state.tab==='events')$('tab-content').querySelectorAll('details').forEach(d=>{d.open=opened.includes(d.dataset.seq);});
  if(state.tab==='lessons')$('tab-content').querySelectorAll('details[data-reliability-panel]').forEach(d=>{d.open=researchOpened.includes(d.dataset.reliabilityPanel);if(researchFocused===d.dataset.reliabilityPanel)d.querySelector('summary')?.focus({preventScroll:true});});
}

function renderTrials() {
  const trials=state.snapshot.trials.filter(matches).slice().reverse();
  let html=toolbar('All attempts are recorded, including failures and duplicates','Search programs');
  if(!trials.length){$('tab-content').innerHTML=html+empty('No programs yet','Candidate evaluations and changes will appear here.');return;}
  html+='<div class="table-wrap"><table><thead><tr><th>Iteration</th><th>Program</th><th>Change</th><th>'+esc(metricLabel())+'</th><th>Δ vs. parent</th><th>Result</th><th></th></tr></thead><tbody>';
  html+=trials.slice(0,state.limit).map(t=>{
    const id=key(t);
    const history=state.snapshot.result_history?.by_program?.[t.candidate_id||t.id];
    const repeated=history?.output_match_count>0?'<span class="history-match" title="Exact saved output also occurs in another evaluation; this does not establish algorithm equivalence.">Same recorded output</span>':'';
    return '<tr class="interactive'+(id===state.selected?' selected':'')+'" data-candidate="'+esc(id)+'" tabindex="0" aria-label="Open program '+esc(id)+'"><td class="trial-index">'+esc(t.iteration ?? '—')+'</td><td><span class="program-id"><span class="program-icon">⌘</span>'+esc(t.candidate_id||t.id)+'</span>'+repeated+'</td><td class="trial-text" title="'+esc(hypothesisText(t.hypothesis))+'">'+esc(hypothesisText(t.hypothesis)||t.operator||'No hypothesis recorded')+'</td><td class="number">'+metricHTML(metricDisplay(t))+'</td><td class="number '+(trialDifference(t)>0?'positive':trialDifference(t)<0?'negative-text':'')+'">'+delta(trialDifference(t))+'</td><td>'+metricBadge(t)+'</td><td class="row-action"><button class="inline-link" data-llm-experiment="'+esc(t.id)+'" aria-label="LLM request and response for '+esc(t.id)+'">LLM ↗</button></td></tr>';
  }).join('');
  $('tab-content').innerHTML=html+'</tbody></table></div>'+more(trials.length);
}

function renderHypotheses() {
  const list=state.snapshot.hypotheses.filter(matches).slice().reverse();
  let html=toolbar('Model predictions and measured outcomes are shown separately','Search hypotheses');
  if(!list.length){$('tab-content').innerHTML=html+empty('No hypotheses recorded','Hypotheses will appear when the research loop produces its first prediction.');return;}
  html+='<div class="cards">'+list.slice(0,state.limit).map(t=>{
    const h=t.hypothesis||{},conclusion=typeof t.conclusion==='string'?t.conclusion:(t.conclusion?.explanation||t.conclusion?.llm?.explanation);
    return '<article class="research-card"><div class="card-meta"><span class="mono">'+esc(t.id)+'</span><span>· Iteration '+esc(t.iteration)+'</span><span>· '+esc(t.parent_id||'No parent')+'</span>'+badge(t.forecast_verdict)+'</div><h3>'+esc(hypothesisText(h))+'</h3>'+(h.reasoning?'<p>'+esc(h.reasoning)+'</p>':'')+'<div class="card-facts"><div>Predicted Δ · score units<strong>['+delta(h.predicted_low)+'; '+delta(h.predicted_high)+']</strong></div><div>Measured Δ<strong class="'+(trialDifference(t)>0?'positive':'')+'">'+delta(trialDifference(t))+'</strong></div><div>Model confidence<strong>'+(numeric(h.confidence)?Math.round(h.confidence*100)+'%':'—')+'</strong></div><div>'+esc(metricLabel())+'<strong>'+metricHTML(metricDisplay(t))+'</strong></div></div>'+(conclusion?'<div class="card-subsection"><span class="label">Model analysis</span><p>'+esc(conclusion)+'</p></div>':'')+'<div class="card-actions"><button class="inline-link" data-candidate="'+esc(key(t))+'">View code and diff ↗</button><button class="inline-link" data-llm-experiment="'+esc(t.id)+'">LLM request &amp; response ↗</button></div></article>';
  }).join('')+'</div>'+more(list.length);
  $('tab-content').innerHTML=html;
}

function reliabilityHTML(view) {
  if(!view)return '<section class="research-reliability"><h3>Research reliability</h3><p>Delivery and validation metadata not recorded.</p></section>';
  const memory=view.memory||{},conclusions=view.conclusions||{},ideas=view.ideas||{},latest=memory.latest;
  const count=value=>numeric(value)?String(value):'Unknown';
  const fact=(label,value)=>'<div><span>'+esc(label)+'</span><strong>'+esc(value)+'</strong></div>';
  const known=(section,value)=>section.recorded?count(value):'Not recorded';
  const diagnostic=item=>[item.reason,...Object.entries(item.diagnostic||{}).map(([key,value])=>key+': '+value)].filter(Boolean).join(' · ');
  const rows=(history,columns)=>'<div class="table-wrap reliability-table"><table><thead><tr>'+columns.map(([title])=>'<th>'+esc(title)+'</th>').join('')+'</tr></thead><tbody>'+(history||[]).slice(-120).reverse().map(item=>'<tr>'+columns.map(([,get])=>'<td>'+esc(get(item))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  let html='<section class="research-reliability"><h3>Research reliability</h3><p>Stored lessons and delivered advice are different. Counts below use recorded metadata.</p><div class="reliability-metrics">'+
    fact('Stored active',count(memory.stored_active))+fact('Latest ranked',count(latest?.ranked))+fact('Latest selected',count(latest?.selected))+fact('Latest delivered',count(latest?.delivered))+fact('Latest dropped by size',count(latest?.dropped_by_size))+'</div>';
  html+='<p class="reliability-note">'+esc(count(memory.zero_delivered_due_size))+' attempts delivered no ranked lessons with size omissions · '+esc(count(memory.metadata_known))+' / '+esc(count(memory.attempts))+' attempts have delivery metadata. This does not imply that all historical context was absent.</p>';
  html+='<details data-reliability-panel="memory"><summary>Memory delivery by attempt</summary>'+rows(memory.history,[['Attempt',item=>item.experiment_id],['Stored active',item=>count(item.stored_active)],['Ranked',item=>count(item.ranked)],['Selected',item=>count(item.selected)],['Delivered',item=>count(item.delivered)],['Dropped by size',item=>count(item.dropped_by_size)],['Omissions',item=>item.delivery_consistent===false?'Inconsistent recorded IDs':Object.entries(item.omission_reasons||{}).map(([key,value])=>key+': '+value).join(', ')||'—']])+'</details>';
  html+='<div class="reliability-outcomes"><div><h3>Conclusions</h3><p>Final outcomes, after any bounded correction.</p><div class="reliability-metrics">'+fact('Parsed',known(conclusions,conclusions.parsed))+fact('Rejected',known(conclusions,conclusions.rejected))+fact('Skipped',known(conclusions,conclusions.skipped))+fact('Corrections scheduled',known(conclusions,conclusions.repairs))+'</div></div>';
  html+='<div><h3>Two-stage ideas</h3><p>Terminal card failures before code generation.</p><div class="reliability-metrics">'+fact('Finished',known(ideas,ideas.finished))+fact('Rejected before code',known(ideas,ideas.rejected_before_code))+fact('Invalid cards',known(ideas,ideas.invalid_cards))+fact('Correction exhausted',known(ideas,ideas.repair_exhausted))+fact('Duplicate cards',known(ideas,ideas.duplicates))+'</div></div></div>';
  html+='<details data-reliability-panel="conclusions"><summary>Conclusion diagnostics</summary>'+rows(conclusions.history,[['Experiment',item=>item.experiment_id],['Final status',item=>item.status],['Corrections',item=>count(item.repairs)],['Recorded validation diagnostic',diagnostic]])+'</details>';
  html+='<details data-reliability-panel="ideas"><summary>Idea diagnostics</summary>'+rows(ideas.history,[['Idea',item=>item.idea_id],['Final status',item=>item.status],['Code requested',item=>item.code_requested?'Yes':item.card_requested?'No':'Unknown'],['Card validation failures',item=>count(item.card_rejections)],['Recorded diagnostic',diagnostic]])+'</details>';
  return html+'<p class="reliability-note">'+(view.notes||[]).map(esc).join(' ')+'</p></section>';
}

function renderLessons() {
  const list=state.snapshot.lessons.filter(matches).slice().reverse();
  let html=toolbar('Evidence-linked knowledge · original model wording','Search lessons')+reliabilityHTML(state.snapshot.reliability);
  if(!list.length){$('tab-content').innerHTML=html+empty('No lessons yet','Lessons will appear after results are analyzed. Experiments may still be running without recorded lessons.');return;}
  html+='<div class="cards">'+list.slice(0,state.limit).map(l=>{
    const evidence=Array.isArray(l.evidence_ids)?l.evidence_ids:[];
    const exposure=numeric(l.exposure_count)?l.exposure_count+' '+plural(l.exposure_count,['time','times']):'Not recorded';
    return '<article class="research-card"><div class="card-meta"><span class="mono">'+esc(l.id)+'</span><span>· '+esc(l.scope==='global'?'Global':l.scope==='branch'?'Branch '+(l.branch||''):l.scope||'')+'</span><span>· '+esc(l.polarity==='negative'?'Negative evidence':l.polarity==='positive'?'Positive evidence':l.polarity||'Observation')+'</span>'+badge(l.status||'active')+'</div><h3>'+esc(l.rule)+'</h3><div class="card-facts"><div>Supporting experiments<div class="card-actions">'+evidence.map(id=>'<button class="evidence-id" data-evidence="'+esc(id)+'">'+esc(id)+'</button>').join('')+'</div></div><div>Used in generation<strong>'+esc(exposure)+'</strong></div></div></article>';
  }).join('')+'</div>'+more(list.length);
  $('tab-content').innerHTML=html;
}

function renderEvents() {
  const list=state.snapshot.events.filter(matches).slice().reverse();
  let html=toolbar('Events in journal order','Search events');
  html+='<div class="event-list">'+list.slice(0,state.limit).map(e=>'<details class="event-row" data-seq="'+esc(e.seq)+'"><summary><span class="number">'+esc(e.seq)+'</span><span class="event-title">'+esc(eventTitle(e))+'</span><span class="badge neutral">'+esc(e.phase||e.event)+'</span></summary><div class="event-receipt"></div><pre class="event-data"></pre></details>').join('')+'</div>'+more(list.length);
  $('tab-content').innerHTML=html;
}

function noveltyReceiptHTML(data) {
  const neighbors=Array.isArray(data.neighbors)?data.neighbors.slice(0,10):[];
  const verdict=data.remeasurement===true?'Eligible remeasurement':data.accept===false?'Duplicate rejected':data.accept===true?'Candidate accepted':'Decision recorded';
  const kind={sha256:'Exact source SHA256',ast:'Structural AST',embedding:'Code embedding (advisory)',new:'No previous source'}[data.match_kind]||data.match_kind||'Not recorded';
  let html='<section class="novelty-receipt"><h3>'+esc(verdict)+'</h3><p>SHA256 → AST → code embedding · final source after repair and entry-point grafting.</p><dl class="novelty-facts">'+
    [['Match',kind],['Matched program',data.matched_program_id||'None recorded'],['Reason',data.reason||'Not recorded']].map(([label,value])=>'<div><dt>'+esc(label)+'</dt><dd>'+esc(value)+'</dd></div>').join('')+'</dl>'+
    '<p>Embedding cosine is advisory; similar code is not proof of equivalent behavior. Remeasurements are recorded separately from new mutations.</p>';
  if(!neighbors.length)html+='<p>No nearest-source details were recorded.</p>';
  for(const neighbor of neighbors){
    if(!neighbor||typeof neighbor!=='object')continue;
    const difference=typeof neighbor.ast_diff==='string'?neighbor.ast_diff:null;
    const truncated=neighbor.ast_diff_truncated===true||(difference?.length||0)>12000;
    html+='<article class="novelty-neighbor"><h4>'+esc(neighbor.program_id||'Program ID not recorded')+' <span>cosine '+esc(numeric(neighbor.similarity)?neighbor.similarity.toFixed(6):'not recorded')+'</span></h4>'+
      (difference===null?'<p>AST diff unavailable in this record.</p>':difference===''?'<p>No structural AST differences.</p>':'<pre class="novelty-ast-diff" tabindex="0" aria-label="Recorded AST difference">'+esc(difference.slice(0,12000))+'</pre>')+
      (truncated?'<p class="novelty-truncated">AST diff truncated; inspect the source for the complete program.</p>':'')+'</article>';
  }
  if(Array.isArray(data.neighbors)&&data.neighbors.length>10)html+='<p>Showing the first 10 recorded neighbors.</p>';
  return html+'<p class="novelty-original">Original journal record</p></section>';
}

function destroyPopulation() {
  const mount=$('population-map');
  if(mount)destroyPopulationMap(mount);
}

function historyLinks(ids) {
  return (Array.isArray(ids)?ids:[]).slice(0,12).map(id=>'<button class="inline-link mono" data-candidate="'+esc(id)+'">'+esc(id)+' ↗</button>').join(', ');
}

function resultHistoryDetailHTML(history) {
  if(!history)return '';
  const facts=[];
  if(history.alias_kind)facts.push('<p>'+esc(history.alias_kind==='seed_copy'?'Shared seed measurement':'Migration copy')+' · not a new evaluation.</p>');
  if(history.source_match_count>0)facts.push('<p>Same source · '+esc(history.source_match_count)+' other program IDs: '+historyLinks(history.source_matches)+'</p>');
  if(history.ast_match_count>0)facts.push('<p>Same structural AST · '+esc(history.ast_match_count)+' other program IDs: '+historyLinks(history.ast_matches)+'</p>');
  if(history.output_match_count>0)facts.push('<p><strong>Same recorded output</strong> · '+esc(history.output_match_count)+' other evaluations: '+historyLinks(history.output_matches)+'</p><p>Exact saved output match across the run, including other islands and former members. These measurements are unpaired; algorithm equivalence and runtime benefit are not established.</p>');
  else facts.push('<p>'+esc(history.output_status==='unavailable'?'No comparable saved output is available.':history.output_comparison_available===false||history.output_match_count==null?'Output comparison unavailable: evaluation identity is not recorded.':'No other evaluation with this exact saved output in the covered history.')+'</p>');
  const coverage=state.snapshot?.result_history?.coverage;
  if(coverage)facts.push('<p class="history-note">'+esc('Saved history through iteration '+(coverage.iteration??'not recorded')+(coverage.stale?' · newer measurements are not covered yet.':'.'))+'</p>');
  facts.push('<p class="history-note">Equal scores alone are not counted as repeated outputs. Listed links are capped at 12.</p>');
  return '<section class="result-history-detail" aria-label="Whole-run identity and output history"><h3>Across saved run history</h3>'+facts.join('')+'</section>';
}

function renderResultHistory() {
  const mount=$('population-history'),view=state.snapshot.result_history;
  if(!mount)return;
  if(!view){mount.innerHTML='';return;}
  const wasOpen=mount.querySelector('details')?.open===true,c=view.counts||{},coverage=view.coverage||{};
  const count=value=>Number.isInteger(value)?String(value):'not recorded';
  const repeats=Object.entries(view.by_program||{}).filter(([id,h])=>h.output_match_count>0&&!h.alias_kind&&h.first_output_program_id!==id);
  mount.innerHTML='<details class="result-history-summary"'+(wasOpen?' open':'')+'><summary>Run-wide history <span>'+esc(count(c.unique_sources))+' source variants · '+esc(count(c.repeated_outputs))+' repeated outputs · '+esc(count(c.source_aliases))+' source copies</span></summary><div class="result-history-body"><p>All islands, including former members. Repeated outputs count separate measurements; seed and migration copies do not add evaluations.</p><p>'+esc('Comparable saved outputs: '+count(coverage.output_evaluations)+' of '+count(c.evaluations)+' finished evaluations. Output history covers saved admitted programs; rejected candidates may have no output observation.')+'</p><p>'+esc('Saved through iteration '+(coverage.iteration??'not recorded')+(coverage.stale?' · newer measurements are not covered yet.':'.'))+'</p>'+repeats.slice(0,12).map(([id,h])=>'<p>'+historyLinks([id])+' has the same recorded output as '+historyLinks([h.first_output_program_id||h.earliest_output_match].filter(Boolean))+'</p>').join('')+(repeats.length>12?'<p>Showing 12 matching programs. Open individual source cards for their history.</p>':'')+'<p class="history-note">Exact saved output does not establish algorithm equivalence. Score ties are not used as output fingerprints.</p></div></details>';
}

function updatePopulationMap() {
  const mount=$('population-map');
  if(!mount||!state.snapshot?.population)return;
  renderPopulationMap(mount,state.snapshot.population,{
    runKey:scientificIdentity(state.snapshot),
    storageRenderer:renderStorageSpace,
    metricLabel:metricLabel(),
    metricValue:(row,field='metric_display',scoreKey='score')=>measuredValue(metricDisplay(row,field,scoreKey)),
    formatScore:(value,row,field='metric_display')=>row?metricText(metricDisplay(row,field,field==='best_metric_display'?'best_score':'score'),6):format(value,6),
    live:state.snapshot.runtime?.active===true&&state.timingConnected,
    follow:state.follow,
    onProgram:(id,{action}={})=>{
      state.selected=id;state.detail=null;
      state.codeMode=action==='source'?'code':'diff';
      renderPlot();switchTab('code');
    }
  });
}

function updatePopulationPreview() {
  if(!state.snapshot||state.snapshot.kind==='methods'||state.snapshot.run.kind==='methods')return;
  renderPopulationPreview($('population-preview'),state.snapshot.population,{
    runKey:scientificIdentity(state.snapshot),metricLabel:metricLabel(),follow:state.follow,
    formatScore:(value,row)=>metricText(metricDisplay(row),6),
    onOpen:()=>{switchTab('population');$('tab-content').scrollIntoView({behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});},
    onProgram:(id,{action}={})=>{state.selected=id;state.detail=null;state.codeMode=action==='source'?'code':'diff';renderPlot();switchTab('code');}
  });
}

function renderPopulation() {
  const population=state.snapshot.population;
  if(!population?.available&&!population?.dynamics?.islands?.length){destroyPopulation();$('tab-content').innerHTML=empty('Population not recorded','Islands and archive members appear after the engine saves a population snapshot.');return;}
  if(!$('population-map'))$('tab-content').innerHTML='<div id="population-history"></div><div id="population-map"></div><details id="population-details" class="population-storage-details"><summary>Storage details <span>Descriptor cells, members &amp; global archive</span></summary><div id="population-details-body"></div></details>';
  renderResultHistory();
  updatePopulationMap();
  if(!population.available){$('population-details-body').innerHTML=empty('Storage snapshot pending','Configured islands are shown above. Individual members appear when recorded.');return;}
  renderPopulationDetails(population);
}

function renderPopulationDetails(population) {
  const layout=population.layout||{},descriptor=population.descriptor||{};
  const name={map_elites:'MAP-Elites',vq:'VQ niches',pool:'Population pool',geometry:'Geometry container',unknown:'Recorded population'}[layout.kind]||'Recorded population';
  const memberLink=member=>member.id&&member.code_available?'<button class="inline-link mono" data-candidate="'+esc(member.id)+'">'+esc(member.id)+' ↗</button>':'<span class="mono">'+esc(member.id||'ID not recorded')+'</span>';
  const gridHTML=island=>{
    if(!island.grid_available)return '<p class="population-muted">Grid not recorded.</p>';
    if(layout.kind==='pool')return '<p class="population-muted">Members are retained in a pool.</p>';
    const bins=layout.grid_bins;
    if(!Number.isInteger(bins)||bins<1||bins>32||!['map_elites','vq'].includes(layout.kind))return '<div class="population-sparse">'+island.grid.map(cell=>'<span>Cell '+esc(cell.x)+', '+esc(cell.y)+' · '+esc(metricText(metricDisplay(cell)))+'</span>').join('')+'</div>';
    const size=220,step=size/bins;
    let svg='<svg viewBox="0 0 250 255" role="img" aria-label="'+esc(name+' grid, island '+island.id)+'"><title>Recorded grid cells. Horizontal: '+esc(layout.x_label)+'. Vertical: '+esc(layout.y_label)+'.</title>';
    for(let x=0;x<bins;x++)for(let y=0;y<bins;y++)svg+='<rect class="population-empty-cell" x="'+(20+x*step)+'" y="'+(5+(bins-1-y)*step)+'" width="'+(step-2)+'" height="'+(step-2)+'" rx="2"/>';
    for(const cell of island.grid){
      if(!Number.isInteger(cell.x)||!Number.isInteger(cell.y)||cell.x<0||cell.y<0||cell.x>=bins||cell.y>=bins)continue;
      const member=island.members.find(member=>member.id===cell.candidate_id);
      const open=member?.code_available?' data-candidate="'+esc(member.id)+'" tabindex="0" role="button"':'';
      svg+='<rect class="population-filled-cell"'+open+' x="'+(20+cell.x*step)+'" y="'+(5+(bins-1-cell.y)*step)+'" width="'+(step-2)+'" height="'+(step-2)+'" rx="2"><title>'+esc(cell.candidate_id||'Elite ID not recorded')+' · '+esc(metricLabel())+' '+esc(metricText(metricDisplay(cell),9))+' · cell '+cell.x+', '+cell.y+'</title></rect>';
    }
    return svg+'<text x="130" y="241" text-anchor="middle">'+esc(layout.x_label)+'</text><text x="10" y="115" text-anchor="middle" transform="rotate(-90 10 115)">'+esc(layout.y_label)+'</text></svg>';
  };
  let html='<div class="population"><div class="population-heading"><div><h2>Islands & storage</h2><p>'+esc(name)+' · '+esc(population.island_count??population.islands.length)+' islands · snapshot at iteration '+esc(population.iteration??'—')+' · '+esc(population.source)+'</p></div><span class="badge '+(population.stale?'warning':'neutral')+'">'+(population.stale?'Earlier snapshot':'Latest recorded population')+'</span></div>';
  html+='<div class="population-pipeline"><span>Program source & behavior</span><b>→</b><span>'+esc(descriptor.kind||'Descriptor not recorded')+'</span><b>→</b><span>'+esc(name)+'</span><b>→</b><span>Island elites & global archive</span></div>';
  html+='<p class="population-muted">Cells show recorded storage bins. Embeddings can define the descriptor used by MAP-Elites. Storage space shows saved prototype or program vectors when available; it does not reconstruct missing embeddings.</p>';
  html+='<div class="population-islands">'+population.islands.map(island=>'<article class="population-island"><div class="population-island-heading"><h3>Island '+esc(island.id)+'</h3><span>'+esc(island.member_count)+' members · '+esc(island.grid_cell_count)+' cells</span></div><div class="population-best">Best '+esc(metricLabel().toLowerCase())+' <strong>'+metricHTML(metricDisplay(island,'best_metric_display','best_score'),9)+'</strong></div>'+gridHTML(island)+'<div class="population-members"><table><thead><tr><th>Program</th><th>'+esc(metricLabel())+'</th><th>Role</th></tr></thead><tbody>'+island.members.map(member=>'<tr><td>'+memberLink(member)+'</td><td class="number">'+metricHTML(metricDisplay(member))+'</td><td>'+esc(member.grid_elite===true?'Cell elite':member.grid_elite===false?'Member':'Membership only')+(member.archive_member===true?' · archive':'')+'</td></tr>').join('')+'</tbody></table></div>'+(!island.members_available?'<p class="population-muted">Individual members not recorded.</p>':'')+((island.members_truncated||island.grid_truncated)?'<p class="population-muted">Display capped; counts include the complete recorded population.</p>':'')+'</article>').join('')+'</div>';
  const archive=population.archive||{};
  html+='<section class="population-archive"><h3>Global archive <span class="count-pill">'+esc(archive.count??0)+'</span></h3><p class="population-muted">Archive membership is separate from island membership and cell elites.</p><div class="archive-members">'+(archive.members||[]).map(member=>'<div>'+memberLink(member)+'<strong>'+metricHTML(metricDisplay(member),9)+'</strong></div>').join('')+'</div>'+(archive.truncated?'<p class="population-muted">Showing the first recorded archive members; display capped.</p>':'')+'</section>';
  if(population.warnings?.length)html+='<div class="architecture-notes">'+population.warnings.map(note=>'<p>'+esc(note)+'</p>').join('')+'</div>';
  $('population-details-body').innerHTML=html+'</div>';
}

function codeToolbar() {
  const trials=state.snapshot.trials.slice(-MAX_ROWS);
  const selected=currentTrial();
  if(selected&&!trials.includes(selected))trials.unshift(selected);
  if(state.selected&&!trials.some(trial=>key(trial)===state.selected))trials.unshift({id:state.selected,candidate_id:state.selected,parent_id:state.detail?.parent_id,iteration:'—'});
  return '<div class="code-toolbar"><select id="code-select" class="code-select" aria-label="Program to inspect">'+trials.map(t=>'<option value="'+esc(key(t))+'" '+(key(t)===state.selected?'selected':'')+'>'+esc((t.candidate_id||t.id)+' ← '+(t.parent_id||'∅')+' · iteration '+t.iteration)+'</option>').join('')+'</select><div class="code-actions"><div class="segmented"><button data-code-mode="diff" class="'+(state.codeMode==='diff'?'active':'')+'">Diff</button><button data-code-mode="code" class="'+(state.codeMode==='code'?'active':'')+'">Candidate</button><button data-code-mode="parent_code" class="'+(state.codeMode==='parent_code'?'active':'')+'">Parent</button></div><button class="button" id="copy-code">Copy</button></div></div>';
}

function renderCode() {
  if(!state.snapshot.trials.length&&!state.selected){$('tab-content').innerHTML=empty('No code recorded yet');return;}
  if(!state.selected)state.selected=key(state.snapshot.trials[0]);
  $('tab-content').innerHTML=codeToolbar()+'<div id="code-body"><div class="loading">Loading source code…</div></div>';
  const identity=sourceIdentity();
  if(state.detail?.id===state.selected&&state.detailKey===identity){renderCodeBody();return;}
  if(state.detailPending?.identity===identity)return;
  const request=++state.detailRequest,runId=state.runId,candidate=state.selected;
  state.detailPending={identity};
  getJSON('/api/runs/'+encodeURIComponent(runId)+'/program/'+encodeURIComponent(candidate)).then(detail=>{
    if(request!==state.detailRequest||sourceIdentity()!==identity)return;
    state.detail={...detail,id:candidate};state.detailKey=identity;
    if(state.tab==='code')renderCodeBody();
  }).catch(error=>{if(request===state.detailRequest&&sourceIdentity()===identity&&state.tab==='code'&&$('code-body'))$('code-body').innerHTML=empty('Source code unavailable',error.message);})
    .finally(()=>{if(request===state.detailRequest)state.detailPending=null;});
}
function displayedCode() {
  const detail=state.detail;
  if(!detail)return '';
  const value=detail[state.codeMode];
  return Array.isArray(value)?value.join('\n'):(value||'');
}
function renderCodeBody() {
  if(!$('code-body')||!state.detail)return;
  const d=state.detail,code=displayedCode();
  const sourceNames={'checkpoint':'Saved source','journal.child_code':'Source from journal','journal.code_fragment':'Hash-verified source','journal.hash_bound_response':'Hash-verified source'};
  const sourceLabel=state.codeMode==='diff'&&d.diff_kind==='recorded_excerpt'?'Saved change excerpt · full diff unavailable':sourceNames[d.code_source]||'Saved source';
  const metadata='<div class="code-meta"><span>'+esc(sourceLabel)+'</span><span class="mono">'+esc(short(d.parent_source_sha256))+' → '+esc(short(d.source_sha256))+'</span></div>'+resultHistoryDetailHTML(d.result_history);
  if(!code){
    const reason=state.codeMode==='diff'?(d.code&&d.parent_code?'No differences between the sources.':'A diff requires saved source for both the candidate and its parent.'):state.codeMode==='parent_code'?'Parent source is not available in the journal or checkpoint.':'No executable source was saved for this attempt.';
    $('code-body').innerHTML=metadata+empty('No data to display',reason);$('copy-code').disabled=true;return;
  }
  $('copy-code').disabled=false;
  const lines=code.split('\n');
  $('code-body').innerHTML=metadata+(lines.length>2000?'<p class="display-limit">Showing the first 2,000 lines. Copy includes the complete saved source.</p>':'')+'<pre class="code-view" tabindex="0" aria-label="'+(state.codeMode==='diff'?'Program diff':'Source code')+'">'+lines.slice(0,2000).map((line,index)=>{
    let cls='';
    if(state.codeMode==='diff'){if(line.startsWith('@@'))cls='hunk';else if(line.startsWith('+')&&!line.startsWith('+++'))cls='add';else if(line.startsWith('-')&&!line.startsWith('---'))cls='remove';}
    return '<span class="code-line '+cls+'"><span class="line-number">'+(index+1)+'</span><span class="line-text">'+esc(line)+'</span></span>';
  }).join('')+'</pre>';
}

async function refreshAll() {
  if(state.refreshing)return;
  state.refreshing=true;$('refresh-button').disabled=true;
  try{
    await refreshRuns(true);
    if(state.runId){
      const runId=state.runId,snapshot=await getJSON('/api/runs/'+encodeURIComponent(runId));
      if(state.runId===runId)applySnapshot(snapshot);
      if(state.follow)connectStream();
    }
  } catch(error){showError(error.message);}
  finally{state.refreshing=false;$('refresh-button').disabled=false;}
}

$('run-list').addEventListener('click',event=>{const button=event.target.closest('[data-run]');if(button)selectRun(button.dataset.run);});
$('run-search').addEventListener('input',renderRuns);
$('refresh-button').addEventListener('click',refreshAll);
$('empty-retry').addEventListener('click',refreshAll);
$('follow-button').addEventListener('click',()=>{
  state.follow=!state.follow;
  $('follow-button').setAttribute('aria-pressed',String(state.follow));
  $('follow-button').querySelector('span').textContent=state.follow?'Pause updates':'Resume updates';
  $('follow-button').querySelector('svg').innerHTML=state.follow?'<path d="M7 5v14M17 5v14"/>':'<path d="m8 5 11 7-11 7Z"/>';
  if(state.follow)connectStream();
  else{state.stream?.close();state.stream=null;connection('Updates paused','');}
  renderRuntime();
  if(state.snapshot?.kind==='methods'||state.snapshot?.run.kind==='methods')renderMethodsRun();
  else if(state.tab==='workflow')renderWorkflow();
  if(state.tab==='population')updatePopulationMap();
});
document.querySelectorAll('[data-axis]').forEach(button=>button.addEventListener('click',()=>{
  state.axis=button.dataset.axis;
  document.querySelectorAll('[data-axis]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});renderPlot();
}));
document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>switchTab(button.dataset.tab)));
document.querySelector('.tabs').addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  const tabs=[...document.querySelectorAll('[data-tab]')],index=tabs.indexOf(document.activeElement);
  if(index<0)return;
  event.preventDefault();
  const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
  switchTab(tabs[next].dataset.tab);tabs[next].focus();
});
$('all-events-button').addEventListener('click',()=>{switchTab('events');document.querySelector('.research-panel').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});});
$('tab-content').addEventListener('input',event=>{if(event.target.id==='content-search'){state.query=event.target.value;state.limit=60;renderTab();}});
$('tab-content').addEventListener('change',event=>{if(event.target.id==='code-select'){state.selected=event.target.value;state.detail=null;renderPlot();renderCode();}});
$('tab-content').addEventListener('keydown',event=>{if(event.target.closest('button,a,input,select,textarea'))return;const row=event.target.closest('tr[data-candidate]');if(row&&(event.key==='Enter'||event.key===' ')){event.preventDefault();row.click();}});
$('tab-content').addEventListener('toggle',event=>{
  const details=event.target;
  if(!details.matches('details[data-seq]')||!details.open)return;
  const pre=details.querySelector('.event-data');
  if(!pre||pre.textContent)return;
  const record=state.snapshot.events.find(e=>String(e.seq)===details.dataset.seq);
  if(record){
    if(record.event==='decision'&&record.data?.policy==='candidate_novelty')details.querySelector('.event-receipt').innerHTML=noveltyReceiptHTML(record.data);
    const text=JSON.stringify(record.data,null,2);pre.textContent=text.slice(0,80000)+(text.length>80000?'\n… Display truncated at 80,000 characters.':'');
  }
},true);
$('tab-content').addEventListener('click',async event=>{
  const llmLink=event.target.closest('[data-llm-experiment]');
  if(llmLink){switchTab('llm',llmLink.dataset.llmExperiment);return;}
  const candidate=event.target.closest('[data-candidate]');
  if(candidate){state.selected=candidate.dataset.candidate;state.detail=null;renderPlot();switchTab('code');return;}
  const evidence=event.target.closest('[data-evidence]');
  if(evidence){switchTab('hypotheses');state.query=evidence.dataset.evidence;renderTab();return;}
  const mode=event.target.closest('[data-code-mode]');
  if(mode){state.codeMode=mode.dataset.codeMode;renderCode();return;}
  if(event.target.closest('[data-more]')){state.limit=Math.min(MAX_ROWS,state.limit+60);renderTab();return;}
  if(event.target.id==='copy-code'){
    try{await navigator.clipboard.writeText(displayedCode());event.target.textContent='Copied';setTimeout(()=>{if($('copy-code'))$('copy-code').textContent='Copy';},1600);}
    catch(error){event.target.textContent='Select code manually';}
  }
});
for(const id of ['help-button','empty-help'])$(id).addEventListener('click',()=>$('help-dialog').showModal());
for(const id of ['close-help','help-done'])$(id).addEventListener('click',()=>$('help-dialog').close());
new ResizeObserver(()=>renderPlot()).observe($('score-chart'));
document.querySelectorAll('[data-tab]').forEach(button=>button.tabIndex=button.dataset.tab==='trials'?0:-1);
const requestedTab=new URL(location.href).searchParams.get('tab');
if([...document.querySelectorAll('[data-tab]')].some(button=>button.dataset.tab===requestedTab))switchTab(requestedTab);
setInterval(()=>refreshRuns(),10000);
setInterval(()=>renderTiming(),1000);
refreshRuns(true);
