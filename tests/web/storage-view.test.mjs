import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source=readFileSync(new URL('../../web/storage-view.js',import.meta.url),'utf8')
  .replaceAll('export function ','function ');
const member=(id,score=.8)=>({id,score,code_available:true});
const binding=(island,program,x,y)=>({island_id:island,program_id:program,cell:[x,y],niche_id:null,binding:program===null?'recorded_cell':'recorded_elite'});
function fixture(){return {
  source:'checkpoint',iteration:5,islands:[
    {id:0,member_count:2,members:[member('p1'),member('p2',.7)],grid:[{x:2,y:8,score:.8,candidate_id:'p1'}]},
    {id:1,member_count:1,members:[member('p3',.9)],grid:[{x:2,y:8,score:.9,candidate_id:'p3'}]}],
  storage:{kind:'map_elites',label:'MAP-Elites',source:'checkpoint',iteration:5,stale:false,
    axes:[{label:'Recorded descriptor bin'},{label:'Score bin'}],bins:{x:10,y:10},
    assignments:[binding(0,'p1',2,8),binding(1,'p3',2,8)],projection:{available:false},notes:[]}
};}
function projectedFixture(){
  const p=fixture();p.storage.kind='vq_elites';p.storage.label='VQ niches × score bins';
  p.storage.axes=[{label:'VQ niche ID'},{label:'Score bin'}];p.storage.bins={x:null,y:10};
  p.storage.assignments=[{...binding(0,'p2',1,7),niche_id:1}];
  p.storage.projection={available:true,method:'pca',input_dimensions:64,output_dimensions:3,
    projected_rank:1,source:'checkpoint.db.niche.centroids',iteration:3,stale:true,
    axes:[{label:'Snapshot PC 1'},{label:'Snapshot PC 2'},{label:'Snapshot PC 3'}],
    explained_variance:[1,0,0],scope:'global_codebook',notes:['Unused dimensions are zero.'],
    points:[{id:'niche:0',kind:'centroid',island_id:null,program_id:null,niche_id:0,position:[-1,0,0]},
      {id:'niche:1',kind:'centroid',island_id:null,program_id:null,niche_id:1,position:[1,0,0]}],
    assignments:[{...binding(0,'old-elite',0,6),niche_id:0},{...binding(1,'old-other-island',0,5),niche_id:0}]};
  return p;
}
function setup(){
  const dom=new JSDOM('<div id="space"></div>',{runScripts:'outside-only',pretendToBeVisual:true}),w=dom.window;
  w.eval('{'+source+';window.renderStorageSpace=renderStorageSpace;}');
  const root=w.document.getElementById('space');Object.defineProperty(root,'clientWidth',{value:960,configurable:true});
  let handle;
  return {dom,w,root,draw:(value,options={})=>handle=w.renderStorageSpace(root,value,{current:true,metricLabel:'Quality',...options}),
    close:()=>{handle?.destroy();dom.window.close();}};
}
const button=(f,label)=>[...f.root.querySelectorAll('button')].find(b=>b.textContent===label);
const mark=(f,key)=>[...f.root.querySelectorAll('.storage-mark')].find(node=>node.dataset.storageKey===key);
function chooseIsland(f,value){const select=f.root.querySelector('select');select.value=value;select.dispatchEvent(new f.w.Event('change',{bubbles:true}));}

test('same native cell in two islands stays two selectable cells; non-elites get no position',()=>{
  const f=setup();try{
    const p=fixture();let opened;f.draw(p,{onProgram:(program,options)=>opened={program,options}});
    const first=mark(f,'cell:0:2:8'),second=mark(f,'cell:1:2:8');
    assert.equal(f.root.querySelectorAll('.storage-mark').length,2);
    assert.notEqual(first.getAttribute('transform'),second.getAttribute('transform'));
    assert.match(f.root.querySelector('.storage-caption').textContent,/islands/);
    first.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    assert.equal(first.getAttribute('aria-pressed'),'true');
    assert.deepEqual([...f.root.querySelectorAll('.storage-program strong')].map(n=>n.textContent),['p1']);
    button(f,'Source').click();assert.equal(opened.program,'p1');assert.equal(opened.options.islandId,'0');
    second.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:' ',bubbles:true}));
    assert.deepEqual([...f.root.querySelectorAll('.storage-program strong')].map(n=>n.textContent),['p3']);
    assert.equal(f.root.querySelector('[data-storage-key*="p2"]'),null);
  }finally{f.close();}
});

test('journal cell without elite ID cannot borrow a same-score member or another cell binding',()=>{
  const f=setup();try{
    const p=fixture();p.source='journal';p.islands[0].grid[0].candidate_id=null;
    p.islands[0].grid.push({x:3,y:8,score:.8,candidate_id:'p1'});
    p.storage.assignments=[binding(0,null,2,8),binding(0,'p1',3,8)];
    f.draw(p,{onProgram:()=>assert.fail('Unknown cell must not expose a program action')});
    mark(f,'cell:0:2:8').dispatchEvent(new f.w.Event('click'));
    assert.match(f.root.querySelector('.storage-inspector').textContent,/did not record its elite ID/);
    assert.equal(f.root.querySelectorAll('.storage-program').length,0);
  }finally{f.close();}
});

test('old global VQ projection uses its own bindings and never current grid assignments',()=>{
  const f=setup();try{
    const p=projectedFixture();p.islands[0].members.push(member('old-elite',.99));
    p.storage.projection.assignments[0].score=.61;f.draw(p);
    assert.equal(f.root.querySelectorAll('.storage-mark').length,2);
    assert.match(f.root.querySelector('.storage-heading p').textContent,/earlier saved geometry/);
    mark(f,'projected:niche:0').dispatchEvent(new f.w.Event('click'));
    assert.deepEqual([...f.root.querySelectorAll('.storage-program strong')].map(n=>n.textContent),['old-elite','old-other-island']);
    assert.match(f.root.querySelector('.storage-program span').textContent,/0\.61000/);
    assert.doesNotMatch(f.root.querySelector('.storage-program span').textContent,/0\.99000/);
    mark(f,'projected:niche:1').dispatchEvent(new f.w.Event('click'));
    assert.equal(f.root.querySelectorAll('.storage-program').length,0);
    chooseIsland(f,'1');assert.equal(f.root.querySelectorAll('.storage-mark').length,2);
    mark(f,'projected:niche:0').dispatchEvent(new f.w.Event('click'));
    assert.deepEqual([...f.root.querySelectorAll('.storage-program strong')].map(n=>n.textContent),['old-other-island']);
  }finally{f.close();}
});

test('camera acts on saved positions; rank-one flat projection has no fabricated spread',()=>{
  const f=setup();try{
    f.draw(projectedFixture());const initial=mark(f,'projected:niche:0').getAttribute('transform');
    const rotate=f.root.querySelector('[aria-label="Rotate storage space"]');rotate.value='80';rotate.dispatchEvent(new f.w.Event('input'));
    assert.notEqual(mark(f,'projected:niche:0').getAttribute('transform'),initial);
    assert.deepEqual([...f.root.querySelectorAll('.storage-axis-label')].map(n=>n.textContent),['Snapshot PC 1','Snapshot PC 2','Snapshot PC 3']);
    button(f,'2D').click();
    const positions=[...f.root.querySelectorAll('.storage-mark')].map(n=>n.getAttribute('transform').match(/translate\(([-\d.e+]+) ([-\d.e+]+)\)/).slice(1).map(Number));
    assert.equal(positions[0][1],positions[1][1]);assert.notEqual(positions[0][0],positions[1][0]);
    assert.equal(f.root.querySelectorAll('.storage-axis-label').length,2);
    assert.match(f.root.querySelector('.storage-heading p').textContent,/rank 1/);
  }finally{f.close();}
});

test('native VQ and centre-only containers retain distinct axes',()=>{
  const f=setup();try{
    const p=projectedFixture();f.draw(p);button(f,'Archive cells').click();
    assert.match(f.root.querySelector('.storage-caption').textContent,/categorical/);
    assert.equal(f.root.querySelector('.storage-axis-label').textContent,'VQ niche ID');
    p.storage.kind='vq';p.storage.axes=[{label:'Centre ID within island'}];p.storage.projection={available:false};
    f.draw(p);
    assert.equal(f.root.querySelector('.storage-axis-label').textContent,'Centre ID within island');
    assert.doesNotMatch(f.root.querySelector('.storage-heading p').textContent,/score bin/);
  }finally{f.close();}
});

test('pool inspector describes membership without inventing archive-cell geometry',()=>{
  const f=setup();try{
    const p=fixture();p.storage={kind:'pool',label:'Ranked program pool',axes:[],assignments:[],projection:{available:false}};
    f.draw(p);
    assert.equal(f.root.querySelectorAll('.storage-mark').length,0);
    assert.equal(f.root.querySelectorAll('.storage-pool button').length,3);
    assert.match(f.root.querySelector('.storage-caption').textContent,/No geometric niches/);
    assert.doesNotMatch(f.root.querySelector('.storage-inspector').textContent,/Each mark is one occupied storage cell|third axis|Archive cells/);
    f.root.querySelector('.storage-pool button').click();
    assert.match(f.root.querySelector('.storage-program span').textContent,/0\.80000/);
    chooseIsland(f,'1');assert.equal(f.root.querySelectorAll('.storage-pool button').length,1);
  }finally{f.close();}
});

test('unknown storage and replay never substitute current geometry',()=>{
  const f=setup();try{
    const p=projectedFixture();f.draw(p,{current:false});
    assert.equal(f.root.querySelectorAll('.storage-mark').length,0);
    assert.match(f.root.querySelector('.storage-empty').textContent,/not saved for this replay frame/);
    f.draw(p);assert.equal(f.root.querySelectorAll('.storage-mark').length,2);
    p.storage={kind:'unknown',label:'Storage not recorded',projection:{available:false}};f.draw(p);
    assert.equal(f.root.querySelectorAll('.storage-mark').length,0);
    assert.match(f.root.querySelector('.storage-empty').textContent,/No storage coordinates/);
    assert.doesNotMatch(f.root.querySelector('.storage-heading p').textContent,/Centre ID/);
  }finally{f.close();}
});

test('labels and program IDs stay text; unchanged heartbeat keeps selected DOM',()=>{
  const f=setup();try{
    const p=fixture(),unsafe='<img src=x onerror=boom()>';p.storage.label=unsafe;p.islands[0].members[0].id=unsafe;
    p.islands[0].grid[0].candidate_id=unsafe;p.storage.assignments[0].program_id=unsafe;
    let opened;f.draw(p,{onProgram:program=>opened=program});
    const selected=mark(f,'cell:0:2:8');selected.dispatchEvent(new f.w.Event('click'));
    assert.equal(f.root.querySelector('img'),null);assert.match(f.root.querySelector('.storage-inspector').textContent,/<img/);
    button(f,'Source').click();assert.equal(opened,unsafe);
    f.draw(p,{onProgram:program=>opened=program});assert.equal(mark(f,'cell:0:2:8'),selected);assert.equal(selected.getAttribute('aria-pressed'),'true');
  }finally{f.close();}
});
