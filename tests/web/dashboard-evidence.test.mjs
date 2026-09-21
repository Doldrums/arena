// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { base, measured, until, mounted, fixtureRun } from './helpers/dashboard-fixture.mjs';
test('timings, start provenance and population reflect recorded data and open saved member code', async () => {
  const { dom, doc, streams, errors } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'population-timing-fixture';
    snapshot.start_protocol = {
      kind: 'fresh',
      label: 'Fresh start · canonical seed + portfolio seeding',
    };
    snapshot.timing = {
      session: { elapsed_seconds: 3672 },
      last_hypothesis_age_seconds: 18,
      intervals: { last_seconds: 73, median_seconds: 80, count: 2, source: 'recorded_monotonic' },
      hypotheses: [{ experiment_id: 'r000003a1' }],
      coverage: { untimed_hypotheses: 0, gaps: [] },
    };
    snapshot.population = {
      available: true,
      source: 'checkpoint',
      iteration: 4,
      stale: false,
      island_count: 1,
      descriptor: { kind: 'pca2_v3' },
      layout: {
        kind: 'map_elites',
        grid_bins: 10,
        x_label: 'Recorded descriptor bin',
        y_label: 'Score bin',
      },
      islands: [
        {
          id: 0,
          best_score: 0.926955,
          member_count: 2,
          grid_cell_count: 1,
          members_available: true,
          grid_available: true,
          grid: [{ x: 3, y: 9, score: 0.926955, candidate_id: 'p3' }],
          members: [
            {
              id: 'p3',
              score: 0.926955,
              code_available: true,
              grid_elite: true,
              archive_member: true,
            },
            {
              id: '<img src=x onerror=alert(1)>',
              score: 0.4,
              code_available: false,
              grid_elite: null,
            },
          ],
        },
      ],
      archive: { count: 1, members: [{ id: 'p3', score: 0.926955, code_available: true }] },
      warnings: [],
    };
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.getElementById('run-elapsed').textContent, '01:01:12');
    assert.equal(doc.getElementById('hypothesis-interval').textContent, '00:01:13');
    assert.match(doc.getElementById('timing-note').textContent, /recorded engine timestamps/);
    assert.match(doc.getElementById('run-note').textContent, /Fresh start/);
    doc.getElementById('tab-population').click();
    assert.equal(doc.getElementById('tab-population').previousElementSibling.id, 'tab-events');
    assert.equal(doc.querySelectorAll('.population-island').length, 1);
    assert.equal(doc.querySelectorAll('.population-empty-cell').length, 100);
    assert.equal(doc.querySelectorAll('.population-filled-cell').length, 1);
    assert.match(doc.getElementById('tab-content').textContent, /Embeddings can define/);
    assert.match(doc.getElementById('tab-content').textContent, /Cell elite/);
    assert.equal(doc.querySelectorAll('.population img').length, 0);
    const svg = doc.querySelector('.population svg');
    const territory = doc.querySelector('#population-map svg');
    assert.ok(territory, 'interactive territory map is mounted');
    doc
      .querySelector('#population-map [data-program="p3"]')
      .dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }));
    assert.equal(doc.querySelector('#population-map .territory-card-title').textContent, 'p3');
    doc.getElementById('population-details').open = true;
    streams
      .at(-1)
      .runtime({
        run: { id: fixtureRun.id, status: snapshot.run.status },
        runtime: null,
        timing: {
          session: { elapsed_seconds: 3674 },
          last_hypothesis_age_seconds: 20,
          intervals: snapshot.timing.intervals,
        },
      });
    assert.equal(doc.getElementById('run-elapsed').textContent, '01:01:14');
    assert.equal(doc.getElementById('last-hypothesis-id').textContent, 'r000003a1');
    assert.equal(
      doc.querySelector('.population svg'),
      svg,
      'heartbeat does not rebuild population',
    );
    assert.equal(
      doc.querySelector('#population-map svg'),
      territory,
      'heartbeat preserves the interactive map',
    );
    snapshot.content_version = 'population-new-observation';
    streams.at(-1).snapshot(snapshot);
    assert.equal(
      doc.querySelector('#population-map svg'),
      territory,
      'content update preserves the map DOM',
    );
    assert.equal(
      doc.querySelector('#population-map .territory-card-title').textContent,
      'p3',
      'selected program survives content update',
    );
    assert.equal(
      doc.getElementById('population-details').open,
      true,
      'storage disclosure persists',
    );
    doc.querySelector('.population-members [data-candidate="p3"]').click();
    await until(() => doc.querySelector('.code-view'), 'population code loaded');
    assert.equal(doc.getElementById('tab-code').getAttribute('aria-selected'), 'true');
    assert.equal(doc.querySelector('#population-map'), null, 'leaving the tab destroys the map');
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('LLM calls tab expands saved exchanges and reference comparison stays collapsed initially', async () => {
  const calls = [];
  const call = {
    id: 'test-call',
    role: 'G',
    reference: 'r1',
    experiment_id: 'r1',
    iteration: 1,
    model: 'recorded-model',
    status: 'returned',
    started_at: '2026-09-19T00:00:00Z',
  };
  const fetchOverride = (url) => {
    if (!url.includes('/llm-calls')) return;
    calls.push(url);
    const value = url.includes('?')
      ? { calls: [call], total: 1, next_offset: null }
      : {
          ...call,
          prompt: { text: 'The full recorded request.', available: true, truncated: false },
          response: { text: 'The raw recorded response.', available: true, truncated: false },
        };
    return Promise.resolve({ ok: true, json: async () => value });
  };
  const { dom, doc, streams, errors } = await mounted({ fetchOverride });
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'calls-reference';
    snapshot.benchmark = {
      label: 'Tolerance-matched reference',
      value: 2.6,
      current_value: 2.5,
      task_target: 2.635,
      metric: 'Sum of radii',
      references: [],
    };
    streams.at(-1).snapshot(snapshot);
    const disclosure = doc.querySelector('.benchmark-disclosure');
    assert.equal(disclosure.open, false);
    assert.match(disclosure.querySelector('summary').textContent, /Tolerance-matched reference/);
    disclosure.open = true;
    const programCall = doc.querySelector('tr[data-candidate] [data-llm-experiment]');
    assert.ok(programCall, 'Programs rows link to their recorded calls');
    programCall.click();
    await until(() => doc.querySelector('.llm-call'), 'LLM call index');
    assert.equal(calls.length, 1);
    assert.equal(doc.getElementById('tab-llm').getAttribute('aria-selected'), 'true');
    doc.querySelector('.llm-call').open = true;
    await until(() => doc.querySelector('.llm-raw'), 'full LLM call');
    assert.match(doc.getElementById('tab-content').textContent, /The full recorded request/);
    const saved = doc.querySelector('.llm-call');
    streams
      .at(-1)
      .runtime({ run: { id: fixtureRun.id, status: snapshot.run.status }, runtime: null });
    assert.equal(
      doc.querySelector('.llm-call'),
      saved,
      'runtime heartbeat does not rebuild transcripts',
    );
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('synthetic API records render score, programs, hypotheses, knowledge and parent diff', async () => {
  const { dom, w, doc, errors, copied } = await mounted();
  try {
    assert.equal(doc.querySelectorAll('[data-run]').length, 7);
    assert.match(doc.getElementById('run-title').textContent, /Synthetic study/);
    assert.match(doc.getElementById('run-status').textContent, /Completed/);
    assert.equal(
      doc.getElementById('best-score').textContent,
      'Not measured',
      'unbound legacy score must not become a native observation',
    );
    assert.equal(doc.getElementById('evaluations').textContent, '4');
    assert.equal(doc.getElementById('cost').textContent, '$0.1157');
    assert.equal(doc.querySelectorAll('tbody tr').length, 7);
    assert.match(doc.querySelector('#chart-outcomes summary').textContent, /unavailable/);
    doc.getElementById('tab-hypotheses').click();
    assert.equal(doc.querySelectorAll('.research-card').length, 7);
    const search = doc.getElementById('content-search');
    search.value = 'r000002a1';
    search.dispatchEvent(new w.Event('input', { bubbles: true }));
    assert.equal(doc.querySelectorAll('.research-card').length, 1);
    doc.querySelector('[data-candidate="p3"]').click();
    await until(() => doc.querySelector('.code-view'), 'diff loaded');
    assert.ok(doc.querySelector('.code-line.add'));
    assert.ok(doc.querySelector('.code-line.remove'));
    doc.querySelector('[data-code-mode="code"]').click();
    assert.match(doc.querySelector('.code-view').textContent, /def construct_packing/);
    doc.getElementById('copy-code').click();
    await until(() => copied(), 'clipboard');
    assert.match(copied(), /def construct_packing/);
    doc.getElementById('tab-lessons').click();
    assert.ok(doc.querySelectorAll('.research-card').length >= 1);
    doc.querySelector('[data-evidence]').click();
    assert.equal(doc.getElementById('tab-hypotheses').getAttribute('aria-selected'), 'true');
    assert.ok(doc.querySelector('.research-card'));
    doc.getElementById('all-events-button').click();
    assert.equal(doc.querySelectorAll('#tab-content details').length, 60);
    doc.querySelector('[data-more]').click();
    assert.equal(doc.querySelectorAll('#tab-content details').length, 75);
    doc.getElementById('help-button').click();
    assert.equal(doc.getElementById('help-dialog').open, true);
    doc.getElementById('help-done').click();
    assert.equal(doc.getElementById('help-dialog').open, false);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('published reference is separate from task target, shows scope and accepts only web source links', async () => {
  const { dom, doc, streams } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.stats.best_score = 2.5 / 2.635;
    snapshot.stats.best_metric_display = measured(2.5, snapshot.stats.best_score, 'Sum of radii');
    snapshot.benchmark = {
      label: 'SOTA reference',
      value: 2.6359830849176078,
      current_value: 2.5,
      reference_tolerance: 1e-6,
      run_tolerance: 1e-6,
      metric: 'Sum of radii',
      task_target: 2.635,
      target_metric: 'Sum of radii',
      source_url: 'https://www.gotherlabs.com/results/circle-packing-26-unit-square/',
      source_label: 'Göther Labs · strict witness',
      note: 'Published strict packing (τ = 0). The comparison is descriptive, not a proof of a new record.',
    };
    streams.at(-1).snapshot(snapshot);
    const panel = doc.getElementById('benchmark-comparison');
    assert.equal(doc.getElementById('best-score-label').textContent, 'Sum of radii');
    assert.equal(doc.getElementById('best-score').textContent, '2.500000');
    assert.equal(
      doc.getElementById('best-score-comparison').textContent,
      '| 5.16% below best known | Best AI search: not available',
    );
    assert.match(doc.getElementById('chart-subtitle').textContent, /Sum of radii/);
    assert.equal(panel.previousElementSibling, doc.querySelector('.metrics'));
    assert.equal(panel.nextElementSibling, doc.querySelector('.overview-grid'));
    assert.match(panel.textContent, /SOTA reference/);
    assert.match(panel.textContent, /2\.500000000/);
    assert.match(panel.textContent, /2\.635983085/);
    assert.match(panel.textContent, /Gap to reference/);
    assert.match(panel.textContent, /not a proof of a new record/);
    assert.match(panel.querySelector('.benchmark-target').textContent, /Task target.*2\.635/);
    assert.equal(panel.querySelector('a').getAttribute('rel'), 'noopener noreferrer');
    snapshot.benchmark.run_tolerance = 1e-6;
    snapshot.benchmark.references = [
      {
        name: 'ShinkaEvolve — reported',
        value: 2.635983099011548,
        value_label: '2.635983099011548',
        tolerance: 1e-6,
        status: 'reported',
        source_name: 'Sakana AI',
        source_url: 'https://openreview.net/pdf?id=lKEdGCoDNC',
        gap_percent: 0.000001,
      },
      {
        name: 'Strict reference',
        value: 2.6359830849176078,
        value_label:
          '2.6359830849176077831865694854434817303966767982744748577457711298607038493344723396767997365079',
        tolerance: 0,
        status: 'audited',
        source_name: 'Untrusted <script>',
        source_url: 'javascript:alert(1)',
        gap_percent: -0.000003,
      },
    ];
    streams.at(-1).snapshot(snapshot);
    assert.equal(panel.querySelectorAll('.benchmark-table [data-reference-row]').length, 2);
    assert.equal(panel.querySelectorAll('.benchmark-table [data-current-solution]').length, 1);
    assert.equal(panel.querySelector('[data-current-solution] td:nth-child(2)').textContent, '2.5');
    assert.match(panel.textContent, /τ = 0 \(strict\)/);
    assert.match(panel.querySelector('.benchmark-table').textContent, /5\.16% below/);
    assert.match(panel.querySelector('.benchmark-table').textContent, /Not comparable/);
    assert.equal(panel.querySelectorAll('.benchmark-table a').length, 1);
    assert.equal(panel.querySelectorAll('script').length, 0);
    snapshot.benchmark.references = [];
    snapshot.benchmark.source_url = 'javascript:window.owned=true';
    streams.at(-1).snapshot(snapshot);
    assert.equal(panel.querySelector('a'), null);
    snapshot.benchmark.current_value = snapshot.benchmark.value * 1.01;
    snapshot.stats.best_score = snapshot.benchmark.current_value / 2.635;
    snapshot.stats.best_metric_display = measured(
      snapshot.benchmark.current_value,
      snapshot.stats.best_score,
      'Sum of radii',
    );
    streams.at(-1).snapshot(snapshot);
    assert.equal(
      doc.getElementById('best-score-comparison').textContent,
      '| 1.0000% above best known | Best AI search: not available',
    );
    snapshot.benchmark.current_value = null;
    snapshot.stats.best_metric_display = {
      ...snapshot.stats.best_metric_display,
      status: 'unknown',
      value: null,
    };
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.getElementById('best-score').textContent, 'Not measured');
    assert.equal(doc.getElementById('best-score-comparison').hidden, true);
  } finally {
    dom.window.close();
  }
});
