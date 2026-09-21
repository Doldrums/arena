import {researchSummary} from './results-research.js';
import {researchEfficiencyPanel} from './results-efficiency.js';
import {researchRsiPanel} from './results-rsi.js';

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
export function initResultsOverview({doc=document,fetcher=(...args)=>fetch(...args),storage=sessionStorage,pollMs=60000,requestTimeoutMs=20000,rootId='results-overview'}={}) {
  const root=doc.getElementById(rootId); if(!root) return {destroy(){}};
  const win=doc.defaultView; let data=null,pending=null,epoch=0,destroyed=false,expanded=false,selectedCohort='',axis='tokens',enabled=true,resultTask='',resultSystem='all',resultPage=0,researchGroup='',researchAll=false,researchPage=0,researchModel='all',researchBudget=300,integrationOpen=false;
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
  const modelLabel=value=>({'gpt-6-astra':'GPT-6 Astra','gpt-5.6-sol':'GPT-5.6 Sol','gpt-5.6-terra':'GPT-5.6 Terra','gpt-5.6-luna':'GPT-5.6 Luna','gpt-5.5':'GPT-5.5','anthropic/claude-opus-5':'Claude Opus 5','google/gemini-2.5-flash':'Gemini 2.5 Flash'})[value]||value;
  const researchModels=r=>r.models.length?r.models.map(modelLabel).join(' + '):'Model not recorded';
  const researchContract=r=>JSON.stringify([r.task_id,r.metric,r.direction,r.units,r.protocol]);
  const elapsed=value=>!numeric(value)?'Not recorded':value<60?`${fmt(value)} s`:value<3600?minutes(value):`${fmt(value/3600)} h`;
  function researchPlot(title,description,headingTag='h3'){
    const panel=el('section','overview-research-chart');panel.append(el(headingTag,'',title),el('p','overview-note',description));
    const svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 620 310');svg.setAttribute('role','group');svg.setAttribute('aria-label',title);svg.classList.add('overview-research-plot');
    const draw=(tag,attrs,text,parent=svg)=>{const n=doc.createElementNS(svg.namespaceURI,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;parent.append(n);return n;};
    const detail=el('p','overview-chart-detail','Select a point for its measurements.');detail.setAttribute('role','status');panel.append(svg,detail);
    const point=(attrs,row,extra='')=>{
      const text=`${researchModels(row)} · ${scoreNumber(row.best_score)} · ${elapsed(row.to_best_wall_seconds)} to this run’s best · ${row.state} · evaluator ${row.protocol.slice(0,8)}${extra}`;
      const n=draw('circle',{...attrs,tabindex:0,role:'button','aria-label':text,'data-research-protocol':row.protocol});draw('title',{},text,n);
      const show=()=>{detail.textContent=text;};n.addEventListener('click',show);n.addEventListener('focus',show);n.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();show();}});return n;
    };
    return {panel,svg,draw,point,detail};
  }
  function researchTimeChart(rows,summary,context){
    const plot=researchPlot('Quality & elapsed time','Selected evaluator and model filter. Each point is a run’s best result at its recorded elapsed time.');
    const {panel,svg,draw,point}=plot;
    const points=rows.filter(r=>r.measurement_status==='measured'&&numeric(r.best_score)&&numeric(r.to_best_wall_seconds)&&r.to_best_wall_seconds>=0);
    if(!points.length){svg.remove();plot.detail.textContent='Paired result and elapsed-time measurements have not been recorded.';return panel;}
    const values=points.map(r=>r.best_score),lo=Math.min(...values),hi=Math.max(...values),pad=(hi-lo)*.12||Math.max(Math.abs(hi)*.015,.001);
    const maxT=Math.max(researchBudget,...points.map(r=>r.to_best_wall_seconds))*1.08||1;
    const x=t=>77+Math.log1p(t/60)/Math.log1p(maxT/60)*508,y=v=>245-(v-lo+pad)/(hi-lo+2*pad)*204;
    draw('rect',{x:77,y:33,width:Math.max(0,x(researchBudget)-77),height:212,class:'overview-budget-region'});
    for(let i=0;i<5;i++){const value=lo-pad+(hi-lo+2*pad)*i/4;draw('line',{x1:77,x2:588,y1:y(value),y2:y(value),class:'overview-grid'});draw('text',{x:65,y:y(value)+4,'text-anchor':'end',class:'overview-axis'},fmt(value));}
    for(const t of [0,60,300,900,3600,14400,86400,345600])if(t<=maxT){draw('text',{x:x(t),y:270,'text-anchor':'middle',class:'overview-axis'},t?elapsed(t):'0');}
    draw('line',{x1:x(researchBudget),x2:x(researchBudget),y1:33,y2:245,class:'overview-budget-line'});
    draw('text',{x:77,y:19,class:'overview-axis'},`${metricName(context.metric)} · ${context.direction==='maximize'?'higher':'lower'} is better`);
    draw('text',{x:585,y:298,'text-anchor':'end',class:'overview-axis'},'Elapsed to best · logarithmic time axis');
    const frontier=[...summary.frontier].sort((a,b)=>a.to_best_wall_seconds-b.to_best_wall_seconds);
    if(frontier.length>1)draw('polyline',{points:frontier.map(r=>`${x(r.to_best_wall_seconds)},${y(r.best_score)}`).join(' '),class:'overview-frontier-line'});
    points.forEach(r=>point({cx:x(r.to_best_wall_seconds),cy:y(r.best_score),r:summary.frontier.includes(r)?6:4.5,class:`overview-research-dot${summary.frontier.includes(r)?' on-frontier':''}`},r));
    panel.append(el('p','overview-note',`${points.length} / ${rows.length} runs have paired values. Amber connects the observed frontier. Elapsed time includes pauses; each point is the time of that run’s final recorded best.`));return panel;
  }
  function researchModelFacet(rows,selectedContract){
    const context=rows[0],summary=researchSummary(rows),selected=researchContract(context)===selectedContract;
    const plot=researchPlot(`Evaluator ${context.protocol.slice(0,8)}${selected?' · selected':''}`,`${metricName(context.metric)} · ${context.direction==='maximize'?'higher':'lower'} is better · ${context.units.replace(/_/g,' ')} · ${rows.length} recorded runs`, 'h4');
    const {panel,svg,draw,point}=plot,groups=summary.groups;
    panel.className='overview-model-facet';panel.dataset.researchContract=researchContract(context);panel.dataset.researchProtocol=context.protocol;
    const measuredRows=rows.filter(r=>r.measurement_status==='measured'&&numeric(r.best_score));
    if(!measuredRows.length){svg.remove();plot.detail.textContent=`${groups.map(g=>researchModels(g.rows[0])).join(' · ')}: measurements have not been recorded.`;return panel;}
    const values=measuredRows.map(r=>r.best_score),lo=Math.min(...values),hi=Math.max(...values),pad=(hi-lo)*.07||Math.max(Math.abs(hi)*.01,.001);
    const height=Math.max(190,groups.length*48+90);svg.setAttribute('viewBox',`0 0 620 ${height}`);
    const x=v=>167+(v-lo+pad)/(hi-lo+2*pad)*407,top=45,bottom=height-51,gap=(bottom-top)/Math.max(groups.length,1);
    for(let i=0;i<4;i++){const value=lo-pad+(hi-lo+2*pad)*i/3;draw('line',{x1:x(value),x2:x(value),y1:top-15,y2:bottom,class:'overview-grid'});draw('text',{x:x(value),y:height-25,'text-anchor':'middle',class:'overview-axis'},fmt(value));}
    draw('text',{x:167,y:18,class:'overview-axis'},metricName(context.metric));
    groups.forEach((g,i)=>{
      const y=top+gap*i+gap/2,label=g.rows[0]?researchModels(g.rows[0]):g.model;
      draw('text',{x:153,y:y+4,'text-anchor':'end',class:'overview-model-label'},label.length>23?label.slice(0,21)+'…':label);
      const measured=g.rows.filter(r=>r.measurement_status==='measured'&&numeric(r.best_score));
      measured.forEach((r,j)=>point({cx:x(r.best_score),cy:y+((j%5)-2)*3,r:3.8,class:'overview-research-dot overview-model-dot'},r));
      if(!measured.length)draw('text',{x:167,y:y+4,class:'overview-axis'},'No measured result');
      if(numeric(g.median))draw('line',{x1:x(g.median),x2:x(g.median),y1:y-13,y2:y+13,class:'overview-median-mark'});
      if(g.best)point({cx:x(g.best.best_score),cy:y,r:6,class:'overview-research-dot on-frontier'},g.best,` · best of ${g.rows.length} recorded runs`);
    });
    return panel;
  }
  function researchModelChart(taskRows,context){
    const panel=el('section','overview-research-chart overview-model-comparison'),groups=new Map();
    for(const row of taskRows){const key=researchContract(row);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
    const models=new Set(taskRows.map(r=>r.models.join(' + ')).filter(Boolean));
    panel.dataset.evaluatorGroups=String(groups.size);
    panel.append(el('h3','','Results across models'),el('p','overview-note',`${models.size} model configurations across ${groups.size} evaluator groups for ${context.task_name}. Every measured outcome for this task is included, regardless of the model filter above.`));
    const selected=researchContract(context),ordered=[...groups].sort(([a],[b])=>Number(b===selected)-Number(a===selected)||a.localeCompare(b));
    for(const [,rows] of ordered)panel.append(researchModelFacet(rows,selected));
    panel.append(el('p','overview-note overview-model-scope','Each evaluator group has its own score axis. Amber: best recorded; black mark: median within that model and evaluator. Groups are not pooled or ranked against each other. Recorded runs are observations, not estimates from independent repeated trials.'));return panel;
  }
  function researchResults(){
    const research=data.research;if(!research?.runs?.length)return null;
    const [panel,head]=card('SCiEL · Research results');panel.classList.add('overview-table-card','overview-research-results');
    head.append(el('span','overview-note',`${research.measured} measured / ${research.total} recorded runs`));
    const groups=new Map();
    for(const r of research.runs){const key=researchContract(r);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r);}
    if(!groups.has(researchGroup))researchGroup=[...groups].sort((a,b)=>a[1][0].task_name.localeCompare(b[1][0].task_name)||new Set(b[1].flatMap(r=>r.models)).size-new Set(a[1].flatMap(r=>r.models)).size)[0][0];
    const controls=el('div','overview-result-controls');const label=el('label','overview-select','Task / evaluator'),select=el('select');select.dataset.overviewFocus='research-task';
    for(const [key,rows] of groups){const r=rows[0],o=el('option','',`${r.task_name} · ${r.protocol.slice(0,6)} · ${rows.length} runs`);o.value=key;select.append(o);}select.value=researchGroup;
    select.addEventListener('change',()=>{researchGroup=select.value;researchModel='all';researchPage=0;render();});label.append(select);controls.append(label);
    const groupMembers=groups.get(researchGroup),modelKey=r=>r.models.join(' + ')||'Model not recorded';
    const modelControl=el('label','overview-select','Model in selected evaluator'),modelSelect=el('select');modelSelect.dataset.overviewFocus='research-model';
    const modelOptions=[...new Set(groupMembers.map(modelKey))].sort();if(researchModel!=='all'&&!modelOptions.includes(researchModel))researchModel='all';
    for(const key of ['all',...modelOptions]){const option=el('option','',key==='all'?'All models':researchModels(groupMembers.find(r=>modelKey(r)===key)));option.value=key;modelSelect.append(option);}modelSelect.value=researchModel;modelSelect.addEventListener('change',()=>{researchModel=modelSelect.value;researchPage=0;render();});modelControl.append(modelSelect);controls.append(modelControl);
    const budgetControl=el('label','overview-select','Elapsed checkpoint'),budgetSelect=el('select');budgetSelect.dataset.overviewFocus='research-budget';
    for(const [seconds,text] of [[300,'5 min'],[900,'15 min'],[3600,'1 hour']]){const option=el('option','',text);option.value=String(seconds);budgetSelect.append(option);}budgetSelect.value=String(researchBudget);budgetSelect.addEventListener('change',()=>{researchBudget=Number(budgetSelect.value);render();});budgetControl.append(budgetSelect);controls.append(budgetControl);
    const modeLabel=el('label','overview-select','Show'),mode=el('select');mode.dataset.overviewFocus='research-mode';
    for(const [value,text] of [['best','Best recorded per model'],['all','Every recorded run']]){const o=el('option','',text);o.value=value;mode.append(o);}mode.value=researchAll?'all':'best';mode.addEventListener('change',()=>{researchAll=mode.value==='all';researchPage=0;render();});modeLabel.append(mode);controls.append(modeLabel);panel.append(controls);
    const members=groupMembers.filter(r=>researchModel==='all'||modelKey(r)===researchModel),context=members[0],sign=context.direction==='minimize'?-1:1;
    const taskRows=research.runs.filter(r=>r.task_id===context.task_id);
    const models=r=>r.models.length?r.models.join(' + '):'Model not recorded';
    const buckets=new Map();for(const r of members){const key=models(r);if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(r);}
    const compare=(a,b)=>numeric(a.best_score)&&numeric(b.best_score)?sign*(b.best_score-a.best_score):numeric(a.best_score)?-1:numeric(b.best_score)?1:0;
    const summary=researchSummary(members,{budgetSeconds:researchBudget});
    const representatives=summary.groups.map(g=>g.best||g.rows[0]);
    const rows=(researchAll?[...members]:representatives).sort((a,b)=>models(a).localeCompare(models(b))||compare(a,b));
    const best=summary.best,budgetBest=summary.bestWithinBudget;
    const headline=el('div','overview-research-highlight');headline.append(el('p','overview-note',`${metricName(context.metric)} · ${context.direction==='maximize'?'higher':'lower'} is better · ${context.units.replace(/_/g,' ')}. Metrics, elapsed-time chart and table use evaluator ${context.protocol.slice(0,8)} and the selected model filter: ${members.length} recorded runs. Paused and stopped runs retain their measurements.`));panel.append(headline);
    const metrics=el('div','overview-research-metrics');
    const metric=(key,label,value,note)=>{const item=el('article','overview-research-metric');item.dataset.researchMetric=key;item.append(el('span','',label),el('strong','',value),el('small','',note));metrics.append(item);};
    metric('best','Best recorded',scoreNumber(best?.best_score),best?`${elapsed(best.to_best_wall_seconds)} to best · selected evaluator`:'Measurement not recorded');
    metric('budget',`Recorded within ${elapsed(researchBudget)}`,scoreNumber(budgetBest?.best_score),budgetBest?`${elapsed(budgetBest.to_best_wall_seconds)} to final recorded best · selected evaluator`:'No timed best result within this checkpoint');
    metric('improved','Runs improving the initial solution',`${summary.improved} / ${summary.paired}`,`${summary.paired} paired initial/best measurements · ${summary.recorded} recorded runs`);
    const improvingModels=summary.groups.filter(g=>g.improved>0&&g.rows.some(r=>r.models.length)).length;
    metric('models','Models with recorded improvement',`${improvingModels} / ${summary.modelCount}`,'At least one improved outcome per model configuration');
    panel.append(metrics);
    const efficiency=researchEfficiencyPanel(doc,taskRows),charts=el('div',`overview-research-charts${efficiency?' has-efficiency':''}`);
    charts.append(researchTimeChart(members,summary,context));if(efficiency)charts.append(efficiency);
    charts.append(researchModelChart(taskRows,context));panel.append(charts);
    const evidenceHead=el('div','overview-research-evidence-heading');evidenceHead.append(el('h3','','Recorded outcomes'),el('p','overview-note',researchAll?'Every run in the selected group.':'Best outcome per model. Initial score and elapsed time belong to that same run.'));panel.append(evidenceHead);
    const wrap=el('div','overview-table-scroll');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','SCiEL recorded research outcomes');const table=el('table','overview-table overview-research-table'),thead=el('thead'),tr=el('tr');
    for(const text of ['Model','Initial','Best recorded','Change','Elapsed to best','Total recorded tokens','Run status']){const th=el('th','',text);th.scope='col';tr.append(th);}thead.append(tr);table.append(thead);const body=el('tbody');researchPage=Math.min(researchPage,Math.max(0,Math.ceil(rows.length/8)-1));
    for(const r of rows.slice(researchPage*8,researchPage*8+8)){
      const row=el('tr','overview-research-row'),identity=el('th','',models(r));identity.scope='row';if(!researchAll)identity.append(el('small','',`Selected from ${buckets.get(models(r)).length} recorded runs`));row.append(identity,el('td','',scoreNumber(r.seed_score)));
      const result=el('td','overview-result-value');result.append(el('strong','',scoreNumber(r.best_score)));row.append(result);
      const delta=numeric(r.seed_score)&&numeric(r.best_score)?r.best_score-r.seed_score:null;
      row.append(el('td',delta!==null&&delta*sign>0?'overview-result-gain':'',delta===null?'Not paired':delta===0?'Unchanged':`${delta>0?'+':''}${fmt(delta)}`),el('td','',numeric(r.to_best_wall_seconds)?minutes(r.to_best_wall_seconds):'Not recorded'));
      const tokens=el('td','',numeric(r.tokens)?compact(r.tokens):'Not fully recorded');if(r.usage?.billing_mode==='subscription_unpriced')tokens.append(el('small','','Subscription · USD not supplied'));tokens.append(el('small','','Total run receipts, not tokens to best'));row.append(tokens,el('td','',r.state));body.append(row);
    }
    table.append(body);wrap.append(table);panel.append(wrap);
    const footer=el('footer','overview-table-footer');footer.append(el('span','overview-note',researchAll?`${researchPage*8+1}–${Math.min((researchPage+1)*8,rows.length)} of ${rows.length} recorded runs`:'Best outcome per model within this evaluator group; initial values and elapsed time come from that same run.'));
    if(rows.length>8){const nav=el('div','overview-result-pages');for(const [text,step,key] of [['← Previous',-1,'research-prev'],['Next →',1,'research-next']]){const b=button(text,()=>{researchPage+=step;render();});b.dataset.overviewFocus=key;b.disabled=step<0?researchPage===0:(researchPage+1)*8>=rows.length;nav.append(b);}footer.append(nav);}panel.append(footer);
    const notes=el('details','overview-research-notes');notes.append(el('summary','','Measurement notes'));
    notes.append(el('p','overview-note','Elapsed time includes pauses. Checkpoints select final recorded bests reached within the chosen time; earlier outcomes from runs with a later best are not reconstructed. Total run tokens cover physical receipts across the whole run, separately from time to best. Task and metric versions stay in separate evaluator groups.'));
    if(numeric(research.source_generated_at))notes.append(el('p','overview-note','Research snapshot prepared '+new Date(research.source_generated_at*1000).toLocaleString('en-GB')+'. Imported runs are a recorded snapshot.'));
    panel.append(notes);
    return panel;
  }
  function render(){
    const focused=content.contains(doc.activeElement)?doc.activeElement.dataset.overviewFocus:null;
    const scrolls=[...content.querySelectorAll('.overview-table-scroll')].map(n=>n.scrollLeft);
    content.replaceChildren();if(!data.summary.runs&&!data.research?.runs?.length){content.append(el('div','showcase-empty','No published results yet.'));return;}
    const rsi=data.research?researchRsiPanel(doc,data.research.runs):null;if(rsi)content.append(rsi);
    const research=researchResults();if(research)content.append(research);
    if(data.summary.runs){
      const integration=el('details','overview-integrations');integration.open=integrationOpen||!research;integration.addEventListener('toggle',()=>{if(integration.isConnected)integrationOpen=integration.open;});
      const toggle=el('summary');toggle.append(el('span','','Framework integration results'),el('span','overview-note',`${data.summary.systems} system profiles · ${data.summary.runs} runs`));integration.append(toggle);
      const panels=el('div','overview-integration-content');
      const stats=el('div','overview-stats');stats.append(stat('Integration runs',data.summary.runs,`${fmt(data.summary.completed)} completed · ${fmt(data.summary.active)} active or queued`),stat('System profiles',data.summary.systems,'Including versioned integration profiles'),stat('Models',data.summary.models,'Across all published runs'),stat('Verified programs',data.validity.unique_programs,'Distinct valid programs, including seeds'));panels.append(stats);
      const grid=el('div','overview-grid-layout');grid.append(chart(),outcomes());panels.append(taskResults(),grid,table());
      panels.append(el('p','overview-note overview-scope',`Integration pilots · ${data.loaded} of ${data.total} accessible runs in this published snapshot.${data.truncated?' Older runs are outside this snapshot.':''} Scores are compared only within a shared evaluator contract. Source prepared ${new Date(data.source_generated_at*1000).toLocaleString('en-GB')}.`));integration.append(panels);content.append(integration);
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
      data=next;retry.textContent='Refresh';render();const time=new Date(data.generated_at*1000);
      status.textContent=`Published snapshot · ${time.toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZoneName:'short'})}`;root.dataset.state=data.summary.runs||data.research?.runs?.length?'ready':'empty';
    }catch{if(current!==epoch||destroyed||!enabled)return;root.dataset.state='error';status.textContent=data?'Update unavailable · showing the last published snapshot.':'Results overview is temporarily unavailable.';if(!data){content.replaceChildren(el('p','showcase-empty','The snapshot could not be loaded. Retry to reconnect.'));}retry.textContent='Retry';}
    finally{win.clearTimeout(timeoutId);if(current===epoch){pending=null;retry.disabled=false;root.setAttribute('aria-busy','false');}}
  }
  function sync(event){const next=event?!event.detail.connected:enabled;enabled=next;root.hidden=!enabled;if(enabled)refresh();else{epoch++;pending?.abort();pending=null;root.setAttribute('aria-busy','false');}}
  doc.addEventListener('arena:results-access',sync);sync();const timer=pollMs?win.setInterval(()=>{if(!doc.hidden)refresh();},pollMs):null;
  return {refresh,destroy(){destroyed=true;epoch++;pending?.abort();if(timer)win.clearInterval(timer);doc.removeEventListener('arena:results-access',sync);}};
}
if(typeof document!=='undefined'&&document.body?.dataset.resultsShowcase==='true')initResultsOverview();
