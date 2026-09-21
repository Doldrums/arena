const numeric = value => typeof value === 'number' && Number.isFinite(value);
const fmt = value => numeric(value) ? new Intl.NumberFormat('en', {maximumSignificantDigits:5}).format(value) : 'Not recorded';
const compact = value => numeric(value) ? new Intl.NumberFormat('en', {notation:'compact',maximumFractionDigits:1}).format(value) : 'Not recorded';
const minutes = value => `${fmt(Math.round(value / 6) / 10)} min`;
const names = {'sciel-release':'SCiEL',sciel:'SCiEL · source',shinka:'ShinkaEvolve','ael-portfolio-gateway':'AEL','qdaif-poetry-gateway':'QDAIF','aflow-gateway-gsm8k-v1':'AFlow','promptagent-penguins-gateway':'PromptAgent','funsearch-original-timeout-v2':'FunSearch · original v2','gepa-gateway-gsm8k':'GEPA','miprov2-gateway-gsm8k':'MIPROv2','adas-gateway-mgsm-v1':'ADAS',dgm:'DGM','eoh-s-gateway-v2':'EoH-S · v2','coevo-observed-v2':'CoEvo · v2','darwinian-evolver-gateway':'Darwinian Evolver','mcts-ahd-gateway-v2':'MCTS-AHD · v2',base:'Base','codeevolve':'CodeEvolve','openevolve':'OpenEvolve',eoh:'EoH',meoh:'MEoH',hsevo:'HSEvo',reevo:'ReEvo','llamea-hpo':'LLaMEA-HPO',adaevolve:'AdaEvolve',evox:'EvoX',loongflow:'LoongFlow'};
const name = id => names[id] || id;
const cohortKey = c => JSON.stringify([c.cohort,c.task_id,c.metric,c.direction]);

// The discovery page reads only an operator-published aggregate. It never sends a
// control credential and never falls back to private run or queue endpoints.
export function initResultsOverview({doc=document,fetcher=(...args)=>fetch(...args),storage=sessionStorage,pollMs=60000,requestTimeoutMs=20000}={}) {
  const root=doc.getElementById('results-overview'); if(!root) return {destroy(){}};
  const win=doc.defaultView; let data=null,pending=null,epoch=0,destroyed=false,expanded=false,selectedCohort='',axis='tokens',enabled=true;
  try {enabled=!storage.getItem('arena.queue.session-key');} catch {}
  const el=(tag,cls,text)=>{const n=doc.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const button=(text,callback)=>{const n=el('button','button',text);n.type='button';n.addEventListener('click',callback);return n;};
  const status=el('span','overview-status');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const retry=button('Refresh',()=>refresh());retry.setAttribute('aria-label','Refresh published overview');
  const heading=el('div','overview-context');heading.append(status,retry);
  const content=el('div','overview-content'); root.append(heading,content);
  const loading=()=>{
    content.replaceChildren();const cards=el('div','overview-stats');cards.setAttribute('aria-hidden','true');
    for(let i=0;i<4;i++){const card=el('div','overview-stat');for(const cls of ['label','value','note']) card.append(el('span',`showcase-skeleton showcase-skeleton-${cls}`));cards.append(card);}
    const plot=el('div','showcase-card overview-loading');plot.setAttribute('aria-hidden','true');plot.append(el('div','showcase-skeleton showcase-skeleton-plot'));content.append(cards,plot);
  };
  function stat(label,value,note){const card=el('article','overview-stat');card.append(el('span','',label),el('strong','',fmt(value)),el('small','',note));return card;}
  function card(title){const c=el('section','showcase-card');const h=el('header','overview-card-heading');h.append(el('h2','',title));c.append(h);return [c,h];}
  function chart(){
    const [panel,head]=card('Score & resources');
    const control=el('label','overview-select','Resource');const select=el('select');select.dataset.overviewFocus='resource';
    for(const [v,label] of [['tokens','Tokens'],['time','Wall time']]){const o=el('option','',label);o.value=v;select.append(o);}select.value=axis;select.addEventListener('change',()=>{axis=select.value;render();});control.append(select);head.append(control);
    const hasTokens=c=>c.points.some(p=>numeric(p.best_score)&&p.usage_complete&&numeric(p.total_tokens));
    const cohorts=[...data.cohorts].sort((a,b)=>Number(hasTokens(b))-Number(hasTokens(a))||b.points.length-a.points.length);
    if(!selectedCohort&&!cohorts.some(hasTokens)){axis='time';select.value=axis;}
    if(!cohorts.some(c=>cohortKey(c)===selectedCohort))selectedCohort=cohorts.length?cohortKey(cohorts[0]):'';
    const cohort=cohorts.find(c=>cohortKey(c)===selectedCohort);
    if(!cohort){panel.append(el('p','overview-chart-empty','Comparable evaluator measurements have not been published yet.'));return panel;}
    const groupControl=el('label','overview-select overview-cohort','Task / evaluator');const groups=el('select');groups.dataset.overviewFocus='cohort';
    cohorts.forEach((c,i)=>{const o=el('option','',`${c.task_name} · ${c.metric} · ${c.cohort.slice(0,8)}`);o.value=cohortKey(c);groups.append(o);});groups.value=selectedCohort;
    groups.addEventListener('change',()=>{selectedCohort=groups.value;render();});groupControl.append(groups);panel.append(groupControl);
    const resource=p=>axis==='tokens' ? p.usage_complete ? p.total_tokens : null : p.wall_seconds;
    const points=cohort.points.filter(p=>numeric(p.best_score)&&numeric(resource(p))&&resource(p)>=0);
    if(!points.length){panel.append(el('p','overview-chart-empty','No complete resource measurements for this evaluator. Try the other resource axis.'));return panel;}
    const svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 630 270');svg.classList.add('overview-plot');svg.setAttribute('role','img');svg.setAttribute('aria-label',`${cohort.task_name}: score versus ${axis==='tokens'?'recorded tokens':'wall time'}, within one evaluator contract.`);
    const draw=(tag,attrs,text)=>{const n=doc.createElementNS(svg.namespaceURI,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;svg.append(n);return n;};
    const xs=points.map(resource),ys=points.map(p=>p.best_score),low=Math.min(...ys),high=Math.max(...ys),pad=(high-low)*.15||Math.max(Math.abs(high)*.02,.01),maxX=Math.max(...xs)*1.12||1;
    const x=v=>70+v/maxX*528,y=v=>214-(v-(low-pad))/(high-low+2*pad)*164;
    for(let i=0;i<5;i++){
      const score=low-pad+(high-low+2*pad)*i/4;
      draw('line',{x1:70,x2:604,y1:y(score),y2:y(score),class:'overview-grid'});
      draw('text',{x:60,y:y(score)+4,'text-anchor':'end',class:'overview-axis'},fmt(score));
      const r=maxX*i/4;draw('text',{x:x(r),y:238,'text-anchor':'middle',class:'overview-axis'},axis==='tokens'?compact(r):`${Math.round(r/60)}m`);
    }
    draw('text',{x:70,y:21,class:'overview-axis'},`${cohort.metric} · ${cohort.direction==='maximize'?'higher':'lower'} is better`);
    draw('text',{x:605,y:261,'text-anchor':'end',class:'overview-axis'},axis==='tokens'?'Recorded tokens':'Recorded wall time');
    const detail=el('p','overview-chart-detail','Select a point to inspect its recorded measurements.');detail.setAttribute('role','status');
    points.forEach((p,index)=>{
      const info=`${name(p.system)} / ${p.model} · ${fmt(p.seed_score)} → ${fmt(p.best_score)} · ${axis==='tokens'?fmt(p.total_tokens)+' tokens':minutes(p.wall_seconds)} · ${p.state}${p.evidence_partial?' · partial evidence':''}`;
      const circle=draw('circle',{cx:x(resource(p)),cy:y(p.best_score),r:6,class:`overview-point${p.system.startsWith('sciel')?' is-sciel':''}${p.evidence_partial?' is-partial':''}`,tabindex:0,'data-overview-focus':`point-${index}`,'aria-label':info});
      const title=doc.createElementNS(svg.namespaceURI,'title');title.textContent=info;circle.append(title);circle.addEventListener('focus',()=>{detail.textContent=info;});circle.addEventListener('click',()=>{detail.textContent=info;});
    });
    panel.append(svg,detail);
    panel.append(el('p','overview-note',`${points.length} measured runs in this evaluator cohort. Models and search budgets may differ.${cohort.points.length>points.length?` ${cohort.points.length-points.length} runs without complete values on this axis.`:''}`));return panel;
  }
  function outcomes(){
    const [panel]=card('Experiment coverage');const summary=data.summary;
    const strip=el('div','overview-status-strip');strip.setAttribute('aria-hidden','true');
    const list=el('dl','overview-status-list');
    for(const [key,label] of [['completed','Completed'],['active','In progress / queued'],['failed','Stopped with an error'],['cancelled','Cancelled'],['other','Other']]){
      if(!summary[key]&&key==='other')continue;
      const segment=el('span',`is-${key}`);segment.style.flexGrow=summary[key];strip.append(segment);
      const row=el('div');const term=el('dt');term.append(el('i',`is-${key}`),doc.createTextNode(label));row.append(term,el('dd','',fmt(summary[key])));list.append(row);
    }
    panel.append(strip,list);
    const valid=data.validity;const evidence=el('div','overview-evidence');
    evidence.append(el('span','','Canonical evaluations'),el('strong','',`${fmt(valid.valid)} / ${fmt(valid.evaluations)} valid`),el('p','overview-note',`${fmt(valid.invalid)} invalid · ${fmt(valid.unknown)} unclassified. Native task metrics retain their own evaluation protocols.`));
    panel.append(evidence);return panel;
  }
  function table(){
    const [panel,head]=card('Systems at a glance');panel.classList.add('overview-table-card');head.append(el('span','overview-note',`${data.systems.length} registered configurations`));
    const wrap=el('div','overview-table-scroll');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','System results summary');
    const table=el('table','overview-table'),thead=el('thead'),tr=el('tr');for(const text of ['System','Runs','Completed','Models','Median tokens']){const th=el('th','',text);th.scope='col';tr.append(th);}thead.append(tr);table.append(thead);
    const tbody=el('tbody');const ordered=[...data.systems].sort((a,b)=>(a.system==='sciel-release'?-1:b.system==='sciel-release'?1:name(a.system).localeCompare(name(b.system))));
    for(const s of expanded?ordered:ordered.slice(0,6)){
      const row=el('tr',s.system==='sciel-release'?'overview-sciel':'');row.append(el('th','',name(s.system)));row.firstChild.scope='row';
      row.append(el('td','',fmt(s.runs)));
      const done=el('td');const meter=el('span','overview-meter',`${fmt(s.completed)} / ${fmt(s.runs)}`);meter.style.setProperty('--completion',`${s.runs?s.completed/s.runs*100:0}%`);done.append(meter);row.append(done,el('td','',fmt(s.models.length)));
      const tokens=el('td','',compact(s.median_tokens));if(s.complete_token_runs)tokens.append(el('small','',`${s.complete_token_runs} complete ledgers`));row.append(tokens);tbody.append(row);
    }
    table.append(tbody);wrap.append(table);panel.append(wrap);
    const footer=el('footer','overview-table-footer');footer.append(el('span','overview-note','Process completion and task score are separate measurements. Tokens are not dollars.'));
    if(ordered.length>6){const toggle=button(expanded?'Show fewer':`Show all ${ordered.length} systems`,()=>{expanded=!expanded;render();});toggle.dataset.overviewFocus='expand';toggle.setAttribute('aria-expanded',String(expanded));footer.append(toggle);}panel.append(footer);return panel;
  }
  function render(){
    const focused=content.contains(doc.activeElement)?doc.activeElement.dataset.overviewFocus:null;
    const scroll=content.querySelector('.overview-table-scroll')?.scrollLeft||0;
    content.replaceChildren();if(!data.summary.runs){content.append(el('div','showcase-empty','No published results yet.'));return;}
    const stats=el('div','overview-stats');stats.append(stat('Recorded runs',data.summary.runs,`${fmt(data.summary.completed)} completed · ${fmt(data.summary.active)} active or queued`),stat('System profiles',data.summary.systems,'Including versioned integration profiles'),stat('Models',data.summary.models,'Across all published runs'),stat('Verified programs',data.validity.unique_programs,'Distinct valid programs, including seeds'));
    const grid=el('div','overview-grid-layout');grid.append(chart(),outcomes());content.append(stats,grid,table());
    content.append(el('p','overview-note overview-scope',`Integration pilots · ${data.loaded} of ${data.total} accessible runs in this published snapshot.${data.truncated?' Older runs are outside this snapshot.':''} Scores are compared only within a shared evaluator contract.`));
    if(focused){const target=[...content.querySelectorAll('[data-overview-focus]')].find(n=>n.dataset.overviewFocus===focused);target?.focus({preventScroll:true});}
    const tableScroll=content.querySelector('.overview-table-scroll');if(tableScroll)tableScroll.scrollLeft=scroll;
  }
  async function refresh(){
    if(!enabled||destroyed||pending)return;const current=++epoch,controller=new win.AbortController();let timeoutId;
    pending=controller;retry.disabled=true;root.dataset.state=data?'refreshing':'loading';root.setAttribute('aria-busy','true');status.textContent=data?'Updating published snapshot…':'Loading results overview…';if(!data)loading();
    const timeout=new Promise((_,reject)=>{timeoutId=win.setTimeout(()=>{controller.abort();reject(new Error('timeout'));},requestTimeoutMs);});
    try{
      const response=await Promise.race([fetcher('/api/results-overview',{cache:'no-store',credentials:'same-origin',redirect:'error',signal:controller.signal}),timeout]);if(!response.ok)throw new Error('unavailable');
      const next=await Promise.race([response.json(),timeout]);if(current!==epoch||destroyed||!enabled)return;
      if(next?.schema!=='arena.results-overview/1'||!next.summary||!next.validity||!Array.isArray(next.systems)||!Array.isArray(next.cohorts)||!numeric(next.generated_at))throw new Error('invalid');
      data=next;retry.textContent='Refresh';render();const time=new Date((data.source_generated_at||data.generated_at)*1000);
      status.textContent=`Published snapshot · ${time.toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZoneName:'short'})}`;root.dataset.state=data.summary.runs?'ready':'empty';
    }catch{if(current!==epoch||destroyed||!enabled)return;root.dataset.state='error';status.textContent=data?'Update unavailable · showing the last published snapshot.':'Results overview is temporarily unavailable.';if(!data){content.replaceChildren(el('p','showcase-empty','The snapshot could not be loaded. Retry to reconnect.'));}retry.textContent='Retry';}
    finally{win.clearTimeout(timeoutId);if(current===epoch){pending=null;retry.disabled=false;root.setAttribute('aria-busy','false');}}
  }
  function sync(event){const next=event?!event.detail.connected:enabled;enabled=next;root.hidden=!enabled;if(enabled)refresh();else{epoch++;pending?.abort();pending=null;root.setAttribute('aria-busy','false');}}
  doc.addEventListener('arena:results-access',sync);sync();const timer=pollMs?win.setInterval(()=>{if(!doc.hidden)refresh();},pollMs):null;
  return {refresh,destroy(){destroyed=true;epoch++;pending?.abort();if(timer)win.clearInterval(timer);doc.removeEventListener('arena:results-access',sync);}};
}
if(typeof document!=='undefined'&&document.body?.dataset.resultsShowcase==='true')initResultsOverview();
