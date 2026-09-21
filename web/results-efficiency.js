// A selected native run beside a published reference, not a cross-system rank.
// Only the reviewed n=26, unit-square, sum-radii protocols at tau=1e-6 qualify.
const circleProtocols = new Set([
  '7258d873e87d181696cad7c12f67813f5e0b18e3ef2694a0113dee285d77ba87',
  '8969ddb87889e225e6afc4d7e7889032e6f0863b13f73d7465f84af8f60ee343',
]);
export const shinkaReference = Object.freeze({
  value: 2.635983099011548,
  url: 'https://arxiv.org/html/2509.19349v1#A2.SS1',
  label: 'ShinkaEvolve · Sakana AI · Appendix B.1',
  tolerance: 1e-6,
});
const finite = value => typeof value === 'number' && Number.isFinite(value);
const count = value => Number.isSafeInteger(value) && value >= 0;

/** Select the fewest complete recorded calls among near-reference endpoints.
 * Scope is explicitly this run; these are neither independent repeats nor a
 * budget-matched reproduction of the reference's full search campaign.
 */
export function researchEfficiency(rows) {
  const candidates = (Array.isArray(rows) ? rows : []).filter(row => {
    const effort = row.effort_to_best;
    const gap = shinkaReference.value - row.best_score;
    return row.task_id === 'oe/circle_packing' && row.metric === 'sum_radii' &&
      row.direction === 'maximize' && row.units === 'unit_square_side_length' &&
      circleProtocols.has(row.protocol) && row.measurement_status === 'measured' &&
      finite(row.best_score) && gap >= 0 && gap <= 1e-7 &&
      effort?.scope === 'current_run_through_best_evaluation' &&
      effort.history_complete === true && count(effort.physical_llm_calls) &&
      effort.physical_llm_calls > 0 && effort.dispatched_llm_calls === effort.physical_llm_calls &&
      effort.pending_llm_calls === 0 && finite(effort.elapsed_seconds) &&
      effort.elapsed_seconds >= 0 && effort.elapsed_seconds === row.to_best_wall_seconds;
  });
  candidates.sort((a,b) => a.effort_to_best.physical_llm_calls - b.effort_to_best.physical_llm_calls ||
    b.best_score - a.best_score || a.to_best_wall_seconds - b.to_best_wall_seconds);
  return candidates.length ? {row:candidates[0],gap:shinkaReference.value-candidates[0].best_score,qualifyingRuns:candidates.length} : null;
}

export function researchEfficiencyPanel(doc,rows) {
  const selected = researchEfficiency(rows);
  if (!selected) return null;
  const {row,gap,qualifyingRuns} = selected, effort = row.effort_to_best;
  const el = (tag,className,text) => {
    const node=doc.createElement(tag);if(className)node.className=className;
    if(text!==undefined)node.textContent=text;return node;
  };
  const panel=el('section','overview-efficiency');
  panel.setAttribute('aria-label','Selected run near the published ShinkaEvolve result');
  const header=el('header');
  header.append(el('small','','Circle packing · 26 circles · selected run'),el('strong','','Near the ShinkaEvolve result'));
  panel.append(header);
  panel.append(el('p','overview-efficiency-scope','Selected across all models and evaluator groups for this task; independent of the filters above.'));
  const stats=el('div','overview-efficiency-stats');
  const stat=(key,value,label,note)=>{
    const item=el('div');item.dataset.efficiencyMetric=key;
    item.append(el('strong','',value),el('span','',label),el('small','',note));stats.append(item);
  };
  stat('calls',String(effort.physical_llm_calls),'LLM calls to this result','Completed calls within this run');
  const gapLabel=gap===0?'0':gap<5e-11?gap.toExponential(2):Number(gap.toPrecision(3)).toFixed(10);
  stat('gap',gapLabel,'Gap to the published reference','Difference in sum of radii · higher is better');
  stat('elapsed',`${(effort.elapsed_seconds/60).toFixed(2)} min`,'Elapsed to this result','From the start of this run');
  panel.append(stats);
  const details=el('details','overview-efficiency-details');
  details.append(el('summary','','Result, model & comparison details'));
  details.append(el('p','',`SCiEL: ${row.best_score}. ShinkaEvolve: ${shinkaReference.value}. Both use 26 circles in a unit square and numerical slack τ = 10⁻⁶; matching slack does not establish identical numerical verification.`));
  details.append(el('p','',`Model: ${row.models.join(' + ')}. Initial sum of radii: ${row.seed_score}. Evaluator group: ${row.protocol.slice(0,6)}. The call count covers this run through the evaluation of this result; it excludes earlier framework development. No calls were pending at that point.`));
  details.append(el('p','',`Selected for the fewest fully recorded calls among ${qualifyingRuns} runs within 10⁻⁷ of this published reference, across the task’s recorded evaluator groups. All runs remain visible in the model distributions. This is one observed run, not an estimate from repeated trials.`));
  details.append(el('p','',`ShinkaEvolve reports a 150-generation search budget, not 150 total LLM calls. These records do not establish a wall-time speedup or an equal-budget comparison. This reference is the paper’s reported result, not a claim of the current global best.`));
  const link=el('a','',shinkaReference.label+' ↗');link.href=shinkaReference.url;link.target='_blank';link.rel='noopener noreferrer';details.append(link);
  panel.append(details);return panel;
}
