import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const assets=new URL('../../web/',import.meta.url);
const read=name=>readFileSync(new URL(name,assets),'utf8');
const app=read('app.js').replace(/^import .*$/mg,'').split("$('run-list').addEventListener")[0];
const schema='sciel-metric-display/1',hash='a'.repeat(64);
const view=(status,value=null,raw=0,label='Sum of radii',metric=hash)=>({schema,status,value,label,units:'unit_square_side_length',raw_score:raw,reason:status==='invalid_penalty'?'Validity check failed; score is a penalty.':null,metric_sha256:metric});
const seed=view('measured',.9597642169962064,.36423689449571406);
function trial(id,display,extra={}) {
  return {id:'r'+id,candidate_id:id,parent_id:'seed',parent_ids:['seed'],iteration:1,island:0,status:'evaluated',score:display.raw_score,best_score:seed.raw_score,parent_score:seed.raw_score,actual_delta:display.raw_score-seed.raw_score,metric_display:display,parent_metric_display:seed,best_metric_display:seed,code_available:true,operator:'diff',hypothesis:{text:'Change one constant.',predicted_low:.1,predicted_high:.3,confidence:.5},...extra};
}
function snapshot(rows) {
  return {run:{id:'fixture',run_id:'saved-run',task:'test/task'},content_version:'v1',metric_display:view('unknown'),benchmark:{metric:'Sum of radii',task_target:2.635},stats:{best_score:seed.raw_score,seed_score:seed.raw_score,best_metric_display:seed,seed_metric_display:seed,iterations:rows.length,evaluations:rows.length},curves:[trial('seed',seed,{iteration:0,parent_ids:[],parent_id:null,parent_score:null,parent_metric_display:view('unknown'),kind:'seed'}),...rows],programs:rows,trials:rows,hypotheses:rows,events:[],runtime:{active:false}};
}
function setup(data) {
  const dom=new JSDOM(read('experiment.html'),{runScripts:'outside-only',pretendToBeVisual:true,url:'http://fixture.invalid/'}),w=dom.window;
  w.matchMedia=()=>({matches:true});w.ResizeObserver=class{observe(){}disconnect(){}};w.HTMLElement.prototype.scrollIntoView=function(){};
  const requests=[];w.fetch=async url=>{requests.push(String(url));return {ok:true,json:async()=>({code:'def run(): return 1',diff:'+ def run(): return 1',parent_code:'def run(): return 0',code_source:'checkpoint'})};};
  w.renderLLMCalls=(mount,options)=>{w.lastLLM=options.query;mount.textContent='Saved calls for '+options.query;};
  w.eval('{'+read('chart.js').replace('export function renderChart','function renderChart')+';window.renderChart=renderChart;}');
  w.eval('{'+read('population.js').replace(/export function /g,'function ')+';Object.assign(window,{renderPopulationMap,destroyPopulationMap});}');
  w.eval('{'+read('storage-view.js').replace('export function renderStorageSpace','function renderStorageSpace')+';window.renderStorageSpace=renderStorageSpace;}');
  w.eval('{'+readFileSync(new URL('effort.js',assets),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderEffort,effortDetailsHTML,publishedEffortHTML});}');
  w.eval('{'+readFileSync(new URL('population-preview.js',assets),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderPopulationPreview,destroyPopulationPreview});}');
  w.eval('{'+app+';window.metricFixture={set(data){state.snapshot=data;state.runId="fixture";state.contentVersion=data.content_version;state.selected=null;plotProjection=null;},state,renderPlot,renderTrials,renderHypotheses,renderPopulation,metricDisplay,metricText,metricDifference,metricLabel};}');
  w.metricFixture.set(data);
  return {dom,w,doc:w.document,api:w.metricFixture,requests};
}

test('actual chart keeps valid zero but excludes penalty/failure/unknown values; related cards have no fabricated delta',()=>{
  const rows=[trial('invalid',view('invalid_penalty')),trial('zero',view('measured',0)),trial('failed',view('failed',null,0),{status:'eval_fail'}),trial('unknown',view('unknown',null,.8)),trial('child',view('measured',2.614123456789,.99),{parent_id:'invalid',parent_ids:['invalid'],parent_score:0,parent_metric_display:view('invalid_penalty')})];
  const original=JSON.stringify(rows),{dom,w,doc,api}=setup(snapshot(rows));
  try{
    api.renderPlot();
    assert.equal(doc.querySelectorAll('.chart-dot').length,3);
    assert.ok(doc.querySelector('.chart-dot[data-point-key="zero"]'));
    for(const id of ['invalid','failed','unknown'])assert.equal(doc.querySelector('.chart-dot[data-point-key="'+id+'"]'),null);
    assert.match(doc.querySelector('#chart-outcomes summary').textContent,/1 invalid · 1 failed · 1 unavailable/);
    doc.querySelector('.chart-dot[data-point-key="zero"]').dispatchEvent(new w.Event('pointerenter'));
    assert.equal(doc.querySelector('.chart-card-score strong').textContent,'0');
    assert.match(doc.querySelector('.chart-card-score small').textContent,/-0\.959764217 vs parent/);
    doc.querySelector('.chart-dot[data-point-key="child"]').dispatchEvent(new w.Event('pointerenter'));
    assert.equal(doc.querySelector('.chart-card-score strong').textContent,'2.614123457');
    assert.equal(doc.querySelector('.chart-card-score small'),null,'invalid parent has no physical delta');
    doc.querySelector('.chart-family-chip[data-program="invalid"]').click();
    assert.match(doc.querySelector('.chart-card-score strong').textContent,/Invalid result.*penalty score 0/);
    assert.equal(doc.querySelector('.chart-card-score small'),null);
    assert.match(doc.querySelector('.chart-card-tags').textContent,/Invalid result · penalty/);
    assert.equal(JSON.stringify(rows),original,'rendering must not rewrite saved raw scores');
  }finally{dom.window.close();}
});

test('Programs and Hypotheses distinguish invalid penalties, raw forecast units and measured deltas',()=>{
  const rows=[trial('invalid',view('invalid_penalty')),trial('zero',view('measured',0))];
  const {dom,doc,api}=setup(snapshot(rows));
  try{
    api.renderTrials();
    const invalid=doc.querySelector('tr[data-candidate="invalid"]'),zero=doc.querySelector('tr[data-candidate="zero"]');
    assert.match(invalid.cells[3].textContent,/Invalid resultPenalty score 0/);
    assert.equal(invalid.cells[4].textContent,'—');assert.match(invalid.cells[5].textContent,/Invalid result · penalty/);
    assert.equal(zero.cells[3].textContent,'0.000000');assert.match(zero.cells[4].textContent,/-0\.959764/);
    api.renderHypotheses();
    const cards=[...doc.querySelectorAll('.research-card')],bad=cards.find(x=>x.textContent.includes('rinvalid'));
    assert.match(bad.textContent,/Predicted Δ · score units\[\+0.100000; \+0.300000\]/);
    assert.match(bad.textContent,/Measured Δ—/);assert.match(bad.textContent,/Invalid resultPenalty score/);
  }finally{dom.window.close();}
});

test('excluded outcomes keep real source and LLM navigation, totals, truncation and disclosure on refresh',async()=>{
  const rows=Array.from({length:65},(_,i)=>trial('bad'+i,view('invalid_penalty'))),{dom,doc,api,w,requests}=setup(snapshot(rows));
  try{
    api.renderPlot();const details=doc.querySelector('#chart-outcomes details');details.open=true;
    assert.match(details.querySelector('summary').textContent,/65 invalid/);
    assert.equal(doc.querySelectorAll('[data-outcome-id]').length,60);
    assert.match(details.textContent,/Latest 60 of 65 outcomes shown/);
    api.renderPlot();assert.equal(doc.querySelector('#chart-outcomes details').open,true);
    doc.querySelector('[data-outcome-id="bad64"] [data-candidate]').click();
    assert.equal(api.state.tab,'code');assert.equal(api.state.selected,'bad64');
    await new Promise(resolve=>w.setTimeout(resolve,0));
    assert.deepEqual(requests,['/api/runs/fixture/program/bad64']);
    doc.querySelector('[data-outcome-id="bad64"] [data-llm-experiment]').click();
    assert.equal(w.lastLLM,'rbad64');assert.equal(api.state.tab,'llm');
  }finally{dom.window.close();}
});

function populationData(rows){
  const members=rows.map(r=>({id:r.candidate_id,score:r.score,metric_display:r.metric_display,code_available:true,origin:'portfolio',grid_elite:true}));
  return {available:true,iteration:1,layout:{kind:'map_elites',grid_bins:4},descriptor:{},archive:{count:members.length,members},islands:[{id:0,member_count:members.length,members,members_available:true,grid_available:true,grid_cell_count:members.length,best_score:0,best_metric_display:view('measured',0),grid:members.map((m,i)=>({x:i,y:0,candidate_id:m.id,score:m.score,metric_display:m.metric_display,code_available:true}))}],storage:{schema:'sciel-population-storage/1',kind:'map_elites',label:'MAP-Elites',bins:{x:4,y:4},assignments:[]}};
}

test('population membership, storage cells, archive and color legend preserve the zero versus penalty distinction',()=>{
  const rows=[trial('invalid',view('invalid_penalty')),trial('zero',view('measured',0))],data=snapshot(rows);data.population=populationData(rows);
  const {dom,doc,api,w}=setup(data);
  try{
    api.renderPopulation();
    assert.match(doc.querySelector('.population-members tbody tr:nth-child(1)').textContent,/invalid.*Invalid resultPenalty score/);
    assert.match(doc.querySelector('.archive-members').textContent,/invalid.*Invalid resultPenalty score/);
    doc.querySelector('[data-population-view="islands"]').click();
    const bad=doc.querySelector('.territory-cell[data-program="invalid"]'),zero=doc.querySelector('.territory-cell[data-program="zero"]');
    assert.match(bad.getAttribute('aria-label'),/Invalid result \(penalty score 0/);
    assert.match(zero.getAttribute('aria-label'),/Sum of radii 0.000000/);
    bad.dispatchEvent(new w.Event('pointerenter'));assert.match(doc.querySelector('.territory-card-score').textContent,/Invalid result/);
    doc.querySelector('[data-color-mode="score"]').click();
    assert.equal(bad.style.getPropertyValue('--island-color'),'#cdd1d9');
    assert.notEqual(zero.style.getPropertyValue('--island-color'),'#cdd1d9');
    doc.querySelector('[data-population-view="storage"]').click();
    doc.querySelector('.storage-mark[data-storage-key="cell:0:0:0"]').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
    assert.match(doc.querySelector('.storage-copy').textContent,/Invalid result/);
    assert.match(doc.querySelector('.storage-bound-programs').textContent,/Invalid result/);
  }finally{dom.window.close();}
});

test('legacy unknowns and conflicting bindings stay unmeasured, while arbitrary task-native values are used exactly',()=>{
  const rows=[trial('latency',view('measured',1500,.25,'Latency (ms)','b'.repeat(64)),{parent_metric_display:view('measured',1800,.2,'Latency (ms)','b'.repeat(64)),parent_score:.2}),trial('legacy',view('unknown',null,.9))];
  delete rows[1].metric_display;
  const data=snapshot(rows);data.metric_display=view('unknown',null,null,'Latency (ms)','b'.repeat(64));data.benchmark={metric:'Latency (ms)',task_target:9999};
  const {dom,doc,w,api}=setup(data);
  try{
    api.renderPlot();doc.querySelector('.chart-dot[data-point-key="latency"]').dispatchEvent(new w.Event('pointerenter'));
    assert.equal(doc.querySelector('.chart-card-score strong').textContent,'1500');
    assert.match(doc.querySelector('.chart-card-score small').textContent,/-300 vs parent/);
    assert.equal(doc.querySelector('.chart-dot[data-point-key="legacy"]'),null);
    assert.match(doc.querySelector('[data-outcome-id="legacy"]').textContent,/Not measuredRaw score 0.900000/);
    assert.equal(api.metricDisplay({score:.3,metric_display:view('measured',1500,.25)}).status,'unknown');
    assert.equal(api.metricDifference(view('measured',0,0),view('invalid_penalty')),null);
  }finally{dom.window.close();}
});


test('generic metric identifiers become readable captions without changing acronym tokens or measurement identity',()=>{
  const data=snapshot([]);data.metric_display.label='GPU_latency_ms';delete data.benchmark;
  const {dom,api}=setup(data);
  try{
    assert.equal(api.metricLabel(),'GPU latency ms');
    assert.equal(data.metric_display.label,'GPU_latency_ms');
    data.metric_display.label='sum_radii';data.benchmark={metric:'Sum of radii'};
    assert.equal(api.metricLabel(),'Sum of radii');
  }finally{dom.window.close();}
});

test('saved storage observations do not borrow current membership measurements, even when scores tie',()=>{
  const rows=[trial('zero',view('measured',0))],data=snapshot(rows);data.population=populationData(rows);
  delete data.population.islands[0].grid[0].metric_display;
  const {dom,doc,api,w}=setup(data);
  try{
    api.renderPopulation();doc.querySelector('[data-population-view="storage"]').click();
    doc.querySelector('.storage-mark[data-storage-key="cell:0:0:0"]').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
    assert.match(doc.querySelector('.storage-copy').textContent,/Not measured \(raw score 0/);
    assert.match(doc.querySelector('.storage-bound-programs').textContent,/Not measured \(raw score 0/);
    assert.equal(data.population.islands[0].members[0].metric_display.status,'measured');
  }finally{dom.window.close();}
});
