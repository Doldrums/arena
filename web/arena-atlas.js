// Every particle represents one catalog task. Coordinates only arrange the groups.
const atlasSessions = new WeakMap();
const SVG = 'http://www.w3.org/2000/svg';
const UNSPECIFIED = '__unspecified__';
const format = value => Number(value).toLocaleString('en-US');
const hash = value => { let n = 2166136261; for (const character of String(value)) n = Math.imul(n ^ character.charCodeAt(0), 16777619); return n >>> 0; };
const prettyFamily = value => ({matmul_tensor:'Matrix multiplication',circle_packing_square:'Circle packing · square',circle_packing_rectangle:'Circle packing · rectangle',llm_benchmark:'Language model benchmarks',llmsr_equation:'LLM-SR equations',lsr_equation:'Symbolic regression equations',ode_integrator:'ODE integration',online_bin_packing:'Online bin packing',sciel_copy:'SCiEL task copies'}[value] || value.replaceAll('_', ' ').replace(/^./, letter => letter.toUpperCase()));

/** Normalize an exact, disjoint partition of the supplied catalog. Missing labels stay explicit. */
export function buildAtlasModel({catalog, insights, searchFamilies, mode = 'methods'}) {
  const tasks = [...new Map((catalog?.tasks || []).filter(task => typeof task.id === 'string').map(task => [task.id, task])).values()];
  const byId = new Map(tasks.map(task => [task.id, task]));
  const domainsAvailable = Boolean(insights?.task_annotations && Array.isArray(insights?.domains));
  const claimed = new Set(), groups = [];
  const append = (source, ids) => {
    const members = [...new Set(ids)].filter(id => byId.has(id) && !claimed.has(id)).sort();
    if (!members.length) return;
    members.forEach(id => claimed.add(id));
    const domains = new Map();
    for (const id of domainsAvailable ? members : []) {
      const domainId = insights?.task_annotations?.[id]?.domain_id || 'unknown';
      const domain = insights?.domains?.find(item => item.id === domainId);
      const entry = domains.get(domainId) || {id:domainId,label:domain?.label || 'Unclassified',count:0}; entry.count++; domains.set(domainId,entry);
    }
    groups.push({...source, tasks:members.map(id=>byId.get(id)), task_ids:members, count:members.length,
      executable:members.filter(id=>byId.get(id).executable).length,
      domains:[...domains.values()].sort((a,b)=>b.count-a.count || a.label.localeCompare(b.label)),
      representative_task_ids:(source.representative_task_ids || []).filter(id=>members.includes(id))});
  };
  if (mode === 'families') {
    const families = new Map();
    for (const task of tasks) { const id = task.family || UNSPECIFIED; if (!families.has(id)) families.set(id,[]); families.get(id).push(task.id); }
    for (const [id,ids] of families) append({id,label:id === UNSPECIFIED ? 'Unspecified task family' : prettyFamily(id),
      raw_label:id === UNSPECIFIED ? null : id,
      description:id === UNSPECIFIED ? 'These task packages have no recorded evaluator-family label.' : `Tasks sharing the source evaluator-family label “${id}”. Explore their contracts and scientific domains below.`,
      filter_kind:'family',filter_value:id}, ids);
  } else {
    for (const source of searchFamilies?.groups || []) {
      const ids = source.task_ids || tasks.filter(task=>searchFamilies.task_annotations?.[task.id]?.search_family_id === source.id).map(task=>task.id);
      append({...source,filter_kind:'search_family',filter_value:source.id},ids);
    }
    if (searchFamilies) append({id:'unclassified',label:'Unclassified methods',description:'No declared method-family grouping is recorded for these task packages.',filter_kind:'search_family',filter_value:'unclassified'}, tasks.filter(task=>!claimed.has(task.id)).map(task=>task.id));
  }
  groups.sort((a,b)=>b.count-a.count || a.label.localeCompare(b.label));
  return {mode,tasks,groups,total:tasks.length,domainsAvailable,methodology:searchFamilies?.methodology};
}

/** Deterministic decorative layout, with space between islands and an open center. */
export function layoutAtlasGroups(groups) {
  const placed = [], center = {x:450,y:338};
  const candidates = [];
  for (let y=76;y<=598;y+=13) for (let x=86;x<=814;x+=13) {
    const dx=(x-center.x)/342,dy=(y-center.y)/270;
    if (dx*dx+dy*dy<=1 && Math.hypot(x-center.x,y-center.y)>136) candidates.push({x,y});
  }
  groups.forEach((group,index)=>{
    const radius=Math.max(11, Math.sqrt(group.count)*3.14+9);
    const angle = (-110 + (index < 8 ? index*45 : index*137.508))*Math.PI/180;
    const target={x:center.x+Math.cos(angle)*270,y:center.y+Math.sin(angle)*216};
    let chosen=null,best=Infinity;
    for (const point of candidates) {
      const boundary=Math.max(0,58+radius-point.x,point.x+radius-842,52+radius-point.y,point.y+radius-626);
      const inner=Math.max(0,94+radius-Math.hypot(point.x-center.x,point.y-center.y));
      const overlap=placed.reduce((sum,item)=>sum+Math.max(0,radius+item.radius+7-Math.hypot(point.x-item.x,point.y-item.y))**2,0);
      const score=Math.hypot(point.x-target.x,point.y-target.y)+100*(overlap+boundary**2+inner**2);
      if(score<best){best=score;chosen=point;}
    }
    const item={...group,...chosen,radius};
    const seed=hash(group.id), rotation=(seed%360)*Math.PI/180, sx=.84+(seed%29)/100, sy=1/sx;
    // An irregular hexagonal island keeps individual squares apart at every task count.
    const cells=[], side=Math.ceil(Math.sqrt(group.count)*1.15)+3;
    for(let row=-side;row<=side;row++) for(let col=-side;col<=side;col++) {
      const x=(col+(row%2)*.5)*5.3,y=row*4.65,theta=Math.atan2(y,x);
      const boundary=1+.14*Math.sin(theta*3+rotation)+.09*Math.cos(theta*5-rotation);
      cells.push({x,y,rank:Math.hypot(x/sx,y/sy)/boundary});
    }
    cells.sort((a,b)=>a.rank-b.rank || a.x-b.x || a.y-b.y);
    item.points=group.tasks.map((task,pointIndex)=>{
      const cell=cells[pointIndex],jitter=hash(task.id),dx=cell.x+((jitter%9)-4)*.12,dy=cell.y+((Math.floor(jitter/9)%9)-4)*.12;
      return {id:task.id,name:task.name || task.id,x:Number((item.x+dx*Math.cos(rotation)-dy*Math.sin(rotation)).toFixed(2)),
        y:Number((item.y+dx*Math.sin(rotation)+dy*Math.cos(rotation)).toFixed(2)),size:3.35+(jitter%4)*.16,tone:jitter%5};
    });
    placed.push(item);
  });
  return placed;
}

/** Root calls this on catalog/URL changes. Internal hover and selection survive unrelated renders. */
export function renderArenaAtlas(root, options = {}) {
  let session = atlasSessions.get(root);
  if (!session) {
    session={mode:options.current?.atlasMode || 'methods',selected:null,preview:null,pickerOpen:false,search:'',options};
    atlasSessions.set(root,session);
  }
  session.options=options;
  if (['methods','families'].includes(options.current?.atlasMode) && options.current.atlasMode!==session.mode) {
    session.mode=options.current.atlasMode;session.selected=null;session.preview=null;
  }
  const key=[options.catalog,options.insights,options.searchFamilies,session.mode,options.errors?.searchFamilies,options.errors?.catalog,options.loading];
  const changed=!session.key || key.some((value,index)=>value!==session.key[index]);
  if(changed){session.model=buildAtlasModel({...options,mode:session.mode});session.layout=layoutAtlasGroups(session.model.groups);session.key=key;}
  const requested=options.current?.[session.mode === 'methods' ? 'search_family' : 'family'];
  if(requested && session.model.groups.some(group=>group.id===requested)) session.selected=requested;
  if(session.selected && !session.model.groups.some(group=>group.id===session.selected)) session.selected=null;
  if (session.built && !changed) { session.update(); return; }
  session.built=true;
  const doc=root.ownerDocument;
  const make=(tag,cls,value)=>{const node=doc.createElement(tag);if(cls)node.className=cls;if(value!=null)node.textContent=String(value);return node;};
  const svgNode=(tag,attributes={})=>{const node=doc.createElementNS(SVG,tag);for(const[key,value]of Object.entries(attributes))node.setAttribute(key,String(value));return node;};
  const button=(label,cls,action)=>{const node=make('button',cls,label);node.type='button';node.addEventListener('click',action);return node;};
  const card=make('section','atlas-card');card.setAttribute('aria-label','Interactive task atlas');
  const header=make('header','atlas-header'),heading=make('div','atlas-heading');
  heading.append(make('span','atlas-eyebrow','A PLACE TO EXPLORE'),make('h2','','Task atlas'),make('p','atlas-intro','Find a research direction. Every square is a real task.'));
  const modeControl=make('div','atlas-modes');modeControl.setAttribute('role','group');modeControl.setAttribute('aria-label','Group tasks by');
  for(const[mode,label]of[['methods','Search methods'],['families','Task families']]) {
    const control=button(label,'atlas-mode',()=>{
      if(session.mode===mode)return;session.mode=mode;session.selected=null;session.preview=null;session.search='';
      session.options.onModeChange?.(mode);
      renderArenaAtlas(root,{...session.options,current:{...session.options.current,atlasMode:mode}});
      root.querySelector(`[data-atlas-mode="${mode}"]`)?.focus({preventScroll:true});
    });control.dataset.atlasMode=mode;control.setAttribute('aria-pressed',String(session.mode===mode));modeControl.append(control);
  }
  header.append(heading,modeControl);card.append(header);
  if (!options.catalog || session.model.total === 0) {
    const missing=make('div','atlas-unavailable'),isLoading=!options.catalog && options.loading && !options.errors?.catalog;
    const title=!options.catalog?(isLoading?'The task atlas is loading…':'Task atlas unavailable'):'No tasks in this catalog';
    const message=!options.catalog?'The task catalog is needed to show real task points and counts. It is not available yet.':'The current catalog contains no task packages. New task definitions can be proposed through the repository.';
    missing.append(make('span','atlas-unavailable-mark','◌'),make('h3','',title),make('p','',message));
    card.append(missing);root.replaceChildren(card);session.update=()=>{};return;
  }
  if (session.mode === 'methods' && !options.searchFamilies) {
    const missing=make('div','atlas-unavailable'),isLoading=options.loading && !options.errors?.searchFamilies;
    missing.append(make('span','atlas-unavailable-mark','◌'),make('h3','',isLoading?'The method atlas is loading…':'Method atlas unavailable'),
      make('p','',isLoading?'Loading the source method-family assignments. You can already explore the catalog by task family.':'Method-family data could not be loaded. This does not mean the tasks have no method associations. Task-family grouping remains available.'),
      button('Explore task families →','atlas-browse',()=>modeControl.querySelector('[data-atlas-mode="families"]').click()));
    card.append(missing);root.replaceChildren(card);session.update=()=>{};return;
  }
  const body=make('div','atlas-body'),canvas=make('div','atlas-canvas'),map=svgNode('svg',{viewBox:'0 0 900 680',class:'atlas-map',role:'group','aria-label':`${session.mode==='methods'?'Search method':'Task family'} clusters. Select a cluster to explore its tasks.`});
  const mapTitle=svgNode('title');mapTitle.textContent='Task atlas: one square per catalog task';map.append(mapTitle);
  const center=svgNode('g',{class:'atlas-center','aria-hidden':'true'}),centerValue=svgNode('text',{x:450,y:327,'text-anchor':'middle',class:'atlas-center-value'}),centerLabel=svgNode('text',{x:450,y:354,'text-anchor':'middle',class:'atlas-center-label'});
  center.append(centerValue,centerLabel);map.append(center);
  const clusters=new Map();
  const choose=id=>{session.selected=session.selected===id?null:id;session.preview=null;session.update();};
  for(const[groupIndex,group]of session.layout.entries()) {
    const cluster=svgNode('g',{class:'atlas-cluster',tabindex:0,role:'button','aria-label':`${group.label}, ${format(group.count)} tasks. Select cluster.`, 'aria-pressed':'false','data-atlas-cluster':group.id});
    const hit=svgNode('circle',{cx:group.x,cy:group.y,r:Math.max(23,group.radius+8),class:'atlas-cluster-hit'});cluster.append(hit);
    for(const point of group.points) {
      const particle=svgNode('rect',{x:point.x,y:point.y,width:point.size,height:point.size,rx:.9,class:`atlas-point atlas-tone-${point.tone}`,'data-task-id':point.id,'aria-hidden':'true'});
      const title=svgNode('title');title.textContent=point.name;particle.append(title);cluster.append(particle);
    }
    const above=group.y<338,labelY=group.y+(above?-group.radius-17:group.radius+24);
    const label=svgNode('text',{x:group.x,y:Math.max(26,Math.min(650,labelY)),'text-anchor':'middle',class:`atlas-cluster-label${groupIndex<8?' atlas-label-priority':''}`});
    const words=String(group.label).split(' '),lines=[''];for(const word of words){if(lines[lines.length-1].length+word.length>24 && lines.length<2)lines.push(word);else lines[lines.length-1]+=(lines[lines.length-1]?' ':'')+word;}
    for(const[lineIndex,line]of lines.entries()){const span=svgNode('tspan',{x:group.x,dy:lineIndex?17:0});span.textContent=line;label.append(span);}cluster.append(label);
    cluster.addEventListener('pointerenter',()=>{session.preview=group.id;session.update();});
    cluster.addEventListener('pointerleave',()=>{session.preview=null;session.update();});
    cluster.addEventListener('focus',()=>{session.preview=group.id;session.update();});
    cluster.addEventListener('blur',()=>{session.preview=null;session.update();});
    cluster.addEventListener('click',()=>choose(group.id));
    cluster.addEventListener('keydown',event=>{
      if(event.key==='Enter'||event.key===' '){event.preventDefault();choose(group.id);}
      if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'].includes(event.key)){
        event.preventDefault();const step=['ArrowRight','ArrowDown'].includes(event.key)?1:-1;
        const next=session.layout[(groupIndex+step+session.layout.length)%session.layout.length];clusters.get(next.id)?.focus();
      }
    });
    clusters.set(group.id,cluster);map.append(cluster);
  }
  canvas.append(map);
  const legend=make('div','atlas-map-legend');legend.append(make('span','atlas-key-square'),make('span','',`${format(session.model.total)} task packages · ${format(session.model.groups.length)} ${session.mode==='methods'?'method groups':'task-family groups'}`));canvas.append(legend);
  const aside=make('aside','atlas-context');aside.setAttribute('aria-label','Cluster details');
  const picker=make('div','atlas-picker'),pickerLabel=make('label','atlas-picker-label','Jump to a cluster'),select=make('select','atlas-select');select.setAttribute('aria-label','Select atlas cluster');
  const fillOptions=()=>{
    select.replaceChildren(make('option','','All clusters'));select.firstChild.value='';
    const matching=session.model.groups.filter(group=>!session.search || `${group.label} ${group.raw_label||''}`.toLowerCase().includes(session.search.toLowerCase()));
    for(const group of [...matching].sort((a,b)=>a.label.localeCompare(b.label))){const option=make('option','',`${group.label} · ${format(group.count)}`);option.value=group.id;select.append(option);}
    if(!matching.length){const option=make('option','','No matching families');option.disabled=true;select.append(option);}
    select.value=session.selected||'';
  };
  if(session.mode==='families'){
    const search=make('input','atlas-family-search');search.type='search';search.placeholder=`Search ${session.model.groups.length} families…`;search.setAttribute('aria-label','Search atlas task families');search.value=session.search;
    search.addEventListener('input',()=>{session.search=search.value;fillOptions();});pickerLabel.append(search);
  }
  fillOptions();
  select.addEventListener('change',()=>{session.selected=select.value||null;session.preview=null;session.update();});pickerLabel.append(select);picker.append(pickerLabel);aside.append(picker);
  const details=make('div','atlas-details');aside.append(details);body.append(canvas,aside);card.append(body);
  const footer=make('footer','atlas-footer');
  const hint=make('p','','Select a cluster to keep it highlighted. Use arrow keys to move between clusters; Escape clears the selection.');
  const note=make('details','atlas-note');note.append(make('summary','','About this map'),make('p','','One square is one task package, including unsupported definitions. Cluster size reflects package count. Positions are a visual arrangement of groups, not distances, performance or solved results.'));
  if(session.mode==='methods')note.append(make('p','','Method groups follow the source paper-family labels. A task with several paper associations uses its recorded primary group for this map.'));
  else note.append(make('p','','Task families use the evaluator-family field in the catalog. Packages without that field remain in the Unspecified group.'));
  footer.append(hint,note);card.append(footer);
  card.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();session.selected=null;session.preview=null;session.update();}});
  root.replaceChildren(card);
  session.update=()=>{
    const activeId=session.preview||session.selected,active=session.model.groups.find(group=>group.id===activeId);
    card.dataset.hasSelection=String(Boolean(active));
    for(const[id,cluster]of clusters){cluster.classList.toggle('is-active',id===activeId);cluster.classList.toggle('is-muted',Boolean(activeId)&&id!==activeId);cluster.setAttribute('aria-pressed',String(id===session.selected));}
    centerValue.textContent=format(active?.count??session.model.total);centerLabel.textContent=active?'tasks in this cluster':'task packages';
    select.value=session.selected||'';
    // Keep the panel stable while the same cluster remains active.
    const panelKey=activeId+'|'+session.selected;
    if(details.dataset.panelKey===panelKey)return;details.dataset.panelKey=panelKey;details.replaceChildren();
    if(!active){
      details.append(make('span','atlas-context-kicker','THE RESEARCH LANDSCAPE'),make('h3','','Many paths.\nOne shared arena.'),
        make('p','atlas-context-description','Explore the methods behind the papers, or switch to the kinds of tasks they tackle. Choose a cluster to see its domains and concrete examples.'));
      const list=make('div','atlas-starting-points');
      for(const group of session.model.groups.slice(0,4)){
        const item=button('','atlas-starting-point',()=>{session.selected=group.id;session.preview=null;session.update();});item.append(make('span','',group.label),make('span','',`${format(group.count)} ↗`));list.append(item);
      }
      details.append(list);return;
    }
    const status=make('div','atlas-selection-status');status.append(make('span','atlas-context-kicker',session.selected===active.id?'SELECTED CLUSTER':'CLUSTER PREVIEW'));
    if(session.selected){const clear=button('Clear','atlas-clear',()=>{session.selected=null;session.preview=null;session.update();});clear.setAttribute('aria-label','Clear atlas selection');status.append(clear);}
    details.append(status,make('h3','',active.label),make('p','atlas-context-description',active.description||'Explore the tasks recorded in this source group.'));
    const stats=make('dl','atlas-stats');
    for(const[label,value]of[['Tasks',active.count],['Domains',session.model.domainsAvailable?active.domains.filter(domain=>domain.id!=='unknown').length:null],['Executable definitions',active.executable]]){
      const item=make('div');item.append(make('dt','',label),make('dd','',value==null?'—':format(value)));stats.append(item);
    }
    details.append(stats);
    const domains=make('div','atlas-domain-tags');
    if(!session.model.domainsAvailable)domains.append(make('p','atlas-domain-unavailable','Domain data unavailable'));
    for(const domain of active.domains.slice(0,2))domains.append(make('span','',`${domain.label} · ${format(domain.count)}`));
    if(active.domains.length>2){const more=make('span','',`+${active.domains.length-2} more`);more.title=active.domains.slice(2).map(domain=>`${domain.label}: ${format(domain.count)}`).join(' · ');domains.append(more);}details.append(domains);
    if(active.why_it_matters){const why=make('details','atlas-context-why');why.append(make('summary','','About this method group'),make('p','',active.why_it_matters));details.append(why);}
    const examples=make('div','atlas-examples');examples.append(make('h4','','A few starting points'));
    const ids=[...new Set([...active.representative_task_ids,...active.task_ids])].slice(0,2);
    for(const id of ids){const task=active.tasks.find(item=>item.id===id),link=make('a','atlas-task-link',task.name||task.id);link.href=`/?task=${encodeURIComponent(id)}`;link.addEventListener('click',event=>{if(session.options.onTask&&event.button===0&&!event.metaKey&&!event.ctrlKey&&!event.shiftKey&&!event.altKey){event.preventDefault();session.options.onTask(id);}});examples.append(link);}
    details.append(examples);
    const browse=button(`Browse ${format(active.count)} tasks →`,'atlas-browse',()=>session.options.onFilter?.(active.filter_kind,active.filter_value));details.append(browse);
    if(session.selected!==active.id)details.append(button('Keep this cluster selected','atlas-pin',()=>{session.selected=active.id;session.preview=null;session.update();}));
  };
  session.update();
}
