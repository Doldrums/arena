const text=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=value=>typeof value==='number'&&Number.isFinite(value);
const number=value=>finite(value)?value.toLocaleString('en-US'):'Unknown';
const dollars=(value,partial=false)=>finite(value)?(partial?'≥ ':'')+'$'+value.toFixed(4):'Unknown USD';
const duration=value=>finite(value)?(value<60?Math.round(value)+'s':value<3600?Math.floor(value/60)+'m '+Math.round(value%60)+'s':(value/3600).toFixed(1)+'h'):'Unknown';
const link=(url,label)=>{try{const parsed=new URL(url);if(['http:','https:'].includes(parsed.protocol))return '<a href="'+text(parsed.href)+'" target="_blank" rel="noopener noreferrer">'+text(label||'Effort source')+' ↗</a>';}catch{}return text(label||'Effort source unavailable');};
const modelsHTML=(models,count)=>{
  const names=(models||[]).map(model=>typeof model==='string'?model:typeof model?.name==='string'?model.name+(model.role?' ('+model.role+')':''):null).filter(Boolean);
  return '<details class="effort-models"><summary>'+text(number(count))+' LLM '+(count===1?'identity':'identities')+'</summary><span>'+text(names.length?names.join(' · '):'Model identities not reported')+'</span></details>';
};

export function effortDetailsHTML(scope){
  if(!scope)return '<span class="effort-unknown">Effort unknown · no bound physical history</span>';
  const partial=scope.history_complete!==true||scope.pending_llm_calls>0||scope.unknown_cost_calls>0;
  const subscription=scope.unpriced_llm_calls>0||scope.billing_mode==='subscription_unpriced'||scope.cost_status==='subscription_unpriced';
  const price=subscription?(scope.reported_usd>0?dollars(scope.reported_usd,true)+' known + subscription · USD unavailable':'Subscription · USD unavailable'):dollars(scope.reported_usd,partial);
  return '<div class="effort-facts"><span>'+text(price)+' <small>LLM charges'+(scope.cost_status==='partial_or_estimated'?' · partial / estimated':'')+'</small></span>'+
    '<span>'+text(number(scope.evaluator_cascades))+' program evaluations · '+text(number(scope.physical_llm_calls))+' completed LLM calls</span>'+
    '<span>'+(finite(scope.target_iteration)?'Best reached at evolution iteration '+text(number(scope.target_iteration)):text(number(scope.ordinary_iterations))+' completed evolution iterations')+'</span>'+
    '<span>'+text(duration(scope.wall_seconds))+' elapsed (incl. pauses) · CPU time unknown</span>'+
    (scope.pending_llm_calls||scope.unknown_cost_calls?'<span class="effort-uncertain">'+text(number(scope.pending_llm_calls))+' calls pending · '+text(number(scope.unknown_cost_calls))+' charges unknown</span>':'')+
    (scope.history_complete!==true?'<span class="effort-uncertain">Incomplete receipt history · observed lower bounds</span>':'')+
    (scope.unpriced_llm_calls>0?'<span>'+text(number(scope.unpriced_llm_calls))+' completed subscription calls · no USD price supplied</span>':'')+
    (finite(scope.prompt_tokens)||finite(scope.completion_tokens)?'<span>'+text(number(scope.prompt_tokens))+' input tokens · '+text(number(scope.completion_tokens))+' output tokens'+(scope.token_usage_complete?'':' · recorded subtotal')+'</span>':'')+
    modelsHTML(scope.models,scope.model_count)+'</div>';
}

export function publishedEffortHTML(effort){
  if(!effort||effort.status==='unknown')return '<span class="effort-unknown">Steps, USD, calls and models unknown</span>';
  const steps=effort.steps;
  return '<div class="effort-facts"><span>'+text(steps&&finite(steps.value)?number(steps.value)+' '+steps.unit:'Steps unknown')+'</span>'+
    (steps?.scope?'<small>'+text(steps.scope)+'</small>':'')+
    '<span>'+text(dollars(effort.usd))+' · '+text(number(effort.llm_calls))+' LLM calls</span>'+
    '<span>'+text(duration(effort.wall_seconds))+' elapsed · '+text(duration(effort.cpu_seconds))+' CPU</span>'+
    modelsHTML(effort.models,effort.model_count)+
    '<details class="effort-scope"><summary>Reported scope</summary><span>'+text(effort.note||'Discovery effort to first attainment is not established.')+'</span>'+
    (effort.generated_programs?'<span>'+text(number(effort.generated_programs.value))+' '+text(effort.generated_programs.unit||'generated samples')+' · '+text(effort.generated_programs.scope||effort.generated_programs.status||'')+'</span><span>'+text(effort.generated_programs.derivation||'')+'</span>':'')+
    ((effort.auxiliary_models||[]).length?'<span>Auxiliary: '+text(effort.auxiliary_models.map(m=>typeof m==='string'?m:m.name+(m.role?' ('+m.role+')':'')).join(' · '))+'</span>':'')+
    (effort.source_url?'<span>'+link(effort.source_url,'Effort source')+(effort.locator?' · '+text(effort.locator):'')+'</span>':'')+'</details></div>';
}

export function renderEffort(effort){
  return '<div class="effort-scopes" aria-label="Run effort comparison"><section><div class="effort-title">To current best'+(effort?.best_program_id?' · '+text(effort.best_program_id):'')+'</div>'+effortDetailsHTML(effort?.to_best)+
    (effort?.to_best?.cutoff_at?'<time datetime="'+text(effort.to_best.cutoff_at)+'">Evaluation completed '+text(effort.to_best.cutoff_at.replace('T',' ').replace('+00:00',' UTC'))+'</time>':'')+'</section>'+
    '<section><div class="effort-title">Total run · now</div>'+effortDetailsHTML(effort?.total)+
    (effort?.observed_at?'<time datetime="'+text(effort.observed_at)+'">Receipt snapshot '+text(effort.observed_at.replace('T',' ').replace('+00:00',' UTC'))+'</time>':'')+'</section></div>'+
    '<p class="effort-note">'+text(effort?.note||'Discovery effort is not recorded. A candidate’s generation charge is not the total cost of finding its result.')+'</p>';
}
