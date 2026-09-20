import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source = readFileSync(new URL('../../web/methods_atlas.js',import.meta.url),'utf8').replaceAll('export function ','function ');
function fixture(){return {
  summary:{labs:2,methods:4,solutions:1,experiments:2,proposals:2,invocations:3,claims:1,released:0,adoptions:1},
  identity:{library_policy:'verified',transfer_policy:'methods',generator:{model:'actual-model'},executor:{docker_server:'27.5.1',architecture:'arm64'},resources:{cpu_seconds:150,wall_seconds:180,memory_bytes:1073741824},procedure:'0123456789abcdef'},
  labs:[{id:'author',mode:'C',status:'trial',current_stage:'generation',revision_id:'ra',revision_number:2,active_methods:['common','child'],active_adapters:[]},{id:'reviewer',mode:'C',status:'trial',current_stage:'capacity_wait',revision_id:'rb',revision_number:3,active_methods:['common','child'],active_adapters:[],current_operations:[{category:'execution'},{category:'capacity_wait'}]}],
  tools:[{id:'common',name:'Common toolbox',provenance:'common_toolbox',parents:[],dependencies:[],status:'draft',registration_seq:1},{id:'parent',name:'Parent version',author_lab:'author',provenance:'lab_created',parents:[],dependencies:[],status:'draft',registration_seq:3},{id:'dependency',name:'Dependency',author_lab:'reviewer',provenance:'lab_created',parents:[],dependencies:[],status:'draft',registration_seq:4},{id:'child',name:'Child version',author_lab:'author',provenance:'lab_created',parents:['parent'],dependencies:['dependency'],adopted_by:['reviewer'],active_in:['author','reviewer'],invocations:0,status:'draft',registration_seq:5}],
  execution_bundles:[{id:'execution-only',record_kind:'solution_execution_bundle',protocol:{permanent_toolbox_method:false},author_lab:'author'}],
  solutions:[{id:'solution-record',program_id:'p1',lab_id:'author',method_id:'execution-only',experiment_id:'e2',native_metric:'sum_radii',native_score:0,score:0,confirmed:false}],
  experiments:[{id:'e1',lab_id:'author',purpose:'local',effect:0,passed:true},{id:'e2',lab_id:'reviewer',purpose:'replay',effect:0,passed:true}],
  proposals:[{id:'proposal-bad',lab_id:'author',status:'invalid'},{id:'proposal-valid',lab_id:'reviewer',status:'continued'}],
  claims:[{id:'claim1',supporting:[],inconclusive:['e1']}],
  transfers:[{id:'adoption1',kind:'adoption',lab_id:'reviewer',method_id:'child',next_use_experiment_id:null}]
};}
function mount(){
  const dom=new JSDOM('<main><section id="population"></section><section id="architecture"></section></main>',{runScripts:'outside-only',pretendToBeVisual:true});
  dom.window.eval('{'+source+';window.renderMethodsPopulation=renderMethodsPopulation;window.renderMethodsArchitecture=renderMethodsArchitecture;}');
  const root=dom.window.document.getElementById('population'),architecture=dom.window.document.getElementById('architecture');
  return {dom,w:dom.window,root,architecture,population:(data,options={})=>dom.window.renderMethodsPopulation(root,data,options),drawArchitecture:(data,options={})=>dom.window.renderMethodsArchitecture(architecture,data,options)};
}
const cells=(root,id)=>[...root.querySelectorAll('.ma-cell')].filter(node=>node.dataset.recordId===id);
const cellIn=(root,lab,id)=>[...root.querySelectorAll('.ma-population-group')].find(node=>node.dataset.groupId===lab).querySelector(`[data-record-id="${id}"]`);

test('population distinguishes unique tool versions, active memberships and evaluated programs',()=>{
  const f=mount();try{
    f.population(fixture());
    assert.match(f.root.textContent,/4 reusable versions · 1 evaluated programs/);
    assert.equal(f.root.querySelectorAll('.ma-population-group').length,3);
    assert.equal(f.root.querySelectorAll('[data-kind="tool"]').length,7);
    assert.equal(f.root.querySelectorAll('[data-kind="solution"]').length,1);
    assert.equal(cells(f.root,'common').length,3);
    assert.equal(cells(f.root,'child').length,2);
    assert.equal(cells(f.root,'execution-only').length,0);
    assert.match(f.root.textContent,/All laboratories/);
    assert.match(f.root.textContent,/A shared version can appear in several labs/);
    assert.match(f.root.textContent,/Position and distance do not encode score, niches or code similarity/);
    assert.equal(cellIn(f.root,'reviewer','child').classList.contains('is-imported'),true);
    assert.equal(cellIn(f.root,'reviewer','child').classList.contains('is-active'),true);
  }finally{f.dom.window.close();}
});

test('focus traces actual parents, dependencies, shared identity and adoption without creating edges',()=>{
  const f=mount();try{
    f.population(fixture());cellIn(f.root,'author','child').focus();
    assert.equal(cells(f.root,'parent')[0].dataset.relation,'parent');
    assert.equal(cells(f.root,'dependency')[0].dataset.relation,'dependency');
    assert.deepEqual(cells(f.root,'child').map(node=>node.dataset.relation),['selected','selected']);
    assert.equal(cells(f.root,'common')[0].classList.contains('is-muted'),true);
    assert.match(f.root.querySelector('.ma-population-detail').textContent,/0 actual invocations/);
    assert.match(f.root.querySelector('.ma-population-detail').textContent,/Parents: Parent version/);
    assert.match(f.root.querySelector('.ma-population-detail').textContent,/Adopted by: reviewer/);
    assert.equal([...f.root.querySelectorAll('.ma-population-group.is-related')].length,2);
  }finally{f.dom.window.close();}
});

test('keyboard navigation selects exact saved artifacts and a program opens the solution inspector',()=>{
  const f=mount(),opened=[];try{
    f.population(fixture(),{onSelect:(...args)=>opened.push(args)});
    const child=cellIn(f.root,'author','child');child.focus();
    child.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    assert.deepEqual(opened,[['tool','child']]);assert.equal(child.getAttribute('aria-pressed'),'true');
    child.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'End',bubbles:true}));
    const program=f.w.document.activeElement;
    assert.equal(program.dataset.kind,'solution');
    assert.match(f.root.querySelector('.ma-population-detail').textContent,/0\.000000 sum_radii/);
    program.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:' ',bubbles:true}));
    assert.deepEqual(opened.at(-1),['solution','solution-record']);
    program.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    assert.equal(f.root.querySelector('[aria-pressed="true"]'),null);
  }finally{f.dom.window.close();}
});

test('unchanged heartbeat preserves DOM and new data preserves focused immutable version',()=>{
  const f=mount();try{
    const data=fixture();let opened;
    f.population(data);const original=cellIn(f.root,'author','child');original.focus();
    original.dispatchEvent(new f.w.Event('click'));
    f.population(structuredClone(data),{onSelect:(...args)=>opened=args});
    assert.equal(cellIn(f.root,'author','child'),original);
    original.dispatchEvent(new f.w.Event('click'));assert.deepEqual(opened,['tool','child']);
    data.tools.push({id:'next',name:'Next version',author_lab:'author',parents:['child'],dependencies:[],registration_seq:9});data.summary.methods++;
    f.population(data);
    assert.equal(f.w.document.activeElement.dataset.recordId,'child');
    assert.equal(cellIn(f.root,'author','child').getAttribute('aria-pressed'),'true');
    assert.equal(cells(f.root,'next')[0].classList.contains('is-new'),true);
    assert.equal(cells(f.root,'parent')[0].classList.contains('is-new'),false);
  }finally{f.dom.window.close();}
});

test('active membership follows actual revisions and incomplete views do not fabricate cells',()=>{
  const f=mount();try{
    const data=fixture();data.labs[1].active_methods=['common','missing-version'];data.tools.at(-1).active_in=['reviewer'];data.summary.methods=50;
    f.population(data);
    assert.equal(cellIn(f.root,'reviewer','child'),null);
    assert.equal(cells(f.root,'missing-version').length,0);
    assert.match(f.root.textContent,/Showing 4 tool versions in this snapshot; 1 active references are outside this view/);
    assert.match(f.root.textContent,/50 reusable versions/);
  }finally{f.dom.window.close();}
});

test('unavailable revision keeps population membership unknown even with historical active arrays',()=>{
  const f=mount();try{
    const data=fixture();
    data.labs[0].revision_available=false;
    data.labs[1].active_methods=[];
    f.population(data);
    const group=f.root.querySelector('[data-group-id="author"]');
    assert.match(group.querySelector('.ma-group-heading').textContent,/active unknown/);
    assert.doesNotMatch(group.querySelector('.ma-group-heading').textContent,/0 active/);
    assert.equal(cellIn(f.root,'author','child').classList.contains('is-active'),false);
    assert.equal(cellIn(f.root,'author','common'),null);
    cellIn(f.root,'author','child').focus();
    assert.match(f.root.querySelector('.ma-population-detail').textContent,/Active in: no verified current membership; unknown for author/);
    data.labs[0].revision_available=true;
    f.population(data);
    assert.match(f.root.querySelector('[data-group-id="author"] .ma-group-heading').textContent,/2 active/);
    assert.equal(cellIn(f.root,'author','child').classList.contains('is-active'),true);
  }finally{f.dom.window.close();}
});

test('unsafe tool names and IDs remain inert text in SVG labels and detail links',()=>{
  const f=mount();try{
    const data=fixture();data.tools.at(-1).name='<img src=x onerror="alert(1)">';data.tools.at(-1).parents=['<script>bad</script>'];
    f.population(data);cellIn(f.root,'author','child').focus();
    assert.equal(f.root.querySelector('img'),null);assert.equal(f.root.querySelector('script'),null);
    assert.match(f.root.querySelector('.ma-population-detail').textContent,/<img/);
    assert.match(cellIn(f.root,'author','child').getAttribute('aria-label'),/<img/);
  }finally{f.dom.window.close();}
});

test('architecture uses real configuration and counts, and keeps queued work separate from active execution',()=>{
  const f=mount();try{
    f.drawArchitecture(fixture(),{live:true});
    assert.equal(f.architecture.querySelector('[data-architecture-step="proposal"]').classList.contains('is-active'),true);
    assert.equal(f.architecture.querySelector('[data-architecture-step="trial"]').classList.contains('is-active'),false);
    assert.match(f.architecture.querySelector('.ma-queue').textContent,/reviewer waiting for a shared slot/);
    assert.match(f.architecture.textContent,/2 experiments · 3 calls/);
    assert.match(f.architecture.textContent,/0 released tool versions/);
    assert.match(f.architecture.textContent,/1 adoptions · 0 with later use/);
    assert.match(f.architecture.textContent,/actual-model/);assert.match(f.architecture.textContent,/Docker 27\.5\.1 · arm64/);
    assert.match(f.architecture.textContent,/Per-call wall180 s/);assert.match(f.architecture.textContent,/Memory1024 MiB/);
    assert.match(f.architecture.textContent,/Format & contract checks/);
    assert.match(f.architecture.textContent,/Standalone programs also pass the solution novelty gate/);
    assert.match(f.architecture.textContent,/RL, bandits, MAP-Elites and VQ storage are not enabled/);
    assert.doesNotMatch(f.architecture.textContent,/gain observed|improved|SOTA/);
  }finally{f.dom.window.close();}
});

test('saved or stale architecture never animates old reservations as live activity',()=>{
  const f=mount();try{
    const data=fixture();f.drawArchitecture(data);
    assert.equal(f.architecture.querySelectorAll('.is-active').length,0);
    assert.match(f.architecture.textContent,/Recorded: Waiting for a shared slot/);
    assert.match(f.architecture.textContent,/Last recorded queue: reviewer/);
    f.drawArchitecture(data,{live:true});assert.ok(f.architecture.querySelectorAll('.is-active').length>0);
    f.drawArchitecture(data,{live:false});assert.equal(f.architecture.querySelectorAll('.is-active').length,0);
  }finally{f.dom.window.close();}
});

test('architecture opens exact recorded evidence, preserves keyboard focus and retains DOM on heartbeat',()=>{
  const f=mount(),opened=[];try{
    const data=fixture();f.drawArchitecture(data,{onSelect:(...args)=>opened.push(args)});
    const replay=f.architecture.querySelector('[data-architecture-step="replay"]');replay.focus();
    replay.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    assert.deepEqual(opened,[['experiment','e2']]);
    assert.ok(f.architecture.querySelector('[data-to="replay"]').classList.contains('is-highlighted'));
    f.drawArchitecture(structuredClone(data),{onSelect:(...args)=>opened.push(args)});assert.equal(f.architecture.querySelector('[data-architecture-step="replay"]'),replay);
    data.summary.invocations=4;f.drawArchitecture(data);
    assert.equal(f.w.document.activeElement.dataset.architectureStep,'replay');
  }finally{f.dom.window.close();}
});

test('architecture refreshes a recovered revision ordinal even when the latest ID is unchanged',()=>{
  const f=mount();try{
    const data=fixture();data.labs[0].revision_number=null;
    f.drawArchitecture(data);
    assert.match(f.architecture.querySelector('[data-lab-id="author"]').textContent,/r—/);
    data.labs[0].revision_number=3;
    f.drawArchitecture(data);
    assert.match(f.architecture.querySelector('[data-lab-id="author"]').textContent,/r3/);
  }finally{f.dom.window.close();}
});

test('architecture respects mode A and an explicitly unreplayed library policy',()=>{
  const f=mount();try{
    const data=fixture();data.labs.forEach(lab=>lab.mode='A');f.drawArchitecture(data);
    assert.equal(f.architecture.querySelectorAll('.ma-flow-node.is-disabled').length,3);
    assert.match(f.architecture.textContent,/Not enabled in mode A/);
    data.labs.forEach(lab=>lab.mode='C');data.identity.library_policy='unreplayed';f.drawArchitecture(data);
    assert.equal(f.architecture.querySelectorAll('.ma-flow-node.is-disabled').length,1);
    assert.match(f.architecture.textContent,/Not required by library policy/);
  }finally{f.dom.window.close();}
});

test('empty registry remains empty and reports unknown configuration without inventing versions',()=>{
  const f=mount();try{
    f.population({});f.drawArchitecture({});
    assert.equal(f.root.querySelectorAll('.ma-cell').length,0);
    assert.match(f.root.textContent,/0 reusable versions · 0 evaluated programs/);
    assert.match(f.root.textContent,/No recorded versions yet/);
    assert.match(f.architecture.querySelector('.ma-contract').textContent,/Not recorded/);
  }finally{f.dom.window.close();}
});
