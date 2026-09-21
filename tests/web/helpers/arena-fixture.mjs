import { arenaSource } from './arena-source.mjs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';
import { webcrypto } from 'node:crypto';
const html = readFileSync(new URL('../../../web/index.html', import.meta.url), 'utf8').replace(
  'data-arena-app="true"',
  'data-arena-app="test"',
);

const source = arenaSource();

const insightsSource = readFileSync(
  new URL('../../../web/arena-insights.js', import.meta.url),
  'utf8',
).replace(/^export /gm, '');

const atlasSource = readFileSync(
  new URL('../../../web/arena-atlas.js', import.meta.url),
  'utf8',
).replace(/^export /gm, '');

function task(overrides = {}) {
  return {
    id: 'packing/circle',
    name: 'Circle packing',
    family: 'Geometry',
    description: 'Pack circles into a square.',
    protocol: 'original',
    executable: true,
    runtime_readiness: 'not_verified',
    metric: 'sum_radii',
    direction: 'max',
    declared_status: 'ready',
    requirements: ['numpy'],
    paper_ids: [],
    ...overrides,
  };
}

const participants = {
  summary: { integrated_count: 0 },
  participants: [
    {
      id: 'sciel',
      name: 'SCiEL',
      description: 'Evolutionary research system.',
      registration_status: 'planned',
      adapter_status: 'not_implemented',
      repository: { url: 'https://github.com/example/sciel', commit: '123abc' },
      capabilities: { native_run: false, canonical_evaluation: false, pause: false, resume: false },
    },
  ],
};

function insightsFixture(tasks) {
  const task_annotations = Object.fromEntries(
    tasks.map((item) => [
      item.id,
      {
        domain_id: item.family === 'Geometry' ? 'geometry' : 'other',
        task_type_id: item.executable ? 'construction' : 'analysis',
        rationale: 'Synthetic metadata classification.',
      },
    ]),
  );
  const groups = (key, definitions) =>
    definitions
      .map(([id, label]) => {
        const rows = tasks.filter((item) => task_annotations[item.id][key] === id);
        return {
          id,
          label,
          total: rows.length,
          executable: rows.filter((item) => item.executable).length,
          unsupported: rows.filter((item) => !item.executable).length,
          description: `${label} description.`,
          why_it_matters: `${label} scientific role.`,
          representative_task_ids: rows.slice(0, 2).map((item) => item.id),
        };
      })
      .filter((item) => item.total);
  return {
    denominator: { task_count: tasks.length, unit: 'task_package' },
    summary: { unique_paper_count: 1 },
    domains: groups('domain_id', [
      ['geometry', 'Geometry'],
      ['other', 'Other domain'],
    ]),
    task_types: groups('task_type_id', [
      ['construction', 'Construction'],
      ['analysis', 'Analysis'],
    ]),
    task_annotations,
    coverage: [
      { id: 'executable', total: tasks.filter((item) => item.executable).length },
      { id: 'recorded_contract', total: 0 },
      { id: 'runtime_verified', total: 0 },
    ],
  };
}

async function mount({
  tasks = [task()],
  url = 'http://arena.test/',
  fetchJSON,
  insights,
  references,
  searchFamilies,
  prepare,
  participantRecords = participants,
} = {}) {
  const dom = new JSDOM(html, { url, runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  w.TextEncoder = TextEncoder;
  Object.defineProperty(w.crypto, 'subtle', { value: webcrypto.subtle });
  w.eval(
    `{${insightsSource}; Object.assign(window,{renderArenaInsights,renderTaskReferences,referenceMatches});}`,
  );
  w.eval(`{${atlasSource}; Object.assign(window,{renderArenaAtlas});}`);
  w.eval(
    `{${source}; window.createArenaApp = createArenaApp; window.safeExternalURL = safeExternalURL;}`,
  );
  const catalog = { tasks, sources: [{ id: 'catalog', url: 'https://github.com/example/tasks' }] };
  const responses = {
    '/api/catalog': catalog,
    '/api/participants': participantRecords,
    '/api/insights': insights || insightsFixture(tasks),
    '/api/search-families': searchFamilies || {
      groups: [
        {
          id: 'evolution',
          label: 'Evolution',
          description: 'Research program search.',
          task_ids: tasks.map((item) => item.id),
        },
      ],
      task_annotations: Object.fromEntries(
        tasks.map((item) => [item.id, { search_family_id: 'evolution' }]),
      ),
    },
    '/api/references': references || {
      summary: {
        task_count: tasks.length,
        tasks_with_published_reference: 0,
        tasks_with_recorded_baseline: 0,
        tasks_without_numeric_reference: tasks.length,
        verified_current_sota: 0,
        current_sota_status: 'not_assessed',
      },
      tasks: tasks.map((item) => ({ task_id: item.id, anchors: [] })),
    },
  };
  prepare?.(w);
  const app = w.createArenaApp({ fetchJSON: fetchJSON || (async (path) => responses[path]) });
  await app.ready;
  return { dom, w, doc: w.document, app };
}

function input(w, node, value, event = 'input') {
  node.value = value;
  node.dispatchEvent(new w.Event(event, { bubbles: true }));
}

function referenceFixture(tasks) {
  return {
    as_of: '2026-09-20',
    summary: {
      tasks_with_published_reference: 1,
      tasks_with_recorded_baseline: 2,
      tasks_without_numeric_reference: tasks.length - 2,
      current_sota_status: 'not_assessed',
      verified_current_sota: 0,
    },
    highlights: [{ task_id: tasks[1].id }, { task_id: tasks[0].id }],
    tasks: tasks.map((item, index) => ({
      task_id: item.id,
      evaluation: { parameters: { n: 26 }, case_count: 10, case_count_kind: 'configured_default' },
      anchors:
        index > 1
          ? []
          : [
              ...(index === 0
                ? [
                    {
                      kind: 'published_reference',
                      label: 'Published value',
                      value: 2.63,
                      metric_label: 'Sum of radii',
                      direction: 'maximize',
                      scope: 'Exact construction only',
                      evaluation: { case_count: 1, case_count_kind: 'candidate_construction' },
                      reproduction: 'recorded_upstream',
                      source: { url: 'https://example.org/pinned' },
                      primary_sources: [{ type: 'paper', url: 'https://example.org/paper' }],
                      reproduction_source: { url: 'https://example.org/receipt' },
                      notes: ['Use identical constraints.'],
                    },
                  ]
                : []),
              {
                kind: 'recorded_seed_baseline',
                label: 'Recorded seed',
                value: index === 0 ? 2.14 : 100,
                metric_label: index === 0 ? 'Sum of radii' : 'Exact-match percentage',
                direction: 'maximize',
                validity: index === 0 ? true : null,
                comparison: 'historical_smoke_only',
                scope: 'Historical check',
                evaluation: { case_count: 5 },
                source: { url: 'https://example.org/seed' },
                notes: ['Historical sample only.'],
              },
            ],
    })),
  };
}

function recordedOverview() {
  const registry = (name) =>
    JSON.parse(readFileSync(new URL(`../../../registry/${name}.json`, import.meta.url), 'utf8'));
  const catalog = registry('catalog'),
    insights = registry('insights');
  const responses = {
    '/api/catalog': catalog,
    '/api/insights': insights,
    '/api/references': registry('references'),
    '/api/search-families': registry('search-families'),
    '/api/participants': participants,
  };
  return { catalog, insights, fetchJSON: async (path) => responses[path] };
}
export {
  task,
  participants,
  mount,
  input,
  insightsFixture,
  referenceFixture,
  source,
  recordedOverview,
};
