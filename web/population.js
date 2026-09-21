/* Recorded membership on a schematic hex map. Coordinates are never embeddings. */
const territoryStates=new WeakMap();
const territoryColors=['#aaa7e8','#93b3ee','#e8c16c','#c6a2e1','#a6c8e9','#d9b7e9','#8d9edf','#d5c58d','#b9bbef','#98cad3','#c7aad1','#b6cbdc'];
const territoryNS='http://www.w3.org/2000/svg';
// One pointy-top axial lattice for both empty and occupied cells.
const territoryRadius=7.5,territoryStepX=Math.sqrt(3)*territoryRadius,territoryStepY=1.5*territoryRadius;
const territoryArray=value=>Array.isArray(value)?value:[];
const territoryId=value=>value===null||value===undefined?'':String(value);
const territoryNumber=value=>typeof value==='number'&&Number.isFinite(value)?value:null;
let territorySerial=0;

function territoryElement(state,tag,className,text,svg=false){
  const node=svg?state.doc.createElementNS(territoryNS,tag):state.doc.createElement(tag);
  if(className)node.setAttribute('class',className);
  if(text!==undefined)node.textContent=String(text);
  return node;
}
function territoryText(node,text){const value=String(text??'');if(node.textContent!==value)node.textContent=value;}
function territoryAttr(node,name,value){const text=String(value);if(node.getAttribute(name)!==text)node.setAttribute(name,text);}
function territoryScore(state,value,row,field='metric_display'){
  if(state.options.formatScore)return String(state.options.formatScore(value,row,field));
  if(territoryNumber(value)===null)return 'Not recorded';
  return value.toFixed(6);
}
function territoryMetric(state,row){return state.options.metricValue?state.options.metricValue(row):territoryNumber(row?.score);}
function territoryHex(radius){return Array.from({length:6},(_,i)=>{const a=(i*60-30)*Math.PI/180;return (radius*Math.cos(a)).toFixed(4)+','+(radius*Math.sin(a)).toFixed(4);}).join(' ');}
function territoryMatrix(count,columns){
  return Array.from({length:count},(_,i)=>{const r=Math.floor(i/columns);return [i%columns-Math.floor(r/2),r];});
}
function territoryBoundary(slots,coordinates){
  const cells=new Set([...slots].map(slot=>coordinates[slot].join(',')));
  const neighbors=[[1,0],[0,1],[-1,1],[-1,0],[0,-1],[1,-1]];
  const vertices=Array.from({length:6},(_,i)=>{const angle=(i*60-30)*Math.PI/180;return [territoryRadius*Math.cos(angle),territoryRadius*Math.sin(angle)];});
  const lines=[];
  for(const slot of slots){
    const [q,r]=coordinates[slot],x=territoryStepX*(q+r/2),y=territoryStepY*r;
    neighbors.forEach(([dq,dr],edge)=>{
      if(cells.has([q+dq,r+dr].join(',')))return;
      const [ax,ay]=vertices[edge],[bx,by]=vertices[(edge+1)%6];
      lines.push('M'+(x+ax).toFixed(4)+','+(y+ay).toFixed(4)+'L'+(x+bx).toFixed(4)+','+(y+by).toFixed(4));
    });
  }
  return lines.join('');
}

function territoryFrames(state){
  const dynamics=state.population.dynamics||{};
  const frames=territoryArray(dynamics.frames).filter(frame=>frame&&Array.isArray(frame.islands)).slice(-60);
  if(!frames.length)return [{id:'current',iteration:state.population.iteration,evaluations:dynamics.as_of?.evaluations,source:state.population.source,islands:[]}];
  return frames;
}
function territoryView(state){
  const frames=territoryFrames(state);
  let index=state.follow?frames.length-1:frames.findIndex(frame=>territoryId(frame.id)===state.frameId);
  if(index<0)index=0;
  const frame=frames[index],current=index===frames.length-1;
  state.frames=frames;state.frameIndex=index;state.frameId=territoryId(frame.id);
  const stored=new Map(territoryArray(state.population.islands).map(island=>[territoryId(island.id),island]));
  const live=new Map(territoryArray(state.population.dynamics?.islands).map(island=>[territoryId(island.id),island]));
  const rows=current?Array.from(new Set([...stored.keys(),...live.keys()])).map(id=>({...stored.get(id),...live.get(id),id,
    members:territoryArray(stored.get(id)?.members).length||stored.get(id)?.members_available===true?
      territoryArray(stored.get(id)?.members):territoryArray(live.get(id)?.member_ids).map(programId=>({id:programId,score:null}))})):
    territoryArray(frame.islands).map(island=>({...island,id:territoryId(island.id),
      members:territoryArray(island.members).length?island.members:territoryArray(island.member_ids).map(id=>({id,score:null})),
      members_available:island.member_ids!==null&&island.member_ids!==undefined}));
  return {frame,index,current,islands:rows,frames};
}

function territoryCreate(container,options){
  const state={container,doc:container.ownerDocument,options,population:{},runKey:options.runKey,follow:options.follow!==false,
    frameId:null,playing:false,timer:null,selectedIsland:null,selectedProgram:null,hoverProgram:null,
    tiles:new Map(),clusters:new Map(),islandSlots:new Map(),positions:new Map(),layouts:new Map(),timers:new Set(),placeholderTiles:new Map(),colorMode:'island',islandFilter:false,page:0,zoom:1,
    reduced:container.ownerDocument.defaultView?.matchMedia?.('(prefers-reduced-motion: reduce)').matches===true,
    prefix:'territory-'+(++territorySerial),signature:null,initialized:false,displayMode:null};
  const e=(tag,cls,text,svg)=>territoryElement(state,tag,cls,text,svg);
  state.root=e('section','territory');state.root.setAttribute('aria-label','Recorded population territory');
  const heading=e('div','territory-heading'),title=e('div');
  title.append(e('p','territory-eyebrow','SEARCH TERRITORY'),e('h2','territory-title','Population'));
  state.subtitle=e('p','territory-subtitle');title.append(state.subtitle);
  state.liveBadge=e('span','territory-state');heading.append(title,state.liveBadge);state.root.append(heading);
  const toolbar=e('div','territory-toolbar');
  state.play=e('button','territory-control','▶ Replay');state.play.type='button';state.play.setAttribute('aria-label','Play recorded population history');
  state.play.addEventListener('click',()=>territoryPlayback(state));
  state.range=e('input','territory-range');state.range.type='range';state.range.min='0';state.range.step='1';state.range.setAttribute('aria-label','Recorded population frame');
  state.range.addEventListener('input',()=>{territoryStop(state);state.follow=false;state.frameId=territoryId(state.frames[Number(state.range.value)]?.id);territoryRender(state);});
  state.frameLabel=e('span','territory-frame-label');
  state.live=e('button','territory-control territory-live','Latest');state.live.type='button';
  state.live.addEventListener('click',()=>{territoryStop(state);state.follow=true;territoryRender(state);});
  toolbar.append(state.play,state.range,state.frameLabel,state.live);state.root.append(toolbar);
  const views=e('div','territory-display-modes');state.viewButtons=views;
  for(const [mode,label]of[['storage','Storage space'],['islands','Islands']]){const b=e('button','territory-control',label);b.type='button';b.dataset.populationView=mode;b.addEventListener('click',()=>{state.displayMode=mode;territoryRender(state);});views.append(b);}state.root.append(views);
  const body=e('div','territory-body');state.membershipBody=body;state.map=e('div','territory-ocean');
  state.summary=e('div','territory-summary');state.map.append(state.summary);
  const controls=e('div','territory-visual-controls');
  const colorControls=e('div','territory-view-switch');colorControls.setAttribute('role','group');colorControls.setAttribute('aria-label','Color programs by');
  colorControls.append(e('span','territory-control-label','Color by'));
  for(const [mode,label] of [['island','Island'],['score','Score']]){const button=e('button',null,label);button.type='button';button.dataset.colorMode=mode;button.addEventListener('click',()=>{state.colorMode=mode;territoryRender(state);});colorControls.append(button);}
  controls.append(colorControls);state.map.append(controls);
  const browse=e('div','territory-browse');browse.setAttribute('aria-label','Population view controls');
  state.allIslands=e('button','territory-control','All islands');state.allIslands.type='button';state.allIslands.addEventListener('click',()=>{state.islandFilter=false;state.page=0;territoryRender(state);});
  state.previousPage=e('button','territory-control','Previous');state.previousPage.type='button';state.previousPage.setAttribute('aria-label','Previous population page');state.previousPage.addEventListener('click',()=>{state.page=Math.max(0,state.page-1);territoryRender(state);});
  state.pageLabel=e('span','territory-page-label');
  state.nextPage=e('button','territory-control','Next');state.nextPage.type='button';state.nextPage.setAttribute('aria-label','Next population page');state.nextPage.addEventListener('click',()=>{state.page++;territoryRender(state);});
  const zoomOut=e('button','territory-control','−'),zoomIn=e('button','territory-control','+');zoomOut.type=zoomIn.type='button';zoomOut.setAttribute('aria-label','Zoom out population');zoomIn.setAttribute('aria-label','Zoom in population');
  zoomOut.addEventListener('click',()=>{state.zoom=Math.max(.5,state.zoom-.25);territoryRender(state);});zoomIn.addEventListener('click',()=>{state.zoom=Math.min(2,state.zoom+.25);territoryRender(state);});state.zoomLabel=e('span','territory-zoom-label','100%');
  browse.append(state.allIslands,state.previousPage,state.pageLabel,state.nextPage,zoomOut,state.zoomLabel,zoomIn);state.map.append(browse);
  state.legend=e('div','territory-legend');state.legend.setAttribute('aria-label','Island legend');controls.append(state.legend);
  state.scoreLegend=e('div','territory-score-legend');state.map.append(state.scoreLegend);
  state.svg=e('svg','territory-svg',undefined,true);state.svg.setAttribute('role','group');state.svg.setAttribute('aria-label','Population matrix. Colored hexagons are recorded programs; neutral hexagons are unfilled retention targets.');
  const defs=e('defs',null,undefined,true),pattern=e('pattern',null,undefined,true);
  pattern.id=state.prefix+'-ocean';pattern.setAttribute('width',territoryStepX);pattern.setAttribute('height',2*territoryStepY);pattern.setAttribute('patternUnits','userSpaceOnUse');
  for(const [x,y] of [[0,0],[territoryStepX,0],[territoryStepX/2,territoryStepY],[0,2*territoryStepY],[territoryStepX,2*territoryStepY]]){const hex=e('polygon','territory-water-hex',undefined,true);hex.setAttribute('points',territoryHex(territoryRadius));hex.setAttribute('transform','translate('+x+' '+y+')');pattern.append(hex);}
  defs.append(pattern);
  const marker=e('marker',null,undefined,true);marker.id=state.prefix+'-arrow';marker.setAttribute('viewBox','0 0 10 10');marker.setAttribute('refX','8');marker.setAttribute('refY','5');marker.setAttribute('markerWidth','5');marker.setAttribute('markerHeight','5');marker.setAttribute('orient','auto-start-reverse');
  const arrow=e('path',null,undefined,true);arrow.setAttribute('d','M 1 1 L 9 5 L 1 9');arrow.setAttribute('fill','none');arrow.setAttribute('stroke','#596878');arrow.setAttribute('stroke-width','1.7');marker.append(arrow);defs.append(marker);
  state.svg.append(defs);state.water=e('rect',null,undefined,true);state.water.setAttribute('width','100%');state.water.setAttribute('height','100%');state.water.setAttribute('fill','url(#'+pattern.id+')');state.water.style.display='none';state.svg.append(state.water);
  state.clusterLayer=e('g','territory-clusters',undefined,true);state.edgeLayer=e('g','territory-migrations',undefined,true);state.cellLayer=e('g','territory-cells',undefined,true);
  state.placeholderLayer=e('g','territory-empty-slots',undefined,true);state.placeholderLayer.setAttribute('aria-hidden','true');
  state.svg.append(state.placeholderLayer,state.edgeLayer,state.cellLayer,state.clusterLayer);
  state.canvas=e('div','territory-canvas');state.canvas.append(state.svg);state.map.append(state.canvas);
  state.spawnDock=e('div','territory-spawn-dock');state.map.append(state.spawnDock);
  state.caption=e('p','territory-map-caption','Schematic layout · one colored hex per recorded program. Positions are not embeddings.');state.map.append(state.caption);
  state.limit=e('p','territory-limit');state.map.append(state.limit);
  const aside=e('aside','territory-sidebar');
  state.inspector=e('div','territory-inspector');state.inspector.setAttribute('aria-live','polite');aside.append(state.inspector);
  const asideHeading=e('div','territory-sidebar-heading');asideHeading.append(e('h3',null,'Islands'));state.islandCount=e('span','territory-count');asideHeading.append(state.islandCount);aside.append(asideHeading);
  state.list=e('div','territory-island-list');aside.append(state.list);
  state.forecast=e('div','territory-forecast');aside.append(state.forecast);
  body.append(state.map,aside);state.root.append(body);state.storageMount=e('div','territory-storage-mount');state.root.append(state.storageMount);container.append(state.root);
  state.svg.addEventListener('keydown',event=>{
    if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','Escape'].includes(event.key))return;
    if(event.key==='Escape'){state.selectedProgram=null;state.hoverProgram=null;territoryInspector(state);return;}
    const nodes=[...state.tiles.values()].filter(node=>!node.classList.contains('is-leaving'));
    const current=nodes.indexOf(event.target);if(current<0)return;
    event.preventDefault();let next=event.key==='Home'?0:event.key==='End'?nodes.length-1:current+(['ArrowLeft','ArrowUp'].includes(event.key)?-1:1);
    nodes[(next+nodes.length)%nodes.length]?.focus();
  });
  const Resize=state.doc.defaultView?.ResizeObserver;
  if(Resize){state.observer=new Resize(()=>territoryRender(state));state.observer.observe(state.map);state.observer.observe(state.root);}
  return state;
}

function territoryStop(state){if(state.timer!==null)state.doc.defaultView.clearInterval(state.timer);state.timer=null;state.playing=false;}
function territoryPlayback(state){
  if(state.playing){territoryStop(state);territoryRender(state);return;}
  if(state.frames.length<2)return;
  state.follow=false;
  if(state.frameIndex===state.frames.length-1)state.frameId=territoryId(state.frames[0].id);
  state.playing=true;territoryRender(state);
  state.timer=state.doc.defaultView.setInterval(()=>{
    if(!state.container.isConnected){territoryStop(state);return;}
    if(state.frameIndex>=state.frames.length-1){territoryStop(state);territoryRender(state);return;}
    state.frameId=territoryId(state.frames[state.frameIndex+1].id);territoryRender(state);
  },1100);
}

function territoryRender(state){
  const view=territoryView(state);state.view=view;
  const dyn=state.population.dynamics||{},islands=view.islands;
  for(const island of islands)if(!state.islandSlots.has(island.id))state.islandSlots.set(island.id,state.islandSlots.size);
  if(!islands.some(island=>island.id===state.selectedIsland))state.selectedIsland=islands[0]?.id??null;
  const shown=state.islandFilter?islands.filter(island=>island.id===state.selectedIsland):islands;
  const width=Math.max(240,state.map.clientWidth||state.container.clientWidth||760);
  const spawn=dyn.spawn||{},showSpawn=view.current&&spawn.enabled===true&&territoryNumber(spawn.lifetime_islands)!==null&&territoryNumber(spawn.max_islands)!==null&&spawn.lifetime_islands<spawn.max_islands;
  const latest=state.follow&&view.current,isLive=!!state.options.live&&state.options.follow!==false;
  state.root.classList.toggle('is-live',latest&&isLive);
  const saved=state.population.stale===true||dyn.as_of?.checkpoint_stale===true;
  territoryText(state.liveBadge,latest?(isLive?(saved?'Live · saved snapshot':'Live population'):'Latest snapshot'):'Replay');
  state.liveBadge.classList.toggle('is-live',latest&&isLive);
  territoryText(state.live,isLive?'Live':'Latest');state.live.setAttribute('aria-pressed',String(latest));
  territoryText(state.play,state.playing?'Ⅱ Pause':'▶ Replay');state.play.disabled=view.frames.length<2;
  state.range.disabled=view.frames.length<2;state.range.max=String(Math.max(0,view.frames.length-1));state.range.value=String(view.index);
  const evaluation=view.frame.evaluations??(view.current?dyn.as_of?.evaluations:null);
  const iteration=view.frame.iteration??(view.current?state.population.iteration:null);
  territoryText(state.frameLabel,(latest?'':'Replay · ')+(evaluation!==null&&evaluation!==undefined?evaluation+' evaluations':'Evaluation count not recorded'));
  state.range.setAttribute('aria-valuetext','Frame '+(view.index+1)+' of '+view.frames.length+', iteration '+(iteration??'not recorded'));
  territoryText(state.subtitle,'One hex = one stored program · '+islands.length+' recorded islands'+(saved&&view.current?' · saved at iteration '+(state.population.iteration??'unknown'):''));
  territoryText(state.islandCount,islands.length);
  const signature=JSON.stringify([view.frame.id,islands.map(island=>[island.id,island.status,island.at_risk,island.best_score,island.members.map(member=>[territoryId(member.id),member.score])])]);
  const animate=state.initialized&&signature!==state.signature&&!state.reduced&&latest&&isLive;
  const layout=new Map(),positions=new Map(),desired=new Map(),occupied=new Set(),islandCells=new Map();
  const allRecords=[],target=territoryNumber(state.population.retention?.target_members_per_island);
  let totalKnown=0,emptyTarget=0,storedCount=0,unknownCounts=false;
  for(const island of islands){const count=territoryNumber(island.member_count);storedCount+=count??island.members.length;unknownCounts ||= count===null;}
  for(const island of shown){
    const members=island.members.filter(member=>member&&territoryId(member.id));totalKnown+=members.length;
    const count=territoryNumber(island.member_count);
    if(target!==null&&count!==null)emptyTarget+=Math.max(0,Math.floor(target)-count);
    for(const member of members)allRecords.push({...member,id:territoryId(member.id),islandId:island.id,key:island.id+':'+territoryId(member.id)});
  }
  const pages=Math.max(1,Math.ceil(allRecords.length/600));state.page=Math.min(pages-1,Math.max(0,state.page));
  const records=allRecords.slice(state.page*600,(state.page+1)*600),displayed=records.length;
  state.previousPage.disabled=state.page===0;state.nextPage.disabled=state.page>=pages-1;
  state.allIslands.setAttribute('aria-pressed',String(!state.islandFilter));
  territoryText(state.pageLabel,(state.islandFilter?'Island '+state.selectedIsland+' · ':'')+'Page '+(state.page+1)+' / '+pages+' · '+displayed+' shown');
  territoryText(state.zoomLabel,Math.round(state.zoom*100)+'%');
  const layoutKey=state.frameId+':'+(state.islandFilter?state.selectedIsland:'all')+':'+state.page;
  const oldLayout=state.layouts.get(layoutKey)||state.lastLayout||new Map();
  // Stable global positions: newly recorded members fill the first free hex.
  // Neutral cells are configured target space, never invented program records.
  for(const item of records){const slot=oldLayout.get(item.key);if(slot!==undefined&&slot<600&&!occupied.has(slot)){layout.set(item.key,slot);occupied.add(slot);}}
  let next=0;for(const item of records)if(!layout.has(item.key)){while(occupied.has(next))next++;layout.set(item.key,next);occupied.add(next);}
  const placeholders=[];next=0;
  for(let i=0;i<Math.min(600,emptyTarget);i++){while(occupied.has(next))next++;placeholders.push(next);occupied.add(next++);}
  // One compact, occupancy-aware field; no decorative cells are invented.
  // All addresses remain on the same axial lattice at every viewport size.
  const availableColumns=Math.max(12,Math.min(64,Math.floor((width-48)/territoryStepX)));
  const columns=Math.min(availableColumns,Math.max(12,Math.ceil(Math.sqrt(Math.max(1,occupied.size)*1.7*territoryStepY/territoryStepX))));
  const coordinates=territoryMatrix(1201,columns);
  const rowsUsed=[...occupied].map(slot=>coordinates[slot]);
  const maxR=Math.max(0,...rowsUsed.map(([,r])=>r));
  const boardWidth=width,height=Math.max(230,(maxR+4)*territoryStepY);
  const centerR=Math.max(2,Math.round((height-maxR*territoryStepY)/(2*territoryStepY)));
  const centerQ=Math.round((width/territoryStepX-columns)/2-centerR/2);
  const cx=territoryStepX*(centerQ+centerR/2),cy=territoryStepY*centerR;
  territoryAttr(state.svg,'viewBox','0 0 '+boardWidth+' '+height);state.svg.style.width=boardWidth*state.zoom+'px';state.svg.style.height=height*state.zoom+'px';
  for(const item of records){
    const slot=layout.get(item.key),[q,r]=coordinates[slot],x=cx+territoryStepX*(q+r/2),y=cy+territoryStepY*r;
    const color=territoryColors[state.islandSlots.get(item.islandId)%territoryColors.length];
    desired.set(item.key,{...item,color,radius:territoryRadius,x,y});positions.set(item.key,{x,y});
    if(!islandCells.has(item.islandId))islandCells.set(item.islandId,new Set());islandCells.get(item.islandId).add(slot);
  }
  const placeholderSet=new Set(placeholders);
  for(const [slot,node] of state.placeholderTiles)if(!placeholderSet.has(slot)){node.remove();state.placeholderTiles.delete(slot);}
  for(const slot of placeholders){let node=state.placeholderTiles.get(slot);if(!node){node=territoryElement(state,'polygon','territory-empty-slot',undefined,true);node.setAttribute('points',territoryHex(territoryRadius));state.placeholderLayer.append(node);state.placeholderTiles.set(slot,node);}
    const [q,r]=coordinates[slot];territoryAttr(node,'transform','translate('+(cx+territoryStepX*(q+r/2)).toFixed(4)+' '+(cy+territoryStepY*r).toFixed(4)+')');}
  const scores=records.map(item=>territoryMetric(state,item)).filter(value=>value!==null);
  state.scoreExtent=scores.length?[Math.min(...scores),Math.max(...scores)]:null;
  for(const island of shown){
    let cluster=state.clusters.get(island.id);
    if(!cluster){cluster=territoryElement(state,'g','territory-cluster',undefined,true);cluster.dataset.island=island.id;
      cluster.append(territoryElement(state,'path','territory-boundary',undefined,true));state.clusterLayer.append(cluster);state.clusters.set(island.id,cluster);}
    territoryAttr(cluster.children[0],'d',territoryBoundary(islandCells.get(island.id)||new Set(),coordinates));
    territoryAttr(cluster,'transform','translate('+cx+' '+cy+')');cluster.style.setProperty('--island-color',territoryColors[state.islandSlots.get(island.id)%territoryColors.length]);
    cluster.classList.toggle('is-selected',state.selectedIsland===island.id);cluster.classList.toggle('is-retired',island.status==='retired');cluster.classList.toggle('is-risk',view.current&&island.at_risk===true);
  }
  const slots=new Set(shown.map(island=>island.id));
  territoryOverview(state,{storedCount,unknownCounts,emptyTarget,displayed,shown});
  for(const [id,cluster] of state.clusters)if(!slots.has(id)){cluster.remove();state.clusters.delete(id);}
  state.layout=layout;state.lastLayout=layout;state.layouts.set(layoutKey,layout);while(state.layouts.size>60)state.layouts.delete(state.layouts.keys().next().value);
  state.positions=positions;state.members=desired;
  for(const [key,node] of state.tiles)if(!desired.has(key)){
    state.tiles.delete(key);node.removeAttribute('tabindex');node.setAttribute('aria-hidden','true');
    if(animate&&state.cellLayer.children.length+Math.max(0,desired.size-state.tiles.size)<=600){node.classList.add('is-leaving');const timer=state.doc.defaultView.setTimeout(()=>{node.remove();state.timers.delete(timer);},350);state.timers.add(timer);}else node.remove();
  }
  for(const [key,item] of desired){let node=state.tiles.get(key);
    if(!node){node=territoryElement(state,'g','territory-cell',undefined,true);node.dataset.program=item.id;node.dataset.island=item.islandId;node.setAttribute('role','button');node.setAttribute('tabindex','0');
      node.append(territoryElement(state,'polygon','territory-tile',undefined,true),territoryElement(state,'circle','territory-elite',undefined,true),territoryElement(state,'title',null,undefined,true));
      node.children[1].setAttribute('r','1.25');node.children[1].setAttribute('cy','0');
      node.addEventListener('pointerenter',()=>{state.hoverProgram=key;territoryInspector(state);});node.addEventListener('pointerleave',()=>{state.hoverProgram=null;territoryInspector(state);});
      node.addEventListener('focus',()=>{state.hoverProgram=key;territoryInspector(state);});node.addEventListener('blur',()=>{state.hoverProgram=null;territoryInspector(state);});
      const choose=()=>{state.selectedProgram=key;state.selectedIsland=item.islandId;territorySelection(state);territoryInspector(state);};node.addEventListener('click',choose);node.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}});
      if(animate)node.classList.add('is-born');state.cellLayer.append(node);state.tiles.set(key,node);
    }
    territoryAttr(node,'transform','translate('+item.x.toFixed(4)+' '+item.y.toFixed(4)+')');territoryAttr(node.children[0],'points',territoryHex(item.radius));node.style.setProperty('--island-color',territoryCellColor(state,item));
    node.children[1].style.display=item.grid_elite===true?'':'none';
    const label=item.id+' · Island '+item.islandId+' · '+(state.options.metricLabel||'Score')+' '+territoryScore(state,item.score,item);
    territoryAttr(node,'aria-label',label);territoryText(node.children[2],label);node.classList.toggle('is-retired',islands.find(island=>island.id===item.islandId)?.status==='retired');
  }
  if(state.selectedProgram&&!desired.has(state.selectedProgram))state.selectedProgram=null;
  territorySpawn(state,showSpawn?{spawn}:null);
  territoryMigrations(state,view.current?territoryArray(dyn.migrations):territoryArray(view.frame.migrations));
  territorySidebar(state);territorySelection(state);territoryInspector(state);territoryForecast(state);
  const hidden=Math.max(0,totalKnown-displayed),extra=Math.max(0,islands.length-shown.length),unprojected=shown.reduce((sum,island)=>sum+Math.max(0,(territoryNumber(island.member_count)??island.members.length)-island.members.length),0);
  territoryText(state.limit,[unprojected?unprojected+' stored member IDs are outside the per-island snapshot projection cap.':'',hidden?hidden+' recorded programs outside the 600-cell display cap. Use pages or select an island.':'',extra?extra+' islands outside this view; select one in the sidebar.':'',dyn.history_limited?'Replay shows a bounded window of recorded snapshots.':'',!view.current?'Historical member scores are shown only when recorded in that frame.':''].filter(Boolean).join(' '));state.limit.hidden=!state.limit.textContent;
  state.signature=signature;state.initialized=true;
  const storage=typeof state.options.storageRenderer==='function'&&state.population.storage?.schema==='sciel-population-storage/1';
  state.viewButtons.hidden=!storage;
  if(state.displayMode===null&&storage)state.displayMode=state.population.storage.kind==='unknown'?'islands':'storage';
  const showStorage=storage&&state.displayMode==='storage';
  if(showStorage)territoryText(state.subtitle,'Recorded storage geometry · '+islands.length+' islands · '+(view.current?'saved coordinates':'historical frame'));
  state.membershipBody.hidden=showStorage;state.storageMount.hidden=!showStorage;
  for(const b of state.viewButtons.children)b.setAttribute('aria-pressed',String(b.dataset.populationView===(showStorage?'storage':'islands')));
  if(showStorage)state.storageControl=state.options.storageRenderer(state.storageMount,state.population,{...state.options,current:view.current});
}

function territoryCellColor(state,item){
  if(state.colorMode!=='score')return item.color;
  const value=territoryMetric(state,item);
  if(value===null||!state.scoreExtent)return '#cdd1d9';
  const [low,high]=state.scoreExtent,colors=['#dbe1fc','#acb9ef','#b18bdd','#d59bcb','#efb632'];
  const fraction=high===low?.5:Math.min(1,Math.max(0,(value-low)/(high-low)));
  return colors[Math.min(4,Math.floor(fraction*5))];
}
function territoryOverview(state,info){
  const e=(tag,cls,text)=>territoryElement(state,tag,cls,text);
  const members=state.view.islands.flatMap(island=>island.members);
  const elites=members.some(member=>typeof member.grid_elite==='boolean')?members.filter(member=>member.grid_elite===true).length:'—';
  const summary=[['Retained programs',info.unknownCounts?(info.storedCount?'≥ '+info.storedCount:'—'):info.storedCount],['Islands',state.view.islands.length],['Cell elites',elites]];
  const sources=state.view.current?state.population.source_summary:null;
  if(sources)summary.push(['Unique sources (saved)',sources.complete===true?sources.unique_sources:'Unknown']);
  state.summary.replaceChildren(...summary.map(([label,value])=>{const cell=e('div','territory-summary-item');cell.append(e('strong',null,value),e('span',null,label));return cell;}));
  for(const button of state.root.querySelectorAll('[data-color-mode]'))button.setAttribute('aria-pressed',String(button.dataset.colorMode===state.colorMode));
  const existing=new Map([...state.legend.children].map(node=>[node.dataset.island,node]));
  for(const island of state.view.islands){let button=existing.get(island.id);existing.delete(island.id);if(!button){button=e('button','territory-legend-item');button.type='button';button.dataset.island=island.id;button.append(e('span',null,'Island '+island.id),e('span','count'));button.addEventListener('click',()=>{state.islandFilter=!(state.islandFilter&&state.selectedIsland===island.id);state.selectedIsland=island.id;state.selectedProgram=null;state.page=0;territoryRender(state);});state.legend.append(button);}
    button.style.setProperty('--island-color',territoryColors[state.islandSlots.get(island.id)%territoryColors.length]);territoryText(button.children[1],island.member_count??'—');button.setAttribute('aria-pressed',String(state.islandFilter&&state.selectedIsland===island.id));}
  for(const node of existing.values())node.remove();
  state.scoreLegend.hidden=state.colorMode!=='score';state.scoreLegend.replaceChildren();
  if(state.colorMode==='score'){state.scoreLegend.append(e('span',null,state.options.metricLabel||'Score'),e('span',null,state.scoreExtent?territoryScore(state,state.scoreExtent[0]):'Not recorded'),e('span','territory-score-ramp'),e('span',null,state.scoreExtent?territoryScore(state,state.scoreExtent[1]):'Not recorded'));state.scoreLegend.querySelector('.territory-score-ramp').style.setProperty('--score-gradient','linear-gradient(90deg,#dbe1fc 0% 20%,#acb9ef 20% 40%,#b18bdd 40% 60%,#d59bcb 60% 80%,#efb632 80% 100%)');}
  const retention=state.population.retention||{},targetNote=info.emptyTarget>0?' Neutral cells = unfilled '+(retention.limit_kind==='soft'?'soft ':'')+'retention target ('+Math.min(600,info.emptyTarget)+' shown of '+info.emptyTarget+').':'';
  territoryText(state.caption,'Schematic layout · one colored hex per recorded program.'+targetNote+' Positions are not embedding coordinates.'+(sources?' Exact-source coverage: '+sources.source_bound_members+' / '+(sources.member_count??'unknown')+' saved members; '+sources.known_identical_source_copies+' known identical-source copies.':''));
}

function territorySpawn(state,view){
  state.spawnDock.hidden=!view;if(!view){state.spawnDock.replaceChildren();state.spawnNode=null;return;}
  if(!state.spawnNode){const e=(tag,cls,text)=>territoryElement(state,tag,cls,text),box=e('div','territory-spawn');
    const glyph=e('span','territory-spawn-glyph','+');glyph.setAttribute('aria-hidden','true');const info=e('div','territory-spawn-info');
    info.append(e('h3',null,'Conditional next island'),e('p','territory-spawn-copy'));const track=e('div','territory-spawn-track'),fill=e('span');track.append(fill);track.setAttribute('role','progressbar');track.setAttribute('aria-label','Recorded evaluations toward the stall threshold');info.append(track,e('p','territory-spawn-count'));
    box.append(glyph,info);state.spawnDock.append(box);state.spawnNode=box;}
  const spawn=view.spawn,info=state.spawnNode.children[1],remaining=territoryNumber(spawn.remaining_evaluations),count=territoryNumber(spawn.stall_evaluations),threshold=territoryNumber(spawn.stall_threshold);
  territoryText(info.children[1],remaining===0?'Stall threshold reached · guards still apply':remaining!==null?remaining+' evaluations to stall threshold':'Evaluation threshold not recorded');
  const known=count!==null&&threshold!==null&&threshold>0,track=info.children[2];track.hidden=!known;
  if(known){const value=Math.max(0,Math.min(threshold,count));track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax',String(threshold));track.setAttribute('aria-valuenow',String(value));track.children[0].style.width=(value/threshold*100)+'%';}
  territoryText(info.children[3],known?count+' / '+threshold+' evaluations · all guards must pass':'All recorded guards must pass.');
}
function territoryMigrations(state,migrations){
  state.migrationRows=migrations;state.edgeLayer.replaceChildren();let shown=0,available=0;
  const selected=state.hoverProgram||state.selectedProgram;
  for(const edge of migrations.slice(-120)){
    const from=state.positions.get(territoryId(edge.from_island)+':'+territoryId(edge.parent_id??edge.from_program_id));
    const to=state.positions.get(territoryId(edge.to_island)+':'+territoryId(edge.program_id??edge.to_program_id));
    if(!from||!to||from===to)continue;
    available++;
    if(selected!==territoryId(edge.from_island)+':'+territoryId(edge.parent_id??edge.from_program_id)&&selected!==territoryId(edge.to_island)+':'+territoryId(edge.program_id??edge.to_program_id))continue;
    const line=territoryElement(state,'path','territory-migration',undefined,true);
    const dx=to.x-from.x,dy=to.y-from.y,distance=Math.hypot(dx,dy);if(distance<1)continue;
    const ex=to.x-dx/distance*14,ey=to.y-dy/distance*14;
    line.setAttribute('d','M '+from.x+' '+from.y+' Q '+((from.x+to.x)/2)+' '+((from.y+to.y)/2-35)+' '+ex+' '+ey);
    line.setAttribute('marker-end','url(#'+state.prefix+'-arrow)');line.dataset.from=territoryId(edge.parent_id??edge.from_program_id);line.dataset.to=territoryId(edge.program_id??edge.to_program_id);
    const title=territoryElement(state,'title',null,'Recorded migration: '+line.dataset.from+' → '+line.dataset.to,true);line.append(title);state.edgeLayer.append(line);shown++;
  }
  state.migrationCount=shown;state.availableMigrationCount=available;
}
function territorySidebar(state){
  const existing=new Map([...state.list.children].map(node=>[node.dataset.island,node]));
  for(const island of state.view.islands){let button=existing.get(island.id);existing.delete(island.id);
    if(!button){button=territoryElement(state,'button','territory-island');button.type='button';button.dataset.island=island.id;
      button.append(territoryElement(state,'span','territory-island-dot'),territoryElement(state,'span','territory-island-name'),territoryElement(state,'span','territory-island-meta'));
      button.addEventListener('click',()=>{state.selectedIsland=island.id;state.selectedProgram=null;state.hoverProgram=null;state.islandFilter=true;state.page=0;territoryRender(state);});state.list.append(button);}
    button.style.setProperty('--island-color',territoryColors[state.islandSlots.get(island.id)%territoryColors.length]);territoryText(button.children[1],'Island '+island.id);
    const status=(island.status||'unknown')+(island.status_stale===true?' · saved':'');territoryText(button.children[2],(island.member_count??'—')+' · '+status);button.title='Best '+(state.options.metricLabel||'score')+': '+territoryScore(state,island.best_score,island,'best_metric_display');
  }
  for(const node of existing.values())node.remove();
}
function territorySelection(state){
  for(const [key,node] of state.tiles){node.classList.toggle('is-selected',key===state.selectedProgram);node.classList.toggle('is-muted',state.islandFilter&&state.selectedIsland!==null&&node.dataset.island!==state.selectedIsland);node.setAttribute('aria-pressed',String(key===state.selectedProgram));}
  for(const [id,node] of state.clusters)node.classList.toggle('is-selected',id===state.selectedIsland);
  for(const node of state.list.children)node.setAttribute('aria-pressed',String(node.dataset.island===state.selectedIsland));
  for(const node of state.legend.children)node.setAttribute('aria-pressed',String(state.islandFilter&&node.dataset.island===state.selectedIsland));
}
function territoryInspector(state){
  territoryMigrations(state,state.migrationRows||[]);
  const item=state.members?.get(state.hoverProgram||state.selectedProgram),island=state.view?.islands.find(row=>row.id===(item?.islandId??state.selectedIsland));
  const signature=JSON.stringify([item,island?.id,island?.status,island?.status_stale,island?.membership_stale,island?.best_score,island?.best_metric_display,island?.member_count,state.options.metricLabel]);if(signature===state.inspectorSignature)return;state.inspectorSignature=signature;
  state.inspector.replaceChildren();const e=(tag,cls,text)=>territoryElement(state,tag,cls,text);
  state.inspector.append(e('p','territory-card-kicker',item?'PROGRAM':'SELECTED ISLAND'),e('h3','territory-card-title',item?item.id:island?'Island '+island.id:'No recorded islands'));
  const label=state.options.metricLabel||'Score';state.inspector.append(e('p','territory-card-score',label+' '+territoryScore(state,item?item.score:island?.best_score,item||island,item?'metric_display':'best_metric_display')));
  if(item){const roles=[item.grid_elite===true?'Cell elite':null,item.archive_member===true?'Archive member':null,item.generation!==null&&item.generation!==undefined?'Generation '+item.generation:null].filter(Boolean);
    state.inspector.append(e('p','territory-card-copy','Island '+item.islandId+(roles.length?' · '+roles.join(' · '):'')));
    const fields=e('dl','territory-card-fields');
    for(const [name,value] of [['Parent',item.parent_id],['Origin',item.origin]])if(value!==null&&value!==undefined&&value!==''){
      const row=e('div');row.append(e('dt',null,name),e('dd',null,value));fields.append(row);
    }
    if(fields.children.length)state.inspector.append(fields);
    const actions=e('div','territory-card-actions');for(const [action,text] of [['source','Open source'],['diff','Parent diff']]){
      const button=e('button','territory-control',text);button.type='button';button.disabled=item.code_available!==true||typeof state.options.onProgram!=='function';
      button.addEventListener('click',()=>state.options.onProgram(item.id,{islandId:item.islandId,action}));actions.append(button);}
    state.inspector.append(actions);if(item.code_available!==true)state.inspector.append(e('p','territory-card-copy','Source availability is not recorded in this frame.'));
  }else{state.inspector.append(e('p','territory-card-copy',island?(island.member_count===null||island.member_count===undefined?'Members not recorded.':island.member_count+' stored members. Select or focus a hex to inspect a program.'):'Stored programs will appear when membership is recorded.'));
    if(island?.status_stale===true)state.inspector.append(e('p','territory-card-copy','Status: '+island.status+' · saved scheduler state; it may have changed.'));
    if(island?.membership_stale===true)state.inspector.append(e('p','territory-card-copy','Membership is from an earlier saved snapshot.'));
  }
}
function territoryForecast(state){
  const guardsOpen=state.forecast.querySelector('details')?.open===true;
  state.forecast.replaceChildren();if(!state.view.current)return;
  const dyn=state.population.dynamics||{},cut=dyn.next_cut||{},spawn=dyn.spawn||{},e=(tag,cls,text)=>territoryElement(state,tag,cls,text);
  if(cut.status==='conditional'){
    const asOf=territoryNumber(cut.forecast_as_of?.evaluations);
    state.forecast.append(e('p','territory-card-kicker','CONDITIONAL CUT'),e('p','territory-forecast-title',territoryNumber(cut.evaluations_remaining)!==null?cut.evaluations_remaining+' evaluations to milestone'+(asOf!==null?' · as of evaluation '+asOf:''):'Milestone timing not recorded'),e('p','territory-card-copy','Amber outlines show recorded risk, subject to ranking and fairness guards.'));
    if(cut.forecast_as_of?.stale)state.forecast.append(e('p','territory-stale','Earlier forecast · saved at '+(cut.forecast_as_of.evaluations??'unknown')+' evaluations. Risk uses that saved scheduler state.'));
  }
  if(spawn.enabled===true){
    const guards=territoryArray(spawn.guards).slice(0,6),details=e('details','territory-guards');details.open=guardsOpen;
    details.append(e('summary',null,'Spawn guards · '+guards.filter(guard=>guard.satisfied===true).length+'/'+guards.length+' met'));
    for(const guard of guards)details.append(e('p','territory-guard',(guard.satisfied===true?'✓ ':guard.satisfied===false?'○ ':'? ')+String(guard.label||'Condition not recorded')));
    details.append(e('p','territory-card-copy','A threshold is conditional, not a promise of a new island.'));state.forecast.append(details);
  }
  if(state.availableMigrationCount)state.forecast.append(e('p','territory-card-copy',state.availableMigrationCount+' recorded migration links in this view. Hover or select a program to see its links.'));
  state.forecast.hidden=!state.forecast.children.length;
}

export function renderPopulationMap(container,population,options={}){
  if(!container)return null;
  let state=territoryStates.get(container);
  if(state&&state.runKey!==options.runKey){destroyPopulationMap(container);state=null;}
  if(!state){state=territoryCreate(container,options);territoryStates.set(container,state);}
  state.population=population||{};state.options=options;territoryRender(state);
  return {destroy:()=>destroyPopulationMap(container),selectIsland:id=>{state.selectedIsland=territoryId(id);state.selectedProgram=null;territoryRender(state);},
    selectFrame:id=>{territoryStop(state);state.follow=false;state.frameId=territoryId(id);territoryRender(state);}};
}
export function destroyPopulationMap(container){
  const state=territoryStates.get(container);if(!state)return;
  state.storageControl?.destroy();
  territoryStop(state);state.observer?.disconnect();for(const timer of state.timers)state.doc.defaultView.clearTimeout(timer);state.root.remove();territoryStates.delete(container);
}
