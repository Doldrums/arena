import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {buildResearchMap} from '../../web/research-map-model.js';
import {layoutResearchMap, visibleResearchNodes, visibleResearchLinks, MAP_WIDTH, MAP_HEIGHT} from '../../web/research-map-layout.js';

function fixture() {
  const tasks = [
    {id:'heat',name:'Heat equation',paper_ids:['paper-a']},
    {id:'light',name:'Light transport',paper_ids:['paper-a']},
    {id:'wave',name:'Wave equation',paper_ids:['paper-b']},
    {id:'missing',name:'Missing measurement',paper_ids:['paper-a']},
    {id:'packing',name:'Circle packing',paper_ids:['paper-a']},
    {id:'isolated',name:'Isolated task',paper_ids:[]},
  ];
  const point = (system,best_score,state='completed') => ({system,model:'model-a',state,seed_score:10,best_score});
  const cohort = (task_id,points) => ({task_id,cohort:`protocol:${task_id}`,metric:'error',direction:'minimize',points});
  return buildResearchMap({catalog:{tasks},insights:{domains:[{id:'physics',label:'Physics'},{id:'mathematics',label:'Mathematics'}],
    task_annotations:Object.fromEntries(tasks.map(task=>[task.id,{domain_id:task.id==='packing'?'mathematics':task.id==='isolated'?'unknown':'physics'}]))},
    participants:{participants:[{id:'sciel',name:'SCiEL',papers:[{id:'paper-a'}]},
      {id:'baseline',name:'Baseline',papers:[{id:'paper-b'}]},{id:'isolated',name:'Isolated system',papers:[]}]},
    overview:{schema:'arena.results-overview/1',cohorts:[cohort('heat',[point('sciel',0),point('baseline',null,'failed')]),
      cohort('wave',[point('baseline',8)]),cohort('missing',[point('sciel',null,'failed')]),cohort('packing',[point('sciel',9)])]}});
}

const ids = values => [...values].sort();
const names = (model, options) => ids([...visibleResearchNodes(model,options)].map(id=>model.nodes.find(n=>n.id===id).label));
const edges = (model, options) => visibleResearchLinks(model,options).map(edge=>
  `${model.nodes.find(n=>n.id===edge.source).label}:${model.nodes.find(n=>n.id===edge.target).label}:${edge.kind}`).sort();

function freeze(value) {
  if (value && typeof value === 'object') {
    Object.freeze(value);
    for (const child of Object.values(value)) freeze(child);
  }
  return value;
}

function assertGeometry(model, positions) {
  assert.equal(positions.size, model.nodes.length);
  assert.deepEqual(ids(positions.keys()), ids(model.nodes.map(node=>node.id)));
  for (const node of positions.values()) {
    assert.ok(Number.isFinite(node.x) && Number.isFinite(node.y) && Number.isFinite(node.radius), node.id);
    assert.ok(node.radius >= 0 && node.x >= 0 && node.x <= MAP_WIDTH && node.y >= 0 && node.y <= MAP_HEIGHT, node.id);
    if (node.kind !== 'domain') {
      assert.ok(node.x >= 50 && node.x <= 1040 && node.y >= 105 && node.y <= 700, node.id);
    }
  }
}

test('layout preserves all nodes and input without using input order as an extra layout parameter',()=>{
  const model=freeze(fixture()), before=JSON.stringify(model), first=layoutResearchMap(model);
  assertGeometry(model,first);
  assert.equal(JSON.stringify(model),before);
  assert.deepEqual(layoutResearchMap(model),first);
  const shuffled={...model,nodes:[...model.nodes].reverse(),links:[...model.links].reverse(),domains:[...model.domains].reverse()};
  assert.deepEqual(layoutResearchMap(shuffled),first);
});

test('dense edge clusters stay finite and bounded after the final collision adjustment',()=>{
  const domain={id:'domain:custom',kind:'domain',domainId:'custom',label:'Custom domain',counts:{measured:0}};
  const nodes=Array.from({length:1600},(_,index)=>({id:`task:dense-${index}`,kind:'task',domainId:'custom',label:`Dense ${index}`,counts:{measured:index%7===0?1:0}}));
  const model={nodes:[...nodes,domain],links:[],domains:[domain]};
  assertGeometry(model,layoutResearchMap(model));
});

test('landscape includes isolated tasks and systems, never taxonomy labels as interactive nodes',()=>{
  const model=fixture(), visible=visibleResearchNodes(model);
  assert.deepEqual(ids(visible),ids(model.nodes.filter(node=>node.kind!=='domain').map(node=>node.id)));
  assert.ok(names(model).includes('Isolated task') && names(model).includes('Isolated system'));
  assert.ok(visibleResearchLinks(model).every(edge=>edge.kind!=='domain' && visible.has(edge.source) && visible.has(edge.target)));
});

test('domain filtering keeps only that domain and its actually linked systems',()=>{
  const model=fixture(), options={domain:'physics'};
  assert.deepEqual(names(model,options),['Baseline','Heat equation','Light transport','Missing measurement','SCiEL','Wave equation']);
  assert.ok(visibleResearchLinks(model,options).every(edge=>model.nodes.find(node=>node.id===edge.source).domainId==='physics'));
  assert.deepEqual(names(model,{domain:'not-present'}),[]);
});

test('task query reveals its direct systems but not every task sharing those systems',()=>{
  const model=fixture(), options={domain:'physics',query:'  HEAT  '};
  assert.deepEqual(names(model,options),['Baseline','Heat equation','SCiEL']);
  assert.deepEqual(edges(model,options),['Heat equation:Baseline:measured','Heat equation:SCiEL:literature','Heat equation:SCiEL:measured']);
  assert.deepEqual(names(model,{query:'no matching literal'}),[]);
});

test('system query works inside a domain and does not admit other-domain neighbors',()=>{
  const model=fixture(), options={domain:'physics',query:'sCiEl'};
  assert.deepEqual(names(model,options),['Heat equation','Light transport','Missing measurement','SCiEL']);
  assert.ok(visibleResearchLinks(model,options).every(edge=>model.nodes.find(node=>node.id===edge.target).participantId==='sciel'));
  assert.deepEqual(names(model,{domain:'mathematics',query:'Baseline'}),[]);
  assert.deepEqual(names(model,{query:'Isolated system'}),['Isolated system']);
});

test('recorded view needs actual measured outcomes, not failed run edges or literature links',()=>{
  const model=fixture(), options={mode:'recorded'};
  assert.deepEqual(names(model,options),['Baseline','Circle packing','Heat equation','SCiEL','Wave equation']);
  assert.deepEqual(edges(model,options),['Circle packing:SCiEL:measured','Heat equation:SCiEL:measured','Wave equation:Baseline:measured']);
  // Heat has a real zero result; Baseline is measured elsewhere, but its heat
  // edge failed without a result. Both endpoint counts alone are insufficient.
  const wrongEdge=model.links.find(edge=>edge.kind==='measured' && edge.source==='task:heat' && edge.target==='participant:baseline');
  assert.equal(wrongEdge.measurements[0].measured,0);
  assert.ok(!visibleResearchLinks(model,options).includes(wrongEdge));
});

test('query + domain + recorded intersects all constraints for both tasks and systems',()=>{
  const model=fixture();
  for (const query of ['heat','sciel']) {
    const options={query,domain:'physics',mode:'recorded'};
    assert.deepEqual(names(model,options),['Heat equation','SCiEL']);
    assert.deepEqual(edges(model,options),['Heat equation:SCiEL:measured']);
  }
  assert.deepEqual(names(model,{query:'sciel',domain:'unknown',mode:'recorded'}),[]);
  assert.deepEqual(names(model,{query:'light',domain:'physics',mode:'recorded'}),[]);
});

test('visible edge helper rejects dangling links, wrong endpoints and caller-hidden nodes',()=>{
  const model=fixture(), options={domain:'physics',query:'heat'};
  model.links.push({id:'dangling',source:'task:absent',target:'participant:sciel',kind:'literature'},
    {id:'reversed',source:'participant:sciel',target:'task:heat',kind:'literature'});
  const visible=visibleResearchNodes(model,options);
  assert.ok(!visible.has('task:absent'));
  visible.delete('participant:baseline');
  assert.deepEqual(visibleResearchLinks(model,options,visible).map(edge=>edge.target),['participant:sciel','participant:sciel']);
});

test('actual public catalog positions preserve every node and recorded edges bind positive observations',async()=>{
  const read=async name=>JSON.parse(await readFile(new URL(`../../registry/${name}.json`,import.meta.url),'utf8'));
  const [catalog,insights,participants,overview]=await Promise.all(['catalog','insights','participants','results-overview'].map(read));
  const model=buildResearchMap({catalog,insights,participants,overview});
  assert.equal(model.nodes.filter(node=>node.kind==='task').length,1163);
  assertGeometry(model,layoutResearchMap(model));
  const options={mode:'recorded'}, visible=visibleResearchNodes(model,options);
  for (const edge of visibleResearchLinks(model,options)) {
    assert.equal(edge.kind,'measured');
    assert.ok(edge.measurements.some(row=>row.measured>0));
    assert.ok(visible.has(edge.source) && visible.has(edge.target));
  }
});
