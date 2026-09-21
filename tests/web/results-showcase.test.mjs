import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html = readFileSync(new URL('../../web/results.html',import.meta.url),'utf8').replace('data-results-showcase="true"','data-results-showcase="test"');
const source = readFileSync(new URL('../../web/arena-results-showcase.js',import.meta.url),'utf8').replace(/^export /gm,'');
const run = {
  id:'private-image-run', framework:'sciel-release', model:'model-a', state:'completed', created:100,
  metrics:{
    canonical:{status:'recorded',evaluations:3,valid:3,invalid:0,unknown:0,unique_valid_candidates:3,valid_candidate_hashes:['a'.repeat(64),'b'.repeat(64),'c'.repeat(64)],seed_score:1,best_score:1,metric:'score',direction:'maximize',task_id:'reference-sat',task_name:'Reference SAT',cohort:'d'.repeat(64)},
    usage:{total_tokens:5000,complete:true,requests:7,usd:0.001},
    budget:{evaluations:4,label:'Native search budget (B_evals)'},wall_seconds:300,evidence:{artifact_count:3,issues:[]}
  }
};
const clone = value => JSON.parse(JSON.stringify(value));
const flush = async () => {for(let i=0;i<5;i++) await new Promise(resolve=>setImmediate(resolve));};
function mount({runs=[run],initialKey='private-key',responseStatus=200,responseExtra={},fetcher:customFetcher,requestTimeoutMs=30000}={}) {
  const dom=new JSDOM(html,{url:'http://arena.test/results',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,doc=w.document,calls=[],stored=new Map(initialKey ? [['arena.queue.session-key',initialKey]] : []);
  const storage={getItem:key=>stored.get(key),setItem:(key,value)=>stored.set(key,value),removeItem:key=>stored.delete(key)};
  w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  const fetcher=async(path,options)=>{
    calls.push({path,options});
    if(customFetcher)return customFetcher(path,options,calls.length);
    return {ok:responseStatus===200,status:responseStatus,json:async()=>({schema:'arena.results/1',generated_at:1789958000,scope:'owner',runs,total:runs.length,truncated:false,...responseExtra})};
  };
  w.eval(`${source};window.mountShowcase=initResultsShowcase;`);
  const app=w.mountShowcase({doc,fetcher,storage,pollMs:0,requestTimeoutMs});
  return {doc,w,calls,stored,app,close(){app.destroy();w.close();}};
}


const rows = t => [...t.doc.querySelectorAll('#showcase-models > tr.showcase-model')];
const evidenceRow = row => row.nextElementSibling;
const evidenceFor = row => evidenceRow(row)?.querySelector('details.run-evidence');
const card = (t, label) => [...t.doc.querySelectorAll('.showcase-highlight')].find(n=>n.querySelector('.showcase-highlight-label')?.textContent === label);
const value = (t, label) => card(t,label)?.querySelector('.showcase-highlight-value')?.textContent;
function change(t,id,value,type='change') {const control=t.doc.getElementById(id);control.value=value;control.dispatchEvent(new t.w.Event(type,{bubbles:true}));}
const chartIds = t => [...t.doc.querySelectorAll('#showcase-efficiency .plot-point')].map(n=>n.dataset.runId);
const frontierIds = t => [...t.doc.querySelectorAll('#showcase-efficiency .plot-point.on-frontier')].map(n=>n.dataset.runId);
function assertLoadState(t,state,{busy=false,skeleton=false}={}) {
  assert.equal(t.doc.getElementById('main').dataset.loadState,state);
  assert.equal(t.doc.getElementById('main').getAttribute('aria-busy'),String(busy));
  const loading=t.doc.getElementById('showcase-loading');
  assert.ok(loading,'loading placeholders exist separately from measured values');
  assert.equal(loading.hidden,!skeleton);
  assert.equal(loading.getAttribute('aria-hidden'),'true','decorative skeletons do not announce fake measurements');
}

test('research dashboard retains the discovery navigation and research link without promotional hero or Queue',()=>{
  const dom=new JSDOM(html);try{
    const doc=dom.window.document;
    assert.ok(doc.querySelector('.arena-masthead .arena-brand'));
    assert.deepEqual([...doc.querySelectorAll('.arena-tabs>a')].map(link=>link.getAttribute('href')),['/','/?view=participants','/experiments','/results']);
    assert.equal(doc.querySelector('.arena-tabs [aria-current="page"]').textContent,'Results');
    assert.equal(doc.querySelectorAll('a[href="/queue"], a[href="/experiments/queue"], .sidebar').length,0);
    assert.equal(doc.querySelector('h1').textContent,'Results');
    assert.doesNotMatch(doc.querySelector('main').textContent,/SCiEL in the arena|The programs it produces|The resources it takes|RESULTS · SCIEL/i);
    assert.match(doc.querySelector('.showcase-next').textContent,/Follow the research behind the numbers\./);
    assert.ok(doc.querySelector('a[href="/experiments/results"]'));
    assert.ok(doc.querySelector('table #showcase-models'));
    for(const id of ['framework','model','state','search','sort','cohort','axis','budget']) assert.ok(doc.getElementById(`showcase-${id}`));
  }finally{dom.window.close();}
});
test('without a key the connection state has no request, skeleton or dummy metric cards',async()=>{
  const t=mount({initialKey:''});try{
    await flush();
    assert.equal(t.calls.length,0);
    assertLoadState(t,'disconnected');
    assert.equal(t.doc.getElementById('showcase-content').hidden,true);
    assert.equal(t.doc.querySelectorAll('.showcase-highlight-value').length,0);
    for(const selector of ['#showcase-highlights','#showcase-basis','.showcase-toolbar']) assert.equal(t.doc.querySelector(selector).hidden,true);
    assert.equal(t.doc.getElementById('showcase-empty').hidden,false);
    assert.equal(t.doc.getElementById('showcase-empty-connect').hidden,false);
    assert.equal(t.doc.getElementById('showcase-empty-retry').hidden,true);
    assert.match(t.doc.querySelector('#showcase-empty h2').textContent,/connect/i);
  }finally{t.close();}
});
test('an initial read shows decorative skeletons until real results arrive without flashing the connection or unknown-metric state',async()=>{
  let resolve;
  const t=mount({fetcher:()=>new Promise(done=>{resolve=done;})});try{
    await flush();
    assertLoadState(t,'loading',{busy:true,skeleton:true});
    assert.equal(t.calls.length,1);
    assert.equal(t.doc.getElementById('showcase-empty').hidden,true);
    assert.equal(t.doc.getElementById('showcase-content').hidden,true);
    assert.equal(t.doc.querySelectorAll('.showcase-highlight-value').length,0);
    for(const selector of ['#showcase-highlights','#showcase-basis','.showcase-toolbar']) assert.equal(t.doc.querySelector(selector).hidden,true);
    assert.match(t.doc.getElementById('showcase-status').textContent,/loading/i);
    resolve({ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})});
    await flush();
    assertLoadState(t,'ready');
    assert.equal(t.doc.getElementById('showcase-empty').hidden,true);
    assert.equal(t.doc.getElementById('showcase-content').hidden,false);
    for(const selector of ['#showcase-highlights','#showcase-basis','.showcase-toolbar']) assert.equal(t.doc.querySelector(selector).hidden,false);
    assert.equal(value(t,'Runs'),'1');
    assert.equal(rows(t).length,1);
  }finally{t.close();}
});
test('loading continues after response headers until the result body is available',async()=>{
  let resolveBody;
  const t=mount({fetcher:async()=>({ok:true,json:()=>new Promise(done=>{resolveBody=done;})})});try{
    await flush();
    assertLoadState(t,'loading',{busy:true,skeleton:true});
    assert.equal(t.doc.getElementById('showcase-empty').hidden,true);
    assert.equal(t.doc.querySelectorAll('.showcase-highlight-value').length,0);
    resolveBody({schema:'arena.results/1',runs:[run]});
    await flush();
    assertLoadState(t,'ready');
    assert.equal(value(t,'Runs'),'1');
  }finally{t.close();}
});
test('a background refresh retains measured cards and charts, and a failed refresh offers retry while disclosing stale results',async()=>{
  let rejectRefresh;
  const updated=clone(run);updated.metrics.usage.total_tokens=6500;
  const t=mount({fetcher:async(_path,_options,n)=>{
    if(n===2)return new Promise((_resolve,reject)=>{rejectRefresh=reject;});
    return {ok:true,json:async()=>({schema:'arena.results/1',runs:[n===1?run:updated]})};
  }});try{
    await flush();
    const refresh=t.app.refresh();
    await flush();
    assertLoadState(t,'refreshing',{busy:true});
    assert.equal(value(t,'Median recorded tokens'),'5,000');
    assert.deepEqual(chartIds(t),[run.id]);
    assert.equal(t.doc.getElementById('showcase-content').hidden,false);
    assert.equal(t.doc.getElementById('showcase-empty').hidden,true);
    rejectRefresh(new Error('temporary network outage'));
    await refresh;
    assertLoadState(t,'error');
    assert.equal(value(t,'Median recorded tokens'),'5,000');
    assert.equal(rows(t).length,1);
    assert.deepEqual(chartIds(t),[run.id]);
    assert.equal(t.doc.getElementById('showcase-content').hidden,false);
    assert.equal(t.doc.getElementById('showcase-empty').hidden,true);
    assert.match(t.doc.getElementById('showcase-status').textContent,/previous|last|stale|retained/i);
    assert.equal(t.doc.getElementById('showcase-refresh').disabled,false);
    t.doc.getElementById('showcase-refresh').click();
    await flush();
    assertLoadState(t,'ready');
    assert.equal(value(t,'Median recorded tokens'),'6,500');
    assert.equal(t.calls.length,3);
  }finally{t.close();}
});
test('an initial read failure replaces skeletons with an explicit retry that recovers without asking for another key',async()=>{
  let resolveRetry;
  const t=mount({fetcher:async(_path,_options,n)=>{
    if(n===1)throw new Error('network unavailable');
    return new Promise(done=>{resolveRetry=done;});
  }});try{
    await flush();
    assertLoadState(t,'error');
    assert.equal(t.doc.getElementById('showcase-content').hidden,true);
    assert.equal(t.doc.querySelectorAll('.showcase-highlight-value').length,0);
    assert.equal(t.doc.getElementById('showcase-empty').hidden,false);
    assert.match(t.doc.querySelector('#showcase-empty h2').textContent,/could not load results/i);
    assert.equal(t.doc.getElementById('showcase-empty-connect').hidden,true);
    const retry=t.doc.getElementById('showcase-empty-retry');
    assert.equal(retry.hidden,false);
    assert.equal(retry.disabled,false);
    retry.click();
    await flush();
    assertLoadState(t,'loading',{busy:true,skeleton:true});
    assert.equal(t.doc.getElementById('showcase-empty').hidden,true);
    assert.equal(t.calls.length,2);
    assert.equal(t.calls[1].options.headers.Authorization,'Bearer private-key');
    resolveRetry({ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})});
    await flush();
    assertLoadState(t,'ready');
    assert.equal(rows(t).length,1);
    assert.equal(retry.hidden,true);
    assert.equal(t.doc.getElementById('showcase-key-dialog').open,false);
  }finally{t.close();}
});
test('a successful empty response shows recorded-run absence rather than loading, connection prompts or dummy metric cards',async()=>{
  const t=mount({runs:[]});try{
    await flush();
    assertLoadState(t,'empty');
    assert.equal(t.calls.length,1);
    assert.equal(t.doc.getElementById('showcase-empty').hidden,false);
    assert.match(t.doc.querySelector('#showcase-empty h2').textContent,/no recorded runs/i);
    assert.equal(t.doc.getElementById('showcase-empty-connect').hidden,true);
    assert.equal(t.doc.getElementById('showcase-empty-retry').hidden,true);
    assert.equal(t.doc.getElementById('showcase-content').hidden,true);
    assert.equal(t.doc.getElementById('showcase-highlights').hidden,true);
    assert.equal(t.doc.querySelector('.showcase-toolbar').hidden,false);
    assert.equal(rows(t).length,0);
  }finally{t.close();}
});
test('session key performs only a read of the scoped same-origin endpoint',async()=>{
  const t=mount();try{await flush();assert.equal(t.calls.length,1);const call=t.calls[0];assert.equal(call.path,'/api/control/results');assert.equal(call.options.method,undefined);assert.equal(call.options.headers.Authorization,'Bearer private-key');assert.equal(call.options.redirect,'error');assert.equal(call.options.cache,'no-store');assert.equal(call.options.credentials,'same-origin');assert.equal(rows(t).length,1);assert.equal(t.doc.querySelectorAll('details.run-evidence').length,1);}finally{t.close();}
});
test('SCiEL is the initial filter, but the dashboard exposes all systems without dropping native evidence',async()=>{
  const other=clone(run);other.id='other';other.framework='openevolve';other.metrics.canonical={status:'missing'};other.metrics.native={scope:'native',best_score:.9,metric:'target_ratio',direction:'maximize',task:'circle-packing'};
  const t=mount({runs:[run,other]});try{await flush();assert.equal(t.doc.getElementById('showcase-framework').value,'sciel-release');assert.equal(rows(t).length,1);assert.ok([...t.doc.getElementById('showcase-framework').options].some(n=>n.value==='openevolve'));change(t,'showcase-framework','all');assert.equal(rows(t).length,2);assert.match(t.doc.querySelector('tr[data-run-id="other"]').textContent,/Native/i);assert.equal(t.doc.querySelector('#showcase-sort option[value="score"]').disabled,true);assert.ok(!chartIds(t).includes('other'));}finally{t.close();}
});
test('overview deduplicates source hashes across models and reports completed runs separately from valid evidence',async()=>{
  const second=clone(run);second.id='run-two';second.model='model-b';second.metrics.canonical.valid_candidate_hashes=['a'.repeat(64),'e'.repeat(64)];
  const native=clone(run);native.id='native';native.framework='sciel';const another=clone(run);another.id='another';another.framework='openevolve';
  const t=mount({runs:[run,second,native,another]});try{await flush();assert.equal(value(t,'Runs'),'2');assert.equal(value(t,'Models with valid evidence'),'2 / 2');assert.equal(value(t,'Distinct valid programs'),'4');assert.equal(value(t,'Candidate validity'),'100%');assert.equal(value(t,'Median recorded tokens'),'5,000');assert.equal(value(t,'Completed runs'),'2 / 2');assert.match(card(t,'Distinct valid programs').textContent,/seed/);}finally{t.close();}
});
test('seed ties remain explicit, and native search limits are separate from requests and billing',async()=>{
  const t=mount();try{await flush();assert.match(rows(t)[0].querySelector('.showcase-score-pair').textContent,/1\s*→\s*1/);assert.match(t.doc.getElementById('showcase-seed-note').textContent,/match|tie/i);assert.doesNotMatch(t.doc.getElementById('showcase-seed-note').textContent,/1 run improved/);assert.match(evidenceFor(rows(t)[0]).textContent,/B_evals/);assert.match(evidenceFor(rows(t)[0]).textContent,/4/);assert.doesNotMatch(t.doc.getElementById('main').textContent,/\$0|cheapest|best system|optimal solution achieved|perfect/i);}finally{t.close();}
});
test('failed processes retain evidence while partial tokens stay out of complete-ledger median and frontier',async()=>{
  const partial=clone(run);partial.id='partial';partial.model='model-b';partial.state='failed';partial.metrics.usage={total_tokens:2000,complete:false};
  const t=mount({runs:[run,partial]});try{await flush();assert.equal(rows(t).length,2);assert.match(t.doc.querySelector('tr[data-run-id="partial"]').textContent,/Failed/i);assert.equal(t.doc.querySelectorAll('#showcase-tokens .measure-row.is-partial').length,1);assert.equal(value(t,'Median recorded tokens'),'5,000');assert.equal(value(t,'Completed runs'),'1 / 2');assert.ok(!frontierIds(t).includes('partial'));}finally{t.close();}
});
test('partial canonical evidence remains visible and excluded from the complete-evidence frontier',async()=>{
  const partial=clone(run);partial.id='partial-canon';partial.metrics.canonical={...partial.metrics.canonical,status:'partial',evaluations:1,valid:1,invalid:0,unknown:0,valid_candidate_hashes:['a'.repeat(64)],best_score:.75,seed_score:null};partial.metrics.evidence={issues:['Private rejected artifact diagnostic']};
  const t=mount({runs:[partial]});try{await flush();const row=rows(t)[0];assert.match(row.textContent,/completed/i);assert.match(row.textContent,/partial/i);assert.match(row.querySelector('.showcase-score-pair').textContent,/—\s*→\s*0\.75/);assert.equal(value(t,'Candidate validity'),'100%');assert.ok(!frontierIds(t).includes('partial-canon'));assert.match(t.doc.getElementById('showcase-coverage-note').textContent,/partial/i);assert.doesNotMatch(t.doc.getElementById('main').textContent,/Private rejected artifact diagnostic/);}finally{t.close();}
});
test('missing canonical values are not replaced by native scores, and missing tokens are never zero',async()=>{
  const missing=clone(run);missing.metrics.canonical={...missing.metrics.canonical,status:'missing',evaluations:0,valid:0,invalid:0,valid_candidate_hashes:undefined,seed_score:null,best_score:null};missing.metrics.usage={total_tokens:null,complete:false};missing.metrics.budget={};missing.metrics.native={best_score:999,metric:'native_score',scope:'native',direction:'maximize'};
  const t=mount({runs:[missing]});try{await flush();assert.equal(t.doc.querySelectorAll('#showcase-tokens .measure-segment').length,0);assert.equal(value(t,'Median recorded tokens'),'—');assert.equal(value(t,'Candidate validity'),'—');assert.equal(value(t,'Distinct valid programs'),'—');assert.equal(chartIds(t).length,0);assert.doesNotMatch(t.doc.getElementById('showcase-progress').textContent,/999/);assert.match(rows(t)[0].textContent,/Native/i);assert.equal(t.doc.querySelector('#showcase-sort option[value="score"]').disabled,true);}finally{t.close();}
});
test('real zero scores and tokens remain measurements, with the correct direction for minimization gains',async()=>{
  const zero=clone(run);zero.metrics.canonical.seed_score=2;zero.metrics.canonical.best_score=0;zero.metrics.canonical.direction='minimize';zero.metrics.usage.total_tokens=0;
  const t=mount({runs:[zero]});try{await flush();assert.match(rows(t)[0].querySelector('.showcase-score-pair').textContent,/2\s*→\s*0/);assert.match(t.doc.getElementById('showcase-seed-note').textContent,/1 (?:run )?improved/);assert.equal(value(t,'Median recorded tokens'),'0');assert.equal(t.doc.querySelector('#showcase-tokens .measure-segment').style.width,'0%');assert.deepEqual(chartIds(t),[zero.id]);assert.ok(!t.doc.getElementById('showcase-efficiency').innerHTML.includes('NaN'));}finally{t.close();}
});
test('task, metric, direction and evaluator identities isolate plots without hiding the other table rows',async()=>{
  const changed=['task_id','metric','direction','cohort'].map((field,index)=>{const item=clone(run);item.id=`other-${index}`;item.model=`other-${index}`;item.metrics.canonical[field]=field==='direction'?'minimize':field==='cohort'?'f'.repeat(64):'different';return item;});
  const t=mount({runs:[run,...changed]});try{await flush();const select=t.doc.getElementById('showcase-cohort');assert.equal(select.options.length,5);assert.equal(rows(t).length,5);assert.equal(chartIds(t).length,1);assert.equal(t.doc.getElementById('showcase-cohort-label').hidden,false);assert.equal(t.doc.querySelector('#showcase-sort option[value="score"]').disabled,true);const initial=chartIds(t)[0];change(t,'showcase-cohort',select.options[1].value);assert.equal(rows(t).length,5);assert.equal(chartIds(t).length,1);assert.notEqual(chartIds(t)[0],initial);assert.equal(value(t,'Runs'),'5');}finally{t.close();}
});
test('unknown receipts stay separate from validity denominator and partial hash coverage is stated',async()=>{
  const unknown=clone(run);unknown.id='unknown';unknown.metrics.canonical={...unknown.metrics.canonical,evaluations:4,valid:2,invalid:1,unknown:1,valid_candidate_hashes:undefined};
  const t=mount({runs:[run,unknown]});try{await flush();assert.equal(value(t,'Candidate validity'),'83.3%');assert.match(card(t,'Candidate validity').textContent,/5\s*\/\s*6/);assert.match(t.doc.getElementById('showcase-validity').textContent,/1/);assert.match(t.doc.getElementById('showcase-validity').textContent,/unknown|unclassified/i);assert.match(card(t,'Distinct valid programs').textContent,/partial/i);}finally{t.close();}
});
test('model, process state, search and budget filters constrain all run-derived summaries',async()=>{
  const second=clone(run);second.id='attention-run';second.model='model-b';second.state='failed';second.metrics.budget.evaluations=8;
  const active=clone(run);active.id='active-run';active.model='model-c';active.state='running';
  const t=mount({runs:[run,second,active]});try{await flush();change(t,'showcase-model','model-b');assert.deepEqual(rows(t).map(n=>n.dataset.runId),['attention-run']);assert.equal(value(t,'Runs'),'1');change(t,'showcase-model','all');change(t,'showcase-state','active');assert.deepEqual(rows(t).map(n=>n.dataset.runId),['active-run']);change(t,'showcase-state','attention');assert.deepEqual(rows(t).map(n=>n.dataset.runId),['attention-run']);change(t,'showcase-state','all');change(t,'showcase-search','private-image','input');assert.deepEqual(rows(t).map(n=>n.dataset.runId),[run.id]);change(t,'showcase-search','','input');const budget=t.doc.getElementById('showcase-budget');const option=[...budget.options].find(n=>n.value!=='all'&&/8/.test(n.textContent));assert.ok(option);change(t,'showcase-budget',option.value);assert.deepEqual(rows(t).map(n=>n.dataset.runId),['attention-run']);assert.equal(value(t,'Runs'),'1');assert.equal(t.calls.length,1);}finally{t.close();}
});
test('a filter with no matching rows has a useful empty state and can recover without another fetch',async()=>{
  const t=mount();try{await flush();change(t,'showcase-search','no-such-research-run','input');assertLoadState(t,'empty');assert.equal(rows(t).length,0);assert.equal(t.doc.getElementById('showcase-content').hidden,true);assert.equal(t.doc.getElementById('showcase-highlights').hidden,true);assert.equal(t.doc.querySelector('.showcase-toolbar').hidden,false);assert.match(t.doc.getElementById('showcase-empty-copy').textContent,/filter|match/i);assert.doesNotMatch(t.doc.querySelector('#showcase-empty h2').textContent,/connect/i);assert.equal(t.doc.getElementById('showcase-empty-connect').hidden,true);assert.equal(t.doc.getElementById('showcase-empty-retry').hidden,true);change(t,'showcase-search','','input');assertLoadState(t,'ready');assert.equal(rows(t).length,1);assert.equal(t.doc.getElementById('showcase-content').hidden,false);assert.equal(t.calls.length,1);}finally{t.close();}
});
test('run table pagination exposes every record while overview totals cover all matching records',async()=>{
  const runs=Array.from({length:25},(_,i)=>{const r=clone(run);r.id=`run-${String(i).padStart(2,'0')}`;r.model=`model-${String(i).padStart(2,'0')}`;return r;});
  const t=mount({runs});try{await flush();assert.equal(rows(t).length,20);assert.equal(value(t,'Runs'),'25');assert.equal(t.doc.getElementById('showcase-page-prev').disabled,true);assert.equal(t.doc.getElementById('showcase-page-next').disabled,false);const firstIds=rows(t).map(n=>n.dataset.runId);t.doc.getElementById('showcase-page-next').click();assert.equal(rows(t).length,5);assert.equal(t.doc.getElementById('showcase-page-next').disabled,true);assert.equal(new Set([...firstIds,...rows(t).map(n=>n.dataset.runId)]).size,25);assert.equal(value(t,'Runs'),'25');change(t,'showcase-search','run-00','input');assert.equal(rows(t).length,1);assert.equal(t.doc.getElementById('showcase-page-prev').disabled,true);}finally{t.close();}
});
test('score sorting respects minimization and resource sorting places unknown values last',async()=>{
  const runs=[3,0,2].map((score,i)=>{const r=clone(run);r.id=`run-${i}`;r.model=`model-${i}`;r.metrics.canonical.direction='minimize';r.metrics.canonical.best_score=score;r.metrics.usage.total_tokens=[300,null,0][i];return r;});
  const t=mount({runs});try{await flush();assert.equal(t.doc.querySelector('#showcase-sort option[value="score"]').disabled,false);change(t,'showcase-sort','score');assert.deepEqual(rows(t).map(n=>n.dataset.runId),['run-1','run-2','run-0']);change(t,'showcase-sort','tokens');assert.deepEqual(rows(t).map(n=>n.dataset.runId),['run-2','run-0','run-1']);}finally{t.close();}
});
test('frontier uses only complete canonical evidence with complete resources and terminal processes',async()=>{
  const make=(id,score,tokens)=>{const r=clone(run);r.id=id;r.model=id;r.metrics.canonical.best_score=score;r.metrics.usage.total_tokens=tokens;return r;};
  const low=make('efficient',1,100),dominated=make('dominated',.5,200),high=make('high-score',2,300),partial=make('partial',3,20),running=make('running',4,10),partialCanon=make('partial-canon',5,5);
  partial.metrics.usage.complete=false;running.state='running';partialCanon.metrics.canonical.status='partial';
  const t=mount({runs:[low,dominated,high,partial,running,partialCanon]});try{await flush();assert.deepEqual(frontierIds(t).sort(),['efficient','high-score']);assert.ok(!chartIds(t).includes('partial'));assert.match(t.doc.querySelector('tr[data-run-id="partial"]').textContent,/partial ledger/i);assert.ok(chartIds(t).includes('partial-canon'));assert.doesNotMatch(t.doc.getElementById('showcase-efficiency-note').textContent,/winner|best system|cheapest/i);assert.match(t.doc.getElementById('showcase-efficiency-note').textContent,/frontier|non.dominated/i);}finally{t.close();}
});
test('changing the resource axis redraws coordinates without fetching or mixing incomparable cohorts',async()=>{
  const second=clone(run);second.id='second';second.model='model-b';second.metrics.usage.total_tokens=6000;second.metrics.wall_seconds=10;
  const t=mount({runs:[run,second]});try{await flush();const before=t.doc.querySelector('#showcase-efficiency [data-run-id="second"]').getAttribute('cx');change(t,'showcase-axis','time');const after=t.doc.querySelector('#showcase-efficiency [data-run-id="second"]').getAttribute('cx');assert.notEqual(before,after);assert.match(t.doc.getElementById('showcase-efficiency').textContent,/time|second|minute/i);assert.equal(t.calls.length,1);}finally{t.close();}
});
test('new key submission stores only a session key and never uses it in a URL',async()=>{
  const t=mount({initialKey:''});try{t.doc.getElementById('showcase-connect').click();assert.equal(t.doc.activeElement.id,'showcase-key');t.doc.getElementById('showcase-key').value='new-secret';t.doc.getElementById('showcase-key-form').dispatchEvent(new t.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(t.stored.get('arena.queue.session-key'),'new-secret');assert.equal(t.doc.getElementById('showcase-key').value,'');assert.equal(t.doc.getElementById('showcase-key-dialog').open,false);assert.ok(t.calls.every(call=>!call.path.includes('new-secret')));}finally{t.close();}
});
test('authorization errors remove prior private content, chart data and invalid keys',async()=>{
  const t=mount({fetcher:async(_path,_options,n)=>n===1?{ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})}:{ok:false,status:403}});try{await flush();assert.equal(rows(t).length,1);await t.app.refresh();assertLoadState(t,'disconnected');assert.equal(rows(t).length,0);assert.equal(chartIds(t).length,0);assert.equal(t.doc.querySelectorAll('.showcase-highlight-value').length,0);assert.equal(t.stored.size,0);assert.match(t.doc.getElementById('showcase-status').textContent,/does not have access/);assert.equal(t.doc.getElementById('showcase-content').hidden,true);assert.equal(t.doc.getElementById('showcase-empty-connect').hidden,false);assert.equal(t.doc.getElementById('showcase-empty-retry').hidden,true);}finally{t.close();}
});
test('disconnect clears evidence and a late response cannot restore it',async()=>{
  let resolve;const t=mount({fetcher:()=>new Promise(done=>{resolve=done;})});try{await flush();assertLoadState(t,'loading',{busy:true,skeleton:true});t.app.disconnect();assertLoadState(t,'disconnected');resolve({ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})});await flush();assertLoadState(t,'disconnected');assert.equal(t.stored.size,0);assert.equal(rows(t).length,0);assert.equal(t.doc.querySelectorAll('.showcase-highlight-value').length,0);assert.match(t.doc.getElementById('showcase-status').textContent,/Disconnected/);await t.app.refresh();assert.equal(t.calls.length,1);}finally{t.close();}
});
test('untrusted model, task and run labels render as text, never HTML or executable links',async()=>{
  const bad=clone(run);bad.id='javascript:alert(1)';bad.model='<img src=x onerror=alert(1)>';bad.metrics.canonical.task_name='<script>alert(1)</script>';
  const t=mount({runs:[bad]});try{await flush();assert.equal(t.doc.querySelectorAll('#main img:not([src^="/brand/"]), #main script, #main a[href^="javascript:"]').length,0);assert.match(t.doc.getElementById('showcase-models').textContent,/<img/);assert.match(t.doc.getElementById('main').textContent,/<script/);assert.equal(t.doc.querySelectorAll('#showcase-efficiency foreignObject').length,0);}finally{t.close();}
});
test('a stalled fetch times out, aborts and allows an explicit read-only retry',async()=>{
  const t=mount({requestTimeoutMs:10,fetcher:async(_path,_options,n)=>n===1?new Promise(()=>{}):{ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})}});
  try{assertLoadState(t,'loading',{busy:true,skeleton:true});await new Promise(resolve=>setTimeout(resolve,25));await flush();assertLoadState(t,'error');assert.match(t.doc.getElementById('showcase-status').textContent,/timed out/);assert.equal(t.calls[0].options.signal.aborted,true);assert.equal(t.doc.getElementById('showcase-refresh').disabled,false);assert.equal(t.doc.getElementById('showcase-empty-retry').hidden,false);assert.equal(t.doc.getElementById('showcase-empty-retry').disabled,false);t.doc.getElementById('showcase-empty-retry').click();await flush();assertLoadState(t,'ready');assert.equal(rows(t).length,1);assert.equal(t.calls.length,2);assert.ok(t.calls.every(call=>call.options.method===undefined&&call.path==='/api/control/results'));}finally{t.close();}
});
test('a stalled response body also times out without leaving Refresh disabled',async()=>{
  const t=mount({requestTimeoutMs:10,fetcher:async()=>({ok:true,json:()=>new Promise(()=>{})})});
  try{assertLoadState(t,'loading',{busy:true,skeleton:true});await new Promise(resolve=>setTimeout(resolve,25));await flush();assertLoadState(t,'error');assert.match(t.doc.getElementById('showcase-status').textContent,/timed out/);assert.equal(t.doc.getElementById('showcase-refresh').disabled,false);assert.equal(t.doc.getElementById('showcase-empty-retry').hidden,false);assert.equal(t.doc.getElementById('showcase-empty-retry').disabled,false);}finally{t.close();}
});
test('truncated results disclose loaded scope and an absent SCiEL cohort never substitutes another system',async()=>{
  const t=mount({responseExtra:{truncated:true,total:600}});try{await flush();assert.match(t.doc.getElementById('showcase-basis').textContent,/1.*600|600.*1/);assert.match(t.doc.getElementById('showcase-basis').textContent,/loaded|sample/i);}finally{t.close();}
  const other=clone(run);other.framework='other-framework';const empty=mount({runs:[other]});try{await flush();assert.equal(empty.doc.getElementById('showcase-content').hidden,true);assert.equal(rows(empty).length,0);assert.equal(empty.doc.getElementById('showcase-framework').value,'sciel-release');change(empty,'showcase-framework','all');assert.equal(rows(empty).length,1);}finally{empty.close();}
});

test('negative scores and equal resource values produce accessible finite chart coordinates',async()=>{
  const second=clone(run);second.id='negative';second.metrics.canonical.seed_score=-3;second.metrics.canonical.best_score=-1;second.metrics.usage.total_tokens=5000;
  const t=mount({runs:[run,second]});try{await flush();for(const id of ['showcase-efficiency','showcase-progress']) {const plot=t.doc.getElementById(id);assert.ok(plot.querySelector('svg'));assert.ok(plot.querySelector('svg[role="img"]'));assert.doesNotMatch(plot.innerHTML,/NaN|Infinity/);for(const node of plot.querySelectorAll('[cx], [cy], [x1], [x2], [y1], [y2]')) for(const attribute of ['cx','cy','x1','x2','y1','y2']) if(node.hasAttribute(attribute)) assert.ok(Number.isFinite(Number(node.getAttribute(attribute))),`${id}: ${attribute}`);}}finally{t.close();}
});
test('destroy aborts an in-flight read and prevents private evidence from appearing after page teardown',async()=>{
  let resolve;const t=mount({fetcher:()=>new Promise(done=>{resolve=done;})});try{await flush();t.app.destroy();assert.equal(t.calls[0].options.signal.aborted,true);resolve({ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})});await flush();assert.equal(rows(t).length,0);assert.equal(chartIds(t).length,0);}finally{t.close();}
});

test('disconnect removes private system, model and budget identities from filter options as well as data panels',async()=>{
  const privateRun=clone(run);privateRun.framework='private-internal-system';privateRun.model='secret-internal-model';privateRun.metrics.budget.label='Secret budget policy';
  const t=mount({runs:[run,privateRun]});try{await flush();assert.match(t.doc.getElementById('showcase-model').textContent,/secret-internal-model/);t.app.disconnect();for(const id of ['showcase-framework','showcase-model','showcase-budget']) assert.doesNotMatch(t.doc.getElementById(id).textContent,/private-internal-system|secret-internal-model|Secret budget policy/);assert.equal(rows(t).length,0);}finally{t.close();}
});
test('multi-objective native results preserve candidate pairs and never manufacture a scalar best or canonical rank',async()=>{
  const paired=clone(run);paired.id='paired';paired.framework='meoh';paired.metrics.canonical={status:'missing',evaluations:0};paired.metrics.native={scope:'native',status:'recorded',metric:'native_two_objective_population',task:'online-bin-packing',best_score:null,seed_score:null,objectives:[{metric:'negative_mean_bins',direction:'maximize'},{metric:'negative_mean_evaluation_seconds',direction:'maximize'}],population_objectives:[{negative_mean_bins:-8.5,negative_mean_evaluation_seconds:-.03},{negative_mean_bins:-9,negative_mean_evaluation_seconds:-.01}],score_kind:'Paired final population objectives; no scalar best is defined.'};
  const t=mount({runs:[paired]});try{await flush();change(t,'showcase-framework','all');const row=rows(t)[0];assert.match(row.querySelector('.score-scope').textContent,/Native/);assert.match(row.querySelector('.showcase-score-pair').textContent,/—\s*→\s*—/);const pairs=[...evidenceFor(row).querySelectorAll('.native-objectives tbody tr')].map(n=>[...n.querySelectorAll('td')].map(c=>c.textContent));assert.deepEqual(pairs,[['1','-8.5','-0.03'],['2','-9','-0.01']]);assert.equal(chartIds(t).length,0);assert.equal(t.doc.querySelector('#showcase-sort option[value="score"]').disabled,true);assert.match(t.doc.getElementById('showcase-coverage').textContent,/1 \/ 1/);}finally{t.close();}
});

test('plot observations can open an individual run even when its row is on a later table page',async()=>{
  const runs=Array.from({length:22},(_,i)=>{const r=clone(run);r.id=`run-${String(i).padStart(2,'0')}`;r.model=`model-${String(i).padStart(2,'0')}`;return r;});
  const t=mount({runs});try{await flush();assert.equal(rows(t).some(n=>n.dataset.runId==='run-21'),false);const point=t.doc.querySelector('#showcase-efficiency [data-run-id="run-21"]');assert.ok(point);point.dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));const row=t.doc.querySelector('#showcase-models tr[data-run-id="run-21"]');assert.ok(row);assert.equal(evidenceFor(row).open,true);assert.equal(evidenceRow(row).hidden,false);assert.equal(t.doc.activeElement,evidenceFor(row).querySelector('summary'));assert.equal(row.querySelector('button.inspect-run').getAttribute('aria-expanded'),'true');point.dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));const reopened=t.doc.querySelector('#showcase-models tr[data-run-id="run-21"]');assert.equal(evidenceFor(reopened).open,true);assert.equal(evidenceRow(reopened).hidden,false);assert.equal(t.doc.activeElement,evidenceFor(reopened).querySelector('summary'));assert.equal(t.calls.length,1);}finally{t.close();}
});
test('partial native measurements are marked in the row before opening evidence details',async()=>{
  const partial=clone(run);partial.framework='native-system';partial.metrics.canonical={status:'missing',evaluations:0};partial.metrics.native={scope:'native',status:'partial',best_score:.9,metric:'target_ratio',direction:'maximize',task:'circle-packing'};
  const t=mount({runs:[partial]});try{await flush();change(t,'showcase-framework','all');const row=rows(t)[0];assert.match(row.textContent,/partial native|native.*partial/i);assert.equal(chartIds(t).length,0);}finally{t.close();}
});

test('Inspect expands into a full-width row, preserves all comparison columns and collapses without hiding the run',async()=>{
  const second=clone(run);second.id='second';second.model='model-b';
  const t=mount({runs:[run,second]});try{await flush();let row=rows(t)[0],detailRow=evidenceRow(row),button=row.querySelector('button.inspect-run');assert.equal(row.cells.length,7);assert.ok(detailRow.matches('tr.showcase-detail-row'));assert.equal(detailRow.cells.length,1);assert.equal(detailRow.cells[0].colSpan,7);assert.equal(detailRow.hidden,true);assert.equal(button.getAttribute('aria-expanded'),'false');assert.equal(t.doc.getElementById(button.getAttribute('aria-controls')),detailRow);button.click();assert.equal(detailRow.hidden,false);assert.equal(evidenceFor(row).open,true);assert.equal(button.getAttribute('aria-expanded'),'true');assert.equal(rows(t).length,2);change(t,'showcase-sort','created');row=rows(t).find(n=>n.dataset.runId===run.id);detailRow=evidenceRow(row);button=row.querySelector('button.inspect-run');assert.equal(detailRow.hidden,false);assert.equal(evidenceFor(row).open,true);assert.equal(button.getAttribute('aria-expanded'),'true');button.click();assert.equal(detailRow.hidden,true);assert.equal(evidenceFor(row).open,false);assert.equal(button.getAttribute('aria-expanded'),'false');assert.equal(row.hidden,false);assert.equal(rows(t).length,2);assert.equal(row.cells.length,7);}finally{t.close();}
});
