// Inert recorded receipts only. No server, candidate evaluation or model calls.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const root=new URL('../../web/',import.meta.url);
const app=readFileSync(new URL('app.js',root),'utf8').replace(/^import .*$/mg,'')
  .replace('setInterval(()=>refreshRuns(),10000);','').replace(/^refreshRuns\(true\);$/m,'');
const diagram=readFileSync(new URL('architecture.js',root),'utf8').replace(/export function/g,'function');
const pause=()=>new Promise(resolve=>setTimeout(resolve,5));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await pause();}assert.fail('DOM did not update');}
function mount(){
  const dom=new JSDOM(readFileSync(new URL('experiment.html',root),'utf8'),{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window;w.ResizeObserver=class{observe(){}};w.matchMedia=()=>({matches:true});
  w.renderChart=()=>({total:0,displayed:0});w.renderLLMCalls=()=>{};
  w.fetch=()=>assert.fail('fixture must not fetch');
  w.eval('{'+readFileSync(new URL('effort.js',root),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderEffort,effortDetailsHTML,publishedEffortHTML});}');
  w.eval('{'+readFileSync(new URL('population-preview.js',root),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderPopulationPreview,destroyPopulationPreview});}');
  w.eval('{'+app+';window.fixture={state,applySnapshot,renderTab,resultHistoryDetailHTML,renderResultHistory};}');
  return {dom,w,doc:w.document,api:w.fixture};
}
function snapshot(events){return {content_version:'v1',run:{id:'fixture',run_id:'science',path:'offline/fixture',task:'test/fixture'},
  stats:{iterations:1,remeasurements:1},trials:[],hypotheses:[],lessons:[],events,curves:[],programs:[]};}

test('whole-run output matches name independent evaluations without equating algorithms or scores',()=>{
  const {dom,doc,api}=mount();
  try{
    doc.getElementById('tab-content').innerHTML=api.resultHistoryDetailHTML({output_match_count:1,
      output_matches:['p27'],output_status:'exact_saved_output',source_match_count:0,ast_match_count:0});
    const section=doc.querySelector('.result-history-detail');
    assert.match(section.textContent,/Same recorded output.*1 other evaluations/);
    assert.match(section.textContent,/unpaired.*algorithm equivalence and runtime benefit are not established/);
    assert.match(section.textContent,/Equal scores alone are not counted/);
    assert.equal(section.querySelector('[data-candidate]').dataset.candidate,'p27');
    assert.doesNotMatch(section.textContent,/Same structural AST/);
    doc.getElementById('tab-content').innerHTML=api.resultHistoryDetailHTML({output_match_count:0,output_status:'unavailable'});
    assert.match(doc.querySelector('.result-history-detail').textContent,/No comparable saved output/);
    assert.doesNotMatch(doc.querySelector('.result-history-detail').textContent,/No other evaluation/);
    doc.getElementById('tab-content').innerHTML=api.resultHistoryDetailHTML({output_match_count:null,
      output_status:'exact_saved_output',output_comparison_available:false});
    assert.match(doc.querySelector('.result-history-detail').textContent,/comparison unavailable/);
    assert.doesNotMatch(doc.querySelector('.result-history-detail').textContent,/No other evaluation/);
  }finally{dom.window.close();}
});

test('seed copies stay separate from repeated measurements and hostile program IDs are inert',()=>{
  const {dom,doc,api}=mount();
  try{
    const attack='<img src=x onerror="window.owned=true">';
    doc.getElementById('tab-content').innerHTML=api.resultHistoryDetailHTML({alias_kind:'seed_copy',
      source_matches:[attack],source_match_count:23,ast_matches:[attack],ast_match_count:23,
      output_match_count:0,output_status:'exact_saved_output'});
    assert.match(doc.querySelector('.result-history-detail').textContent,/Shared seed measurement · not a new evaluation/);
    assert.equal(doc.querySelector('[data-candidate]').dataset.candidate,attack);
    assert.equal(doc.querySelectorAll('section img, section script').length,0);
    assert.doesNotMatch(doc.querySelector('.result-history-detail').textContent,/Same recorded output/);
  }finally{dom.window.close();}
});

test('population history disclosure keeps its open state and names checkpoint coverage',()=>{
  const {dom,doc,api}=mount();
  try{
    doc.getElementById('tab-content').innerHTML='<div id="population-history"></div>';
    api.state.snapshot={result_history:{counts:{unique_sources:89,repeated_outputs:6,source_aliases:23},
      coverage:{iteration:64,stale:true},by_program:{p27:{output_match_count:1,first_output_program_id:'p27'},
        p57:{output_match_count:1,first_output_program_id:'p27'}}}};
    api.renderResultHistory();
    let details=doc.querySelector('details');
    assert.match(details.querySelector('summary').textContent,/89 source variants · 6 repeated outputs · 23 source copies/);
    assert.match(details.textContent,/iteration 64.*newer measurements are not covered/);
    assert.equal(details.querySelectorAll('[data-candidate="p57"]').length,1);
    details.open=true;api.renderResultHistory();
    assert.equal(doc.querySelector('details').open,true);
  }finally{dom.window.close();}
});

test('novelty event lazily shows safe AST differences, matching program and advisory cosine',async()=>{
  const {dom,w,doc,api}=mount();
  try{
    api.state.runId='fixture';api.state.tab='events';
    const malicious='<img src=x onerror="window.owned=true">';
    const diff='--- p143\n+++ candidate\n-Constant(value=1)\n+Constant(value='+malicious+')\n';
    const event={seq:1,event:'decision',data:{policy:'candidate_novelty',accept:false,match_kind:'ast',
      matched_program_id:'p143',reason:'structural_ast_duplicate',neighbors:[
        {program_id:'p143',similarity:1,ast_diff:'',ast_diff_truncated:false},
        {program_id:malicious,similarity:.9876543,ast_diff:diff,ast_diff_truncated:true}]}};
    const view=snapshot([event]);api.applySnapshot(view);
    assert.match(doc.getElementById('attempts').textContent,/1 remeasurement/);
    assert.match(doc.querySelector('.event-title').textContent,/duplicate rejected/);
    assert.equal(doc.querySelector('.novelty-receipt'),null,'large receipt stays lazy');
    doc.querySelector('.event-row').open=true;
    await until(()=>doc.querySelector('.novelty-receipt'));
    assert.match(doc.querySelector('.novelty-facts').textContent,/p143.*structural_ast_duplicate/);
    assert.match(doc.querySelector('.novelty-receipt').textContent,/cosine 0.987654/);
    assert.match(doc.querySelector('.novelty-receipt').textContent,/similar code is not proof/);
    assert.match(doc.querySelector('.novelty-receipt').textContent,/No structural AST differences/);
    assert.equal(doc.querySelector('.novelty-ast-diff').textContent,diff);
    assert.match(doc.querySelector('.novelty-truncated').textContent,/truncated/);
    assert.equal(doc.querySelectorAll('.event-row img, .event-row script').length,0);
    const next=structuredClone(view);next.content_version='v2';api.applySnapshot(next);
    await until(()=>doc.querySelector('.novelty-ast-diff'));
    assert.equal(doc.querySelector('.event-row').open,true,'outer disclosure survives snapshot refresh');
    assert.equal(doc.querySelector('.novelty-ast-diff').textContent,diff);
  }finally{dom.window.close();}
});

test('legacy events remain generic and novelty receipts explicitly bound display size',async()=>{
  const {dom,doc,api}=mount();
  try{
    api.state.runId='fixture';api.state.tab='events';
    api.applySnapshot(snapshot([{seq:1,event:'decision',data:{policy:'controller',mode:'base'}},
      {seq:2,event:'decision',data:{policy:'candidate_novelty',accept:true,remeasurement:true,
        reason:'previous_evaluation_failed',neighbors:Array.from({length:12},(_,i)=>({program_id:'p'+i,
          similarity:0,ast_diff:'x'.repeat(13000),ast_diff_truncated:false}))}}]));
    const rows=doc.querySelectorAll('.event-row');rows.forEach(row=>row.open=true);
    await until(()=>doc.querySelector('.novelty-receipt'));
    assert.equal(doc.querySelector('[data-seq="1"] .novelty-receipt'),null);
    assert.match(doc.querySelector('[data-seq="2"] .event-title').textContent,/eligible remeasurement/);
    assert.equal(doc.querySelectorAll('.novelty-neighbor').length,10);
    assert.ok([...doc.querySelectorAll('.novelty-ast-diff')].every(node=>node.textContent.length===12000));
    assert.equal(doc.querySelectorAll('.novelty-truncated').length,10);
    assert.match(doc.querySelector('.novelty-receipt').textContent,/first 10 recorded neighbors/);
  }finally{dom.window.close();}
});

test('near-output refusals stay distinct from new output and exact repeats',()=>{
  const {dom,doc,api}=mount();
  try{
    api.state.runId='fixture';api.state.tab='events';
    const view=snapshot([
      {seq:1,event:'decision',data:{policy:'output_novelty',status:'non_improving_near_repeat'}},
      {seq:2,event:'decision',data:{policy:'output_novelty',status:'non_improving_near_repeat',remeasurement:true}},
      {seq:3,event:'decision',data:{policy:'output_novelty',status:'exact_recorded_repeat'}}
    ]);
    view.stats.repeated_outputs=3;view.stats.output_resolution=1e-6;
    api.applySnapshot(view);
    assert.equal(doc.querySelector('[data-seq="1"] .event-title').textContent,'Near output without improvement · mutation not admitted');
    assert.equal(doc.querySelector('[data-seq="2"] .event-title').textContent,'Near output without improvement · remeasurement');
    assert.match(doc.querySelector('[data-seq="3"] .event-title').textContent,/Exact recorded output repeated/);
    assert.match(doc.querySelector('#attempts').textContent,/3 output repeat refusals/);
    assert.match(doc.querySelector('#attempts').title,/task-configured output resolution/);
    assert.doesNotMatch(doc.querySelector('#attempts').textContent,/exact output repeats/);
    delete view.stats.output_resolution;view.content_version='legacy';api.applySnapshot(view);
    assert.match(doc.querySelector('#attempts').textContent,/3 exact output repeats/);
  }finally{dom.window.close();}
});

test('four-step diagram includes novelty under Generate with rejection and evaluation edges',()=>{
  const dom=new JSDOM('<main id="graph"></main>',{runScripts:'outside-only',pretendToBeVisual:true});
  try{
    const w=dom.window;w.eval('{'+diagram+';window.view={architectureGraphHTML,bindArchitectureGraph};}');
    const ids=['scheduler','parent','operator','generation','evaluation','population','mode_policy',
      'operator_bandit','refine','ideas','descriptor','memory','conclusion','reflection','reward','novelty'];
    const graph={nodes:ids.map(id=>({id,label:id==='novelty'?'Candidate novelty':id,status:'enabled',kind:'rule',
      detail:id==='novelty'?'After repair/graft; whole-run history; at most 2 resamples. Similarity is advisory.':'Recorded module',features:[]})),
      edges:[{from:'generation',to:'novelty',label:'Repaired source',kind:'flow'},
        {from:'novelty',to:'evaluation',label:'Accepted source',kind:'flow'},
        {from:'novelty',to:'generation',label:'Rejected duplicate · bounded retry',kind:'control'}]};
    const container=w.document.getElementById('graph');
    container.innerHTML=w.view.architectureGraphHTML(graph);w.view.bindArchitectureGraph(container,graph);
    assert.equal(container.querySelectorAll('.arch-step').length,4);
    const novelty=container.querySelector('[data-step="generate"] [data-node="novelty"]');
    assert.ok(novelty,'sixteenth module survives graph display bound');
    assert.match(novelty.textContent,/SHA256 → AST → code embedding/);
    novelty.click();
    assert.match(container.querySelector('.graph-inspector').textContent,/whole-run history.*2 resamples/);
    assert.ok(container.querySelector('.graph-inspector [data-from="novelty"][data-to="generation"]'));
    assert.ok(container.querySelector('.graph-inspector [data-from="novelty"][data-to="evaluation"]'));
    const historical={...graph,nodes:graph.nodes.filter(node=>node.id!=='novelty')};
    container.innerHTML=w.view.architectureGraphHTML(historical);
    assert.equal(container.querySelector('[data-node="novelty"]'),null);
    const improved=structuredClone(historical);
    improved.nodes.find(node=>node.id==='ideas').label='Two-stage ideas';
    improved.nodes.find(node=>node.id==='ideas').features=['Up to 1 card correction'];
    improved.nodes.find(node=>node.id==='memory').features=['Compact lesson memory'];
    improved.nodes.find(node=>node.id==='conclusion').features=['Host-bound source references','Up to 1 format correction'];
    container.innerHTML=w.view.architectureGraphHTML(improved);
    assert.match(container.querySelector('[data-node="ideas"]').textContent,/Up to 1 card correction/);
    assert.match(container.querySelector('[data-node="memory"]').textContent,/Compact decision cards/);
    assert.match(container.querySelector('[data-node="conclusion"]').textContent,/Host-bound references.*up to 1 correction/);
  }finally{dom.window.close();}
});
