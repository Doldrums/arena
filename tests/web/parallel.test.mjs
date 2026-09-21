import { dashboardFunction } from './helpers/dashboard-source.mjs';
// Recorded execution UI only. No server, provider, evaluator or run mutations.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const assets=new URL('../../web/',import.meta.url);
const runtimeFunction = dashboardFunction('renderRuntime', 'dashboard-runtime.js');
const architecture=readFileSync(new URL('architecture.js',assets),'utf8').replace(/export function /g,'function ');

test('runtime presents submitted work separately from executing slots and keeps unknown counts',()=>{
  const dom=new JSDOM('<div id="runtime-bar"></div>',{runScripts:'outside-only'});
  try{
    const w=dom.window;w.eval(`{
      const state={follow:true,snapshot:{run:{status:'running'},runtime:{available:true,active:true,stage:'generating',parallel:{schema:'sciel-parallel-runtime/1',wave:2,phase:'generation',workers:4,pending_llm_calls:3,pending_evaluations:null}}}};
      const $=id=>document.getElementById(id),numeric=value=>typeof value==='number'&&Number.isFinite(value),elapsed=value=>String(value),esc=value=>String(value??'').replace(/[&<>"']/g,'');
      ${runtimeFunction}
      window.draw=runtime=>{if(runtime)state.snapshot.runtime=runtime;renderRuntime();};window.draw();
    }`);
    const detail=w.document.querySelector('.runtime-parallel');
    assert.match(detail.textContent,/Wave 2 · generation · 4 workers · pending LLM 3 \/ evaluation unknown/);
    assert.match(detail.title,/include host-queued/);assert.match(detail.title,/not measured executing/);
    w.draw({available:true,active:false,parallel:{schema:'sciel-parallel-runtime/1',wave:2,phase:'<img src=x>',workers:4,pending_llm_calls:0,pending_evaluations:0}});
    assert.equal(w.document.querySelector('img'),null);
    assert.match(w.document.querySelector('.runtime-parallel').textContent,/Recorded · Wave 2/);
    w.draw({available:true,active:true,stage:'evaluating',parallel:{schema:'sciel-parallel-runtime/1',phase:'conclusion'}});
    assert.equal(w.document.querySelector('.runtime-label').textContent,'Writing conclusions');
    w.draw({available:true,active:false,stage:'evaluating',parallel:{schema:'sciel-parallel-runtime/1',phase:'paused'}});
    assert.equal(w.document.querySelector('.runtime-label').textContent,'Parallel wave paused');
    w.draw({available:true,active:false,stage:'finished'});
    assert.equal(w.document.querySelector('.runtime-parallel'),null);
    w.draw({available:true,active:true,stage:'generating',parallel:{schema:'sciel-parallel-runtime/1',phase:'generation',workers:4,portfolio:{policy:'interleaved',wave_kind:'evolution',initial_batch_attempted:4,initial_batch_total:4,attempted:4,total:24,remaining:20,eligible_islands:4,scope:'Committed attempted fresh starts, including failures.'}}});
    assert.equal(w.document.querySelector('.runtime-label').textContent,'Evolving initialized islands');
    assert.match(w.document.querySelector('.runtime-portfolio').textContent,/Initial batch 4\/4 attempted · Fresh starts 4\/24 · 20 remaining · 4 islands eligible/);
    assert.match(w.document.querySelector('.runtime-portfolio').title,/including failures/);
    w.draw({available:true,active:false,parallel:{schema:'sciel-parallel-runtime/1',phase:'paused',portfolio:{policy:'interleaved',wave_kind:'portfolio',attempted:8,total:24,remaining:16}}});
    assert.match(w.document.querySelector('.runtime-portfolio').textContent,/Recorded ·/);
    w.draw({available:true,active:true,parallel:{schema:'sciel-parallel-runtime/1',phase:'bootstrap'}});
    assert.equal(w.document.querySelector('.runtime-portfolio'),null);assert.equal(w.document.querySelector('.runtime-label').textContent,'Initializing portfolio wave');
  }finally{dom.window.close();}
});

test('architecture labels waves only for explicit recorded parallel execution',()=>{
  const dom=new JSDOM('<div id="diagram"></div>',{runScripts:'outside-only'});
  try{
    const w=dom.window;w.eval('{'+architecture+';window.render=architectureGraphHTML;}');
    const graph={nodes:[{id:'parent',label:'Parent',status:'enabled'},{id:'generation',label:'G',status:'enabled'}],edges:[]};
    assert.match(w.render(graph),/One experiment/);assert.doesNotMatch(w.render(graph),/Parallel wave/);
    graph.execution={status:'disabled',workers:4};assert.doesNotMatch(w.render(graph),/Parallel wave/);
    graph.execution={status:'enabled',workers:4,feedback:'C/R at wave boundaries'};
    const html=w.render(graph);assert.match(html,/Parallel wave/);assert.match(html,/4 workers · C\/R at wave boundaries/);
  }finally{dom.window.close();}
});

test('known unpublished spend updates independently and never calls a committed baseline total',()=>{
  const dom=new JSDOM('<div id="cost"></div><div id="cost-note"></div>',{runScripts:'outside-only'});
  try{
    const w=dom.window,fn=dashboardFunction('renderSpend', 'dashboard-summary.js');
    w.eval(`{const state={snapshot:{stats:{cost_total:1.25,cost_status:'reported'},runtime:{}}};const $=id=>document.getElementById(id),numeric=v=>typeof v==='number'&&Number.isFinite(v);${fn};window.draw=value=>{state.snapshot.runtime.uncommitted_cost=value;renderSpend();};}`);
    w.draw({available:true,wave:'2',baseline_cost:1.25,known_cost:.15,known_spend:1.4,unknown_call_count:1,pending_call_count:2});
    assert.equal(w.document.getElementById('cost').textContent,'≥ $1.4000');
    assert.match(w.document.getElementById('cost-note').textContent,/\$1.2500 committed \+ \$0.1500 uncommitted · 1 unknown-cost calls · 2 awaiting receipts/);
    w.draw({available:false,reason:'Incomplete receipt'});
    assert.equal(w.document.getElementById('cost').textContent,'≥ $1.2500');
    assert.match(w.document.getElementById('cost-note').textContent,/current wave cost unavailable/);
    w.draw(null);assert.equal(w.document.getElementById('cost').textContent,'$1.2500');
  }finally{dom.window.close();}
});
