/** Saved evaluator geometry only. No browser-side candidate execution. */
const sessions = new WeakMap();
const PAGE_SIZE = 120;
const SVG = 'http://www.w3.org/2000/svg';
const finite = value => typeof value === 'number' && Number.isFinite(value);
const active = s => !s.dead && !s.paused && sessions.get(s.root) === s;
const make = (s, tag, cls, text) => {
  const node=s.root.ownerDocument.createElement(tag);
  if(cls)node.className=cls;
  if(text!==undefined)node.textContent=String(text);
  return node;
};
const button = (s, cls, text, fn) => {
  const node=make(s,'button',cls,text);node.type='button';node.addEventListener('click',fn);return node;
};
const labelOf = item => item.program_id || item.evaluation_id || item.id;
const scoreOf = item => item.valid===true&&finite(item.score)?item.score.toFixed(9):item.valid===false?'Invalid layout':'Score unavailable';
const timeOf = value => {
  const date=typeof value==='string'?new Date(value):null;
  return date&&Number.isFinite(date.valueOf())?new Intl.DateTimeFormat('en-GB',{
    day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:'UTC',hour12:false
  }).format(date)+' UTC':'Not recorded';
};
function geometry(item) {
  return Array.isArray(item.centers)&&Array.isArray(item.radii)&&item.radii.length>0
    &&item.centers.length===item.radii.length&&item.radii.length<=4096
    &&item.centers.every(row=>Array.isArray(row)&&row.length===2&&row.every(finite))
    &&item.radii.every(finite);
}
function board(s,item,large=false) {
  const doc=s.root.ownerDocument,svg=doc.createElementNS(SVG,'svg');
  svg.classList.add('pg-board');if(large)svg.classList.add('pg-board-large');
  svg.setAttribute('viewBox','-0.01 -0.01 1.02 1.02');svg.setAttribute('role','img');
  svg.setAttribute('aria-label','Saved packing '+labelOf(item)+': '+item.radii.length+' circles'+(item.valid===false?', invalid layout':''));
  const title=doc.createElementNS(SVG,'title');title.textContent=svg.getAttribute('aria-label');svg.append(title);
  const square=doc.createElementNS(SVG,'rect');
  for(const [key,value] of Object.entries({x:0,y:0,width:1,height:1,fill:'#fff',stroke:'#69727d','stroke-width':.003}))square.setAttribute(key,String(value));
  svg.append(square);
  item.centers.forEach(([x,y],index)=>{
    if(item.radii[index]<0)return; // Negative radii have no drawable circle; never take abs().
    const circle=doc.createElementNS(SVG,'circle');
    for(const [key,value] of Object.entries({cx:x,cy:1-y,r:item.radii[index],fill:'#edf1f6',stroke:'#61738d','stroke-width':.0025}))circle.setAttribute(key,String(value));
    circle.dataset.circleIndex=String(index);svg.append(circle);
  });
  return svg;
}
function build(s) {
  s.panel=make(s,'section','packings');s.panel.setAttribute('aria-label','Packing layouts');
  const heading=make(s,'header','pg-heading'),intro=make(s,'div');
  intro.append(make(s,'h2','','Packings'),make(s,'p','','Every available saved layout, including earlier and retired programs.'));
  s.refresh=button(s,'pg-refresh','Refresh',()=>load(s));heading.append(intro,s.refresh);
  const toolbar=make(s,'div','pg-toolbar');
  s.search=make(s,'input','pg-search');s.search.type='search';s.search.placeholder='Search program, evaluation or source…';s.search.setAttribute('aria-label','Search packing history');
  s.search.addEventListener('input',()=>{cancel(s);s.query=s.search.value;s.searchTimer=setTimeout(()=>filter(s),200);});
  const select=(cls,label,values,onChange)=>{
    const wrap=make(s,'label','pg-control');wrap.append(make(s,'span','',label));const node=make(s,'select',cls);node.setAttribute('aria-label',label);
    for(const [value,text] of values){const option=make(s,'option','',text);option.value=value;node.append(option);}
    node.addEventListener('change',onChange);wrap.append(node);toolbar.append(wrap);return node;
  };
  toolbar.append(s.search);
  s.sortControl=select('pg-sort','Sort',[['score','Highest score'],['newest','Newest first'],['oldest','Oldest first']],()=>{s.sort=s.sortControl.value;filter(s);});
  s.islandControl=select('pg-island','Island',[['all','All islands']],()=>{s.island=s.islandControl.value;filter(s);});
  s.count=make(s,'p','pg-count','Loading saved layouts…');s.count.setAttribute('role','status');
  s.notice=make(s,'p','pg-notice');s.notice.hidden=true;
  s.error=make(s,'div','pg-error');s.error.hidden=true;s.error.setAttribute('role','status');
  s.empty=make(s,'div','pg-empty');s.empty.hidden=true;
  s.grid=make(s,'div','pg-grid');s.grid.setAttribute('aria-label','Saved packing layouts');
  s.more=button(s,'pg-more','Load more',()=>{if(!s.loading&&s.hasMore){s.wanted=s.nextOffset+PAGE_SIZE;load(s,{append:true});}});s.more.hidden=true;
  s.panel.append(heading,toolbar,s.count,s.notice,s.error,s.empty,s.grid,s.more);
  s.dialog=make(s,'dialog','pg-dialog');s.dialog.setAttribute('aria-label','Packing details');
  const top=make(s,'header','pg-detail-heading');s.detailTitle=make(s,'h3');
  s.close=button(s,'pg-close','Close',()=>closeDetail(s));top.append(s.detailTitle,s.close);
  s.detail=make(s,'div','pg-detail');s.dialog.append(top,s.detail);
  s.dialog.addEventListener('click',event=>{if(event.target===s.dialog)closeDetail(s);});
  s.dialog.addEventListener('close',()=>{s.detailOpen=false;});
  s.dialog.addEventListener('cancel',()=>{s.detailOpen=false;});
  s.root.replaceChildren(s.panel,s.dialog);
}
function closeDetail(s) {
  s.detailOpen=false;
  if(typeof s.dialog.close==='function')s.dialog.close();else s.dialog.removeAttribute('open');
}
function showDetail(s,item) {
  s.selected=item.id;s.selectedItem=item;s.detailOpen=true;updateSelection(s);
  const signature=JSON.stringify(item);
  if(signature!==s.detailSignature){
    const open=s.detail.querySelector('details')?.open===true;
    const top=s.dialog.scrollTop;
    s.detailSignature=signature;s.detailTitle.textContent=labelOf(item);
    const visual=make(s,'div','pg-large');visual.append(board(s,item,true));
    visual.append(make(s,'p','pg-caption',item.valid===false?'Recorded invalid geometry. Parts outside the unit square may be clipped.':'Unit square · '+item.radii.length+' saved circles'));
    if(item.radii.some(radius=>radius<0))visual.append(make(s,'p','pg-caption','Negative radii cannot be drawn; their exact values remain below.'));
    const info=make(s,'div','pg-detail-info'),score=make(s,'div','pg-large-score',scoreOf(item));
    info.append(make(s,'span','pg-score-label','Sum of radii'),score);
    const metadata=make(s,'dl','pg-metadata');
    const fields=[['Validity',item.valid===true?'Valid under the recorded evaluator':item.valid===false?'Invalid under the recorded evaluator':'Not recorded'],
      ['Program',item.program_id||'Not admitted / no program link'],['Island',item.island_id??'Not recorded'],
      ['Iteration',item.iteration??'Not recorded'],['Recorded',timeOf(item.timestamp)],
      ['Evaluation',item.evaluation_id||'Not recorded'],['Source SHA-256',item.source_sha256||'Not recorded']];
    if(item.witness_sha256)fields.push(['Witness SHA-256',item.witness_sha256]);
    if(item.provenance?.kind)fields.push(['Saved evidence',String(item.provenance.kind).replaceAll('_',' ')]);
    for(const [label,value] of fields){const row=make(s,'div');row.append(make(s,'dt','',label),make(s,'dd','',value));if(label==='Recorded')row.lastChild.title=item.timestamp||'';metadata.append(row);}
    info.append(metadata);
    const code=button(s,'pg-code','Open Code & diff ↗',()=>{if(item.program_id){closeDetail(s);s.onProgram?.(item.program_id);}});
    code.disabled=!item.program_id;info.append(code);
    const exact=make(s,'details','pg-exact');exact.open=open;exact.append(make(s,'summary','','Recorded coordinates'));
    const pre=make(s,'pre','',JSON.stringify({centers:item.centers,radii:item.radii},null,2));pre.tabIndex=0;exact.append(pre);info.append(exact);
    s.detail.replaceChildren(visual,info);s.dialog.scrollTop=top;
  }
  if(!s.dialog.open){if(typeof s.dialog.showModal==='function')s.dialog.showModal();else s.dialog.setAttribute('open','');}
}
function updateSelection(s){for(const row of s.tiles.values())row.node.setAttribute('aria-pressed',String(row.item.id===s.selected));}
function tile(s,item) {
  const node=button(s,'pg-tile','',()=>showDetail(s,row.item));node.dataset.packingId=item.id;
  const row={node,item,signature:null};return row;
}
function updateTile(s,row,item) {
  row.item=item;const signature=JSON.stringify(item);if(signature===row.signature)return;
  row.signature=signature;row.node.dataset.packingId=item.id;
  row.node.classList.toggle('is-invalid',item.valid===false);
  const caption=make(s,'div','pg-tile-caption'),name=make(s,'strong','pg-id',labelOf(item));name.title=labelOf(item);
  const value=make(s,'span','pg-score',scoreOf(item));value.title=item.valid===true?'Native sum of radii':'A penalty score is not a physical measurement';
  const meta=make(s,'span','pg-tile-meta',item.island_id===null||item.island_id===undefined?'Island not recorded':'Island '+item.island_id);
  if(item.iteration!==null&&item.iteration!==undefined)meta.textContent+=' · G'+item.iteration;
  caption.append(name,value,meta);row.node.replaceChildren(board(s,item),caption);
}
function apply(s,payload,items) {
  const scroll=s.root.scrollTop,gridScroll=s.grid.scrollTop;
  s.payload=payload;s.items=items;s.hasMore=payload.has_more===true;s.loadedVersion=s.version;s.serverVersion=payload.content_version??payload.version;
  const wanted=new Set(items.map(item=>item.id));
  for(const [id,row] of s.tiles)if(!wanted.has(id)){row.node.remove();s.tiles.delete(id);}
  let cursor=s.grid.firstChild;
  for(const item of items){let row=s.tiles.get(item.id);if(!row){row=tile(s,item);s.tiles.set(item.id,row);}updateTile(s,row,item);
    if(row.node!==cursor)s.grid.insertBefore(row.node,cursor);cursor=row.node.nextSibling;
  }
  const selected=items.find(item=>item.id===s.selected);if(selected&&s.detailOpen)showDetail(s,selected);updateSelection(s);
  const islands=new Set((payload.islands||[]).map(value=>String(typeof value==='object'?value.id:value)));
  if(s.island!=='all')islands.add(s.island);
  const values=['all',...Array.from(islands).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}))];
  if(JSON.stringify([...s.islandControl.options].map(option=>option.value))!==JSON.stringify(values)){
    s.islandControl.replaceChildren(...values.map(value=>{const option=make(s,'option','',value==='all'?'All islands':'Island '+value);option.value=value;return option;}));s.islandControl.value=s.island;
  }
  const supported=payload.supported!==false,total=Number.isSafeInteger(payload.total)?payload.total:items.length;
  s.count.textContent=supported?'Showing '+items.length+' of '+total+' matching layouts':'Packing gallery unavailable';
  const notes=[];
  if(Number.isSafeInteger(payload.available))notes.push(payload.available+' saved layouts available');
  if(payload.unavailable>0)notes.push(payload.unavailable+' evaluations have no available verified layout');
  if(s.clientUnavailable)notes.push(s.clientUnavailable+' returned layouts could not be drawn');
  s.notice.textContent=notes.join(' · ');s.notice.hidden=!notes.length;
  s.empty.hidden=items.length>0;
  if(!items.length){s.empty.replaceChildren(make(s,'strong','',!supported?'Packing layouts are not supported for this run':total===0&&(s.query||s.island!=='all')?'No matching layouts':'No saved packing layouts yet'),make(s,'p','',!supported?(payload.supported_reason||payload.reason||'This gallery requires saved circle-packing geometry.'):(s.query||s.island!=='all')?'Try another search or island.':'Layouts appear after the evaluator saves complete geometry. Missing layouts are not reconstructed.'));}
  s.more.hidden=!supported||!s.hasMore;s.more.textContent='Load more'+(total>items.length?' · '+(total-items.length)+' remaining':'');
  s.root.scrollTop=scroll;s.grid.scrollTop=gridScroll;
}
function cancel(s) {s.request++;s.controller?.abort();s.controller=null;clearTimeout(s.searchTimer);s.loading=false;}
function filter(s) {if(!active(s))return;s.wanted=PAGE_SIZE;load(s,{reset:true});}
async function load(s,{append=false,reset=false}={}) {
  if(!active(s))return;
  cancel(s);const request=s.request,version=s.version;
  const filters={sort:s.sort,island:s.island,q:s.query};
  s.controller=new s.root.ownerDocument.defaultView.AbortController();const controller=s.controller;
  s.loading=true;s.refresh.disabled=true;s.more.disabled=true;s.error.hidden=true;s.panel.setAttribute('aria-busy','true');
  const current=()=>active(s)&&s.request===request;
  try {
    let items=append?s.items.slice():[],offset=append?s.nextOffset:0,payload=null,serverVersion=append?s.serverVersion:null;
    const target=reset?PAGE_SIZE:Math.max(PAGE_SIZE,s.wanted);let restarted=false,unavailable=append?s.clientUnavailable:0;
    while(true){
      const params=new URLSearchParams({offset:String(offset),limit:String(PAGE_SIZE),...filters});
      payload=await s.fetchJSON('/api/runs/'+encodeURIComponent(s.runId)+'/packings?'+params,{signal:controller.signal});
      if(!current())return;
      if(payload.schema!=='sciel-packings/1'||!Array.isArray(payload.items))throw new Error('Saved packing data has an unsupported format.');
      const stamp=payload.content_version??payload.version;
      if(serverVersion!=null&&stamp!==serverVersion){
        if(restarted)throw new Error('Packing history changed while loading. Refresh to load a consistent page.');
        restarted=true;items=[];offset=0;serverVersion=null;unavailable=0;continue;
      }
      serverVersion=stamp;
      const known=new Set(items.map(item=>item.id));
      for(const item of payload.items){if(typeof item.id!=='string'||!geometry(item)){unavailable++;continue;}if(!known.has(item.id)){items.push(item);known.add(item.id);}}
      const step=Number.isSafeInteger(payload.limit)&&payload.limit>0?payload.limit:PAGE_SIZE;
      const next=Number.isSafeInteger(payload.next_offset)?payload.next_offset:offset+step;
      if(payload.has_more===true&&next<=offset)throw new Error('Packing page did not advance.');
      offset=next;
      if(!payload.has_more||offset>=target)break;
    }
    if(!current())return;
    s.nextOffset=offset;s.clientUnavailable=unavailable;apply(s,payload,items);s.loadedVersion=version;
  } catch(error) {
    if(!current()||error?.name==='AbortError')return;
    s.error.textContent='Unable to load saved layouts. '+String(error?.message||error);s.error.hidden=false;
    if(!s.items.length)s.count.textContent='Saved layouts unavailable';
  } finally {
    if(current()){s.loading=false;s.controller=null;s.refresh.disabled=false;s.more.disabled=false;s.panel.removeAttribute('aria-busy');}
  }
}

export function renderPackings(root,options={}) {
  const key=JSON.stringify([options.runId,options.identity]);let s=sessions.get(root);
  if(!s||s.key!==key){if(s)destroyPackings(root);s={root,key,runId:options.runId,version:options.version,loadedVersion:null,dead:false,paused:false,request:0,sort:'score',island:'all',query:'',items:[],tiles:new Map(),wanted:PAGE_SIZE,nextOffset:0,hasMore:false,selected:null,detailOpen:false,clientUnavailable:0};sessions.set(root,s);build(s);}
  s.fetchJSON=options.fetchJSON||((url,init)=>fetch(url,init).then(response=>{if(!response.ok)throw new Error('HTTP '+response.status);return response.json();}));s.onProgram=options.onProgram;
  s.paused=false;const changed=s.version!==options.version;s.version=options.version;
  if(!s.payload||changed||s.loadedVersion!==s.version){if(!s.loading||changed)load(s);}
  return s.panel;
}

export function suspendPackings(root) {
  const s=sessions.get(root);if(!s||s.paused)return;s.paused=true;cancel(s);closeDetail(s);
  s.refresh.disabled=false;s.more.disabled=false;s.panel.removeAttribute('aria-busy');
}

export function destroyPackings(root) {
  const s=sessions.get(root);if(!s)return;s.dead=true;cancel(s);closeDetail(s);sessions.delete(root);root.replaceChildren();
}
