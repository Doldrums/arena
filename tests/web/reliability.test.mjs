import { dashboardSource } from './helpers/dashboard-source.mjs';
// Recorded fixtures only: no server, renderer, evaluator or provider calls.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const root=new URL('../../web/',import.meta.url);
const app=dashboardSource({assets:root})
  .replace(/setInterval\(\(\) => refreshRuns\(\), 10000\);/g, '').replace(/^refreshRuns\(true\);$/m,'');
function mount(){
  const dom=new JSDOM(readFileSync(new URL('experiment.html',root),'utf8'),{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window;w.ResizeObserver=class{observe(){}};w.matchMedia=()=>({matches:true});
  w.renderChart=()=>({total:0,displayed:0});w.fetch=()=>assert.fail('fixture must not fetch');
  w.eval('{'+readFileSync(new URL('effort.js',root),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderEffort,effortDetailsHTML,publishedEffortHTML});}');
  w.eval('{'+readFileSync(new URL('population-preview.js',root),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderPopulationPreview,destroyPopulationPreview});}');
  w.eval('{'+app+';window.fixture={state,applySnapshot,renderTab};}');
  const api=w.fixture;api.state.runId='fixture';api.state.tab='lessons';
  return {dom,api,doc:w.document};
}
function snapshot(reliability){return {content_version:'v1',run:{id:'fixture',run_id:'science',path:'offline/fixture',task:'test/fixture'},
  stats:{iterations:1,lessons:48},trials:[],hypotheses:[],lessons:[],events:[],curves:[],programs:[],reliability};}
function reliability(){return {memory:{stored_active:48,attempts:297,metadata_known:297,metadata_unknown:0,
  zero_delivered_due_size:147,latest:{ranked:48,selected:null,delivered:0,dropped_by_size:46},
  history:[{experiment_id:'r297',stored_active:null,ranked:48,selected:null,delivered:0,dropped_by_size:46,
    omission_reasons:{card_char_limit:46}}]},
  conclusions:{recorded:true,parsed:81,rejected:157,skipped:3,repairs:0,history:[]},
  ideas:{recorded:true,finished:55,rejected_before_code:28,invalid_cards:27,duplicates:1,repair_exhausted:0,history:[]},
  notes:['Recorded in the prepared prompt; model use is not established.']};}

test('Lessons separates stored knowledge from actual prompt delivery, even when no lesson cards are retained',()=>{
  const {dom,api,doc}=mount();
  try{
    api.applySnapshot(snapshot(reliability()));
    assert.match(doc.querySelector('#lessons-count').textContent,/48/);
    assert.match(doc.querySelector('#hypotheses-count').textContent,/0 delivered in latest prompt/);
    const section=doc.querySelector('.research-reliability');assert.ok(section);
    assert.match(section.textContent,/147 attempts delivered no ranked lessons with size omissions/);
    const metrics=[...section.querySelector('.reliability-metrics').children].map(x=>x.textContent);
    assert.deepEqual(metrics,['Stored active48','Latest ranked48','Latest selectedUnknown','Latest delivered0','Latest dropped by size46']);
    assert.match(section.textContent,/Parsed81.*Rejected157.*Skipped3/);
    assert.match(section.textContent,/Rejected before code28.*Invalid cards27/);
    const panel=section.querySelector('[data-reliability-panel="memory"]');panel.open=true;panel.querySelector('summary').focus();
    api.applySnapshot({...snapshot(reliability()),content_version:'v2'});
    assert.equal(doc.querySelector('[data-reliability-panel="memory"]').open,true);
    assert.equal(doc.activeElement,doc.querySelector('[data-reliability-panel="memory"] summary'));
  }finally{dom.window.close();}
});

test('unknown historical delivery remains unknown; diagnostic text is escaped and rows are bounded',()=>{
  const {dom,api,doc}=mount();
  try{
    const view=reliability();view.memory={stored_active:null,attempts:1,metadata_known:0,metadata_unknown:1,
      zero_delivered_due_size:null,latest:{ranked:null,selected:null,delivered:null,dropped_by_size:null},history:[]};
    const hostile='<img src=x onerror="window.owned=true">';
    view.conclusions={recorded:false,parsed:0,rejected:0,skipped:0,repairs:0,
      history:Array.from({length:140},(_,i)=>({experiment_id:'r'+i,status:'parsed',repairs:1,reason:hostile,
        diagnostic:{path:'quote',actual:513}}))};
    api.applySnapshot(snapshot(view));
    assert.equal(doc.querySelector('#lessons-count').textContent,'—');
    assert.match(doc.querySelector('#hypotheses-count').textContent,/not recorded/);
    assert.match(doc.querySelector('.reliability-outcomes').textContent,/ParsedNot recorded/);
    assert.equal(doc.querySelectorAll('[data-reliability-panel="conclusions"] tbody tr').length,120);
    assert.match(doc.querySelector('[data-reliability-panel="conclusions"]').textContent,/<img src=x/);
    assert.equal(doc.querySelectorAll('.research-reliability img, .research-reliability script').length,0);
    api.applySnapshot({...snapshot(undefined),content_version:'old'});
    assert.match(doc.querySelector('.research-reliability').textContent,/metadata not recorded/);
  }finally{dom.window.close();}
});

test('hypothesis badges describe numerical forecast agreement, not supported causal mechanisms',()=>{
  const {dom,api,doc}=mount();
  try{
    api.state.tab='hypotheses';
    const view=snapshot(undefined);
    view.hypotheses=['CONFIRMED','REFUTED'].map((verdict,i)=>({id:'r'+i,iteration:i+1,parent_id:'p1',
      hypothesis:{text:'A faster helper will increase useful search.',predicted_low:.01,predicted_high:.02},
      forecast_verdict:verdict,actual_delta:i===0?.015:-.01,score:.8}));
    api.applySnapshot(view);
    const labels=[...doc.querySelectorAll('.research-card .badge')].map(node=>node.textContent);
    assert.deepEqual(labels,['Forecast outside interval','Forecast within interval']);
    assert.ok(!labels.some(label=>/Supported|Refuted/.test(label)));
    assert.match(doc.querySelector('#tab-content').textContent,/A faster helper will increase useful search/);
  }finally{dom.window.close();}
});
