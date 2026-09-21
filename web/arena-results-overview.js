const numeric = value => typeof value === 'number' && Number.isFinite(value);
const fmt = value => numeric(value) ? new Intl.NumberFormat('en', {maximumSignificantDigits:5}).format(value) : 'Not recorded';
const scoreNumber = value => numeric(value) ? new Intl.NumberFormat('en',{maximumSignificantDigits:10}).format(value) : 'Not recorded';
const compact = value => numeric(value) ? new Intl.NumberFormat('en', {notation:'compact',maximumFractionDigits:1}).format(value) : 'Not recorded';
const minutes = value => `${fmt(Math.round(value / 6) / 10)} min`;
const names = {'sciel-release':'SCiEL',sciel:'SCiEL · source',shinka:'ShinkaEvolve','ael-portfolio-gateway':'AEL','qdaif-poetry-gateway':'QDAIF','aflow-gateway-gsm8k-v1':'AFlow','promptagent-penguins-gateway':'PromptAgent','funsearch-original-timeout-v2':'FunSearch · original v2','gepa-gateway-gsm8k':'GEPA','miprov2-gateway-gsm8k':'MIPROv2','adas-gateway-mgsm-v1':'ADAS',dgm:'DGM','eoh-s-gateway-v2':'EoH-S · v2','coevo-observed-v2':'CoEvo · v2','darwinian-evolver-gateway':'Darwinian Evolver','mcts-ahd-gateway-v2':'MCTS-AHD · v2',base:'Base','codeevolve':'CodeEvolve','openevolve':'OpenEvolve',eoh:'EoH',meoh:'MEoH',hsevo:'HSEvo',reevo:'ReEvo','llamea-hpo':'LLaMEA-HPO',adaevolve:'AdaEvolve',evox:'EvoX',loongflow:'LoongFlow'};
const name = id => names[id] || id;
const cohortKey = c => JSON.stringify([c.cohort,c.task_id,c.metric,c.direction]);

// The discovery page reads only an operator-published aggregate. It never sends a
// control credential and never falls back to private run or queue endpoints.
export function initResultsOverview({doc=document,fetcher=(...args)=>fetch(...args),storage=sessionStorage,pollMs=60000,requestTimeoutMs=20000}={}) {
  const root=doc.getElementById('results-overview'); if(!root) return {destroy(){}};
  const win=doc.defaultView; let data=null,pending=null,epoch=0,destroyed=false,expanded=false,selectedCohort='',axis='tokens',enabled=true,resultTask='',resultSystem='all',resultPage=0,researchGroup='',researchAll=false,researchPage=0;
  enabled=doc.body.dataset.resultsAccess !== 'connected';
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
    const [panel,head]=card('Systems at a glance');panel.classList.add('overview-table-card','overview-systems-table');head.append(el('span','overview-note',`${data.systems.length} registered configurations`));
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
  function resultRows(){
    const canonical=data.cohorts.flatMap(c=>c.points.filter(p=>numeric(p.best_score)).map(p=>({...p,task_id:c.task_id,task_name:c.task_name,metric:c.metric,direction:c.direction,contract:c.cohort,source:'canonical',objectives:[],population_objectives:[]})));
    const native=(data.native_results||[]).map(p=>({...p,source:'native',contract:p.system}));
    return [...canonical,...native];
  }
  const taskCategory=row=>/circle[-_ ]packing/.test(row.task_id)?'circle-packing':row.task_id;
  const taskName=id=>({'circle-packing':'Circle packing','reference-sat':'Reference SAT','online-bin-packing':'Online bin packing','oscillation_1':'Oscillation equations','gsm8k':'GSM8K','penguins-in-a-table':'Penguins in a table'})[id]||id.replace(/[-_]/g,' ').replace(/^./,c=>c.toUpperCase());
  const metricName=id=>({'sum_radii':'Sum of radii','target_ratio':'Target ratio','benchmark_ratio':'Benchmark ratio','negative_mse':'Negative MSE','mean_relative_bin_excess':'Relative bin excess','validation_excess_percent':'Validation excess (%)','heldout_accuracy':'Held-out accuracy','score':'Score'})[id]||id.replace(/_/g,' ');
  function taskResults(){
    const [panel,head]=card('Task results');panel.classList.add('overview-task-results','overview-table-card');
    const rows=resultRows(),tasks=[...new Set(rows.map(taskCategory))].sort((a,b)=>taskName(a).localeCompare(taskName(b)));
    if(!tasks.includes(resultTask))resultTask=tasks.includes('circle-packing')?'circle-packing':tasks[0]||'';
    head.append(el('span','overview-note',`${rows.length} recorded outcomes`));
    const controls=el('div','overview-result-controls');
    const taskLabel=el('label','overview-select','Task'),taskSelect=el('select');taskSelect.dataset.overviewFocus='result-task';
    for(const t of tasks){const count=rows.filter(r=>taskCategory(r)===t).length;const option=el('option','',`${taskName(t)} · ${count}`);option.value=t;taskSelect.append(option);}taskSelect.value=resultTask;
    taskSelect.addEventListener('change',()=>{resultTask=taskSelect.value;resultSystem='all';resultPage=0;render();});taskLabel.append(taskSelect);controls.append(taskLabel);
    const taskRows=rows.filter(r=>taskCategory(r)===resultTask);
    const systemLabel=el('label','overview-select','System'),systemSelect=el('select');systemSelect.dataset.overviewFocus='result-system';
    const all=el('option','','All systems');all.value='all';systemSelect.append(all);
    for(const system of [...new Set(taskRows.map(r=>r.system))].sort((a,b)=>name(a).localeCompare(name(b)))){const option=el('option','',name(system));option.value=system;systemSelect.append(option);}
    if(![...systemSelect.options].some(o=>o.value===resultSystem))resultSystem='all';systemSelect.value=resultSystem;
    systemSelect.addEventListener('change',()=>{resultSystem=systemSelect.value;resultPage=0;render();});systemLabel.append(systemSelect);controls.append(systemLabel);panel.append(controls);
    const filtered=taskRows.filter(r=>resultSystem==='all'||r.system===resultSystem).sort((a,b)=>(Number(b.system==='sciel-release')-Number(a.system==='sciel-release'))||name(a.system).localeCompare(name(b.system))||a.model.localeCompare(b.model));
    if(!filtered.length){panel.append(el('p','overview-chart-empty','No measured outcomes are published for this selection yet.'));return panel;}
    const wrap=el('div','overview-table-scroll');wrap.dataset.resultScroll='true';wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Recorded task results, scroll for all measurements');
    const table=el('table','overview-table overview-score-table'),thead=el('thead'),tr=el('tr');
    for(const text of ['System / model','Metric','Initial','Result','Change','Wall time','Tokens','Status']){const th=el('th','',text);th.scope='col';tr.append(th);}thead.append(tr);table.append(thead);
    const body=el('tbody');resultPage=Math.min(resultPage,Math.max(0,Math.ceil(filtered.length/10)-1));
    for(const r of filtered.slice(resultPage*10,resultPage*10+10)){
      const row=el('tr',r.system.startsWith('sciel')?'overview-sciel':'');row.classList.add('overview-result-row');
      const identity=el('th','',name(r.system));identity.scope='row';identity.append(el('small','',r.model));row.append(identity);
      const metric=el('td','overview-result-metric',`${metricName(r.metric)} ${r.direction==='maximize'?'↑':r.direction==='minimize'?'↓':''}`);
      metric.append(el('small','',r.source==='canonical'?`Shared evaluator · ${r.contract.slice(0,8)}`:'Framework-native evaluation'));row.append(metric,el('td','',scoreNumber(r.seed_score)));
      const outcome=el('td','overview-result-value');
      if(r.population_objectives?.length){
        const details=el('details','overview-objectives');details.append(el('summary','',`${r.population_objectives.length} objective pairs`));
        for(const pair of r.population_objectives){details.append(el('p','',r.objectives.map(o=>`${metricName(o.metric)}: ${fmt(pair[o.metric])}`).join(' · ')));}outcome.append(details);
      }else{outcome.append(el('strong','',scoreNumber(r.best_score)));}
      row.append(outcome);
      const delta=numeric(r.best_score)&&numeric(r.seed_score)?r.best_score-r.seed_score:null;
      const change=el('td',delta!==null&&delta*(r.direction==='minimize'?-1:1)>0?'overview-result-gain':'',delta===null?'Not paired':delta===0?'Unchanged':`${delta>0?'+':''}${fmt(delta)}`);
      row.append(change,el('td','',numeric(r.wall_seconds)?minutes(r.wall_seconds):'Not recorded'),el('td','',r.usage_complete?compact(r.total_tokens):'Not recorded'));
      const state=el('td','',r.state);if(r.evidence_partial)state.append(el('small','','Partial evidence'));row.append(state);body.append(row);
    }
    table.append(body);wrap.append(table);panel.append(wrap);
    const footer=el('footer','overview-table-footer');footer.append(el('span','overview-note',`${resultPage*10+1}–${Math.min((resultPage+1)*10,filtered.length)} of ${filtered.length} outcomes · one row per run, all recorded process states retained.`));
    const nav=el('div','overview-result-pages');
    for(const [text,step,key] of [['← Previous',-1,'results-prev'],['Next →',1,'results-next']]){const b=button(text,()=>{resultPage+=step;render();});b.dataset.overviewFocus=key;b.disabled=step<0?resultPage===0:(resultPage+1)*10>=filtered.length;nav.append(b);}footer.append(nav);panel.append(footer);
    panel.append(el('p','overview-results-note','Initial and result values use the same metric within each run. Native protocols stay separate; shared task names do not establish equivalent evaluation conditions.'));
    return panel;
  }
  function researchResults(){
    const research=data.research;if(!research?.runs?.length)return null;
    const [panel,head]=card('SCiEL research results');panel.classList.add('overview-table-card','overview-research-results');
    head.append(el('span','overview-note',`${research.measured} measured / ${research.total} recorded runs`));
    const groups=new Map();
    for(const r of research.runs){const key=JSON.stringify([r.task_id,r.metric,r.direction,r.protocol]);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r);}
    if(!groups.has(researchGroup))researchGroup=[...groups].sort((a,b)=>a[1][0].task_name.localeCompare(b[1][0].task_name)||new Set(b[1].flatMap(r=>r.models)).size-new Set(a[1].flatMap(r=>r.models)).size)[0][0];
    const controls=el('div','overview-result-controls');const label=el('label','overview-select','Task / evaluator'),select=el('select');select.dataset.overviewFocus='research-task';
    for(const [key,rows] of groups){const r=rows[0],o=el('option','',`${r.task_name} · ${r.protocol.slice(0,6)} · ${rows.length} runs`);o.value=key;select.append(o);}select.value=researchGroup;
    select.addEventListener('change',()=>{researchGroup=select.value;researchPage=0;render();});label.append(select);controls.append(label);
    const modeLabel=el('label','overview-select','Show'),mode=el('select');mode.dataset.overviewFocus='research-mode';
    for(const [value,text] of [['best','Best recorded per model'],['all','Every recorded run']]){const o=el('option','',text);o.value=value;mode.append(o);}mode.value=researchAll?'all':'best';mode.addEventListener('change',()=>{researchAll=mode.value==='all';researchPage=0;render();});modeLabel.append(mode);controls.append(modeLabel);panel.append(controls);
    const members=groups.get(researchGroup),context=members[0],sign=context.direction==='minimize'?-1:1;
    const models=r=>r.models.length?r.models.join(' + '):'Model not recorded';
    const buckets=new Map();for(const r of members){const key=models(r);if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(r);}
    const compare=(a,b)=>numeric(a.best_score)&&numeric(b.best_score)?sign*(b.best_score-a.best_score):numeric(a.best_score)?-1:numeric(b.best_score)?1:0;
    const representatives=[...buckets.values()].map(rows=>[...rows].sort(compare)[0]);
    const rows=(researchAll?[...members]:representatives).sort((a,b)=>models(a).localeCompare(models(b))||compare(a,b));
    const measured=members.filter(r=>numeric(r.best_score)),best=[...measured].sort(compare)[0];
    const headline=el('div','overview-research-highlight');const measurement=el('div');measurement.append(el('span','overview-note',`${metricName(context.metric)} · ${context.direction==='maximize'?'higher':'lower'} is better`),el('strong','',scoreNumber(best?.best_score)),el('small','overview-note','Best observed in this evaluator group'));
    const description=el('p','overview-note',`${members.length} recorded runs · ${buckets.size} model configurations. ${context.units.replace(/_/g,' ')}. Native observations; paused and stopped runs retain their measured outcomes.`);headline.append(measurement,description);panel.append(headline);
    const wrap=el('div','overview-table-scroll');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','SCiEL recorded research outcomes');const table=el('table','overview-table overview-research-table'),thead=el('thead'),tr=el('tr');
    for(const text of ['Model','Initial','Best recorded','Change','Elapsed to best','Run status']){const th=el('th','',text);th.scope='col';tr.append(th);}thead.append(tr);table.append(thead);const body=el('tbody');researchPage=Math.min(researchPage,Math.max(0,Math.ceil(rows.length/8)-1));
    for(const r of rows.slice(researchPage*8,researchPage*8+8)){
      const row=el('tr','overview-research-row'),identity=el('th','',models(r));identity.scope='row';if(!researchAll)identity.append(el('small','',`Selected from ${buckets.get(models(r)).length} recorded runs`));row.append(identity,el('td','',scoreNumber(r.seed_score)));
      const result=el('td','overview-result-value');result.append(el('strong','',scoreNumber(r.best_score)));row.append(result);
      const delta=numeric(r.seed_score)&&numeric(r.best_score)?r.best_score-r.seed_score:null;
      row.append(el('td',delta!==null&&delta*sign>0?'overview-result-gain':'',delta===null?'Not paired':delta===0?'Unchanged':`${delta>0?'+':''}${fmt(delta)}`),el('td','',numeric(r.to_best_wall_seconds)?minutes(r.to_best_wall_seconds):'Not recorded'),el('td','',r.state));body.append(row);
    }
    table.append(body);wrap.append(table);panel.append(wrap);
    const footer=el('footer','overview-table-footer');footer.append(el('span','overview-note',researchAll?`${researchPage*8+1}–${Math.min((researchPage+1)*8,rows.length)} of ${rows.length} recorded runs`:'Best outcome per model within this evaluator group; initial values and elapsed time come from that same run.'));
    if(rows.length>8){const nav=el('div','overview-result-pages');for(const [text,step,key] of [['← Previous',-1,'research-prev'],['Next →',1,'research-next']]){const b=button(text,()=>{researchPage+=step;render();});b.dataset.overviewFocus=key;b.disabled=step<0?researchPage===0:(researchPage+1)*8>=rows.length;nav.append(b);}footer.append(nav);}panel.append(footer);
    panel.append(el('p','overview-results-note','Elapsed time includes pauses; it is not CPU time or API cost. Task and metric versions stay in separate evaluator groups.'));
    return panel;
  }
  function render(){
    const focused=content.contains(doc.activeElement)?doc.activeElement.dataset.overviewFocus:null;
    const scrolls=[...content.querySelectorAll('.overview-table-scroll')].map(n=>n.scrollLeft);
    content.replaceChildren();if(!data.summary.runs&&!data.research?.runs?.length){content.append(el('div','showcase-empty','No published results yet.'));return;}
    if(data.summary.runs){
      const stats=el('div','overview-stats');stats.append(stat('Integration runs',data.summary.runs,`${fmt(data.summary.completed)} completed · ${fmt(data.summary.active)} active or queued`),stat('System profiles',data.summary.systems,'Including versioned integration profiles'),stat('Models',data.summary.models,'Across all published runs'),stat('Verified programs',data.validity.unique_programs,'Distinct valid programs, including seeds'));content.append(stats);
    }
    const research=researchResults();if(research)content.append(research);
    if(data.summary.runs){
      const grid=el('div','overview-grid-layout');grid.append(chart(),outcomes());content.append(taskResults(),grid,table());
      content.append(el('p','overview-note overview-scope',`Integration pilots · ${data.loaded} of ${data.total} accessible runs in this published snapshot.${data.truncated?' Older runs are outside this snapshot.':''} Scores are compared only within a shared evaluator contract.`));
    }
    if(focused){const target=[...content.querySelectorAll('[data-overview-focus]')].find(n=>n.dataset.overviewFocus===focused);target?.focus({preventScroll:true});}
    [...content.querySelectorAll('.overview-table-scroll')].forEach((n,i)=>{n.scrollLeft=scrolls[i]||0;});
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
      status.textContent=`Published snapshot · ${time.toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZoneName:'short'})}`;root.dataset.state=data.summary.runs||data.research?.runs?.length?'ready':'empty';
    }catch{if(current!==epoch||destroyed||!enabled)return;root.dataset.state='error';status.textContent=data?'Update unavailable · showing the last published snapshot.':'Results overview is temporarily unavailable.';if(!data){content.replaceChildren(el('p','showcase-empty','The snapshot could not be loaded. Retry to reconnect.'));}retry.textContent='Retry';}
    finally{win.clearTimeout(timeoutId);if(current===epoch){pending=null;retry.disabled=false;root.setAttribute('aria-busy','false');}}
  }
  function sync(event){const next=event?!event.detail.connected:enabled;enabled=next;root.hidden=!enabled;if(enabled)refresh();else{epoch++;pending?.abort();pending=null;root.setAttribute('aria-busy','false');}}
  doc.addEventListener('arena:results-access',sync);sync();const timer=pollMs?win.setInterval(()=>{if(!doc.hidden)refresh();},pollMs):null;
  return {refresh,destroy(){destroyed=true;epoch++;pending?.abort();if(timer)win.clearInterval(timer);doc.removeEventListener('arena:results-access',sync);}};
}
if(typeof document!=='undefined'&&document.body?.dataset.resultsShowcase==='true')initResultsOverview();
