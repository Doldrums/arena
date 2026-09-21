import { dashboardSource } from './dashboard-source.mjs';
import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createServer } from 'node:http';
import { JSDOM, VirtualConsole } from 'jsdom';
import { dashboardFixtureResponse, fixtureRun, runIndex } from '../fixtures/dashboard-fixture.mjs';
const root = fileURLToPath(new URL('../../../', import.meta.url));

const server = createServer((request, response) => {
  const payload = dashboardFixtureResponse(request.url);
  response.writeHead(payload === null ? 404 : 200, { 'Content-Type': 'application/json' });
  response.end(JSON.stringify(payload ?? { error: 'Unknown synthetic fixture endpoint' }));
});

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));

const port = server.address().port;

after(() => new Promise((resolve) => server.close(resolve)));

const base = 'http://127.0.0.1:' + port;

const assets = process.env.ARENA_WEB_ASSETS
  ? fileURLToPath(new URL(process.env.ARENA_WEB_ASSETS))
  : root + 'web/';

const chart = readFileSync(assets + 'chart.js', 'utf8').replace(
  'export function renderChart',
  'function renderChart',
);

const learning = readFileSync(assets + 'learning.js', 'utf8').replace(
  'export function learningHTML',
  'function learningHTML',
);

const architecture = readFileSync(assets + 'architecture.js', 'utf8').replace(
  /export function (architectureGraphHTML|bindArchitectureGraph|updateArchitectureGraphPhase)/g,
  'function $1',
);

const app = dashboardSource({ assets });

const population = readFileSync(assets + 'population.js', 'utf8').replace(
  /export function (renderPopulationMap|destroyPopulationMap)/g,
  'function $1',
);

const preview = readFileSync(assets + 'population-preview.js', 'utf8').replace(/^export /gm, '');

const storage = readFileSync(assets + 'storage-view.js', 'utf8').replace(
  'export function renderStorageSpace',
  'function renderStorageSpace',
);

const llmCalls = readFileSync(assets + 'llm_calls.js', 'utf8').replace(
  'export function renderLLMCalls',
  'function renderLLMCalls',
);

const workflow = readFileSync(assets + 'workflow.js', 'utf8').replace(/^export /gm, '');

const methodsView = readFileSync(assets + 'methods.js', 'utf8')
  .replace(/^import .*$/gm, '')
  .replace(
    /export function (renderMethodsDashboard|updateMethodsTiming|destroyMethodsDashboard)/g,
    'function $1',
  );

const methodsProgress = readFileSync(assets + 'methods_progress.js', 'utf8').replace(
  /^export /gm,
  '',
);

const methodsAtlas = readFileSync(assets + 'methods_atlas.js', 'utf8').replace(/^export /gm, '');

const researchTools = readFileSync(assets + 'research_tools.js', 'utf8').replace(/^export /gm, '');

const researchCells = readFileSync(assets + 'research_cells.js', 'utf8').replace(/^export /gm, '');

const packings = readFileSync(assets + 'packings.js', 'utf8').replace(/^export /gm, '');

const html = readFileSync(assets + 'experiment.html', 'utf8');

const measured = (value, raw = value, label = 'Score') => ({
  schema: 'sciel-metric-display/1',
  status: 'measured',
  value,
  label,
  units: null,
  raw_score: raw,
  reason: null,
  metric_sha256: 'a'.repeat(64),
});

async function until(predicate, label = 'condition') {
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 15));
  }
  assert.fail('Timed out: ' + label);
}

async function mounted({ runId = fixtureRun.id, tab, fetchOverride, ready, configure } = {}) {
  const errors = [],
    streams = [];
  const console = new VirtualConsole();
  console.on('jsdomError', (error) => errors.push(error));
  const location = new URL(base);
  if (runId) location.searchParams.set('run', runId);
  if (tab) location.searchParams.set('tab', tab);
  const dom = new JSDOM(html, {
    url: location.href,
    runScripts: 'outside-only',
    pretendToBeVisual: true,
    virtualConsole: console,
  });
  const w = dom.window;
  configure?.(w);
  w.fetch = (url) => fetchOverride?.(String(url)) || fetch(new URL(url, base));
  w.ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  w.matchMedia = () => ({ matches: true });
  w.HTMLElement.prototype.scrollIntoView = function () {};
  w.HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  w.HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
  w.EventSource = class extends w.EventTarget {
    constructor(url) {
      super();
      this.url = url;
      this.closed = false;
      streams.push(this);
      w.setTimeout(() => this.onopen?.(), 0);
    }
    close() {
      this.closed = true;
    }
    snapshot(data) {
      this.dispatchEvent(new w.MessageEvent('snapshot', { data: JSON.stringify(data) }));
    }
    runtime(data) {
      this.dispatchEvent(new w.MessageEvent('runtime', { data: JSON.stringify(data) }));
    }
  };
  let copied = null;
  Object.defineProperty(w.navigator, 'clipboard', {
    value: {
      writeText: async (text) => {
        copied = text;
      },
    },
  });
  // Separate scopes mirror ES modules; only the explicit export is shared.
  w.eval(
    '{' +
      readFileSync(assets + 'effort.js', 'utf8').replace(/^export /gm, '') +
      ';Object.assign(window,{renderEffort,effortDetailsHTML,publishedEffortHTML});}',
  );
  w.eval('{' + chart + '; window.renderChart=renderChart;}');
  w.eval('{' + learning + '; window.learningHTML=learningHTML;}');
  w.eval(
    '{' +
      architecture +
      '; Object.assign(window,{architectureGraphHTML,bindArchitectureGraph,updateArchitectureGraphPhase});}',
  );
  w.eval('{' + llmCalls + '; window.renderLLMCalls=renderLLMCalls;}');
  w.eval('{' + workflow + '; Object.assign(window,{renderWorkFlow,destroyWorkFlow});}');
  w.eval('{' + population + '; Object.assign(window,{renderPopulationMap,destroyPopulationMap});}');
  w.eval(
    '{' + preview + '; Object.assign(window,{renderPopulationPreview,destroyPopulationPreview});}',
  );
  w.eval('{' + storage + '; window.renderStorageSpace=renderStorageSpace;}');
  w.eval('{' + methodsProgress + '; Object.assign(window,{renderMethodsProgress});}');
  w.eval(
    '{' +
      methodsAtlas +
      '; Object.assign(window,{renderMethodsPopulation,renderMethodsArchitecture});}',
  );
  w.eval(
    '{' +
      methodsView +
      '; Object.assign(window,{renderMethodsDashboard,updateMethodsTiming,destroyMethodsDashboard});}',
  );
  w.eval('{' + researchTools + '; Object.assign(window,{renderResearchTools});}');
  w.eval('{' + researchCells + '; Object.assign(window,{renderResearchCells});}');
  w.eval(
    '{' + packings + '; Object.assign(window,{renderPackings,suspendPackings,destroyPackings});}',
  );
  w.eval('{' + app + '}');
  await until(
    () =>
      ready
        ? ready(w.document)
        : w.document.getElementById('run-path').textContent !== '' &&
          w.document.getElementById('evaluations').textContent === '4',
    'requested run loaded',
  );
  return { dom, w, doc: w.document, errors, streams, copied: () => copied };
}
export { base, until, mounted, fixtureRun, runIndex, chart, architecture, measured, preview };
