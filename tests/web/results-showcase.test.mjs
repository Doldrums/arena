import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html = readFileSync(new URL('../../web/results.html',import.meta.url),'utf8').replace('data-results-showcase="true"','data-results-showcase="test"');
const source = readFileSync(new URL('../../web/arena-results-showcase.js',import.meta.url),'utf8').replace(/^export /gm,'');
const run = {
  id:'private-image-run', framework:'sciel-release', model:'model-a', state:'completed', created:100,
  metrics:{
    canonical:{evaluations:3,valid:3,invalid:0,unknown:0,unique_valid_candidates:3,valid_candidate_hashes:['a'.repeat(64),'b'.repeat(64),'c'.repeat(64)],seed_score:1,best_score:1,metric:'score',direction:'maximize',task_id:'reference-sat',task_name:'Reference SAT',cohort:'d'.repeat(64)},
    usage:{total_tokens:5000,complete:true,requests:7,usd:0.001},
    budget:{evaluations:4,label:'Native search budget (B_evals)'},wall_seconds:300
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

test('landing retains the shared masthead and only adds a Results tab; workspace remains a separate link',()=>{
  const dom=new JSDOM(html);try{
    const doc=dom.window.document;
    assert.ok(doc.querySelector('.arena-masthead .arena-brand'));
    assert.deepEqual([...doc.querySelectorAll('.arena-tabs>a')].map(link=>link.getAttribute('href')),['/','/?view=participants','/experiments','/results']);
    assert.equal(doc.querySelector('.arena-tabs [aria-current="page"]').textContent,'Results');
    assert.equal(doc.querySelectorAll('a[href="/queue"], a[href="/experiments/queue"], .sidebar, table').length,0);
    assert.ok(doc.querySelector('a[href="/experiments/results"]'));
    assert.ok(doc.querySelector('link[href="/arena-theme.css"]'));
  }finally{dom.window.close();}
});
test('without a key no request is made and unmeasured highlights remain unknown',async()=>{
  const t=mount({initialKey:''});try{await flush();assert.equal(t.calls.length,0);assert.equal(t.doc.getElementById('showcase-content').hidden,true);assert.deepEqual([...t.doc.querySelectorAll('.showcase-highlight-value')].map(n=>n.textContent),['—','—','—','—']);}finally{t.close();}
});
test('same session key performs only a read of the scoped same-origin endpoint',async()=>{
  const t=mount();try{await flush();assert.equal(t.calls.length,1);const call=t.calls[0];assert.equal(call.path,'/api/control/results');assert.equal(call.options.method,undefined);assert.equal(call.options.headers.Authorization,'Bearer private-key');assert.equal(call.options.redirect,'error');assert.equal(call.options.cache,'no-store');assert.equal(t.doc.querySelectorAll('.showcase-model').length,1);assert.equal(t.doc.querySelectorAll('table').length,0);}finally{t.close();}
});
test('private-image study deduplicates program hashes across all models and excludes other frameworks',async()=>{
  const second=clone(run);second.id='run-two';second.model='model-b';second.metrics.canonical.valid_candidate_hashes=['a'.repeat(64),'e'.repeat(64)];
  const native=clone(run);native.framework='sciel';const another=clone(run);another.framework='openevolve';
  const t=mount({runs:[run,second,native,another]});try{await flush();assert.deepEqual([...t.doc.querySelectorAll('.showcase-highlight-value')].map(n=>n.textContent),['2 / 2','4','100%','2 / 2']);assert.equal(t.doc.querySelectorAll('.showcase-model').length,2);assert.match(t.doc.getElementById('showcase-highlights').textContent,/includes the seed/);}finally{t.close();}
});
test('seed ties are explicit and native search budget is never presented as model requests or billing',async()=>{
  const t=mount();try{await flush();assert.match(t.doc.querySelector('.showcase-score-pair').textContent,/1→1/);assert.match(t.doc.getElementById('showcase-seed-note').textContent,/No improvement over the starting score/);assert.equal(t.doc.getElementById('showcase-budget-value').textContent,'4');assert.match(t.doc.getElementById('showcase-budget-title').textContent,/B_evals/);assert.match(t.doc.getElementById('showcase-budget-note').textContent,/not the number of LLM requests/);assert.doesNotMatch(t.doc.getElementById('main').textContent,/\$0|cheapest|best system|optimal solution achieved|improved by|perfect/i);}finally{t.close();}
});
test('failed processes retain evidence and partial tokens are excluded from complete-ledger ranges',async()=>{
  const partial=clone(run);partial.id='partial';partial.model='model-b';partial.state='failed';partial.metrics.usage={total_tokens:2000,complete:false};
  const t=mount({runs:[run,partial]});try{await flush();assert.equal(t.doc.querySelectorAll('.showcase-model').length,2);assert.match(t.doc.querySelector('[data-run-id="partial"]').textContent,/Failed · recorded evidence retained/);assert.equal(t.doc.querySelectorAll('.showcase-token-fill.is-partial').length,1);assert.match(t.doc.getElementById('showcase-token-context').textContent,/5,000 tokens per run · 1 complete provider ledger/);assert.doesNotMatch(t.doc.getElementById('showcase-token-context').textContent,/2,000/);assert.equal(t.doc.querySelectorAll('.showcase-highlight-value')[3].textContent,'1 / 2');}finally{t.close();}
});
test('partial canonical evidence stays visible even when all retained evaluations are valid and the process completed',async()=>{
  const partial=clone(run);partial.metrics.canonical={...partial.metrics.canonical,status:'partial',evaluations:1,valid:1,invalid:0,unknown:0,valid_candidate_hashes:['a'.repeat(64)],best_score:.75,seed_score:null};partial.metrics.evidence={issues:['Private rejected artifact diagnostic']};
  const t=mount({runs:[partial]});try{await flush();const row=t.doc.querySelector('.showcase-model');assert.match(row.textContent,/Completed/);assert.match(row.textContent,/Partial canonical evidence/);assert.equal(row.querySelector('.showcase-score-pair').textContent,'—→0.75');assert.match(t.doc.getElementById('showcase-methodology-body').textContent,/1 run has partial canonical evidence; validity percentages cover retained, classified receipts/);assert.match(t.doc.querySelectorAll('.showcase-highlight')[2].textContent,/100%1 \/ 1 classified evaluations/);assert.doesNotMatch(t.doc.getElementById('main').textContent,/Private rejected artifact diagnostic/);}finally{t.close();}
});
test('missing measurements and hash lists are not replaced by zero or native scores',async()=>{
  const missing=clone(run);missing.metrics.canonical={...missing.metrics.canonical,evaluations:0,valid:0,invalid:0,valid_candidate_hashes:undefined,seed_score:null,best_score:null};missing.metrics.usage={total_tokens:null,complete:false};missing.metrics.budget={};missing.metrics.native={best_score:999};
  const t=mount({runs:[missing]});try{await flush();assert.equal(t.doc.querySelector('.showcase-score-pair').textContent,'—→—');assert.equal(t.doc.querySelectorAll('.showcase-token-fill').length,0);assert.match(t.doc.getElementById('showcase-tokens').textContent,/tokens not recorded/);assert.equal(t.doc.querySelectorAll('.showcase-highlight-value')[1].textContent,'—');assert.equal(t.doc.querySelectorAll('.showcase-highlight-value')[2].textContent,'—');assert.equal(t.doc.getElementById('showcase-budget-value').textContent,'—');assert.doesNotMatch(t.doc.getElementById('main').textContent,/999/);}finally{t.close();}
});
test('real zero scores and zero token counts remain measurements; minimization gains use the right direction',async()=>{
  const zero=clone(run);zero.metrics.canonical.seed_score=2;zero.metrics.canonical.best_score=0;zero.metrics.canonical.direction='minimize';zero.metrics.usage.total_tokens=0;
  const t=mount({runs:[zero]});try{await flush();assert.equal(t.doc.querySelector('.showcase-score-pair').textContent,'2→0');assert.match(t.doc.getElementById('showcase-seed-note').textContent,/1 run improved/);assert.match(t.doc.getElementById('showcase-token-context').textContent,/0 tokens per run/);assert.equal(t.doc.querySelector('.showcase-token-fill').style.width,'0%');}finally{t.close();}
});
test('task, metric, direction and evaluator identities keep separate studies',async()=>{
  const changed=['task_id','metric','direction','cohort'].map((field,index)=>{const item=clone(run);item.id=`other-${index}`;item.model=`other-${index}`;item.metrics.canonical[field]=field==='direction'?'minimize':field==='cohort'?'f'.repeat(64):'different';return item;});
  const t=mount({runs:[run,...changed]});try{await flush();const select=t.doc.getElementById('showcase-cohort');assert.equal(select.options.length,5);assert.equal(t.doc.querySelectorAll('.showcase-model').length,1);assert.equal(t.doc.getElementById('showcase-cohort-label').hidden,false);assert.match(t.doc.getElementById('showcase-basis').textContent,/4 other SCiEL runs outside this study/);select.value=select.options[1].value;select.dispatchEvent(new t.w.Event('change'));assert.equal(t.doc.querySelectorAll('.showcase-model').length,1);assert.match(t.doc.querySelector('.showcase-model').textContent,/other-0/);}finally{t.close();}
});
test('unknown validity remains separate from classified validity and partial hash coverage is stated',async()=>{
  const unknown=clone(run);unknown.id='unknown';unknown.metrics.canonical={...unknown.metrics.canonical,evaluations:4,valid:2,invalid:1,unknown:1,valid_candidate_hashes:undefined};
  const t=mount({runs:[run,unknown]});try{await flush();const cards=t.doc.querySelectorAll('.showcase-highlight');assert.match(cards[2].textContent,/83.3%/);assert.match(cards[2].textContent,/5 \/ 6 classified evaluations. 1 receipt unclassified/);assert.match(cards[1].textContent,/Hash coverage is partial/);}finally{t.close();}
});
test('new key submission stores only a session key and never uses it in a URL',async()=>{
  const t=mount({initialKey:''});try{t.doc.getElementById('showcase-connect').click();assert.equal(t.doc.activeElement.id,'showcase-key');t.doc.getElementById('showcase-key').value='new-secret';t.doc.getElementById('showcase-key-form').dispatchEvent(new t.w.Event('submit',{bubbles:true,cancelable:true}));await flush();assert.equal(t.stored.get('arena.queue.session-key'),'new-secret');assert.equal(t.doc.getElementById('showcase-key').value,'');assert.equal(t.doc.getElementById('showcase-key-dialog').open,false);assert.ok(t.calls.every(call=>!call.path.includes('new-secret')));}finally{t.close();}
});
test('authorization errors remove previous private content and invalid keys',async()=>{
  const t=mount({fetcher:async(_path,_options,n)=>n===1?{ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})}:{ok:false,status:403}});try{await flush();assert.equal(t.doc.querySelectorAll('.showcase-model').length,1);await t.app.refresh();assert.equal(t.doc.querySelectorAll('.showcase-model').length,0);assert.equal(t.stored.size,0);assert.match(t.doc.getElementById('showcase-status').textContent,/does not have access/);assert.equal(t.doc.getElementById('showcase-content').hidden,true);}finally{t.close();}
});
test('disconnect clears evidence and a late response cannot restore it',async()=>{
  let resolve;const t=mount({fetcher:()=>new Promise(done=>{resolve=done;})});try{await flush();t.app.disconnect();resolve({ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})});await flush();assert.equal(t.stored.size,0);assert.equal(t.doc.querySelectorAll('.showcase-model').length,0);assert.match(t.doc.getElementById('showcase-status').textContent,/Disconnected/);await t.app.refresh();assert.equal(t.calls.length,1);}finally{t.close();}
});
test('untrusted labels render as text, never HTML',async()=>{
  const bad=clone(run);bad.model='<img src=x onerror=alert(1)>';bad.metrics.canonical.task_name='<script>alert(1)</script>';
  const t=mount({runs:[bad]});try{await flush();assert.equal(t.doc.querySelectorAll('#main img:not([src^="/brand/"]), #main script').length,0);assert.match(t.doc.getElementById('showcase-models').textContent,/<img/);assert.match(t.doc.getElementById('showcase-basis').textContent,/<script/);}finally{t.close();}
});
test('a stalled fetch times out, aborts and allows an explicit read-only retry',async()=>{
  const t=mount({requestTimeoutMs:10,fetcher:async(_path,_options,n)=>n===1?new Promise(()=>{}):{ok:true,json:async()=>({schema:'arena.results/1',runs:[run]})}});
  try{await new Promise(resolve=>setTimeout(resolve,25));await flush();assert.match(t.doc.getElementById('showcase-status').textContent,/timed out/);assert.equal(t.calls[0].options.signal.aborted,true);assert.equal(t.doc.getElementById('showcase-refresh').disabled,false);await t.app.refresh();assert.equal(t.doc.querySelectorAll('.showcase-model').length,1);assert.equal(t.calls.length,2);}finally{t.close();}
});
test('a stalled response body also times out without leaving Refresh disabled',async()=>{
  const t=mount({requestTimeoutMs:10,fetcher:async()=>({ok:true,json:()=>new Promise(()=>{})})});
  try{await new Promise(resolve=>setTimeout(resolve,25));await flush();assert.match(t.doc.getElementById('showcase-status').textContent,/timed out/);assert.equal(t.doc.getElementById('showcase-refresh').disabled,false);}finally{t.close();}
});
test('truncated results disclose sample scope and absent SCiEL results never substitute another participant',async()=>{
  const t=mount({responseExtra:{truncated:true,total:600}});try{await flush();assert.match(t.doc.getElementById('showcase-basis').textContent,/Loaded 1 record of 600 available/);}finally{t.close();}
  const other=clone(run);other.framework='other-framework';const empty=mount({runs:[other]});try{await flush();assert.equal(empty.doc.getElementById('showcase-content').hidden,true);assert.equal(empty.doc.querySelectorAll('.showcase-model').length,0);assert.match(empty.doc.getElementById('showcase-empty-copy').textContent,/No canonical SCiEL private-image results/);}finally{empty.close();}
});
