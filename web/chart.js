const number = value => typeof value === 'number' && Number.isFinite(value);
const escape = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => Math.abs(value)<.001&&value!==0?value.toExponential(2):value.toFixed(3);
const precise = value => number(value)?value.toFixed(9).replace(/0+$/,'').replace(/\.$/,''):'Not measured';
const MAX_POINTS=600, MAX_EDGES=32;
const sessions=new WeakMap();
let sequence=0;
const identity=(point,index=0)=>String(point.candidate_id||point.experiment_id||point.id||point.point_id||'observation:'+point.iteration+':'+(point.event_seq??index));
const aliases=point=>[point.candidate_id,...(point.alias_ids||[]),point.experiment_id].filter(Boolean).map(String);
const measurementIds=point=>[...aliases(point),...(point.candidate_ids||[]).map(String)];

function samplePoints(data, selectedIteration, selectedId) {
  if(data.length<=MAX_POINTS)return data;
  const selected=new Set([0,data.length-1]);
  const selectedIndex=data.findIndex(p=>selectedId?measurementIds(p).includes(String(selectedId)):p.iteration===selectedIteration);
  if(selectedIndex>=0)selected.add(selectedIndex);
  const buckets=Math.floor((MAX_POINTS-3)/3);
  const value=i=>number(data[i].score)?data[i].score:data[i].best_score;
  for(let b=0;b<buckets;b++){
    const start=Math.floor(b*data.length/buckets),end=Math.floor((b+1)*data.length/buckets);
    let low=start,high=start;
    for(let i=start+1;i<end;i++){if(value(i)<value(low))low=i;if(value(i)>value(high))high=i;}
    selected.add(low);selected.add(high);selected.add(end-1);
  }
  return [...selected].sort((a,b)=>a-b).map(i=>data[i]);
}

function reduced(session){return session.container.ownerDocument.defaultView.matchMedia?.('(prefers-reduced-motion: reduce)').matches===true;}
function stepPath(points){return points.map((p,i)=>(i?'H '+p.x+' V '+p.y:'M '+p.x+' '+p.y)).join(' ');}
function parentIds(point){return [...new Set(Array.isArray(point.parent_ids)?point.parent_ids.filter(x=>typeof x==='string'):point.parent_id?[point.parent_id]:[])];}

function focusedControl(session){
  const node=session.container.ownerDocument.activeElement;
  if(!node||!session.container.contains(node))return null;
  if(node.dataset.relative)return {kind:'relative',id:node.dataset.relative};
  if(node.dataset.pointKey)return {kind:'point',id:node.dataset.pointKey};
  if(node.dataset.program)return {kind:'program',id:node.dataset.program};
  for(const selector of ['.chart-card-close','[data-chart-inspect]','[data-chart-llm]']){
    if(node.matches(selector))return {kind:'control',selector};
  }
  return null;
}
function restoreFocus(session,focus){
  if(!focus)return;
  let target;
  if(focus.kind==='point')target=session.dots.get(focus.id);
  if(focus.kind==='relative')target=[...session.overlay.querySelectorAll('[data-relative]')].find(n=>n.dataset.relative===focus.id);
  if(focus.kind==='program')target=[...session.card.querySelectorAll('[data-program]')].find(n=>n.dataset.program===focus.id);
  if(focus.kind==='control')target=session.card.querySelector(focus.selector);
  // A removed relation/point must not throw keyboard users back to the page.
  target??=session.dots.get(focus.id)||[...session.overlay.querySelectorAll('[data-relative]')].find(n=>n.dataset.relative===focus.id)
    ||session.dots.get(session.activeId)||session.dots.values().next().value;
  if(target&&!target.disabled&&session.container.ownerDocument.activeElement!==target){
    session.restoringFocus=true;
    try{target.focus({preventScroll:true});}finally{session.restoringFocus=false;}
  }
  session.window.clearTimeout(session.hideTimer);
}

function positionCard(session,point){
  const card=session.card;if(!card||card.hidden)return;
  if(!point){hidePreview(session);return;}
  const win=session.container.ownerDocument.defaultView,box=session.svg.getBoundingClientRect();
  const mobile=win.innerWidth<=720;
  const location=session.locate(point),cardWidth=mobile?win.innerWidth-24:Math.min(320,Math.max(240,win.innerWidth-24));
  card.style.width=cardWidth+'px';
  card.style.maxHeight=mobile?Math.min(390,win.innerHeight*.48)+'px':'calc(100vh - 24px)';
  const px=box.left+(location?.x??session.width/2)*(box.width/session.width||1);
  const py=box.top+(location?.y??session.height/2)*(box.height/session.height||1);
  let left=px+22;
  if(left+cardWidth>win.innerWidth-12)left=px-cardWidth-22;
  left=Math.max(12,Math.min(left,win.innerWidth-cardWidth-12));
  const height=card.getBoundingClientRect().height||260;
  const top=mobile?Math.max(12,win.innerHeight-height-12):Math.max(12,Math.min(py-32,win.innerHeight-height-12));
  if(mobile)left=12;
  card.style.left=left+'px';card.style.top=top+'px';
}

function hidePreview(session){
  const focus=focusedControl(session),active=session.activeId;
  session.window.clearTimeout(session.hideTimer);session.activeId=null;session.pinned=false;
  if(session.card)session.card.hidden=true;
  session.container.classList.remove('chart-exploring');
  session.overlay?.replaceChildren();
  session.svg?.querySelectorAll('.chart-related,.chart-hovered').forEach(node=>node.classList.remove('chart-related','chart-hovered'));
  if(focus&&focus.kind!=='point'&&session.dots)restoreFocus(session,{kind:'point',id:active});
}
function deferHide(session){
  if(!session.pinned)session.hideTimer=session.window.setTimeout(()=>hidePreview(session),180);
}

function bindPoint(session,node,point){
  const current=()=>session.nodes.get(identity(point))||point;
  node.addEventListener('pointerenter',()=>{session.window.clearTimeout(session.hideTimer);if(!session.pinned)preview(session,current());});
  node.addEventListener('pointerleave',()=>deferHide(session));
  node.addEventListener('focus',()=>{if(!session.pinned&&!session.restoringFocus)preview(session,current());});
  node.addEventListener('blur',()=>deferHide(session));
  const select=event=>{
    event?.preventDefault();session.pinned=true;preview(session,current(),true);
    session.onSelect?.(current());
  };
  node.addEventListener('click',select);
  node.addEventListener('keydown',event=>{
    if(event.key==='Enter'||event.key===' ')select(event);
    if(event.key==='Escape'){event.preventDefault();hidePreview(session);}
    if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
      event.preventDefault();const focusable=session.data.filter(p=>number(p.score));
      const index=focusable.findIndex(p=>identity(p)===identity(point)),direction=event.key==='ArrowRight'?1:-1;
      const next=focusable[index+direction];
      if(next){session.pinned=false;preview(session,next);session.dots.get(identity(next))?.focus();}
    }
  });
}

function preview(session,point,force=false){
  const id=identity(point);
  session.window.clearTimeout(session.hideTimer);
  if(session.activeId===id&&!force){positionCard(session,point);return;}
  const focus=focusedControl(session),scroll=session.activeId===id?session.card.scrollTop:0;
  session.activeId=id;session.container.classList.add('chart-exploring');
  const edges=[],edgeKeys=new Set(),related=new Map([[id,point]]),seen=new Set([id]),missing=new Set();
  const edge=(from,to,kind)=>{
    const key=JSON.stringify([identity(from),identity(to)]);
    if(edgeKeys.has(key)||identity(from)===identity(to)||edges.length>=MAX_EDGES)return;
    edgeKeys.add(key);edges.push({from,to,kind});
  };
  let truncated=false;
  const queue=[{point,depth:0}];
  while(queue.length&&edges.length<MAX_EDGES){
    const current=queue.shift();
    for(const parentId of parentIds(current.point)){
      if(edges.length>=MAX_EDGES){truncated=true;break;}
      const parent=session.nodes.get(parentId),parentKey=parent&&identity(parent);
      if(!parent){missing.add(parentId);continue;}
      related.set(parentKey,parent);
      edge(parent,current.point,current.depth?'ancestor':'parent');
      if(seen.has(parentKey))continue;
      seen.add(parentKey);
      if(current.depth<12)queue.push({point:parent,depth:current.depth+1});
      else if(parentIds(parent).length)truncated=true;
    }
  }
  const children=session.children.get(id)||[];
  for(const child of children.slice(0,6)){
    if(edges.length>=MAX_EDGES)break;
    const key=identity(child);if(seen.has(key))continue;
    related.set(key,child);edge(point,child,'child');
  }
  let links='';
  const plotted=new Map();
  for(const [key,node] of related){const p=session.locate(node);if(p)plotted.set(key,p);}
  for(const edge of edges){
    const a=plotted.get(identity(edge.from)),b=plotted.get(identity(edge.to));if(!a||!b)continue;
    const lift=Math.max(12,Math.min(42,Math.abs(b.x-a.x)*.12));
    links+='<path class="chart-family-edge '+edge.kind+'" data-parent="'+escape(identity(edge.from))+'" data-child="'+escape(identity(edge.to))+'" d="M '+a.x+' '+a.y+' Q '+((a.x+b.x)/2)+' '+(Math.min(a.y,b.y)-lift)+' '+b.x+' '+b.y+'" marker-end="url(#'+session.uid+'-arrow)"/>';
  }
  for(const [key,node] of related){
    const p=plotted.get(key);if(!p)continue;
    links+='<circle class="chart-relative-dot'+(key===id?' active':'')+'" data-relative="'+escape(key)+'" cx="'+p.x+'" cy="'+p.y+'" r="'+(key===id?6:4.5)+'" tabindex="0" role="button" aria-label="Inspect '+escape(key)+'"/>';
  }
  session.overlay.innerHTML=links;
  for(const element of session.overlay.querySelectorAll('[data-relative]'))bindPoint(session,element,related.get(element.dataset.relative));
  for(const [key,dot] of session.dots){dot.classList.toggle('chart-related',related.has(key));dot.classList.toggle('chart-hovered',key===id);}
  const parents=parentIds(point),loc=session.locate(point);
  const nearby=loc?session.data.filter(p=>{const other=session.locate(p);return identity(p)!==id&&other&&Math.hypot(loc.x-other.x,loc.y-other.y)<=5;}):[];
  const change=Object.hasOwn(point,'display_delta')?point.display_delta:number(point.score)&&number(point.parent_score)?point.score-point.parent_score:null;
  const hypothesis=typeof point.hypothesis==='string'?point.hypothesis:point.hypothesis?.description||point.hypothesis?.mechanism||null;
  const chips=ids=>ids.map(key=>'<button class="chart-family-chip" data-program="'+escape(key)+'"'+(!session.nodes.has(key)?' disabled':'')+'>'+escape(key)+'</button>').join('');
  session.card.innerHTML='<div class="chart-card-heading"><div><span class="chart-card-eyebrow">'+escape(point.kind==='seed'?'Shared seed measurement':'Iteration '+(point.iteration??'not recorded'))+(point.island!==null&&point.island!==undefined?' · Island '+escape(point.island):'')+'</span><strong>'+escape(id)+'</strong></div><button class="chart-card-close" aria-label="Close program preview">×</button></div>'+
    '<div class="chart-card-score"><span>'+escape(session.metricLabel)+'</span><strong>'+escape(point.metric_text??precise(point.score))+'</strong>'+(number(change)?'<small class="'+(change>0?'positive':change<0?'negative-text':'')+'">'+(change>0?'+':'')+escape(precise(change))+' vs parent</small>':'')+'</div>'+
    '<div class="chart-card-tags">'+[point.operator,point.display_status||point.status].filter(Boolean).map(x=>'<span>'+escape(x)+'</span>').join('')+'</div>'+
    (point.metric_note?'<p class="chart-card-note">'+escape(point.metric_note)+'</p>':'')+
    (point.lineage_note?'<p class="chart-card-note">'+escape(point.lineage_note)+'</p>':'')+
    (point.candidate_ids?.length>1?'<p class="chart-card-note">Same seed measurement · '+point.candidate_ids.map(escape).join(', ')+'</p>':'')+
    (hypothesis?'<p class="chart-card-hypothesis">'+escape(hypothesis.slice(0,340))+'</p>':'')+
    '<div class="chart-card-family"><span>Parents</span><div>'+ (parents.length?chips(parents):'<small>'+(point.kind==='seed'?'Initial source':'Not recorded')+'</small>')+'</div></div>'+
    (children.length?'<div class="chart-card-family"><span>Children · '+children.length+'</span><div>'+chips(children.slice(0,4).map(identity))+(children.length>4?'<small>+'+(children.length-4)+' more</small>':'')+'</div></div>':'')+
    (nearby.length?'<div class="chart-card-family"><span>Nearby points</span><div>'+chips(nearby.slice(0,4).map(identity))+'</div></div>':'')+
    (point.operator==='cross'?'<p class="chart-card-note">Only recorded parent links are shown; extra crossover contributors were not recorded.</p>':'')+
    (missing.size||edges.some(e=>!session.locate(e.from))?'<p class="chart-card-note">Some ancestors have no recorded chart position.</p>':'')+
    (queue.length||truncated?'<p class="chart-card-note">Showing the nearest recorded ancestors.</p>':'')+
    '<div class="chart-card-actions"><button data-chart-inspect'+(!session.options.onInspect||!point.code_available?' disabled':'')+'>Open program ↗</button><button data-chart-llm'+(!session.options.onLLM||!point.experiment_id||point.llm_available===false?' disabled':'')+'>LLM ↗</button></div>'+
    '<p class="chart-card-note chart-interaction-hint">'+(session.pinned?'Pinned · Esc to close':'Click a point to pin · Blue links show ancestry')+'</p>';
  session.card.hidden=false;positionCard(session,point);
  session.card.querySelector('.chart-card-close').onclick=()=>hidePreview(session);
  session.card.querySelector('[data-chart-inspect]').onclick=()=>session.options.onInspect?.(point);
  session.card.querySelector('[data-chart-llm]').onclick=()=>session.options.onLLM?.(point);
  for(const button of session.card.querySelectorAll('[data-program]'))button.onclick=()=>{
    const next=session.nodes.get(button.dataset.program);if(next){session.pinned=true;preview(session,next,true);}
  };
  session.card.scrollTop=scroll;restoreFocus(session,focus);
}

export function renderChart(container,points,axis,selectedIteration,onSelect,metricLabel='Score',options={}) {
  let session=sessions.get(container);
  let focus=session?focusedControl(session):null;
  if(!session){
    const win=container.ownerDocument.defaultView;
    session={container,window:win,uid:'chart-'+(++sequence),runKey:options.runKey,coordinates:new Map(),pinned:false,activeId:null};
    sessions.set(container,session);
    // One listener per chart, never one per refresh or sample.
    container.addEventListener('keydown',event=>{if(event.key==='Escape')hidePreview(session);});
    win.addEventListener('scroll',()=>{if(session.activeId)positionCard(session,session.nodes.get(session.activeId));},true);
    win.addEventListener('resize',()=>{if(session.activeId)positionCard(session,session.nodes.get(session.activeId));});
  }
  if(session.runKey!==options.runKey){hidePreview(session);session.coordinates.clear();session.fingerprint=null;session.runKey=options.runKey;focus=null;}
  session.onSelect=onSelect;session.options=options;session.metricLabel=metricLabel;
  const all=points.filter(p=>number(p[axis])&&(number(p.score)||number(p.best_score)));
  if(!all.length){hidePreview(session);container.innerHTML='<div class="empty-panel"><strong>No measured outcomes available</strong>Only recorded measurements appear on this axis. Other outcomes remain inspectable below and in Programs.</div>';return {total:0,displayed:0};}
  const data=samplePoints(all,selectedIteration,options.selectedCandidateId);
  const width=Math.max(320,container.clientWidth-32),height=container.clientHeight||240;
  const pad={left:49,right:20,top:25,bottom:32},plotW=width-pad.left-pad.right,plotH=height-pad.top-pad.bottom;
  let minX=0,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
  for(const p of all){minX=Math.min(minX,p[axis]);maxX=Math.max(maxX,p[axis]);for(const v of [p.score,p.best_score])if(number(v)){minY=Math.min(minY,v);maxY=Math.max(maxY,v);}}
  maxX=Math.max(maxX,minX+(axis==='iteration'?1:.001));
  const span=maxY-minY||Math.max(Math.abs(maxY)*.1,.01);minY-=span*.12;maxY+=span*.15;
  const x=v=>pad.left+(v-minX)/(maxX-minX)*plotW,y=v=>pad.top+(maxY-v)/(maxY-minY)*plotH;
  session.data=data;session.width=width;session.height=height;
  session.locate=p=>p&&number(p[axis])&&number(p.score)&&p[axis]>=minX&&p[axis]<=maxX?{x:x(p[axis]),y:y(p.score)}:null;
  const indexVersion=options.dataVersion==null?null:JSON.stringify([options.runKey,options.dataVersion,axis,metricLabel]);
  if(indexVersion===null||indexVersion!==session.indexVersion){
    const nodes=new Map(),rawPrograms=Array.isArray(options.programs)?options.programs:Object.values(options.programs||{});
    // Measurements override metadata only for their own exact IDs/recorded aliases.
    for(const p of [...rawPrograms,...all]){
      const key=identity(p);nodes.set(key,{...(nodes.get(key)||{}),...p});
      for(const alias of aliases(p))nodes.set(alias,nodes.get(key));
    }
    // Copies share an evaluation position, never a stored program identity.
    for(const p of all)for(const id of p.candidate_ids||[]){
      if(String(id)===identity(p))continue;
      const copy=nodes.get(String(id))||{candidate_id:String(id),code_available:false};
      nodes.set(String(id),{...copy,iteration:p.iteration,score:p.score,best_score:p.best_score,
        cost_total:p.cost_total,point_id:p.point_id,kind:p.kind,candidate_ids:p.candidate_ids});
    }
    session.nodes=nodes;session.children=new Map();
    const indexed=new Set();
    for(const p of nodes.values()){
      const key=identity(p);if(indexed.has(key))continue;indexed.add(key);
      for(const parent of parentIds(p)){
        const parentKey=identity(nodes.get(parent)||{candidate_id:parent});
        if(parentKey===key)continue;
        const children=session.children.get(parentKey)||[];children.push(p);session.children.set(parentKey,children);
      }
    }
    session.indexVersion=indexVersion;
  }
  const nodes=session.nodes;
  const fingerprint=JSON.stringify([axis,width,height,metricLabel,data.map(p=>[identity(p),p[axis],p.score,p.best_score])]);
  const selected=p=>options.selectedCandidateId?measurementIds(p).includes(String(options.selectedCandidateId)):p.iteration===selectedIteration;
  const active=session.activeId&&nodes.get(session.activeId);
  if(session.fingerprint===fingerprint&&container.querySelector('svg')){
    session.svg.classList.toggle('is-live',options.live===true);
    for(const p of data)session.dots.get(identity(p))?.classList.toggle('selected',selected(p));
    if(active)preview(session,active,true);else if(session.activeId)hidePreview(session);
    restoreFocus(session,focus);
    return {total:all.length,displayed:data.length};
  }
  session.fingerprint=fingerprint;
  session.window.cancelAnimationFrame?.(session.frame);
  let grids='',labels='';
  for(let i=0;i<5;i++){const v=minY+(maxY-minY)*i/4,yy=y(v);grids+='<line class="chart-grid" x1="'+pad.left+'" y1="'+yy+'" x2="'+(width-pad.right)+'" y2="'+yy+'"/>';labels+='<text class="chart-axis" x="'+(pad.left-10)+'" y="'+(yy+3)+'" text-anchor="end">'+fmt(v)+'</text>';}
  const ticks=axis==='iteration'?Math.min(5,Math.max(1,Math.round(maxX-minX))):5,seen=new Set();
  for(let i=0;i<=ticks;i++){let v=minX+(maxX-minX)*i/ticks;if(axis==='iteration')v=Math.round(v);if(seen.has(v))continue;seen.add(v);labels+='<text class="chart-axis" x="'+x(v)+'" y="'+(height-8)+'" text-anchor="middle">'+(axis==='iteration'?v:'$'+v.toFixed(3))+'</text>';}
  const best=data.filter(p=>number(p.best_score)).map(p=>({id:identity(p),x:x(p[axis]),y:y(p.best_score)}));
  const path=stepPath(best),base=height-pad.bottom;
  const area=best.length?path+' L '+best.at(-1).x+' '+base+' L '+best[0].x+' '+base+' Z':'';
  let dots='';
  data.forEach((p,index)=>{
    if(!number(p.score))return;
    const title='Iteration '+p.iteration+' · '+(p.candidate_id||p.experiment_id||'Candidate')+' · '+metricLabel.toLowerCase()+' '+p.score.toPrecision(8);
    dots+='<g class="chart-point"><circle class="chart-hit" cx="'+x(p[axis])+'" cy="'+y(p.score)+'" r="10" data-index="'+index+'"/><circle class="chart-dot'+(selected(p)?' selected':'')+'" cx="'+x(p[axis])+'" cy="'+y(p.score)+'" r="4" tabindex="0" role="button" aria-label="'+escape(title)+'" aria-haspopup="dialog" data-index="'+index+'" data-point-key="'+escape(identity(p))+'"><title>'+escape(title)+'</title></circle></g>';
  });
  const last=best.at(-1);
  const endpoint=last?'<circle class="chart-live-halo" cx="'+last.x+'" cy="'+last.y+'" r="5"/><circle class="chart-best-dot" cx="'+last.x+'" cy="'+last.y+'" r="4"/>':'';
  container.innerHTML='<svg class="'+(options.live?'is-live':'')+'" viewBox="0 0 '+width+' '+height+'" role="group" aria-label="Search progress. Focus or hover a candidate to inspect its parents and program."><defs><linearGradient id="'+session.uid+'-gradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ffcc00" stop-opacity=".14"/><stop offset="100%" stop-color="#ffcc00" stop-opacity=".01"/></linearGradient><marker id="'+session.uid+'-arrow" viewBox="0 0 8 8" refX="10" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 1 L 7 4 L 0 7" fill="none" stroke="#4e81bd" stroke-width="1.5"/></marker></defs>'+grids+'<path class="chart-area" style="fill:url(#'+session.uid+'-gradient)" d="'+area+'"/><path class="chart-line" pathLength="1" d="'+path+'"/>'+dots+endpoint+'<g class="chart-lineage"></g>'+labels+'</svg><div class="chart-program-card" role="dialog" aria-label="Program preview" hidden></div>';
  session.svg=container.querySelector('svg');session.overlay=container.querySelector('.chart-lineage');session.card=container.querySelector('.chart-program-card');session.dots=new Map();
  session.card.addEventListener('pointerenter',()=>session.window.clearTimeout(session.hideTimer));
  session.card.addEventListener('pointerleave',()=>deferHide(session));
  session.card.addEventListener('focusin',()=>session.window.clearTimeout(session.hideTimer));
  session.card.addEventListener('focusout',()=>deferHide(session));
  for(const dot of container.querySelectorAll('[data-index]')){
    const p=data[Number(dot.dataset.index)];bindPoint(session,dot,p);
    if(dot.classList.contains('chart-dot'))session.dots.set(identity(p),dot);
  }
  const previous=session.coordinates;session.coordinates=new Map(best.map(p=>[p.id,p]));
  if(!reduced(session)&&!container.ownerDocument.hidden){
    if(previous.size&&best.length){
      const previousLast=[...previous.values()].at(-1);
      const from=best.map(p=>previous.get(p.id)||previousLast||p);
      const line=container.querySelector('.chart-line'),areaNode=container.querySelector('.chart-area'),head=container.querySelector('.chart-best-dot'),halo=container.querySelector('.chart-live-halo');
      let started;
      const animate=time=>{
        if(!line.isConnected)return;
        started??=time;const t=Math.min(1,(time-started)/420),e=1-Math.pow(1-t,3);
        const frame=best.map((p,i)=>({x:from[i].x+(p.x-from[i].x)*e,y:from[i].y+(p.y-from[i].y)*e}));
        const d=stepPath(frame);line.setAttribute('d',d);areaNode.setAttribute('d',d+' L '+frame.at(-1).x+' '+base+' L '+frame[0].x+' '+base+' Z');
        for(const node of [head,halo]){node?.setAttribute('cx',frame.at(-1).x);node?.setAttribute('cy',frame.at(-1).y);}
        if(t<1)session.frame=session.window.requestAnimationFrame(animate);
      };
      session.frame=session.window.requestAnimationFrame(animate);
    }else session.svg.classList.add('chart-enter');
    for(const [id,dot] of session.dots)if(!previous.has(id))dot.classList.add('chart-dot-new');
  }
  if(active)preview(session,active,true);else if(session.activeId)hidePreview(session);
  restoreFocus(session,focus);
  return {total:all.length,displayed:data.length};
}
