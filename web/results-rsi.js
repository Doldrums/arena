// Describe observed changes to the research machinery, separately from scores.
const counters = ['cells_created','cell_revisions','tools_registered','tools_executed','tool_executions','shared_observation_deliveries'];
const validCount = value => Number.isSafeInteger(value) && value >= 0;
const valid = record => record?.schema === 'sciel-self-improvement/1' && record.scope === 'recorded_run' &&
  ['complete','partial','not_recorded'].includes(record.coverage) &&
  counters.every(key => record.coverage==='not_recorded' ? record[key]===null : record[key] === null || validCount(record[key]));
const sum = (rows,key) => {
  const known = rows.filter(row => valid(row.self_improvement) && validCount(row.self_improvement[key]));
  return {value:known.length ? known.reduce((total,row)=>total+row.self_improvement[key],0) : null,runs:known.length};
};

export function researchRsiSummary(rows) {
  const records=Array.isArray(rows)?rows:[];
  const known=records.filter(row=>valid(row.self_improvement)&&row.self_improvement.coverage!=='not_recorded');
  const models=new Map();
  for(const row of records){const name=row.models?.join(' + ')||'Model not recorded';if(!models.has(name))models.set(name,[]);models.get(name).push(row);}
  return {runs:records.length,covered:known.length,complete:known.filter(row=>row.self_improvement.coverage==='complete').length,
    partial:known.filter(row=>row.self_improvement.coverage==='partial').length,
    counts:Object.fromEntries(counters.map(key=>[key,sum(records,key)])),
    models:[...models].sort(([a],[b])=>a.localeCompare(b)).map(([model,items])=>({model,runs:items.length,counts:Object.fromEntries(counters.map(key=>[key,sum(items,key)]))})),
  };
}

export function researchRsiPanel(doc,rows) {
  const summary=researchRsiSummary(rows);
  if(!summary.covered)return null;
  const el=(tag,className,text)=>{const node=doc.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;};
  const number=value=>value===null?'Not recorded':value.toLocaleString('en-US');
  const panel=el('section','showcase-card overview-rsi');panel.setAttribute('aria-label','Recorded self-improvement activity');
  const header=el('header');header.append(el('p','overview-note','SCiEL · Research process'),el('h2','','What the system builds during research'));
  header.append(el('p','overview-note',`Across all ${summary.runs} recorded runs and all models. These counts track changes to the research machinery, separately from task scores.`));panel.append(header);
  const stats=el('div','overview-rsi-stats');
  const authored=summary.counts.tools_registered,used=summary.counts.tools_executed;
  const usageNote=authored.value>0&&used.runs===summary.runs&&authored.runs===summary.runs
    ?`${(used.value/authored.value*100).toFixed(1)}% of the ${number(authored.value)} authored versions have recorded use`
    :'Distinct versions with recorded executions in each run';
  for(const [key,label,note] of [
    ['cells_created','Research cells created','New cells recorded during a run; initial built-ins excluded'],
    ['tools_registered','Tool versions authored','Registered source versions from those research cells'],
    ['tools_executed','Authored tool versions used',usageNote],
    ['cell_revisions','Research cell revisions','Recorded changes to cell definitions'],
  ]){
    const card=el('div');card.dataset.rsiMetric=key;
    card.append(el('span','',label),el('strong','',number(summary.counts[key].value)),el('small','',note));stats.append(card);
  }
  panel.append(stats);
  const flow=el('div','overview-rsi-flow');
  for(const [key,title,note] of [
    ['tool_executions','Recorded tool executions','Invocations with receipt references; these count use, not just tool definitions.'],
    ['shared_observation_deliveries','Research observations delivered','Recorded delivery into a research prompt, beyond making an observation available.'],
  ]){
    const item=el('div');item.dataset.rsiMetric=key;item.append(el('strong','',number(summary.counts[key].value)),el('h3','',title),el('p','overview-note',note));flow.append(item);
  }
  const evidence=el('div');evidence.append(el('h3','','Inspect the research process'),el('p','overview-note','Follow cell definitions, tools and their recorded use in the experiment board.'));
  const link=el('a','','Open experiments ↗');link.href='/experiments';evidence.append(link);flow.append(evidence);panel.append(flow);
  const details=el('details','overview-rsi-details');details.append(el('summary','',`Coverage & model breakdown · ${summary.covered} / ${summary.runs} runs`));
  details.append(el('p','overview-note',`${summary.complete} complete retained histories; ${summary.partial} partial histories; ${summary.runs-summary.covered} without recorded coverage. Counts describe observed events and can be lower bounds where history is partial. Missing measurements are not zero.`));
  details.append(el('p','overview-note','Counts are summed within runs, not globally unique inventions. A tool version reused in another run is counted in that run as well. Built-in tools are excluded. Recorded receipt references establish observed use; artifact bodies are not independently reverified by this aggregate.'));
  details.append(el('p','overview-note','Created cells and tools show how the research process changes. They do not by themselves prove that a change caused a score improvement, or that the system achieved recursive capability gains. Task results and call-budget comparisons are evaluated separately.'));
  const wrap=el('div','overview-rsi-table-scroll');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Self-improvement activity by recorded model');
  const table=el('table','overview-table'),head=el('thead'),tr=el('tr');
  for(const name of ['Model','Runs','Cells created','Tool versions authored','Versions used','Cell revisions']){const th=el('th','',name);th.scope='col';tr.append(th);}head.append(tr);table.append(head);
  const body=el('tbody');for(const group of summary.models){const row=el('tr'),identity=el('th','',group.model);identity.scope='row';row.append(identity,el('td','',number(group.runs)));for(const key of ['cells_created','tools_registered','tools_executed','cell_revisions'])row.append(el('td','',number(group.counts[key].value)));body.append(row);}table.append(body);wrap.append(table);details.append(wrap);panel.append(details);
  return panel;
}
