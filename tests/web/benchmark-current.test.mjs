import { dashboardSource } from './helpers/dashboard-source.mjs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const app=dashboardSource().split("$('run-list').addEventListener")[0];
const effort=readFileSync(new URL('../../web/effort.js',import.meta.url),'utf8').replace(/^export /gm,'');
function loadApp(window){
  window.eval('{'+effort+';Object.assign(window,{renderEffort,effortDetailsHTML,publishedEffortHTML});}');
}
const metric=(value,status='measured')=>({schema:'sciel-metric-display/1',status,value:status==='measured'?value:null,raw_score:.99,label:'Native metric',metric_sha256:'a'.repeat(64)});
const row=(name,value,tolerance=1e-6)=>({name,value,value_label:String(value),tolerance,status:'reported',source_name:'Primary source',source_url:'https://example.org/result'});
function fixture(extra={}){
  const data={stats:{best_score:.99,best_metric_display:metric(2.5)},best_candidate_id:'p29',...extra};
  const reference={metric:'Native metric',run_tolerance:1e-6,current_value:2.5,references:[row('Lower',2.4),row('Strict',9,0),row('Higher',2.6)],...extra.reference};
  const dom=new JSDOM('<main></main>',{runScripts:'outside-only'});
  loadApp(dom.window);
  dom.window.eval(app+';window.tableFixture={render(data,reference){state.snapshot=data;return benchmarkTableHTML(reference);}};');
  const render=()=>{dom.window.document.querySelector('main').innerHTML=dom.window.tableFixture.render(data,reference);return dom.window.document;};
  return {dom,data,reference,render};
}

test('best native solution is positioned among same-tolerance references without altering their saved values',()=>{
  const {dom,data,reference,render}=fixture(),before=JSON.stringify(reference);
  try{
    const doc=render(),matched=doc.querySelector('tbody[data-comparability="matched"]');
    assert.deepEqual([...matched.querySelectorAll('td:first-child')].map(x=>x.textContent),['Higher','This run · bestp29 ↗','Lower']);
    const current=doc.querySelector('[data-current-solution]');
    assert.equal(current.cells[1].textContent,'2.5');assert.equal(current.dataset.comparable,'true');
    assert.equal(current.querySelector('button').dataset.benchmarkCandidate,'p29');
    assert.equal(doc.querySelector('thead th:nth-child(2)').textContent,'Native metric');
    const strict=doc.querySelector('tbody[data-comparability="unranked"] [data-reference-row]');
    assert.equal(strict.cells[0].textContent,'Strict');assert.match(strict.cells[3].textContent,/Not comparable/);
    assert.equal(JSON.stringify(reference),before,'presentation never modifies reference evidence');
    data.stats.best_metric_display=metric(2.7);reference.current_value=2.7;data.best_candidate_id='p32';
    const updated=render();assert.equal(updated.querySelector('tbody[data-comparability="matched"] td:first-child').textContent,'This run · bestp32 ↗');
    assert.equal(updated.querySelectorAll('[data-current-solution]').length,1);
  }finally{dom.window.close();}
});

test('native measured zero remains a result, while invalid/failed/unknown outcomes never acquire a numerical rank',()=>{
  for(const status of ['measured','invalid_penalty','failed','unknown']){
    const {dom,render}=fixture({stats:{best_score:.99,best_metric_display:metric(0,status)},reference:{current_value:status==='measured'?0:null}});
    try{
      const current=render().querySelector('[data-current-solution]');
      assert.equal(current.dataset.comparable,String(status==='measured'));
      if(status==='measured')assert.equal(current.cells[1].textContent,'0');
      else{assert.match(current.cells[3].textContent,/Not ranked/);assert.notEqual(current.cells[1].textContent,'0');}
    }finally{dom.window.close();}
  }
});

test('unknown tolerance or mismatched benchmark binding keeps the headline measurement visible without ranking',()=>{
  for(const reference of [{run_tolerance:null},{run_tolerance:'1e-6'},{run_tolerance:-1},{current_value:2.49},{current_value:null}]){
    const {dom,render}=fixture({reference});
    try{
      const doc=render(),current=doc.querySelector('[data-current-solution]');
      assert.equal(current.cells[1].textContent,'2.5');assert.equal(current.dataset.comparable,'false');
      assert.equal(doc.querySelectorAll('[data-reference-row] td:nth-child(4)').length,3);
      assert.ok([...doc.querySelectorAll('[data-reference-row] td:nth-child(4)')].every(x=>!x.textContent.includes('%')));
    }finally{dom.window.close();}
  }
});

test('strict tolerance zero is comparable; missing program identity cannot invent a source link',()=>{
  const {dom,render}=fixture({best_candidate_id:null,reference:{run_tolerance:0}});
  try{
    const doc=render(),current=doc.querySelector('[data-current-solution]');
    assert.equal(current.dataset.comparable,'true');assert.equal(current.cells[2].textContent,'τ = 0 (strict)');
    assert.equal(current.querySelector('button'),null);assert.match(current.textContent,/Program ID not recorded/);
    assert.equal(doc.querySelector('tbody[data-comparability="matched"] [data-reference-row] td').textContent,'Strict');
  }finally{dom.window.close();}
});

test('long native precision and unsafe labels are preserved as inert text',()=>{
  const native=2.6359830589175943,{dom,render}=fixture({best_candidate_id:'p"><script>bad</script>',stats:{best_score:.99,best_metric_display:metric(native)},reference:{current_value:native,metric:'Metric <script>',references:[{...row('<script>bad</script>',3),source_url:'javascript:alert(1)'}]}});
  try{
    const doc=render(),current=doc.querySelector('[data-current-solution]');
    assert.equal(current.cells[1].textContent,String(native));assert.equal(current.cells[1].title,String(native));
    assert.equal(doc.querySelector('script'),null);assert.equal(doc.querySelector('a'),null);
    assert.equal(current.querySelector('button').dataset.benchmarkCandidate,'p"><script>bad</script>');
  }finally{dom.window.close();}
});

test('tiny nonzero gaps do not round to equality and method labels do not infer AI from names',()=>{
  const {dom,render}=fixture({reference:{references:[{...row('Close AI title',2.500000000001),method_classification:'unknown'},{...row('Exact',2.5),method_classification:'ai_search_framework',classification_source_url:'https://example.org/method'},{...row('Assisted',2.4),method_classification:'ai_assisted'}]}});
  try{
    const refs=[...render().querySelectorAll('[data-reference-row]')];
    assert.equal(refs[0].cells[3].textContent,'<0.000001% below');
    assert.match(refs[0].cells[5].textContent,/Method not classified/);
    assert.equal(refs[1].cells[3].textContent,'equal');assert.match(refs[1].cells[5].textContent,/AI search/);
    assert.equal(refs[1].querySelector('small a').href,'https://example.org/method');
    assert.match(refs[2].cells[5].textContent,/AI-assisted/);
  }finally{dom.window.close();}
});

test('reference header has the same binding guard and current-program navigation follows refreshes',()=>{
  const html=readFileSync(new URL('../../web/experiment.html',import.meta.url),'utf8');
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'http://fixture.invalid/'});
  loadApp(dom.window);
  dom.window.eval(app+';renderPlot=()=>{};switchTab=tab=>{state.tab=tab;};window.fixture={state,render(data){state.snapshot=data;renderBenchmark();}};');
  const api=dom.window.fixture,data={events:[],best_candidate_id:'p29',stats:{best_score:.99,best_metric_display:metric(2.5)},benchmark:{value:2.6,current_value:2.5,run_tolerance:1e-6,reference_tolerance:1e-6,metric:'Native metric',references:[row('Higher',2.6)]}};
  try{
    api.render(data);const doc=dom.window.document;
    assert.equal(doc.querySelector('.benchmark-values>div:nth-child(3) strong').textContent,'-0.100000');
    assert.equal(doc.querySelector('.benchmark-values>div:nth-child(4) strong').textContent,'96.1538%');
    const disclosure=doc.querySelector('.benchmark-disclosure');disclosure.open=true;
    data.best_candidate_id='p32';api.render(data);
    assert.equal(doc.querySelector('.benchmark-disclosure').open,true);
    doc.querySelector('[data-benchmark-candidate]').click();
    assert.equal(api.state.selected,'p32');assert.equal(api.state.tab,'code');
    for(const change of [{current_value:2.49},{current_value:2.5,reference_tolerance:0},{reference_tolerance:1e-6,run_tolerance:null}]){
      Object.assign(data.benchmark,change);api.render(data);
      assert.equal(doc.querySelector('.benchmark-values>div:nth-child(3) strong').textContent,'—');
      assert.equal(doc.querySelector('.benchmark-values>div:nth-child(4) strong').textContent,'—');
    }
  }finally{dom.window.close();}
});
