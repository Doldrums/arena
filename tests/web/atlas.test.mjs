import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source=readFileSync(new URL('../../web/arena-atlas.js',import.meta.url),'utf8').replace(/^export /gm,'');
const fixture={catalog:{tasks:[
  {id:'circle-1',name:'Circle packing',family:'circle_packing_square',executable:true},
  {id:'tensor-1',name:'Tensor decomposition',family:'matmul_tensor',executable:true},
  {id:'circle-2',name:'Second packing task',family:'circle_packing_square',executable:true},
  {id:'unavailable',name:'Unspecified definition',family:null,executable:false},
]},insights:{domains:[{id:'math',label:'Mathematics'},{id:'physics',label:'Physics',description:'Physical systems and their dynamics.',why_it_matters:'Model and measure physical systems.',representative_task_ids:['unavailable']}],task_annotations:{'circle-1':{domain_id:'math'},'circle-2':{domain_id:'math'},'tensor-1':{domain_id:'math'},unavailable:{domain_id:'physics'}}},
searchFamilies:{groups:[{id:'evolution',label:'Evolutionary methods',description:'Search over programs.',task_ids:['circle-1','tensor-1'],representative_task_ids:['tensor-1']},
{id:'other',label:'Other source methods',description:'Other methods.',task_ids:['circle-2','unavailable']}]}};
function mount(options={}) {
 const dom=new JSDOM('<main><div id="atlas"></div></main>',{url:'http://arena.test/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;w.eval(`{${source};Object.assign(window,{renderArenaAtlas,buildAtlasModel,layoutAtlasGroups});}`);
 const root=w.document.getElementById('atlas');w.renderArenaAtlas(root,{...fixture,...options});return{dom,w,doc:w.document,root};
}

test('atlas represents each actual task once and ignores foreign or duplicate memberships',()=>{
 const {dom,w,root}=mount({searchFamilies:{groups:[{id:'first',label:'First',task_ids:['circle-1','circle-1','foreign']},{id:'second',label:'Second',task_ids:['circle-1','tensor-1']}]}});
 try {
  const points=[...root.querySelectorAll('[data-task-id]')].map(x=>x.dataset.taskId);
  assert.equal(points.length,4);assert.equal(new Set(points).size,4);assert.ok(!points.includes('foreign'));
  const model=w.buildAtlasModel({...fixture,mode:'families'});
  assert.equal(model.groups.length,2);assert.equal(model.groups.find(g=>g.id==='physics').count,1);
  assert.equal(model.groups.reduce((n,g)=>n+g.count,0),fixture.catalog.tasks.length);
 }finally{dom.window.close();}
});

test('hover previews fade other clusters while selection survives pointer departure and clears with Escape',()=>{
 const {dom,w,root}=mount();
 try {
  const first=root.querySelector('[data-atlas-cluster="evolution"]'),other=root.querySelector('[data-atlas-cluster="other"]');
  first.dispatchEvent(new w.Event('pointerenter'));
  assert.ok(first.classList.contains('is-active'));assert.ok(other.classList.contains('is-muted'));
  assert.match(root.querySelector('.atlas-context').textContent,/CLUSTER PREVIEW/);
  first.dispatchEvent(new w.Event('click'));first.dispatchEvent(new w.Event('pointerleave'));
  assert.equal(first.getAttribute('aria-pressed'),'true');assert.ok(first.classList.contains('is-active'));
  other.dispatchEvent(new w.Event('pointerenter'));assert.ok(other.classList.contains('is-active'));
  other.dispatchEvent(new w.Event('pointerleave'));assert.ok(first.classList.contains('is-active'));
  first.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
  assert.equal(root.querySelectorAll('.is-muted').length,0);assert.equal(first.getAttribute('aria-pressed'),'false');
 }finally{dom.window.close();}
});

test('keyboard navigation, task links and browse action address actual selected group',()=>{
 const calls=[];const {dom,w,root,doc}=mount({onFilter:(...args)=>calls.push(args),onTask:id=>calls.push(['task',id])});
 try {
  const first=root.querySelector('[data-atlas-cluster="evolution"]');first.focus();
  first.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
  root.querySelector('.atlas-browse').click();assert.deepEqual(calls[0],['search_family','evolution']);
  assert.match(root.querySelector('.atlas-domain-tags').textContent,/Mathematics · 2/);
  root.querySelector('.atlas-task-link').click();assert.deepEqual(calls[1],['task','tensor-1']);
  first.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  assert.equal(doc.activeElement.dataset.atlasCluster,'other');
  doc.activeElement.dispatchEvent(new w.KeyboardEvent('keydown',{key:' ',bubbles:true}));
  assert.equal(doc.activeElement.getAttribute('aria-pressed'),'true');
 }finally{dom.window.close();}
});

test('Task families groups by scientific domain metadata and browses the domain filter',()=>{
 const modes=[],calls=[];const {dom,w,root}=mount({onModeChange:mode=>modes.push(mode),onFilter:(...args)=>calls.push(args)});
 try {
  root.querySelector('[data-atlas-mode="families"]').click();assert.deepEqual(modes,['families']);
  assert.equal(root.querySelector('[data-atlas-mode="families"]').getAttribute('aria-pressed'),'true');
  assert.equal(root.querySelectorAll('[data-atlas-cluster]').length,2);assert.equal(root.querySelectorAll('[data-task-id]').length,4);
  assert.equal(root.querySelector('[data-atlas-cluster="circle_packing_square"]'),null);
  const select=root.querySelector('select');select.value='physics';select.dispatchEvent(new w.Event('change'));
  assert.equal(root.querySelector('.atlas-details h3').textContent,'Physics');
  assert.equal(root.querySelector('.atlas-context-description').textContent,fixture.insights.domains[1].description);
  assert.match(root.querySelector('.atlas-context-why').textContent,/Model and measure physical systems/);
  assert.equal(root.querySelector('.atlas-stats dd').textContent,'1');
  assert.equal(new URL(root.querySelector('.atlas-task-link').href).searchParams.get('task'),'unavailable');
  root.querySelector('.atlas-browse').click();assert.deepEqual(calls[0],['domain','physics']);
 }finally{dom.window.close();}
});

test('family search finds scientific domains without dropping task particles or inventing a group',()=>{
 const {dom,w,root}=mount({current:{atlasMode:'families'}});
 try {
  const search=root.querySelector('.atlas-family-search');search.value='physics';search.dispatchEvent(new w.Event('input'));
  assert.equal(root.querySelectorAll('select option').length,2);
  assert.equal(root.querySelector('select option:last-child').value,'physics');
  assert.equal(root.querySelectorAll('[data-task-id]').length,4);
  search.value='no such family';search.dispatchEvent(new w.Event('input'));
  assert.equal(root.querySelector('select option:last-child').textContent,'No matching families');
  assert.equal(root.querySelector('select option:last-child').disabled,true);
 }finally{dom.window.close();}
});

test('domain partitions use annotations, retain every unique catalog task and preserve unknown metadata',()=>{
 const unknown={id:'unknown',label:'Mixed / unclassified',description:'Classification is not recorded.',why_it_matters:'Keep missing classifications visible.',representative_task_ids:['missing','foreign']};
 const catalog={tasks:[...fixture.catalog.tasks,{id:'missing',family:'Physics'},{id:'invalid',family:'Physics'},{id:'explicit-unknown',family:'Physics'},fixture.catalog.tasks[0]]};
 const insights={domains:[...fixture.insights.domains,unknown],task_annotations:{...fixture.insights.task_annotations,invalid:{domain_id:'not-a-domain'},'explicit-unknown':{domain_id:'unknown'},foreign:{domain_id:'physics'}}};
 const {dom,w}=mount();
 try {
  const model=w.buildAtlasModel({catalog,insights,mode:'families'});
  assert.deepEqual(Array.from(model.groups,group=>group.id).sort(),['math','physics','unknown']);
  const ids=model.groups.flatMap(group=>Array.from(group.task_ids));
  assert.equal(ids.length,7);assert.equal(new Set(ids).size,7);assert.ok(!ids.includes('foreign'));
  assert.deepEqual(Array.from(model.groups.find(group=>group.id==='math').task_ids),['circle-1','circle-2','tensor-1']);
  assert.deepEqual(Array.from(model.groups.find(group=>group.id==='physics').task_ids),['unavailable']);
  const unclassified=model.groups.find(group=>group.id==='unknown');
  assert.deepEqual(Array.from(unclassified.task_ids),['explicit-unknown','invalid','missing']);
  for(const key of ['label','description','why_it_matters'])assert.equal(unclassified[key],unknown[key]);
  assert.deepEqual(Array.from(unclassified.representative_task_ids),['missing']);
  for(const group of model.groups){assert.equal(group.filter_kind,'domain');assert.equal(group.filter_value,group.id);}
 }finally{dom.window.close();}
});

test('families selects the URL domain independently of the evaluator-family filter',()=>{
 const {dom,root}=mount({current:{atlasMode:'families',domain:'physics',family:'circle_packing_square'}});
 try {
  assert.equal(root.querySelector('[data-atlas-cluster="physics"]').getAttribute('aria-pressed'),'true');
  assert.equal(root.querySelector('select').value,'physics');
  assert.equal(root.querySelector('.atlas-details h3').textContent,'Physics');
 }finally{dom.window.close();}
});

test('missing method API is unavailable rather than an unclassified claim and families remain usable',()=>{
 const {dom,w,root}=mount({searchFamilies:null,loading:true});
 try {
  assert.match(root.textContent,/method atlas is loading/);
  assert.equal(root.querySelectorAll('[data-atlas-cluster]').length,0);
  w.renderArenaAtlas(root,{...fixture,searchFamilies:null,loading:false,errors:{searchFamilies:'Offline'}});
  assert.match(root.textContent,/Method atlas unavailable/);
  assert.doesNotMatch(root.textContent,/Unclassified methods/);
  root.querySelector('.atlas-unavailable button').click();
  assert.equal(root.querySelectorAll('[data-task-id]').length,4);
  assert.equal(root.querySelectorAll('[data-atlas-cluster]').length,2);
 }finally{dom.window.close();}
});

test('families distinguishes unavailable and loading domain assignments from an unknown classification',()=>{
 const {dom,w,root}=mount({insights:null,loading:true,current:{atlasMode:'families'}});
 try {
  assert.match(root.querySelector('.atlas-unavailable').textContent,/loading/i);
  assert.equal(root.querySelectorAll('[data-atlas-cluster],[data-task-id]').length,0);
  assert.equal(w.buildAtlasModel({...fixture,insights:null,mode:'families'}).groups.length,0);
  w.renderArenaAtlas(root,{...fixture,insights:null,loading:false,errors:{insights:'Offline'},current:{atlasMode:'families'}});
  assert.match(root.querySelector('.atlas-unavailable').textContent,/unavailable/i);
  assert.doesNotMatch(root.querySelector('.atlas-unavailable').textContent,/Unclassified methods|Mixed \/ unclassified/);
  assert.equal(root.querySelectorAll('[data-atlas-cluster],[data-task-id]').length,0);
  w.renderArenaAtlas(root,{...fixture,current:{atlasMode:'families'}});
  assert.equal(root.querySelector('.atlas-unavailable'),null);
  assert.equal(root.querySelectorAll('[data-task-id]').length,4);
 }finally{dom.window.close();}
});

test('missing domain metadata shows unavailable instead of zero domains or unclassified claims',()=>{
 const {dom,w,root}=mount({insights:null,errors:{insights:'Offline'}});
 try {
  root.querySelector('[data-atlas-cluster="evolution"]').dispatchEvent(new w.Event('click'));
  assert.match(root.querySelector('.atlas-domain-tags').textContent,/Domain data unavailable/);
  assert.equal(root.querySelector('.atlas-stats>div:nth-child(2) dd').textContent,'—');
  assert.doesNotMatch(root.querySelector('.atlas-domain-tags').textContent,/Unclassified/);
 }finally{dom.window.close();}
});

test('catalog loading, catalog failure and a true empty catalog stay distinct',()=>{
 const {dom,w,root}=mount({catalog:null,loading:true});
 try {
  assert.match(root.textContent,/task atlas is loading/);
  assert.doesNotMatch(root.textContent,/0 task packages/);
  w.renderArenaAtlas(root,{...fixture,catalog:null,loading:false,errors:{catalog:'Offline'}});
  assert.match(root.textContent,/Task atlas unavailable/);
  assert.doesNotMatch(root.textContent,/No tasks in this catalog/);
  w.renderArenaAtlas(root,{...fixture,catalog:{tasks:[]},loading:false});
  assert.match(root.textContent,/No tasks in this catalog/);
  assert.equal(root.querySelectorAll('[data-task-id]').length,0);
 }finally{dom.window.close();}
});

test('unrelated rerenders preserve selected cluster and deterministic coordinates',()=>{
 const {dom,w,root}=mount();
 try {
  root.querySelector('[data-atlas-cluster="evolution"]').dispatchEvent(new w.Event('click'));
  const before=[...root.querySelectorAll('[data-task-id]')].map(p=>[p.dataset.taskId,p.getAttribute('cx'),p.getAttribute('cy')]);
  w.renderArenaAtlas(root,{...fixture,current:{query:'unrelated'}});
  assert.equal(root.querySelector('[data-atlas-cluster="evolution"]').getAttribute('aria-pressed'),'true');
  assert.deepEqual([...root.querySelectorAll('[data-task-id]')].map(p=>[p.dataset.taskId,p.getAttribute('cx'),p.getAttribute('cy')]),before);
 }finally{dom.window.close();}
});

test('untrusted labels and task identifiers render as text with safe task routes',()=>{
 const data={catalog:{tasks:[{id:'<img>/"?odd',name:'<img src=x onerror=alert(1)>',family:'<script>alert(1)</script>'}]},searchFamilies:{groups:[{id:'hostile',label:'<script>alert(1)</script>',description:'<img src=x>',task_ids:['<img>/"?odd']}]}};
 const {dom,w,root}=mount(data);
 try {
  root.querySelector('[data-atlas-cluster]').dispatchEvent(new w.Event('click'));
  assert.equal(root.querySelector('img,script'),null);assert.match(root.textContent,/<script>alert\(1\)<\/script>/);
  assert.equal(new URL(root.querySelector('.atlas-task-link').href).searchParams.get('task'),'<img>/"?odd');
 }finally{dom.window.close();}
});

test('real catalog layouts contain all 1163 task particles in both exact partitions',()=>{
 const catalog=JSON.parse(readFileSync(new URL('../../registry/catalog.json',import.meta.url),'utf8'));
 const insights=JSON.parse(readFileSync(new URL('../../registry/insights.json',import.meta.url),'utf8'));
 const searchFamilies=JSON.parse(readFileSync(new URL('../../registry/search-families.json',import.meta.url),'utf8'));
 const {dom,w}=mount();
 try {
  for(const mode of ['methods','families']) {
   const model=w.buildAtlasModel({catalog,insights,searchFamilies,mode}),layout=w.layoutAtlasGroups(model.groups),points=layout.flatMap(g=>g.points);
   assert.equal(model.total,1163);assert.equal(points.length,1163);assert.equal(new Set(points.map(p=>p.id)).size,1163);
   assert.equal(model.groups.length,mode==='methods'?10:insights.domains.length);
   if(mode==='families')for(const domain of insights.domains){
    const group=model.groups.find(group=>group.id===domain.id);
    assert.ok(group,`Missing research domain ${domain.id}`);
    assert.equal(group.label,domain.label);assert.equal(group.count,domain.total);
    const expected=catalog.tasks.filter(task=>insights.task_annotations[task.id]?.domain_id===domain.id).map(task=>task.id).sort();
    assert.deepEqual(Array.from(group.task_ids),expected);
    assert.equal(group.filter_kind,'domain');assert.equal(group.filter_value,domain.id);
   }
   for(const point of points){assert.ok(Number.isFinite(point.x)&&Number.isFinite(point.y));assert.ok(point.x>0&&point.x<900&&point.y>0&&point.y<680,`${mode} ${point.id} is outside map`);}
   assert.equal(model.groups.reduce((n,g)=>n+g.count,0),1163);
  }
 }finally{dom.window.close();}
});

test('science and community supplements remain selectable collections with exact task links',()=>{
 const catalog=JSON.parse(readFileSync(new URL('../../registry/catalog.json',import.meta.url),'utf8'));
 const insights=JSON.parse(readFileSync(new URL('../../registry/insights.json',import.meta.url),'utf8'));
 const searchFamilies=JSON.parse(readFileSync(new URL('../../registry/search-families.json',import.meta.url),'utf8'));
 const calls=[],{dom,w,root}=mount({catalog,insights,searchFamilies,onFilter:(...args)=>calls.push(args)});
 try {
  assert.equal(root.querySelectorAll('[data-atlas-cluster]').length,10);
  for(const[id,count]of[['science-supplement',277],['community-supplement',1]]){
   const group=searchFamilies.groups.find(group=>group.id===id),cluster=root.querySelector(`[data-atlas-cluster="${id}"]`);
   assert.ok(cluster);assert.equal(group.paper_count,0);
   assert.match(cluster.style.getPropertyValue('--cluster-color'),/^#[a-f\d]{6}$/i);
   assert.equal(cluster.querySelectorAll('[data-task-id]').length,count);
   const select=root.querySelector('select');select.value=id;select.dispatchEvent(new w.Event('change'));
   assert.equal(cluster.getAttribute('aria-pressed'),'true');
   assert.equal(root.querySelector('.atlas-details h3').textContent,group.label);
   assert.equal(root.querySelector('.atlas-context-description').textContent,group.description);
   assert.equal(root.querySelector('.atlas-context-why summary').textContent,'About this task collection');
   assert.equal(root.querySelector('.atlas-stats dd').textContent,String(count));
   for(const link of root.querySelectorAll('.atlas-task-link'))assert.ok(group.task_ids.includes(new URL(link.href).searchParams.get('task')));
   root.querySelector('.atlas-browse').click();assert.deepEqual(calls.at(-1),['search_family',id]);
  }
 }finally{dom.window.close();}
});
