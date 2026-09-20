/* A camera over saved storage coordinates, never a reconstruction of missing vectors. */
const previews=new WeakMap(),NS='http://www.w3.org/2000/svg',LIMIT=384,SEEN_LIMIT=50000;
const list=v=>Array.isArray(v)?v:[],finite=v=>typeof v==='number'&&Number.isFinite(v),key=v=>String(v??'');
const palette=['#8f88ce','#64a8b7','#b8a170','#889fc6','#b58fba','#7ca893'];
const label=v=>typeof v==='object'?v?.label:v;

export function populationPreviewModel(population={}) {
  const storage=population.storage||{},projection=storage.projection||{},islands=list(population.islands);
  const known=['map_elites','vq_elites','cvt','vq','annealed','pool'].includes(storage.kind);
  const projected=known&&storage.kind!=='pool'&&projection.available===true;
  const members=islands.flatMap(i=>list(i.members).map(m=>({...m,island_id:i.id}))),memberIndex=new Map(members.map(m=>[key(m.island_id)+':'+key(m.id),m]));
  const assignments=list(projected?projection.assignments:storage.assignments);
  const bound=new Map();
  for(const a of assignments)for(const k of['*:'+key(a.niche_id),key(a.island_id)+':'+key(a.niche_id)]){if(!bound.has(k))bound.set(k,[]);bound.get(k).push(a);}
  const row=a=>({...a,id:a.program_id,code_available:memberIndex.get(key(a.island_id)+':'+key(a.program_id))?.code_available===true});
  let points=[],axes=[],mode=known?'cells':'unavailable',description='Storage coordinates not recorded';
  if(projected){
    mode='vectors';
    const raw=list(projection.points).filter(p=>p.id!=null&&list(p.position).length===3&&p.position.every(finite));
    const low=[0,1,2].map(i=>raw.reduce((v,p)=>Math.min(v,p.position[i]),Infinity)),high=[0,1,2].map(i=>raw.reduce((v,p)=>Math.max(v,p.position[i]),-Infinity));
    const span=Math.max(...high.map((v,i)=>v-low[i]),1e-12);
    points=raw.map(p=>({...p,key:'vector:'+key(p.id),world:p.position.map((v,i)=>(v-(low[i]+high[i])/2)/span),
      bindings:p.program_id?[row(p)]:(bound.get((p.island_id==null?'*':key(p.island_id))+':'+key(p.niche_id))||[]).map(row)}));
    axes=list(projection.axes).length?projection.axes.map(label):['PC1','PC2','PC3'];
    description=(projection.input_dimensions??'?')+'D saved vectors → '+(projection.output_dimensions??3)+'D '+String(projection.method||'projection').toUpperCase();
  }else if(storage.kind==='pool'){
    mode='pool';points=members.map(m=>({key:'member:'+m.island_id+':'+m.id,kind:'program',island_id:m.island_id,program_id:m.id,bindings:[m]}));
    description='Membership only · no geometric partition';
  }else if(known){
    const raw=islands.flatMap(i=>list(i.grid).filter(c=>finite(c.x)&&finite(c.y)).map(c=>({key:'cell:'+i.id+':'+c.x+':'+c.y,kind:'cell',island_id:i.id,cell:[c.x,c.y],program_id:c.candidate_id,score:c.score,metric_display:c.metric_display,
      bindings:c.candidate_id?[row({...c,program_id:c.candidate_id,island_id:i.id})]:[]})));
    const bins=storage.bins||{},max=i=>Math.max(1,(bins[['x','y'][i]]||population.layout?.grid_bins||1),...raw.map(p=>p.cell[i]+1));
    const nx=max(0),ny=max(1),islandIDs=islands.map(i=>key(i.id)).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
    points=raw.map(p=>({...p,world:[(p.cell[0]+.5)/nx-.5,(p.cell[1]+.5)/ny-.5,islandIDs.length>1?islandIDs.indexOf(key(p.island_id))/(islandIDs.length-1)-.5:0]}));
    axes=[label(storage.axes?.[0])||'Descriptor bin',label(storage.axes?.[1])||'Unused row','Island (category)'];
    description=storage.kind==='vq_elites'?'Categorical niche × score bin · island layers':storage.kind==='map_elites'?'Descriptor × score bin · islands as layers':'Centre ID × island · categorical coordinates';
  }
  const evidence=projected?projection:storage,all=points;
  points=all.slice(0,LIMIT);
  for(const p of all)p.bindingKey=p.bindings.map(b=>key(b.island_id)+':'+key(b.id)).sort().join('|');
  const limited=all.length>LIMIT||population.truncated===true||population.islands_truncated===true||islands.some(i=>i.members_truncated||i.grid_truncated)||(projected?projection.limited:storage.assignments_limited);
  const total=finite(population.source_summary?.member_count)?population.source_summary.member_count:population.available===true&&islands.every(i=>finite(i.member_count))?islands.reduce((n,i)=>n+i.member_count,0):null;
  return {points,observed:all,mode,axes,description,kind:storage.kind,label:storage.label||'Recorded population',iteration:evidence.iteration??population.iteration,stale:evidence.stale===true||(!projected&&population.stale===true),
    source:evidence.source||population.source||'Unavailable',total,islandCount:population.island_count??islands.length,uniqueSources:population.source_summary?.unique_sources,
    limited:Boolean(limited),savedMarks:all.length,rank:projection.projected_rank,
    note:projected?'Rings are saved centroids, not programs.':mode==='cells'?'Height separates islands; it is not a learned dimension.':mode==='pool'?'Ordered by saved membership; spacing has no meaning.':'Coordinates appear after a population snapshot is saved.'};
}

function el(s,tag,cls,text,svg=false){const e=svg?s.doc.createElementNS(NS,tag):s.doc.createElement(tag);if(cls)e.setAttribute('class',cls);if(text!=null)e.textContent=text;return e;}
function attr(e,values){for(const[k,v]of Object.entries(values))e.setAttribute(k,String(v));}
function create(container){
  const s={container,doc:container.ownerDocument,nodes:new Map(),seen:new Map(),yaw:.5,paused:false,hover:false,hovered:null,focused:false,selected:null,raf:null,lastFrame:0,inView:true,identity:null,initialized:false};
  s.win=s.doc.defaultView;s.media=s.win.matchMedia?.('(prefers-reduced-motion: reduce)');s.reduced=s.media?.matches===true;
  const e=(...args)=>el(s,...args);s.root=e('div','population-preview');
  const toolbar=e('div','preview-toolbar');s.summary=e('span','preview-summary');s.pause=e('button','preview-pause','Pause rotation');s.pause.type='button';s.pause.setAttribute('aria-pressed','false');
  s.pause.addEventListener('click',()=>{s.paused=!s.paused;motion(s);});toolbar.append(s.summary,s.pause);
  s.stage=e('div','preview-stage');s.svg=e('svg','preview-svg',null,true);attr(s.svg,{viewBox:'0 0 460 245',role:'group','aria-label':'Population in recorded storage coordinates'});
  s.guides=e('g','preview-guides',null,true);s.marks=e('g','preview-marks',null,true);s.svg.append(s.guides,s.marks);
  s.empty=e('div','preview-empty','Waiting for saved population');s.inspector=e('div','preview-inspector');s.inspector.hidden=true;
  s.stage.append(s.svg,s.empty,s.inspector);
  s.stage.addEventListener('pointerenter',()=>{s.hover=true;motion(s);});s.stage.addEventListener('pointerleave',()=>{s.hover=false;s.hovered=null;inspect(s,s.selected);motion(s);});
  s.stage.addEventListener('focusin',()=>{s.focused=true;motion(s);});s.stage.addEventListener('focusout',event=>{if(!s.stage.contains(event.relatedTarget)){s.focused=false;s.hovered=null;inspect(s,s.selected);motion(s);}});
  s.stage.addEventListener('keydown',event=>{if(event.key==='Escape'){s.selected=null;inspect(s,null);motion(s);}});
  s.caption=e('p','preview-caption');const footer=e('div','preview-footer');s.legend=e('span','preview-legend');s.legend.innerHTML='<i class="preview-new-key"></i> Newly observed <i class="preview-updated-key"></i> Elite changed';
  s.full=e('button','preview-full','Open population ↗');s.full.type='button';s.full.addEventListener('click',()=>s.options.onOpen?.());footer.append(s.legend,s.full);
  s.root.append(toolbar,s.stage,s.caption,footer);container.append(s.root);
  s.visibility=()=>motion(s);s.doc.addEventListener('visibilitychange',s.visibility);
  s.preference=event=>{s.reduced=event.matches;s.root.classList.toggle('reduced-motion',s.reduced);motion(s);};s.media?.addEventListener?.('change',s.preference);
  if(s.win.IntersectionObserver){s.observer=new s.win.IntersectionObserver(entries=>{s.inView=entries[0]?.isIntersecting===true;motion(s);});s.observer.observe(container);}
  return s;
}

function inspect(s,pointKey){
  const p=s.model?.points.find(p=>p.key===pointKey);s.inspector.replaceChildren();s.inspector.hidden=!p;if(!p)return;
  const title=p.kind==='centroid'?'Centroid '+key(p.niche_id??p.id):p.kind==='cell'?'Island '+p.island_id+' · cell '+p.cell.join(', '):key(p.program_id);
  s.inspector.append(el(s,'strong',null,title));
  const info=[s.model.stale?'Earlier saved snapshot':'Saved snapshot','iteration '+(s.model.iteration??'not recorded')];
  s.inspector.append(el(s,'p','preview-inspector-meta',info.join(' · ')));
  if(p.kind==='cell'&&!p.program_id)s.inspector.append(el(s,'p',null,'Elite ID not recorded. '+(s.options.metricLabel||'Score')+': '+s.options.formatScore?.(p.score,p)));
  if(!p.bindings.length&&p.kind==='centroid')s.inspector.append(el(s,'p',null,'No elite binding recorded in this geometry snapshot.'));
  for(const b of p.bindings.slice(0,4)){
    const line=el(s,'div','preview-binding'),name=el(s,'button','preview-program',key(b.id)+' ↗');name.type='button';name.disabled=b.code_available!==true||!s.options.onProgram;
    name.addEventListener('click',()=>s.options.onProgram?.(key(b.id),{action:'source',islandId:key(b.island_id)}));
    line.append(name,el(s,'span',null,'Island '+key(b.island_id)+' · '+(s.options.metricLabel||'Score')+' '+(s.options.formatScore?s.options.formatScore(b.score,b):finite(b.score)?b.score.toFixed(5):'Not recorded')));s.inspector.append(line);
  }
  if(p.bindings.length>4)s.inspector.append(el(s,'p',null,'+'+(p.bindings.length-4)+' bindings · open Population for all'));
  s.inspector.append(el(s,'small',null,s.selected?'Selected · Escape to clear':'Click to keep this card'));
}
function camera(s,point){
  const[x,y,z]=point,c=Math.cos(s.yaw),n=Math.sin(s.yaw),a=x*c-y*n,b=x*n+y*c;
  return [230+a*230,124+(b*.52-z*.85)*110,b*.85+z*.52];
}
function guide(s,a,b){const node=el(s,'line','preview-guide',null,true);s.guides.append(node);return {node,a,b};}
function buildGuides(s){
  s.guides.replaceChildren();s.lines=[];s.axisLabels=[];
  if(!['vectors','cells'].includes(s.model.mode)||!s.model.points.length)return;
  const z=-.55;
  for(let i=0;i<=4;i++){const t=-.55+i*.275;s.lines.push(guide(s,[t,-.55,z],[t,.55,z]),guide(s,[-.55,t,z],[.55,t,z]));}
  const base=[-.55,-.55,z],ends=[[.68,-.55,z],[-.55,.68,z],[-.55,-.55,.68]];
  for(let i=0;i<3;i++){const line=guide(s,base,ends[i]);line.node.classList.add('preview-axis');s.lines.push(line);const node=el(s,'text','preview-axis-label',s.model.axes[i],true);s.guides.append(node);s.axisLabels.push({node,point:ends[i]});}
}
function paint(s){
  for(const {node,a,b}of s.lines||[]){const p=camera(s,a),q=camera(s,b);attr(node,{x1:p[0].toFixed(2),y1:p[1].toFixed(2),x2:q[0].toFixed(2),y2:q[1].toFixed(2)});}
  for(const {node,point}of s.axisLabels||[]){const p=camera(s,point);attr(node,{x:p[0].toFixed(2),y:(p[1]-5).toFixed(2),'text-anchor':p[0]>300?'end':'start'});}
  const pool=s.model?.mode==='pool';
  for(const [i,p]of (s.model?.points||[]).entries()){
    const node=s.nodes.get(p.key),at=pool?[26+(i%27)*15.7,28+Math.floor(i/27)*14.3,0]:camera(s,p.world);
    attr(node,{transform:'translate('+at[0].toFixed(2)+' '+at[1].toFixed(2)+')',opacity:pool?1:(.7+(at[2]+.9)*.15).toFixed(2)});
  }
}
function motion(s){
  const canRotate=['vectors','cells'].includes(s.model?.mode)&&s.model.points.length>0;
  s.pause.disabled=s.reduced||!canRotate;s.pause.textContent=s.reduced?'Reduced motion':!canRotate?'Static view':s.paused?'Resume rotation':'Pause rotation';s.pause.setAttribute('aria-pressed',String(s.paused));
  const active=canRotate&&!s.paused&&!s.reduced&&!s.hover&&!s.focused&&!s.selected&&s.inView&&!s.doc.hidden&&s.options?.follow!==false;
  s.root.dataset.rotating=String(active);
  if(!active){if(s.raf!==null)s.win.cancelAnimationFrame(s.raf);s.raf=null;s.lastFrame=0;return;}
  if(s.raf!==null)return;
  const frame=t=>{s.raf=null;if(!s.lastFrame)s.lastFrame=t;if(t-s.lastFrame>=1000/30){s.yaw+=Math.min(t-s.lastFrame,80)*.000065;s.lastFrame=t;paint(s);}s.raf=s.win.requestAnimationFrame(frame);};
  s.raf=s.win.requestAnimationFrame(frame);
}
function refresh(s,population,options){
  s.options=options;const identity=key(options.runKey);
  if(s.identity!==identity){s.identity=identity;s.seen.clear();s.initialized=false;s.selected=null;s.hovered=null;s.yaw=.5;s.signature=null;s.iterations=new Map();s.lastMode=null;}
  const signature=JSON.stringify([population?.storage,population?.islands,population?.source_summary,population?.iteration,population?.stale,population?.island_count,options.metricLabel]);
  if(signature!==s.signature){
    s.signature=signature;s.model=populationPreviewModel(population);const m=s.model,now=Date.now();
    const previousIteration=s.iterations.get(m.mode),forward=!finite(m.iteration)||!finite(previousIteration)||m.iteration>=previousIteration,sameMode=m.mode===s.lastMode;
    s.root.dataset.mode=m.mode;s.root.classList.toggle('reduced-motion',s.reduced);
    s.summary.textContent=(m.total===null?'Membership not recorded':m.total+' stored members')+' · '+m.islandCount+' islands'+(finite(m.uniqueSources)?' · '+m.uniqueSources+' source'+(m.uniqueSources===1?'':'s'):'');
    s.summary.title='Saved membership, including shared seed and migration copies. Distinct source bytes do not establish behavioral diversity.';
    s.empty.hidden=m.points.length>0;s.svg.hidden=!m.points.length;
    s.empty.textContent=m.mode==='unavailable'?'Storage coordinates not recorded':'Waiting for saved '+(m.mode==='pool'?'members':'storage coordinates');
    s.caption.textContent=m.description+' · '+(m.stale?'earlier snapshot':'saved')+' at iteration '+(m.iteration??'not recorded')+'. '+(m.mode==='vectors'?'Rings = centroids, not programs.':m.mode==='cells'?'Height = island category.':m.mode==='pool'?'Spacing has no meaning.':'')+(m.limited?' '+m.points.length+' marks shown · capped.':'');
    s.caption.title=m.label+' · '+m.source+'. '+m.note+(m.kind==='vq_elites'&&m.mode!=='vectors'?' Niche IDs are categorical; spacing does not encode similarity.':'');
    const retained=new Set(m.points.map(p=>p.key));for(const[k,node]of s.nodes)if(!retained.has(k)){node.remove();s.nodes.delete(k);}
    for(const p of m.observed){
      const seen=s.seen.get(p.key),fresh=s.initialized&&forward&&sameMode&&!seen&&s.seen.size<SEEN_LIMIT;
      const updated=s.initialized&&forward&&sameMode&&seen&&seen.bindingKey!==p.bindingKey&&p.bindings.length>0;
      const event=fresh?'new':updated?'updated':seen?.event,until=fresh||updated?now+9000:seen?.until;
      if(forward&&(seen||s.seen.size<SEEN_LIMIT))s.seen.set(p.key,{bindingKey:p.bindingKey,event,until});
      if(!retained.has(p.key))continue;
      let node=s.nodes.get(p.key);
      if(!node){node=el(s,'g','preview-mark',null,true);node.dataset.pointKey=p.key;attr(node,{tabindex:'0',role:'button'});const halo=el(s,'circle','preview-halo',null,true);attr(halo,{r:9});const shape=el(s,p.kind==='cell'?'rect':'circle','preview-point',null,true);node.append(halo,shape);s.marks.append(node);s.nodes.set(p.key,node);
        const choose=()=>{s.selected=s.selected===p.key?null:p.key;inspect(s,s.selected);motion(s);};node.addEventListener('click',choose);node.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}else if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp','Home','End'].includes(event.key)){event.preventDefault();const points=s.model.points,index=points.findIndex(x=>x.key===p.key),next=event.key==='Home'?0:event.key==='End'?points.length-1:(index+(['ArrowRight','ArrowDown'].includes(event.key)?1:points.length-1))%points.length;s.nodes.get(points[next].key)?.focus();}});node.addEventListener('pointerenter',()=>{s.hovered=p.key;inspect(s,p.key);});node.addEventListener('focus',()=>{s.hovered=p.key;for(const[k,n]of s.nodes)n.setAttribute('tabindex',k===p.key?'0':'-1');inspect(s,p.key);});}
      node.dataset.change=forward&&sameMode&&until>now?event||'':'';node.setAttribute('aria-label',p.kind==='cell'?'Island '+p.island_id+' cell '+p.cell.join(', '):p.kind+' '+key(p.niche_id??p.program_id??p.id));
      const shape=node.querySelector('.preview-point'),color=palette[Math.abs(Number(p.island_id)||0)%palette.length];
      if(p.kind==='cell')attr(shape,{x:-3.3,y:-3.3,width:6.6,height:6.6,rx:1.8,fill:color});
      else attr(shape,{r:p.kind==='centroid'?4.5:3.5,fill:p.kind==='centroid'?(p.bindings.length?'#b7afd9':'#fff'):color,stroke:p.kind==='centroid'?'#978cc5':'#fff','stroke-width':p.kind==='centroid'?1.3:.65});
    }
    s.initialized=s.initialized||m.points.length>0;s.lastMode=m.mode;if(forward)s.iterations.set(m.mode,m.iteration);buildGuides(s);paint(s);if(!retained.has(s.selected))s.selected=null;if(!retained.has(s.hovered))s.hovered=null;
    const tabKey=s.hovered||s.selected||m.points[0]?.key;for(const[k,node]of s.nodes)node.setAttribute('tabindex',k===tabKey?'0':'-1');inspect(s,s.hovered||s.selected);
    s.win.clearTimeout(s.highlightTimer);s.highlightTimer=s.win.setTimeout(()=>{for(const[k,node]of s.nodes)if((s.seen.get(k)?.until||0)<=Date.now())node.dataset.change='';},9100);
  }
  motion(s);
}
export function renderPopulationPreview(container,population,options={}){
  let s=previews.get(container);if(!s){s=create(container);previews.set(container,s);}refresh(s,population||{},options);
}
export function destroyPopulationPreview(container){
  const s=previews.get(container);if(!s)return;
  if(s.raf!==null)s.win.cancelAnimationFrame(s.raf);s.win.clearTimeout(s.highlightTimer);s.observer?.disconnect();s.doc.removeEventListener('visibilitychange',s.visibility);s.media?.removeEventListener?.('change',s.preference);s.root.remove();previews.delete(container);
}
