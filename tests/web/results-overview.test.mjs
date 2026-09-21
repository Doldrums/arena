import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
const html=readFileSync(new URL('../../web/results.html',import.meta.url),'utf8').replace('data-results-showcase="true"','data-results-showcase="test"');
const source=readFileSync(new URL('../../web/arena-results-overview.js',import.meta.url),'utf8').replace(/^export /gm,'');
const sample=JSON.parse(readFileSync(new URL('../../registry/results-overview.json',import.meta.url),'utf8'));
const copy=v=>JSON.parse(JSON.stringify(v));
const flush=async()=>{for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r));};
function mount({key='',confirmed=false,fetcher,timeout=5000}={}){
 const dom=new JSDOM(html,{url:'http://arena.test/results',runScripts:'outside-only',pretendToBeVisual:true}),w=dom.window,doc=w.document,calls=[];
 if(confirmed)doc.body.dataset.resultsAccess='connected';
 const storage={getItem:()=>key};w.eval(`${source};window.mount=initResultsOverview;`);
 const app=w.mount({doc,storage,pollMs:0,requestTimeoutMs:timeout,fetcher:async(path,options)=>{calls.push({path,options});return fetcher?fetcher(path,options,calls.length):{ok:true,json:async()=>copy(sample)};}});
 return {doc,w,app,calls,root:doc.getElementById('results-overview'),close(){app.destroy();w.close();}};
}
test('a fresh landing tab gets measured overview without run key, private API, or writes',async()=>{
 const t=mount();try{await flush();assert.equal(t.root.hidden,false);assert.equal(t.root.dataset.state,'ready');assert.equal(t.root.getAttribute('aria-busy'),'false');assert.equal(t.calls.length,1);assert.equal(t.calls[0].path,'/api/results-overview');assert.equal(t.calls[0].options.headers,undefined);assert.ok(!t.calls[0].options.method);assert.equal(t.root.querySelectorAll('.overview-stat').length,4);assert.equal(t.root.querySelector('.overview-stat strong').textContent,String(sample.summary.runs));assert.match(t.root.textContent,/Published snapshot/);assert.ok(t.root.querySelectorAll('.overview-point').length);assert.ok(t.root.querySelector('.overview-table'));assert.ok(t.doc.querySelector('.showcase-next a[href="/experiments/results"]'));}finally{t.close();}
});
test('initial loading is decorative then measured; it never flashes invented values',async()=>{
 let done;const t=mount({fetcher:()=>new Promise(r=>{done=r;})});try{await flush();assert.equal(t.root.dataset.state,'loading');assert.equal(t.root.getAttribute('aria-busy'),'true');assert.equal(t.root.querySelectorAll('.overview-stat strong').length,0);assert.equal(t.root.querySelectorAll('.overview-stats[aria-hidden=true]').length,1);done({ok:true,json:async()=>copy(sample)});await flush();assert.equal(t.root.dataset.state,'ready');assert.equal(t.root.querySelectorAll('.overview-stat strong').length,4);}finally{t.close();}
});
test('score plot selects one full cohort contract and does not blend other tasks',async()=>{
 const payload=copy(sample),group=payload.cohorts.find(c=>c.points.some(p=>p.usage_complete));payload.cohorts=[group,{...copy(group),task_id:'different-task',task_name:'Different task',points:[{...group.points[0],best_score:987}]}];
 const t=mount({fetcher:async()=>({ok:true,json:async()=>payload})});try{await flush();let select=t.root.querySelector('.overview-cohort select');assert.equal(new Set([...select.options].map(o=>o.value)).size,2);assert.equal(t.root.querySelectorAll('.overview-point').length,group.points.filter(p=>p.usage_complete&&p.total_tokens!==null&&p.best_score!==null).length);select.value=select.options[1].value;select.dispatchEvent(new t.w.Event('change'));assert.equal(t.root.querySelectorAll('.overview-point').length,payload.cohorts[1].points[0].total_tokens===null?0:1);assert.match(t.root.textContent,/Different task/);}finally{t.close();}
});
test('resource chart excludes incomplete token counts but retains failed verified scores for time',async()=>{
 const p=copy(sample);p.cohorts=[{...p.cohorts[0],points:[{system:'sciel-release',model:'m',state:'failed',seed_score:-1,best_score:0,wall_seconds:120,total_tokens:700,usage_complete:false,evidence_partial:true}]}];
 const t=mount({fetcher:async()=>({ok:true,json:async()=>p})});try{await flush();assert.equal(t.root.querySelector('[data-overview-focus=resource]').value,'time','when tokens are absent, the initial chart uses recorded wall time');const select=t.root.querySelector('[data-overview-focus=resource]');select.value='tokens';select.dispatchEvent(new t.w.Event('change'));assert.equal(t.root.querySelectorAll('.overview-point').length,0);const timeSelect=t.root.querySelector('[data-overview-focus=resource]');timeSelect.value='time';timeSelect.dispatchEvent(new t.w.Event('change'));const point=t.root.querySelector('.overview-point');assert.ok(point);assert.match(point.getAttribute('aria-label'),/-1 → 0/);assert.match(point.getAttribute('aria-label'),/failed.*partial/);point.dispatchEvent(new t.w.Event('focus'));assert.match(t.root.querySelector('.overview-chart-detail').textContent,/failed/);}finally{t.close();}
});
test('all system and failure counts remain present when the short table is expanded',async()=>{
 const t=mount();try{await flush();assert.equal(t.root.querySelectorAll('.overview-systems-table tbody tr').length,Math.min(6,sample.systems.length));const toggle=t.root.querySelector('.overview-systems-table .overview-table-footer button');assert.equal(toggle.getAttribute('aria-expanded'),'false');toggle.click();assert.equal(t.root.querySelectorAll('.overview-systems-table tbody tr').length,sample.systems.length);assert.equal(t.root.querySelector('.overview-systems-table .overview-table-footer button').getAttribute('aria-expanded'),'true');const errors=[...t.root.querySelectorAll('.overview-status-list>div')].find(r=>r.textContent.includes('Stopped with an error'));assert.equal(errors.querySelector('dd').textContent,String(sample.summary.failed));assert.ok(!t.root.textContent.includes('rank #'));}finally{t.close();}
});
test('refresh failure retains real values and retry recovers without asking for a key',async()=>{
 const t=mount({fetcher:async(_p,_o,n)=>{if(n===2)throw new Error('offline');return {ok:true,json:async()=>copy(sample)};}});try{await flush();const before=t.root.querySelector('.overview-stat strong').textContent;await t.app.refresh();assert.equal(t.root.dataset.state,'error');assert.equal(t.root.querySelector('.overview-stat strong').textContent,before);assert.match(t.root.querySelector('.overview-status').textContent,/last published snapshot/);t.root.querySelector('.overview-context button').click();await flush();assert.equal(t.root.dataset.state,'ready');assert.equal(t.root.querySelector('.overview-context button').textContent,'Refresh');}finally{t.close();}
});
test('initial fetch error and timeout offer a working retry with no dummy metrics',async()=>{
 for(const kind of ['error','timeout']){const t=mount({timeout:5,fetcher:async(_p,_o,n)=>{if(n>1)return {ok:true,json:async()=>copy(sample)};if(kind==='timeout')return new Promise(()=>{});throw new Error('offline');}});try{await new Promise(r=>setTimeout(r,15));await flush();assert.equal(t.root.dataset.state,'error');assert.equal(t.root.querySelectorAll('.overview-stat strong').length,0);t.root.querySelector('.overview-context button').click();await flush();assert.equal(t.root.dataset.state,'ready');}finally{t.close();}}
});
test('connected private view makes no public request; disconnect reveals overview, late reads cannot reveal it under private view',async()=>{
 let done;const t=mount({key:'private',confirmed:true,fetcher:()=>new Promise(r=>{done=r;})});try{await flush();assert.equal(t.calls.length,0);assert.equal(t.root.hidden,true);t.doc.dispatchEvent(new t.w.CustomEvent('arena:results-access',{detail:{connected:false}}));await flush();assert.equal(t.calls.length,1);t.doc.dispatchEvent(new t.w.CustomEvent('arena:results-access',{detail:{connected:true}}));done({ok:true,json:async()=>copy(sample)});await flush();assert.equal(t.root.hidden,true);assert.equal(t.root.querySelectorAll('.overview-stat strong').length,0);}finally{t.close();}
});
test('source strings render as text rather than HTML and overview links do not contain private run identifiers',async()=>{
 const p=copy(sample);p.systems[0].system='<img src=x onerror=alert(1)>';
 const t=mount({fetcher:async()=>({ok:true,json:async()=>p})});try{await flush();t.root.querySelector('.overview-systems-table .overview-table-footer button').click();assert.equal(t.root.querySelectorAll('img,script').length,0);assert.equal(t.root.querySelectorAll('a[href*="run="],a[href*="/api/"]').length,0);}finally{t.close();}
});

test('chart controls and table expansion retain keyboard focus across render and polling',async()=>{
 const t=mount();try{await flush();let select=t.root.querySelector('[data-overview-focus=resource]');select.focus();select.value='time';select.dispatchEvent(new t.w.Event('change'));assert.equal(t.doc.activeElement.dataset.overviewFocus,'resource');await t.app.refresh();assert.equal(t.doc.activeElement.dataset.overviewFocus,'resource');let toggle=t.root.querySelector('[data-overview-focus=expand]');toggle.focus();toggle.click();assert.equal(t.doc.activeElement.dataset.overviewFocus,'expand');assert.equal(t.doc.activeElement.getAttribute('aria-expanded'),'true');assert.match(t.root.querySelector('.overview-stats').textContent,/including seeds/);}finally{t.close();}
});

test('a saved key alone never hides the published results',async()=>{
 const t=mount({key:'saved-on-another-server'});try{await flush();assert.equal(t.root.hidden,false);assert.equal(t.root.dataset.state,'ready');assert.equal(t.calls[0].path,'/api/results-overview');assert.equal(t.calls[0].options.headers,undefined);}finally{t.close();}
});
test('actual canonical and native task scores are visible in table cells without opening chart tooltips',async()=>{
 const p=copy(sample);p.native_results=[{system:'base',model:'model-a',state:'completed',task_id:'circle-packing',task_name:'Circle packing',metric:'target_ratio',direction:'maximize',seed_score:.4,best_score:.987654321,wall_seconds:100,total_tokens:null,usage_complete:false,evidence_partial:false,objectives:[],population_objectives:[]}];
 const t=mount({fetcher:async()=>({ok:true,json:async()=>p})});try{await flush();const table=t.root.querySelector('.overview-score-table');assert.match(table.textContent,/0.987654321/);assert.match(table.textContent,/0.4/);assert.match(table.textContent,/Framework-native evaluation/);assert.match(table.textContent,/model-a/);assert.ok(t.root.querySelector('.overview-result-gain'));const task=t.root.querySelector('[data-overview-focus=result-task]');task.value='reference-sat';task.dispatchEvent(new t.w.Event('change'));assert.match(t.root.querySelector('.overview-score-table').textContent,/SCiEL/);assert.match(t.root.querySelector('.overview-score-table').textContent,/Shared evaluator/);}finally{t.close();}
});
test('multiobjective outcomes preserve pairs, minimizing changes and missing baselines are not invented',async()=>{
 const p=copy(sample);p.cohorts=[];p.native_results=[{system:'meoh',model:'m',state:'completed',task_id:'packing',task_name:'Packing',metric:'native_two_objective_population',direction:null,seed_score:null,best_score:null,wall_seconds:200,total_tokens:null,usage_complete:false,evidence_partial:false,objectives:[{metric:'bins',direction:'minimize'},{metric:'time',direction:'minimize'}],population_objectives:[{bins:5,time:9},{bins:6,time:8}]}];
 const t=mount({fetcher:async()=>({ok:true,json:async()=>p})});try{await flush();const row=t.root.querySelector('.overview-result-row');assert.match(row.textContent,/2 objective pairs/);assert.match(row.textContent,/bins: 5 · time: 9/);assert.match(row.textContent,/bins: 6 · time: 8/);assert.match(row.textContent,/Not paired/);assert.equal(row.querySelectorAll('.overview-result-gain').length,0);}finally{t.close();}
});
test('research best-per-model keeps initial score and time from the selected run, with every run inspectable',async()=>{
 const p=copy(sample);const seed={task_id:'oe/circle_packing',task_name:'Circle packing',metric:'sum_radii',direction:'maximize',units:'unit_square_side_length',protocol:'a'.repeat(64),models:['model-a'],state:'paused',seed_score:1.3,best_score:2.6,total_wall_seconds:5000,to_best_wall_seconds:900,wall_scope:'elapsed_including_pauses',tokens:null,source:'native_observer',measurement_status:'measured'};
 p.research={source_generated_at:p.generated_at,total:3,measured:3,runs:[seed,{...seed,best_score:2.635983084917587,to_best_wall_seconds:2400,seed_score:2.5},{...seed,protocol:'b'.repeat(64),best_score:99}]};
 const t=mount({fetcher:async()=>({ok:true,json:async()=>p})});try{await flush();const section=t.root.querySelector('.overview-research-results');assert.equal(section.querySelectorAll('.overview-research-row').length,1);assert.match(section.textContent,/2.635983085/);assert.match(section.textContent,/2.5/);assert.match(section.textContent,/40 min/);assert.match(section.textContent,/Selected from 2 recorded runs/);assert.match(section.textContent,/paused/);assert.doesNotMatch(section.querySelector('.overview-research-highlight').textContent,/99/);const mode=section.querySelector('[data-overview-focus=research-mode]');mode.value='all';mode.dispatchEvent(new t.w.Event('change'));assert.equal(t.root.querySelectorAll('.overview-research-row').length,2);}finally{t.close();}
});
test('catalog private-API 404 retains the independently loaded published overview with a saved key',async()=>{
 const t=mount({key:'saved'});const legacy=readFileSync(new URL('../../web/arena-results-showcase.js',import.meta.url),'utf8').replace(/^export /gm,'');t.w.eval(`(()=>{${legacy};window.mountLegacy=initResultsShowcase;})();`);
 const app=t.w.mountLegacy({doc:t.doc,storage:{getItem:()=> 'saved',removeItem(){}},pollMs:0,fetcher:async()=>({ok:false,status:404,json:async()=>({})})});
 try{await flush();assert.equal(t.doc.body.dataset.resultsAccess,'overview');assert.equal(t.root.hidden,false);assert.equal(t.root.dataset.state,'ready');assert.ok(t.root.querySelector('.overview-score-table'));}finally{app.destroy();t.close();}
});

test('research results remain ready and inspectable when no integration runs are published',async()=>{
 const p=copy(sample);p.total=p.loaded=0;p.truncated=false;p.summary={runs:0,completed:0,active:0,failed:0,cancelled:0,other:0,systems:0,models:0};p.systems=[];p.cohorts=[];p.native_results=[];p.validity={evaluations:0,valid:0,invalid:0,unknown:0,unique_programs:null,hash_coverage_runs:0};p.resources={complete_token_runs:0,median_tokens:null,wall_time_runs:0};
 const observed={task_id:'oe/circle_packing',task_name:'Circle packing',metric:'sum_radii',direction:'maximize',units:'unit_square_side_length',protocol:'a'.repeat(64),models:['model-a'],state:'paused',seed_score:0,best_score:2.5,total_wall_seconds:600,to_best_wall_seconds:300,wall_scope:'elapsed_including_pauses',tokens:null,source:'native_observer',measurement_status:'measured'};
 p.research={source_generated_at:p.generated_at,total:1,measured:1,runs:[observed]};
 const t=mount({fetcher:async()=>({ok:true,json:async()=>copy(p)})});try{
  await flush();assert.equal(t.root.dataset.state,'ready');assert.equal(t.root.getAttribute('aria-busy'),'false');assert.equal(t.root.hidden,false);
  const section=t.root.querySelector('.overview-research-results');assert.ok(section);assert.equal(section.querySelectorAll('.overview-research-row').length,1);assert.match(section.textContent,/2.5/);assert.match(section.textContent,/5 min/);assert.doesNotMatch(t.root.textContent,/No published results yet/);
  assert.equal(t.root.querySelectorAll('.overview-stat,.overview-task-results,.overview-systems-table').length,0,'empty integration panels must not obscure actual research');
  const select=section.querySelector('[data-overview-focus=research-mode]');select.value='all';select.dispatchEvent(new t.w.Event('change'));assert.equal(t.root.querySelectorAll('.overview-research-row').length,1);
  await t.app.refresh();assert.equal(t.root.dataset.state,'ready');assert.ok(t.root.querySelector('.overview-research-results'));
  p.research=null;await t.app.refresh();assert.equal(t.root.dataset.state,'empty');assert.match(t.root.textContent,/No published results yet/);assert.equal(t.root.querySelectorAll('.overview-research-row').length,0);
 }finally{t.close();}
});
