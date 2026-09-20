// DOM interaction tests against hand-authored synthetic HTTP fixtures.
// No research archive, candidate execution, LLM, or experiment writes.
import {test, after} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createServer} from 'node:http';
import {JSDOM, VirtualConsole} from 'jsdom';
import {dashboardFixtureResponse, fixtureRun, runIndex} from './fixtures/dashboard-fixture.mjs';

const root=fileURLToPath(new URL('../../',import.meta.url));
const server=createServer((request,response)=>{
  const payload=dashboardFixtureResponse(request.url);
  response.writeHead(payload===null?404:200,{'Content-Type':'application/json'});
  response.end(JSON.stringify(payload??{error:'Unknown synthetic fixture endpoint'}));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const port=server.address().port;
after(()=>new Promise(resolve=>server.close(resolve)));
const base='http://127.0.0.1:'+port;
const assets=process.env.ARENA_WEB_ASSETS ? fileURLToPath(new URL(process.env.ARENA_WEB_ASSETS)) : root+'web/';
const chart=readFileSync(assets+'chart.js','utf8').replace('export function renderChart','function renderChart');
const learning=readFileSync(assets+'learning.js','utf8').replace('export function learningHTML','function learningHTML');
const architecture=readFileSync(assets+'architecture.js','utf8').replace(/export function (architectureGraphHTML|bindArchitectureGraph|updateArchitectureGraphPhase)/g,'function $1');
const app=readFileSync(assets+'app.js','utf8').replace(/^import .*$/mg,'');
const population=readFileSync(assets+'population.js','utf8').replace(/export function (renderPopulationMap|destroyPopulationMap)/g,'function $1');
const preview=readFileSync(assets+'population-preview.js','utf8').replace(/^export /gm,'');
const storage=readFileSync(assets+'storage-view.js','utf8').replace('export function renderStorageSpace','function renderStorageSpace');
const llmCalls=readFileSync(assets+'llm_calls.js','utf8').replace('export function renderLLMCalls','function renderLLMCalls');
const workflow=readFileSync(assets+'workflow.js','utf8').replace(/^export /gm,'');
const methodsView=readFileSync(assets+'methods.js','utf8').replace(/^import .*$/mg,'').replace(/export function (renderMethodsDashboard|updateMethodsTiming|destroyMethodsDashboard)/g,'function $1');
const methodsProgress=readFileSync(assets+'methods_progress.js','utf8').replace(/^export /gm,'');
const methodsAtlas=readFileSync(assets+'methods_atlas.js','utf8').replace(/^export /gm,'');
const researchTools=readFileSync(assets+'research_tools.js','utf8').replace(/^export /gm,'');
const researchCells=readFileSync(assets+'research_cells.js','utf8').replace(/^export /gm,'');
const packings=readFileSync(assets+'packings.js','utf8').replace(/^export /gm,'');
const html=readFileSync(assets+'experiment.html','utf8');
const measured=(value,raw=value,label='Score')=>({schema:'sciel-metric-display/1',status:'measured',value,label,units:null,raw_score:raw,reason:null,metric_sha256:'a'.repeat(64)});


async function until(predicate,label='condition') {
  const deadline=Date.now()+5000;
  while(Date.now()<deadline){if(predicate())return;await new Promise(resolve=>setTimeout(resolve,15));}
  assert.fail('Timed out: '+label);
}

async function mounted({runId=fixtureRun.id,tab,fetchOverride,ready,configure}={}) {
  const errors=[],streams=[];
  const console=new VirtualConsole();
  console.on('jsdomError',error=>errors.push(error));
  const location=new URL(base);
  if(runId)location.searchParams.set('run',runId);
  if(tab)location.searchParams.set('tab',tab);
  const dom=new JSDOM(html,{url:location.href,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:console});
  const w=dom.window;
  configure?.(w);
  w.fetch=url=>fetchOverride?.(String(url))||fetch(new URL(url,base));
  w.ResizeObserver=class{observe(){}disconnect(){}};
  w.matchMedia=()=>({matches:true});
  w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;};
  w.EventSource=class extends w.EventTarget{
    constructor(url){super();this.url=url;this.closed=false;streams.push(this);w.setTimeout(()=>this.onopen?.(),0);}
    close(){this.closed=true;}
    snapshot(data){this.dispatchEvent(new w.MessageEvent('snapshot',{data:JSON.stringify(data)}));}
    runtime(data){this.dispatchEvent(new w.MessageEvent('runtime',{data:JSON.stringify(data)}));}
  };
  let copied=null;
  Object.defineProperty(w.navigator,'clipboard',{value:{writeText:async text=>{copied=text;}}});
  // Separate scopes mirror ES modules; only the explicit export is shared.
  w.eval('{'+chart+'; window.renderChart=renderChart;}');
  w.eval('{'+learning+'; window.learningHTML=learningHTML;}');
  w.eval('{'+architecture+'; Object.assign(window,{architectureGraphHTML,bindArchitectureGraph,updateArchitectureGraphPhase});}');
  w.eval('{'+llmCalls+'; window.renderLLMCalls=renderLLMCalls;}');
  w.eval('{'+workflow+'; Object.assign(window,{renderWorkFlow,destroyWorkFlow});}');
  w.eval('{'+population+'; Object.assign(window,{renderPopulationMap,destroyPopulationMap});}');
  w.eval('{'+preview+'; Object.assign(window,{renderPopulationPreview,destroyPopulationPreview});}');
  w.eval('{'+storage+'; window.renderStorageSpace=renderStorageSpace;}');
  w.eval('{'+methodsProgress+'; Object.assign(window,{renderMethodsProgress});}');
  w.eval('{'+methodsAtlas+'; Object.assign(window,{renderMethodsPopulation,renderMethodsArchitecture});}');
  w.eval('{'+methodsView+'; Object.assign(window,{renderMethodsDashboard,updateMethodsTiming,destroyMethodsDashboard});}');
  w.eval('{'+researchTools+'; Object.assign(window,{renderResearchTools});}');
  w.eval('{'+researchCells+'; Object.assign(window,{renderResearchCells});}');
  w.eval('{'+packings+'; Object.assign(window,{renderPackings,suspendPackings,destroyPackings});}');
  w.eval('{'+app+'}');
  await until(()=>ready?ready(w.document):w.document.getElementById('run-path').textContent!==''&&w.document.getElementById('evaluations').textContent==='4','requested run loaded');
  return {dom,w,doc:w.document,errors,streams,copied:()=>copied};
}

test('Work Flow opens endpoint evidence and preserves the conversation on a dashboard refresh',async()=>{
  const feed=await (await fetch(base+'/api/runs/'+fixtureRun.id+'/workflow?limit=60&actor=all')).json();
  assert.ok(feed.items.length,'fixture supplies workflow activity');
  const event=feed.items.find(item=>item.details_available!==false);
  assert.ok(event,'fixture has inspectable evidence');
  const evidence=await (await fetch(base+'/api/runs/'+fixtureRun.id+'/workflow/'+encodeURIComponent(event.id))).json();
  assert.ok(evidence.sections.length,'the HTTP fixture returns inspectable sections');
  const {dom,doc,streams,errors}=await mounted();
  try{
    doc.querySelector('#tab-workflow').click();
    await until(()=>doc.querySelectorAll('.wf-message').length>0,'workflow messages loaded');
    const message=[...doc.querySelectorAll('.wf-message')].find(node=>node.dataset.eventId===event.id);
    assert.ok(message,'the saved event appears in the conversation');
    assert.equal(doc.querySelector('#tab-workflow').getAttribute('aria-selected'),'true');
    assert.equal(message.querySelector('.wf-title').textContent,event.title);
    if(event.timestamp)assert.equal(message.querySelector('time').dateTime,new Date(event.timestamp).toISOString());
    const disclosure=message.querySelector('.wf-inspect');disclosure.open=true;
    await until(()=>message.querySelector('.wf-section'),'saved workflow evidence expanded');
    assert.equal(message.querySelector('.wf-section-name').textContent,evidence.sections[0].label);
    assert.equal(message.querySelector('.wf-raw').textContent,evidence.sections[0].text);
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();snapshot.content_version='workflow-refresh-fixture';
    streams.at(-1).snapshot(snapshot);
    await until(()=>doc.querySelector('.wf-refresh')?.disabled===false,'workflow refresh finished');
    assert.equal([...doc.querySelectorAll('.wf-message')].find(node=>node.dataset.eventId===event.id),message);
    assert.equal(disclosure.open,true);
    doc.querySelector('#follow-button').click();assert.equal(doc.querySelector('.wf-connection').textContent,'Updates paused');
    doc.querySelector('#tab-events').click();assert.equal(doc.querySelector('.workflow'),null);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('parallel execution runtime updates preserve recorded architecture and pending queue semantics',async()=>{
  const {dom,doc,streams,errors}=await mounted();
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='parallel-ui-fixture';
    snapshot.runtime={available:true,active:true,stage:'generating',parallel:{schema:'sciel-parallel-runtime/1',
      wave:3,phase:'generation',workers:4,jobs:4,pending_llm_calls:2,pending_evaluations:1}};
    snapshot.architecture.sections=snapshot.architecture.sections.filter(section=>section.id!=='execution');
    snapshot.architecture.sections.push({id:'execution',title:'Execution and shared resource limits',fields:[
      {key:'parallel_search.workers',label:'Concurrent jobs per run',value:4,status:'recorded'},
      {key:'parallel_search.host_evaluator_slots',label:'Shared host evaluator slots',value:2,status:'recorded'}]});
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-architecture').click();
    assert.match(doc.querySelector('[data-field="parallel_search.workers"]').textContent,/4/);
    assert.match(doc.getElementById('runtime-bar').textContent,/Wave 3 · generation · 4 workers · pending LLM 2 \/ evaluation 1/);
    const configuration=doc.querySelector('.architecture-configuration');configuration.open=true;
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:'running'},runtime:{available:true,active:true,stage:'research',
      parallel:{schema:'sciel-parallel-runtime/1',wave:3,phase:'conclusion',workers:4,jobs:4,pending_llm_calls:3,pending_evaluations:0}}});
    assert.equal(doc.querySelector('.architecture-configuration'),configuration);assert.equal(configuration.open,true);
    assert.match(doc.getElementById('runtime-bar').textContent,/Wave 3 · conclusion · 4 workers · pending LLM 3 \/ evaluation 0/);
    assert.match(doc.querySelector('.runtime-parallel').title,/not measured executing/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('timings, start provenance and population reflect recorded data and open saved member code',async()=>{
  const {dom,doc,streams,errors}=await mounted();
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='population-timing-fixture';
    snapshot.start_protocol={kind:'fresh',label:'Fresh start · canonical seed + portfolio seeding'};
    snapshot.timing={session:{elapsed_seconds:3672},last_hypothesis_age_seconds:18,
      intervals:{last_seconds:73,median_seconds:80,count:2,source:'recorded_monotonic'},
      hypotheses:[{experiment_id:'r000003a1'}],coverage:{untimed_hypotheses:0,gaps:[]}};
    snapshot.population={available:true,source:'checkpoint',iteration:4,stale:false,island_count:1,
      descriptor:{kind:'pca2_v3'},layout:{kind:'map_elites',grid_bins:10,x_label:'Recorded descriptor bin',y_label:'Score bin'},
      islands:[{id:0,best_score:.926955,member_count:2,grid_cell_count:1,members_available:true,grid_available:true,
        grid:[{x:3,y:9,score:.926955,candidate_id:'p3'}],
        members:[{id:'p3',score:.926955,code_available:true,grid_elite:true,archive_member:true},
                 {id:'<img src=x onerror=alert(1)>',score:.4,code_available:false,grid_elite:null}]}],
      archive:{count:1,members:[{id:'p3',score:.926955,code_available:true}]},warnings:[]};
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.getElementById('run-elapsed').textContent,'01:01:12');
    assert.equal(doc.getElementById('hypothesis-interval').textContent,'00:01:13');
    assert.match(doc.getElementById('timing-note').textContent,/recorded engine timestamps/);
    assert.match(doc.getElementById('run-note').textContent,/Fresh start/);
    doc.getElementById('tab-population').click();
    assert.equal(doc.getElementById('tab-population').previousElementSibling.id,'tab-events');
    assert.equal(doc.querySelectorAll('.population-island').length,1);
    assert.equal(doc.querySelectorAll('.population-empty-cell').length,100);
    assert.equal(doc.querySelectorAll('.population-filled-cell').length,1);
    assert.match(doc.getElementById('tab-content').textContent,/Embeddings can define/);
    assert.match(doc.getElementById('tab-content').textContent,/Cell elite/);
    assert.equal(doc.querySelectorAll('.population img').length,0);
    const svg=doc.querySelector('.population svg');
    const territory=doc.querySelector('#population-map svg');
    assert.ok(territory,'interactive territory map is mounted');
    doc.querySelector('#population-map [data-program="p3"]').dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true}));
    assert.equal(doc.querySelector('#population-map .territory-card-title').textContent,'p3');
    doc.getElementById('population-details').open=true;
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:snapshot.run.status},runtime:null,
      timing:{session:{elapsed_seconds:3674},last_hypothesis_age_seconds:20,intervals:snapshot.timing.intervals}});
    assert.equal(doc.getElementById('run-elapsed').textContent,'01:01:14');
    assert.equal(doc.getElementById('last-hypothesis-id').textContent,'r000003a1');
    assert.equal(doc.querySelector('.population svg'),svg,'heartbeat does not rebuild population');
    assert.equal(doc.querySelector('#population-map svg'),territory,'heartbeat preserves the interactive map');
    snapshot.content_version='population-new-observation';
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelector('#population-map svg'),territory,'content update preserves the map DOM');
    assert.equal(doc.querySelector('#population-map .territory-card-title').textContent,'p3','selected program survives content update');
    assert.equal(doc.getElementById('population-details').open,true,'storage disclosure persists');
    doc.querySelector('.population-members [data-candidate="p3"]').click();
    await until(()=>doc.querySelector('.code-view'),'population code loaded');
    assert.equal(doc.getElementById('tab-code').getAttribute('aria-selected'),'true');
    assert.equal(doc.querySelector('#population-map'),null,'leaving the tab destroys the map');
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('session clocks tick only while live, freeze when paused and reset honestly on resume',async()=>{
  let now=0, tick;
  const {dom,doc,streams,errors}=await mounted({configure:w=>{
    Object.defineProperty(w.performance,'now',{value:()=>now});
    const interval=w.setInterval.bind(w);
    w.setInterval=(fn,ms)=>ms===1000?(tick=fn,1):interval(fn,ms);
  }});
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='live-timing';
    snapshot.runtime={available:true,active:true,stage:'generating',heartbeat_age_seconds:2,stale_after_seconds:10};
    snapshot.run.status='running';
    snapshot.timing={live:true,session:{elapsed_seconds:60},last_hypothesis_age_seconds:5,
      last_hypothesis_id:'r1',intervals:{count:1,last_seconds:20,median_seconds:20,source:'recorded_monotonic'},
      hypotheses:[{experiment_id:'r1',source:'recorded'}],coverage:{gaps:[]}};
    streams.at(-1).snapshot(snapshot);
    const plot=doc.querySelector('#score-chart svg');
    now=2500;tick();
    assert.equal(doc.getElementById('run-elapsed').textContent,'00:01:02');
    assert.equal(doc.getElementById('hypothesis-age').textContent,'00:00:07');
    assert.equal(doc.querySelector('#score-chart svg'),plot,'clock tick does not redraw plot');
    now=20000;tick();
    assert.equal(doc.getElementById('run-elapsed').textContent,'00:01:08','stale heartbeat bounds extrapolation');
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:'paused'},runtime:{available:true,active:false},
      timing:{live:false,session:{elapsed_seconds:65},last_hypothesis_age_seconds:10}});
    now=30000;tick();
    assert.equal(doc.getElementById('run-elapsed').textContent,'00:01:05');
    assert.equal(doc.getElementById('hypothesis-age').textContent,'00:00:10');
    assert.match(doc.getElementById('timing-note').textContent,/frozen/);
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:'running'},runtime:snapshot.runtime,
      timing:{live:true,session:{elapsed_seconds:2},last_hypothesis_age_seconds:null,last_hypothesis_id:null,
        intervals:{count:1,last_seconds:null,median_seconds:20,source:'recorded_monotonic'}}});
    assert.equal(doc.getElementById('last-hypothesis-id').textContent,'Not recorded in this session');
    assert.equal(doc.getElementById('hypothesis-age').textContent,'—');
    assert.equal(doc.getElementById('hypothesis-interval').textContent,'—');
    now=33000;tick();
    assert.equal(doc.getElementById('run-elapsed').textContent,'00:00:05');
    doc.getElementById('follow-button').click();
    now=35000;tick();
    assert.equal(doc.getElementById('run-elapsed').textContent,'00:00:05','pausing the view freezes its clock');
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('LLM calls tab expands saved exchanges and reference comparison stays collapsed initially',async()=>{
  const calls=[];
  const call={id:'test-call',role:'G',reference:'r1',experiment_id:'r1',iteration:1,
    model:'recorded-model',status:'returned',started_at:'2026-09-19T00:00:00Z'};
  const fetchOverride=url=>{
    if(!url.includes('/llm-calls'))return;
    calls.push(url);
    const value=url.includes('?')?{calls:[call],total:1,next_offset:null}:{...call,
      prompt:{text:'The full recorded request.',available:true,truncated:false},
      response:{text:'The raw recorded response.',available:true,truncated:false}};
    return Promise.resolve({ok:true,json:async()=>value});
  };
  const {dom,doc,streams,errors}=await mounted({fetchOverride});
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='calls-reference';
    snapshot.benchmark={label:'Tolerance-matched reference',value:2.6,current_value:2.5,task_target:2.635,metric:'Sum of radii',references:[]};
    streams.at(-1).snapshot(snapshot);
    const disclosure=doc.querySelector('.benchmark-disclosure');
    assert.equal(disclosure.open,false);
    assert.match(disclosure.querySelector('summary').textContent,/Tolerance-matched reference/);
    disclosure.open=true;
    const programCall=doc.querySelector('tr[data-candidate] [data-llm-experiment]');
    assert.ok(programCall,'Programs rows link to their recorded calls');
    programCall.click();
    await until(()=>doc.querySelector('.llm-call'),'LLM call index');
    assert.equal(calls.length,1);
    assert.equal(doc.getElementById('tab-llm').getAttribute('aria-selected'),'true');
    doc.querySelector('.llm-call').open=true;
    await until(()=>doc.querySelector('.llm-raw'),'full LLM call');
    assert.match(doc.getElementById('tab-content').textContent,/The full recorded request/);
    const saved=doc.querySelector('.llm-call');
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:snapshot.run.status},runtime:null});
    assert.equal(doc.querySelector('.llm-call'),saved,'runtime heartbeat does not rebuild transcripts');
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('progress card follows exact program lineage and opens code and LLM for that candidate',async()=>{
  const requests=[];
  const fetchOverride=url=>{
    if(url.endsWith('/program/chart-b')){
      requests.push(url);
      return Promise.resolve({ok:true,json:async()=>({id:'chart-b',code:'saved chart child\n',
        parent_code:'saved seed\n',parent_id:'seed-2',diff:'-saved seed\n+saved chart child\n',
        diff_kind:'full_sources',code_source:'checkpoint'})});
    }
    if(url.includes('/llm-calls?')){
      requests.push(url);
      return Promise.resolve({ok:true,json:async()=>({calls:[],total:0,next_offset:null})});
    }
  };
  const {dom,w,doc,streams,errors}=await mounted({fetchOverride});
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='interactive-lineage';snapshot.benchmark=null;
    const seed={candidate_id:'seed-1',candidate_ids:['seed-1','seed-2'],parent_ids:[],kind:'seed',
      iteration:0,score:.1,best_score:.1,cost_total:0,code_available:true,llm_available:false,status:'seed'};
    const a={candidate_id:'chart-a',experiment_id:'research-a',parent_ids:['seed-1'],iteration:1,
      score:.4,best_score:.4,cost_total:.1,code_available:true,llm_available:true,status:'evaluated'};
    const b={candidate_id:'chart-b',experiment_id:'research-b',parent_ids:['seed-2'],iteration:1,
      score:.8,parent_score:.1,best_score:.8,cost_total:.2,code_available:true,llm_available:true,
      status:'evaluated',hypothesis:'Exact recorded child B',operator:'diff',island:1};
    for(const row of [seed,a,b]){row.metric_display=measured(row.score);row.best_metric_display=measured(row.best_score);if(row.parent_score!==undefined)row.parent_metric_display=measured(row.parent_score);}
    snapshot.curves=[seed,a,b];
    snapshot.programs=[seed,{...seed,candidate_id:'seed-2',candidate_ids:[]},a,b];
    snapshot.trials=[{id:'research-a',candidate_id:'chart-a',iteration:1,parent_id:'seed-1',score:.4,code_available:true},
      {id:'research-b',candidate_id:'chart-b',iteration:1,parent_id:'seed-2',score:.8,code_available:true}];
    snapshot.hypotheses=[];
    streams.at(-1).snapshot(snapshot);
    const dot=doc.querySelector('.chart-dot[data-index="2"]');
    assert.ok(dot);
    dot.dispatchEvent(new w.Event('pointerenter'));
    assert.match(doc.querySelector('.chart-program-card').textContent,/Exact recorded child B/);
    assert.ok(doc.querySelector('.chart-family-edge[data-child="chart-b"]'));
    assert.ok(doc.querySelector('.chart-program-card [data-program="seed-2"]'));
    dot.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    const svg=doc.querySelector('#score-chart svg');
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:snapshot.run.status},runtime:null});
    assert.equal(doc.querySelector('#score-chart svg'),svg,'heartbeat preserves pinned graph');
    doc.querySelector('[data-chart-inspect]').click();
    await until(()=>doc.querySelector('.code-view'),'selected chart source');
    assert.match(doc.querySelector('.code-view').textContent,/saved chart child/);
    assert.ok(requests.some(path=>path.endsWith('/program/chart-b')),'equal iteration does not select chart-a');
    doc.querySelector('[data-chart-llm]').click();
    await until(()=>requests.some(path=>path.includes('/llm-calls?')),'selected chart LLM calls');
    assert.ok(requests.some(path=>path.includes('q=research-b')));
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('bandits and RL show recorded status, credit, probabilities and bounded charts',async()=>{
  const {dom,doc,streams,errors}=await mounted();
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='learning-fixture';
    snapshot.learning={components:[{id:'operator',label:'Operator bandit',status:'online',detail:'Learns from credited records.'},
      {id:'mode',label:'Mode bandit',status:'disabled',detail:'Not enabled.'},
      {id:'rl',label:'Neural policy training',status:'disabled',detail:'No optimizer updates.'},
      {id:'embed',label:'Code embedding',status:'frozen',detail:'<img src=x onerror=alert(1)>'}],
      summary:{iterations:1200,record_events:1,credited_operator_updates:0,cumulative_reward:1.25},history_limit:300,
      operator:{arms:[{name:'diff',choices:1,executions:0,evaluated_count:0,record_count:0,credited_updates:0,cumulative_reward:0},
        {name:'full_rewrite',choices:0,executions:1,evaluated_count:1,record_count:1,credited_updates:0,cumulative_reward:1.25}],
        history:Array.from({length:1200},(_,i)=>({iteration:i+1,island:0,operator:'full_rewrite',selected_operator:'diff',selected_probability:.33,reward:1.25,escalated:true,forced:false,stats:{diff:0,full_rewrite:0}})),
        checkpoint:{iteration:1190,stale:true,window:50,temperature:.5,floor:.05,arms:[{name:'diff',window_count:0,window_max:0}]}},
      controller:{source:'static',history:[{iteration:9,iteration_before:8,event_seq:2,mode:'exploit',effective_mode:'base',plateau:false,distribution:{base:.8,exploit:.2},propensity:.2,phase:0},
        {iteration:null,iteration_before:9,event_seq:3,mode:'base',effective_mode:null,plateau:false,distribution:{base:.8,exploit:.2},propensity:.8,phase:0}]},
      rewards:Array.from({length:1200},(_,i)=>({iteration:i+1,reward:i===0?1.25:0,cumulative_reward:1.25})),notes:['Missing observations remain unknown.']};
    streams.at(-1).snapshot(snapshot);doc.getElementById('tab-learning').click();
    assert.equal(doc.getElementById('tab-learning').getAttribute('aria-selected'),'true');
    assert.match(doc.querySelector('[data-component="operator"]').textContent,/Online adaptation/);
    assert.match(doc.querySelector('[data-component="rl"]').textContent,/Disabled/);
    assert.match(doc.querySelector('[data-component="embed"]').textContent,/Frozen inference/);
    assert.equal(doc.querySelectorAll('.learning img').length,0);
    assert.equal(doc.querySelectorAll('.learning-chart').length,4);
    for(const svg of doc.querySelectorAll('.learning-chart'))assert.ok(svg.querySelectorAll('circle').length<=2400);
    assert.equal(doc.querySelectorAll('.learning-decisions tbody tr').length,30);
    assert.match(doc.querySelector('.learning-decisions').textContent,/diff → full_rewrite/);
    assert.match(doc.querySelector('.learning-decisions').textContent,/Escalated/);
    assert.match(doc.querySelector('.learning').textContent,/earlier than the live journal/);
    assert.match(doc.querySelector('.learning').textContent,/not an RL training loss/);
    const modeChart=doc.querySelectorAll('.learning-chart')[1];
    assert.equal(modeChart.querySelectorAll('circle').length,4,'pending controller decisions remain visible');
    assert.match(modeChart.textContent,/Recorded pre-step iteration 8/);
    const chart=doc.querySelector('.learning-chart');
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:snapshot.run.status},runtime:null});
    assert.equal(doc.querySelector('.learning-chart'),chart,'heartbeat does not rebuild bandit charts');
    snapshot.content_version='learning-presets';
    snapshot.learning.controller={source:'preset weights',history:[
      {source:'preset_weights',iteration:10,iteration_before:9,mode:'explore',effective_mode:'explore',adaptive:true,distribution:{base:.7,exploit:.2,explore:.1},propensity:.1},
      {source:'preset_weights',iteration:null,iteration_before:10,mode:'base',effective_mode:null,adaptive:true,distribution:{base:.75,exploit:.15,explore:.1},propensity:.75}],
      preset_weights:{available:true,iteration:9,stale:true,updates:8,learning_rate:.1,exploration:.1,max_importance_reward:10,
        log_weights:{base:0,exploit:-1.5,explore:-2,'<img src=x onerror=alert(1)>':-3}}};
    streams.at(-1).snapshot(snapshot);
    assert.match(doc.querySelector('.learning-preset-state').textContent,/Checkpoint iteration 9 · earlier than the live journal/);
    assert.match(doc.querySelector('.learning-preset-state').textContent,/Recorded updates: 8/);
    assert.match(doc.querySelector('.learning-preset-state').textContent,/Log weights are saved state, not probabilities/);
    assert.match(doc.querySelector('.learning-preset-state').textContent,/-1\.500/);
    assert.equal(doc.querySelectorAll('.learning img').length,0);
    assert.match(doc.querySelector('.learning-controller-decisions').textContent,/Preset weights/);
    assert.match(doc.querySelector('.learning-controller-decisions').textContent,/Not recorded/);
    assert.equal(doc.querySelectorAll('.learning-chart')[1].querySelectorAll('circle').length,6);
    assert.match(doc.querySelectorAll('.learning-chart')[1].textContent,/explore · Recorded pre-step iteration 9 · 10\.00%/);
    snapshot.content_version='learning-no-checkpoint';snapshot.learning.operator.checkpoint={available:false,iteration:null,arms:[]};
    snapshot.learning.controller.preset_weights={available:false};
    streams.at(-1).snapshot(snapshot);
    assert.match(doc.querySelector('.learning').textContent,/No saved operator bandit state yet/);
    assert.match(doc.querySelector('.learning').textContent,/No saved preset weights yet/);
    snapshot.content_version='learning-missing';snapshot.learning=null;streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelectorAll('.learning-chart').length,0);
    assert.match(doc.getElementById('tab-content').textContent,/not recorded/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('bootstrap attempts do not present the zero search counter as all evaluated programs',async()=>{
  const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
  snapshot.content_version='bootstrap-counter-scope';
  snapshot.stats={...snapshot.stats,evaluations:0,iterations:0,attempts:4};
  snapshot.trials=snapshot.trials.slice(0,4);
  snapshot.runtime={available:true,active:true,stage:'evaluating',parallel:{
    schema:'sciel-parallel-runtime/1',wave:2,phase:'bootstrap',workers:4,jobs:4,
    pending_llm_calls:0,pending_evaluations:4}};
  const before=JSON.stringify(snapshot.stats);
  const {dom,doc,errors}=await mounted({
    fetchOverride:url=>url.endsWith('/api/runs/'+fixtureRun.id)?Promise.resolve({ok:true,json:async()=>snapshot}):null,
    ready:doc=>doc.getElementById('evaluations').textContent==='0'});
  try{
    const counter=doc.getElementById('evaluations');
    assert.equal(counter.textContent,'0');
    assert.equal(counter.parentElement.querySelector('.metric-label').textContent,'Successful search evaluations');
    assert.equal(doc.getElementById('evaluation-scope').textContent,'Excludes seed, bootstrap and failed evaluations.');
    assert.match(counter.title,/including successful remeasurements/);
    assert.equal(doc.getElementById('trials-tab-count').textContent,'4');
    assert.match(doc.getElementById('chart-end').textContent,/0 iterations · 0 search evaluations/);
    assert.match(doc.getElementById('chart-end').title,/Excludes seed, bootstrap and failed evaluations/);
    assert.equal(JSON.stringify(snapshot.stats),before,'UI does not change scientific counter values');
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('measured output repeats remain visible separately from admitted search evaluations',async()=>{
  const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
  snapshot.stats={...snapshot.stats,evaluations:0,measured_results:4,repeated_outputs:3};
  const {dom,doc,errors}=await mounted({
    fetchOverride:url=>url.endsWith('/api/runs/'+fixtureRun.id)?Promise.resolve({ok:true,json:async()=>snapshot}):null,
    ready:doc=>doc.getElementById('evaluations').textContent==='0'});
  try{
    assert.match(doc.getElementById('attempts').textContent,/4 measured results · 3 exact output repeats/);
    assert.match(doc.getElementById('attempts').title,/do not prove equivalent algorithms/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('synthetic API records render score, programs, hypotheses, knowledge and parent diff',async()=>{
  const {dom,w,doc,errors,copied}=await mounted();
  try{
    assert.equal(doc.querySelectorAll('[data-run]').length,7);
    assert.match(doc.getElementById('run-title').textContent,/Synthetic study/);
    assert.match(doc.getElementById('run-status').textContent,/Completed/);
    assert.equal(doc.getElementById('best-score').textContent,'Not measured','unbound legacy score must not become a native observation');
    assert.equal(doc.getElementById('evaluations').textContent,'4');
    assert.equal(doc.getElementById('cost').textContent,'$0.1157');
    assert.equal(doc.querySelectorAll('tbody tr').length,7);
    assert.match(doc.querySelector('#chart-outcomes summary').textContent,/unavailable/);
    doc.getElementById('tab-hypotheses').click();
    assert.equal(doc.querySelectorAll('.research-card').length,7);
    const search=doc.getElementById('content-search');
    search.value='r000002a1';search.dispatchEvent(new w.Event('input',{bubbles:true}));
    assert.equal(doc.querySelectorAll('.research-card').length,1);
    doc.querySelector('[data-candidate="p3"]').click();
    await until(()=>doc.querySelector('.code-view'),'diff loaded');
    assert.ok(doc.querySelector('.code-line.add'));
    assert.ok(doc.querySelector('.code-line.remove'));
    doc.querySelector('[data-code-mode="code"]').click();
    assert.match(doc.querySelector('.code-view').textContent,/def construct_packing/);
    doc.getElementById('copy-code').click();
    await until(()=>copied(),'clipboard');
    assert.match(copied(),/def construct_packing/);
    doc.getElementById('tab-lessons').click();
    assert.ok(doc.querySelectorAll('.research-card').length>=1);
    doc.querySelector('[data-evidence]').click();
    assert.equal(doc.getElementById('tab-hypotheses').getAttribute('aria-selected'),'true');
    assert.ok(doc.querySelector('.research-card'));
    doc.getElementById('all-events-button').click();
    assert.equal(doc.querySelectorAll('#tab-content details').length,60);
    doc.querySelector('[data-more]').click();
    assert.equal(doc.querySelectorAll('#tab-content details').length,75);
    doc.getElementById('help-button').click();
    assert.equal(doc.getElementById('help-dialog').open,true);
    doc.getElementById('help-done').click();
    assert.equal(doc.getElementById('help-dialog').open,false);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('stream updates are safe, pauseable, preserve selection, and do not execute research text',async()=>{
  const {dom,w,doc,errors,streams}=await mounted();
  try{
    const id=new URL(w.location.href).searchParams.get('run');
    const snapshot=await (await fetch(base+'/api/runs/'+id)).json();
    doc.getElementById('tab-hypotheses').click();
    const injected=structuredClone(snapshot);
    injected.hypotheses[0].hypothesis.text='<img src=x onerror="window.owned=true">';
    injected.stats.best_score=.94;injected.stats.best_metric_display=measured(.94);
    streams.at(-1).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent,'0.940000');
    assert.equal(doc.querySelectorAll('.research-card img').length,0);
    assert.match(doc.getElementById('tab-content').textContent,/<img src=x/);
    assert.equal(w.owned,undefined);
    assert.equal(doc.getElementById('tab-hypotheses').getAttribute('aria-selected'),'true');
    doc.getElementById('follow-button').click();
    assert.equal(streams.at(-1).closed,true);
    assert.match(doc.getElementById('connection').textContent,/paused/);
    injected.stats.best_score=.95;injected.stats.best_metric_display=measured(.95);streams.at(-1).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent,'0.940000');
    doc.getElementById('follow-button').click();
    assert.equal(streams.at(-1).closed,false);
    // A queued frame from a closed connection cannot overwrite newer state.
    streams.at(-2).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent,'0.940000');
    streams.at(-1).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent,'0.950000');
    doc.querySelector('[data-axis="cost_total"]').click();
    assert.match(doc.querySelector('#chart-outcomes summary').textContent,/unavailable/);
    doc.getElementById('run-search').value='cards_off';
    doc.getElementById('run-search').dispatchEvent(new w.Event('input'));
    assert.equal(doc.querySelectorAll('[data-run]').length,2);
    doc.querySelector('[data-run]').click();
    await until(()=>doc.getElementById('run-title').textContent.includes('OFF'),'run switched');
    await until(()=>streams.at(-1).url.includes(new URL(w.location.href).searchParams.get('run')),'new run loaded');
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('architecture shows recorded options, zero values, unknowns and verified runtime without executing text',async()=>{
  const {dom,doc,streams,errors}=await mounted();
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.architecture={schema:'sciel-architecture/1',source:'run_start.config',recorded:true,summary:'Actual configuration of the selected run.',
      stages:[
        {id:'selection',label:'Select parent',status:'enabled',description:'Sample from the population'},
        {id:'generation',label:'Generate program',status:'enabled',description:'Use the recorded model'},
        {id:'evaluation',label:'Evaluate',status:'enabled',description:'Measure the candidate'},
        {id:'admission',label:'Update population',status:'enabled',description:'Retain eligible candidates'},
        ...['conclusion','reflection','retrieval'].map(id=>({id,label:id,status:'disabled',description:'Optional research stage'}))
      ],edges:[{from:'generation',to:'evaluation',label:'candidate'}],sections:[{id:'population',title:'Population',fields:[
        {key:'capacity',label:'Capacity',value:0,status:'recorded',source:'run_start.config'},
        {key:'dynamic',label:'Dynamic islands',value:false,status:'recorded'},
        {key:'unknown',label:'Unrecorded option',value:null,status:'unknown'},
        ...['budget','max_iterations','research.max_aux_calls'].map(key=>({key,label:key,value:null,status:'recorded'})),
        {key:'research.model',label:'Dedicated model',value:null,status:'recorded'},
        {key:'unsafe',label:'Recorded model',value:'<img src=x onerror="window.owned=true">',status:'recorded'}
      ]}],warnings:['Only recorded values are shown.']};
    snapshot.runtime={available:true,status:'running',stage:'generating',active:true,heartbeat_at:new Date().toISOString(),heartbeat_age_seconds:2,pid:12345,reason:'Verified local engine process'};
    snapshot.run.status='running';
    snapshot.stats.cost_status='estimated';
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-architecture').click();
    assert.equal(doc.querySelectorAll('.architecture-stage').length,7);
    assert.equal(doc.querySelectorAll('.architecture-stage.disabled').length,3);
    assert.ok(doc.querySelector('[data-stage="generation"].current'));
    assert.equal(doc.querySelector('[data-field="capacity"] dd').textContent,'0');
    assert.equal(doc.querySelector('[data-field="dynamic"] dd').textContent,'Disabled');
    assert.equal(doc.querySelector('[data-field="unknown"] dd').textContent,'Not recorded');
    for(const key of ['budget','max_iterations','research.max_aux_calls'])assert.equal(doc.querySelector('[data-field="'+key+'"] dd').textContent,'Unlimited');
    assert.equal(doc.querySelector('[data-field="research.model"] dd').textContent,'Not set');
    assert.equal(doc.querySelectorAll('.architecture img').length,0);
    assert.match(doc.querySelector('[data-field="unsafe"]').textContent,/<img src=x/);
    assert.match(doc.getElementById('runtime-bar').textContent,/Generating a candidate/);
    assert.match(doc.getElementById('runtime-bar').textContent,/Heartbeat 2s ago/);
    assert.match(doc.getElementById('cost-note').textContent,/Estimated/);
    snapshot.runtime.active=false;snapshot.runtime.stage='finished';snapshot.run.status='completed';
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelector('.architecture-stage.current'),null);
    assert.equal(doc.querySelector('.runtime-indicator.live'),null);
    assert.match(doc.getElementById('runtime-bar').textContent,/Run finished/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('architecture graph traces recorded run mechanisms with keyboard selection and stable runtime phases',async()=>{
  const {dom,w,doc,streams,errors}=await mounted();
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    const unsafe='<img src=x onerror="window.owned=true">';
    const node=(id,label,kind='core',extra={})=>({id,label,subtitle:'Recorded '+id,kind,status:'enabled',detail:label+' role for this run.',features:[],...extra});
    const graph={
      nodes:[node('parent','Novelty-chain parent','rule'),node('operator','Choose operator'),
        node('operator_bandit','Adaptive operator bandit','online',{features:['Window max reward',unsafe]}),
        node('generation','Generate with model A','core',{phase:'generating',subtitle:'Provider / model A',detail:'Recorded model A. '+unsafe}),
        node('evaluation','Evaluate the candidate','core',{phase:'evaluating'}),
        node('population','Population archive'),node('reward','Improvement reward','core'),node('conclusion','Conclusion','knowledge',{phase:'research'}),
        node('reflection','Reflection','knowledge',{phase:'research'}),node('memory','Research memory','knowledge'),
        node('descriptor',unsafe,'frozen',{subtitle:unsafe,detail:unsafe})],
      edges:[{from:'parent',to:'operator',label:'Parent identity',kind:'flow'},
        {from:'operator_bandit',to:'operator',label:'Operator sampling weights',kind:'control'},
        {from:'operator',to:'generation',label:'Selected generation operator',kind:'flow'},
        {from:'generation',to:'evaluation',label:'Candidate source',kind:'flow'},
        {from:'evaluation',to:'population',label:'Measured score',kind:'flow'},
        {from:'evaluation',to:'reward',label:'Measured improvement',kind:'reward'},
        {from:'reward',to:'operator_bandit',label:'Eligible island improvement',kind:'reward'},
        {from:'evaluation',to:'conclusion',label:'Observed evidence',kind:'knowledge'},
        {from:'conclusion',to:'reflection',label:'Tested conclusions',kind:'knowledge'},
        {from:'reflection',to:'memory',label:unsafe,kind:'knowledge'},
        {from:'memory',to:'generation',label:'Retrieved lessons',kind:'knowledge'}],
      inactive:[{id:'mode_mlp',label:'Mode MLP',status:'disabled',detail:unsafe}],
      summary:['Model A · recorded selection policy',unsafe],notes:[unsafe]
    };
    snapshot.content_version='architecture-graph-a';
    snapshot.architecture={schema:'sciel-architecture/2',source:'run_start.config',recorded:true,
      summary:'Mechanisms recorded for this run.',graph,stages:[],edges:[],sections:[],warnings:[]};
    snapshot.run.status='running';
    snapshot.runtime={available:true,active:true,status:'running',stage:'generating',heartbeat_age_seconds:1};
    streams.at(-1).snapshot(snapshot);doc.getElementById('tab-architecture').click();
    const map=doc.querySelector('.architecture-map');
    const getNode=id=>doc.querySelector('.architecture-node[data-node="'+id+'"]');
    assert.ok(map);
    assert.equal(doc.querySelectorAll('.architecture-node').length,graph.nodes.length);
    assert.deepEqual([...map.querySelectorAll('.arch-pipeline > .arch-step .arch-step-heading h4')].map(el=>el.textContent),['Select','Generate','Evaluate','Store']);
    assert.equal(getNode('operator_bandit').closest('.arch-step').dataset.step,'select','learning controls sit at the choice they affect');
    assert.equal(getNode('generation').closest('.arch-step').dataset.step,'generate');
    assert.equal(getNode('descriptor').closest('.arch-step').dataset.step,'store');
    assert.match(map.querySelector('.arch-model').textContent,/Provider \/ model A/);
    assert.equal(map.querySelectorAll('.arch-feedback[data-feedback]').length,2);
    assert.match(map.querySelector('[data-feedback="learning"] [data-return-step="select"]').textContent,/1 · Select/);
    assert.match(map.querySelector('[data-feedback="knowledge"] [data-return-step="generate"]').textContent,/2 · Generate/);
    assert.equal(getNode('generation').tagName,'BUTTON');
    assert.equal(getNode('generation').tabIndex,0);
    assert.equal(getNode('generation').classList.contains('current'),true);
    assert.equal(getNode('mode_mlp'),null,'disabled mechanism belongs outside the active graph');
    assert.match(doc.querySelector('.graph-inactive').textContent,/Mode MLP/);
    assert.equal(doc.querySelector('.graph-inspector').hidden,true,'details stay collapsed until a mechanism is selected');
    getNode('generation').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
    assert.equal(map.dataset.selectedNode,'generation');
    assert.equal(getNode('generation').getAttribute('aria-pressed'),'true');
    assert.equal(getNode('evaluation').classList.contains('related'),true);
    assert.equal(getNode('reflection').classList.contains('related'),false);
    assert.equal(doc.querySelector('.graph-inspector').hidden,false);
    assert.match(doc.querySelector('.graph-inspector').textContent,/Recorded model A/);
    assert.match(doc.querySelector('.graph-inspector').textContent,/Candidate source/);
    assert.match(doc.querySelector('.graph-inspector').textContent,/Selected generation operator/);
    assert.match(doc.querySelector('.graph-inspector').textContent,/Retrieved lessons/);
    assert.doesNotMatch(doc.querySelector('.graph-inspector').textContent,/Observed evidence|Tested conclusions/);
    const enter=new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});
    getNode('operator_bandit').focus();
    getNode('operator_bandit').dispatchEvent(enter);
    assert.equal(enter.defaultPrevented,true);assert.equal(map.dataset.selectedNode,'operator_bandit');
    assert.match(doc.querySelector('.graph-inspector').textContent,/Window max reward/);
    const space=new w.KeyboardEvent('keydown',{key:' ',bubbles:true,cancelable:true});
    getNode('memory').focus();
    getNode('memory').dispatchEvent(space);
    assert.equal(space.defaultPrevented,true);assert.equal(map.dataset.selectedNode,'memory');
    assert.equal(getNode('operator_bandit').getAttribute('aria-pressed'),'false');
    assert.equal(getNode('memory').getAttribute('aria-pressed'),'true');
    const selectedNode=getNode('memory'),inspector=doc.querySelector('.graph-inspector'),inspectorHTML=inspector.innerHTML;
    const update={run:{id:fixtureRun.id,status:'running'},runtime:{available:true,active:true,status:'running',stage:'evaluating',heartbeat_age_seconds:2}};
    streams.at(-1).runtime(update);
    assert.equal(doc.querySelector('.architecture-map'),map);
    assert.equal(getNode('memory'),selectedNode,'heartbeat preserves the selected keyboard target');
    assert.equal(doc.activeElement,selectedNode,'heartbeat preserves keyboard focus');
    assert.equal(doc.querySelector('.graph-inspector'),inspector);assert.equal(inspector.innerHTML,inspectorHTML);
    assert.equal(map.dataset.selectedNode,'memory');assert.equal(getNode('memory').getAttribute('aria-pressed'),'true');
    assert.equal(getNode('evaluation').classList.contains('current'),true);
    assert.equal(getNode('generation').classList.contains('current'),false);
    update.runtime.stage='research';streams.at(-1).runtime(update);
    assert.equal(doc.querySelector('.architecture-node.current'),null,'generic research heartbeat does not identify conclusion or reflection');
    assert.equal(map.dataset.selectedNode,'memory');assert.equal(inspector.innerHTML,inspectorHTML);
    assert.equal(doc.querySelectorAll('.architecture img').length,0);assert.equal(w.owned,undefined);
    assert.match(map.textContent,/<img src=x/,'untrusted text remains visible as literal text');
    getNode('memory').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
    assert.equal(map.dataset.selectedNode,'');assert.equal(doc.querySelector('.architecture-node.selected'),null);
    assert.equal(inspector.hidden,true,'Escape collapses details again');
    map.querySelector('[data-return-step="select"]').click();
    assert.equal(doc.activeElement,getNode('parent'),'reward feedback returns keyboard focus to selection');
    map.querySelector('[data-return-step="generate"]').click();
    assert.equal(doc.activeElement,getNode('generation'),'knowledge feedback returns keyboard focus to generation');
    const target=runIndex.find(run=>run.id!==fixtureRun.id);
    const other=JSON.parse(JSON.stringify(snapshot));
    other.run={...snapshot.run,...target};other.content_version='architecture-graph-b';other.runtime=null;
    other.architecture.graph={nodes:[node('generation','Generate with model B','core',{subtitle:'Provider / model B'}),node('evaluation','Second evaluator'),node('population','Single archive')],
      edges:[{from:'generation',to:'evaluation',label:'Second-run candidate',kind:'flow'}],inactive:[],summary:['Model B'],notes:[]};
    w.fetch=url=>String(url)==='/api/runs/'+encodeURIComponent(target.id)?Promise.resolve(new Response(JSON.stringify(other),{headers:{'Content-Type':'application/json'}})):fetch(new URL(url,base));
    doc.querySelector('[data-run="'+target.id+'"]').click();
    await until(()=>doc.querySelector('.arch-model')?.textContent.includes('Provider / model B'),'new run architecture loaded');
    assert.equal(doc.querySelectorAll('.architecture-node').length,3);
    assert.equal(getNode('operator_bandit'),null);assert.equal(getNode('memory'),null);
    assert.doesNotMatch(doc.querySelector('.architecture-map').textContent,/model A|Adaptive operator bandit/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('failed run switch clears previous metrics, plot and runtime and ignores the closed stream',async()=>{
  const {dom,w,doc,streams,errors}=await mounted();
  try{
    const oldStream=streams.at(-1);
    const target=runIndex.find(run=>run.id!==fixtureRun.id);
    w.fetch=url=>String(url)==='/api/runs/'+encodeURIComponent(target.id)?Promise.resolve(new Response('',{status:503})):fetch(new URL(url,base));
    doc.querySelector('[data-run="'+target.id+'"]').click();
    assert.equal(doc.getElementById('best-score').textContent,'—');
    assert.equal(doc.getElementById('cost').textContent,'—');
    assert.equal(doc.querySelector('#score-chart svg'),null);
    assert.equal(doc.getElementById('runtime-bar').hidden,true);
    await until(()=>doc.getElementById('tab-content').textContent.includes('Unable to load this run'),'run error displayed');
    assert.match(doc.getElementById('error-banner').textContent,/503/);
    oldStream.dispatchEvent(new w.Event('unavailable'));
    assert.match(doc.getElementById('error-banner').textContent,/503/);
    assert.doesNotMatch(doc.getElementById('error-banner').textContent,/no longer available/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('runtime-only heartbeats preserve the source view and scroll position',async()=>{
  const {dom,doc,streams}=await mounted();
  try{
    doc.querySelector('[data-candidate="p3"]').click();
    await until(()=>doc.querySelector('.code-view'),'source view loaded');
    const view=doc.querySelector('.code-view');view.scrollTop=90;
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.runtime={available:true,status:'running',stage:'evaluating',active:true,heartbeat_age_seconds:1,pid:12345};
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelector('.code-view'),view);
    assert.equal(doc.querySelector('.code-view').scrollTop,90);
    assert.match(doc.getElementById('runtime-bar').textContent,/Evaluating a candidate/);
  }finally{dom.window.close();}
});

test('runtime events update status without replacing source, chart, or architecture nodes',async()=>{
  const {dom,doc,streams}=await mounted();
  try{
    doc.querySelector('[data-candidate="p3"]').click();
    await until(()=>doc.querySelector('.code-view'),'source view loaded');
    const source=doc.querySelector('.code-view'),chart=doc.querySelector('#score-chart svg');
    source.scrollTop=75;
    const update={run:{id:fixtureRun.id,status:'running',status_reason:null},runtime:{available:true,active:true,stage:'evaluating',heartbeat_age_seconds:1}};
    streams.at(-1).runtime(update);
    assert.equal(doc.querySelector('.code-view'),source);
    assert.equal(source.scrollTop,75);
    assert.equal(doc.querySelector('#score-chart svg'),chart);
    assert.match(doc.getElementById('run-status').textContent,/Running/);
    doc.getElementById('tab-architecture').click();
    const architecture=doc.querySelector('.architecture');
    update.runtime.stage='generating';streams.at(-1).runtime(update);
    assert.equal(doc.querySelector('.architecture'),architecture);
    assert.ok(doc.querySelector('.architecture-node[data-node="generation"].current'));
    update.run.status='stopped';update.runtime.active=false;update.runtime.stage='finished';
    streams.at(-1).runtime(update);
    assert.match(doc.getElementById('run-status').textContent,/Stopped/);
    assert.equal(doc.querySelector('.architecture-stage.current'),null);
    streams.at(-1).runtime({...update,run:{id:'other-run',status:'running'}});
    assert.match(doc.getElementById('run-status').textContent,/Stopped/);
  }finally{dom.window.close();}
});

test('long histories have bounded chart and event DOM while retaining selected samples and searchable history',async()=>{
  const {dom,w,doc,streams}=await mounted();
  try{
    const points=Array.from({length:130000},(_,iteration)=>({iteration,score:iteration===50001?-3:iteration===129999?5:.5,best_score:iteration===129999?5:.5}));
    let selected;
    const shown=w.renderChart(doc.getElementById('score-chart'),points,'iteration',42000,p=>selected=p);
    assert.equal(shown.total,130000);
    assert.ok(shown.displayed<=600);
    assert.ok(doc.querySelectorAll('.chart-dot').length<=600);
    doc.querySelector('.chart-dot.selected').dispatchEvent(new w.Event('click'));
    assert.equal(selected.iteration,42000);
    assert.match(doc.getElementById('score-chart').textContent,/Iteration 50001/);
    assert.match(doc.getElementById('score-chart').textContent,/Iteration 129999/);
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='bounded-event-fixture';
    snapshot.events=Array.from({length:650},(_,i)=>({seq:i+1,event:'decision',data:{text:i===0?'older-search-marker':'Recorded event'}}));
    streams.at(-1).snapshot(snapshot);doc.getElementById('tab-events').click();
    for(let i=0;i<9;i++)doc.querySelector('[data-more]')?.click();
    assert.equal(doc.querySelectorAll('.event-row').length,600);
    assert.equal(doc.querySelector('[data-more]'),null);
    assert.match(doc.querySelector('.display-limit').textContent,/650/);
    assert.ok([...doc.querySelectorAll('.event-data')].every(node=>!node.textContent));
    doc.querySelector('.event-row').open=true;
    await until(()=>doc.querySelector('.event-data').textContent.includes('Recorded event'),'lazy event data');
    const input=doc.getElementById('content-search');input.value='older-search-marker';input.dispatchEvent(new w.Event('input',{bubbles:true}));
    assert.equal(doc.querySelectorAll('.event-row').length,1);
    assert.equal(doc.querySelector('.event-row').dataset.seq,'1');
  }finally{dom.window.close();}
});

test('published reference is separate from task target, shows scope and accepts only web source links',async()=>{
  const {dom,doc,streams}=await mounted();
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.stats.best_score=2.5/2.635;snapshot.stats.best_metric_display=measured(2.5,snapshot.stats.best_score,'Sum of radii');
    snapshot.benchmark={label:'SOTA reference',value:2.6359830849176078,current_value:2.5,metric:'Sum of radii',task_target:2.635,target_metric:'Sum of radii',source_url:'https://www.gotherlabs.com/results/circle-packing-26-unit-square/',source_label:'Göther Labs · strict witness',note:'Published strict packing (τ = 0). The comparison is descriptive, not a proof of a new record.'};
    streams.at(-1).snapshot(snapshot);
    const panel=doc.getElementById('benchmark-comparison');
    assert.equal(doc.getElementById('best-score-label').textContent,'Sum of radii');
    assert.equal(doc.getElementById('best-score').textContent,'2.500000');
    assert.equal(doc.getElementById('best-score-comparison').textContent,'| 5.16% below SOTA');
    assert.match(doc.getElementById('chart-subtitle').textContent,/Sum of radii/);
    assert.equal(panel.previousElementSibling,doc.querySelector('.metrics'));
    assert.equal(panel.nextElementSibling,doc.querySelector('.overview-grid'));
    assert.match(panel.textContent,/SOTA reference/);
    assert.match(panel.textContent,/2\.500000000/);
    assert.match(panel.textContent,/2\.635983085/);
    assert.match(panel.textContent,/Gap to reference/);
    assert.match(panel.textContent,/not a proof of a new record/);
    assert.match(panel.querySelector('.benchmark-target').textContent,/Task target.*2\.635/);
    assert.equal(panel.querySelector('a').getAttribute('rel'),'noopener noreferrer');
    snapshot.benchmark.references=[{name:'ShinkaEvolve — reported',value_label:'2.635983099011548',tolerance:1e-6,status:'reported',source_name:'Sakana AI',source_url:'https://openreview.net/pdf?id=lKEdGCoDNC',gap_percent:.000001},
      {name:'Strict reference',value_label:'2.6359830849176077831865694854434817303966767982744748577457711298607038493344723396767997365079',tolerance:0,status:'audited',source_name:'Untrusted <script>',source_url:'javascript:alert(1)',gap_percent:-.000003}];
    streams.at(-1).snapshot(snapshot);
    assert.equal(panel.querySelectorAll('.benchmark-table tbody tr').length,2);
    assert.match(panel.textContent,/τ = 0 \(strict\)/);
    assert.match(panel.textContent,/0\.000001% below/);
    assert.match(panel.textContent,/0\.000003% above/);
    assert.equal(panel.querySelectorAll('.benchmark-table a').length,1);
    assert.equal(panel.querySelectorAll('script').length,0);
    snapshot.benchmark.references=[];
    snapshot.benchmark.source_url='javascript:window.owned=true';streams.at(-1).snapshot(snapshot);
    assert.equal(panel.querySelector('a'),null);
    snapshot.benchmark.current_value=snapshot.benchmark.value*1.01;snapshot.stats.best_score=snapshot.benchmark.current_value/2.635;snapshot.stats.best_metric_display=measured(snapshot.benchmark.current_value,snapshot.stats.best_score,'Sum of radii');streams.at(-1).snapshot(snapshot);
    assert.equal(doc.getElementById('best-score-comparison').textContent,'| 1.00% above SOTA');
    snapshot.benchmark.current_value=null;snapshot.stats.best_metric_display={...snapshot.stats.best_metric_display,status:'unknown',value:null};streams.at(-1).snapshot(snapshot);
    assert.equal(doc.getElementById('best-score').textContent,'Not measured');
    assert.equal(doc.getElementById('best-score-comparison').hidden,true);
  }finally{dom.window.close();}
});

test('default selection prefers a verified live run and then recent output, while explicit archives stay accessible',async()=>{
  const original=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
  const active={...fixtureRun,id:'live-test',name:'Live experiment',path:'outputs/live-test/run.jsonl',status:'running',last_modified:'2026-09-19T12:00:00Z'};
  const recent={...fixtureRun,id:'output-test',name:'Latest experiment',path:'outputs/latest/run.jsonl',status:'completed',last_modified:'2026-09-19T13:00:00Z'};
  for(const includeLive of [true,false]){
    const runs=[{...fixtureRun,last_modified:'2026-09-19T14:00:00Z'},recent,...(includeLive?[active]:[])];
    const {dom,w,doc,streams}=await mounted({runId:null,fetchOverride:url=>{
      if(url==='/api/runs')return Promise.resolve(Response.json({runs}));
      const chosen=runs.find(run=>url==='/api/runs/'+run.id);
      if(chosen)return Promise.resolve(Response.json({...structuredClone(original),run:chosen}));
    }});
    try{
      assert.equal(new URL(w.location.href).searchParams.get('run'),includeLive?'live-test':'output-test');
      assert.equal(doc.querySelectorAll('[data-run]').length,runs.length);
      doc.querySelector('[data-run="'+fixtureRun.id+'"]').click();
      await until(()=>doc.getElementById('run-title').textContent.includes('Synthetic study')&&doc.getElementById('best-score').textContent==='Not measured'&&streams.at(-1).url.includes(fixtureRun.id),'archive still selectable');
      assert.equal(new URL(w.location.href).searchParams.get('run'),fixtureRun.id);
    }finally{dom.window.close();}
  }
});

test('invalid conclusions and rejected reflections never appear as successful knowledge revisions',async()=>{
  const {dom,doc,streams}=await mounted();
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    // Matches live sciel-research/12 outcomes, including parsed JSON rejected by admission.
    const cases=[
      ['conclusion',{status:'invalid',llm:null,accepted_lesson_ids:[],lesson_error:null}],
      ['reflection',{status:'parsed',applied:null,changed:false,error:'ValueError',error_detail:'retirement requires a replacement preserving scope, polarity and evidence'}],
      ['conclusion',{status:'parsed',llm:{explanation:'Measured outcome recorded'},verdict_matches_observation:true,accepted_lesson_ids:[],lesson_error:null}],
      ['reflection',{status:'parsed',applied:{lesson_ids:['l1'],retired_ids:[]},changed:true,error:null}],
      ['reflection',{status:'parsed',applied:{lesson_ids:[],retired_ids:[]},changed:false,error:null}],
      ['conclusion',{status:'parsed',llm:{explanation:'Invalid lesson evidence'},accepted_lesson_ids:[],lesson_error:'ValueError'}],
      ['reflection',{status:'invalid',applied:null,changed:false,error:null}]
    ];
    snapshot.events=cases.map(([phase,data],index)=>({event:'research',phase,seq:index+1,data}));
    snapshot.stats.reflections=4;
    streams.at(-1).snapshot(snapshot);
    const activity=seq=>doc.querySelector('.activity-item[data-event-seq="'+seq+'"]');
    assert.match(doc.getElementById('hypotheses-count').textContent,/4 reflection attempts/);
    assert.doesNotMatch(doc.getElementById('hypotheses-count').textContent,/revisions/);
    for(const [seq,title] of [[1,'Conclusion invalid'],[2,'Reflection rejected'],[6,'Conclusion rejected'],[7,'Reflection invalid']]){
      assert.equal(activity(seq).querySelector('.activity-title').textContent,title);
      assert.equal(activity(seq).querySelector('.activity-icon.green'),null);
      assert.equal(activity(seq).querySelector('.activity-icon').textContent,'!');
    }
    assert.equal(activity(4).querySelector('.activity-title').textContent,'Knowledge revised');
    assert.equal(activity(5).querySelector('.activity-title').textContent,'Reflection accepted · no change');
    assert.equal(doc.querySelectorAll('.activity-icon.green').length,3);
    assert.match(activity(2).querySelector('.activity-subtitle').textContent,/retirement requires a replacement/);
    doc.getElementById('tab-events').click();
    assert.equal(doc.querySelector('[data-seq="2"] .event-title').textContent,'Reflection rejected');
    assert.equal(doc.querySelector('[data-seq="1"] .event-title').textContent,'Conclusion invalid');
  }finally{dom.window.close();}
});


test('methods snapshots select a dedicated lab view and returning to an engine restores its metrics',async()=>{
  const {dom,doc,streams,errors}=await mounted();
  try{
    const engine=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    streams.at(-1).snapshot({kind:'methods',content_version:'methods-kind-switch',run:{id:fixtureRun.id,name:'Research practices pilot',path:'outputs/methods-pilot',kind:'methods',status:'running'},
      runtime:{active:true,stale_after_seconds:30,heartbeat_age_seconds:0},timing:{session:{elapsed_seconds:8}},methods:{summary:{labs:1,methods:0,experiments:0,proposals:0,invocations:0},labs:[{id:'C-1',mode:'C',active_methods:[],active_adapters:[],steps:0}],tools:[],experiments:[],proposals:[],transfers:[],events:[],budget:{spent:{dollars:0},reserved:{},limits:{}}}});
    assert.equal(doc.getElementById('dashboard').dataset.kind,'methods');
    assert.equal(doc.getElementById('methods-dashboard').hidden,false);
    assert.match(doc.getElementById('methods-dashboard').textContent,/Research labs/);
    assert.match(doc.getElementById('run-title').textContent,/Research practices pilot/);
    assert.match(doc.querySelector('.methods-lab').textContent,/C-1/);
    streams.at(-1).runtime({run:{id:fixtureRun.id,kind:'methods',status:'completed'},runtime:{active:false,elapsed_seconds:12},timing:{live:false,session:{elapsed_seconds:12}}});
    assert.match(doc.getElementById('run-status').textContent,/Completed/);
    assert.equal(doc.querySelector('[data-methods-elapsed]').textContent,'00:00:12');
    streams.at(-1).snapshot(engine);
    assert.equal(doc.getElementById('dashboard').dataset.kind,'engine');
    assert.equal(doc.getElementById('methods-dashboard').hidden,true);
    assert.equal(doc.getElementById('best-score').textContent,'Not measured');
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('native Tool library preserves original metrics and source while exposing recorded events and architecture',async()=>{
  const tool='a'.repeat(64),paths=[];
  const {dom,doc,streams,errors}=await mounted({fetchOverride:url=>{
    if(url.includes('/research-tools/')){paths.push(url);return Promise.resolve({ok:true,json:async()=>({verified:true,files:{'tool.py':'def run(inputs):\n    return {"observed": 0}\n'},manifest:{name:'Recorded helper'},parents:[]})});}
  }});
  try{
    const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    const evaluations=doc.getElementById('evaluations').textContent;
    snapshot.content_version='tool-fixture-1';snapshot.research_tools={available:true,configured:{enabled:true,share_between_islands:true},summary:{versions:1,published:1,actual_invocations:0,foreign_invocations:0,linked_programs:0},versions:[{id:tool,name:'Recorded helper',author_island_id:0,status:'published',invocations:0,foreign_invocations:0,used_by:[]}],events:[]};
    snapshot.events.push({event:'research_tool',phase:'published',seq:999,data:{phase:'published',tool_id:tool}});
    snapshot.architecture.graph.nodes.push({id:'tool_library',label:'Shared tool library',kind:'knowledge',detail:'Published versions are available to islands; availability is not use.'},{id:'tool_execution',label:'Isolated tool calls',kind:'rule',detail:'Prepared Snapshot context does not prove prompt delivery.'});
    snapshot.architecture.graph.edges.push({from:'tool_library',to:'tool_execution',label:'Explicit version invocation'},{from:'tool_execution',to:'generation',label:'Prepared Snapshot context',kind:'knowledge'});
    streams.at(-1).snapshot(snapshot);doc.getElementById('tab-tools').click();
    assert.equal(doc.getElementById('evaluations').textContent,evaluations);assert.equal(doc.getElementById('tools-tab-count').textContent,'1');
    assert.match(doc.getElementById('activity-feed').textContent,/Tool published for sharing/);
    doc.querySelector('.tool-name button').click();await until(()=>doc.querySelector('.tool-raw'));
    const source=doc.querySelector('.tool-raw');source.scrollTop=21;source.focus();
    snapshot.content_version='tool-fixture-2';snapshot.research_tools.versions[0].invocations=1;streams.at(-1).snapshot(snapshot);
    assert.strictEqual(doc.querySelector('.tool-raw'),source);assert.strictEqual(doc.activeElement,source);assert.equal(paths.length,1);
    doc.getElementById('tab-architecture').click();doc.querySelector('[data-node="tool_execution"]').click();assert.match(doc.querySelector('.graph-inspector').textContent,/does not prove prompt delivery/);
    doc.getElementById('tab-tools').click();assert.strictEqual(doc.querySelector('.tool-raw'),source);assert.equal(source.scrollTop,21);
    assert.equal(errors.length,0);
  }finally{dom.window.close();}
});

test('Research cells deep link distinguishes disabled configuration and retains ordinary search metrics',async()=>{
  const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
  snapshot.research_tools={configuration:{status:'disabled',enabled:false},configured:{enabled:false},summary:{cells:0,versions:0},cells:[]};
  const {dom,w,doc,errors}=await mounted({tab:'research-cells',fetchOverride:url=>{
    if(url==='/api/runs/'+fixtureRun.id)return Promise.resolve(Response.json(snapshot));
  }});
  try{
    assert.equal(doc.getElementById('tab-research-cells').getAttribute('aria-selected'),'true');
    assert.equal(doc.getElementById('tab-research-cells').previousElementSibling.id,'tab-packings');
    assert.match(doc.querySelector('.research-cells').textContent,/disabled for this run/);
    assert.match(doc.querySelector('.research-cells').textContent,/VQ/);
    assert.equal(doc.getElementById('cells-tab-count').textContent,'0');
    assert.equal(doc.getElementById('evaluations').textContent,'4');
    assert.ok(doc.getElementById('score-chart'));
    doc.getElementById('tab-events').click();
    assert.equal(new URL(w.location.href).searchParams.get('tab'),'events');
    assert.equal(new URL(w.location.href).searchParams.get('run'),fixtureRun.id);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('Research cells receives background-only updates and retains its workspace across tab switches',async()=>{
  const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
  const cell='c'.repeat(64),calls=[];
  const detail={kind:'cell',id:cell,verified:true,genesis:{question:'Which method should be tested next?'},revision_history:[],related:{jobs:[]},related_coverage:{}};
  snapshot.research_tools={configuration:{status:'enabled',enabled:true},summary:{cells:1,versions:0},cells:[{id:cell,question:detail.genesis.question,stage:'research',scheduled:true,detail_version:'same-checkpoint',affinities:[0]}],jobs:{version:'initial',items:[]}};
  const {dom,doc,streams,errors}=await mounted({tab:'research-cells',fetchOverride:url=>{
    if(url==='/api/runs/'+fixtureRun.id)return Promise.resolve(Response.json(snapshot));
    if(url.includes('/research-cells/')){calls.push(url);return Promise.resolve(Response.json(detail));}
  }});
  try{
    await until(()=>doc.querySelector('.rc-detail')?.textContent.includes('No background job'),'cell details loaded');
    assert.equal(doc.getElementById('cells-tab-count').textContent,'1');
    const workspace=doc.querySelector('.research-cells'),pane=doc.querySelector('.rc-detail');
    const job={id:'j'.repeat(64),cell_id:cell,status:'queued',requested:{cpu_seconds:60,wall_seconds:90}};
    detail.related.jobs=[job];
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:'running'},research_tool_jobs:{version:'new-job',items:[job]}});
    await until(()=>doc.querySelector('[data-section="jobs"]')?.textContent.includes('Queued'),'runtime-only jobs delivered to research cells');
    assert.ok(calls.length>=2,'mutable job status refreshes details without a checkpoint change');
    assert.equal(doc.querySelector('.rc-detail'),pane);
    doc.getElementById('tab-events').click();doc.getElementById('tab-research-cells').click();
    assert.equal(doc.querySelector('.research-cells'),workspace);
    assert.equal(doc.querySelector('.rc-detail'),pane);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('Packings deep link loads only active geometry, survives polling, and opens the saved program',async()=>{
  const snapshot=await (await fetch(base+'/api/runs/'+fixtureRun.id)).json();
  snapshot.content_version='packings-v1';
  const program=snapshot.trials.find(row=>row.code_available),programId=String(program.candidate_id||program.id),requests=[];
  const layout={id:'saved-invocation',program_id:programId,evaluation_id:'evaluation-fixture',island_id:0,iteration:1,timestamp:'2026-09-20T09:00:00Z',valid:true,score:.2,source_sha256:'a'.repeat(64),centers:[[.2,.3],[.7,.8]],radii:[.1,.1]};
  const {dom,w,doc,streams,errors}=await mounted({tab:'packings',fetchOverride:url=>{
    if(url==='/api/runs/'+fixtureRun.id)return Promise.resolve(Response.json(snapshot));
    if(url.includes('/packings?')){requests.push(url);return Promise.resolve(Response.json({schema:'sciel-packings/1',supported:true,total:1,available:1,unavailable:0,offset:0,limit:120,has_more:false,content_version:snapshot.content_version,islands:[0],items:[layout]}));}
  }});
  try{
    await until(()=>doc.querySelector('.pg-tile'),'deep-linked gallery loaded');
    assert.equal(doc.getElementById('tab-packings').getAttribute('aria-selected'),'true');assert.equal(new URL(w.location.href).searchParams.get('tab'),'packings');assert.equal(requests.length,1);
    const tile=doc.querySelector('.pg-tile'),search=doc.querySelector('.pg-search');
    streams.at(-1).runtime({run:{id:fixtureRun.id,status:'running'},runtime:{active:true,stage:'generating'}});await new Promise(r=>setTimeout(r,30));assert.equal(requests.length,1,'runtime updates do not fetch geometry');
    snapshot.content_version='packings-v2';streams.at(-1).snapshot(snapshot);await until(()=>requests.length===2);assert.strictEqual(doc.querySelector('.pg-tile'),tile);assert.strictEqual(doc.querySelector('.pg-search'),search);
    doc.getElementById('tab-events').click();snapshot.content_version='packings-v3';streams.at(-1).snapshot(snapshot);await new Promise(r=>setTimeout(r,30));assert.equal(requests.length,2,'inactive tab never fetches geometry');
    doc.getElementById('tab-packings').click();await until(()=>requests.length===3);doc.querySelector('.pg-tile').click();assert.equal(doc.querySelector('.pg-dialog').open,true);doc.querySelector('.pg-code').click();await until(()=>doc.getElementById('code-select')?.value===programId&&doc.querySelector('#code-body .code-meta'));assert.equal(doc.getElementById('tab-code').getAttribute('aria-selected'),'true');assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

test('overview Population stays beside search markup and opens existing full population and source views',async()=>{
  const {dom,doc,streams,errors}=await mounted();
  try{
    const snapshot=await(await fetch(base+'/api/runs/'+fixtureRun.id)).json();
    snapshot.content_version='population-preview-fixture';
    snapshot.population={available:true,source:'checkpoint',iteration:5,island_count:1,layout:{kind:'map_elites',grid_bins:10},descriptor:{kind:'code_length'},
      islands:[{id:0,member_count:1,members_available:true,grid_available:true,grid_cell_count:1,members:[{id:'p3',score:.9,code_available:true}],grid:[{x:2,y:3,candidate_id:'p3',score:.9,metric_display:measured(2.7,.9,'Sum of radii')}]}],
      archive:{count:0,members:[]},storage:{schema:'sciel-population-storage/1',kind:'map_elites',label:'MAP-Elites',iteration:5,bins:{x:10,y:10},projection:{available:false}}};
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelector('.chart-panel').nextElementSibling.className,'panel population-preview-panel');
    assert.equal(doc.querySelector('.overview-grid').nextElementSibling.classList.contains('overview-activity'),true);
    const preview=doc.querySelector('#population-preview .population-preview'),mark=preview.querySelector('.preview-mark');
    assert.ok(mark);assert.equal(mark.dataset.change,'');
    mark.dispatchEvent(new dom.window.Event('pointerenter',{bubbles:true}));
    assert.match(preview.querySelector('.preview-inspector').textContent,/2.700000/);
    preview.querySelector('.preview-full').click();
    assert.equal(doc.getElementById('tab-population').getAttribute('aria-selected'),'true');
    assert.ok(doc.getElementById('population-map'),'complete population workspace remains available');
    assert.equal(doc.querySelector('#population-preview .population-preview'),preview);
    preview.querySelector('.preview-program').click();await until(()=>doc.querySelector('.code-view'),'saved program source opens');
    assert.equal(doc.getElementById('tab-code').getAttribute('aria-selected'),'true');
    assert.equal(doc.querySelector('#population-preview .preview-mark'),mark);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});
