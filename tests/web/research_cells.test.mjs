import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source=readFileSync(new URL('../../web/research_cells.js',import.meta.url),'utf8').replace(/^export /gm,'');
const cell='a'.repeat(64),other='b'.repeat(64),tool='c'.repeat(64),receipt='d'.repeat(64),proposal='e'.repeat(64),job='f'.repeat(64);
const pause=()=>new Promise(resolve=>setTimeout(resolve,5));
async function until(predicate){for(let n=0;n<100;n++){if(predicate())return;await pause();}assert.fail('DOM did not update');}
function mount(){const dom=new JSDOM('<main id="root"></main>',{runScripts:'outside-only',pretendToBeVisual:true});dom.window.eval('{'+source+';window.renderResearchCells=renderResearchCells;}');return {dom,w:dom.window,root:dom.window.document.getElementById('root')};}
function row(id=cell){return {id,head_revision:'1'.repeat(64),detail_version:'initial',question:'Investigate a candidate <img src=x>',affinities:[0],scheduled:false,activity_status:'activity_recorded',stage:'research',created_at:'2026-09-20T08:00:00Z',last_activity_at:'2026-09-20T08:02:00Z',state_source:'checkpoint',counts:{followups:1}};}
function fixture(){return {configuration:{status:'enabled',enabled:true},configured:{enabled:true},summary:{cells:1,versions:1},cells:[row()],jobs:{version:'one',summary:{total:1},items:[]}};}
function detail(id=cell){return {verified:true,kind:'cell',id,genesis:{origin_island:0,question:'A durable research question <script>untrusted</script>',trigger:{kind:'proactive'}},revision_history:[{id:'1'.repeat(64),ordinal:1,phase:'propose',summary:'Question opened',tool_ids:[tool]}],related:{versions:[{id:tool,name:'Probe <img src=x>',status:'registered',replay_policy:'independent_execution'}],invocations:[{id:'invocation',invocation_id:'invocation',receipt_id:receipt,tool_id:tool,status:'ok',dispatch_status:'invoked',tool_result_status:'success',stage:'research',timestamp:'2026-09-20T08:01:00Z',resources:{cpu_seconds:0,wall_seconds:1}}],jobs:[],llm_calls:[{action_id:'action',attempt:0,status:'returned',model:'fixture',known_cost:0,receipt_id:proposal,timestamp:'2026-09-20T08:00:00Z'}],child_links:[],lifecycle_events:[],events:[],followups:[]},related_coverage:{versions:{visible:1,omitted:0,verification_failed:0}}};}
function open(w,node){node.open=true;node.dispatchEvent(new w.Event('toggle'));}
const sourceRow=root=>root.querySelector('[data-section="tools"] .rc-record');

test('terminal interpretation is visible separately from execution and hides during a newer pending decision',async()=>{
 const {dom,w,root}=mount();try{
  const body=detail();body.research_state={status:'closed',conclusion:'inconclusive',question:'Was the output feasible?',current_experiment:'Inspect saved geometry.',next_decision:'Repair feasibility checks.',scope:'cell_cumulative',resources:{cpu_seconds:1},steps:[]};
  body.terminal_decision={verified:true,proposal_id:proposal,conclusion:'inconclusive',interpretation:'The reported result is invalid <img src=x>.',next_decision:'Repair feasibility checks.',omitted_chars:{interpretation:20}};
  const data=fixture(),requests=[];
  const options={runId:'terminal',fetchJSON:async path=>{requests.push(path);return path.includes('/research-cells/')?body:{verified:true,kind:'proposal',payload:{prompt:'Saved final planner prompt',response:{text:'Exact terminal response'}}};}};
  w.renderResearchCells(root,data,options);await until(()=>root.querySelector('[data-section="terminal-decision"]'));
  const current=root.querySelector('.rc-research');assert.match(current.textContent,/Model interpretation · inconclusive/);assert.match(current.textContent,/reported result is invalid <img src=x>/);assert.match(current.textContent,/canonical candidate validity are separate/);assert.match(current.textContent,/complete statement is in the saved model response/);assert.equal(current.querySelector('img'),null);
  open(w,root.querySelector('[data-section="terminal-decision"] .rc-record'));await until(()=>root.textContent.includes('Exact terminal response'));assert.ok(requests.some(path=>path.endsWith('/research-tool-artifacts/'+proposal)));
  body.active_decision={proposal_id:'9'.repeat(64),question:'New question',experiment:'New experiment',next_decision:'Measure again.',status:'planned'};
  data.cells[0].detail_version='new-pending';w.renderResearchCells(root,data,options);await until(()=>root.querySelector('.rc-research').textContent.includes('Uncommitted model decision'));
  assert.doesNotMatch(root.querySelector('.rc-research').textContent,/reported result is invalid|Model interpretation · inconclusive/);assert.equal(root.querySelector('[data-section="terminal-decision"]'),null);
 }finally{dom.window.close();}
});

test('disabled, enabled waiting, and unrecorded config are distinct; disabled history remains visible',async()=>{
 const {dom,w,root}=mount();try{
  const options={runId:'vq',fetchJSON:()=>assert.fail('empty states do not fetch')};
  w.renderResearchCells(root,{configuration:{status:'disabled',enabled:false,reason:'Recorded tools.enabled=false'},cells:[]},options);
  assert.equal(root.dataset.configuration,'disabled');assert.match(root.textContent,/Research cells are disabled/);assert.match(root.textContent,/VQ placement and reinforcement learning do not enable/);assert.match(root.textContent,/Recorded tools.enabled=false/);assert.equal(root.querySelector('.rc-workspace').hidden,true);
  w.renderResearchCells(root,{configuration:{status:'enabled',enabled:true},cells:[]},{...options,runId:'labs'});assert.match(root.textContent,/Waiting for the first research cell/);assert.doesNotMatch(root.textContent,/disabled for this run/);
  w.renderResearchCells(root,{}, {...options,runId:'archive'});assert.match(root.textContent,/configuration not recorded/);
  const data=fixture();data.configuration={status:'disabled',enabled:false};w.renderResearchCells(root,data,{runId:'history',fetchJSON:async()=>detail()});await until(()=>root.textContent.includes('Verified cell history'));assert.match(root.textContent,/recorded historical cells remain available/);assert.equal(root.querySelector('.rc-workspace').hidden,false);
 }finally{dom.window.close();}
});

test('first uncommitted cell shows its concrete plan while committed counters remain zero and paused is explicit',async()=>{
 const {dom,w,root}=mount();try{
  const plan={proposal_id:proposal,question:'Does continuing the saved state improve the result?',experiment:'Run another stage from the exact artifact.',next_decision:'Compare measured gains.',decision_if_supported:'Continue.',decision_if_refuted:'Try another start.',status:'awaiting_wave_commit',requested_limits:{cpu_seconds:120,wall_seconds:180}};
  const pending={id:cell,publication:'pending',committed:false,affinities:[0],stage:'propose',detail_version:'pending-one',active_decision:null,pending_decision:plan,current_question:plan.question};
  const data={configuration:{enabled:true,status:'enabled'},summary:{cells:0,versions:0},cells:[],pending_cells:{version:'wave-one',run_status:'paused',cells:[pending]}};
  const body={verified:true,id:cell,kind:'cell',publication:'pending',genesis:{question:'Scheduling context.',origin_island:0},revision_history:[],research_state:null,related:{},active_decision:null,pending_decision:plan,current_question:plan.question};
  w.renderResearchCells(root,data,{runId:'paused',fetchJSON:async()=>body});await until(()=>root.textContent.includes('Authenticated pending wave'));
  assert.equal(root.querySelector('.rc-workspace').hidden,false);
  assert.equal(root.querySelector('.rc-question').textContent,plan.question);
  assert.match(root.textContent,/Run another stage from the exact artifact/);assert.match(root.textContent,/Compare measured gains/);
  assert.match(root.textContent,/Pending wave · paused/);assert.match(root.textContent,/No running computation is implied/);
  assert.match(root.querySelector('.rc-summary').textContent,/Cells0Scheduled cells0Tool versions0/);
  assert.match(root.querySelector('.rc-research').textContent,/Cell tool CPUUnknown/);
  assert.match(root.textContent,/120\.000 s/);assert.match(root.textContent,/awaiting wave commit/);
  assert.equal(data.cells.length,0);assert.equal(data.summary.cells,0);
  data.pending_cells={version:'withdrawn',run_status:'paused',cells:[]};w.renderResearchCells(root,data,{runId:'paused',fetchJSON:async()=>assert.fail('withdrawn cell must not fetch')});
  assert.equal(root.querySelector('.rc-workspace').hidden,true);assert.match(root.textContent,/Waiting for the first research cell/);
 }finally{dom.window.close();}
});

test('cell metadata loads first; source/diff and model exchanges are lazy and rendered only as text',async()=>{
 const {dom,w,root}=mount();try{
  const requests=[];const options={runId:'run 1',identity:'science',fetchJSON:async path=>{requests.push(path);if(path.includes('/research-cells/'))return detail();if(path.includes('/research-tools/'))return {verified:true,files:{'tool.py':'# <script>source</script>\ndef run(payload): return 0'},manifest:{name:'probe'},parents:[{id:other,verified:true,diff:'- old\n+ <img src=x>'}]};return {verified:true,kind:'proposal',payload:{prompt:'exact <script>request</script>',response:{text:'<img src=x>response',cost:0}}};}};
  w.renderResearchCells(root,fixture(),options);await until(()=>sourceRow(root));assert.equal(requests.length,1);assert.match(requests[0],/run%201\/research-cells\/a{64}$/);
  open(w,sourceRow(root));await until(()=>root.textContent.includes('def run(payload)'));assert.equal(requests.length,2);assert.match(requests[1],/research-tools\/c{64}$/);assert.match(root.textContent,/Diff from bbbbb/);
  open(w,root.querySelector('[data-section="models"] .rc-record'));await until(()=>root.textContent.includes('exact <script>request</script>'));assert.match(requests[2],/research-tool-artifacts\/e{64}$/);assert.equal(root.querySelectorAll('script,img').length,0);assert.match(root.textContent,/\$0\.000000/);
  const time=root.querySelector('time');assert.equal(time.title,'2026-09-20T08:00:00Z');assert.match(time.textContent,/UTC|GMT|GST/);
 }finally{dom.window.close();}
});

test('unverified artifact bodies are refused instead of presenting their source',async()=>{
 const {dom,w,root}=mount();try{
  w.renderResearchCells(root,fixture(),{runId:'run',fetchJSON:async path=>path.includes('/research-cells/')?detail():{verified:false,files:{'tool.py':'forged source'}}});await until(()=>sourceRow(root));open(w,sourceRow(root));await until(()=>root.textContent.includes('Saved content unavailable'));assert.doesNotMatch(root.textContent,/forged source/);
 }finally{dom.window.close();}
});

test('model wire text is unchanged and softly wrapped; metadata and exact response stay closed',async()=>{
 const {dom,w,root}=mount();try{
  const prompt='  First line\n\nПроверка <script>unsafe()</script>\t'+ 'x'.repeat(300);
  const response={text:'  Actual response\n{"code":"line1\\nline2"}\n<img src=x> & café\n',model:'recorded-model',finish_reason:'stop',usage:{output_tokens:17},cost:0};
  const css=w.document.createElement('style');css.textContent=readFileSync(new URL('../../web/research_cells.css',import.meta.url),'utf8');w.document.head.append(css);
  w.renderResearchCells(root,fixture(),{runId:'run',fetchJSON:async path=>path.includes('/research-cells/')?detail():path.includes('/research-tools/')?{verified:true,files:{'tool.py':'def run(payload):\n    return "'+ 'x'.repeat(300)+'"'},manifest:{},parents:[]}:{verified:true,kind:'proposal',payload:{prompt,response}}});
  await until(()=>root.querySelector('[data-section="models"] .rc-record'));const record=root.querySelector('[data-section="models"] .rc-record');open(w,record);await until(()=>record.querySelectorAll('.rc-model-text').length===2);
  const texts=record.querySelectorAll('.rc-model-text');assert.equal(texts[0].textContent,prompt);assert.equal(texts[1].textContent,response.text);assert.equal(w.getComputedStyle(texts[0]).whiteSpace,'pre-wrap');assert.equal(w.getComputedStyle(texts[1]).overflowWrap,'anywhere');assert.equal(record.querySelectorAll('script,img').length,0);
  const panels=[...record.querySelectorAll('.rc-panel')],metadata=panels.find(n=>n.firstChild.textContent==='Response metadata'),exact=panels.find(n=>n.firstChild.textContent==='Exact saved response');assert.equal(metadata.open,false);assert.equal(exact.open,false);assert.deepEqual(JSON.parse(metadata.querySelector('pre').textContent),{model:'recorded-model',finish_reason:'stop',usage:{output_tokens:17},cost:0});assert.deepEqual(JSON.parse(exact.querySelector('pre').textContent),response);
  open(w,sourceRow(root));await until(()=>sourceRow(root).querySelector('pre'));const code=sourceRow(root).querySelector('pre');assert.equal(code.classList.contains('rc-model-text'),false);assert.equal(w.getComputedStyle(code).whiteSpace,'pre');
 }finally{dom.window.close();}
});

test('legacy string responses remain literal; absent response text is explicit with saved metadata retained',async()=>{
 const {dom,w,root}=mount();try{
  const options={runId:'legacy',fetchJSON:async path=>path.includes('/research-cells/')?detail():{verified:true,kind:'proposal',payload:{prompt:'request',response:'legacy\nresponse <b>literal</b>'}}};
  w.renderResearchCells(root,fixture(),options);await until(()=>root.querySelector('[data-section="models"] .rc-record'));open(w,root.querySelector('[data-section="models"] .rc-record'));await until(()=>root.querySelectorAll('.rc-model-text').length===2);assert.equal(root.querySelectorAll('.rc-model-text')[1].textContent,'legacy\nresponse <b>literal</b>');assert.equal(root.querySelector('b'),null);
  w.renderResearchCells(root,fixture(),{...options,runId:'missing',fetchJSON:async path=>path.includes('/research-cells/')?detail():{verified:true,kind:'proposal',payload:{prompt:'request',response:{finish_reason:'error',text:null}}}});await until(()=>root.querySelector('[data-section="models"] .rc-record'));open(w,root.querySelector('[data-section="models"] .rc-record'));await until(()=>root.textContent.includes('Response text not recorded.'));assert.equal(root.querySelectorAll('.rc-model-text').length,1);assert.match(root.textContent,/finish_reason/);
 }finally{dom.window.close();}
});

test('a late cell response cannot populate a switched run',async()=>{
 const {dom,w,root}=mount();try{
  let resolve;w.renderResearchCells(root,fixture(),{runId:'old',fetchJSON:()=>new Promise(r=>{resolve=r;})});await until(()=>resolve);
  w.renderResearchCells(root,{configuration:{status:'disabled',enabled:false},cells:[]},{runId:'new',fetchJSON:()=>assert.fail('disabled run fetch')});resolve(detail());await pause();await pause();assert.match(root.textContent,/Research cells are disabled/);assert.doesNotMatch(root.textContent,/durable research question/);assert.equal(root.querySelector('.rc-detail'),null);
 }finally{dom.window.close();}
});

test('selected cell, source DOM, focus, open state and scroll survive changed metadata polling',async()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.cells.push({...row(other),question:'Other question',affinities:[1]});data.summary.cells=2;const requests=[];
  const options={runId:'run',fetchJSON:async path=>{requests.push(path);return path.includes('/research-cells/')?detail(path.split('/').at(-1)):{verified:true,files:{'tool.py':'source\n'.repeat(100)},manifest:{},parents:[]};}};
  w.renderResearchCells(root,data,options);await until(()=>sourceRow(root));root.querySelector('[data-cell-id="'+cell+'"].rc-cell-row').click();await until(()=>root.querySelector('.rc-detail').dataset.cellId===cell&&sourceRow(root));open(w,sourceRow(root));await until(()=>root.querySelector('.rc-artifact pre'));
  const pre=root.querySelector('.rc-artifact pre'),record=sourceRow(root);pre.scrollTop=77;pre.scrollLeft=12;pre.focus();const nested=pre.parentElement;nested.open=false;
  data.cells[0].detail_version='new';data.cells[0].last_activity_at='2026-09-20T08:05:00Z';w.renderResearchCells(root,data,options);await until(()=>root.querySelector('time[title="2026-09-20T08:05:00Z"]'));
  assert.equal(root.querySelector('.rc-detail').dataset.cellId,cell);assert.strictEqual(root.querySelector('.rc-artifact pre'),pre);assert.strictEqual(w.document.activeElement,pre);assert.equal(pre.scrollTop,77);assert.equal(pre.scrollLeft,12);assert.equal(record.open,true);assert.equal(nested.open,false);assert.equal(requests.filter(p=>p.includes('/research-tools/')).length,1);
 }finally{dom.window.close();}
});

test('polling while an immutable body loads neither duplicates nor loses the response',async()=>{
 const {dom,w,root}=mount();try{
  let resolve;let sourceCalls=0;const data=fixture();const options={runId:'run',fetchJSON:path=>path.includes('/research-cells/')?Promise.resolve(detail()):(sourceCalls++,new Promise(r=>{resolve=r;}))};
  w.renderResearchCells(root,data,options);await until(()=>sourceRow(root));open(w,sourceRow(root));await until(()=>resolve);data.cells[0].detail_version='changed';w.renderResearchCells(root,data,options);await pause();resolve({verified:true,files:{'tool.py':'pending response retained'},manifest:{},parents:[]});await until(()=>root.textContent.includes('pending response retained'));assert.equal(sourceCalls,1);
 }finally{dom.window.close();}
});

test('job-only refresh fetches terminal receipt and preserves open details and scroll',async()=>{
 const {dom,w,root}=mount();try{
  const data=fixture(),jobRow={id:job,status:'running',phase:'waiting_for_capacity',requested:{cpu_seconds:20,wall_seconds:30},actual:{cpu_seconds:null},receipt_id:null,updated_at:'2026-09-20T08:00:00Z'};const requests=[];
  const options={runId:'run',fetchJSON:async path=>{requests.push(path);if(path.includes('/research-cells/')){const d=detail();d.related.jobs=[{...jobRow}];return d;}return {verified:true,kind:'job',request:{inputs:{seed:0}},snapshot:{status:jobRow.status},receipt:jobRow.receipt_id?{status:'ok',output:{status:'success',observations:{answer:0}},resources:{cpu_seconds:0,wall_seconds:1}}:null};}};
  w.renderResearchCells(root,data,options);await until(()=>root.querySelector('[data-section="jobs"] .rc-record'));const row=root.querySelector('[data-section="jobs"] .rc-record');open(w,row);await until(()=>row.textContent.includes('No terminal execution receipt'));const inputPanel=[...row.querySelectorAll('details')].find(n=>n.firstChild.textContent==='Exact saved inputs');inputPanel.open=true;const pre=inputPanel.querySelector('pre');pre.scrollTop=41;
  jobRow.status='completed';jobRow.phase='terminal';jobRow.receipt_id=receipt;jobRow.updated_at='2026-09-20T08:01:00Z';jobRow.actual.cpu_seconds=0;data.jobs.version='two';w.renderResearchCells(root,data,options);await until(()=>row.textContent.includes('"answer": 0'));
  assert.equal(row.open,true);const nextInputs=[...row.querySelectorAll('details')].find(n=>n.firstChild.textContent==='Exact saved inputs');assert.equal(nextInputs.open,true);assert.equal(nextInputs.querySelector('pre').scrollTop,41);assert.match(row.textContent,/Measured CPU \/ requested0\.000 s \/ Unknown/);assert.equal(requests.filter(p=>p.includes('/research-cells/')).length,2);assert.equal(requests.filter(p=>p.includes('/research-tool-jobs/')).length,2);
 }finally{dom.window.close();}
});

test('search/filter preserve selection and do not manufacture failed outcomes',async()=>{
 const {dom,w,root}=mount();try{
  const data=fixture();data.cells.push({...row(other),question:'Independent replay',scheduled:true,stage:'independent_replay',affinities:[2]});const options={runId:'run',fetchJSON:async()=>detail(other)};
  w.renderResearchCells(root,data,options);await until(()=>sourceRow(root));const search=root.querySelector('.rc-search');search.value='island 2';search.dispatchEvent(new w.Event('input'));assert.equal(root.querySelectorAll('.rc-cell-row').length,1);assert.equal(root.querySelector('.rc-cell-row').dataset.cellId,other);assert.match(root.querySelector('.rc-cell-row').textContent,/Scheduled/);assert.match(root.querySelector('.rc-summary').textContent,/Scheduled cells/);assert.doesNotMatch(root.textContent,/Active lease/);
  const filter=root.querySelector('.rc-filter');filter.value='issues';filter.dispatchEvent(new w.Event('change'));assert.match(root.querySelector('.rc-list').textContent,/No matching cells/);assert.equal(root.querySelector('.rc-detail').dataset.cellId,other);assert.doesNotMatch(root.textContent,/No solutions/);
 }finally{dom.window.close();}
});

test('followups retain unknown benefit and controller-score semantics without inferring validity',async()=>{
 const {dom,w,root}=mount();try{
  let selected=null;const d=detail();d.related.followups=[{id:'followup',experiment_id:'r1',iteration:1,outcome_status:'evaluated',child_program_id:'p1',score:0,actual_delta:0,generation:{dispatch:'returned'},score_scope:'Recorded controller-score units, not inferred native measurements or method benefit.',model_use:'unknown',causal_benefit:'unknown',canonical_evaluation:{ok:true,score:0,reached:'full',cases:{validity:0}}}];
  w.renderResearchCells(root,fixture(),{runId:'run',fetchJSON:async()=>d,onProgram:id=>{selected=id;}});await until(()=>root.querySelector('[data-section="outcomes"] .rc-record'));const outcome=root.querySelector('[data-section="outcomes"] .rc-record');open(w,outcome);assert.match(outcome.textContent,/Evaluation returned/);assert.doesNotMatch(outcome.textContent,/returned valid|native score/i);assert.match(outcome.textContent,/Controller score0/);assert.match(outcome.textContent,/causal benefit remain unknown/);outcome.querySelector('.rc-program').click();assert.equal(selected,'p1');
 }finally{dom.window.close();}
});

test('bounded omissions and verification failures remain visible',async()=>{
 const {dom,w,root}=mount();try{
  const d=detail();d.history_truncated=true;d.next_revision_id=other;d.related.invocations=[];d.related_coverage={followups:{omitted:3,verification_failed:1},invocations:{omitted:0,verification_failed:2}};w.renderResearchCells(root,fixture(),{runId:'run',fetchJSON:async()=>d});await until(()=>root.textContent.includes('3 older records omitted'));assert.match(root.textContent,/1 records unavailable or failed verification/);assert.match(root.textContent,/Older revisions omitted by the read bound/);const executions=root.querySelector('[data-section=executions]');assert.match(executions.textContent,/2 records unavailable or failed verification/);assert.doesNotMatch(executions.textContent,/No execution receipt recorded/);assert.match(root.querySelector('[data-section=outcomes]').textContent,/1 records unavailable or failed verification/);
 }finally{dom.window.close();}
});

test('current concrete question and decision branches replace scheduling boilerplate; exact stage evidence stays lazy',async()=>{
 const {dom,w,root}=mount();try{
  const d=detail(),requests=[];d.current_question='Does another search stage improve the saved incumbent?';d.research_state={question:d.current_question,current_experiment:'Continue the exact saved state for 60 CPU seconds.',decision_if_supported:'Retain the continuation and evaluate its output.',decision_if_refuted:'Try an independent starting state.',next_decision:'Compare improvement per CPU second.',status:'open',conclusion:null,scope:'cell_cumulative',scientific_steps:2,known_llm_cost:0,unknown_llm_calls:1,resources:{cpu_seconds:0,wall_seconds:1,unknown_cpu_invocations:1},steps:[{action_id:'a1',proposal_id:proposal,receipt_id:receipt,tool_id:tool,action:'execute',status:'success',experiment:'Continue the saved state.',next_decision:'Compare measurements.',requested_limits:{cpu_seconds:60},resources:{cpu_seconds:0},observed_at:'2026-09-20T08:01:00Z'}],steps_omitted:1};
  const data=fixture();data.cells[0].research_state=d.research_state;
  w.renderResearchCells(root,data,{runId:'episode',fetchJSON:async path=>{requests.push(path);return path.includes('/research-cells/')?d:{verified:true,kind:'proposal',payload:{prompt:'Exact stage request',response:{text:'Exact stage response'}}};}});
  await until(()=>root.querySelector('[data-section="steps"]'));
  assert.equal(root.querySelector('.rc-question').textContent,d.current_question);assert.equal(root.querySelector('.rc-cell-question').textContent,d.current_question);
  const current=root.querySelector('.rc-research');assert.match(current.textContent,/If supportedRetain the continuation/);assert.match(current.textContent,/If refutedTry an independent/);assert.match(current.textContent,/Cell model cost · known\$0\.000000/);assert.match(current.textContent,/Cell tool CPU0\.000 s/);assert.match(current.textContent,/1 model calls with unknown cost/);assert.match(current.textContent,/1 executions with unknown CPU/);assert.doesNotMatch(current.textContent,/A durable research question/);
  assert.match(root.querySelector('[data-section="origin"]').textContent,/A durable research question/);assert.match(root.querySelector('[data-section="steps"]').textContent,/1 earlier steps omitted/);assert.equal(requests.length,1);
  const model=root.querySelector('[data-section="steps"] [data-id="'+proposal+'"]');open(w,model);await until(()=>model.textContent.includes('Exact stage request'));assert.equal(requests.length,2);
 }finally{dom.window.close();}
});

test('historical verified experiment question takes precedence over genesis without fabricating a decision plan',async()=>{
 const {dom,w,root}=mount();try{
  const d=detail();d.current_question='Do the saved coordinates satisfy the boundary constraints?';d.question_scope='Last verified experiment question';
  w.renderResearchCells(root,fixture(),{runId:'archive',fetchJSON:async()=>d});await until(()=>root.textContent.includes('Verified cell history'));
  assert.equal(root.querySelector('.rc-question').textContent,d.current_question);assert.match(root.querySelector('.rc-research').textContent,/structured research plan was not recorded/);assert.equal(root.querySelector('.rc-decisions'),null);assert.match(root.querySelector('[data-section="origin"]').textContent,/A durable research question/);
 }finally{dom.window.close();}
});

test('pending decision shows actual current question and planned work without adding committed usage',async()=>{
 const {dom,w,root}=mount();try{
  const d=detail(),data=fixture();d.research_state={question:'Previous committed question',current_experiment:'Earlier experiment',status:'closed',conclusion:'supported',scope:'cell_cumulative',scientific_steps:1,known_llm_cost:.4,resources:{cpu_seconds:2,wall_seconds:3},steps:[]};
  d.active_decision={action:'create',status:'awaiting_execution_receipt',proposal_id:proposal,question:'Can a longer continuation improve the saved state?',experiment:'Continue the saved state for 60 CPU seconds.',decision_if_supported:'Continue',decision_if_refuted:'Try a different start',next_decision:'Inspect the measured gain.',requested_limits:{cpu_seconds:60},committed:false};data.cells[0].active_decision=d.active_decision;
  const options={runId:'pending',fetchJSON:async()=>d};w.renderResearchCells(root,data,options);await until(()=>root.querySelector('[data-section="pending"]'));
  assert.equal(root.querySelector('.rc-question').textContent,d.active_decision.question);const current=root.querySelector('.rc-research');assert.match(current.textContent,/Uncommitted model decision/);assert.match(current.textContent,/Continue the saved state for 60 CPU seconds/);assert.match(current.textContent,/Cell model cost · known\$0\.400000/);assert.match(current.textContent,/Cell tool CPU2\.000 s/);assert.doesNotMatch(current.textContent,/Planner conclusion: supported/);assert.match(root.querySelector('[data-section="steps"]').textContent,/No completed scientific step/);
  d.active_decision=null;data.cells[0].detail_version='settled';w.renderResearchCells(root,data,options);await until(()=>!root.querySelector('[data-section="pending"]'));
  // A newer detail response explicitly clearing pending work wins over an older list row.
  assert.equal(root.querySelector('.rc-question').textContent,'Previous committed question');assert.doesNotMatch(root.querySelector('.rc-research').textContent,/Uncommitted model decision/);
 }finally{dom.window.close();}
});
