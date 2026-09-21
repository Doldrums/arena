import { dashboardSource } from './helpers/dashboard-source.mjs';
// Offline app integration: no server, run artifacts, candidate execution or model calls.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const root=new URL('../../web/',import.meta.url);
const source=dashboardSource({assets:root})
  .replace(/setInterval\(\(\) => refreshRuns\(\), 10000\);/g, '').replace(/^refreshRuns\(true\);$/m,'');
const pause=()=>new Promise(resolve=>setTimeout(resolve,5));
async function until(fn){for(let n=0;n<100;n++){if(fn())return;await pause();}assert.fail('DOM did not update');}
const snapshot=(science='A',version='v1')=>({
  run:{id:'same-path',run_id:science,task_hash:'task-v1',path:'outputs/offline-fixture',task:'test/fixture',status:'running'},
  content_version:version,stats:{best_score:.5,seed_score:.1,iterations:1,evaluations:1,cost_total:.01},
  trials:[{id:'r1',candidate_id:'p1',iteration:1,score:.5,code_available:true,status:'evaluated'}],
  hypotheses:[],lessons:[],events:[],curves:[],programs:[],warnings:[],
});
const detail=(id,code)=>({id,code,parent_code:'parent source',diff:'+'+code,code_source:'checkpoint'});
function mount(fetchDetail){
  const dom=new JSDOM(readFileSync(new URL('experiment.html',root),'utf8'),{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window;
  w.ResizeObserver=class{observe(){}};w.matchMedia=()=>({matches:true});
  w.renderChart=()=>({total:0,displayed:0});w.renderLLMCalls=()=>{};
  w.fetch=async url=>({ok:true,json:()=>fetchDetail(url)});
  w.eval('{'+readFileSync(new URL('effort.js',root),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderEffort,effortDetailsHTML,publishedEffortHTML});}');
  w.eval('{'+readFileSync(new URL('population-preview.js',root),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderPopulationPreview,destroyPopulationPreview});}');
  w.eval('{'+source+';window.fixture={state,applySnapshot,renderCode,applyRuntime};}');
  const {state}=w.fixture;state.runId='same-path';state.tab='code';state.codeMode='code';state.runs=[snapshot().run];
  return {dom,w,api:w.fixture,body:()=>w.document.querySelector('#code-body')?.textContent||''};
}

test('source inspector refetches identical candidate ids after scientific run or task identity changes',async()=>{
  let code='run A source',requests=0;
  const {dom,api,body}=mount(async()=>{requests++;return detail('p1',code);});
  try{
    api.applySnapshot(snapshot());await until(()=>body().includes('run A source'));
    code='run B source';api.applySnapshot(snapshot('B'));
    await until(()=>body().includes('run B source'));
    assert.equal(requests,2,'public path, candidate id and content version may all be reused');
    code='new task source';const next=snapshot('B');next.run.task_hash='task-v2';api.applySnapshot(next);
    await until(()=>body().includes('new task source'));assert.equal(requests,3);
    assert.doesNotMatch(body(),/run A source|run B source/);
  }finally{dom.window.close();}
});

test('a pending source becomes available on a content update; heartbeat-only updates reuse it',async()=>{
  let code=null,requests=0;
  const {dom,api,body}=mount(async()=>{requests++;return detail('pending-r2',code);});
  try{
    const first=snapshot();first.trials=[{id:'pending-r2',iteration:2,score:null,status:'pending',code_available:false}];
    api.applySnapshot(first);await until(()=>api.state.detail);
    assert.equal(api.state.detail.code,null);
    code='newly returned source';const next=structuredClone(first);next.content_version='v2';next.trials[0].code_available=true;
    api.applySnapshot(next);await until(()=>body().includes('newly returned source'));
    assert.equal(requests,2);
    api.applyRuntime({run:{id:'same-path',status:'running'},runtime:{active:true,stage:'generating'}});
    api.applySnapshot(structuredClone(next));api.renderCode();await pause();
    assert.equal(requests,2,'runtime refresh and same source rerender do not refetch');
  }finally{dom.window.close();}
});

test('source requests deduplicate while pending and stale completions cannot overwrite current run',async()=>{
  const pending=[];
  const {dom,api,body}=mount(()=>new Promise(resolve=>pending.push(resolve)));
  try{
    api.applySnapshot(snapshot());await until(()=>pending.length===1);
    api.renderCode();api.renderCode();await pause();assert.equal(pending.length,1);
    api.applySnapshot(snapshot('B','v2'));await until(()=>pending.length===2);
    pending[1](detail('p1','current source'));await until(()=>body().includes('current source'));
    pending[0](detail('p1','obsolete source'));await pause();
    assert.match(body(),/current source/);assert.doesNotMatch(body(),/obsolete source/);
    assert.equal(api.state.detail.code,'current source');
  }finally{dom.window.close();}
});
