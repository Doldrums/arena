// Pure DOM regression: inert JSON/text fixtures, no engine or server process.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source=readFileSync(new URL('../../web/llm_calls.js',import.meta.url),'utf8').replace('export function renderLLMCalls','function renderLLMCalls');
const pause=()=>new Promise(resolve=>setTimeout(resolve,5));
async function until(fn){for(let n=0;n<100;n++){if(fn())return;await pause();}assert.fail('DOM did not update');}
function mount(){
  const dom=new JSDOM('<main id="content"></main>',{runScripts:'outside-only'});
  dom.window.eval('{'+source+'; window.renderLLMCalls=renderLLMCalls;}');
  return {dom,w:dom.window,container:dom.window.document.getElementById('content')};
}

test('cost inspector distinguishes provider zero, estimated zero and unannotated history',async()=>{
  for(const [provenance,label] of [
    [{source:'provider_reported',reported_cost:0},'Provider reported'],
    [{source:'token_estimate',pricing_key:'default',prompt_usd_per_1k:.001,completion_usd_per_1k:.002},'Token estimate'],
    [null,'Not recorded']]){
    const {dom,w,container}=mount();
    try{
      const call={id:'zero',role:'G',status:'returned',cost:0,cost_provenance:provenance};
      w.renderLLMCalls(container,{runId:'run',version:'v1',fetchJSON:async path=>path.includes('?')?{calls:[call],total:1,next_offset:null}:call});
      await until(()=>container.querySelector('.llm-call'));
      container.querySelector('.llm-call').open=true;
      await until(()=>container.querySelector('.llm-metadata'));
      const fields=Object.fromEntries([...container.querySelectorAll('.llm-metadata > div')].map(node=>[node.querySelector('dt').textContent,node.querySelector('dd').textContent]));
      assert.equal(fields['Recorded cost'],'$0.000000');
      assert.equal(fields['Cost source'],label);
      if(provenance?.source==='token_estimate')assert.match(fields['Saved estimate rates'],/default.*0.001.*0.002.*per 1K tokens/);
    }finally{dom.window.close();}
  }
});

test('LLM inspector lazily loads exact text and honestly shows failed/missing response',async()=>{
  const {dom,w,container}=mount();
  try{
    const paths=[];
    const call={id:'call-1',role:'C',reference:'r17',iteration:16,model:'model <img src=x>',status:'failed',started_at:'2026-09-19T01:00:00Z',elapsed_seconds:3};
    const fetchJSON=async path=>{
      paths.push(path);
      if(path.includes('?'))return {calls:[call],total:1,next_offset:null};
      return {...call,latency_source:'recorded_call',current_call_cost_unknown:true,cost:null,
        error:{reason:'connection_error'},request_options:{temperature:.2},
        prompt:{text:'<script>never execute</script>\nfull request',available:true,truncated:false,sha256:'abc'},
        response:{text:null,available:false,truncated:false,note:'No response text was recorded for this call.'}};
    };
    w.renderLLMCalls(container,{runId:'run 1',version:'v1',fetchJSON});
    await until(()=>container.querySelector('.llm-call'));
    assert.equal(paths.length,1,'list carries metadata only');
    assert.match(container.querySelector('.llm-call-time').textContent,/19 Sep.*00:00.*UTC/);
    assert.equal(container.querySelectorAll('img,script').length,0);
    const element=container.querySelector('.llm-call');
    element.open=true;
    await until(()=>container.querySelector('.llm-raw'));
    assert.equal(paths.length,2);
    assert.match(paths[1],/\/api\/runs\/run%201\/llm-calls\/call-1$/);
    assert.match(container.textContent,/billed cost is unknown/);
    assert.match(container.textContent,/No response text was recorded/);
    assert.match(container.textContent,/<script>never execute<\/script>/);
    assert.equal(container.querySelectorAll('img,script').length,0);
    assert.match(container.textContent,/Full recorded text/);
    element.open=false;await pause();element.open=true;await pause();
    assert.equal(paths.length,2,'same saved detail is reused');
  }finally{dom.window.close();}
});

test('LLM inspector paginates and rejects stale async updates after changing runs',async()=>{
  const {dom,w,container}=mount();
  try{
    let release;
    const oldFetch=()=>new Promise(resolve=>{release=resolve;});
    w.renderLLMCalls(container,{runId:'old',version:'v1',fetchJSON:oldFetch});
    const pages=[];
    const fetchJSON=async path=>{pages.push(path);return {calls:[{id:'new-call',role:'unknown',reference:'new',status:'returned'}],total:51,next_offset:path.includes('offset=50')?null:50};};
    w.renderLLMCalls(container,{runId:'new',version:'v1',query:'r8',fetchJSON});
    await until(()=>container.querySelector('[data-call-id="new-call"]'));
    release({calls:[{id:'stale',role:'R',reference:'old'}],total:1,next_offset:null});
    await pause();
    assert.equal(container.querySelector('[data-call-id="stale"]'),null);
    assert.equal(container.querySelector('#content-search').value,'r8');
    assert.equal(container.querySelector('.llm-role').textContent,'?');
    assert.match(container.textContent,/Role not recorded/);
    container.querySelector('[data-page="next"]').click();
    await until(()=>pages.length===2);
    assert.match(pages[1],/offset=50/);
    assert.match(pages[1],/q=r8/);
  }finally{dom.window.close();}
});

test('live transcript refresh fetches once and retains nested panels, scroll and keyboard focus',async()=>{
  const {dom,w,container}=mount();
  try{
    const call={id:'one',role:'G',reference:'r1',status:'returned'};
    let requests=0,version='v1',release;
    const detail=label=>({...call,request_options:{temperature:.4},prompt:{text:'request '+label,available:true},response:{text:'response '+label,available:true}});
    const fetchJSON=async path=>{
      if(path.includes('?'))return {calls:[call],total:1,next_offset:null};
      requests++;
      if(version==='v2')return new Promise(resolve=>{release=()=>resolve(detail('v2'));});
      return detail('v1');
    };
    w.renderLLMCalls(container,{runId:'run',identity:'science-A',version,fetchJSON});
    await until(()=>container.querySelector('.llm-call'));
    const element=container.querySelector('.llm-call');element.open=true;
    await until(()=>container.querySelector('[data-text-part="response"]'));
    for(const part of element.querySelectorAll('[data-text-part]'))part.open=true;
    const oldText=element.querySelector('[data-text-part="response"] .llm-raw');
    oldText.scrollTop=45;oldText.scrollLeft=17;oldText.focus();
    version='v2';
    w.renderLLMCalls(container,{runId:'run',identity:'science-A',version,fetchJSON});
    await until(()=>release);
    // Native toggle delivery and repeated same-version renders can overlap the request.
    element.dispatchEvent(new w.Event('toggle'));
    w.renderLLMCalls(container,{runId:'run',identity:'science-A',version,fetchJSON});
    await pause();
    assert.equal(requests,2,'one detail request for each content version');
    assert.strictEqual(container.querySelector('.llm-call'),element,'open call DOM is retained');
    assert.strictEqual(w.document.activeElement,oldText,'focus survives pending list refresh');
    release();
    await until(()=>element.querySelector('[data-text-part="response"] .llm-raw')?.textContent==='response v2');
    assert.equal(element.open,true);
    for(const part of element.querySelectorAll('[data-text-part]'))assert.equal(part.open,true);
    const currentText=element.querySelector('[data-text-part="response"] .llm-raw');
    assert.equal(currentText.scrollTop,45);assert.equal(currentText.scrollLeft,17);
    assert.strictEqual(w.document.activeElement,currentText,'focus returns to the same text pane');
    await pause();assert.equal(requests,2,'restoring nested details does not refetch the call');
  }finally{dom.window.close();}
});

test('transcript identity and version exclude obsolete asynchronous responses',async()=>{
  const {dom,w,container}=mount();
  try{
    const call={id:'shared-call',role:'G',reference:'r1',status:'returned'};
    const pending=[];
    const fetchJSON=async path=>path.includes('?')?{calls:[call],total:1,next_offset:null}:new Promise(resolve=>pending.push(resolve));
    const detail=text=>({...call,prompt:{text,available:true},response:{text,available:true}});
    w.renderLLMCalls(container,{runId:'same-path',identity:'science-A',version:'v1',fetchJSON});
    await until(()=>container.querySelector('.llm-call'));
    container.querySelector('.llm-call').open=true;await until(()=>pending.length===1);
    w.renderLLMCalls(container,{runId:'same-path',identity:'science-B',version:'v1',fetchJSON});
    await until(()=>container.querySelector('.llm-call')?.open===false);
    container.querySelector('.llm-call').open=true;await until(()=>pending.length===2);
    pending[0](detail('obsolete scientific run'));await pause();
    assert.doesNotMatch(container.textContent,/obsolete scientific run/);
    w.renderLLMCalls(container,{runId:'same-path',identity:'science-B',version:'v2',fetchJSON});
    await until(()=>pending.length===3);
    pending[2](detail('current response'));
    await until(()=>container.textContent.includes('current response'));
    pending[1](detail('obsolete version'));await pause();
    assert.doesNotMatch(container.textContent,/obsolete version/);
    assert.match(container.textContent,/current response/);
  }finally{dom.window.close();}
});
