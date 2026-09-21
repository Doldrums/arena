import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
const source=readFileSync(new URL('../../web/chart.js',import.meta.url),'utf8').replace('export function renderChart','function renderChart');
function setup(reduced=true){
  const dom=new JSDOM('<div id="plot"></div>',{runScripts:'outside-only',pretendToBeVisual:true});
  const w=dom.window;w.matchMedia=()=>({matches:reduced});
  const plot=w.document.getElementById('plot');
  Object.defineProperties(plot,{clientWidth:{value:700},clientHeight:{value:260}});
  w.eval('{'+source+';window.renderChart=renderChart;}');
  return {dom,w,plot,draw:(points,options={},select=()=>{})=>w.renderChart(plot,points,'iteration',null,select,'Sum of radii',{runKey:'one',...options})};
}
const node=(id,iteration,score,parent)=>({candidate_id:id,experiment_id:'r'+id,iteration,score,best_score:Math.max(2.5,score),parent_ids:parent?[parent]:[],parent_score:parent?2.5:null,operator:'diff',status:'evaluated',island:1,code_available:true,hypothesis:'Increase the radius by moving the outer ring.'});

test('hover and keyboard expose exact parents, real units, and actionable safe card',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const points=[node('p1',0,2.5),node('p2',1,2.6,'p1'),node('p3',2,2.61,'p2')];
    points[1].hypothesis='<img src=x onerror="boom()">';
    let opened,llm,selected;
    draw(points,{programs:points,onInspect:p=>opened=p.candidate_id,onLLM:p=>llm=p.experiment_id},p=>selected=p.candidate_id);
    const dot=plot.querySelector('.chart-dot[data-index="1"]');
    dot.dispatchEvent(new w.Event('pointerenter'));
    assert.equal(plot.querySelector('.chart-program-card').hidden,false);
    assert.match(plot.querySelector('.chart-card-score').textContent,/2.6.*\+0.1 vs parent/);
    assert.equal(plot.querySelector('[data-parent="p1"][data-child="p2"]').classList.contains('parent'),true);
    assert.ok(plot.querySelector('[data-parent="p2"][data-child="p3"]'));
    assert.equal(plot.querySelector('.chart-program-card img'),null);
    assert.match(plot.querySelector('.chart-card-hypothesis').textContent,/<img/);
    dot.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    assert.equal(selected,'p2');assert.match(plot.querySelector('.chart-interaction-hint').textContent,/Pinned/);
    plot.querySelector('[data-chart-inspect]').click();plot.querySelector('[data-chart-llm]').click();
    assert.equal(opened,'p2');assert.equal(llm,'rp2');
    dot.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    assert.equal(plot.querySelector('.chart-program-card').hidden,true);
  }finally{dom.window.close();}
});

test('overlapping observations use candidate identity and pinned preview survives live append',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const points=[node('seed',0,2.5),node('portfolio',0,2.5)];
    let selected;
    draw(points,{selectedCandidateId:'portfolio'},p=>selected=p.candidate_id);
    assert.equal(plot.querySelectorAll('.chart-dot.selected').length,1);
    plot.querySelector('.chart-dot.selected').dispatchEvent(new w.Event('click'));assert.equal(selected,'portfolio');
    assert.match(plot.querySelector('.chart-card-heading').textContent,/portfolio/);
    assert.ok(plot.querySelector('[data-program="seed"]'));
    draw([...points,node('next',1,2.6,'portfolio')],{selectedCandidateId:'portfolio'});
    assert.equal(plot.querySelector('.chart-program-card').hidden,false);
    assert.match(plot.querySelector('.chart-card-heading').textContent,/portfolio/);
    assert.match(plot.querySelector('.chart-interaction-hint').textContent,/Pinned/);
    draw(points,{runKey:'different'});
    assert.equal(plot.querySelector('.chart-program-card').hidden,true);
    assert.equal(plot.querySelectorAll('.chart-family-edge').length,0);
  }finally{dom.window.close();}
});

test('downsampled parents appear as exact lineage overlays, without growing base point count',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const points=Array.from({length:2100},(_,i)=>node('p'+i,i,2.5));
    points.at(-1).parent_ids=['p117'];
    const result=draw(points,{programs:points});
    assert.ok(result.displayed<=600);
    const child=[...plot.querySelectorAll('.chart-dot')].at(-1);
    child.dispatchEvent(new w.Event('pointerenter'));
    assert.ok(plot.querySelector('[data-parent="p117"][data-child="p2099"]'));
    assert.ok(plot.querySelector('[data-relative="p117"]'));
    assert.ok(plot.querySelectorAll('.chart-dot').length<=600);
  }finally{dom.window.close();}
});

test('missing positions, aliases, and cycles never invent measurement locations or hang',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const a=node('a',0,2.5,'b'),b=node('b',1,2.6,'a'),c=node('child',2,2.61,'migrant');
    const migrant={...node('migrant',null,2.5,'a'),lineage_note:'Migrated copy'};
    draw([a,b,c],{programs:[a,b,c,migrant]});
    plot.querySelector('.chart-dot[data-index="1"]').dispatchEvent(new w.Event('pointerenter'));
    assert.ok(plot.querySelectorAll('.chart-family-edge').length<=3);
    plot.querySelector('.chart-dot[data-index="2"]').dispatchEvent(new w.Event('pointerenter'));
    assert.equal(plot.querySelector('[data-relative="migrant"]'),null);
    assert.match(plot.querySelector('.chart-program-card').textContent,/no recorded chart position/);
    const seed={...node('seed',0,2.5),candidate_ids:['seed','copy2'],kind:'seed'};
    draw([seed,{...c,parent_ids:['copy2']}],{programs:[seed]});
    plot.querySelector('.chart-dot[data-index="1"]').dispatchEvent(new w.Event('pointerenter'));
    assert.ok(plot.querySelector('[data-parent="copy2"][data-child="child"]'));
  }finally{dom.window.close();}
});

test('animation respects reduced motion and does not restart for identical observations',()=>{
  const {dom,plot,draw}=setup(false);
  try{
    const points=[node('p1',0,2.5),node('p2',1,2.6,'p1')];
    draw(points,{live:true});
    const svg=plot.querySelector('svg');
    assert.ok(svg.classList.contains('chart-enter'));
    assert.ok(svg.classList.contains('is-live'));
    draw(points,{live:false});
    assert.equal(plot.querySelector('svg'),svg);
    assert.equal(svg.classList.contains('is-live'),false);
  }finally{dom.window.close();}
  const low=setup(true);
  try{low.draw([node('p',0,2.5)]);assert.equal(low.plot.querySelector('.chart-enter'),null);}
  finally{low.dom.window.close();}
});

test('keyboard navigation skips unmeasured steps and keeps moving after live metadata refresh',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const points=[node('p1',0,2.5),node('failed',1,null),node('p3',2,2.6,'p1')];
    draw(points);
    const first=plot.querySelector('.chart-dot[data-index="0"]');first.focus();
    // A new snapshot with unchanged coordinates reuses its nodes/listeners.
    draw(points.map(p=>({...p})));
    first.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
    assert.equal(w.document.activeElement,plot.querySelector('.chart-dot[data-index="2"]'));
    assert.match(plot.querySelector('.chart-card-heading').textContent,/p3/);
    w.document.activeElement.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true}));
    assert.equal(w.document.activeElement,first);
  }finally{dom.window.close();}
});

test('a versioned history index is reused on selection and invalidated for new lineage',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    let reads=0;
    const a=node('a',0,2.5),b=node('b',1,2.6,'a');
    Object.defineProperty(b,'parent_ids',{enumerable:true,get(){reads++;return ['a'];}});
    draw([a,b],{dataVersion:'one'});
    const before=reads;
    draw([a,b],{dataVersion:'one',selectedCandidateId:'b'});
    assert.equal(reads,before,'selection must not rebuild the full lineage index');
    draw([a,{...b,parent_ids:['missing']}],{dataVersion:'two'});
    plot.querySelector('.chart-dot[data-index="1"]').dispatchEvent(new w.Event('pointerenter'));
    assert.match(plot.querySelector('.chart-card-family').textContent,/missing/);
    assert.equal(plot.querySelector('.chart-family-edge'),null);
  }finally{dom.window.close();}
});

test('lineage edge count is bounded even with many recorded parents',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const parents=Array.from({length:50},(_,i)=>node('parent'+i,i,2.5));
    const child={...node('child',51,2.6),parent_ids:parents.map(p=>p.candidate_id)};
    draw([...parents,child]);
    [...plot.querySelectorAll('.chart-dot')].at(-1).dispatchEvent(new w.Event('pointerenter'));
    assert.equal(plot.querySelectorAll('.chart-family-edge').length,32);
    assert.ok(plot.querySelectorAll('.chart-relative-dot').length<=33);
    assert.match(plot.querySelector('.chart-program-card').textContent,/nearest recorded ancestors/);
  }finally{dom.window.close();}
});

test('shared seed coordinates preserve the clicked stored copy, island and source target',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const seed={...node('p1',0,2.5),candidate_ids:['p1','p2'],kind:'seed',island:0};
    const copy={...node('p2',0,2.5),kind:'seed',island:1};
    const child=node('p3',1,2.6,'p2');let opened;
    draw([seed,child],{programs:[seed,copy,child],selectedCandidateId:'p2',onInspect:p=>opened=p});
    assert.equal(plot.querySelectorAll('.chart-dot').length,2,'one shared measurement is still one base dot');
    assert.equal(plot.querySelector('.chart-dot.selected').dataset.index,'0');
    plot.querySelector('.chart-dot[data-index="1"]').dispatchEvent(new w.Event('pointerenter'));
    assert.ok(plot.querySelector('[data-parent="p2"][data-child="p3"]'));
    plot.querySelector('[data-program="p2"]').click();
    assert.match(plot.querySelector('.chart-card-heading').textContent,/Island 1/);
    assert.equal(plot.querySelector('.chart-card-heading strong').textContent,'p2');
    plot.querySelector('[data-chart-inspect]').click();
    assert.equal(opened.candidate_id,'p2');assert.equal(opened.island,1);
  }finally{dom.window.close();}
});

test('shared ancestors retain every distinct recorded edge without repeated traversal',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const points=[node('a',0,2.5),node('b',1,2.6,'a'),node('c',2,2.6,'a'),
      {...node('d',3,2.7),parent_ids:['b','c']}];
    draw(points);plot.querySelector('.chart-dot[data-index="3"]').dispatchEvent(new w.Event('pointerenter'));
    assert.deepEqual([...plot.querySelectorAll('.chart-family-edge')].map(n=>n.dataset.parent+'>'+n.dataset.child).sort(),
      ['a>b','a>c','b>d','c>d']);
    assert.equal(plot.querySelectorAll('[data-relative="a"]').length,1);
  }finally{dom.window.close();}
});

test('keyboard focus survives ancestor exploration, new points, metadata refresh and axis changes',()=>{
  const {dom,w,plot,draw}=setup();
  try{
    const points=[node('a',0,2.5),node('b',1,2.6,'a'),node('c',2,2.7,'b')].map((p,i)=>({...p,cost_total:i*.1}));
    const options={onInspect:()=>{},dataVersion:'one'};
    draw(points,options);
    plot.querySelector('.chart-dot[data-index="2"]').focus();
    plot.querySelector('[data-relative="b"]').focus();
    assert.equal(w.document.activeElement.dataset.relative,'b');
    assert.equal(plot.querySelector('.chart-card-heading strong').textContent,'b');
    w.document.activeElement.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    assert.match(plot.querySelector('.chart-interaction-hint').textContent,/Pinned/);
    plot.querySelector('.chart-dot[data-index="1"]').focus();
    const next=[...points,{...node('d',3,2.8,'c'),cost_total:.3}];
    draw(next,{...options,dataVersion:'two'});
    assert.equal(w.document.activeElement.dataset.pointKey,'b');
    plot.querySelector('[data-chart-inspect]').focus();
    draw(next,{...options,dataVersion:'three'});
    assert.ok(w.document.activeElement.matches('[data-chart-inspect]'));
    w.renderChart(plot,next,'cost_total',null,()=>{},'Score',{runKey:'one',...options,dataVersion:'four'});
    assert.ok(w.document.activeElement.matches('[data-chart-inspect]'));
    w.document.activeElement.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    assert.equal(plot.querySelector('.chart-program-card').hidden,true);
    assert.equal(w.document.activeElement.dataset.pointKey,'b');
  }finally{dom.window.close();}
});
