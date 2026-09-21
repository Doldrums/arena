import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source=readFileSync(new URL('../../web/population.js',import.meta.url),'utf8').replaceAll('export function ','function ');
const member=(id,score=.8)=>({id,score,generation:2,code_available:true,grid_elite:false,archive_member:false});
function population(){return {available:true,iteration:3,islands:[{id:0,best_score:.9,member_count:2,members:[member('p1'),member('p2',.9)]},{id:1,best_score:.85,member_count:1,members:[member('p3',.85)]}],dynamics:{islands:[{id:0,status:'active'},{id:1,status:'active'}],as_of:{evaluations:3},migrations:[],frames:[{id:'old',iteration:1,evaluations:1,islands:[{id:0,status:'active',member_count:1,member_ids:['p1']}]},{id:'current',iteration:3,evaluations:3,islands:[]}],spawn:{enabled:false},next_cut:{status:'disabled'}}};}
function setup(reduced=true){
  const dom=new JSDOM('<div id="map"></div>',{runScripts:'outside-only',pretendToBeVisual:true}),w=dom.window;
  w.matchMedia=()=>({matches:reduced});w.eval('{'+source+';window.renderPopulationMap=renderPopulationMap;window.destroyPopulationMap=destroyPopulationMap;}');
  const root=w.document.getElementById('map');Object.defineProperty(root,'clientWidth',{value:760,configurable:true});
  return {dom,w,root,draw:(value,options={})=>w.renderPopulationMap(root,value,{runKey:'one',metricLabel:'Quality',live:true,follow:true,...options}),close:()=>{w.destroyPopulationMap(root);dom.window.close();}};
}

test('real cells expose safe source actions, island selection, and keyboard focus',()=>{
  const f=setup();try{const p=population();p.islands[0].members[0].id='<img src=x onerror=boom()>';let opened;
    f.draw(p,{onProgram:(id,options)=>opened={id,options}});
    assert.equal(f.root.querySelectorAll('.territory-cell').length,3);assert.equal(f.root.querySelector('img'),null);
    assert.match(f.root.textContent,/Schematic layout/);
    const tile=f.root.querySelector('.territory-cell');tile.dispatchEvent(new f.w.Event('focus'));tile.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    assert.equal(tile.getAttribute('aria-pressed'),'true');assert.match(f.root.querySelector('.territory-inspector').textContent,/<img/);
    f.root.querySelector('.territory-card-actions button').click();assert.equal(opened.id,'<img src=x onerror=boom()>');assert.equal(opened.options.action,'source');
    tile.focus();tile.dispatchEvent(new f.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));assert.equal(f.w.document.activeElement.dataset.program,'p2');
    f.root.querySelector('.territory-island[data-island="1"]').click();assert.match(f.root.querySelector('.territory-inspector').textContent,/Island 1/);
  }finally{f.close();}
});

test('unchanged snapshots keep cell DOM and selection; only new live memberships bloom',()=>{
  const f=setup(false);try{const p=population();f.draw(p);const tile=f.root.querySelector('.territory-cell[data-program="p1"]'),position=tile.getAttribute('transform');tile.click?.();tile.dispatchEvent(new f.w.Event('click'));
    f.draw(p);assert.equal(f.root.querySelector('.territory-cell[data-program="p1"]'),tile);assert.equal(tile.getAttribute('aria-pressed'),'true');assert.equal(f.root.querySelector('.is-born'),null);
    p.islands[0].members.push(member('p4'));p.islands[0].member_count++;f.draw(p);
    assert.equal(tile.getAttribute('transform'),position);assert.ok(f.root.querySelector('.territory-cell[data-program="p4"]').classList.contains('is-born'));
    const newcomer=f.root.querySelector('[data-program="p4"]');f.draw(p,{follow:false});assert.equal(f.root.querySelector('[data-program="p4"]'),newcomer);assert.equal(f.root.querySelector('.territory-state').classList.contains('is-live'),false);
  }finally{f.close();}
});

test('replay uses recorded membership and does not leak current scores, risk, spawn or migration',()=>{
  const f=setup();try{const p=population();p.dynamics.islands[0].at_risk=true;p.dynamics.spawn={enabled:true,lifetime_islands:2,max_islands:4,remaining_evaluations:7,guards:[]};p.dynamics.migrations=[{id:'m1',parent_id:'p1',program_id:'p3',from_island:0,to_island:1}];
    const control=f.draw(p);assert.equal(f.root.querySelectorAll('.territory-migration').length,0);f.root.querySelector('[data-program="p1"]').dispatchEvent(new f.w.Event('click'));assert.equal(f.root.querySelectorAll('.territory-migration').length,1);assert.ok(f.root.querySelector('.territory-spawn'));
    control.selectFrame('old');assert.equal(f.root.querySelectorAll('.territory-cell').length,1);assert.equal(f.root.querySelector('.territory-migration'),null);assert.equal(f.root.querySelector('.territory-spawn'),null);assert.equal(f.root.querySelector('.is-risk'),null);
    const tile=f.root.querySelector('.territory-cell');tile.dispatchEvent(new f.w.Event('focus'));assert.match(f.root.querySelector('.territory-card-score').textContent,/Not recorded/);assert.match(f.root.querySelector('.territory-state').textContent,/Replay/);
    f.draw(p);assert.equal(f.root.querySelectorAll('.territory-cell').length,1);f.root.querySelector('.territory-live').click();assert.equal(f.root.querySelectorAll('.territory-cell').length,3);
  }finally{f.close();}
});

test('migration links require exact recorded endpoint IDs; malformed target is never invented',()=>{
  const f=setup();try{const p=population();p.dynamics.migrations=[{id:'m1',parent_id:'p1',program_id:'p3',from_island:0,to_island:1},{id:'m2',parent_id:'missing',program_id:'p3',from_island:0,to_island:1}];f.draw(p);
    assert.equal(f.root.querySelectorAll('.territory-migration').length,0);
    f.root.querySelector('[data-program="p1"]').dispatchEvent(new f.w.Event('pointerenter'));
    const edges=f.root.querySelectorAll('.territory-migration');assert.equal(edges.length,1);assert.equal(edges[0].dataset.from,'p1');assert.equal(edges[0].dataset.to,'p3');
    f.root.querySelector('[data-program="p1"]').dispatchEvent(new f.w.Event('pointerleave'));
    assert.equal(f.root.querySelectorAll('.territory-migration').length,0);
    assert.match(f.root.querySelector('.territory-forecast').textContent,/1 recorded migration links/);
  }finally{f.close();}
});

test('tile count stays bounded, reduced motion suppresses bloom, and unknown membership is explicit',()=>{
  const f=setup();try{const p=population();p.islands=[{id:0,member_count:1300,members:Array.from({length:1300},(_,i)=>member('p'+i))}];p.dynamics.islands=[{id:0,status:'active'}];f.draw(p);assert.equal(f.root.querySelectorAll('.territory-cell').length,600);assert.match(f.root.querySelector('.territory-limit').textContent,/700 recorded programs/);
    p.islands[0].members=Array.from({length:1300},(_,i)=>member('q'+i));f.draw(p);assert.equal(f.root.querySelectorAll('.territory-cell').length,600);assert.equal(f.root.querySelector('.is-born'),null);
    f.draw({available:false,islands:[],dynamics:{islands:[{id:0,status:'active',member_count:null}],frames:[]}}, {runKey:'fresh'});assert.equal(f.root.querySelectorAll('.territory-cell').length,0);assert.match(f.root.textContent,/Members not recorded/);
    f.draw({available:false,islands:[],dynamics:{islands:[{id:0,status:'active',member_count:1,member_ids:['seed']}],frames:[]}}, {runKey:'fresh'});
    const seed=f.root.querySelector('.territory-cell[data-program="seed"]');assert.ok(seed);seed.dispatchEvent(new f.w.Event('focus'));assert.match(f.root.querySelector('.territory-card-score').textContent,/Not recorded/);assert.equal(f.root.querySelector('.territory-card-actions button').disabled,true);
  }finally{f.close();}
});

test('conditional forecasts expose staleness and are never a wall-clock countdown',()=>{
  const f=setup();try{const p=population();p.dynamics.islands[0].status='cooldown';p.dynamics.islands[0].status_stale=true;p.dynamics.next_cut={status:'conditional',evaluations_remaining:12,forecast_as_of:{stale:true,evaluations:9}};p.dynamics.spawn={enabled:true,lifetime_islands:2,max_islands:4,stall_evaluations:14,stall_threshold:14,remaining_evaluations:0,guards:[{label:'Remaining capacity',satisfied:true},{label:'Fair dispatches',satisfied:null}]};f.draw(p);
    assert.match(f.root.textContent,/12 evaluations to milestone · as of evaluation 9/);assert.match(f.root.querySelector('.territory-stale').textContent,/Earlier forecast/);assert.match(f.root.textContent,/guards still apply/);assert.match(f.root.textContent,/not a promise/);assert.match(f.root.querySelector('.territory-island-meta').textContent,/cooldown · saved/);assert.match(f.root.querySelector('.territory-inspector').textContent,/saved scheduler state/);
    const progress=f.root.querySelector('[role="progressbar"]');assert.equal(progress.getAttribute('aria-valuenow'),'14');assert.equal(progress.getAttribute('aria-valuemax'),'14');
    f.root.querySelector('.territory-guards').open=true;f.draw(p);assert.equal(f.root.querySelector('.territory-guards').open,true);
    p.dynamics.spawn.lifetime_islands=4;f.draw(p);assert.equal(f.root.querySelector('.territory-spawn'),null);
  }finally{f.close();}
});

test('run switches reset pinned state and destroy removes all owned UI',()=>{
  const f=setup();try{f.draw(population());const old=f.root.querySelector('svg');f.draw({islands:[{id:9,members:[member('new')]}]}, {runKey:'two'});assert.notEqual(f.root.querySelector('svg'),old);assert.equal(f.root.querySelector('[data-program="p1"]'),null);f.w.destroyPopulationMap(f.root);assert.equal(f.root.children.length,0);
  }finally{f.close();}
});


test('occupied cells share the background lattice across islands, growth and resizing',()=>{
  const f=setup();try{
    const p=population();
    const verify=()=>{
      const pattern=f.root.querySelector('pattern');
      const width=Number(pattern.getAttribute('width')),height=Number(pattern.getAttribute('height'));
      const points=pattern.querySelector('polygon').getAttribute('points');
      const radii=points.trim().split(/\s+/).map(point=>Math.hypot(...point.split(',').map(Number)));
      assert.equal(radii.length,6);
      const radius=height/3;
      assert.ok(Math.abs(width-Math.sqrt(3)*radius)<.002,'background spacing matches the hex radius');
      for(const measured of radii)assert.ok(Math.abs(measured-radius)<.002,'all polygon vertices share the background radius');
      assert.equal(pattern.getAttribute('patternUnits'),'userSpaceOnUse','one global SVG lattice');
      const positions=new Set();
      for(const tile of f.root.querySelectorAll('.territory-cell')){
        assert.equal(tile.querySelector('polygon').getAttribute('points'),points,'identical occupied/empty hex geometry');
        const [x,y]=tile.getAttribute('transform').match(/[-\d.]+/g).map(Number);
        const r=y/(height/2),q=x/width-r/2;
        assert.ok(Math.abs(r-Math.round(r))<.002,'integer axial row');
        assert.ok(Math.abs(q-Math.round(q))<.002,'integer axial column');
        const address=Math.round(q)+','+Math.round(r);
        assert.equal(positions.has(address),false,'islands must not overlap');positions.add(address);
      }
      assert.equal(f.root.querySelector('ellipse'),null,'no floating island halos');
      assert.equal(f.root.querySelector('.territory-halo'),null);
      assert.ok(f.root.querySelector('.territory-boundary'));
      assert.equal(f.root.querySelector('.territory-boundary').tagName.toLowerCase(),'path');
      const svg=f.root.querySelector('.territory-svg'),view=svg.getAttribute('viewBox').split(' ').map(Number);
      assert.equal(parseFloat(svg.style.width),view[2],'no independent scaling of the lattice');
      assert.equal(parseFloat(svg.style.height),view[3]);
    };
    f.draw(p);verify();
    assert.equal(f.root.querySelector('.territory-boundary').getAttribute('d').split('M').length-1,10,'adjacent pair has no shared interior boundary');
    Object.defineProperty(f.root,'clientWidth',{value:354,configurable:true});f.draw(p);verify();
    p.islands[0].members=Array.from({length:250},(_,i)=>member('large'+i));p.islands[0].member_count=250;
    f.draw(p);verify();
    Object.defineProperty(f.root,'clientWidth',{value:980,configurable:true});f.draw(p);verify();
  }finally{f.close();}
});

test('neutral slots represent only known retention space and never act as programs',()=>{
  const f=setup();try{
    const p=population();p.retention={target_members_per_island:50,limit_kind:'soft'};
    let opened=0;f.draw(p,{onProgram:()=>opened++});
    const cells=f.root.querySelectorAll('.territory-cell'),empty=f.root.querySelectorAll('.territory-empty-slot');
    assert.equal(cells.length,3);assert.equal(empty.length,97);
    const first=cells[0];first.dispatchEvent(new f.w.Event('click'));
    const before=f.root.querySelector('.territory-inspector').textContent;
    for(const slot of empty){
      assert.equal(slot.hasAttribute('data-program'),false);
      assert.equal(slot.hasAttribute('tabindex'),false);
      assert.notEqual(slot.getAttribute('role'),'button');
      assert.equal(slot.closest('[data-program]'),null);
      assert.equal(slot.querySelector('button,a'),null);
    }
    empty[0].dispatchEvent(new f.w.Event('click',{bubbles:true}));
    assert.equal(opened,0);assert.equal(first.getAttribute('aria-pressed'),'true');
    assert.equal(f.root.querySelector('.territory-inspector').textContent,before);
    p.retention.target_members_per_island=1;f.draw(p);
    assert.equal(f.root.querySelectorAll('.territory-empty-slot').length,0,'above-target membership never creates negative or extra slots');
    assert.equal(f.root.querySelectorAll('.territory-cell').length,3,'a soft target never deletes recorded programs');
    assert.equal(f.root.querySelector('.territory-cell'),first);
    p.retention.target_members_per_island=50;f.draw(p);
    assert.equal(f.root.querySelectorAll('.territory-empty-slot').length,97);
  }finally{f.close();}
});

test('unknown target or actual member counts cannot invent vacant capacity',()=>{
  const f=setup();try{
    for(const target of [undefined,null,'50',NaN]){
      const p=population();p.retention={target_members_per_island:target};f.draw(p);
      assert.equal(f.root.querySelectorAll('.territory-empty-slot').length,0);
    }
    const p=population();p.retention={target_members_per_island:50};
    p.islands.forEach(island=>{island.member_count=null;});f.draw(p);
    assert.equal(f.root.querySelectorAll('.territory-cell').length,3);
    assert.equal(f.root.querySelectorAll('.territory-empty-slot').length,0,'displayed IDs do not establish the complete membership count');
    p.islands[1].member_count=1;f.draw(p);
    assert.equal(f.root.querySelectorAll('.territory-empty-slot').length,49,'only the island with a known count contributes capacity');
    delete p.retention;f.draw(p);
    assert.equal(f.root.querySelectorAll('.territory-empty-slot').length,0);
  }finally{f.close();}
});

test('real and neutral cell caps remain separate on the same bounded global lattice',()=>{
  const f=setup();try{
    const p=population();p.retention={target_members_per_island:2000};
    p.islands=[{id:0,member_count:350,members:Array.from({length:350},(_,i)=>member('a'+i))},
      {id:1,member_count:350,members:Array.from({length:350},(_,i)=>member('b'+i))}];
    f.draw(p);
    const cells=f.root.querySelectorAll('.territory-cell'),empty=f.root.querySelectorAll('.territory-empty-slot');
    assert.equal(cells.length,600);assert.equal(empty.length,600);assert.equal(cells.length+empty.length,1200);
    const pattern=f.root.querySelector('pattern'),width=Number(pattern.getAttribute('width')),height=Number(pattern.getAttribute('height'));
    const points=pattern.querySelector('polygon').getAttribute('points'),positions=new Set();
    for(const node of [...cells,...empty]){
      assert.equal((node.matches('polygon')?node:node.querySelector('polygon')).getAttribute('points'),points);
      const [x,y]=node.getAttribute('transform').match(/[-\d.]+/g).map(Number);
      const r=y/(height/2),q=x/width-r/2;
      assert.ok(Number.isFinite(q)&&Number.isFinite(r));
      assert.ok(Math.abs(q-Math.round(q))<.002&&Math.abs(r-Math.round(r))<.002);
      const key=Math.round(q)+','+Math.round(r);assert.equal(positions.has(key),false);positions.add(key);
    }
    assert.equal(f.root.querySelectorAll('[data-program]').length,600,'neutral capacity has no program identity');
  }finally{f.close();}
});

test('score colors use recorded values while color switches retain nodes selection and safe source actions',()=>{
  const f=setup();try{
    const p=population(),unsafe='<img src=x onerror="boom()">';
    p.islands[0].members[0]=member(unsafe,0);
    p.islands[1].members=[member('p3',0),member('unknown',null)];p.islands[1].member_count=2;
    const opened=[];f.draw(p,{onProgram:(id,options)=>opened.push({id,options})});
    const nodes=new Map([...f.root.querySelectorAll('.territory-cell')].map(node=>[node.dataset.program,node]));
    const tile=nodes.get(unsafe),other=nodes.get('p3'),high=nodes.get('p2'),unknown=nodes.get('unknown');
    const color=node=>node.style.getPropertyValue('--island-color');
    assert.notEqual(color(tile),color(other),'island mode distinguishes islands even at equal quality');
    tile.dispatchEvent(new f.w.Event('click'));
    const position=tile.getAttribute('transform'),islandColor=color(tile);
    const scoreButton=f.root.querySelector('.territory-view-switch [data-color-mode="score"]');scoreButton.click();
    assert.equal(scoreButton.getAttribute('aria-pressed'),'true');
    assert.equal(color(tile),color(other),'equal recorded values share score color across islands');
    assert.notEqual(color(tile),color(high));assert.notEqual(color(tile),color(unknown),'unknown quality is distinct from measured zero');
    assert.equal(tile.getAttribute('aria-pressed'),'true');assert.equal(tile.getAttribute('transform'),position);
    for(const [id,node] of nodes)assert.equal([...f.root.querySelectorAll('.territory-cell')].find(item=>item.dataset.program===id),node);
    assert.equal(f.root.querySelector('img'),null);assert.match(f.root.querySelector('.territory-inspector').textContent,/<img/);
    f.root.querySelector('.territory-card-actions button').click();assert.equal(opened.length,1);assert.equal(opened[0].id,unsafe);assert.equal(opened[0].options.action,'source');
    f.root.querySelector('[data-color-mode="island"]').click();assert.equal(color(tile),islandColor);assert.equal(tile.getAttribute('aria-pressed'),'true');
    const legend=f.root.querySelector('.territory-legend-item[data-island="1"]');legend.click();
    assert.equal(legend.getAttribute('aria-pressed'),'true');assert.match(f.root.querySelector('.territory-card-title').textContent,/Island 1/);
    assert.equal(f.root.querySelector('.territory-island[data-island="1"]').getAttribute('aria-pressed'),'true');
  }finally{f.close();}
});

test('color switching during replay preserves the historical frame and does not invent scores',()=>{
  const f=setup();try{
    const p=population();p.retention={target_members_per_island:50};
    const control=f.draw(p);control.selectFrame('old');
    const historical=f.root.querySelector('.territory-cell');historical.dispatchEvent(new f.w.Event('click'));
    const frame=f.root.querySelector('.territory-range').value;
    for(const mode of ['score','island','score']){
      f.root.querySelector('[data-color-mode="'+mode+'"]').click();
      assert.equal(f.root.querySelector('.territory-range').value,frame);
      assert.equal(f.root.querySelectorAll('.territory-cell').length,1);
      assert.equal(f.root.querySelector('.territory-cell'),historical);
      assert.equal(historical.getAttribute('aria-pressed'),'true');
      assert.match(f.root.querySelector('.territory-state').textContent,/Replay/);
      assert.match(f.root.querySelector('.territory-card-score').textContent,/Not recorded/);
      assert.equal(f.root.querySelector('.territory-card-actions button').disabled,true);
    }
    f.root.querySelector('.territory-live').click();
    assert.equal(f.root.querySelectorAll('.territory-cell').length,3);
    assert.equal(f.root.querySelector('[data-color-mode="score"]').getAttribute('aria-pressed'),'true');
  }finally{f.close();}
});

test('paging and real island filters expose programs beyond 600 while preserving global totals',()=>{
  const f=setup();try{
    const p=population();p.islands=Array.from({length:3},(_,island)=>({id:island,member_count:250,
      members:Array.from({length:250},(_,i)=>member('i'+island+'p'+i))}));
    p.dynamics.islands=p.islands.map(island=>({id:island.id,status:'active'}));
    f.draw(p);
    const retained=()=>f.root.querySelector('.territory-summary-item strong').textContent;
    assert.equal(retained(),'750');assert.equal(f.root.querySelectorAll('.territory-cell').length,600);
    assert.equal(f.root.querySelector('[data-program="i2p249"]'),null);
    f.root.querySelector('[aria-label="Next population page"]').click();
    assert.equal(f.root.querySelectorAll('.territory-cell').length,150);
    assert.ok(f.root.querySelector('[data-program="i2p249"]'));
    assert.equal(retained(),'750');assert.match(f.root.querySelector('.territory-page-label').textContent,/Page 2 \/ 2/);
    f.root.querySelector('.territory-legend-item[data-island="2"]').click();
    assert.equal(f.root.querySelectorAll('.territory-cell').length,250);
    assert.ok([...f.root.querySelectorAll('.territory-cell')].every(node=>node.dataset.island==='2'));
    assert.equal(retained(),'750');assert.match(f.root.querySelector('.territory-page-label').textContent,/Island 2 · Page 1/);
    f.root.querySelector('.territory-browse button').click();
    assert.equal(f.root.querySelectorAll('.territory-cell').length,600);assert.equal(retained(),'750');
    // The sidebar also filters before applying the display cap.
    f.root.querySelector('.territory-island[data-island="2"]').click();
    assert.equal(f.root.querySelectorAll('.territory-cell').length,250);
  }finally{f.close();}
});

test('zoom keeps source selection, frame and hex coordinates while only scaling the viewport',()=>{
  const f=setup();try{
    f.draw(population());const tile=f.root.querySelector('[data-program="p1"]');
    tile.dispatchEvent(new f.w.Event('click'));tile.focus();
    const transform=tile.getAttribute('transform'),viewBox=f.root.querySelector('svg').getAttribute('viewBox');
    f.root.querySelector('[aria-label="Zoom in population"]').click();
    assert.equal(f.root.querySelector('[data-program="p1"]'),tile);
    assert.equal(tile.getAttribute('aria-pressed'),'true');assert.equal(tile.getAttribute('transform'),transform);
    const svg=f.root.querySelector('svg');assert.equal(svg.getAttribute('viewBox'),viewBox);
    assert.equal(parseFloat(svg.style.width),Number(viewBox.split(' ')[2])*1.25);
    assert.equal(f.root.querySelector('.territory-zoom-label').textContent,'125%');
    f.draw(population());assert.equal(f.root.querySelector('[data-program="p1"]'),tile);
    assert.equal(f.root.querySelector('.territory-zoom-label').textContent,'125%');
    f.root.querySelector('[aria-label="Zoom out population"]').click();
    assert.equal(f.root.querySelector('.territory-zoom-label').textContent,'100%');
  }finally{f.close();}
});

test('unique source counts distinguish recorded copies and never leak current diversity into replay',()=>{
  const f=setup();try{
    const p=population();p.source_summary={complete:true,member_count:3,source_bound_members:3,
      unique_sources:2,known_identical_source_copies:1};
    const control=f.draw(p);
    assert.match(f.root.querySelector('.territory-summary').textContent,/2Unique sources \(saved\)/);
    assert.match(f.root.querySelector('.territory-map-caption').textContent,/1 known identical-source copies/);
    p.source_summary.complete=false;p.source_summary.unique_sources=null;p.source_summary.source_bound_members=1;
    f.draw(p);assert.match(f.root.querySelector('.territory-summary').textContent,/UnknownUnique sources/);
    control.selectFrame('old');assert.doesNotMatch(f.root.querySelector('.territory-summary').textContent,/Unique sources/);
    assert.doesNotMatch(f.root.querySelector('.territory-map-caption').textContent,/Exact-source coverage/);
  }finally{f.close();}
});

test('24 by 256 population is a dense bounded field with reachable later islands and first-position inspector',()=>{
  const f=setup();try{
    const p=population();p.islands=Array.from({length:24},(_,id)=>({id,member_count:256,members:Array.from({length:256},(_,i)=>member('p'+id+'-'+i,i/256))}));
    p.dynamics.islands=p.islands.map(row=>({id:row.id,status:'active'}));p.retention={target_members_per_island:256};
    f.draw(p);
    assert.equal(f.root.querySelectorAll('.territory-cell').length,600);
    assert.equal(f.root.querySelectorAll('.territory-empty-slot').length,0);
    assert.match(f.root.querySelector('.territory-summary').textContent,/6144/);
    assert.match(f.root.querySelector('.territory-page-label').textContent,/Page 1 \/ 11/);
    const centers=[...f.root.querySelectorAll('.territory-cell')].map(n=>n.getAttribute('transform').match(/[-\d.]+/g).map(Number));
    const xs=centers.map(p=>p[0]),ys=centers.map(p=>p[1]);
    assert.ok(Math.max(...xs)-Math.min(...xs)>(Math.max(...ys)-Math.min(...ys))*1.4,'broad packed field rather than disconnected island plaques');
    assert.equal(f.root.querySelector('.territory-sidebar').firstElementChild.className,'territory-inspector');
    f.root.querySelector('.territory-legend-item[data-island="23"]').click();
    assert.equal(f.root.querySelectorAll('.territory-cell').length,256);
    assert.ok(f.root.querySelector('[data-program="p23-255"]'));
    Object.defineProperty(f.root,'clientWidth',{value:354,configurable:true});f.draw(p);
    const box=f.root.querySelector('.territory-svg').getAttribute('viewBox').split(' ').map(Number);
    for(const node of f.root.querySelectorAll('.territory-cell')){
      const [x,y]=node.getAttribute('transform').match(/[-\d.]+/g).map(Number);
      assert.ok(x>0&&x<box[2]&&y>0&&y<box[3],'every actual program stays inside the resized board');
    }
  }finally{f.close();}
});

test('small known population occupies a balanced centered field rather than a skinny top ribbon',()=>{
  const f=setup();try{
    const p=population();p.retention={target_members_per_island:100};
    Object.defineProperty(f.root,'clientWidth',{value:884,configurable:true});f.draw(p);
    const cells=[...f.root.querySelectorAll('.territory-cell,.territory-empty-slot')];assert.equal(cells.length,200);
    const centers=cells.map(node=>node.getAttribute('transform').match(/[-\d.]+/g).map(Number));
    const rows=new Set(centers.map(p=>p[1]));assert.ok(rows.size>=10,'occupancy determines column count');
    const xs=centers.map(p=>p[0]),ys=centers.map(p=>p[1]);
    const width=Math.max(...xs)-Math.min(...xs),height=Math.max(...ys)-Math.min(...ys);
    assert.ok(width/height<2.2&&width/height>1,'balanced connected honeycomb');
    assert.ok(Math.abs((Math.min(...xs)+Math.max(...xs))/2-442)<20,'field stays centered on the global lattice');
  }finally{f.close();}
});
