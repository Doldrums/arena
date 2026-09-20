// Passive views of recorded decisions. This module never reconstructs a policy.
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite = value => typeof value === 'number' && Number.isFinite(value);
const number = value => !finite(value)?'—':value!==0&&(Math.abs(value)<.001||Math.abs(value)>10000)?value.toExponential(3):value.toFixed(3);
const probability = value => finite(value)?(value*100).toFixed(2)+'%':'—';
const statusNames = {online:'Online adaptation',static:'Rule-based / static',frozen:'Frozen inference',disabled:'Disabled',unknown:'Not recorded'};
const empty = text => '<div class="learning-empty">'+esc(text)+'</div>';
const pathLabel = row => [row.forced?'Forced':'',row.escalated?'Escalated':'',row.refine?'Refine bias':'',row.credited===true?'Credited update':''].filter(Boolean).join(' · ')||(row.forced===false&&row.escalated===false?'Bandit choice':'Not recorded');

function lineChart(rows, series, title, {probabilities=false,xLabel='Search iteration'}={}) {
  rows=(rows||[]).slice(-300);
  series=series.slice(0,8);
  let xMin=Infinity,xMax=-Infinity,yMax=probabilities?1:0,observations=0;
  for(const row of rows){
    if(!finite(row.iteration))continue;
    for(const item of series){const value=item.value(row);if(!finite(value))continue;observations++;xMin=Math.min(xMin,row.iteration);xMax=Math.max(xMax,row.iteration);yMax=Math.max(yMax,value);}
  }
  if(!observations)return empty('No recorded values for this chart yet.');
  if(yMax<=0)yMax=1;
  const x=value=>48+(value-xMin)/(xMax-xMin||1)*534;
  const y=value=>156-value/(yMax||1)*137;
  let svg='<svg class="learning-chart" viewBox="0 0 610 190" role="img" aria-label="'+esc(title)+'"><title>'+esc(title)+'</title>';
  for(let i=0;i<=2;i++){
    const value=yMax*i/2,yy=y(value);
    svg+='<line class="learning-grid" x1="48" y1="'+yy+'" x2="582" y2="'+yy+'"/><text x="41" y="'+(yy+3)+'" text-anchor="end">'+esc(probabilities?probability(value):number(value))+'</text>';
  }
  series.forEach((item,index)=>{
    let path='',connected=false;
    for(const row of rows){
      const value=item.value(row);
      if(!finite(row.iteration)||!finite(value)){connected=false;continue;}
      const xx=x(row.iteration),yy=y(value);
      path+=(connected?'L':'M')+xx.toFixed(2)+','+yy.toFixed(2)+' ';
      connected=true;
      svg+='<circle class="learning-dot learning-color-'+index+'" cx="'+xx+'" cy="'+yy+'" r="2"><title>'+esc(item.label)+' · '+esc(xLabel)+' '+esc(row.iteration)+' · '+esc(probabilities?probability(value):number(value))+'</title></circle>';
    }
    svg+='<path class="learning-line learning-color-'+index+'" d="'+path+'"/>';
  });
  svg+='<text x="48" y="176">'+esc(xMin)+'</text><text x="582" y="176" text-anchor="end">'+esc(xMax)+'</text><text x="315" y="185" text-anchor="middle">'+esc(xLabel)+'</text></svg>';
  return '<div class="learning-legend">'+series.map((item,index)=>'<span><i class="learning-color-'+index+'"></i>'+esc(item.label)+'</span>').join('')+'</div>'+svg;
}

function table(headers,rows,className='') {
  return '<div class="table-wrap '+className+'"><table><thead><tr>'+headers.map(label=>'<th>'+esc(label)+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
}

export function learningHTML(view) {
  if(!view)return empty('Bandit and RL telemetry is not recorded for this run.');
  const summary=view.summary||{},operator=view.operator||{},controller=view.controller||{};
  const arms=(operator.arms||[]).slice(0,24),operatorHistory=(operator.history||[]).slice(-300),modeHistory=(controller.history||[]).slice(-120).map(row=>({...row,iteration:row.iteration_before??row.iteration}));
  let html='<div class="learning"><div class="learning-heading"><h2>Bandits & RL</h2><p>What adapts during this run, and what the recorded rewards actually update.</p></div>';
  html+='<div class="learning-components">'+(view.components||[]).slice(0,12).map(component=>'<article class="learning-component" data-component="'+esc(component.id)+'"><span class="badge '+(component.status==='online'?'success':component.status==='frozen'?'blue':'neutral')+'">'+esc(statusNames[component.status]||'Not recorded')+'</span><h3>'+esc(component.label)+'</h3><p>'+esc(component.detail)+'</p></article>').join('')+'</div>';
  html+='<div class="learning-metrics"><div>Completed search iterations<strong>'+esc(summary.iterations??'—')+'</strong></div><div>Population record events<strong>'+esc(summary.record_events??'—')+'</strong></div><div>Credited operator updates<strong>'+esc(summary.credited_operator_updates??'—')+'</strong></div><div>Recorded normalized reward<strong>'+number(summary.cumulative_reward)+'</strong></div></div>';
  const rewardSeries=[{label:'Per-iteration reward',value:row=>row.reward},{label:'Cumulative reward',value:row=>row.cumulative_reward}];
  html+='<div class="learning-plots"><article class="learning-panel"><h3>Search rewards</h3><p>Recorded normalized improvement reward. This is a search signal, not an RL training loss or the task score.</p><p>'+esc(view.reward_normalization?.detail||'Normalization policy not recorded.')+'</p>'+lineChart(view.rewards,rewardSeries,'Recorded search rewards');
  if(view.reward_normalization?.recorded_events)html+='<p>'+esc(view.reward_normalization.recorded_events)+' events with normalization evidence · '+esc(view.reward_normalization.precision_filtered_channels)+' positive gain channels filtered by precision · '+esc(view.reward_normalization.capped_events)+' rewards capped.</p>';
  html+='</article>';
  const modes=[...new Set(modeHistory.flatMap(row=>Object.keys(row.distribution||{})))].slice(0,8);
  html+='<article class="learning-panel"><h3>Controller mode probabilities</h3><p>Recorded mode distributions, including plateau overrides. Source: '+esc(controller.source||'not recorded')+'.</p>'+lineChart(modeHistory,modes.map(mode=>({label:mode,value:row=>row.distribution?.[mode]})),'Recorded controller mode probabilities',{probabilities:true,xLabel:'Recorded pre-step iteration'})+'</article>';
  const values=[...new Set(operatorHistory.flatMap(row=>Object.keys(row.stats||{})))].slice(0,8);
  html+='<article class="learning-panel"><h3>Operator value estimates</h3><p>Window maximum of credited improvement rewards, recorded before each choice. Refine boosts are excluded from these values.</p>'+lineChart(operatorHistory,values.map(name=>({label:name,value:row=>row.stats?.[name]})),'Recorded operator value estimates')+'</article>';
  html+='<article class="learning-panel"><h3>Chosen operator probability</h3><p>Probability of the sampled operator. Escalation may execute a different operator; forced choices can have probability 1.</p>'+lineChart(operatorHistory,[{label:'Chosen probability',value:row=>row.selected_probability}],'Probability of the chosen operator',{probabilities:true})+'</article></div>';
  html+='<section class="learning-section"><h3>Operator outcomes & credit</h3><p>Sampled choices and executed operators differ after escalation. Evaluations include failed evaluations. Credited updates count only eligible island improvements; reward totals describe observed outcomes.</p>';
  html+=arms.length?table(['Operator','Sampled','Executed','Evaluated','Population records','Credited updates','Observed reward'],arms.map(arm=>'<tr><td class="mono">'+esc(arm.name)+'</td><td class="number">'+esc(arm.choices??'—')+'</td><td class="number">'+esc(arm.executions??'—')+'</td><td class="number">'+esc(arm.evaluated_count??'—')+'</td><td class="number">'+esc(arm.record_count??'—')+'</td><td class="number">'+esc(arm.credited_updates??'—')+'</td><td class="number">'+number(arm.cumulative_reward)+'</td></tr>'),'learning-arm-table'):empty('No operator outcomes recorded yet.');
  html+='</section>';
  const checkpoint=operator.checkpoint;
  html+='<section class="learning-section"><h3>Saved bandit state</h3>';
  if(checkpoint&&checkpoint.available!==false){
    html+='<p>Checkpoint at iteration '+esc(checkpoint.iteration??'—')+(checkpoint.stale?' · earlier than the live journal':'')+'. Window capacity '+esc(checkpoint.window??'—')+' per arm; temperature '+number(checkpoint.temperature)+', probability floor '+probability(checkpoint.floor)+'. Window occupancy is not the lifetime update count.</p>';
    html+=table(['Operator arm','Rewards in saved window','Window maximum'],(checkpoint.arms||[]).slice(0,24).map(arm=>'<tr><td class="mono">'+esc(arm.name)+'</td><td class="number">'+esc(arm.window_count??'—')+'</td><td class="number">'+number(arm.window_max)+'</td></tr>'));
  }else html+=empty('No saved operator bandit state yet.');
  const modeBandit=controller.mode_bandit;
  if(modeBandit?.phase_arms?.length){
    html+='<h4>Mode-bandit reward windows</h4><p>Checkpoint iteration '+esc(modeBandit.iteration??'—')+(modeBandit.stale?' · earlier snapshot':'')+'. Mean reward includes unsuccessful attempts credited as zero by the engine.</p>';
    html+=table(['Phase','Mode','Window samples','Mean normalized reward'],modeBandit.phase_arms.slice(0,96).map(arm=>'<tr><td>'+esc(arm.phase)+'</td><td>'+esc(arm.mode)+'</td><td class="number">'+esc(arm.count)+'</td><td class="number">'+number(arm.mean_reward)+'</td></tr>'));
  }
  const presetState=controller.preset_weights;
  if(presetState?.available){
    html+='<div class="learning-preset-state"><h4>Saved preset weights</h4><p>Checkpoint iteration '+esc(presetState.iteration??'—')+(presetState.stale?' · earlier than the live journal':'')+'. Recorded updates: '+esc(presetState.updates??'—')+'. Learning rate '+number(presetState.learning_rate)+', exploration '+probability(presetState.exploration)+', importance-reward cap '+number(presetState.max_importance_reward)+'.</p>';
    html+=table(['Preset','Saved log weight'],Object.entries(presetState.log_weights||{}).slice(0,24).map(([name,value])=>'<tr><td>'+esc(name)+'</td><td class="number">'+number(value)+'</td></tr>'));
    html+='<p>Log weights are saved state, not probabilities. The chart shows observed selection probabilities; binary rewards and subsequent updates are not reconstructed.</p></div>';
  }else if(controller.source==='preset weights')html+=empty('No saved preset weights yet; observed preset decisions are shown in the chart.');
  html+='</section><section class="learning-section"><h3>Recent decisions</h3><p>Latest recorded search decisions. Sampled and executed operators are shown separately; probabilities belong to the sampled choice.</p>';
  html+=operatorHistory.length?table(['Iteration','Island','Sampled → executed','Chosen probability','Normalized reward','Path'],operatorHistory.slice(-30).reverse().map(row=>'<tr><td>'+esc(row.iteration??'—')+'</td><td>'+esc(row.island??'—')+'</td><td class="mono">'+esc(row.selected_operator||'?')+' → '+esc(row.operator||'?')+'</td><td class="number">'+probability(row.selected_probability)+'</td><td class="number">'+number(row.reward)+'</td><td>'+esc(pathLabel(row))+'</td></tr>'),'learning-decisions'):empty('No completed search decisions recorded yet.');
  html+='</section><section class="learning-section"><h3>Controller decisions</h3><p>Recorded controller and preset-weight selections. A mode can be gated or overridden before execution. Missing effective modes remain unknown.</p>';
  html+=modeHistory.length?table(['Pre-step iteration','Source','Phase','Recorded mode','Effective mode','Recorded propensity','Plateau override'],modeHistory.slice(-20).reverse().map(row=>'<tr><td>'+esc(row.iteration??'—')+'</td><td>'+esc(row.source==='preset_weights'?'Preset weights':'Controller')+'</td><td>'+esc(row.phase??'—')+'</td><td>'+esc(row.mode||'—')+'</td><td class="number">'+esc(row.effective_mode||'Not recorded')+'</td><td class="number">'+probability(row.propensity)+'</td><td>'+esc(row.plateau===true?'Yes':row.plateau===false?'No':'Not recorded')+'</td></tr>'),'learning-controller-decisions'):empty('No controller decisions recorded.');
  html+='</section>';
  if(view.notes?.length)html+='<div class="architecture-notes">'+view.notes.map(note=>'<p>'+esc(note)+'</p>').join('')+'</div>';
  return html+'<p class="learning-footnote">Charts retain up to '+esc(view.history_limit||300)+' recent records; summary counts use the available recorded history. Missing observations are not synthesized.</p></div>';
}
