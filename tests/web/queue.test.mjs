import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html=readFileSync(new URL('../../web/queue.html',import.meta.url),'utf8').replace('data-queue-app="true"','data-queue-app="test"');
const source=readFileSync(new URL('../../web/arena-queue.js',import.meta.url),'utf8').replace(/^export /gm,'');
const run={id:'run-123',framework:'sciel',profile:'reference-sat',model:'model-a',template:'sciel-a',label:'Study A',state:'queued',created:1789958000,resources:{cpus:2,memory_mb:4096,evaluation_slots:1},revision:'abc',canonical_evaluation:false};
const template={id:'sciel-a',framework:'sciel',name:'SCiEL pilot',profile:'reference-sat',model:'model-a',status:'ready',resources:run.resources};
const flush=async()=>{for(let i=0;i<5;i++)await new Promise(resolve=>setImmediate(resolve));};
function mount({initialKey='',rows=[run],status=200,logText='Worker started.',total=rows.length}={}){
  const dom=new JSDOM(html,{url:'http://arena.test/queue',runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window,doc=w.document,calls=[];
  w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  const stored=new Map(initialKey?[['arena.queue.session-key',initialKey]]:[]);
  const storage={getItem:k=>stored.get(k),setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)};
  const fetcher=async(path,options)=>{
    calls.push({path,options});
    let value={};
    if(path.includes('/logs?'))value={text:logText,truncated:false,next_cursor:logText.length};
    else if(path==='/api/control/templates')value={templates:[template]};
    else if(path.startsWith('/api/queue?'))value={runs:rows,total,counts:{queued:rows.length},resources:{used:{active:0},limits:{cpus:96,memory_mb:307200,max_active:8,evaluation_slots:32}}};
    else value={run:rows[0]||run};
    return {ok:status===200,status,json:async()=>value};
  };
  w.eval(`${source};window.mountQueue=initQueue;`);
  const app=w.mountQueue({doc,fetcher,storage,pollMs:0});
  return {dom,w,doc,calls,stored,app};
}

test('unauthenticated page load makes no API calls and never queues a run',async()=>{
  const {dom,doc,calls,app}=mount();
  try{await flush();assert.equal(calls.length,0);assert.equal(doc.getElementById('queue-new').disabled,true);assert.match(doc.getElementById('queue-status').textContent,/Connect/);}finally{app.destroy();dom.window.close();}
});
test('read polling uses only same-origin bearer requests and no POST',async()=>{
  const {dom,doc,calls,app}=mount({initialKey:'private-test-key'});
  try{await flush();assert.equal(doc.querySelectorAll('.queue-run').length,1);assert.ok(calls.length>=2);for(const call of calls){assert.equal(call.options.headers.Authorization,'Bearer private-test-key');assert.ok(!call.path.includes('private-test-key'));assert.ok(!call.options.method);}assert.match(doc.getElementById('queue-capacity').textContent,/96 CPU/);}finally{app.destroy();dom.window.close();}
});
test('framework labels, reasons and logs render as text, not executable markup',async()=>{
  const evil='<img src=x onerror=alert(1)>', malicious={...run,label:evil,reason:evil};
  const {dom,doc,app}=mount({initialKey:'key',rows:[malicious],logText:evil});
  try{await flush();doc.querySelector('.queue-run').click();await flush();assert.match(doc.getElementById('queue-detail').textContent,/<img/);assert.equal(doc.getElementById('queue-run-logs').textContent,evil);assert.equal(doc.querySelectorAll('#queue-detail img,#queue-list img').length,0);}finally{app.destroy();dom.window.close();}
});
test('an explicit submit uses reviewed template identity and an idempotency key',async()=>{
  const {dom,w,doc,calls,app}=mount({initialKey:'key'});
  try{await flush();doc.getElementById('queue-new').click();assert.equal(calls.filter(c=>c.options.method==='POST').length,0);doc.getElementById('queue-label').value='Experiment 1';doc.getElementById('queue-submit-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await flush();const posts=calls.filter(c=>c.options.method==='POST');assert.equal(posts.length,1);const body=JSON.parse(posts[0].options.body);assert.equal(body.template,'sciel-a');assert.equal(body.model,'model-a');assert.equal(body.label,'Experiment 1');assert.ok(body.idempotency_key);assert.equal(body.spec,undefined);}finally{app.destroy();dom.window.close();}
});
test('disconnect clears credentials and run data; authorization failure stays explicit',async()=>{
  const first=mount({initialKey:'private-key'});
  try{await flush();first.app.disconnect();assert.equal(first.stored.size,0);assert.equal(first.doc.querySelectorAll('.queue-run').length,0);assert.equal(first.doc.getElementById('queue-new').disabled,true);const count=first.calls.length;await first.app.refresh();assert.equal(first.calls.length,count);}finally{first.app.destroy();first.dom.window.close();}
  const denied=mount({initialKey:'bad-key',status:401});
  try{await flush();assert.match(denied.doc.getElementById('queue-status').textContent,/expired or revoked/);assert.equal(denied.doc.querySelectorAll('.queue-run').length,0);}finally{denied.app.destroy();denied.dom.window.close();}
});
test('queue pagination makes older batches accessible',async()=>{
  const {dom,doc,calls,app}=mount({initialKey:'key',total:518});
  try{await flush();assert.equal(doc.getElementById('queue-next').disabled,false);doc.getElementById('queue-next').click();await flush();assert.ok(calls.some(call=>call.path==='/api/queue?limit=200&offset=200'));assert.equal(doc.getElementById('queue-prev').disabled,false);}finally{app.destroy();dom.window.close();}
});
