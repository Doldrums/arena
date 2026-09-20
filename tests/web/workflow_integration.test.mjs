// Integration boundaries only. The Work Flow renderer has its own DOM tests.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const assets=new URL('../../web/',import.meta.url);
const source=readFileSync(new URL('app.js',assets),'utf8').replace(/^import .*$/mg,'')
  .replace(/^setInterval\(.*$/mg,'').replace(/^refreshRuns\(true\);$/m,'');
const snapshot=(id='path-a',science='science-a',version='v1')=>({
  run:{id,run_id:science,task_hash:'task-v1',path:'outputs/'+id,task:'test/fixture',status:'stopped'},
  content_version:version,stats:{best_score:.5,seed_score:.1,iterations:1,evaluations:1,cost_total:.01},
  trials:[],hypotheses:[],lessons:[],events:[],curves:[],programs:[],warnings:[],runtime:{active:false},
});
function mount(){
  const dom=new JSDOM(readFileSync(new URL('experiment.html',assets),'utf8'),{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,calls=[],destroys=[];
  w.ResizeObserver=class{observe(){}};w.matchMedia=()=>({matches:true});
  w.renderChart=()=>({total:0,displayed:0});
  w.renderWorkFlow=(node,options)=>{calls.push({node,options});if(!node.firstChild){const details=w.document.createElement('details');details.innerHTML='<summary>Saved request</summary><pre>Prompt fixture</pre>';node.append(details);}};
  w.destroyWorkFlow=node=>{destroys.push(node);node.replaceChildren();};
  w.fetch=async url=>({ok:true,json:async()=>snapshot(decodeURIComponent(String(url).split('/').at(-1)),'science-b','v2')});
  w.eval('{'+readFileSync(new URL('population-preview.js',assets),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderPopulationPreview,destroyPopulationPreview});}');
  w.eval('{'+source+';window.fixture={state,applySnapshot,applyRuntime,switchTab,selectRun,connection};}');
  const api=w.fixture;api.state.runId='path-a';api.state.runs=[snapshot().run];api.state.timingConnected=true;
  api.applySnapshot(snapshot());
  return {dom,w,api,calls,destroys,doc:w.document};
}

test('engine Work Flow keeps selected view, disclosures and scroll on snapshots and runtime updates',()=>{
  const {dom,api,calls,destroys,doc}=mount();try{
    doc.querySelector('#tab-workflow').click();
    const mount=calls.at(-1).node,details=mount.querySelector('details');details.open=true;mount.scrollTop=140;
    assert.equal(doc.querySelector('#tab-workflow').getAttribute('aria-selected'),'true');
    assert.equal(doc.querySelector('#tab-content').getAttribute('aria-labelledby'),'tab-workflow');
    assert.equal(calls.at(-1).options.runId,'path-a');assert.equal(calls.at(-1).options.live,false);
    api.applySnapshot(snapshot('path-a','science-a','v2'));
    assert.equal(calls.at(-1).node,mount);assert.equal(details.open,true);assert.equal(mount.scrollTop,140);
    assert.equal(calls.at(-1).options.version,'v2');
    api.applyRuntime({run:{id:'path-a',status:'running'},runtime:{active:true}});
    assert.equal(calls.at(-1).node,mount);assert.equal(calls.at(-1).options.live,true);
    doc.querySelector('#follow-button').click();assert.equal(calls.at(-1).options.follow,false);
    assert.equal(destroys.length,0);
    doc.querySelector('#tab-events').click();assert.equal(destroys.length,1);assert.equal(destroys[0],mount);
  }finally{dom.window.close();}
});

test('engine Work Flow releases the previous run and receives scientific identity when a public path is reused',async()=>{
  const {dom,api,calls,destroys}=mount();try{
    api.switchTab('workflow');const mount=calls.at(-1).node,oldIdentity=calls.at(-1).options.identity;
    api.applySnapshot(snapshot('path-a','new-science','v1'));
    assert.notEqual(calls.at(-1).options.identity,oldIdentity);
    api.state.follow=false;await api.selectRun('path-b');
    assert.equal(destroys.length,1);assert.equal(destroys[0],mount);
    assert.notEqual(calls.at(-1).node,mount);assert.equal(calls.at(-1).options.runId,'path-b');
    assert.equal(calls.at(-1).options.version,'v2');
  }finally{dom.window.close();}
});
