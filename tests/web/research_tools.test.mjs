import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
const source=readFileSync(new URL('../../web/research_tools.js',import.meta.url),'utf8').replace(/^export /gm,'');
const pause=()=>new Promise(resolve=>setTimeout(resolve,5));
async function until(fn){for(let n=0;n<100;n++){if(fn())return;await pause();}assert.fail('DOM did not update');}
function mount(){const dom=new JSDOM('<main id="root"></main>',{runScripts:'outside-only',pretendToBeVisual:true});dom.window.eval('{'+source+';window.renderResearchTools=renderResearchTools;}');return {dom,w:dom.window,root:dom.window.document.getElementById('root')};}
const id='a'.repeat(64),receipt='b'.repeat(64);
function fixture(){return {available:true,configured:{enabled:true,share_between_islands:true},summary:{versions:1,published:1,actual_invocations:0,foreign_invocations:0,linked_programs:0,prepared_contexts:1},versions:[{id,name:'helper <img src=x>',author_island_id:0,status:'published',invocations:0,foreign_invocations:0,used_by:[]}],invocations:[],llm_calls:[],child_links:[]};}
const tab=(root,name)=>root.querySelector('[data-view="'+name+'"]');

test('a deferred background cell is visibly not submitted and does not imply execution',()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.cells=[{id:'c'.repeat(64),question:'Probe a bottleneck',stage:'background_deferred',scheduled:false,tool_ids:[]}];
  w.renderResearchTools(root,data,{runId:'run'});
  assert.match(root.textContent,/Background job deferred · not submitted/);
  assert.match(root.textContent,/Actual executions0/);
 }finally{dom.window.close();}
});

function jobsFixture(){const data=fixture();data.jobs={available:true,version:'one',summary:{total:2,visible:2,omitted:0,running:1,queued:1,cancel_requested:1,unknown:0,observed_cpu_seconds:0,observed_cpu_jobs:1,unknown_cpu_jobs:1},items:[{id:'d'.repeat(64),tool_id:id,status:'queued',island_id:0,parent_program_id:'p1',requested:{cpu_seconds:60,wall_seconds:120},actual:{cpu_seconds:null,wall_seconds:null}},{id:'e'.repeat(64),tool_id:id,status:'running',cancel_requested:true,island_id:1,parent_program_id:'p2',parent_job_id:'d'.repeat(64),requested:{cpu_seconds:30,wall_seconds:90},actual:{cpu_seconds:0,wall_seconds:0}}]};return data;}

test('background jobs distinguish requested limits, actual zero, unknown use and cancellation request',()=>{
 const {dom,w,root}=mount();try{
  w.renderResearchTools(root,jobsFixture(),{runId:'run',fetchJSON:()=>assert.fail('details are lazy')});
  assert.match(root.textContent,/Ordinary search can continue/);assert.match(root.textContent,/Cancellation requested/);assert.match(root.textContent,/60\.000s \/ 120\.000s/);assert.match(root.textContent,/0\.000s \/ 0\.000s/);assert.match(root.textContent,/Unknown \/ Unknown/);assert.match(root.textContent,/Continues ddddd/);assert.match(root.textContent,/1 have unknown CPU/);
  assert.equal([...root.querySelectorAll('button')].some(node=>/^(Cancel|Poll|Submit)/.test(node.textContent)),false);
  tab(root,'versions').click();assert.match(root.textContent,/helper <img src=x>/);assert.equal(root.querySelector('img'),null);
 }finally{dom.window.close();}
});

test('background job receipt refresh preserves inspected request across running updates and loads completed output',async()=>{
 const {dom,w,root}=mount();try{
  const data=jobsFixture(),requests=[];data.jobs.items=data.jobs.items.slice(0,1);const job=data.jobs.items[0];
  const options={runId:'run',fetchJSON:async path=>{requests.push(path);return {verified:true,kind:'job',request:{inputs:{query:'<script>exact request</script>'}},receipt:job.receipt_id?{output:{answer:0},resources:{cpu_seconds:0}}:null};}};
  w.renderResearchTools(root,data,options);root.querySelector('.tools-table tbody button').click();await until(()=>root.textContent.includes('Exact submitted job'));
  const source=root.querySelector('.tool-raw');source.scrollTop=19;source.focus();
  job.status='running';data.jobs.version='two';w.renderResearchTools(root,data,options);
  assert.strictEqual(root.querySelector('.tool-raw'),source);assert.strictEqual(w.document.activeElement,source);assert.equal(source.scrollTop,19);assert.equal(requests.length,1);assert.match(root.querySelector('.tool-job-status').textContent,/Running/);
  job.status='completed';job.receipt_id=receipt;job.actual={cpu_seconds:0,wall_seconds:2};data.jobs.version='three';w.renderResearchTools(root,data,options);await until(()=>root.textContent.includes('"answer": 0'));
  assert.equal(requests.length,2);assert.match(requests[0],/research-tool-jobs\/d{64}$/);assert.match(root.textContent,/Verified result · full output/);assert.equal(root.querySelector('script'),null);assert.match(root.querySelector('.tool-job-resources').textContent,/CPU 0\.000s/);
 }finally{dom.window.close();}
});

test('library preserves zero, unknown and owner-only semantics without creating Programs',()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.configured.share_between_islands=false;
  w.renderResearchTools(root,data,{runId:'one',fetchJSON:()=>assert.fail('must be lazy')});
  assert.equal(root.querySelector('.tools-summary strong').textContent,'1');
  assert.match(root.textContent,/Island 0/);assert.match(root.textContent,/Owner only/);
  assert.match(root.textContent,/Cross-island executions0/);assert.match(root.textContent,/not prove prompt delivery/);
  assert.match(root.textContent,/causal utility/);assert.equal(root.querySelectorAll('img,script').length,0);
  tab(root,'links').click();assert.match(root.textContent,/Native Programs remain in the Programs tab/);
  w.renderResearchTools(root,{}, {runId:'other'});assert.equal(root.querySelector('.tools-summary strong').textContent,'—');
 }finally{dom.window.close();}
});

test('verified source loads lazily and retains DOM across metadata updates and tab switches',async()=>{
 const {dom,w,root}=mount();try{
  const paths=[],data=fixture();const options={runId:'run 1',identity:'science',fetchJSON:async path=>{paths.push(path);return {verified:true,files:{'tool.py':'# <script>raw</script>\ndef run(): return 0'},manifest:{name:'exact'},parents:[{id:'c'.repeat(64),verified:true,diff:'-old\n+new'}]};}};
  w.renderResearchTools(root,data,options);assert.equal(paths.length,0);
  root.querySelector('.tool-name button').click();await until(()=>root.querySelector('.tool-raw'));
  assert.match(paths[0],/\/api\/runs\/run%201\/research-tools\/a{64}$/);
  const source=root.querySelector('.tool-raw'),holder=root.querySelector('.tool-immutable');source.scrollTop=23;source.focus();
  data.versions[0].invocations=1;w.renderResearchTools(root,data,options);
  assert.strictEqual(root.querySelector('.tool-raw'),source);assert.strictEqual(w.document.activeElement,source);assert.equal(source.scrollTop,23);
  tab(root,'calls').click();tab(root,'versions').click();root.querySelector('.tool-name button').click();
  assert.strictEqual(root.querySelector('.tool-immutable'),holder);assert.equal(paths.length,1);
  assert.equal(root.querySelectorAll('script,img').length,0);assert.match(root.textContent,/Diff from ccccc/);
 }finally{dom.window.close();}
});

test('exact proposal exchange and invocation outputs are inspected separately from code',async()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.llm_calls=[{action_id:'episode',attempt:0,island_id:0,phase:'llm_result',known_cost:0,receipt_id:receipt}];
  data.invocations=[{tool_id:id,invocation_id:'logical',island_id:0,status:'failed',dispatch_status:'not_dispatched',receipt_id:'c'.repeat(64),resources:{cpu_seconds:0,wall_seconds:0}}];
  const requests=[];w.renderResearchTools(root,data,{runId:'run',fetchJSON:async path=>{requests.push(path);return path.endsWith(receipt)?{verified:true,kind:'proposal',payload:{prompt:'exact <script>request</script>',response:{text:'exact reply',cost:0}}}:{verified:true,kind:'invocation',payload:{inputs:{x:0},receipt:{output:{score:0},status:'failed',dispatch_status:'not_dispatched'}}};}});
  tab(root,'calls').click();assert.match(root.textContent,/\$0\.0000/);root.querySelector('.tools-table tbody button').click();await until(()=>root.textContent.includes('exact reply'));
  assert.match(requests[0],/research-tool-artifacts\/b{64}$/);assert.match(root.textContent,/Exact saved request/);assert.equal(root.querySelector('script'),null);
  tab(root,'invocations').click();assert.match(root.textContent,/Not dispatched/);assert.match(root.textContent,/0\.000s \/ 0\.000s/);
  [...root.querySelectorAll('button')].find(n=>n.textContent==='Open exact inputs & output').click();await until(()=>root.textContent.includes('Exact inputs'));
  assert.match(root.textContent,/"score": 0/);assert.match(root.textContent,/file bundle/);
 }finally{dom.window.close();}
});

test('pending and unknown dispatches never appear as successful execution',()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.invocations=[{phase:'invocation_started',tool_id:id,status:'pending',island_id:0},{phase:'invocation_result',tool_id:id,status:'unknown',dispatch_status:'unknown',island_id:1}];
  w.renderResearchTools(root,data,{runId:'run'});tab(root,'invocations').click();
  assert.match(root.textContent,/Pending · dispatch unconfirmed/);assert.match(root.textContent,/Outcome unknown/);assert.match(root.textContent,/No saved receipt/);
 }finally{dom.window.close();}
});

test('unverified artifacts and stale responses cannot replace selected run content',async()=>{
 const {dom,w,root}=mount();try{
  let release;w.renderResearchTools(root,fixture(),{runId:'old',fetchJSON:()=>new Promise(resolve=>{release=resolve;})});root.querySelector('.tool-name button').click();
  const next=fixture();next.versions[0].name='new';w.renderResearchTools(root,next,{runId:'new',fetchJSON:async()=>({verified:false,files:{'tool.py':'DO NOT DISPLAY'}})});
  release({verified:true,files:{'tool.py':'OLD SOURCE'}});await pause();assert.doesNotMatch(root.textContent,/OLD SOURCE/);
  root.querySelector('.tool-name button').click();await until(()=>root.textContent.includes('Artifact not verified'));
  assert.doesNotMatch(root.textContent,/DO NOT DISPLAY/);
 }finally{dom.window.close();}
});

test('linked remeasurement opens native program ID without assigning mutation or utility credit',()=>{
 const {dom,w,root}=mount();try{
  const data=fixture(),selected=[];data.child_links=[{child_program_id:'p0175',link_kind:'remeasurement',island_id:0,tool_ids:[id],receipt_ids:[receipt]}];
  w.renderResearchTools(root,data,{runId:'run',onProgram:ident=>selected.push(ident)});tab(root,'links').click();root.querySelector('.tools-table tbody button').click();
  assert.deepEqual(selected,['p0175']);assert.match(root.textContent,/Remeasurement/);assert.doesNotMatch(root.textContent,/Mutation/);
  [...root.querySelectorAll('button')].find(n=>n.textContent==='Inspect').click();assert.match(root.textContent,/not proof of prompt delivery or a causal score improvement/);
 }finally{dom.window.close();}
});

test('visible records remain bounded to 200 even for an oversized payload',()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.versions=Array.from({length:250},(_,n)=>({...data.versions[0],id:String(n).padStart(64,'0')}));
  w.renderResearchTools(root,data,{runId:'run'});assert.equal(root.querySelectorAll('tbody tr').length,200);
 }finally{dom.window.close();}
});

test('durable cells display recorded lifecycle counts without claiming task benefit',async()=>{
 const {dom,w,root}=mount();try{
  const cell='c'.repeat(64),revision='d'.repeat(64),data=fixture(),paths=[];
  data.cells=[{id:cell,head_revision:revision,question:'Why does the population stagnate? <script>unsafe</script>',origin_island_id:0,stage:'research',scheduled:true,tool_ids:[id]}];
  data.lifecycle={recorded:true,counts:{proposed_cells:1,local_trials:2,matched_replays:0,adoptions:0,post_adoption_uses:0},events:[{phase:'replay_result',cell_id:cell,tool_id:id,receipt_id:receipt,island_id:1,matched:false,status:'not_reproduced'}]};
  w.renderResearchTools(root,data,{runId:'run',fetchJSON:async path=>{paths.push(path);return {verified:true,kind:'cell',terminal_decision:{verified:true,proposal_id:receipt,conclusion:'inconclusive',interpretation:'The reported output is invalid.',next_decision:'Repair the feasibility check.',omitted_chars:{}},genesis:{question:'Exact stored question',origin_island:0,trigger:{score:0}},revision_history:[{id:revision,ordinal:1,phase:'propose',summary:'Opened from recorded stagnation',tool_ids:[id],evidence:[{kind:'tool_invocation',id:receipt}],decision:{benefit:'not_established'}}]};}});
  assert.match(root.textContent,/Local trial & repair · scheduled/);assert.match(root.textContent,/separate from candidate programs/);
  assert.match(root.querySelector('.cell-stage-counts').textContent,/0Replay checks passed/);assert.equal(root.querySelector('script'),null);
  root.querySelector('.tool-name button').click();await until(()=>root.textContent.includes('Exact stored question'));
  assert.match(paths[0],/research-cells\/c{64}$/);assert.match(root.textContent,/Roles, evidence and decision/);
  assert.equal(root.querySelectorAll('.cell-revision').length,1);
  assert.match(root.textContent,/Model interpretation · inconclusive/);assert.match(root.textContent,/reported output is invalid/);assert.match(root.textContent,/separate from execution status and canonical candidate validity/);assert.match(root.textContent,/Saved terminal request & response/);
  const history=root.querySelector('.tool-immutable');w.renderResearchTools(root,data,{runId:'run',fetchJSON:async()=>assert.fail('unchanged source must not refetch')});assert.strictEqual(root.querySelector('.tool-immutable'),history);
  tab(root,'lifecycle').click();assert.match(root.textContent,/Replay criterion not met/);assert.doesNotMatch(root.querySelector('.tools-table').textContent,/Improved/);
 }finally{dom.window.close();}
});

test('adoption and later refused attempt stay distinct from actual use, and new cell heads can be opened',async()=>{
 const {dom,w,root}=mount();try{
  const cell='c'.repeat(64),data=fixture();data.cells=[{id:cell,head_revision:'d'.repeat(64),question:'Question',stage:'adopted_for_trials',origin_island_id:0,tool_ids:[id]}];
  data.lifecycle={recorded:true,counts:{proposed_cells:1,local_trials:1,matched_replays:1,adoptions:1,post_adoption_uses:0},events:[{phase:'adopted',cell_id:cell,tool_id:id,receipt_id:receipt,status:'adopted_for_trials',island_id:1},{phase:'post_adoption_attempt',cell_id:cell,tool_id:id,receipt_id:'f'.repeat(64),dispatch_status:'not_dispatched',status:'failed',island_id:1}]};
  let requests=0;const options={runId:'run',fetchJSON:async()=>({verified:true,kind:'cell',genesis:{question:'History '+(++requests)},revision_history:[]})};
  w.renderResearchTools(root,data,options);root.querySelector('.tool-name button').click();await until(()=>root.textContent.includes('History 1'));
  data.cells[0].head_revision='e'.repeat(64);w.renderResearchTools(root,data,options);root.querySelector('.tool-name button').click();await until(()=>root.textContent.includes('History 2'));assert.equal(requests,2);
  tab(root,'lifecycle').click();assert.match(root.textContent,/Adopted for trials · benefit not established/);assert.match(root.textContent,/Not dispatched · no actual use/);assert.match(root.querySelector('.cell-stage-counts').textContent,/0Later invocations/);
 }finally{dom.window.close();}
});


test('declared tool errors are visible without relabeling archived raw outputs',async()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.invocations=[
   {tool_id:id,receipt_id:receipt,phase:'invocation_result',island_id:0,status:'ok',dispatch_status:'invoked',result_schema:'sciel-tool-result/1',tool_result_status:'tool_error'},
   {tool_id:id,receipt_id:'c'.repeat(64),phase:'invocation_result',island_id:1,status:'ok',dispatch_status:'invoked'}];
  w.renderResearchTools(root,data,{runId:'run',fetchJSON:async()=>({verified:true,kind:'invocation',payload:{result:{schema:'sciel-tool-result-assessment/1',status:'tool_error',host_status:'ok',error:'namespace missing'},receipt:{status:'ok',output:{error:'namespace missing'}}}})});
  tab(root,'invocations').click();
  assert.match(root.querySelector('.tools-table').textContent,/Tool error · check failed/);
  assert.match(root.querySelector('.tools-table').textContent,/ok/);
  const rows=[...root.querySelectorAll('.tools-table tbody tr')];
  rows.find(row=>row.textContent.includes('Tool error')).querySelector('td:last-child button').click();
  await until(()=>root.textContent.includes('Tool outcome · separate from Python execution'));
  assert.match(root.textContent,/namespace missing/);
 }finally{dom.window.close();}
});

test('independent execution never claims reproduced measurements',()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.lifecycle={recorded:true,counts:{matched_replays:1},events:[{phase:'replay_result',cell_id:'c'.repeat(64),tool_id:id,receipt_id:receipt,island_id:1,matched:true,replay_policy:'independent_execution',measurement_reproduced:false}]};
  w.renderResearchTools(root,data,{runId:'run'});tab(root,'lifecycle').click();
  assert.match(root.querySelector('.tools-table').textContent,/Independent execution verified · measurements may differ/);
  assert.doesNotMatch(root.querySelector('.tools-table').textContent,/reproduced/);
 }finally{dom.window.close();}
});

test('failed input source, ancestry and available champion remain distinct',async()=>{
 const {dom,w,root}=mount();try{
  const data=fixture(),binding={candidate_id:null,target_kind:'failed_candidate',target_source_sha256:'d'.repeat(64),ancestry_parent_id:'p1',population_best_id:'p8'};
  data.invocations=[{tool_id:id,receipt_id:receipt,phase:'invocation_result',island_id:0,status:'ok',dispatch_status:'invoked',parent_program_id:'p1',target_binding:binding}];
  const targets={schema:'sciel-research-targets/1',selected:{kind:'failed_candidate',program_id:null,source_sha256:'d'.repeat(64),source:'<script>failed code</script>'},ancestry_parent:{program_id:'p1'},population_best:{program_id:'p8',source_sha256:'e'.repeat(64)}};
  w.renderResearchTools(root,data,{runId:'run',fetchJSON:async()=>({verified:true,kind:'invocation',payload:{inputs:{research_targets:targets},receipt:{status:'ok'}}})});
  tab(root,'invocations').click();const table=root.querySelector('.tools-table');
  assert.match(table.textContent,/Failed candidate · dddddddddddd/);assert.match(table.textContent,/Ancestry p1/);assert.doesNotMatch(table.textContent,/Input p1/);
  [...root.querySelectorAll('button')].find(n=>n.textContent==='Open exact inputs & output').click();await until(()=>root.querySelector('.tool-input-sources'));
  const sources=root.querySelector('.tool-input-sources');assert.match(sources.textContent,/no admitted program ID/);assert.match(sources.textContent,/Available best reference/);assert.match(sources.textContent,/p8 · SHA256 eeeeeeeeeeee/);assert.match(sources.textContent,/does not prove which source/);assert.equal(sources.querySelector('details').open,false);assert.equal(root.querySelector('script'),null);
 }finally{dom.window.close();}
});


test('canonical producer links retain record kind and expose the exact evaluator separately from observations',async()=>{
 const {dom,w,root}=mount();try{
  const data=fixture(),canonical='c'.repeat(64),paths=[];
  data.child_links=[{child_program_id:'p29',link_kind:'remeasurement',link_basis:'canonical_candidate_source',tool_ids:[id],receipt_ids:[receipt],canonical_evaluation_id:canonical,evaluation_id:'physical-123',candidate_source_sha256:'d'.repeat(64)},
   {child_program_id:'p30',link_kind:'mutation',link_basis:'observations_before_generation',tool_ids:[id],receipt_ids:[receipt]}];
  w.renderResearchTools(root,data,{runId:'run',fetchJSON:async path=>{paths.push(path);return {verified:true,kind:'candidate_evaluation',payload:{source:'# exact candidate <script>',evaluation:{status:'evaluated',evaluation_id:'physical-123'},provenance:{receipt_id:receipt}}};}});
  tab(root,'links').click();assert.match(root.textContent,/Canonical producer · Remeasurement/);assert.match(root.textContent,/Observations before generation · Mutation/);
  [...[...root.querySelectorAll('tbody tr')].find(n=>n.textContent.includes('p29')).querySelectorAll('button')].find(n=>n.textContent==='Inspect').click();assert.match(root.textContent,/not a new program/);assert.match(root.textContent,/Method benefit and cross-branch transfer are not established/);
  [...root.querySelectorAll('button')].find(n=>n.textContent==='Open canonical evaluator record').click();await until(()=>root.textContent.includes('physical-123'));
  assert.deepEqual(paths,['/api/runs/run/research-tool-artifacts/'+canonical]);assert.match(root.textContent,/Exact submitted candidate source/);assert.match(root.textContent,/# exact candidate <script>/);assert.equal(root.querySelector('script'),null);
 }finally{dom.window.close();}
});
