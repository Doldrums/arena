/* Storage geometry from recorded bins/vectors only. Camera transforms are visual. */
const spaces=new WeakMap(),ns='http://www.w3.org/2000/svg';
const colors=['#aaa7e8','#93b3ee','#e8c16c','#c6a2e1','#a6c8e9','#98cad3'];
const list=x=>Array.isArray(x)?x:[],finite=x=>typeof x==='number'&&Number.isFinite(x),id=x=>x==null?'':String(x);
function element(s,tag,cls,text,svg=false){const e=svg?s.doc.createElementNS(ns,tag):s.doc.createElement(tag);if(cls)e.setAttribute('class',cls);if(text!==undefined)e.textContent=String(text);return e;}
function attributes(e,values){for(const[k,v]of Object.entries(values))e.setAttribute(k,String(v));return e;}
function control(s,label,action){const b=element(s,'button','territory-control',label);b.type='button';b.addEventListener('click',action);return b;}
function format(s,value,row){return s.options.formatScore?String(s.options.formatScore(value,row)):finite(value)?value.toFixed(5):'Not recorded';}
function create(container){
  const s={container,doc:container.ownerDocument,island:'all',yaw:35,elevation:35,flat:false,selected:null,signature:null,spaceMode:'auto'};
  const e=(...a)=>element(s,...a);s.root=e('section','storage-space');s.root.setAttribute('aria-label','Recorded storage space');
  s.heading=e('div','storage-heading');s.name=e('h3');s.description=e('p');s.heading.append(s.name,s.description);
  const body=e('div','storage-body'),left=e('div','storage-main');s.toolbar=e('div','storage-toolbar');
  const label=e('label','storage-filter','Island ');s.filter=e('select');s.filter.setAttribute('aria-label','Storage island');label.append(s.filter);
  s.filter.addEventListener('change',()=>{s.island=s.filter.value;s.selected=null;draw(s);});
  s.three=control(s,'3D',()=>{s.flat=false;draw(s);});s.two=control(s,'2D',()=>{s.flat=true;draw(s);});
  s.cells=control(s,'Archive cells',()=>{s.spaceMode='cells';s.selected=null;draw(s);});s.vectors=control(s,'Vector space',()=>{s.spaceMode='vectors';s.selected=null;draw(s);});
  s.toolbar.append(label,s.cells,s.vectors,s.three,s.two);s.metrics=e('span','storage-metrics');s.toolbar.append(s.metrics);
  s.stage=e('div','storage-stage');s.svg=e('svg','storage-svg',undefined,true);s.svg.setAttribute('role','group');s.svg.setAttribute('aria-label','Recorded storage coordinates');s.stage.append(s.svg);
  s.empty=e('p','storage-empty');s.stage.append(s.empty);
  s.pool=e('div','storage-pool');s.stage.append(s.pool);
  s.camera=e('div','storage-camera');
  for(const [key,title,min,max]of[['yaw','Rotate',-180,180],['elevation','Tilt',15,75]]){
    const label=e('label',null,title),range=e('input');range.type='range';range.min=min;range.max=max;range.step=1;range.value=s[key];range.setAttribute('aria-label',title+' storage space');
    range.addEventListener('input',()=>{s[key]=Number(range.value);draw(s);});label.append(range);s.camera.append(label);s[key+'Input']=range;
  }
  s.camera.append(control(s,'Reset',()=>{s.yaw=35;s.elevation=35;s.flat=false;s.yawInput.value=35;s.elevationInput.value=35;draw(s);}));
  s.caption=e('p','storage-caption');left.append(s.toolbar,s.stage,s.camera,s.caption);
  s.inspector=e('aside','storage-inspector');s.inspector.setAttribute('aria-live','polite');body.append(left,s.inspector);
  s.root.append(s.heading,body);container.append(s.root);return s;
}
function members(s){return s.memberRows||[];}
function assignments(s){return list(s.projected?s.model.projection?.assignments:s.model.assignments).filter(a=>s.island==='all'||id(a.island_id)===s.island);}
function indexBindings(s){
  s.boundNiches=new Map();for(const a of assignments(s))for(const key of['*:'+id(a.niche_id),id(a.island_id)+':'+id(a.niche_id)]){if(!s.boundNiches.has(key))s.boundNiches.set(key,[]);s.boundNiches.get(key).push(a);}
}
function nativePoints(s){
  const native=[];for(const island of list(s.population.islands)){
    if(s.island!=='all'&&id(island.id)!==s.island)continue;
    for(const cell of list(island.grid))if(finite(cell.x)&&finite(cell.y))native.push({
      key:'cell:'+island.id+':'+cell.x+':'+cell.y,kind:'cell',island_id:island.id,
      program_id:cell.candidate_id,score:cell.score,metric_display:cell.metric_display,cell:[cell.x,cell.y],niche_id:s.model.kind==='vq_elites'?cell.x:null,
      position:[cell.x,cell.y,0]});
  }s.nativeTotal=native.length;return native.slice(0,2048);
}
function geometry(s){
  const projection=s.model.projection||{},projected=projection.available===true&&s.spaceMode!=='cells';
  if(projected){
    const points=list(projection.points).filter(p=>list(p.position).length===3&&p.position.every(finite)&&
      (s.island==='all'||p.island_id==null||id(p.island_id)===s.island)).slice(0,1024).map(p=>({...p,key:'projected:'+id(p.id)}));
    // One shared scale preserves the relative projected aspect ratio.
    const all=list(projection.points).filter(p=>list(p.position).length===3&&p.position.every(finite));
    const low=[0,1,2].map(i=>all.length?Math.min(...all.map(p=>p.position[i])):0),high=[0,1,2].map(i=>all.length?Math.max(...all.map(p=>p.position[i])):1);
    const span=Math.max(...high.map((v,i)=>v-low[i]),1e-12);
    return {points:points.map(p=>({...p,world:p.position.map((v,i)=>(v-(low[i]+high[i])/2)/span)})),projected:true,
      axes:list(projection.axes).length?projection.axes:['PC1','PC2','PC3'],projection};
  }
  const points=nativePoints(s),islands=list(s.population.islands).map(x=>id(x.id));
  const bins=s.model.bins,defaultBins=s.population.layout?.grid_bins;
  const binMax=i=>Math.max(1,(finite(bins?.[['x','y'][i]])?bins[['x','y'][i]]:finite(defaultBins)?defaultBins:1)-1,...points.map(p=>p.cell[i]));
  const xMax=binMax(0),yMax=binMax(1),layers=Math.max(1,islands.length-1);
  return {points:points.map(p=>({...p,world:[(p.cell[0]+.5)/(xMax+1)-.5,(p.cell[1]+.5)/(yMax+1)-.5,s.island==='all'?islands.indexOf(id(p.island_id))/layers-.5:-.5]})),
    projected:false,axes:[s.model.axes?.[0]?.label||'Descriptor bin',s.model.axes?.[1]?.label||'Unused row','Island (categorical)'],xMax,yMax,islands};
}
function camera(s,width,height){
  const yaw=(s.flat?0:s.yaw)*Math.PI/180,tilt=(s.flat?90:s.elevation)*Math.PI/180;
  const rotate=([x,y,z])=>{if(s.flat)return [x,-y,0];const a=x*Math.cos(yaw)-y*Math.sin(yaw),b=x*Math.sin(yaw)+y*Math.cos(yaw);return [a,b*Math.sin(tilt)-z*Math.cos(tilt),b*Math.cos(tilt)+z*Math.sin(tilt)];};
  const bounds=[];for(const x of[-.65,.65])for(const y of[-.65,.65])for(const z of[-.65,.65])bounds.push(rotate([x,y,z]));
  const span=i=>Math.max(...bounds.map(p=>p[i]))-Math.min(...bounds.map(p=>p[i]));
  const scale=Math.min((width-105)/span(0),(height-60)/span(1));
  return point=>{const[a,b,depth]=rotate(point);return [width/2+a*scale,height*.5+b*scale,depth];};
}
function line(s,from,to,cls){const p=s.project(from),q=s.project(to);return attributes(element(s,'line',cls,undefined,true),{x1:p[0],y1:p[1],x2:q[0],y2:q[1]});}
function drawAxes(s,g){
  const base=[-.55,-.55,-.55],ends=[[.62,-.55,-.55],[-.55,.62,-.55],[-.55,-.55,.62]];
  for(let i=0;i<(s.flat?2:3);i++){
    s.svg.append(line(s,base,ends[i],'storage-axis'));const at=s.project(ends[i]);
    const label=element(s,'text','storage-axis-label',typeof g.axes[i]==='object'?g.axes[i].label:g.axes[i],true);
    attributes(label,{x:at[0]+4,y:at[1]-6,'text-anchor':at[0]>Number(s.svg.viewBox?.baseVal?.width||s.stage.clientWidth||640)*.7?'end':'start'});s.svg.append(label);
  }
  if(g.projected){
    for(let i=0;i<=4;i++){const t=-.5+i/4;s.svg.prepend(line(s,[t,-.5,-.5],[t,.5,-.5],'storage-guide'));s.svg.prepend(line(s,[-.5,t,-.5],[.5,t,-.5],'storage-guide'));}
  }else{
    const islands=s.island==='all'?g.islands:[s.island],visibleLayers=s.flat?[islands[0]]:islands;
    for(const island of visibleLayers){
      const z=s.island==='all'?g.islands.indexOf(island)/Math.max(1,g.islands.length-1)-.5:-.5;
      for(const [a,b]of[[[-.5,-.5],[.5,-.5]],[[.5,-.5],[.5,.5]],[[.5,.5],[-.5,.5]],[[-.5,.5],[-.5,-.5]]])s.svg.prepend(line(s,[...a,z],[...b,z],'storage-layer'));
      if(islands.length<=1||s.flat){for(let i=1;i<Math.min(g.xMax+1,20);i++)s.svg.prepend(line(s,[i/(g.xMax+1)-.5,-.5,z],[i/(g.xMax+1)-.5,.5,z],'storage-guide'));for(let i=1;i<Math.min(g.yMax+1,20);i++)s.svg.prepend(line(s,[-.5,i/(g.yMax+1)-.5,z],[.5,i/(g.yMax+1)-.5,z],'storage-guide'));}
    }
  }
}
function matching(s,p){
  if(p.kind==='cell'&&!p.program_id)return [];
  if(p.program_id){const m=s.memberIndex.get(id(p.island_id)+':'+id(p.program_id));return m?[{...m,score:Object.hasOwn(p,'score')?p.score:m.score,metric_display:Object.hasOwn(p,'score')?p.metric_display:m.metric_display}]: [{id:p.program_id,island_id:p.island_id,score:p.score,metric_display:p.metric_display,code_available:false}];}
  return (s.boundNiches.get((p.island_id==null?'*':id(p.island_id))+':'+id(p.niche_id))||[]).map(a=>{
    const member=s.memberIndex.get(id(a.island_id)+':'+id(a.program_id));return {...member,...a,id:a.program_id,metric_display:Object.hasOwn(a,'score')?a.metric_display:member?.metric_display};
  });
}
function inspect(s,p){
  s.inspector.replaceChildren();const e=(...a)=>element(s,...a);
  s.inspector.append(e('p','territory-card-kicker',p?'RECORDED STORAGE':'HOW TO READ THIS VIEW'));
  if(!p){
    s.inspector.append(e('h3',null,s.model.kind==='pool'?'Stored membership':s.projected?'Saved vector space':'Archive cells'));
    s.inspector.append(e('p','storage-copy',s.model.kind==='pool'?'Programs are listed by saved membership. This store has no geometric partition.':s.projected?'Each ring is a saved centroid. Filled points, when available, are programs with saved vectors. Select a mark to inspect its recorded bindings.':'Each mark is one occupied storage cell in an island. The third axis separates islands; it is not an embedding dimension. Select a cell to inspect its elite.'));
    if(s.model.kind==='vq_elites')s.inspector.append(e('p','storage-copy','VQ niche IDs are categories. Their numeric order does not measure similarity. Score bins remain a separate storage axis.'));
    const evidence=s.projected?s.model.projection:s.model;
    const rows=[['Stored programs',list(s.population.islands).reduce((n,i)=>n+(finite(i.member_count)?i.member_count:0),0)],['Recorded cell bindings',assignments(s).length],['Coordinates from',evidence.source||'Unknown'],['At iteration',evidence.iteration??'Unknown']];
    const dl=e('dl','territory-card-fields');for(const[k,v]of rows){const row=e('div');row.append(e('dt',null,k),e('dd',null,v));dl.append(row);}s.inspector.append(dl);
  }else{
    const title=p.kind==='cell'?'Cell ['+p.cell.join(', ')+'] · Island '+p.island_id:p.kind==='centroid'?'Centroid '+id(p.niche_id??p.id):id(p.program_id||p.id);
    s.inspector.append(e('h3',null,title));
    if(p.kind==='cell')s.inspector.append(e('p','storage-copy',(s.options.metricLabel||'Score')+' '+format(s,p.score,p)));
    if(p.kind==='cell'&&!p.program_id)s.inspector.append(e('p','storage-copy','The journal recorded this cell and score, but did not record its elite ID.'));
    const bound=matching(s,p);s.inspector.append(e('p','storage-copy',bound.length+' recorded program binding'+(bound.length===1?'':'s')+(p.kind==='centroid'?' · non-elite membership may be unavailable.':'.')));
    const entries=e('div','storage-bound-programs');for(const m of bound.slice(0,256)){
      const item=e('div','storage-program');item.append(e('strong',null,id(m.id)),e('span',null,'Island '+id(m.island_id)+' · '+format(s,m.score,m)));
      const actions=e('div','territory-card-actions');for(const[action,label]of[['source','Source'],['diff','Diff']]){const b=control(s,label,()=>s.options.onProgram?.(id(m.id),{action,islandId:id(m.island_id)}));b.disabled=m.code_available!==true||typeof s.options.onProgram!=='function';actions.append(b);}item.append(actions);entries.append(item);
    }s.inspector.append(entries);
  }
  const details=e('details','storage-notes');details.append(e('summary',null,'Coordinate details'));
  for(const note of list(s.model.notes).slice(0,5))details.append(e('p','storage-footnote',note));
  if(s.projected)for(const note of list(s.model.projection?.notes).slice(0,3))details.append(e('p','storage-footnote',note));s.inspector.append(details);
}
function draw(s){
  s.model=s.population.storage||{};
  const kind=s.model.kind,projection=s.model.projection||{},known=['map_elites','vq_elites','cvt','vq','annealed','pool'].includes(kind),projected=projection.available===true&&s.spaceMode!=='cells';
  s.name.textContent=s.model.label||'Storage not recorded';
  const dimensional=projected?(projection.input_dimensions+'D saved vectors → '+projection.output_dimensions+'D '+String(projection.method||'projection').toUpperCase()+' · rank '+projection.projected_rank):kind==='map_elites'?'Descriptor bin × score bin · islands as categorical layers':kind==='vq_elites'?'Niche ID × score bin · categorical archive coordinates':kind==='pool'?'Stored membership · no geometric partition':known?'Centre ID × island · unused grid row':'Storage metadata unavailable';
  const gridSize=kind==='map_elites'&&finite(s.model.bins?.x)&&finite(s.model.bins?.y)?s.model.bins.x+' × '+s.model.bins.y+' cells per island · ':'';
  s.description.textContent=gridSize+dimensional+((projected?projection.stale:s.model.stale)?' · earlier saved geometry':'');
  const visible=s.options.current!==false&&known;
  s.toolbar.hidden=!visible;s.camera.hidden=!visible||kind==='pool';s.svg.toggleAttribute('hidden',!visible||kind==='pool');s.pool.hidden=!visible||kind!=='pool';s.empty.hidden=visible;
  s.empty.textContent=s.options.current===false?'Storage coordinates were not saved for this replay frame. Use Islands to replay recorded membership.':'No storage coordinates were recorded for this snapshot. The Islands view still shows saved membership.';
  if(!visible){s.svg.replaceChildren();s.inspector.replaceChildren();s.caption.textContent='No current geometry is substituted into an earlier frame.';return;}
  s.three.setAttribute('aria-pressed',String(!s.flat));s.two.setAttribute('aria-pressed',String(s.flat));s.three.hidden=s.two.hidden=kind==='pool';
  s.cells.hidden=s.vectors.hidden=projection.available!==true;s.cells.setAttribute('aria-pressed',String(!projected));s.vectors.setAttribute('aria-pressed',String(projected));
  s.elevationInput.disabled=s.flat;s.yawInput.disabled=s.flat;
  if(kind==='pool'){
    s.pool.replaceChildren();const rows=members(s).filter(m=>s.island==='all'||id(m.island_id)===s.island).slice(0,600);
    for(const m of rows){const b=control(s,id(m.id)+' · Island '+m.island_id+' · '+format(s,m.score,m),()=>inspect(s,{kind:'program',program_id:m.id,island_id:m.island_id}));s.pool.append(b);}
    s.metrics.textContent=rows.length+' stored members shown';s.caption.textContent='Membership order only. No geometric niches or embedding coordinates are implied.';s.projected=false;inspect(s,null);return;
  }
  const g=geometry(s);s.projected=g.projected;s.points=g.points;indexBindings(s);
  const width=Math.max(280,s.stage.clientWidth||s.container.clientWidth-240||640),height=390;
  s.project=camera(s,width,height);attributes(s.svg,{viewBox:'0 0 '+width+' '+height});s.svg.replaceChildren();drawAxes(s,g);
  const sorted=g.points.map(p=>({...p,screen:s.project(p.world)})).sort((a,b)=>a.screen[2]-b.screen[2]);
  for(const p of sorted){
    const mark=element(s,'g','storage-mark',undefined,true);attributes(mark,{transform:'translate('+p.screen[0]+' '+p.screen[1]+')',tabindex:'0',role:'button','aria-label':p.kind==='cell'?'Island '+p.island_id+' cell '+p.cell.join(', '):p.kind+' '+id(p.niche_id??p.program_id??p.id),'aria-pressed':String(s.selected===p.key)});mark.dataset.storageKey=p.key;
    const count=p.kind==='centroid'?matching(s,p).length:1,color=colors[(Number(p.island_id)||0)%colors.length];
    const shape=element(s,p.kind==='cell'?'rect':'circle','storage-point',undefined,true);
    if(p.kind==='cell')attributes(shape,{x:-4,y:-4,width:8,height:8,rx:1.5,fill:color});
    else attributes(shape,{r:p.kind==='centroid'?6+Math.min(6,Math.sqrt(count)):4,fill:p.kind==='centroid'?(count?'#b8afea':'#ffffff'):color,stroke:'#a198d1','stroke-width':1.2});
    mark.append(shape);const title=element(s,'title',null,p.kind==='centroid'?'Saved centroid · '+count+' recorded elite bindings':p.program_id||'Elite ID not recorded',true);mark.append(title);
    const choose=()=>{s.selected=p.key;for(const node of s.svg.querySelectorAll('.storage-mark'))node.setAttribute('aria-pressed',String(node===mark));inspect(s,p);};
    mark.addEventListener('click',choose);mark.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}});mark.addEventListener('pointerenter',()=>inspect(s,p));mark.addEventListener('pointerleave',()=>inspect(s,g.points.find(x=>x.key===s.selected)||null));mark.addEventListener('focus',()=>inspect(s,p));s.svg.append(mark);
  }
  s.metrics.textContent=g.points.length+(g.projected?' saved vector marks':' occupied cells')+' shown';
  const ratios=list(projection.explained_variance).slice(0,s.flat?2:3),variance=ratios.length&&ratios.every(finite)?' · '+(100*ratios.reduce((a,b)=>a+b,0)).toFixed(1)+'% variance retained'+(projection.fit_sampled?' on fit subset':''):'';
  s.caption.textContent=g.projected?'Projection of recorded vectors'+variance+'. Centroid rings are prototypes, not additional programs. '+(s.flat?'PC1/PC2 view; the third projected axis is hidden.':'Rotate to inspect the three projected axes.'):
    'Recorded storage cells. X/Y are storage bins; height separates islands, not an extra learned feature. '+(s.flat?'Overlapping islands share bins in this flat view; filter an island to inspect it.':'');
  if(kind==='vq_elites'&&!g.projected)s.caption.textContent+=' Niche IDs are categorical; spacing does not encode similarity.';
  if(g.projected?(projection.limited||list(projection.points).length>1024):(s.model.assignments_limited||s.nativeTotal>2048||list(s.population.islands).some(i=>i.grid_truncated)))s.caption.textContent+=' Display is limited; some saved coordinates are omitted.';
  inspect(s,g.points.find(p=>p.key===s.selected)||null);
}
export function renderStorageSpace(container,population,options={}){
  let s=spaces.get(container);if(!s){s=create(container);spaces.set(container,s);}
  s.population=population||{};s.options=options;
  const signature=JSON.stringify([s.population.storage,s.population.islands,options.current,options.metricLabel,container.clientWidth]);
  if(signature!==s.signature){s.signature=signature;s.memberRows=list(s.population.islands).flatMap(island=>list(island.members).map(member=>({...member,island_id:island.id})));s.memberIndex=new Map(s.memberRows.map(m=>[id(m.island_id)+':'+id(m.id),m]));const selected=s.island;s.filter.replaceChildren();for(const[value,label]of[['all','All islands'],...list(s.population.islands).map(i=>[id(i.id),'Island '+i.id])]){const option=element(s,'option',null,label);option.value=value;s.filter.append(option);}s.island=[...s.filter.options].some(o=>o.value===selected)?selected:'all';s.filter.value=s.island;draw(s);}
  return {destroy:()=>{s.root.remove();spaces.delete(container);}};
}
