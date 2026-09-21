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
async function mount({tasks = [task()], url = 'http://arena.test/', fetchJSON, insights, references, searchFamilies, prepare, participantRecords = participants} = {}) {
  const dom = new JSDOM(html, {url, runScripts: 'outside-only', pretendToBeVisual: true});
  const w = dom.window;
  w.TextEncoder = TextEncoder; Object.defineProperty(w.crypto, 'subtle', {value:webcrypto.subtle});
  w.eval(`{${insightsSource}; Object.assign(window,{renderArenaInsights,renderTaskReferences,referenceMatches});}`);
  w.eval(`{${atlasSource}; Object.assign(window,{renderArenaAtlas});}`);
  w.eval(`{${source}; window.createArenaApp = createArenaApp; window.safeExternalURL = safeExternalURL;}`);
  const catalog = {tasks, sources: [{id: 'catalog', url: 'https://github.com/example/tasks'}]};
  const responses = {'/api/catalog':catalog,'/api/participants':participantRecords,'/api/insights':insights||insightsFixture(tasks),
    '/api/search-families':searchFamilies||{groups:[{id:'evolution',label:'Evolution',description:'Research program search.',task_ids:tasks.map(item=>item.id)}],task_annotations:Object.fromEntries(tasks.map(item=>[item.id,{search_family_id:'evolution'}]))},
    '/api/references':references||{summary:{task_count:tasks.length,tasks_with_published_reference:0,tasks_with_recorded_baseline:0,tasks_without_numeric_reference:tasks.length,verified_current_sota:0,current_sota_status:'not_assessed'},tasks:tasks.map(item=>({task_id:item.id,anchors:[]}))}};
  prepare?.(w);
  const app = w.createArenaApp({fetchJSON: fetchJSON || (async path => responses[path])});
  await app.ready;
  return {dom, w, doc: w.document, app};
}
function input(w, node, value, event = 'input') { node.value = value; node.dispatchEvent(new w.Event(event, {bubbles: true})); }

test('overview keeps domains visible and technical data collapsed without undoing manual closure', async () => {
  const {dom,w,doc,app} = await mount();
  try {
    const browser = doc.getElementById('arena-catalog-browser');
    assert.equal(browser.open,false);
    assert.ok(doc.querySelector('#arena-insights [data-domain-card]'));
    assert.equal(doc.querySelector('#arena-insights .insights-composition'),null);
    assert.ok(doc.querySelector('#arena-statistics .insights-composition'));
    assert.equal(browser.contains(doc.getElementById('arena-statistics')),false);
    assert.equal(doc.getElementById('arena-statistics').hidden,false);
    assert.ok(browser.contains(doc.getElementById('arena-list-panel')));
    assert.equal(browser.contains(doc.getElementById('arena-detail')),false);
    doc.querySelector('[data-domain-card="geometry"]').click();
    doc.querySelector('.field-catalog-link').click();
    assert.equal(browser.open,true);
    browser.open=false;
    app.render();
    assert.equal(browser.open,false);
    await app.reload();
    assert.equal(browser.open,false);
    doc.querySelector('[data-atlas-mode="families"]').click();
    assert.equal(browser.open,false);
    input(w,doc.getElementById('arena-search'),'circle');
    assert.equal(browser.open,true);
    doc.getElementById('arena-clear').click();
    assert.equal(browser.open,true);
  } finally { dom.window.close(); }
});

test('scientific cards expose a keyboard-accessible preview without opening or filtering the catalog', async () => {
  const tasks=[task(),task({id:'second',name:'Second construction'}),task({id:'other',name:'Other task',family:'Physics'})];
  const scrolls=[];
  const {dom,w,doc,app}=await mount({tasks,prepare(w){
    w.HTMLElement.prototype.scrollIntoView=function(){scrolls.push(this.id);};
  }});
  try {
    const browser=doc.getElementById('arena-catalog-browser'),before=w.location.href,historyLength=w.history.length;
    const card=doc.querySelector('[data-domain-card="geometry"]');
    assert.equal(card.tagName,'BUTTON');assert.equal(card.type,'button');assert.equal(card.tabIndex,0);
    assert.equal(card.getAttribute('aria-expanded'),'false');
    assert.equal(card.getAttribute('aria-controls'),'arena-domain-preview');
    card.focus();
    // Native keyboard activation produces a zero-detail click; JSDOM does not synthesize it from keydown.
    card.dispatchEvent(new w.MouseEvent('click',{bubbles:true,detail:0}));
    const preview=doc.getElementById('arena-domain-preview');
    assert.ok(preview);assert.equal(preview.getAttribute('role'),'region');
    assert.equal(preview.getAttribute('aria-labelledby'),'arena-domain-preview-title');
    assert.equal(doc.activeElement.id,'arena-domain-preview-title');
    assert.equal(doc.querySelector('[data-domain-card="geometry"]').getAttribute('aria-expanded'),'true');
    assert.match(preview.textContent,/Geometry scientific role/);
    assert.equal(preview.querySelectorAll('.field-example').length,2);
    assert.equal(browser.open,false);assert.equal(w.location.href,before);assert.equal(w.history.length,historyLength);
    assert.equal(doc.getElementById('arena-result-count').textContent,'3 of 3 tasks');
    assert.equal(doc.getElementById('arena-active-filters').hidden,true);
    assert.ok(!scrolls.some(id=>['arena-list-panel','arena-analysis','arena-catalog-browser'].includes(id)));
    app.render();await app.reload();
    assert.equal(browser.open,false);assert.equal(w.location.href,before);
    assert.equal(doc.querySelector('[data-domain-card="geometry"]').getAttribute('aria-expanded'),'true');
    doc.querySelector('.field-detail-close').focus();
    doc.querySelector('.field-detail-close').click();
    assert.equal(doc.querySelector('[data-field-detail]'),null);
    assert.equal(doc.activeElement.dataset.domainCard,'geometry');
    assert.equal(doc.activeElement.getAttribute('aria-expanded'),'false');
    assert.equal(browser.open,false);assert.equal(w.location.href,before);assert.equal(w.history.length,historyLength);
  } finally { dom.window.close(); }
});

test('domain previews preserve deep-link filters and both manually open and closed catalog states', async () => {
  const tasks=[task(),task({id:'unsupported',executable:false}),task({id:'other',name:'Other task',family:'Physics'})];
  const {dom,w,doc,app}=await mount({tasks,url:'http://arena.test/?domain=geometry&type=construction'});
  try {
    const browser=doc.getElementById('arena-catalog-browser'),before=w.location.href;
    assert.equal(browser.open,true);
    assert.equal(doc.querySelector('[data-field-detail]').dataset.fieldDetail,'geometry');
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 3 tasks');
    doc.querySelector('[data-domain-card="other"]').click();
    assert.equal(browser.open,true);assert.equal(w.location.href,before);
    assert.equal(doc.querySelector('[data-field-detail]').dataset.fieldDetail,'other');
    assert.equal(doc.querySelector('[data-domain-card="geometry"]').getAttribute('aria-expanded'),'false');
    assert.equal(doc.querySelector('[data-domain-card="other"]').getAttribute('aria-expanded'),'true');
    assert.equal(doc.querySelector('.insights-composition [data-filter-value="geometry"]').getAttribute('aria-pressed'),'true');
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 3 tasks');
    doc.querySelector('.field-detail-close').click();
    assert.equal(doc.activeElement.dataset.domainCard,'other');
    assert.equal(doc.querySelector('[data-field-detail]'),null);
    assert.equal(browser.open,true);assert.equal(w.location.href,before);
    browser.open=false;app.render();
    doc.querySelector('[data-domain-card="geometry"]').click();
    assert.equal(browser.open,false);assert.equal(w.location.href,before);
    doc.querySelector('.field-catalog-link').click();
    assert.equal(browser.open,true);
    assert.equal(new URL(w.location).searchParams.get('domain'),'geometry');
    assert.equal(new URL(w.location).searchParams.get('type'),'construction');
    assert.equal(doc.getElementById('arena-result-count').textContent,'1 of 3 tasks');
  } finally { dom.window.close(); }
});

test('a scientific preview example opens task detail without applying a domain filter first', async () => {
  const {dom,w,doc}=await mount();
  try {
    const browser=doc.getElementById('arena-catalog-browser');
    doc.querySelector('[data-domain-card="geometry"]').click();
    assert.equal(browser.open,false);
    doc.querySelector('#arena-domain-preview .field-example a').click();
    assert.equal(new URL(w.location).searchParams.get('task'),'packing/circle');
    assert.equal(new URL(w.location).searchParams.get('domain'),null);
    assert.equal(doc.getElementById('arena-detail').hidden,false);
    assert.equal(doc.getElementById('arena-insights').hidden,true);
    assert.equal(browser.hidden,true);assert.equal(browser.open,false);
    assert.match(doc.getElementById('arena-detail').textContent,/Circle packing/);
  } finally { dom.window.close(); }
});

test('catalog query and hash deep links reveal results while detail links stay outside the disclosure', async t => {
  for (const query of ['q=circle','family=Geometry','protocol=original','domain=geometry','type=construction','reference=missing','search_family=evolution','page=1','#arena-list-panel','#arena-analysis']) {
    await t.test(query,async()=>{
      const {dom,doc}=await mount({url:`http://arena.test/${query.startsWith('#')?'':'?'}${query}`});
      try { assert.equal(doc.getElementById('arena-catalog-browser').open,true); }
      finally { dom.window.close(); }
    });
  }
  const {dom,doc}=await mount({url:'http://arena.test/?task=packing%2Fcircle'});
  try {
    assert.equal(doc.getElementById('arena-catalog-browser').hidden,true);
    assert.equal(doc.getElementById('arena-detail').hidden,false);
    assert.equal(doc.getElementById('arena-faq').hidden,true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.getElementById('arena-catalog-browser').hidden,false);
    assert.equal(doc.getElementById('arena-catalog-browser').open,true);
    assert.equal(doc.activeElement.id,'arena-results-title');
  } finally { dom.window.close(); }
});

test('catalog anchors and history reveal the target before scrolling, including repeated hash links', async () => {
  const {dom,w,doc}=await mount();
  try {
    const browser=doc.getElementById('arena-catalog-browser'),panel=doc.getElementById('arena-list-panel'),scrolls=[];
    panel.scrollIntoView=()=>scrolls.push(browser.open);
    doc.querySelector('.insights-catalog-jump').click();
    assert.equal(w.location.hash,'#arena-list-panel');
    assert.equal(browser.open,true);
    assert.equal(doc.activeElement.id,'arena-results-title');
    assert.ok(scrolls.length);assert.ok(scrolls.every(Boolean));
    browser.open=false;
    doc.querySelector('.insights-catalog-jump').click();
    assert.equal(browser.open,true);
    browser.open=false;
    const faqLink=doc.querySelector('#arena-faq a[href="#arena-list-panel"]');
    faqLink.closest('details').open=true;faqLink.click();
    assert.equal(browser.open,true);
    assert.equal(doc.activeElement.id,'arena-results-title');
    browser.open=false;
    w.history.replaceState(null,'','/?domain=geometry');w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(browser.open,true);
    browser.open=false;
    w.history.replaceState(null,'','/#arena-analysis');w.dispatchEvent(new w.HashChangeEvent('hashchange'));
    assert.equal(browser.open,true);
  } finally { dom.window.close(); }
});

test('initial catalog hash scroll waits for domain cards to establish the target position', async () => {
  const scrolls=[];
  const {dom}=await mount({url:'http://arena.test/#arena-list-panel',prepare(w){
    w.HTMLElement.prototype.scrollIntoView=function(){scrolls.push({id:this.id,domains:w.document.querySelectorAll('[data-domain-card]').length});};
  }});
  try {
    assert.ok(scrolls.length);
    assert.ok(scrolls.every(item=>item.id==='arena-list-panel' && item.domains>0));
  } finally { dom.window.close(); }
});

test('pagination and removing the last filter keep the catalog open and focus its results', async () => {
  const {dom,w,doc}=await mount({tasks:Array.from({length:31},(_,index)=>task({id:`task-${index}`,name:`Task ${index}`}))});
  try {
    const browser=doc.getElementById('arena-catalog-browser');
    doc.querySelector('[data-domain-card="geometry"]').click();
    doc.querySelector('.field-catalog-link').click();
    browser.open=false;
    doc.querySelector('button[aria-label="Remove domain filter: Geometry"]').click();
    assert.equal(browser.open,true);
    [...doc.querySelectorAll('#arena-pagination button')].find(node=>node.textContent==='Next →').click();
    assert.equal(browser.open,true);
    assert.equal(new URL(w.location).searchParams.get('page'),'2');
    assert.equal(doc.activeElement.id,'arena-results-title');
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length,6);
    doc.querySelector('.arena-task-link').click();
    assert.equal(browser.hidden,true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(browser.open,true);
    assert.match(doc.getElementById('arena-pagination').textContent,/Page 2 of 2/);
  } finally { dom.window.close(); }
});

test('participants remain visible without the task disclosure or scientific analysis', async () => {
  const {dom,doc}=await mount({url:'http://arena.test/?view=participants'});
  try {
    const browser=doc.getElementById('arena-catalog-browser');
    assert.equal(browser.open,true);assert.equal(browser.hidden,false);
    assert.equal(doc.getElementById('arena-catalog-toggle').hidden,true);
    assert.equal(doc.getElementById('arena-analysis').hidden,true);
    assert.equal(doc.getElementById('arena-faq').hidden,true);
    assert.ok(doc.querySelector('.arena-participant'));
    doc.querySelector('[data-arena-view="tasks"]').click();
    assert.equal(browser.open,false);
    assert.equal(doc.getElementById('arena-catalog-toggle').hidden,false);
    assert.equal(doc.getElementById('arena-analysis').hidden,false);
  } finally { dom.window.close(); }
});

test('standalone scientific overview retains combined charts and references without an analysis root', async () => {
  const tasks=[task(),task({id:'model'})],{dom,w,doc}=await mount({tasks});
  try {
    const root=doc.createElement('div');doc.body.append(root);
    w.renderArenaInsights(root,{catalog:{tasks},insights:insightsFixture(tasks),references:referenceFixture(tasks),current:{},onFilter:()=>{}});
    assert.ok(root.querySelector('[data-domain-card]'));
    assert.ok(root.querySelector('.insights-composition'));
    assert.ok(root.querySelector('[data-reference-task]'));
  } finally { dom.window.close(); }
});

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
    assert.match(doc.getElementById('arena-results').textContent, /Source pinned/);
    assert.match(doc.getElementById('arena-results').textContent, /Integration open/);
    doc.querySelector('.arena-participant .arena-task-link').click();
    assert.equal(new URL(w.location.href).searchParams.get('participant'), 'sciel');
    assert.match(doc.getElementById('arena-detail').textContent, /Native executionIntegration pending/);
    assert.match(doc.getElementById('arena-detail').textContent, /Canonical evaluationIntegration pending/);
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
    const domain = doc.querySelector('.insights-composition [data-filter-kind="domain"][data-filter-value="geometry"]');
    assert.match(domain.textContent,/66\.6%/);
    assert.match(doc.querySelector('.insights-composition').textContent,/66\.6%/);
    assert.equal(doc.querySelector('.insights-composition').open,false);
    assert.match(domain.getAttribute('aria-label'),/1 executable definitions, 1 awaiting an evaluator/);
    domain.focus(); domain.click();
    assert.equal(doc.activeElement.dataset.filterValue,'geometry');
    assert.equal(doc.activeElement.getAttribute('aria-pressed'),'true');
    assert.equal(new URL(w.location).searchParams.get('domain'),'geometry');
    assert.equal(doc.getElementById('arena-result-count').textContent,'2 of 3 tasks');
    const taskType=doc.querySelector('[data-filter-kind="type"][data-filter-value="construction"]');
    taskType.focus();taskType.click();
    assert.equal(doc.activeElement.dataset.insightsAction,'type:construction');
    assert.equal(doc.getElementById('arena-analysis').contains(doc.activeElement),true);
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
    let rows=doc.querySelectorAll('#arena-analysis [data-reference-task]');
    assert.equal(rows.length,2);
    assert.equal(rows[0].dataset.referenceTask,'model');
    assert.match(rows[0].textContent,/Validity not recorded/);
    assert.match(rows[0].textContent,/5 items \(historical smoke\)/);
    assert.match(rows[1].textContent,/Published reference: 2.63/);
    assert.match(rows[1].textContent,/Seed smoke: 2.14/);
    assert.match(rows[1].textContent,/n: 26/);
    assert.match(rows[1].textContent,/1 construction/);
    assert.doesNotMatch(rows[1].textContent,/Cases: 1/);
    doc.querySelector('[data-domain-card="geometry"]').click();
    doc.querySelector('.field-catalog-link').click();
    rows=doc.querySelectorAll('#arena-analysis [data-reference-task]');
    assert.equal(rows.length,1); assert.equal(rows[0].dataset.referenceTask,'packing/circle');
    input(w,doc.getElementById('arena-search'),'missing query');
    assert.equal(doc.querySelectorAll('#arena-analysis [data-reference-task]').length,0);
    assert.match(doc.getElementById('arena-analysis').textContent,/No numeric references are recorded for the selected tasks/);
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
    assert.match(doc.getElementById('arena-analysis').textContent,/Reference evidence unavailable/);
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
    assert.equal(doc.querySelector('#arena-insights img, #arena-insights script, #arena-insights a[href^="javascript:"], #arena-analysis img, #arena-analysis script, #arena-analysis a[href^="javascript:"]'),null);
    doc.querySelector('.arena-task-link').click();
    assert.equal(doc.querySelector('#arena-detail img, #arena-detail script, #arena-detail a[href^="data:"]'),null);
  } finally { dom.window.close(); }
});


test('atlas mode persists while separate source-method and evaluator-family filters combine', async () => {
  const tasks=[task(),task({id:'unsupported',family:null,executable:false}),task({id:'algebra',family:'Algebra'})];
  const searchFamilies={groups:[{id:'evo',label:'Evolutionary search',task_ids:['packing/circle','unsupported']},{id:'prompt',label:'Prompt optimization',task_ids:['algebra']}],
    task_annotations:{'packing/circle':{search_family_id:'evo'},unsupported:{search_family_id:'evo'},algebra:{search_family_id:'prompt'}}};
  const {dom,w,doc}=await mount({tasks,searchFamilies,url:'http://arena.test/?search_family=evo'});
  try {
    assert.equal(doc.getElementById('arena-result-count').textContent,'2 of 3 tasks');
    assert.equal(doc.querySelectorAll('#arena-atlas circle[data-task-id]').length,3);
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

test('Task families atlas browses the same Physics tasks and scientific detail as its domain card', async () => {
  const tasks=[task(),task({id:'physical-model',name:'Physical model',family:'Algebra'}),task({id:'biology-model',name:'Biology model',family:'Geometry'})];
  const insights=insightsFixture(tasks);
  insights.task_annotations['packing/circle'].domain_id='physics';
  insights.task_annotations['physical-model'].domain_id='physics';
  insights.task_annotations['biology-model'].domain_id='biology-health';
  insights.domains=[
    {id:'physics',label:'Physics',total:2,executable:2,unsupported:0,description:'Physical systems.',why_it_matters:'Understand physical behavior.',representative_task_ids:['physical-model','packing/circle']},
    {id:'biology-health',label:'Biology & health',total:1,executable:1,unsupported:0,description:'Living systems.',why_it_matters:'Understand biological behavior.',representative_task_ids:['biology-model']},
  ];
  const {dom,w,doc}=await mount({tasks,insights});
  const resultIds=()=>[...doc.querySelectorAll('#arena-results .arena-task-id')].map(node=>node.textContent).sort();
  try {
    doc.querySelector('[data-domain-card="physics"]').click();
    doc.querySelector('.field-catalog-link').click();
    const cardTaskIds=resultIds();
    assert.deepEqual(cardTaskIds,['packing/circle','physical-model']);
    assert.equal(new URL(w.location).searchParams.get('domain'),'physics');
    doc.querySelector('.field-detail-close').click();
    doc.getElementById('arena-clear').click();
    assert.equal(doc.querySelector('[data-field-detail]'),null);
    doc.querySelector('[data-atlas-mode="families"]').click();
    assert.equal(new URL(w.location).searchParams.get('atlas'),'families');
    const physics=doc.querySelector('#arena-atlas [data-atlas-cluster="physics"]');
    assert.ok(physics);
    assert.equal(physics.querySelectorAll('[data-task-id]').length,2);
    assert.ok(doc.querySelector('#arena-atlas [data-atlas-cluster="biology-health"]'));
    assert.equal(doc.querySelector('#arena-atlas [data-atlas-cluster="Geometry"]'),null);
    physics.dispatchEvent(new w.Event('click'));
    assert.equal(new URL(w.location).searchParams.get('domain'),null);
    assert.equal(doc.querySelector('#arena-atlas .atlas-details h3').textContent,'Physics');
    doc.querySelector('#arena-atlas .atlas-browse').click();
    assert.equal(new URL(w.location).searchParams.get('domain'),'physics');
    assert.equal(new URL(w.location).searchParams.get('family'),null);
    assert.equal(doc.getElementById('arena-catalog-browser').open,true);
    assert.deepEqual(resultIds(),cardTaskIds);
    assert.equal(doc.getElementById('arena-result-count').textContent,'2 of 3 tasks');
    assert.equal(doc.querySelector('[data-field-detail]').dataset.fieldDetail,'physics');
    assert.equal(doc.querySelector('[data-domain-card="physics"]').getAttribute('aria-expanded'),'true');
    assert.match(doc.getElementById('arena-active-filters').textContent,/Domain: Physics/);
    input(w,doc.getElementById('arena-family'),'Geometry','change');
    assert.equal(new URL(w.location).searchParams.get('domain'),'physics');
    assert.equal(new URL(w.location).searchParams.get('family'),'Geometry');
    assert.deepEqual(resultIds(),['packing/circle']);
    w.history.replaceState(null,'','/?atlas=families&domain=physics');w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.deepEqual(resultIds(),cardTaskIds);
    assert.equal(doc.querySelector('#arena-atlas [data-atlas-cluster="physics"]').getAttribute('aria-pressed'),'true');
  } finally { dom.window.close(); }
});

test('method filters also update published reference examples', async () => {
  const tasks=[task(),task({id:'model',family:'ML'})];
  const searchFamilies={groups:[{id:'evo',label:'Evolution',task_ids:['packing/circle']},{id:'prompt',label:'Prompt',task_ids:['model']}],
    task_annotations:{'packing/circle':{search_family_id:'evo'},model:{search_family_id:'prompt'}}};
  const {dom,w,doc}=await mount({tasks,searchFamilies,references:referenceFixture(tasks)});
  try {
    w.history.replaceState(null,'','/?search_family=evo'); w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(doc.querySelectorAll('#arena-analysis [data-reference-task]').length,1);
    assert.equal(doc.querySelector('#arena-analysis [data-reference-task]').dataset.referenceTask,'packing/circle');
    w.history.replaceState(null,'','/?search_family=prompt'); w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(doc.querySelector('#arena-analysis [data-reference-task]').dataset.referenceTask,'model');
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
    assert.ok(composition.querySelector('[role="img"]').getAttribute('aria-label').includes('Evaluator to be added: 270'));
    composition.querySelector('summary').click();
    assert.equal(composition.open,true);
    const chemistry=doc.querySelector('[data-domain-card="chemistry-materials"]');chemistry.focus();chemistry.click();
    assert.equal(doc.querySelector('.insights-composition').open,true);
    assert.equal(doc.activeElement.id,'arena-domain-preview-title');
    assert.equal(doc.querySelector('[data-domain-card="chemistry-materials"]').getAttribute('aria-expanded'),'true');
    assert.equal(new URL(w.location).searchParams.get('domain'),null);
    assert.equal(doc.getElementById('arena-catalog-browser').open,false);
    doc.querySelector('.field-catalog-link').click();
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
    const beforeClose=w.location.href;
    doc.querySelector('.field-detail-close').click();
    assert.equal(doc.querySelector('.insights-composition').open,false);
    assert.equal(doc.activeElement.dataset.domainCard,'chemistry-materials');
    assert.equal(doc.activeElement.getAttribute('aria-expanded'),'false');
    assert.equal(w.location.href,beforeClose);
    doc.activeElement.click();
    assert.equal(doc.querySelector('.insights-composition').open,false);
    assert.equal(doc.querySelector('[data-domain-card="chemistry-materials"]').getAttribute('aria-expanded'),'true');
    assert.equal(w.location.href,beforeClose);
  } finally { dom.window.close(); }
});

test('all 24 scientific examples explain the task and research value with safe primary sources', async () => {
  const {catalog,insights,fetchJSON}=recordedOverview(),tasks=new Map(catalog.tasks.map(item=>[item.id,item]));
  const {dom,doc}=await mount({fetchJSON});
  try {
    let executableExamples=0,sourceOnlyExamples=0;
    const contexts=new Map();
    for(const domain of insights.domains) {
      doc.querySelector(`[data-domain-card="${domain.id}"]`).click();
      const detail=doc.querySelector(`[data-field-detail="${domain.id}"]`);
      assert.ok(detail,`Missing selected context for ${domain.id}`);
      assert.ok(detail.textContent.includes(domain.why_it_matters));
      const examples=[...detail.querySelectorAll('.field-example')];
      assert.equal(examples.length,2,`${domain.id} must offer two real examples`);
      for(const example of examples) {
        const id=new URL(example.querySelector('a[data-arena-route]').href).searchParams.get('task'),task=tasks.get(id);
        assert.ok(task,`${id} must exist in the catalog`);
        assert.equal(insights.task_annotations[id].domain_id,domain.id,`${id} must belong to the selected domain`);
        const context=example.querySelector('.field-example-context');
        assert.ok(context,`${id} needs a task explanation, not a readiness label`);
        const summary=context.textContent.trim();
        assert.ok(summary.split(/\s+/).length>=20,`${id} needs a substantial explanation of the task and research value`);
        assert.doesNotMatch(summary,/Evaluation definition recorded|Source-only definition|awaiting an evaluator|runtime readiness/i);
        assert.notEqual(summary,domain.why_it_matters,`${id} must describe this task, not repeat its domain card`);
        assert.equal(context.querySelector('img,script,iframe'),null);
        const source=example.querySelector('.field-context-source');
        assert.ok(source,`${id} needs a source for its explanation`);
        const url=new URL(source.href);
        assert.equal(url.protocol,'https:');assert.equal(url.username,'');assert.equal(url.password,'');
        assert.equal(source.target,'_blank');assert.match(source.rel,/noopener/);assert.match(source.rel,/noreferrer/);
        assert.equal(source.hasAttribute('data-arena-route'),false);
        assert.ok(source.textContent.trim());
        assert.equal(contexts.has(id),false,`${id} must not be reused as a different scientific example`);
        contexts.set(id,summary);
        if(task.executable)executableExamples++;else sourceOnlyExamples++;
        if(['earth-environment','finance-economics'].includes(domain.id))assert.equal(task.executable,false);
      }
    }
    assert.equal(contexts.size,24);
    assert.ok(executableExamples>0);
    assert.ok(sourceOnlyExamples>=4,'Source-only Earth and Finance examples must remain visible');
    const matrix=contexts.get('alphaevolve-matrix-multiplication-4-4-4');
    assert.match(matrix,/4[×x]4/);assert.match(matrix,/49/);assert.match(matrix,/Strassen/);assert.match(matrix,/1969/);
    for(const [id,summary] of contexts) {
      if(id!=='alphaevolve-matrix-multiplication-4-4-4')assert.doesNotMatch(summary,/Strassen|1969/,`${id} must not inherit matrix multiplication history`);
    }
    const forest=contexts.get('loongflow-tabular-playground-series-dec-2021');
    assert.match(forest,/synthetic/i);assert.match(forest,/generat(?:ed|ion)|modeled on/i);
    assert.match(forest,/class(?:es|ification)/i);
    const packing=contexts.get('alphaevolve-circle-packing-in-unit-square');
    assert.match(packing,/26/);assert.match(packing,/lower bound/i);assert.match(packing,/(?:total|sum(?: of)?) radii/i);
    assert.doesNotMatch(packing,/proven optimal packing|optimal arrangement|globally optimal|best possible packing|solves the packing problem/i);
  } finally { dom.window.close(); }
});


test('research works expose paper provenance and safe source links without implying execution support', async () => {
  const record = {id:'method-x',name:'Method X',record_kind:'research_work',registration_status:'literature',adapter_status:'not_implemented',
    description:'Evolves search procedures.',search_family:{id:'evolution',label:'Evolutionary methods'},
    papers:[{id:'paper-x',title:'Research <script>literal</script>',url:'https://arxiv.org/abs/1234.56789',year:2025,venue:'Research venue'}],
    code_links:[{label:'Result notebook',url:'https://example.org/results'},{label:'Unsafe',url:'javascript:alert(1)'}],
    provenance:{filename:'research-corpus.md',line_start:12,line_end:30},capabilities:{native_run:false}};
  const {dom,doc}=await mount({url:'http://arena.test/?view=participants',participantRecords:{participants:[record],summary:{research_work_count:1,pinned_registration_count:0}}});
  try {
    const card=doc.querySelector('.arena-participant');
    assert.match(card.textContent,/Research work/);assert.match(card.textContent,/2025 · Research venue/);
    assert.equal(card.querySelector('script'),null);
    const paper=card.querySelector('.arena-paper-title');
    assert.equal(paper.getAttribute('href'),'https://arxiv.org/abs/1234.56789');
    assert.equal(paper.target,'_blank');assert.match(paper.rel,/noopener/);
    assert.ok([...card.querySelectorAll('a')].some(a=>a.textContent==='Result notebook ↗'));
    assert.equal(card.querySelector('a[href^="javascript:"]'),null);
    card.querySelector('.arena-task-link').click();
    const detail=doc.getElementById('arena-detail');
    assert.ok(detail.querySelector('.arena-participant-papers.is-detail'));
    assert.match(detail.textContent,/research-corpus.md, lines 12–30/);
    assert.doesNotMatch(detail.textContent,/Native executionAvailable/);
  } finally {dom.window.close();}
});

test('research adapter links show native engines and exact pins without granting registration capabilities', async () => {
  const record={id:'method-x',name:'Method X',record_kind:'research_work',registration_status:'literature',
    repository:null,adapter_status:'not_implemented',capabilities:{native_run:false,canonical_evaluation:false,pause:false,resume:false},
    native_adapters:[{engine:'method-engine',name:'Native <script>literal</script>',
      repository:{url:'https://github.com/example/method',commit:'a'.repeat(40)},profiles:['native-search','native-evaluate'],
      evaluation:'native',runtime_readiness:'not_verified'}]};
  const {dom,doc}=await mount({url:'http://arena.test/?view=participants',participantRecords:{participants:[record]}});
  try {
    const card=doc.querySelector('.arena-participant');
    assert.match(card.textContent,/Research work/);assert.match(card.textContent,/Local adapter/);
    assert.doesNotMatch(card.textContent,/Source pinned|Adapter integrated/);
    card.querySelector('.arena-task-link').click();
    const detail=doc.getElementById('arena-detail');
    assert.match(detail.textContent,/Source and fixture checks · native environment to be verified/);
    assert.match(detail.textContent,/method-engine/);assert.match(detail.textContent,/native-search, native-evaluate/);
    assert.match(detail.textContent,/native evaluation/);
    assert.match(detail.textContent,/do not establish canonical task compatibility or a verified runtime/);
    assert.doesNotMatch(detail.textContent,/Native executionAvailable|Canonical evaluationAvailable/);
    assert.equal(detail.querySelector('script'),null);
    const source=detail.querySelector(`a[href="https://github.com/example/method/tree/${'a'.repeat(40)}"]`);
    assert.ok(source);assert.equal(source.target,'_blank');assert.match(source.rel,/noopener/);
    assert.equal(record.registration_status,'literature');assert.equal(record.capabilities.native_run,false);
  } finally {dom.window.close();}
});

test('blocked and artifact-only works do not acquire runnable badges from the current snapshot', async () => {
  const snapshot=JSON.parse(readFileSync(new URL('../../registry/participants.json',import.meta.url),'utf8'));
  const records=snapshot.participants.filter(item=>['meta-harness','evoflow','aevo','adas'].includes(item.id));
  assert.equal(records.length,4);
  const {dom,doc}=await mount({url:'http://arena.test/?view=participants',participantRecords:{participants:records}});
  try {
    for(const id of ['meta-harness','evoflow','aevo']) {
      const card=doc.querySelector(`[data-participant="${id}"].arena-participant`);
      assert.match(card.textContent,/Integration open/);assert.doesNotMatch(card.textContent,/Local adapter/);
    }
    assert.match(doc.querySelector('[data-participant="adas"].arena-participant').textContent,/Local adapter/);
  } finally {dom.window.close();}
});

test('participant search includes bibliography and family filters with pagination and history', async () => {
  const records=Array.from({length:31},(_,i)=>({id:`work-${i}`,name:`Work ${i}`,record_kind:'research_work',adapter_status:'not_implemented',
    search_family:{id:i<27?'search':'prompts',label:i<27?'Search methods':'Prompt methods'},
    papers:[{title:i===29?'Distinctive research title':`Publication ${i}`,url:`https://example.org/paper/${i}`,year:2025,venue:'Conference'}]}));
  const {dom,doc,w}=await mount({url:'http://arena.test/?view=participants',participantRecords:{participants:records}});
  try {
    assert.equal(doc.querySelectorAll('.arena-participant').length,25);
    assert.match(doc.getElementById('arena-result-count').textContent,/31 of 31/);
    [...doc.querySelectorAll('#arena-pagination button')].find(b=>b.textContent==='Next →').click();
    assert.equal(doc.querySelectorAll('.arena-participant').length,6);
    assert.equal(new URL(w.location.href).searchParams.get('page'),'2');
    doc.querySelector('.arena-participant .arena-task-link').click();
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.querySelectorAll('.arena-participant').length,6);
    input(w,doc.getElementById('arena-family'),'prompts','change');
    assert.equal(doc.querySelectorAll('.arena-participant').length,4);
    assert.equal(new URL(w.location.href).searchParams.has('page'),false);
    input(w,doc.getElementById('arena-search'),'Distinctive');
    assert.equal(doc.querySelectorAll('.arena-participant').length,1);
    assert.equal(doc.querySelector('.arena-participant').dataset.participant,'work-29');
    doc.getElementById('arena-clear').click();
    assert.match(doc.getElementById('arena-result-count').textContent,/31 of 31/);
  } finally {dom.window.close();}
});


test('participant bylines credit primary research sources and search full institutions', async () => {
  const records=[{id:'lab-method',name:'Lab method',record_kind:'research_work',
    attribution:{kind:'organizations',display:'Sakana AI · UBC',organizations:['Sakana AI','University of British Columbia'],authors:[],
      source_url:'https://arxiv.org/pdf/2505.22954v3',source_locator:'p. 1 author affiliations',evidence_note:'Work-done affiliations.'}},
    {id:'author-method',name:'Author method',record_kind:'research_work',
      attribution:{kind:'authors',display:'A <script>literal</script>',organizations:[],authors:['A Researcher'],source_url:'javascript:alert(1)'}}];
  const {dom,doc,w}=await mount({url:'http://arena.test/?view=participants',participantRecords:{participants:records}});
  try {
    const byline=doc.querySelector('[data-participant="lab-method"] .arena-participant-byline');
    assert.equal(byline.textContent,'by Sakana AI · UBC');
    const source=byline.querySelector('a');
    assert.equal(source.href,'https://arxiv.org/pdf/2505.22954v3');
    assert.equal(source.target,'_blank');assert.match(source.rel,/noopener/);
    const author=doc.querySelector('[data-participant="author-method"] .arena-participant-byline');
    assert.equal(author.querySelector('a'),null);assert.equal(author.querySelector('script'),null);
    assert.equal(author.textContent,'by A <script>literal</script>');
    input(w,doc.getElementById('arena-search'),'British Columbia');
    assert.equal(doc.querySelectorAll('.arena-participant').length,1);
    doc.querySelector('.arena-participant .arena-task-link').click();
    const detail=doc.getElementById('arena-detail');
    assert.equal(detail.querySelector('.arena-participant-byline').textContent,'by Sakana AI · UBC');
    assert.match(detail.querySelector('.arena-attribution-context').textContent,/University of British Columbia/);
    assert.match(detail.querySelector('.arena-attribution-context').textContent,/Work-done affiliations/);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    input(w,doc.getElementById('arena-search'),'A Researcher');
    assert.equal(doc.querySelectorAll('.arena-participant').length,1);
    assert.equal(doc.querySelector('.arena-participant').dataset.participant,'author-method');
  } finally {dom.window.close();}
});
