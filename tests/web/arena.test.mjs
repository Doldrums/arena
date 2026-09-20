import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html = readFileSync(new URL('../../web/index.html', import.meta.url), 'utf8').replace('data-arena-app="true"', 'data-arena-app="test"');
const source = readFileSync(new URL('../../web/arena.js', import.meta.url), 'utf8').replace(/^export /gm, '');
function task(overrides = {}) {
  return {id: 'packing/circle', name: 'Circle packing', family: 'Geometry', description: 'Pack circles into a square.',
    protocol: 'original', executable: true, runtime_readiness: 'not_verified', metric: 'sum_radii',
    direction: 'max', declared_status: 'ready', requirements: ['numpy'], paper_ids: [], ...overrides};
}
const participants = {summary: {integrated_count: 0}, participants: [{id: 'sciel', name: 'SCiEL',
  description: 'Evolutionary research system.', registration_status: 'planned', adapter_status: 'not_implemented',
  repository: {url: 'https://github.com/example/sciel', commit: '123abc'},
  capabilities: {native_run: false, canonical_evaluation: false, pause: false, resume: false}}]};
async function mount({tasks = [task()], url = 'http://arena.test/', fetchJSON} = {}) {
  const dom = new JSDOM(html, {url, runScripts: 'outside-only', pretendToBeVisual: true});
  const w = dom.window;
  w.eval(`{${source}; window.createArenaApp = createArenaApp; window.safeExternalURL = safeExternalURL;}`);
  const catalog = {tasks, sources: [{id: 'catalog', url: 'https://github.com/example/tasks'}]};
  const app = w.createArenaApp({fetchJSON: fetchJSON || (async path => path === '/api/catalog' ? catalog : participants)});
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
