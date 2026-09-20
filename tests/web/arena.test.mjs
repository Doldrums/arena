import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
import {webcrypto} from 'node:crypto';

const html = readFileSync(new URL('../../web/index.html', import.meta.url), 'utf8').replace('data-arena-app="true"', 'data-arena-app="test"');
const source = readFileSync(new URL('../../web/arena.js', import.meta.url), 'utf8').replace(/^export /gm, '').replace(/^import .*$/gm, '');
const insightsSource = readFileSync(new URL('../../web/arena-insights.js', import.meta.url), 'utf8').replace(/^export /gm, '');
const atlasSource = readFileSync(new URL('../../web/arena-atlas.js', import.meta.url), 'utf8').replace(/^export /gm, '');
function task(overrides = {}) {
  return {id: 'packing/circle', name: 'Circle packing', family: 'Geometry', description: 'Pack circles into a square.',
    protocol: 'original', executable: true, runtime_readiness: 'not_verified', metric: 'sum_radii',
    direction: 'max', declared_status: 'ready', requirements: ['numpy'], paper_ids: [], ...overrides};
}
const participants = {summary: {integrated_count: 0}, participants: [{id: 'sciel', name: 'SCiEL',
  description: 'Evolutionary research system.', registration_status: 'planned', adapter_status: 'not_implemented',
  repository: {url: 'https://github.com/example/sciel', commit: '123abc'},
  capabilities: {native_run: false, canonical_evaluation: false, pause: false, resume: false}}]};
function insightsFixture(tasks) {
  const task_annotations = Object.fromEntries(tasks.map(item => [item.id, {domain_id: item.family === 'Geometry' ? 'geometry' : 'other', task_type_id: item.executable ? 'construction' : 'analysis', rationale: 'Synthetic metadata classification.'}]));
  const groups = (key, definitions) => definitions.map(([id,label]) => {
    const rows = tasks.filter(item => task_annotations[item.id][key] === id);
    return {id,label,total:rows.length,executable:rows.filter(item=>item.executable).length,unsupported:rows.filter(item=>!item.executable).length,
      description:`${label} description.`,why_it_matters:`${label} scientific role.`,representative_task_ids:rows.slice(0,2).map(item=>item.id)};
  }).filter(item=>item.total);
  return {denominator:{task_count:tasks.length,unit:'task_package'},summary:{unique_paper_count:1},
    domains:groups('domain_id',[['geometry','Geometry'],['other','Other domain']]),task_types:groups('task_type_id',[['construction','Construction'],['analysis','Analysis']]),
    task_annotations,coverage:[{id:'executable',total:tasks.filter(item=>item.executable).length},{id:'recorded_contract',total:0},{id:'runtime_verified',total:0}]};
}
async function mount({tasks = [task()], url = 'http://arena.test/', fetchJSON, insights, references, searchFamilies} = {}) {
  const dom = new JSDOM(html, {url, runScripts: 'outside-only', pretendToBeVisual: true});
  const w = dom.window;
  w.TextEncoder = TextEncoder; Object.defineProperty(w.crypto, 'subtle', {value:webcrypto.subtle});
  w.eval(`{${insightsSource}; Object.assign(window,{renderArenaInsights,renderTaskReferences,referenceMatches});}`);
  w.eval(`{${atlasSource}; Object.assign(window,{renderArenaAtlas});}`);
  w.eval(`{${source}; window.createArenaApp = createArenaApp; window.safeExternalURL = safeExternalURL;}`);
  const catalog = {tasks, sources: [{id: 'catalog', url: 'https://github.com/example/tasks'}]};
  const responses = {'/api/catalog':catalog,'/api/participants':participants,'/api/insights':insights||insightsFixture(tasks),
    '/api/search-families':searchFamilies||{groups:[{id:'evolution',label:'Evolution',description:'Research program search.',task_ids:tasks.map(item=>item.id)}],task_annotations:Object.fromEntries(tasks.map(item=>[item.id,{search_family_id:'evolution'}]))},
    '/api/references':references||{summary:{task_count:tasks.length,tasks_with_published_reference:0,tasks_with_recorded_baseline:0,tasks_without_numeric_reference:tasks.length,verified_current_sota:0,current_sota_status:'not_assessed'},tasks:tasks.map(item=>({task_id:item.id,anchors:[]}))}};
  const app = w.createArenaApp({fetchJSON: fetchJSON || (async path => responses[path])});
  await app.ready;
  return {dom, w, doc: w.document, app};
}
function input(w, node, value, event = 'input') { node.value = value; node.dispatchEvent(new w.Event(event, {bubbles: true})); }

test('catalog searches real records, combines filters and restores deep-linked task details', async () => {
  const {dom, w, doc} = await mount({tasks: [task(), task({id: 'math/tensor', name: 'Tensor decomposition', description: 'Decompose a tensor.', family: 'Algebra', protocol: 'recreated', executable: false})]});
  try {
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 2);
    input(w, doc.getElementById('arena-search'), 'circle square');
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 1);
    assert.equal(new URL(w.location.href).searchParams.get('q'), 'circle square');
    doc.querySelector('.arena-task-link').click();
    assert.equal(new URL(w.location.href).searchParams.get('task'), 'packing/circle');
    assert.match(doc.getElementById('arena-detail').textContent, /Runtime availabilitynot verified/);
    assert.match(doc.getElementById('arena-detail').textContent, /Metric.*sum_radii/);
    assert.equal(doc.getElementById('arena-list-panel').hidden, true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.getElementById('arena-search').value, 'circle square');
    doc.getElementById('arena-clear').click();
    input(w, doc.getElementById('arena-family'), 'Algebra', 'change');
    input(w, doc.getElementById('arena-protocol'), 'original', 'change');
    assert.match(doc.getElementById('arena-results').textContent, /No tasks match/);
    doc.getElementById('arena-clear').click();
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 2);
  } finally { dom.window.close(); }
});

test('catalog values stay text and unsafe provenance URLs never become links', async () => {
  const {dom, doc, w} = await mount({tasks: [task({id: 'odd/<id>', name: '<img src=x onerror=alert(1)>', description: '<script>alert(1)</script>',
    provenance: {sources: ['javascript:alert(1)', {url: 'data:text/html,danger'}, {url: 'https://example.org/source'}]}})]});
  try {
    assert.equal(doc.querySelector('#arena-results img'), null);
    assert.equal(doc.querySelector('#arena-results script'), null);
    doc.querySelector('.arena-task-link').click();
    assert.equal(new URL(w.location.href).searchParams.get('task'), 'odd/<id>');
    assert.match(doc.getElementById('arena-detail').textContent, /<script>alert\(1\)<\/script>/);
    assert.equal(doc.querySelector('#arena-detail script, #arena-detail img'), null);
    assert.equal(doc.querySelector('#arena-detail a[href^="javascript:"]'), null);
    assert.ok(doc.querySelector('#arena-detail a[href="https://example.org/source"]'));
    assert.equal(w.safeExternalURL('https://user:password@example.org'), null);
  } finally { dom.window.close(); }
});

test('participants show planned capabilities without execution controls', async () => {
  const {dom, doc, w} = await mount({url: 'http://arena.test/?view=participants'});
  try {
    assert.equal(doc.getElementById('arena-title').textContent, 'Participants');
    assert.match(doc.getElementById('arena-results').textContent, /planned/);
    doc.querySelector('.arena-participant .arena-task-link').click();
    assert.equal(new URL(w.location.href).searchParams.get('participant'), 'sciel');
    assert.match(doc.getElementById('arena-detail').textContent, /Native executionNot integrated/);
    assert.match(doc.getElementById('arena-detail').textContent, /Canonical evaluationNot integrated/);
    assert.equal([...doc.querySelectorAll('button')].some(node => /^(Run|Start|Pause|Resume)$/.test(node.textContent)), false);
    assert.ok(doc.querySelector('a[href="/experiments"]'));
  } finally { dom.window.close(); }
});

test('independent API failures keep available registry usable and retry succeeds', async () => {
  let failed = true;
  const {dom, doc, app} = await mount({fetchJSON: async path => {
    if (path === '/api/catalog') { if (failed) throw new Error('Service unavailable'); return {tasks: [task()]}; }
    return participants;
  }});
  try {
    assert.match(doc.getElementById('arena-error').textContent, /Service unavailable/);
    doc.querySelector('[data-arena-view="participants"]').click();
    assert.equal(doc.getElementById('arena-error').hidden, true);
    assert.ok(doc.querySelector('.arena-participant'));
    failed = false; await app.reload();
    doc.querySelector('[data-arena-view="tasks"]').click();
    assert.equal(doc.getElementById('arena-error').hidden, true);
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 1);
  } finally { dom.window.close(); }
});

test('empty registries, unknown links and pagination have explicit states', async () => {
  const empty = await mount({tasks: [], url: 'http://arena.test/?task=missing'});
  try { assert.match(empty.doc.getElementById('arena-detail').textContent, /Task not found/); }
  finally { empty.dom.window.close(); }
  const {dom, doc, w} = await mount({tasks: Array.from({length: 31}, (_, index) => task({id: `task-${index}`, name: `Task ${index}`}))});
  try {
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 25);
    assert.match(doc.getElementById('arena-pagination').textContent, /Page 1 of 2/);
    [...doc.querySelectorAll('#arena-pagination button')].find(node => node.textContent === 'Next →').click();
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 6);
    assert.equal(new URL(w.location.href).searchParams.get('page'), '2');
    assert.equal([...doc.querySelectorAll('#arena-pagination button')].find(node => node.textContent === 'Next →').disabled, true);
  } finally { dom.window.close(); }
});

test('malformed API payload is an error, not an empty catalog', async () => {
  const {dom, doc} = await mount({fetchJSON: async path => path === '/api/catalog' ? {tasks: [{name: 'Missing identity'}]} : participants});
  try { assert.match(doc.getElementById('arena-error').textContent, /invalid registry/); }
  finally { dom.window.close(); }
});

test('task details preserve the declared input/output contract with its pinned source', async () => {
  const contract = 'Input: centers as an array.\nOutput: <candidate> JSON with radii.\n<script>alert(1)</script>';
  const sourceURL = 'https://github.com/example/tasks/blob/123abc/suite/circle/problem.json';
  const {dom, doc} = await mount({url: 'http://arena.test/?task=packing%2Fcircle', tasks: [task({contract,
    contract_source: {url: sourceURL, path: 'suite/circle/problem.json', sha256: 'a'.repeat(64)}})]});
  try {
    const section = doc.querySelector('[data-task-contract]');
    assert.equal(section.querySelector('.arena-contract-text').textContent, contract);
    assert.match(section.textContent, /runtime conformance has not been verified/);
    assert.match(section.textContent, /suite\/circle\/problem.json/);
    assert.match(section.textContent, new RegExp('a'.repeat(64)));
    assert.equal(section.querySelector('a').href, sourceURL);
    assert.equal(section.querySelector('a').rel, 'noopener noreferrer');
    assert.equal(section.querySelector('script, candidate'), null);
  } finally { dom.window.close(); }
});

test('absent task contracts stay explicitly unrecorded without inventing a signature', async () => {
  const {dom, doc} = await mount({url: 'http://arena.test/?task=packing%2Fcircle', tasks: [task({contract: null,
    contract_source: {url: 'javascript:alert(1)', path: 'suite/circle/problem.json', sha256: 'b'.repeat(64)}})]});
  try {
    const section = doc.querySelector('[data-task-contract]');
    assert.equal(section.querySelector('.arena-contract-text').textContent, 'Input/output contract not recorded in the task snapshot.');
    assert.equal(section.querySelector('.arena-contract-note'), null);
    assert.equal(section.querySelector('a'), null);
    assert.match(section.textContent, /suite\/circle\/problem.json/);
  } finally { dom.window.close(); }
});

function referenceFixture(tasks) {
  return {as_of:'2026-09-20',summary:{tasks_with_published_reference:1,tasks_with_recorded_baseline:2,
    tasks_without_numeric_reference:tasks.length-2,current_sota_status:'not_assessed',verified_current_sota:0},
    highlights:[{task_id:tasks[1].id},{task_id:tasks[0].id}],tasks:tasks.map((item,index)=>({task_id:item.id,
      evaluation:{parameters:{n:26},case_count:10,case_count_kind:'configured_default'},
      anchors:index>1?[]:[...(index===0?[{kind:'published_reference',label:'Published value',value:2.63,metric_label:'Sum of radii',
        direction:'maximize',scope:'Exact construction only',evaluation:{case_count:1,case_count_kind:'candidate_construction'},reproduction:'recorded_upstream',source:{url:'https://example.org/pinned'},
        primary_sources:[{type:'paper',url:'https://example.org/paper'}],reproduction_source:{url:'https://example.org/receipt'},notes:['Use identical constraints.']}]:[]),
        {kind:'recorded_seed_baseline',label:'Recorded seed',value:index===0?2.14:100,metric_label:index===0?'Sum of radii':'Exact-match percentage',
          direction:'maximize',validity:index===0?true:null,comparison:'historical_smoke_only',scope:'Historical check',
          evaluation:{case_count:5},source:{url:'https://example.org/seed'},notes:['Historical sample only.']}]}))};
}

test('domain and task-type charts combine URL filters and preserve keyboard focus', async () => {
  const tasks = [task(),task({id:'packing/unsupported',executable:false}),task({id:'other',name:'Other task',family:'Physics'})];
  const insights = insightsFixture(tasks); insights.domains[0].percentage=66.6;
  const {dom,w,doc} = await mount({tasks,insights});
  try {
    const domain = doc.querySelector('[data-filter-kind="domain"][data-filter-value="geometry"]');
    assert.doesNotMatch(domain.textContent,/%/);
    assert.match(doc.querySelector('.insights-composition').textContent,/66\.6%/);
    assert.equal(doc.querySelector('.insights-composition').open,false);
    assert.match(domain.getAttribute('aria-label'),/1 executable definitions, 1 unsupported/);
    domain.focus(); domain.click();
    assert.equal(doc.activeElement.dataset.filterValue,'geometry');
    assert.equal(doc.activeElement.getAttribute('aria-pressed'),'true');
    assert.equal(new URL(w.location).searchParams.get('domain'),'geometry');
    assert.equal(doc.getElementById('arena-result-count').textContent,'2 of 3 tasks');
    doc.querySelector('[data-filter-kind="type"][data-filter-value="construction"]').click();
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 3 tasks');
    assert.match(doc.querySelector('.insights-catalog-jump').textContent,/1 matching tasks/);
    doc.querySelector('button[aria-label="Remove domain filter: Geometry"]').click();
    assert.equal(doc.getElementById('arena-result-count').textContent,'2 of 3 tasks');
    assert.equal(new URL(w.location).searchParams.get('domain'),null);
    w.history.replaceState(null,'','/?domain=geometry&type=analysis');
    w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(doc.querySelector('.arena-task-link').textContent,'Circle packing');
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 3 tasks');
    doc.getElementById('arena-clear').click();
    assert.equal(doc.getElementById('arena-result-count').textContent,'3 of 3 tasks');
  } finally { dom.window.close(); }
});

test('all scientific domains are visible while the independent task-type chart expands', async () => {
  const tasks=[task()],insights=insightsFixture(tasks);
  insights.domains=Array.from({length:12},(_,i)=>({id:`domain-${i}`,label:`Domain ${i}`,total:1,executable:1,unsupported:0}));
  insights.task_types=Array.from({length:18},(_,i)=>({id:`type-${i}`,label:`Type ${i}`,total:1,executable:1,unsupported:0}));
  const {dom,doc}=await mount({tasks,insights});
  try {
    assert.equal(doc.querySelectorAll('[data-domain-card]').length,12);
    assert.equal(doc.querySelectorAll('.insights-composition [data-filter-kind="domain"]').length,12);
    assert.equal(doc.querySelectorAll('[data-filter-kind="type"]').length,10);
    doc.querySelector('[data-insights-action="expand:type"]').click();
    assert.equal(doc.querySelectorAll('[data-filter-kind="type"]').length,18);
    assert.equal(doc.querySelector('[data-insights-action="expand:type"]').getAttribute('aria-expanded'),'true');
  } finally { dom.window.close(); }
});

test('reference examples follow every filter and distinguish published values from seed smoke', async () => {
  const tasks=[task(),task({id:'model',name:'Model task',family:'ML'}),task({id:'no-reference',name:'Missing reference',family:'ML'})];
  const {dom,w,doc}=await mount({tasks,references:referenceFixture(tasks)});
  try {
    let rows=doc.querySelectorAll('#arena-insights [data-reference-task]');
    assert.equal(rows.length,2);
    assert.equal(rows[0].dataset.referenceTask,'model');
    assert.match(rows[0].textContent,/Validity not recorded/);
    assert.match(rows[0].textContent,/5 items \(historical smoke\)/);
    assert.match(rows[1].textContent,/Published reference: 2.63/);
    assert.match(rows[1].textContent,/Seed smoke: 2.14/);
    assert.match(rows[1].textContent,/n: 26/);
    assert.match(rows[1].textContent,/1 construction/);
    assert.doesNotMatch(rows[1].textContent,/Cases: 1/);
    doc.querySelector('[data-filter-kind="domain"][data-filter-value="geometry"]').click();
    rows=doc.querySelectorAll('#arena-insights [data-reference-task]');
    assert.equal(rows.length,1); assert.equal(rows[0].dataset.referenceTask,'packing/circle');
    input(w,doc.getElementById('arena-search'),'missing query');
    assert.equal(doc.querySelectorAll('#arena-insights [data-reference-task]').length,0);
    assert.match(doc.getElementById('arena-insights').textContent,/No numeric references are recorded for the selected tasks/);
    doc.getElementById('arena-clear').click();
    doc.querySelector('[data-insights-action="reference:missing"]').click();
    assert.equal(new URL(w.location).searchParams.get('reference'),'missing');
    assert.equal(doc.querySelector('.arena-task-link').textContent,'Missing reference');
  } finally { dom.window.close(); }
});

test('task detail includes scientific context, precise metric, parameters and source evidence', async () => {
  const tasks=[task(),task({id:'model',name:'Model task',family:'ML'})];
  const {dom,doc}=await mount({tasks,references:referenceFixture(tasks),url:'http://arena.test/?task=packing%2Fcircle'});
  try {
    assert.equal(doc.getElementById('arena-insights').hidden,true);
    assert.match(doc.querySelector('[data-task-science]').textContent,/Geometry scientific role/);
    const section=doc.querySelector('[data-task-references]');
    assert.match(section.textContent,/Sum of radii/);
    assert.match(section.textContent,/Task instance: n: 26/);
    assert.match(section.textContent,/Evaluation size: 10 cases \(configured default\)/);
    assert.match(section.textContent,/5 items \(historical smoke\)/);
    assert.match(section.textContent,/Use identical constraints/);
    assert.ok(section.querySelector('a[href="https://example.org/paper"]'));
    assert.ok(section.querySelector('a[href="https://example.org/receipt"]'));
    assert.match(section.textContent,/Neither alone establishes current SOTA/);
  } finally { dom.window.close(); }
});

test('overview API outages keep task search usable and do not invent zero evidence', async () => {
  const {dom,w,doc}=await mount({url:'http://arena.test/?domain=geometry',fetchJSON:async path=>{
    if(path==='/api/catalog') return {tasks:[task()]};
    if(path==='/api/participants') return participants;
    throw new Error('Offline');
  }});
  try {
    assert.equal(doc.getElementById('arena-error').hidden,true);
    assert.match(doc.getElementById('arena-insights').textContent,/Scientific overview unavailable/);
    assert.match(doc.getElementById('arena-insights').textContent,/Reference evidence unavailable/);
    assert.match(doc.getElementById('arena-active-filters').textContent,/Some filters await overview data/);
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 1 tasks');
    input(w,doc.getElementById('arena-search'),'circle');
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 1 tasks');
    doc.querySelector('.arena-task-link').click();
    assert.match(doc.querySelector('[data-task-references]').textContent,/does not establish that the task has no reference/);
    assert.doesNotMatch(doc.querySelector('[data-task-references]').textContent,/No numeric reference is recorded/);
  } finally { dom.window.close(); }
});

test('scientific and reference metadata remain text and external links reject active content', async () => {
  const tasks=[task(),task({id:'second'})],insights=insightsFixture(tasks),references=referenceFixture(tasks);
  insights.domains[0].label='<img src=x onerror=alert(1)>';
  insights.domains[0].why_it_matters='<script>alert(1)</script>';
  references.tasks[0].anchors[0].value='<img src=x>';
  references.tasks[0].anchors[0].source.url='javascript:alert(1)';
  references.tasks[0].anchors[0].primary_sources=[{url:'data:text/html,bad'}];
  const {dom,doc}=await mount({tasks,insights,references});
  try {
    assert.match(doc.getElementById('arena-insights').textContent,/<img src=x onerror=alert\(1\)>/);
    assert.equal(doc.querySelector('#arena-insights img, #arena-insights script, #arena-insights a[href^="javascript:"]'),null);
    doc.querySelector('.arena-task-link').click();
    assert.equal(doc.querySelector('#arena-detail img, #arena-detail script, #arena-detail a[href^="data:"]'),null);
  } finally { dom.window.close(); }
});


test('atlas switches modes, persists URL and combines source-method and task-family filters', async () => {
  const tasks=[task(),task({id:'unsupported',family:null,executable:false}),task({id:'algebra',family:'Algebra'})];
  const searchFamilies={groups:[{id:'evo',label:'Evolutionary search',task_ids:['packing/circle','unsupported']},{id:'prompt',label:'Prompt optimization',task_ids:['algebra']}],
    task_annotations:{'packing/circle':{search_family_id:'evo'},unsupported:{search_family_id:'evo'},algebra:{search_family_id:'prompt'}}};
  const {dom,w,doc}=await mount({tasks,searchFamilies,url:'http://arena.test/?search_family=evo'});
  try {
    assert.equal(doc.getElementById('arena-result-count').textContent,'2 of 3 tasks');
    assert.equal(doc.querySelectorAll('#arena-atlas rect[data-task-id]').length,3);
    doc.querySelector('[data-atlas-mode="families"]').click();
    assert.equal(new URL(w.location).searchParams.get('atlas'),'families');
    input(w,doc.getElementById('arena-family'),'__unspecified__','change');
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 3 tasks');
    assert.match(doc.getElementById('arena-active-filters').textContent,/Task family: Unspecified/);
    assert.match(doc.getElementById('arena-active-filters').textContent,/Search method: Evolutionary search/);
    doc.querySelector('button[aria-label="Remove search method filter: Evolutionary search"]').click();
    assert.equal(new URL(w.location).searchParams.get('search_family'),null);
    doc.getElementById('arena-clear').click();
    assert.equal(doc.getElementById('arena-result-count').textContent,'3 of 3 tasks');
    assert.equal(doc.querySelector('[data-atlas-mode="families"]').getAttribute('aria-pressed'),'true');
    doc.querySelector('#arena-results .arena-task-link').click();
    assert.equal(doc.getElementById('arena-atlas').hidden,true);
  } finally { dom.window.close(); }
});

test('method filters also update published reference examples', async () => {
  const tasks=[task(),task({id:'model',family:'ML'})];
  const searchFamilies={groups:[{id:'evo',label:'Evolution',task_ids:['packing/circle']},{id:'prompt',label:'Prompt',task_ids:['model']}],
    task_annotations:{'packing/circle':{search_family_id:'evo'},model:{search_family_id:'prompt'}}};
  const {dom,w,doc}=await mount({tasks,searchFamilies,references:referenceFixture(tasks)});
  try {
    w.history.replaceState(null,'','/?search_family=evo'); w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(doc.querySelectorAll('#arena-insights [data-reference-task]').length,1);
    assert.equal(doc.querySelector('#arena-insights [data-reference-task]').dataset.referenceTask,'packing/circle');
    w.history.replaceState(null,'','/?search_family=prompt'); w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(doc.querySelector('#arena-insights [data-reference-task]').dataset.referenceTask,'model');
  } finally { dom.window.close(); }
});


test('unmapped method cluster filters tasks with missing source assignments', async () => {
  const tasks=[task(),task({id:'unmapped'})];
  const searchFamilies={groups:[{id:'evo',label:'Evolution',task_ids:['packing/circle']}],task_annotations:{'packing/circle':{search_family_id:'evo'}}};
  const {dom,doc}=await mount({tasks,searchFamilies,url:'http://arena.test/?search_family=unclassified'});
  try {
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 2 tasks');
    assert.equal(doc.querySelector('#arena-results .arena-task-id').textContent,'unmapped');
  } finally { dom.window.close(); }
});


test('metadata from a different catalog revision is unavailable while task search stays usable', async () => {
  const tasks=[task()],insights=insightsFixture(tasks);
  insights.catalog_digest='0'.repeat(64);
  const searchFamilies={catalog_digest:'0'.repeat(64),groups:[{id:'evo',label:'Evolution',task_ids:['packing/circle']}],task_annotations:{'packing/circle':{search_family_id:'evo'}}};
  const {dom,doc}=await mount({tasks,insights,searchFamilies});
  try {
    assert.match(doc.getElementById('arena-insights').textContent,/Scientific overview unavailable/);
    assert.match(doc.getElementById('arena-atlas').textContent,/unavailable/i);
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 1 tasks');
  } finally { dom.window.close(); }
});

function recordedOverview() {
  const registry = name => JSON.parse(readFileSync(new URL(`../../registry/${name}.json`, import.meta.url), 'utf8'));
  const catalog = registry('catalog'), insights = registry('insights');
  const responses = {'/api/catalog':catalog,'/api/insights':insights,'/api/references':registry('references'),
    '/api/search-families':registry('search-families'),'/api/participants':participants};
  return {catalog,insights,fetchJSON:async path=>responses[path]};
}

test('scientific direction cards retain exact corpus counts and open real chemistry contracts', async () => {
  const {catalog,insights,fetchJSON}=recordedOverview();
  const {dom,w,doc}=await mount({fetchJSON});
  try {
    assert.equal(doc.querySelectorAll('[data-domain-card]').length,insights.domains.length);
    const composition=doc.querySelector('.insights-composition');
    assert.equal(composition.open,false);
    for(const domain of insights.domains) {
      const card=doc.querySelector(`[data-domain-card="${domain.id}"]`);
      assert.ok(card,`Missing direction ${domain.id}`);
      assert.equal(card.querySelector('.field-count').textContent,`${domain.total.toLocaleString('en-US')} tasks`);
      assert.doesNotMatch(card.textContent,/%/);
      const bar=composition.querySelector(`[data-filter-value="${domain.id}"]`);
      assert.ok(bar,`Missing composition count ${domain.id}`);
      assert.match(bar.getAttribute('aria-label'),new RegExp(`${domain.total.toLocaleString('en-US')} tasks`));
      assert.ok(bar.textContent.includes(`${domain.percentage.toFixed(1)}%`));
    }
    assert.ok(composition.querySelector('[role="img"]').getAttribute('aria-label').includes('Unsupported: 428'));
    composition.querySelector('summary').click();
    assert.equal(composition.open,true);
    const chemistry=doc.querySelector('[data-domain-card="chemistry-materials"]');chemistry.focus();chemistry.click();
    assert.equal(doc.querySelector('.insights-composition').open,true);
    assert.equal(doc.activeElement.dataset.domainCard,'chemistry-materials');
    assert.equal(doc.activeElement.getAttribute('aria-pressed'),'true');
    assert.equal(new URL(w.location).searchParams.get('domain'),'chemistry-materials');
    const expected=catalog.tasks.filter(item=>insights.task_annotations[item.id]?.domain_id==='chemistry-materials');
    assert.equal(doc.getElementById('arena-result-count').textContent,`${expected.length} of ${catalog.tasks.length.toLocaleString('en-US')} tasks`);
    assert.deepEqual([...doc.querySelectorAll('#arena-results .arena-task-id')].map(node=>node.textContent).sort(),expected.map(item=>item.id).sort());
    const example=doc.querySelector('[data-field-detail="chemistry-materials"] .field-example a');
    const id=new URL(example.href).searchParams.get('task'),record=catalog.tasks.find(item=>item.id===id);
    assert.ok(record.contract);
    example.click();
    assert.equal(doc.querySelector('[data-task-contract] .arena-contract-text').textContent,record.contract);
    assert.equal(doc.getElementById('arena-insights').hidden,true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.querySelector('.insights-composition').open,true);
    doc.querySelector('.insights-composition summary').click();
    const selected=doc.querySelector('[data-domain-card="chemistry-materials"]');selected.focus();selected.click();
    assert.equal(doc.querySelector('.insights-composition').open,false);
    assert.equal(doc.activeElement.dataset.domainCard,'chemistry-materials');
    assert.equal(doc.activeElement.getAttribute('aria-pressed'),'true');
    doc.activeElement.click();
    assert.equal(doc.querySelector('.insights-composition').open,false);
    assert.equal(doc.activeElement.getAttribute('aria-pressed'),'false');
    assert.equal(new URL(w.location).searchParams.get('domain'),null);
  } finally { dom.window.close(); }
});

test('every scientific direction example belongs to that domain and preserves source-only status', async () => {
  const {catalog,insights,fetchJSON}=recordedOverview(),tasks=new Map(catalog.tasks.map(item=>[item.id,item]));
  const {dom,doc}=await mount({fetchJSON});
  try {
    let executableExamples=0,sourceOnlyExamples=0;
    for(const domain of insights.domains) {
      doc.querySelector(`[data-domain-card="${domain.id}"]`).click();
      const detail=doc.querySelector(`[data-field-detail="${domain.id}"]`);
      assert.ok(detail,`Missing selected context for ${domain.id}`);
      assert.ok(detail.textContent.includes(domain.why_it_matters));
      const examples=[...detail.querySelectorAll('.field-example')];
      assert.equal(examples.length,2,`${domain.id} must offer two real examples`);
      for(const example of examples) {
        const id=new URL(example.querySelector('a').href).searchParams.get('task'),task=tasks.get(id);
        assert.ok(task,`${id} must exist in the catalog`);
        assert.equal(insights.task_annotations[id].domain_id,domain.id,`${id} must belong to the selected domain`);
        assert.equal(example.querySelector('small').textContent,task.executable?'Evaluation definition recorded':'Source-only definition');
        if(task.executable)executableExamples++;else sourceOnlyExamples++;
        if(['earth-environment','finance-economics'].includes(domain.id))assert.equal(task.executable,false);
      }
    }
    assert.ok(executableExamples>0);
    assert.ok(sourceOnlyExamples>=4,'Source-only Earth and Finance examples must remain visible');
  } finally { dom.window.close(); }
});
