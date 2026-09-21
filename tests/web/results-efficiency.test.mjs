import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {researchEfficiency,researchEfficiencyPanel,shinkaReference} from '../../web/results-efficiency.js';

const observed = {
  task_id:'oe/circle_packing',metric:'sum_radii',direction:'maximize',units:'unit_square_side_length',
  protocol:'7258d873e87d181696cad7c12f67813f5e0b18e3ef2694a0113dee285d77ba87',
  models:['anthropic/claude-opus-5'],measurement_status:'measured',seed_score:0.9597642169962064,
  best_score:2.635983084525617,to_best_wall_seconds:141.136,
  effort_to_best:{scope:'current_run_through_best_evaluation',physical_llm_calls:4,dispatched_llm_calls:4,pending_llm_calls:0,history_complete:true,elapsed_seconds:141.136},
};
const copy = value=>JSON.parse(JSON.stringify(value));

test('efficiency selection pairs the selected score with complete calls through its own evaluation',()=>{
  const later=copy(observed);later.best_score+=1e-9;later.effort_to_best.physical_llm_calls=9;later.effort_to_best.dispatched_llm_calls=9;
  const candidates=[later,observed],result=researchEfficiency(candidates);
  assert.equal(result.row,observed);assert.equal(result.qualifyingRuns,2);
  assert.ok(Math.abs(result.gap-1.4485931e-8)<1e-15);
  assert.deepEqual(candidates,[later,observed],'does not reorder the input');
});

test('unknown call history, pending calls, total-only counts and mismatched clocks cannot headline efficiency',()=>{
  const cases=[
    {history_complete:false},{pending_llm_calls:1},{dispatched_llm_calls:5},
    {scope:'total_physical_receipts'},{elapsed_seconds:142},{physical_llm_calls:0,dispatched_llm_calls:0},
  ];
  for(const changes of cases){const row=copy(observed);Object.assign(row.effort_to_best,changes);assert.equal(researchEfficiency([row]),null);}
  const totalOnly=copy(observed);delete totalOnly.effort_to_best;totalOnly.usage={physical_llm_calls:4};
  assert.equal(researchEfficiency([totalOnly]),null);
});

test('reference comparison fails closed outside the reviewed task, tolerance-bound protocol and numerical window',()=>{
  for(const changes of [{task_id:'other'},{metric:'target_ratio'},{direction:'minimize'},{units:'ratio'},{protocol:'a'.repeat(64)},{measurement_status:'unknown'},{best_score:null},{best_score:2.63},{best_score:shinkaReference.value+1e-8}]){
    assert.equal(researchEfficiency([{...observed,...changes}]),null);
  }
});

test('the compact result leads with SCiEL effort while the exact model and comparison limits remain in details',()=>{
  const dom=new JSDOM(''),panel=researchEfficiencyPanel(dom.window.document,[observed]);
  assert.match(panel.querySelector('header').textContent,/Near the ShinkaEvolve result/);
  assert.doesNotMatch(panel.querySelector('header').textContent,/Opus|Astra/);
  assert.equal(panel.querySelector('[data-efficiency-metric=calls] strong').textContent,'4');
  assert.equal(panel.querySelector('[data-efficiency-metric=gap] strong').textContent,'0.0000000145');
  assert.match(panel.querySelector('.overview-efficiency-scope').textContent,/across all models and evaluator groups/);
  const details=panel.querySelector('details');assert.equal(details.open,false);
  assert.match(details.textContent,/anthropic\/claude-opus-5/);assert.match(details.textContent,/not 150 total LLM calls/);
  assert.match(details.textContent,/one observed run/);assert.match(details.textContent,/not a claim of the current global best/);
  assert.equal(details.querySelector('a').href,shinkaReference.url);
  assert.equal(researchEfficiencyPanel(dom.window.document,[]),null);dom.window.close();
});

test('zero and sub-display-precision gaps remain accurate rather than implying a lower score or rounding away the gap',()=>{
  const dom=new JSDOM('');
  for(const [score,expected] of [[shinkaReference.value,'0'],[shinkaReference.value-1e-12,'1.00e-12']]){
    const panel=researchEfficiencyPanel(dom.window.document,[{...observed,best_score:score}]);
    assert.equal(panel.querySelector('[data-efficiency-metric=gap] strong').textContent,expected);
    assert.equal(panel.querySelector('[data-efficiency-metric=gap] span').textContent,'Gap to the published reference');
  }
  dom.window.close();
});
