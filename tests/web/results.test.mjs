import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html = readFileSync(new URL('../../web/results.html',import.meta.url),'utf8').replace('data-results-app="true"','data-results-app="test"');
const source = readFileSync(new URL('../../web/arena-results.js',import.meta.url),'utf8').replace(/^export /gm,'');
const run = {
  id:'image-run',framework:'sciel-release',profile:'reference-sat',model:'model-a',state:'completed',label:'SCiEL pilot',returncode:0,
  metrics:{wall_seconds:400,canonical:{evaluations:7,valid:7,invalid:0,unique_valid_candidates:3,best_score:1,seed_score:1,score_gain:0,metric:'accuracy',direction:'maximize',task_id:'reference-sat',task_name:'Reference SAT',cohort:'a'.repeat(64),receipt_hashes:['b'.repeat(64)],status:'recorded'},native:{best_score:1,metric:'native_accuracy',direction:'maximize',task:'SAT',scope:'native'},usage:{total_tokens:5200,input_tokens:4000,output_tokens:1200,requests:6,complete:true,usd:null},budget:{generation_calls:null,evaluations:4,label:'Native search budget (B_evals)'},evidence:{artifact_count:15,issues:[]}}
};
const clone = value => JSON.parse(JSON.stringify(value));
const flush = async () => { for (let i=0;i<5;i++) await new Promise(resolve => setImmediate(resolve)); };
function mount({rows=[run],initialKey='test-private-key',responseStatus=200,responseExtra={},fetcher:customFetcher}={}) {
  const dom = new JSDOM(html,{url:'http://arena.test/results',runScripts:'outside-only',pretendToBeVisual:true});
  const w = dom.window, doc = w.document, calls = [], stored = new Map(initialKey ? [['arena.queue.session-key',initialKey]] : []);
  const storage = {getItem:key=>stored.get(key),setItem:(key,value)=>stored.set(key,value),removeItem:key=>stored.delete(key)};
  w.HTMLDialogElement.prototype.showModal=function(){ this.setAttribute('open',''); };
  w.HTMLDialogElement.prototype.close=function(){ this.removeAttribute('open'); };
  const fetcher = async (path,options) => {
    calls.push({path,options});
    if (customFetcher) return customFetcher(path,options,calls.length);
    return {ok:responseStatus===200,status:responseStatus,json:async()=>({schema:'arena.results/1',generated_at:1789958000,scope:'owner',runs:rows,total:rows.length,truncated:false,notes:[],...responseExtra})};
  };
  w.eval(`${source};window.mountResults=initResults;`);
  const app = w.mountResults({doc,fetcher,storage,pollMs:0});
  function change(id,value) { const node = doc.getElementById(id); node.value=value; node.dispatchEvent(new w.Event('change',{bubbles:true})); }
  return {dom,w,doc,calls,stored,app,change,close(){app.destroy();dom.window.close();}};
}

test('unauthenticated results never request data or queue work',async()=>{
  const t=mount({initialKey:''}); try { await flush(); assert.equal(t.calls.length,0); assert.equal(t.doc.getElementById('results-refresh').disabled,true); assert.match(t.doc.getElementById('results-status').textContent,/Connect/); } finally {t.close();}
});
test('the existing tab key reads only the same-origin results endpoint',async()=>{
  const t=mount(); try {await flush(); assert.equal(t.calls.length,1); const call=t.calls[0]; assert.equal(call.path,'/api/control/results'); assert.equal(call.options.headers.Authorization,'Bearer test-private-key'); assert.equal(call.options.redirect,'error'); assert.equal(call.options.method,undefined); assert.equal(call.options.cache,'no-store'); assert.equal(t.doc.querySelectorAll('tbody tr').length,1); assert.equal(t.doc.getElementById('results-framework').value,'sciel-release');} finally {t.close();}
});
test('all process states stay visible; valid receipts survive a failed process',async()=>{
  const failed=clone(run);failed.id='failed-run';failed.state='failed';failed.returncode=1;failed.metrics.evidence.issues=['Native process failed after recording evidence'];
  const native=clone(run);native.id='source-run';native.framework='sciel';
  const t=mount({rows:[run,failed,native]}); try {await flush();assert.equal(t.doc.querySelectorAll('tbody tr').length,2); const row=t.doc.querySelector('[data-run-id="failed-run"]'); assert.match(row.textContent,/failed/);assert.match(row.textContent,/7 valid/);assert.match(row.textContent,/Process exit 1/); t.change('results-framework','all'); assert.equal(t.doc.querySelectorAll('tbody tr').length,3); t.change('results-state','attention');assert.equal(t.doc.querySelectorAll('tbody tr').length,1);}finally{t.close();}
});
test('seed-equal best shows no improvement and budget is not mislabeled as requests',async()=>{
  const t=mount();try{await flush();const text=t.doc.querySelector('tbody').textContent;assert.match(text,/1→1/);assert.match(text,/No measured gain over seed/);assert.match(text,/Native search budget \(B_evals\)/);assert.match(text,/6 recorded requests/);assert.doesNotMatch(text,/Generation-call limit|perfect solution|optimal/i);assert.match(t.doc.getElementById('results-overview').textContent,/3/);assert.match(t.doc.getElementById('results-overview').textContent,/Counted within each run/);}finally{t.close();}
});
test('unknown evidence never becomes zero fitness, zero tokens or a plotted point',async()=>{
  const missing={...clone(run),metrics:{wall_seconds:null,canonical:{evaluations:0,valid:0,invalid:0,unique_valid_candidates:0,best_score:null,seed_score:null,status:'missing'},native:{best_score:null},usage:{total_tokens:null,requests:null,complete:false},budget:{generation_calls:null},evidence:{issues:[]}}};
  const t=mount({rows:[missing]});try{await flush();const text=t.doc.querySelector('tbody').textContent;assert.match(text,/—→—/);assert.match(text,/Tokens not recorded/);assert.match(text,/No canonical receipts/);assert.equal(t.doc.querySelectorAll('.point').length,0);assert.equal(t.doc.querySelectorAll('.result-metric-value')[2].textContent,'—');}finally{t.close();}
});
test('zero scores are real values and minimize direction handles seed gain',async()=>{
  const zero=clone(run);zero.metrics.canonical={...zero.metrics.canonical,best_score:0,seed_score:2,direction:'minimize',metric:'MSE'};
  const t=mount({rows:[zero]});try{await flush();assert.match(t.doc.querySelector('tbody').textContent,/2→0/);assert.match(t.doc.querySelector('tbody').textContent,/Gain over seed: 2/);assert.equal(t.doc.querySelectorAll('.point').length,1);assert.match(t.doc.querySelector('.scatter').textContent,/lower is better/);}finally{t.close();}
});
test('shared seeds and programs are deduplicated across runs when canonical hashes are available',async()=>{
  const one=clone(run),two=clone(run);two.id='second-model';two.model='model-b';one.metrics.canonical.valid_candidate_hashes=['c'.repeat(64),'d'.repeat(64)];two.metrics.canonical.valid_candidate_hashes=['c'.repeat(64),'e'.repeat(64)];
  const t=mount({rows:[one,two]});try{await flush();const card=t.doc.querySelectorAll('.result-metric')[2];assert.equal(card.querySelector('.result-metric-value').textContent,'3');assert.match(card.textContent,/Distinct valid programs/);assert.match(card.textContent,/Includes the seed/);assert.doesNotMatch(card.textContent,/then summed/);}finally{t.close();}
});
test('plots never mix cohort, task, metric or direction and do not rank methods across models',async()=>{
  const other=clone(run);other.id='other';other.framework='other-system';other.model='model-b';other.metrics.canonical.cohort='c'.repeat(64);
  const wrongTask=clone(run);wrongTask.id='different-task';wrongTask.metrics.canonical.task_id='other-task';
  const wrongDirection=clone(run);wrongDirection.id='different-direction';wrongDirection.metrics.canonical.direction='minimize';
  const same=clone(run);same.id='same';same.framework='other-system';same.model='model-c';
  const t=mount({rows:[run,other,wrongTask,wrongDirection,same]});try{await flush();t.change('results-framework','all');assert.equal(t.doc.getElementById('results-cohort').options.length,4);assert.equal(t.doc.querySelectorAll('.point').length,2);assert.match(t.doc.querySelector('.plot-key').textContent,/model-a/);assert.match(t.doc.querySelector('.plot-key').textContent,/model-c/);assert.doesNotMatch(t.doc.querySelector('.plot-key').textContent,/model-b/);assert.match(t.doc.getElementById('comparison-title').parentElement.textContent,/Budgets and search protocols can still differ/);assert.doesNotMatch(t.doc.querySelector('.plot-key').textContent,/winner|best method|frontier/i);}finally{t.close();}
});
test('partial tokens are visible in the matrix but excluded from token comparisons; measured wall time remains usable',async()=>{
  const partial=clone(run);partial.metrics.usage.complete=false;
  const t=mount({rows:[partial]});try{await flush();assert.match(t.doc.querySelector('tbody').textContent,/5,200 tokens/);assert.match(t.doc.querySelector('tbody').textContent,/Partial token coverage/);assert.equal(t.doc.querySelectorAll('.point').length,0);const time=t.doc.querySelector('[name="results-axis"][value="time"]');time.checked=true;time.dispatchEvent(new t.w.Event('change'));assert.equal(t.doc.querySelectorAll('.point').length,1);assert.match(t.doc.querySelector('.plot-key').textContent,/6.66667 min/);}finally{t.close();}
});
test('native scores appear with scope, metric and task when canonical evidence is absent, never as canonical points',async()=>{
  const native=clone(run);native.metrics.canonical=null;native.metrics.native={seed_score:1000,best_score:999,direction:'minimize',metric:'native_loss',scope:'native',task:'different task'};
  const t=mount({rows:[native]});try{await flush();assert.match(t.doc.querySelector('.run-evidence').textContent,/999 · native_loss/);assert.match(t.doc.querySelector('.run-evidence').textContent,/different task · native/);const cell=t.doc.querySelector('.score-pair').parentElement;assert.match(cell.textContent,/1,000→999Native/);assert.match(cell.textContent,/native_loss · lower is better/);assert.match(cell.textContent,/Gain over seed: 1/);assert.match(cell.textContent,/different task/);assert.equal(t.doc.querySelectorAll('.point').length,0);}finally{t.close();}
});
test('held-out native score is labeled with its definition and stored counts retain their scope',async()=>{
  const native=clone(run);native.metrics.canonical=null;native.metrics.native={best_score:4.2,metric:'validation_excess_percent',direction:'minimize',task:'online-bin-packing',scope:'native',score_kind:'Held-out validation of the native-selected program; not training best.',candidates:5,candidate_count_scope:'Distinct stored program IDs, not evaluator invocations.',iterations:2,iteration_count_scope:'Recorded native bandit rounds.',named_metrics:{validation_mean_bins:105,validation_lower_bound:100},evidence_hashes:['e'.repeat(64)]};
  const t=mount({rows:[native]});try{await flush();const cell=t.doc.querySelector('.score-pair').parentElement;assert.match(cell.textContent,/4.2Native/);assert.doesNotMatch(cell.textContent,/→/);assert.match(cell.textContent,/Held-out validation/);const details=t.doc.querySelector('.run-evidence');assert.match(details.textContent,/not evaluator invocations/);assert.match(details.textContent,/Recorded native bandit rounds/);assert.match(details.textContent,/Native · validation_mean_bins105/);assert.match(details.textContent,/Native · validation_lower_bound100/);assert.equal(t.doc.querySelectorAll('.point').length,0);}finally{t.close();}
});
test('native multiobjective populations preserve paired values without inventing a scalar best or ranking',async()=>{
  const native=clone(run);native.framework='meoh';native.metrics.canonical=null;native.metrics.native={best_score:null,seed_score:null,metric:'native_two_objective_population',task:'online-bin-packing',scope:'native',score_kind:'Paired final population objectives; no scalar best is defined.',objectives:[{metric:'negative_mean_bins',direction:'maximize'},{metric:'negative_mean_evaluation_seconds',direction:'maximize'}],population_objectives:[{negative_mean_bins:-100,negative_mean_evaluation_seconds:-.03},{negative_mean_bins:-105,negative_mean_evaluation_seconds:-.01}],population_size:2,iterations:1};
  const t=mount({rows:[native]});try{await flush();t.change('results-framework','all');const cell=t.doc.querySelector('.native-paired-title').parentElement;assert.match(cell.textContent,/2 objectivesNative/);assert.doesNotMatch(cell.textContent,/No canonical score/);const pairs=[...t.doc.querySelectorAll('.native-objective-pairs li')].map(node=>node.textContent);assert.equal(pairs.length,2);assert.equal(pairs[0],'negative_mean_bins: -100negative_mean_evaluation_seconds: -0.03');assert.equal(pairs[1],'negative_mean_bins: -105negative_mean_evaluation_seconds: -0.01');assert.match(t.doc.querySelector('.native-objectives').textContent,/source order/);assert.equal(t.doc.querySelectorAll('.point').length,0);}finally{t.close();}
});
test('untrusted labels, notes, metrics and issues render as text; only valid receipt hashes render',async()=>{
  const bad='<img src=x onerror=alert(1)>', malicious=clone(run);malicious.model=bad;malicious.label=bad;malicious.metrics.canonical.metric=bad;malicious.metrics.canonical.receipt_hashes=[bad,'b'.repeat(64)];malicious.metrics.evidence.issues=[bad];
  const t=mount({rows:[malicious],responseExtra:{notes:[bad]}});try{await flush();assert.equal(t.doc.querySelectorAll('img').length,0);assert.match(t.doc.querySelector('tbody').textContent,/<img/);assert.equal(t.doc.querySelector('.receipt-hashes').textContent,'b'.repeat(64));assert.equal(t.doc.getElementById('results-measurement-notes').textContent,bad);assert.equal(t.doc.getElementById('results-notices').textContent,'');assert.equal(t.doc.getElementById('results-methodology').open,false);}finally{t.close();}
});
test('truncation explicitly scopes totals and key entry uses session storage without key URLs',async()=>{
  const t=mount({initialKey:'',responseExtra:{truncated:true,total:500}});try{t.doc.getElementById('results-connect').click();assert.equal(t.doc.activeElement.id,'results-key');t.doc.getElementById('results-key').value='new-private-key';t.doc.getElementById('results-key-form').dispatchEvent(new t.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(t.stored.get('arena.queue.session-key'),'new-private-key');assert.equal(t.doc.getElementById('results-key').value,'');assert.match(t.doc.getElementById('results-notices').textContent,/1 of 500/);assert.ok(t.calls.every(call=>!call.path.includes('new-private-key')));}finally{t.close();}
});
test('disconnect clears private results and late network responses cannot repopulate them',async()=>{
  let resolve;
  const t=mount({fetcher:()=>new Promise(done=>{resolve=done;})});try{await flush();t.app.disconnect();resolve({ok:true,status:200,json:async()=>({schema:'arena.results/1',runs:[run]})});await flush();assert.equal(t.stored.size,0);assert.equal(t.doc.querySelectorAll('tbody tr').length,0);assert.equal(t.doc.querySelectorAll('.point').length,0);assert.match(t.doc.getElementById('results-status').textContent,/Disconnected/);const count=t.calls.length;await t.app.refresh();assert.equal(t.calls.length,count);}finally{t.close();}
});
test('authorization failure removes previously displayed private data',async()=>{
  const t=mount({fetcher:async(_path,_options,n)=>n===1?{ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})}:{ok:false,status:403}});try{await flush();assert.equal(t.doc.querySelectorAll('tbody tr').length,1);await t.app.refresh();assert.equal(t.doc.querySelectorAll('tbody tr').length,0);assert.match(t.doc.getElementById('results-status').textContent,/does not have access/);}finally{t.close();}
});
test('expanded provenance survives an evidence refresh',async()=>{
  const t=mount();try{await flush();t.doc.querySelector('details').open=true;await t.app.refresh();assert.equal(t.doc.querySelector('details').open,true);}finally{t.close();}
});
test('results is reachable from each existing page',()=>{
  for(const name of ['index.html','experiment.html','queue.html']) {
    const dom=new JSDOM(readFileSync(new URL(`../../web/${name}`,import.meta.url),'utf8'));
    try{assert.ok(dom.window.document.querySelector('nav[aria-label="Empira"] a[href="/results"]'),name);}finally{dom.window.close();}
  }
});
