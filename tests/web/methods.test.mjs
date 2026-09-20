import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const assets = new URL(process.env.ARENA_WEB_ASSETS || '../../web/', import.meta.url);
const source = readFileSync(new URL('methods.js', assets), 'utf8').replace(/^import .*$/gm, '').replace(/export function /g, 'function ');
function fixture() {
  return {kind:'methods',content_version:'v1',run:{id:'campaign',kind:'methods',name:'A/B/C pilot',status:'running',task:'sciel-method-circle26-task/1'},runtime:{active:true,stale_after_seconds:30,heartbeat_age_seconds:0},timing:{live:true,session:{elapsed_seconds:120}},methods:{
    summary:{labs:3,methods:2,released:1,experiments:1,proposals:1,invocations:3,unknown:1},
    budget:{spent:{dollars:0,cpu_seconds:2,gpu_seconds:0,wall_seconds:5,storage_bytes:900,steps:1},reserved:{dollars:0.05},remaining:{dollars:9.95},limits:{dollars:10}},
    labs:[{id:'lab-a',mode:'A',agenda:'Fixed common methods',status:'active',revision_id:'revision1',revision_number:1,steps:0,active_methods:['tool1'],active_adapters:[]},{id:'lab-b',mode:'B',agenda:'Improve a tool',status:'active',revision_id:'revision2',revision_number:2,steps:2,active_methods:['tool2'],active_adapters:[]},{id:'lab-c',mode:'C',agenda:'Transfer useful methods',status:'active',revision_id:'revision3',revision_number:3,steps:1,active_methods:['tool2'],active_adapters:[]}],
    tools:[{id:'tool1',name:'Common baseline',kind:'constructor',status:'released',parents:[],dependencies:[],invocations:2},{id:'tool2',name:'<img src=x onerror=alert(1)>',kind:'constructor',status:'draft',author_lab:'lab-b',parents:['tool1'],dependencies:['tool1'],invocations:1,adopted_by:['lab-c']}],
    experiments:[{id:'experiment1',lab_id:'lab-b',purpose:'local',question:'Can the repaired method help?',passed:false,effect:0,control_score:0,treatment_score:0,treatment:['tool2'],control:['tool1'],criterion:{minimum_effect:0.01},results:{control:[{score:0}],treatment:[{score:0}]},invocation_refs:['actual-call']}],
    proposals:[{id:'proposal1',lab_id:'lab-b',index:0,kind:'MethodDraft',status:'completed',cost:0,method_id:'tool2',experiment_id:'experiment1'}],
    transfers:[{id:'adoption1',lab_id:'lab-c',method_id:'tool2',new_revision:'revision3',next_use_experiment_id:null}],events:[],claims:[]}};
}
function mount(fetchJSON=async()=>({files:{'main.py':'return "<script>"'},manifest:{},diff:'- old\n+ new'})) {
  const dom = new JSDOM('<main><section id="view"></section></main>', {runScripts:'outside-only',pretendToBeVisual:true});
  for (const [file, names] of [['methods_progress.js', ['renderMethodsProgress']], ['methods_atlas.js', ['renderMethodsPopulation', 'renderMethodsArchitecture']]]) {
    const module = readFileSync(new URL(file, assets), 'utf8').replace(/^export /gm, '');
    dom.window.eval('Object.assign(window, (() => {' + module + '; return {' + names.join(',') + '}; })());');
  }
  const workflowCalls=[], workflowDestroys=[];
  dom.window.renderWorkFlow=(node,options)=>{workflowCalls.push({node,options});if(!node.firstChild){const details=dom.window.document.createElement('details');details.innerHTML='<summary>Saved request</summary><pre>Prompt fixture</pre>';node.append(details);}};
  dom.window.destroyWorkFlow=node=>{workflowDestroys.push(node);node.replaceChildren();};
  dom.window.eval(source+'; window.renderMethodsDashboard=renderMethodsDashboard; window.updateMethodsTiming=updateMethodsTiming; window.destroyMethodsDashboard=destroyMethodsDashboard;');
  const root=dom.window.document.querySelector('#view');
  const render = snapshot=>dom.window.renderMethodsDashboard(root,snapshot,{fetchJSON});
  return {dom,root,render,w:dom.window,workflowCalls,workflowDestroys};
}
const findButton=(root,label)=>[...root.querySelectorAll('[data-methods-tab]')].find(node=>node.dataset.label===label) || [...root.querySelectorAll('button')].find(node=>node.textContent===label);
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));

function observedFixture(){
  const snapshot=fixture();
  snapshot.methods.observability={
    programs:{accepted_programs:0,submitted_solution_actions:0,invoked_solution_experiments:0,refused_solution_actions:0,failed_solution_experiments:0,invalid_solution_experiments:0,nonaccepted_solution_evaluations:0,unclassified_proposals:0,status:'no_recorded_solution_actions',history_complete:true},
    hypotheses:{count:2,items:[{id:'plan1',lab_id:'lab-b',question:'Can the mechanism improve this input?',purpose:'local',criterion:{metric:'combined_score',direction:'max',minimum_effect:0},treatment:['tool2'],control:['tool1'],experiment_ids:['experiment1'],status:'evaluated'},{id:'plan-pending',lab_id:'lab-a',question:'Will this pending plan help?',purpose:'local',criterion:{minimum_effect:0},experiment_ids:[],status:'planned'}]},
    knowledge:{stored_records:10,active_referenced_records:4,stored_claims:1,current_claims:1,active_referenced_claims:0,prompt_delivery:{count:null,status:'unavailable',reason:'Active evidence does not prove prompt delivery.'},legacy_lessons:{count:null,status:'not_implemented',reason:'This runner records claims and evidence; no legacy Lesson cards.'}},
    features:[{id:'bandits',label:'Bandit controller',enabled:false,status:'not_implemented',reason:'No learned bandit controller.'},{id:'rl',label:'RL controller',enabled:false,status:'not_implemented',reason:'No RL policy updates.'}]
  };
  return snapshot;
}

test('familiar summary and tabs retain actual Programs and distinguish stored knowledge from Lessons',()=>{
  const {dom,root,render}=mount();try{
    const snapshot=observedFixture();snapshot.methods.summary.experiments=500;render(snapshot);
    const facts=root.querySelector('.methods-summary').textContent;
    assert.match(facts,/Session time00:02:00/);assert.match(facts,/Sum of radii—/);
    assert.match(facts,/Programs evaluated0/);assert.match(facts,/Stored active knowledge10 \/ 4/);
    assert.equal(findButton(root,'Programs').textContent,'Programs (0)');
    assert.equal(findButton(root,'Hypotheses').textContent,'Hypotheses (2)');
    assert.equal(findButton(root,'Lessons').textContent,'Lessons (—)');
    for(const label of ['Architecture','Code & diff','LLM calls','Work Flow','Events','Population','Bandits & RL','Tool library','Experiments','Adoptions'])assert.ok(findButton(root,label));
    findButton(root,'Programs').click();assert.match(root.querySelector('.methods-record-content').textContent,/No solution proposal has been submitted/);
  }finally{dom.window.close();}
});

test('Programs empty state separates unknown submissions and failed trial dispatch from accepted evaluations',()=>{
  const {dom,root,render}=mount();try{
    const snapshot=observedFixture(),programs=snapshot.methods.observability.programs;
    programs.status='submission_unavailable';programs.unclassified_proposals=3;
    render(snapshot);findButton(root,'Programs').click();
    assert.match(root.querySelector('.methods-record-content').textContent,/No validated solution proposal recorded/);
    assert.doesNotMatch(root.querySelector('.methods-record-content').textContent,/No solution proposal has been submitted/);
    Object.assign(programs,{status:'requested_no_accepted_program',submitted_solution_actions:1,invoked_solution_experiments:1,failed_solution_experiments:1});render(snapshot);
    assert.match(root.querySelector('.methods-record-content').textContent,/Solution requested; no accepted Program yet/);
    assert.match(root.querySelector('.methods-record-content').textContent,/Solution trials invoked1/);
    assert.match(root.querySelector('.methods-summary').textContent,/Programs evaluated0/);
    programs.status='history_incomplete';programs.submitted_solution_actions=0;render(snapshot);
    assert.match(root.querySelector('.methods-record-content').textContent,/Program history is incomplete/);
  }finally{dom.window.close();}
});

test('Hypotheses exposes saved experiment questions, including pending plans and exact zero criteria',()=>{
  const {dom,root,render}=mount();try{
    render(observedFixture());findButton(root,'Hypotheses').click();
    const content=root.querySelector('.methods-record-content');
    assert.match(content.textContent,/Experiment questions/);assert.match(content.textContent,/These are not legacy H cards/);
    assert.match(content.textContent,/No result recorded/);findButton(root,'plan-pending').click();
    assert.match(root.querySelector('.methods-inspector').textContent,/Precommitted experiment plan/);
    assert.match(root.querySelector('.methods-inspector').textContent,/"minimum_effect": 0/);
    findButton(root,'plan1').click();findButton(root.querySelector('.methods-inspector'),'experiment1').click();
    assert.match(root.querySelector('.methods-inspector').textContent,/Can the repaired method help/);
  }finally{dom.window.close();}
});

test('Lessons shows separate claim evidence and never equates active references with prompt delivery',()=>{
  const {dom,root,render}=mount();try{
    const snapshot=observedFixture();snapshot.methods.claims=[{id:'claim1',scope:'Assigned input only',methods:['tool2'],evidence_level:'contract_passed',supporting:['experiment1'],contradicting:[],inconclusive:[]}];
    render(snapshot);findButton(root,'Lessons').click();const content=root.querySelector('.methods-record-content');
    assert.match(content.textContent,/Lesson cards are not produced/);
    assert.match(content.textContent,/Stored evidence10/);assert.match(content.textContent,/Delivered to prompts—/);
    assert.match(content.textContent,/Active evidence does not prove prompt delivery/);
    findButton(root,'claim1').click();assert.match(root.querySelector('.methods-inspector').textContent,/Assigned input only/);
    assert.match(root.querySelector('.methods-inspector').textContent,/Supporting experiments/);
    findButton(root.querySelector('.methods-inspector'),'experiment1').click();assert.match(root.querySelector('.methods-inspector').textContent,/Criterion passedNo/);
  }finally{dom.window.close();}
});

test('Bandits and RL remain explicitly disabled and Code & diff reuses saved source on updates',async()=>{
  let calls=0;const {dom,root,render}=mount(async()=>{calls++;return {files:{'main.py':'def f(): return 1'},diff:'- old\n+ new'};});try{
    const snapshot=observedFixture();render(snapshot);findButton(root,'Bandits & RL').click();
    assert.match(root.querySelector('.methods-record-content').textContent,/Bandits and RL are not enabled/);
    assert.equal(root.querySelector('.methods-record-content svg'),null);
    findButton(root,'Code & diff').click();findButton(root,'Common baseline').click();await tick();
    const holder=root.querySelector('.methods-loaded-detail');holder.querySelector('details').open=true;
    snapshot.methods.tools[0].invocations=12;snapshot.methods.observability.knowledge.stored_records=11;render(snapshot);
    assert.equal(root.querySelector('.methods-loaded-detail'),holder);assert.equal(holder.querySelector('details').open,true);assert.equal(calls,1);
    assert.match(holder.textContent,/Diff from parent- old\n\+ new/);
  }finally{dom.window.close();}
});

test('laboratory dashboard exposes progress and keeps both population and architecture views accessible',()=>{
  const {dom,root,render}=mount();
  try{
    render(fixture());
    assert.match(root.querySelector('[aria-label="Search progress"]').textContent,/Search progress/);
    assert.equal(findButton(root,'Population').getAttribute('aria-selected'),'true');
    assert.ok(root.querySelector('.methods-population-view')?.textContent.length);
    findButton(root,'Architecture').click();
    assert.equal(findButton(root,'Architecture').getAttribute('aria-selected'),'true');
    const architecture=root.querySelector('.methods-architecture-view');
    assert.ok(architecture?.textContent.length);
    render(fixture());assert.equal(root.querySelector('.methods-architecture-view'),architecture);
    findButton(root,'Tool library').click();assert.match(root.querySelector('.methods-record-content').textContent,/Common baseline/);
    findButton(root,'Population').click();assert.ok(root.querySelector('.methods-population-view'));
  }finally{dom.window.close();}
});

test('an invalid proposal is separate from the laboratory activity status',()=>{
  const {dom,root,render}=mount();
  try{
    const snapshot=fixture();snapshot.methods.labs[1].current_stage='continued';
    snapshot.methods.proposals[0].status='invalid';render(snapshot);
    let stage=root.querySelector('[data-lab-id="lab-b"] .methods-lab-stage');
    assert.equal(stage.querySelector('.methods-status').textContent,'Step recorded');
    assert.match(stage.textContent,/Last proposal: invalid format/);
    snapshot.methods.labs[1].current_stage='generation';render(snapshot);
    stage=root.querySelector('[data-lab-id="lab-b"] .methods-lab-stage');
    assert.equal(stage.querySelector('.methods-status').textContent,'Generating proposal');
    assert.match(stage.textContent,/Last proposal: invalid format/);
    snapshot.methods.proposals[0].status='continued';render(snapshot);
    assert.doesNotMatch(root.querySelector('[data-lab-id="lab-b"] .methods-lab-stage').textContent,/invalid/);
  }finally{dom.window.close();}
});

test('architecture live highlights expire with heartbeat freshness and stop when paused',()=>{
  const {dom,root,render,w}=mount();
  try{
    let clock=0;Object.defineProperty(w.performance,'now',{value:()=>clock});
    const snapshot=fixture();snapshot.methods.labs[0].current_stage='generation';snapshot.runtime.stale_after_seconds=5;
    render(snapshot);findButton(root,'Architecture').click();
    assert.ok(root.querySelector('.ma-flow-node.is-active'));
    clock=6000;w.updateMethodsTiming(root);
    assert.equal(root.querySelector('.ma-flow-node.is-active'),null);
    render(snapshot);assert.ok(root.querySelector('.ma-flow-node.is-active'));
    w.updateMethodsTiming(root,{follow:false,connected:true});assert.equal(root.querySelector('.ma-flow-node.is-active'),null);
  }finally{dom.window.close();}
});

test('lab activity distinguishes waiting for capacity from an actual running trial',()=>{
  const {dom,root,render}=mount();
  try{
    const snapshot=fixture();
    snapshot.methods.labs[0].current_stage='capacity_wait';
    snapshot.methods.labs[1].current_stage='execution';
    render(snapshot);
    const waiting=root.querySelector('[data-lab-id="lab-a"] .methods-lab-stage');
    const running=root.querySelector('[data-lab-id="lab-b"] .methods-lab-stage');
    assert.match(waiting.textContent,/Waiting for a shared slot/);
    assert.doesNotMatch(waiting.textContent,/Running trial/);
    assert.match(running.textContent,/Running trial/);
  }finally{dom.window.close();}
});

test('lab projection keeps zero values, exposes unknown budget reserve and never interprets source as HTML',async()=>{
  const {dom,root,render}=mount();
  try{
    render(fixture());
    assert.equal(root.querySelectorAll('.methods-lab').length,3);
    assert.match(root.querySelector('.methods-summary').textContent,/\$0\.0000/);
    assert.match(root.querySelector('.methods-budget').textContent,/1 unknown/);
    assert.equal(root.querySelector('img'),null);
    findButton(root,'Experiments').click();
    assert.match(root.querySelector('.methods-record-content .methods-table').textContent,/0\.000000/);
    findButton(root,'experiment1').click();
    const inspector=root.querySelector('.methods-inspector');
    assert.match(inspector.textContent,/Control score0\.000000Treatment score0\.000000Paired effect0\.000000/);
    assert.match(inspector.textContent,/Criterion passedNo/);
    findButton(root,'Tool library').click();
    findButton(root,'<img src=x onerror=alert(1)>').click();
    await tick();
    assert.match(inspector.textContent,/Diff from parent- old\n\+ new/);
    assert.match(inspector.textContent,/<script>/);
    assert.equal(root.querySelector('script'),null);
  }finally{dom.window.close();}
});

test('lab filtering, adoption pending use, keyboard tabs and saved request response inspection',async()=>{
  const requests=[];
  const {dom,root,render,w}=mount(async url=>{requests.push(url);return {request:{messages:[{content:'exact prompt'}]},response:{text:'exact response'},receipt:{dollars:0}};});
  try{
    render(fixture());findButton(root,'Tool library').click();
    root.querySelector('[data-lab-id="lab-c"]').click();
    assert.match(root.querySelector('.methods-record-content').textContent,/<img/);
    assert.equal(root.querySelectorAll('.methods-record-content tbody tr').length,1);
    findButton(root,'Adoptions').click();
    assert.match(root.querySelector('.methods-record-content').textContent,/Not observed/);
    findButton(root,'All labs').click();
    const tab=findButton(root,'LLM calls');tab.click();tab.focus();
    tab.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
    assert.equal(w.document.activeElement.textContent,'Work Flow');
    assert.equal(w.document.activeElement.getAttribute('aria-selected'),'true');
    findButton(root,'LLM calls').click();findButton(root,'#0 · proposal1').click();await tick();
    assert.deepEqual(requests,['/api/runs/campaign/proposal/proposal1']);
    assert.match(root.querySelector('.methods-inspector').textContent,/exact prompt/);
    assert.match(root.querySelector('.methods-inspector').textContent,/exact response/);
  }finally{dom.window.close();}
});

test('late saved-artifact response cannot overwrite a different selection or run',async()=>{
  let resolve;
  const {dom,root,render}=mount(()=>new Promise(done=>{resolve=done;}));
  try{
    render(fixture());findButton(root,'Tool library').click();findButton(root,'Common baseline').click();
    findButton(root,'Experiments').click();findButton(root,'experiment1').click();
    resolve({files:{'main.py':'stale response'}});await tick();
    assert.match(root.querySelector('.methods-inspector').textContent,/Can the repaired method help/);
    assert.doesNotMatch(root.querySelector('.methods-inspector').textContent,/stale response/);
    const second=fixture();second.run.id='another';render(second);
    assert.match(root.querySelector('.methods-inspector').textContent,/From an idea to actual use/);
  }finally{dom.window.close();}
});

test('live timer obeys monotonic freshness bound and freezes when paused',()=>{
  const {dom,root,render,w}=mount();
  try{
    let clock=0;Object.defineProperty(w.performance,'now',{value:()=>clock});
    const snap=fixture();snap.runtime.stale_after_seconds=5;render(snap);
    clock=3000;w.updateMethodsTiming(root,{follow:true,connected:true});assert.equal(root.querySelector('[data-methods-elapsed]').textContent,'00:02:03');
    clock=9000;w.updateMethodsTiming(root,{follow:false,connected:true});assert.equal(root.querySelector('[data-methods-elapsed]').textContent,'00:02:03');
    w.updateMethodsTiming(root,{follow:true,connected:true});assert.equal(root.querySelector('[data-methods-elapsed]').textContent,'00:02:05');
    snap.runtime.active=false;snap.timing.live=false;snap.timing.session.elapsed_seconds=130;render(snap);clock=20000;w.updateMethodsTiming(root);assert.equal(root.querySelector('[data-methods-elapsed]').textContent,'00:02:10');
  }finally{dom.window.close();}
});

test('poll refresh preserves open source inspector and ledger disclosure',async()=>{
  let calls=0;const {dom,root,render}=mount(async()=>{calls++;return {files:{'main.py':'def f(): return 1'}};});
  try{
    render(fixture());findButton(root,'Tool library').click();root.querySelector('.methods-budget').open=true;findButton(root,'Common baseline').click();await tick();
    const detail=root.querySelector('.methods-loaded-detail');detail.querySelector('details').open=true;
    const next=fixture();next.content_version='v2';next.timing.session.elapsed_seconds=121;
    next.methods.tools[0].invocations=19;next.methods.tools[0].status='released';next.methods.tools[0].adopted_by=['lab-c'];
    render(next);
    assert.equal(root.querySelector('.methods-loaded-detail'),detail);
    assert.match(root.querySelector('.methods-inspector').textContent,/Actual invocations19/);
    assert.equal(detail.querySelector('details').open,true);
    assert.equal(root.querySelector('.methods-budget').open,true);
    assert.equal(calls,1);
  }finally{dom.window.close();}
});


test('overhead observation preserves unknown CPU and remains separate from charged ledger',()=>{
  const {dom,root,render}=mount();
  try{
    const snapshot=fixture();snapshot.runtime.overhead={controller_cpu_seconds:0,container_cpu_seconds:null,container_cpu_complete:false,unmetered_controller_cpu_seconds_estimate:null,output_logical_bytes_delta:2048,budget_enforced:false,additive_to_ledger:false};render(snapshot);
    const panel=root.querySelector('.methods-overhead');
    assert.match(panel.textContent,/Controller CPU0.00 s/);
    assert.match(panel.textContent,/Container CPU—Partial coverage/);
    assert.match(panel.textContent,/Resolved at the terminal boundary/);
    assert.match(panel.textContent,/2.0 KiB/);
    assert.match(panel.textContent,/must not be added/);
    assert.equal([...root.querySelectorAll('.methods-summary .methods-fact')].find(node=>node.querySelector('span').textContent==='Recorded spend').querySelector('strong').textContent,'$0.0000');
  }finally{dom.window.close();}
});


test('experiment inspector links actual supporting and contradicting claim evidence',()=>{
  const {dom,root,render}=mount();
  try{
    const snapshot=fixture();snapshot.methods.claims=[{id:'positive-claim',supporting:['experiment1'],contradicting:[],inconclusive:[]},{id:'negative-claim',supporting:[],contradicting:['experiment1'],inconclusive:[]},{id:'unrelated-claim',supporting:['another'],contradicting:[],inconclusive:[]}];render(snapshot);
    findButton(root,'Experiments').click();findButton(root,'experiment1').click();
    const claims=[...root.querySelectorAll('.methods-inspector details')].find(node=>node.querySelector('summary').textContent==='Research claims');
    assert.ok(claims);assert.match(claims.textContent,/positive-claim/);assert.match(claims.textContent,/negative-claim/);assert.doesNotMatch(claims.textContent,/unrelated-claim/);
  }finally{dom.window.close();}
});


test('solution execution bundles stay outside reusable library and solution quality excludes tool trials',async()=>{
  const calls=[];const {dom,root,render}=mount(async url=>{calls.push(url);return {files:{'main.py':'def pack(): return []'},manifest:{protocol:{permanent_toolbox_method:false}}};});
  try{
    const snapshot=fixture();
    snapshot.methods.tools.push({id:'solution-bundle',name:'Temporary Solution wrapper',kind:'adapter',protocol:{permanent_toolbox_method:false},author_lab:'lab-b',invocations:1});
    snapshot.methods.summary.methods=3;
    snapshot.methods.solutions=[{id:'solution1',program_id:'p0001',lab_id:'lab-b',method_id:'solution-bundle',experiment_id:'experiment1',native_metric:'sum_radii',native_score:2.5,score:.95,valid:true,confirmed:false}];
    snapshot.methods.quality={best_solution_id:'solution1',best_native_metric:'sum_radii',best_native_score:2.5,best_score:.95};
    snapshot.methods.experiments[0].native_treatment_score=99;
    render(snapshot);findButton(root,'Tool library').click();
    const facts=[...root.querySelectorAll('.methods-summary .methods-fact')];
    assert.equal(facts.find(node=>node.textContent.startsWith('Reusable tool versions')).querySelector('strong').textContent,'2');
    assert.equal(facts.find(node=>node.textContent.startsWith('Sum of radii')).querySelector('strong').textContent,'2.500000');
    assert.doesNotMatch(root.querySelector('.methods-record-content').textContent,/Temporary Solution wrapper/);
    findButton(root,'Programs').click();findButton(root,'p0001').click();await tick();
    assert.match(root.querySelector('.methods-inspector').textContent,/not a reusable library tool/);
    assert.match(root.querySelector('.methods-inspector').textContent,/Sum of radii/);
    assert.match(root.querySelector('.methods-inspector').textContent,/2.500000/);
    assert.deepEqual(calls,['/api/runs/campaign/method/solution-bundle']);
    const next=fixture();next.methods.execution_bundles=[snapshot.methods.tools.pop()];next.methods.solutions=snapshot.methods.solutions;next.methods.quality=snapshot.methods.quality;render(next);
    assert.match(root.querySelector('.methods-inspector').textContent,/2.500000/);
  }finally{dom.window.close();}
});

test('pending solution evaluation and recorded idle lab stages do not invent progress',()=>{
  const {dom,root,render}=mount();
  try{
    const snapshot=fixture();snapshot.methods.labs[0].current_stage='continued';snapshot.methods.labs[1].current_stage='generation';render(snapshot);
    assert.match(root.querySelector('.methods-summary').textContent,/Sum of radii—No evaluated Program yet/);
    assert.match(root.querySelector('[data-lab-id="lab-a"]').textContent,/Step recorded/);
    assert.match(root.querySelector('[data-lab-id="lab-b"]').textContent,/Generating proposal/);
  }finally{dom.window.close();}
});


test('proposal diagnostic is explicit and remains inert structured text',async()=>{
  const {dom,root,render}=mount(async()=>({response:'saved model response'}));
  try{
    const snapshot=fixture();snapshot.methods.proposals[0].status='invalid_proposal_format';snapshot.methods.proposals[0].diagnostic={code:'invalid_field',message:'<img src=x>',field:'kind'};render(snapshot);
    findButton(root,'LLM calls').click();findButton(root,'#0 · proposal1').click();await tick();
    const diagnostic=[...root.querySelectorAll('.methods-inspector details')].find(node=>node.querySelector('summary').textContent==='Proposal diagnostic');
    assert.ok(diagnostic?.open);assert.match(diagnostic.textContent,/invalid_field/);assert.match(diagnostic.textContent,/kind/);assert.equal(diagnostic.querySelector('img'),null);
  }finally{dom.window.close();}
});


test('zero-effect experiments never use a positive criterion badge even when the zero threshold is met',()=>{
  const {dom,root,render}=mount();
  try{
    const snapshot=fixture(), base=snapshot.methods.experiments[0];
    snapshot.methods.experiments=[
      {...base,id:'zero-met',effect:0,passed:true,criterion:{minimum_effect:0}},
      {...base,id:'zero-missed',effect:0,passed:false},
      {...base,id:'positive-met',effect:.1,passed:true},
      {...base,id:'negative-missed',effect:-.1,passed:false},
      {...base,id:'eval-failed',effect:null,passed:false},
      {...base,id:'eval-unknown',effect:null,passed:null}
    ];render(snapshot);findButton(root,'Experiments').click();
    const rows=[...root.querySelectorAll('.methods-record-content tbody tr')];
    const result=id=>rows.find(row=>row.querySelector('button').textContent===id.slice(0,12)).querySelector('.methods-status');
    for(const id of ['zero-met','zero-missed']){
      assert.equal(result(id).textContent,'No measured gain');assert.equal(result(id).classList.contains('is-positive'),false);
    }
    assert.equal(result('positive-met').textContent,'Criterion met');
    assert.equal(result('negative-missed').textContent,'Criterion missed');
    assert.equal(result('eval-failed').textContent,'failed');
    assert.equal(result('eval-unknown').textContent,'unknown');
    findButton(root,'zero-met').click();assert.match(root.querySelector('.methods-inspector').textContent,/Criterion passedYes/);
  }finally{dom.window.close();}
});


test('native experiment display never substitutes a normalized arm score for missing task units',()=>{
  const {dom,root,render}=mount();
  try{
    for(const explicit of [true,false]){
      const snapshot=fixture(), row=snapshot.methods.experiments[0];
      Object.assign(row,{native_metric:'sum_radii',native_control_score:2.6,native_treatment_score:null,control_score:.97,treatment_score:.9,effect:-.07});
      if(explicit)Object.assign(row,{display_metric:'sum_radii',display_control_score:2.6,display_treatment_score:null});
      render(snapshot);findButton(root,'Experiments').click();
      const treatment=root.querySelector('.methods-record-content tbody tr').children[2];
      assert.equal(treatment.querySelector('.mono').textContent,'—');assert.match(treatment.textContent,/sum_radii/);
      findButton(root,'experiment1').click();
      const facts=root.querySelector('.methods-inspector .methods-details').textContent;
      assert.match(facts,/Control score2.600000Treatment score—/);assert.doesNotMatch(facts,/0.900000/);
    }
  }finally{dom.window.close();}
});


test('continuous run shows explicit unlimited caps while finite zero and missing limits remain distinct',()=>{
  const {dom,root,render}=mount();
  try{
    const snapshot=fixture(), budget=snapshot.methods.budget;
    snapshot.run.classification='continuous_run';snapshot.methods.run_policy={classification:'continuous_run',max_steps:null,calendar_seconds:null,storage_bytes:null,capacity_wait_seconds:null};
    budget.limits={dollars:null,cpu_seconds:null,gpu_seconds:0,wall_seconds:null,storage_bytes:null};
    budget.remaining={dollars:null,cpu_seconds:null,gpu_seconds:0,wall_seconds:null,storage_bytes:null};
    snapshot.methods.labs[0].budget=budget;render(snapshot);
    assert.match(root.querySelector('.methods-run-policy').textContent,/Continuous run/);
    assert.match(root.querySelector('.methods-run-policy').textContent,/Per-call execution limits remain/);
    const rows=[...root.querySelectorAll('.methods-budget tbody tr')];
    assert.deepEqual([...rows[0].children].slice(3).map(node=>node.textContent),['Unlimited','Unlimited']);
    assert.deepEqual([...rows[2].children].slice(3).map(node=>node.textContent),['0','0']);
    assert.deepEqual([...rows[5].children].slice(3).map(node=>node.textContent),['—','—']);
    assert.match(root.querySelector('.methods-budget').textContent,/steps: Unlimited/);
    root.querySelector('[data-lab-id="lab-a"]').click();assert.match(root.querySelector('.methods-inspector').textContent,/Unlimited/);
    snapshot.run.status='stopped';snapshot.run.status_reason='User stop requested';snapshot.runtime.active=false;render(snapshot);
    assert.match(root.querySelector('.methods-run-policy').textContent,/Stopped: User stop requested/);
  }finally{dom.window.close();}
});

test('pre-dispatch refusal is shown separately from a malformed model response',()=>{
  const {dom,root,render}=mount();try{
    const snapshot=observedFixture();
    Object.assign(snapshot.methods.observability.programs,{status:'proposal_not_dispatched',not_dispatched_proposals:1});
    render(snapshot);findButton(root,'Programs').click();
    const text=root.querySelector('.methods-record-content').textContent;
    assert.match(text,/Proposal request was not sent/);
    assert.match(text,/Requests not dispatched1/);
    assert.doesNotMatch(text,/Some model replies could not be classified/);
  }finally{dom.window.close();}
});

test('unavailable current lab revision never looks like zero verified active tools',()=>{
  const {dom,root,render}=mount();try{
    const snapshot=observedFixture();
    Object.assign(snapshot.methods.labs[0],{revision_available:false,revision_number:null,revision_id:null,
      current_stage:'revision_unavailable',active_methods:[],active_adapters:[],
      last_verified_revision:{id:'old-revision',active_methods:['tool1']}});
    render(snapshot);
    const lab=root.querySelector('[data-lab-id="'+snapshot.methods.labs[0].id+'"]');
    assert.match(lab.textContent,/Revision unavailable/);
    assert.match(lab.textContent,/Unknownactive tools/);
    lab.click();
    assert.match(root.querySelector('.methods-inspector').textContent,/Current tools unknown/);
    assert.match(root.querySelector('.methods-inspector').textContent,/Last-known tools are historical only/);
  }finally{dom.window.close();}
});


test('Work Flow keeps its mount and open sections across lab snapshots, and releases it when leaving',()=>{
  const {dom,root,render,workflowCalls,workflowDestroys}=mount();try{
    const snapshot=fixture();render(snapshot);findButton(root,'Work Flow').click();
    const mount=root.querySelector('.methods-workflow-view'), details=mount.querySelector('details');details.open=true;mount.scrollTop=180;
    assert.equal(root.querySelector('[data-methods-tab="workflow"]').getAttribute('aria-selected'),'true');
    assert.equal(root.querySelector('.methods-inspector').hidden,true);
    assert.match(root.querySelector('.methods-record-content').textContent,/All laboratories · Work Flow includes the complete run/);
    assert.equal(root.querySelector('.methods-workbench').classList.contains('is-workflow'),true);
    assert.equal(workflowCalls.at(-1).options.runId,'campaign');
    snapshot.content_version='v2';snapshot.methods.summary.proposals++;render(snapshot);
    assert.equal(root.querySelector('.methods-workflow-view'),mount);assert.equal(mount.querySelector('details'),details);assert.equal(details.open,true);assert.equal(mount.scrollTop,180);
    assert.equal(workflowCalls.at(-1).options.version,'v2');
    findButton(root,'Events').click();assert.equal(workflowDestroys.length,1);assert.equal(workflowDestroys[0],mount);
    assert.equal(root.querySelector('.methods-inspector').hidden,false);
    assert.equal(root.querySelector('.methods-workbench').classList.contains('is-workflow'),false);
  }finally{dom.window.close();}
});

test('Work Flow is destroyed when a lab path is reused by another scientific run',()=>{
  const {dom,root,render,workflowCalls,workflowDestroys,w}=mount();try{
    const snapshot=fixture();snapshot.run.run_id='science-a';render(snapshot);findButton(root,'Work Flow').click();
    const old=workflowCalls.at(-1).node;
    snapshot.run.run_id='science-b';render(snapshot);assert.equal(workflowDestroys.length,1);assert.equal(workflowDestroys[0],old);
    assert.equal(root.querySelector('[data-methods-tab="population"]').getAttribute('aria-selected'),'true');
    findButton(root,'Work Flow').click();assert.notEqual(workflowCalls.at(-1).node,old);
    w.destroyMethodsDashboard(root);assert.equal(workflowDestroys.length,2);assert.equal(root.children.length,0);
  }finally{dom.window.close();}
});
