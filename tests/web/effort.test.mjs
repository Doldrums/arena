import { dashboardSource } from './helpers/dashboard-source.mjs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
import {effortDetailsHTML,publishedEffortHTML,renderEffort} from '../../web/effort.js';

const assets=new URL('../../web/',import.meta.url);
const measured={schema:'sciel-metric-display/1',status:'measured',value:2.63,raw_score:1,label:'Sum of radii',metric_sha256:'a'.repeat(64)};
const scope={history_complete:true,status:'complete',reported_usd:3.47392,cost_status:'reported',cost_accounting:'receipt_provenance',
  physical_llm_calls:15,pending_llm_calls:0,unknown_cost_calls:0,evaluator_cascades:9,
  target_iteration:1,ordinary_iterations:0,models:['anthropic/claude-opus-5'],model_count:1,
  cutoff_at:'2026-09-20T16:52:53.042623+00:00',wall_seconds:950};
function mount(){
  const dom=new JSDOM(readFileSync(new URL('experiment.html',assets),'utf8'),{runScripts:'outside-only'}),w=dom.window;
  w.eval('{'+readFileSync(new URL('effort.js',assets),'utf8').replace(/^export /gm,'')+';Object.assign(window,{renderEffort,effortDetailsHTML,publishedEffortHTML});}');
  const app=dashboardSource({assets}).split("$('run-list').addEventListener")[0];
  w.eval('{'+app+';window.fixture={state,renderSummary,renderBenchmark,runEffort};}');
  const reference={label:'Tolerance-matched reference',metric:'Sum of radii',value:2.64,current_value:2.63,
    reference_tolerance:1e-6,run_tolerance:1e-6,references:[
      {name:'Same tolerance',value:2.64,value_label:'2.64',tolerance:1e-6,gap_percent:1,method_classification:'ai_search_framework'},
      {name:'Strict',value:2.62,tolerance:0,gap_percent:-1}],
    best_known:{status:'known',label:'Best known',name:'World',value:2.64,current_value:2.63,tolerance:1e-6},
    best_ai_method:{status:'known',label:'Best AI search',name:'AI',value:2.635,current_value:2.63,tolerance:1e-6}};
  const snapshot={run:{id:'test',path:'fixture',name:'Fixture'},stats:{best_metric_display:measured,best_score:1},events:[],
    trials:[],hypotheses:[],lessons:[],runtime:{},best_candidate_id:'p29',benchmark:reference,
    effort:{best_program_id:'p29',to_best:scope,total:{...scope,terminal:true,target_iteration:null,ordinary_iterations:4,reported_usd:6.265515,physical_llm_calls:31}}};
  w.fixture.state.snapshot=snapshot;
  return {dom,w,doc:w.document,snapshot,api:w.fixture};
}

test('record cutoff and total effort are separate, with precise counting units',()=>{
  const {dom,doc,api,snapshot}=mount();try{
    api.renderSummary();api.renderBenchmark();
    assert.match(doc.querySelector('#best-score-comparison').textContent,/below best known.*below best ai search/);
    const cards=doc.querySelectorAll('.effort-scopes section');
    assert.match(cards[0].textContent,/To current best · p29.*\$3\.4739.*9 program evaluations · 15 completed LLM calls/);
    assert.match(cards[0].textContent,/Best reached at evolution iteration 1/);
    assert.doesNotMatch(cards[0].textContent,/0 ordinary iterations logged/);
    assert.match(cards[1].textContent,/Total run · finished.*\$6\.2655.*31 completed LLM calls/);
    assert.match(cards[0].textContent,/CPU time unknown/);
    const rows=[...doc.querySelectorAll('.benchmark-table tbody tr:not(.benchmark-group)')];
    assert.match(rows[0].textContent,/Same tolerance/);assert.match(rows[1].textContent,/This run · bestp29/);assert.match(rows[2].textContent,/Strict/);
    assert.equal(rows[1].querySelector('[data-benchmark-candidate]').dataset.benchmarkCandidate,'p29');assert.match(rows[2].textContent,/Not comparable/);
    assert.doesNotMatch(rows[2].textContent,/1\.00% above/);
    assert.match(rows[0].textContent,/Steps, USD, calls and models unknown/);
    snapshot.benchmark.current_value=2.62;api.renderBenchmark();
    assert.equal(doc.querySelector('.benchmark-current').dataset.comparable,'false','stale native comparison cannot rank a current row');
    assert.match(doc.querySelector('.benchmark-values').textContent,/Gap to reference—/);
    snapshot.benchmark.best_known.current_value=2.62;snapshot.benchmark.best_ai_method.tolerance=0;api.renderSummary();
    assert.equal(doc.querySelector('#best-score-comparison').hidden,true,'both stale and mismatched references fail closed');
  }finally{dom.window.close();}
});

test('unknown, pending and estimated charges are not free or final costs; model names are inert',()=>{
  const html=effortDetailsHTML({...scope,reported_usd:null,pending_llm_calls:2,unknown_cost_calls:1,models:['<script>bad</script>']});
  const dom=new JSDOM(html);try{
    assert.match(dom.window.document.body.textContent,/Unknown USD.*2 calls pending · 1 charges unknown/);
    assert.equal(dom.window.document.querySelector('script'),null);
    assert.doesNotMatch(html,/\$0\.0000/);
    assert.match(effortDetailsHTML({...scope,pending_llm_calls:1}),/≥ \$3\.4739/);
    assert.match(renderEffort(null),/candidate’s generation charge is not the total cost/);
  }finally{dom.window.close();}
});

test('published generation budget is not called evaluated candidates or known discovery dollars',()=>{
  const html=publishedEffortHTML({status:'reported',steps:{value:150,unit:'generations',scope:'Whole experiment; first-attainment cutoff unknown'},
    usd:null,llm_calls:null,models:[{name:'Generator',role:'generation'},{name:'Meta',role:'novelty'}],model_count:2,
    auxiliary_models:[{name:'Embedding',role:'embedding'}],note:'Training budget, not the exact first-result effort.',
    generated_programs:{value:33280,unit:'samples',status:'derived',derivation:'65 × 32 × 16; not evaluations'},
    source_url:'https://example.org/paper#methods',locator:'§4.1'});
  const dom=new JSDOM(html);try{
    const text=dom.window.document.body.textContent;
    assert.match(text,/150 generations.*first-attainment cutoff unknown.*Unknown USD.*Unknown LLM calls/);
    assert.match(text,/2 LLM identities.*Generator \(generation\) · Meta \(novelty\).*Auxiliary: Embedding \(embedding\)/);
    assert.match(text,/33,280 samples · derived.*65 × 32 × 16; not evaluations/);
    assert.match(text,/Effort source.*§4.1/);
    assert.equal(dom.window.document.querySelector('a').href,'https://example.org/paper#methods');
    assert.equal(dom.window.document.querySelector('a').rel,'noopener noreferrer');
    assert.doesNotMatch(text,/150 evaluator|\$0\.0000/);
  }finally{dom.window.close();}
});


test('subscription usage is completed and unpriced, never displayed as zero-dollar spend',()=>{
  const {dom,doc,api,snapshot}=mount();try{
    snapshot.effort.total={...scope,reported_usd:null,unpriced_llm_calls:15,
      cost_status:'subscription_unpriced',prompt_tokens:400,completion_tokens:120,token_usage_complete:true};
    api.renderSummary();
    assert.equal(doc.querySelector('#cost').textContent,'Subscription');
    assert.match(doc.querySelector('#cost-note').textContent,/15 completed physical LLM calls.*USD unavailable/);
    const html=effortDetailsHTML(snapshot.effort.total);
    assert.match(html,/Subscription · USD unavailable.*15 completed subscription calls/);
    assert.match(html,/400 input tokens · 120 output tokens/);
    assert.doesNotMatch(html,/\$0\.0000|charges unknown/);
    assert.match(effortDetailsHTML({...snapshot.effort.total,reported_usd:1.5}),/≥ \$1\.5000 known \+ subscription/);
  }finally{dom.window.close();}
});


test('first pending subscription call is not zero dollars or a completed call',()=>{
  const {dom,doc,api,snapshot}=mount();try{
    snapshot.stats={...snapshot.stats,billing_mode:'subscription_unpriced',cost_status:'subscription_unpriced'};
    snapshot.effort.total={...scope,reported_usd:null,unpriced_llm_calls:0,physical_llm_calls:0,
      pending_llm_calls:1,unknown_cost_calls:0,cost_status:'subscription_unpriced',billing_mode:'subscription_unpriced',status:'partial'};
    api.renderSummary();
    assert.equal(doc.querySelector('#cost').textContent,'Subscription');
    assert.match(doc.querySelector('#cost-note').textContent,/0 completed physical LLM calls.*1 pending/);
    const html=effortDetailsHTML(snapshot.effort.total);
    assert.match(html,/Subscription · USD unavailable/);
    assert.doesNotMatch(html,/\$0\.0000|completed subscription calls/);
  }finally{dom.window.close();}
});

test('subscription billing survives missing physical history and unknown outcomes',()=>{
  const {dom,doc,api,snapshot}=mount();try{
    snapshot.effort=null;
    snapshot.stats={...snapshot.stats,cost_total:0,billing_mode:'subscription_unpriced',cost_status:'known_logged_lower_bound',unknown_cost_present:true};
    snapshot.runtime={uncommitted_cost:{available:true,known_spend:0,baseline_cost:0,known_cost:0,
      unpriced_call_count:2,unknown_call_count:1,pending_call_count:3}};
    api.renderSummary();
    assert.equal(doc.querySelector('#cost').textContent,'Subscription');
    assert.match(doc.querySelector('#cost-note').textContent,/3 awaiting receipts.*1 unknown-cost calls/);
    const line=api.runEffort({committed_effort:{ordinary_iterations:2,known_llm_usd:0,
      billing_mode:'subscription_unpriced',cost_status:'known_logged_lower_bound',unknown_cost_present:true,configured_models:['native-model']}});
    assert.match(line,/Subscription · USD unavailable.*charges unknown/);
    assert.doesNotMatch(line,/\$0\.00/);
    snapshot.runtime.uncommitted_cost={available:false};api.renderSummary();
    assert.match(doc.querySelector('#cost-note').textContent,/charges unknown.*current wave receipts unavailable/);
    assert.match(api.runEffort({committed_effort:{ordinary_iterations:1,known_llm_usd:1.25,provider_reported_llm_usd:1.25,
      billing_mode:'subscription_unpriced',cost_status:'known_logged_lower_bound'}}),/≥ \$1\.25 known \+ subscription/);
    assert.match(api.runEffort({committed_effort:{ordinary_iterations:1,known_llm_usd:1.25,cost_status:'reported'}}),/USD unverified committed/);
  }finally{dom.window.close();}
});

test('token estimates and CPU omissions cannot be presented as measured all-in spend',()=>{
  const {dom,doc,api,snapshot}=mount();try{
    snapshot.effort.total={...scope,reported_usd:null,estimated_usd:12.5,
      estimated_cost_calls:15,unknown_cost_calls:15,cost_status:'partial_or_estimated',terminal:true};
    api.renderSummary();
    assert.equal(doc.querySelector('#cost').textContent,'$12.5000 estimate');
    assert.match(doc.querySelector('#cost-note').textContent,/historical token-rate estimate; not billed USD/);
    assert.match(doc.querySelector('#cost-note').textContent,/CPU\/infrastructure cost unavailable · all-in cost unavailable/);
    const html=renderEffort(snapshot.effort);
    assert.match(html,/Total run · finished/);
    assert.match(html,/Unknown USD.*Provider-reported LLM charges only.*\$12\.5000 historical token-rate estimate/);
    assert.doesNotMatch(html,/Total run · now|≥ \$12\.5000/);
    snapshot.effort.total.billing_mode='subscription_unpriced';api.renderSummary();
    assert.equal(doc.querySelector('#cost').textContent,'Subscription');
    assert.match(doc.querySelector('#cost-note').textContent,/not billed USD/);
  }finally{dom.window.close();}
});

test('old mixed-cost snapshots and unconfirmed run boundaries remain explicitly unverified',()=>{
  const {dom,doc,api,snapshot}=mount();try{
    const legacy={...scope,reported_usd:9.9,wall_source:'last_recorded_boundary'};
    delete legacy.cost_accounting;snapshot.effort.total=legacy;
    api.renderSummary();
    assert.equal(doc.querySelector('#cost').textContent,'USD unavailable');
    assert.match(doc.querySelector('#cost-note').textContent,/\$9\.9000 recorded accounting; billing source unverified/);
    const html=renderEffort(snapshot.effort);
    assert.match(html,/Total run · recorded.*end time unconfirmed/);
    assert.doesNotMatch(html,/Total run · finished|Total run · live/);
    assert.match(api.runEffort({committed_effort:{ordinary_iterations:2,estimated_llm_usd:3.2,
      cost_basis:'token_estimate'}}),/\$3\.20 token-rate estimate/);
  }finally{dom.window.close();}
});
