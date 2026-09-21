import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {researchRsiSummary,researchRsiPanel} from '../../web/results-rsi.js';

const observed={schema:'sciel-self-improvement/1',scope:'recorded_run',coverage:'complete',cells_created:3,cell_revisions:2,tools_registered:4,tools_executed:2,tool_executions:7,shared_observation_deliveries:1};
const row={models:['model-a'],self_improvement:observed};

test('RSI process totals retain within-run counting and distinguish usage from creation',()=>{
 const data=[row,{...row,models:['model-b']}],summary=researchRsiSummary(data);
 assert.equal(summary.runs,2);assert.equal(summary.covered,2);assert.equal(summary.complete,2);
 assert.equal(summary.counts.cells_created.value,6);assert.equal(summary.counts.tools_registered.value,8);
 assert.equal(summary.counts.tools_executed.value,4);assert.equal(summary.counts.tool_executions.value,14);
 assert.deepEqual(summary.models.map(m=>m.model),['model-a','model-b']);assert.equal(observed.cells_created,3);
});

test('missing coverage and unknown counters never silently become measured zero',()=>{
 const summary=researchRsiSummary([{models:['model-a']},{models:['model-b'],self_improvement:{...observed,coverage:'partial',tools_registered:null}}]);
 assert.equal(summary.covered,1);assert.equal(summary.partial,1);
 assert.deepEqual(summary.counts.tools_registered,{value:null,runs:0});
 assert.deepEqual(summary.counts.cells_created,{value:3,runs:1});
 assert.equal(summary.models[0].counts.cells_created.value,null);
 assert.equal(researchRsiSummary([{self_improvement:{...observed,coverage:'not_recorded'}}]).covered,0);
});

test('a recorded zero remains visible and does not receive an invention or improvement claim',()=>{
 const empty=Object.fromEntries(Object.keys(observed).map(k=>[k,typeof observed[k]==='number'?0:observed[k]]));
 const dom=new JSDOM(''),panel=researchRsiPanel(dom.window.document,[{models:['model-a'],self_improvement:empty}]);
 assert.equal(panel.querySelector('[data-rsi-metric=cells_created] strong').textContent,'0');
 assert.match(panel.querySelector('details').textContent,/do not by themselves prove/);
 assert.equal(researchRsiPanel(dom.window.document,[{models:['model-b']}]),null);dom.window.close();
});

test('RSI panel states global scope, exposes missing coverage and escapes model identities',()=>{
 const dom=new JSDOM(''),panel=researchRsiPanel(dom.window.document,[{...row,models:['<img src=x>']},{models:['other']}]);
 assert.match(panel.querySelector('header').textContent,/all 2 recorded runs and all models/);
 assert.match(panel.querySelector('summary').textContent,/1 \/ 2 runs/);
 assert.equal(panel.querySelectorAll('img,script').length,0);
 assert.match(panel.querySelector('table').textContent,/Not recorded/);
 assert.match(panel.querySelector('details').textContent,/not globally unique inventions/);
 assert.equal(panel.querySelector('a').getAttribute('href'),'/experiments');dom.window.close();
});
