// Saved-fixture UI tests. No provider, evaluator or experiment process is used.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
const source=readFileSync(new URL('../../web/workflow.js',import.meta.url),'utf8').replaceAll('export function ','function ');
const pause=()=>new Promise(resolve=>setTimeout(resolve,5));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await pause();}assert.fail('Workflow did not update');}
function mount(){const dom=new JSDOM('<main id="root"></main>',{runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;w.eval('{'+source+';window.renderWorkFlow=renderWorkFlow;window.destroyWorkFlow=destroyWorkFlow;}');return {dom,w,root:w.document.getElementById('root')};}
const event=(id='one',changes={})=>({id,actor:'model',title:'Candidate proposal returned',summary:'A saved response, pending evaluation.',timestamp:'2026-09-19T18:06:05Z',status:'returned',iteration:4,model:'google/gemini-2.5-flash',elapsed_seconds:125,duration_seconds:3.5,cost:.0012,refs:{experiment_id:'r4'},commit_state:'pending',details_available:true,...changes});
const page=(items,rest={})=>({items,total:items.length,next_before:null,has_more:false,warnings:[],...rest});
const detail=()=>({sections:[{label:'Prompt',format:'text',text:'<script>not HTML</script>\nA complete saved prompt.'},{label:'Response',format:'text',text:'<img src=x onerror=alert(1)>\nA full model response.'},{label:'Changes',format:'diff',text:'--- parent.py\n+++ child.py\n@@ -1 +1 @@\n-radius = 1\n+radius = 2'}]});

test('saved metadata is compact, roles and UTC times explicit, full text loads only on disclosure',async()=>{
 const {dom,w,root}=mount();try{
  const calls=[];const fetchJSON=async url=>{calls.push(url);return url.includes('?')?page([event('one',{model:'model <img src=x>',summary:'<script>summary</script>'})]):detail();};
  w.renderWorkFlow(root,{runId:'run 1',fetchJSON});await until(()=>root.querySelector('.wf-message'));
  assert.equal(calls.length,1);assert.match(calls[0],/\/api\/runs\/run%201\/workflow\?/);
  assert.equal(root.querySelector('.wf-time').textContent,'18:06:05');assert.equal(root.querySelector('.wf-time').getAttribute('datetime'),'2026-09-19T18:06:05.000Z');
  assert.match(root.textContent,/T\+00:02:05/);assert.match(root.textContent,/Pending commit/);assert.match(root.textContent,/\$0\.0012/);
  assert.equal(root.querySelectorAll('img,script').length,0);assert.equal(root.querySelectorAll('.wf-raw').length,0);
  root.querySelector('.wf-inspect').open=true;await until(()=>root.querySelector('.wf-raw'));
  assert.equal(calls.length,2);assert.equal(root.querySelectorAll('.wf-section').length,3);
  assert.match(root.querySelector('.wf-raw').textContent,/<script>not HTML<\/script>/);assert.equal(root.querySelectorAll('img,script').length,0);
  const diff=root.querySelectorAll('.wf-section')[2];assert.equal(diff.open,false);assert.equal(diff.querySelectorAll('.wf-diff-line').length,0);
  diff.open=true;await until(()=>diff.querySelector('.wf-diff-line.added'));assert.match(diff.textContent,/radius = 2/);assert.match(diff.querySelector('.removed').textContent,/radius = 1/);
  const disclosure=root.querySelector('.wf-inspect');disclosure.open=false;await pause();disclosure.open=true;await pause();assert.equal(calls.length,2);
 }finally{w.destroyWorkFlow(root);dom.window.close();}
});

test('unchanged refresh retains message nodes, disclosures, inner scroll and focus',async()=>{
 const {dom,w,root}=mount();try{
  const fetchJSON=async url=>url.includes('?')?page([event()]):detail();
  w.renderWorkFlow(root,{runId:'r',version:'1',fetchJSON});await until(()=>root.querySelector('.wf-message'));
  const message=root.querySelector('.wf-message'),disclosure=message.querySelector('.wf-inspect');disclosure.open=true;await until(()=>message.querySelector('.wf-raw'));
  const raw=message.querySelector('.wf-raw');raw.scrollTop=100;raw.focus();const stream=root.querySelector('.wf-stream');
  Object.defineProperties(stream,{scrollHeight:{get:()=>2000},clientHeight:{get:()=>600}});stream.scrollTop=200;
  w.renderWorkFlow(root,{runId:'r',version:'2',fetchJSON});await pause();await pause();
  assert.equal(root.querySelector('.wf-message'),message);assert.equal(disclosure.open,true);assert.equal(raw.scrollTop,100);assert.equal(stream.scrollTop,200);assert.equal(w.document.activeElement,raw);
 }finally{w.destroyWorkFlow(root);dom.window.close();}
});

test('new activity waits while an earlier message is being read',async()=>{
 const {dom,w,root}=mount();try{
  let items=[event()];const fetchJSON=async()=>page(items);
  w.renderWorkFlow(root,{runId:'r',version:'1',fetchJSON});await until(()=>root.querySelector('.wf-message'));
  const stream=root.querySelector('.wf-stream');Object.defineProperties(stream,{scrollHeight:{get:()=>2000},clientHeight:{get:()=>600}});stream.scrollTop=100;
  items=[event(),event('two',{actor:'task',title:'Evaluation returned'})];
  w.renderWorkFlow(root,{runId:'r',version:'2',fetchJSON});await until(()=>!root.querySelector('.wf-new-activity').hidden);
  assert.equal(root.querySelectorAll('.wf-message').length,1);assert.equal(stream.scrollTop,100);
  root.querySelector('.wf-new-activity').click();assert.equal(root.querySelectorAll('.wf-message').length,2);assert.equal(root.querySelector('.wf-new-activity').hidden,true);
 }finally{w.destroyWorkFlow(root);dom.window.close();}
});

test('actor filters, search and older/newer pages use bounded server queries',async()=>{
 const {dom,w,root}=mount();try{
  const urls=[];const fetchJSON=async url=>{urls.push(url);const q=new URL(url,'http://test').searchParams;return q.has('before')?page([event('old')],{total:120}):page([event('new')],{total:120,has_more:true,next_before:'new & opaque'});};
  w.renderWorkFlow(root,{runId:'r',fetchJSON});await until(()=>root.querySelector('.wf-message'));
  root.querySelector('.wf-pagebar button').click();await until(()=>root.querySelector('[data-event-id=old]'));
  assert.match(urls.at(-1),/before=new\+%26\+opaque/);
  root.querySelectorAll('.wf-pagebar button')[1].click();await until(()=>root.querySelector('[data-event-id=new]'));
  root.querySelector('[data-actor=tool]').click();await pause();assert.equal(new URL(urls.at(-1),'http://test').searchParams.get('actor'),'tool');
  assert.equal(root.querySelector('[data-actor=tool]').getAttribute('aria-pressed'),'true');
  const search=root.querySelector('input[type=search]');search.value='r17 & error';search.dispatchEvent(new w.Event('input'));await new Promise(r=>setTimeout(r,240));
  const params=new URL(urls.at(-1),'http://test').searchParams;assert.equal(params.get('q'),'r17 & error');assert.equal(params.get('limit'),'60');assert.equal(params.has('before'),false);
 }finally{w.destroyWorkFlow(root);dom.window.close();}
});

test('late list/detail results cannot cross run identity or destroyed tab boundaries',async()=>{
 const {dom,w,root}=mount();try{
  let release;w.renderWorkFlow(root,{runId:'old',fetchJSON:()=>new Promise(r=>{release=r;})});
  let releaseDetail;const fetchJSON=url=>url.includes('?')?Promise.resolve(page([event('new')])):new Promise(r=>{releaseDetail=r;});
  w.renderWorkFlow(root,{runId:'new',fetchJSON});await until(()=>root.querySelector('[data-event-id=new]'));
  release(page([event('old')]));await pause();assert.equal(root.querySelector('[data-event-id=old]'),null);
  root.querySelector('.wf-inspect').open=true;await until(()=>releaseDetail);
  w.destroyWorkFlow(root);root.textContent='Another tab';releaseDetail(detail());await pause();assert.equal(root.textContent,'Another tab');
 }finally{dom.window.close();}
});

test('unavailable timestamps are not inferred, failures preserve previous messages, malformed evidence can retry',async()=>{
 const {dom,w,root}=mount();try{
  let failed=false,invalidDetail=true,calls=0;
  const fetchJSON=async url=>{if(!url.includes('?')){calls++;return invalidDetail?{}:detail();}if(failed)throw new Error('unavailable');return page([event('one',{timestamp:null,elapsed_seconds:null,cost:null,cost_unknown:true})],{warnings:['An older artifact is unavailable.']});};
  w.renderWorkFlow(root,{runId:'r',version:1,fetchJSON});await until(()=>root.querySelector('.wf-message'));
  assert.equal(root.querySelector('.wf-time').textContent,'Time not recorded');assert.equal(root.querySelector('.wf-time').hasAttribute('datetime'),false);assert.match(root.textContent,/Cost unknown/);assert.doesNotMatch(root.textContent,/T\+/);
  assert.match(root.querySelector('.wf-notice').textContent,/older artifact/);
  root.querySelector('.wf-inspect').open=true;await until(()=>root.querySelector('.wf-evidence button'));
  invalidDetail=false;root.querySelector('.wf-evidence button').click();await until(()=>root.querySelector('.wf-raw'));assert.equal(calls,2);
  failed=true;w.renderWorkFlow(root,{runId:'r',version:2,fetchJSON});await until(()=>!root.querySelector('.wf-error').hidden);
  assert.equal(root.querySelectorAll('.wf-message').length,1);
  failed=false;root.querySelector('.wf-refresh').click();await until(()=>root.querySelector('.wf-error').hidden);
 }finally{w.destroyWorkFlow(root);dom.window.close();}
});

test('live polling is bounded and stops when paused, disconnected or destroyed',async()=>{
 const {dom,w,root}=mount();try{
  const timers=new Map();let id=0,calls=0;w.setInterval=(fn,ms)=>{assert.equal(ms,3000);timers.set(++id,fn);return id;};w.clearInterval=id=>timers.delete(id);
  const fetchJSON=async()=>{calls++;return page([event()]);};
  w.renderWorkFlow(root,{runId:'r',live:true,follow:true,connected:true,fetchJSON});await until(()=>root.querySelector('.wf-message'));assert.equal(timers.size,1);
  [...timers.values()][0]();await pause();assert.equal(calls,2);
  w.renderWorkFlow(root,{runId:'r',live:true,follow:false,connected:true,fetchJSON});assert.equal(timers.size,0);assert.match(root.textContent,/Updates paused/);
  w.renderWorkFlow(root,{runId:'r',live:true,follow:true,connected:false,fetchJSON});assert.equal(timers.size,0);
  w.renderWorkFlow(root,{runId:'r',live:true,follow:true,connected:true,fetchJSON});assert.equal(timers.size,1);
  w.destroyWorkFlow(root);assert.equal(timers.size,0);
 }finally{dom.window.close();}
});

test('changed saved evidence is explicit and reloadable without closing its reader',async()=>{
 const {dom,w,root}=mount();try{
  let status='dispatched',detailCalls=0;const fetchJSON=async url=>{if(url.includes('?'))return page([event('one',{status})]);detailCalls++;return detail();};
  w.renderWorkFlow(root,{runId:'r',version:1,fetchJSON});await until(()=>root.querySelector('.wf-message'));
  root.querySelector('.wf-inspect').open=true;await until(()=>root.querySelector('.wf-raw'));const raw=root.querySelector('.wf-raw');raw.scrollTop=200;
  status='returned';w.renderWorkFlow(root,{runId:'r',version:2,fetchJSON});await until(()=>root.querySelector('.wf-evidence-refresh'));
  assert.equal(root.querySelector('.wf-raw'),raw);assert.equal(raw.scrollTop,200);assert.equal(detailCalls,1);
  root.querySelector('.wf-evidence-refresh').click();await until(()=>detailCalls===2&&!root.querySelector('.wf-evidence-refresh'));
 }finally{w.destroyWorkFlow(root);dom.window.close();}
});
