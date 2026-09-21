// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { base, chart, measured, until, mounted, fixtureRun } from './helpers/dashboard-fixture.mjs';
test('progress card follows exact program lineage and opens code and LLM for that candidate', async () => {
  const requests = [];
  const fetchOverride = (url) => {
    if (url.endsWith('/program/chart-b')) {
      requests.push(url);
      return Promise.resolve({
        ok: true,
        json: async () => ({
          id: 'chart-b',
          code: 'saved chart child\n',
          parent_code: 'saved seed\n',
          parent_id: 'seed-2',
          diff: '-saved seed\n+saved chart child\n',
          diff_kind: 'full_sources',
          code_source: 'checkpoint',
        }),
      });
    }
    if (url.includes('/llm-calls?')) {
      requests.push(url);
      return Promise.resolve({
        ok: true,
        json: async () => ({ calls: [], total: 0, next_offset: null }),
      });
    }
  };
  const { dom, w, doc, streams, errors } = await mounted({ fetchOverride });
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'interactive-lineage';
    snapshot.benchmark = null;
    const seed = {
      candidate_id: 'seed-1',
      candidate_ids: ['seed-1', 'seed-2'],
      parent_ids: [],
      kind: 'seed',
      iteration: 0,
      score: 0.1,
      best_score: 0.1,
      cost_total: 0,
      code_available: true,
      llm_available: false,
      status: 'seed',
    };
    const a = {
      candidate_id: 'chart-a',
      experiment_id: 'research-a',
      parent_ids: ['seed-1'],
      iteration: 1,
      score: 0.4,
      best_score: 0.4,
      cost_total: 0.1,
      code_available: true,
      llm_available: true,
      status: 'evaluated',
    };
    const b = {
      candidate_id: 'chart-b',
      experiment_id: 'research-b',
      parent_ids: ['seed-2'],
      iteration: 1,
      score: 0.8,
      parent_score: 0.1,
      best_score: 0.8,
      cost_total: 0.2,
      code_available: true,
      llm_available: true,
      status: 'evaluated',
      hypothesis: 'Exact recorded child B',
      operator: 'diff',
      island: 1,
    };
    for (const row of [seed, a, b]) {
      row.metric_display = measured(row.score);
      row.best_metric_display = measured(row.best_score);
      if (row.parent_score !== undefined) row.parent_metric_display = measured(row.parent_score);
    }
    snapshot.curves = [seed, a, b];
    snapshot.programs = [seed, { ...seed, candidate_id: 'seed-2', candidate_ids: [] }, a, b];
    snapshot.trials = [
      {
        id: 'research-a',
        candidate_id: 'chart-a',
        iteration: 1,
        parent_id: 'seed-1',
        score: 0.4,
        code_available: true,
      },
      {
        id: 'research-b',
        candidate_id: 'chart-b',
        iteration: 1,
        parent_id: 'seed-2',
        score: 0.8,
        code_available: true,
      },
    ];
    snapshot.hypotheses = [];
    streams.at(-1).snapshot(snapshot);
    const dot = doc.querySelector('.chart-dot[data-index="2"]');
    assert.ok(dot);
    dot.dispatchEvent(new w.Event('pointerenter'));
    assert.match(doc.querySelector('.chart-program-card').textContent, /Exact recorded child B/);
    assert.ok(doc.querySelector('.chart-family-edge[data-child="chart-b"]'));
    assert.ok(doc.querySelector('.chart-program-card [data-program="seed-2"]'));
    dot.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    const svg = doc.querySelector('#score-chart svg');
    streams
      .at(-1)
      .runtime({ run: { id: fixtureRun.id, status: snapshot.run.status }, runtime: null });
    assert.equal(doc.querySelector('#score-chart svg'), svg, 'heartbeat preserves pinned graph');
    doc.querySelector('[data-chart-inspect]').click();
    await until(() => doc.querySelector('.code-view'), 'selected chart source');
    assert.match(doc.querySelector('.code-view').textContent, /saved chart child/);
    assert.ok(
      requests.some((path) => path.endsWith('/program/chart-b')),
      'equal iteration does not select chart-a',
    );
    doc.querySelector('[data-chart-llm]').click();
    await until(
      () => requests.some((path) => path.includes('/llm-calls?')),
      'selected chart LLM calls',
    );
    assert.ok(requests.some((path) => path.includes('q=research-b')));
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('bandits and RL show recorded status, credit, probabilities and bounded charts', async () => {
  const { dom, doc, streams, errors } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'learning-fixture';
    snapshot.learning = {
      components: [
        {
          id: 'operator',
          label: 'Operator bandit',
          status: 'online',
          detail: 'Learns from credited records.',
        },
        { id: 'mode', label: 'Mode bandit', status: 'disabled', detail: 'Not enabled.' },
        {
          id: 'rl',
          label: 'Neural policy training',
          status: 'disabled',
          detail: 'No optimizer updates.',
        },
        {
          id: 'embed',
          label: 'Code embedding',
          status: 'frozen',
          detail: '<img src=x onerror=alert(1)>',
        },
      ],
      summary: {
        iterations: 1200,
        record_events: 1,
        credited_operator_updates: 0,
        cumulative_reward: 1.25,
      },
      history_limit: 300,
      operator: {
        arms: [
          {
            name: 'diff',
            choices: 1,
            executions: 0,
            evaluated_count: 0,
            record_count: 0,
            credited_updates: 0,
            cumulative_reward: 0,
          },
          {
            name: 'full_rewrite',
            choices: 0,
            executions: 1,
            evaluated_count: 1,
            record_count: 1,
            credited_updates: 0,
            cumulative_reward: 1.25,
          },
        ],
        history: Array.from({ length: 1200 }, (_, i) => ({
          iteration: i + 1,
          island: 0,
          operator: 'full_rewrite',
          selected_operator: 'diff',
          selected_probability: 0.33,
          reward: 1.25,
          escalated: true,
          forced: false,
          stats: { diff: 0, full_rewrite: 0 },
        })),
        checkpoint: {
          iteration: 1190,
          stale: true,
          window: 50,
          temperature: 0.5,
          floor: 0.05,
          arms: [{ name: 'diff', window_count: 0, window_max: 0 }],
        },
      },
      controller: {
        source: 'static',
        history: [
          {
            iteration: 9,
            iteration_before: 8,
            event_seq: 2,
            mode: 'exploit',
            effective_mode: 'base',
            plateau: false,
            distribution: { base: 0.8, exploit: 0.2 },
            propensity: 0.2,
            phase: 0,
          },
          {
            iteration: null,
            iteration_before: 9,
            event_seq: 3,
            mode: 'base',
            effective_mode: null,
            plateau: false,
            distribution: { base: 0.8, exploit: 0.2 },
            propensity: 0.8,
            phase: 0,
          },
        ],
      },
      rewards: Array.from({ length: 1200 }, (_, i) => ({
        iteration: i + 1,
        reward: i === 0 ? 1.25 : 0,
        cumulative_reward: 1.25,
      })),
      notes: ['Missing observations remain unknown.'],
    };
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-learning').click();
    assert.equal(doc.getElementById('tab-learning').getAttribute('aria-selected'), 'true');
    assert.match(doc.querySelector('[data-component="operator"]').textContent, /Online adaptation/);
    assert.match(doc.querySelector('[data-component="rl"]').textContent, /Disabled/);
    assert.match(doc.querySelector('[data-component="embed"]').textContent, /Frozen inference/);
    assert.equal(doc.querySelectorAll('.learning img').length, 0);
    assert.equal(doc.querySelectorAll('.learning-chart').length, 4);
    for (const svg of doc.querySelectorAll('.learning-chart'))
      assert.ok(svg.querySelectorAll('circle').length <= 2400);
    assert.equal(doc.querySelectorAll('.learning-decisions tbody tr').length, 30);
    assert.match(doc.querySelector('.learning-decisions').textContent, /diff → full_rewrite/);
    assert.match(doc.querySelector('.learning-decisions').textContent, /Escalated/);
    assert.match(doc.querySelector('.learning').textContent, /earlier than the live journal/);
    assert.match(doc.querySelector('.learning').textContent, /not an RL training loss/);
    const modeChart = doc.querySelectorAll('.learning-chart')[1];
    assert.equal(
      modeChart.querySelectorAll('circle').length,
      4,
      'pending controller decisions remain visible',
    );
    assert.match(modeChart.textContent, /Recorded pre-step iteration 8/);
    const chart = doc.querySelector('.learning-chart');
    streams
      .at(-1)
      .runtime({ run: { id: fixtureRun.id, status: snapshot.run.status }, runtime: null });
    assert.equal(
      doc.querySelector('.learning-chart'),
      chart,
      'heartbeat does not rebuild bandit charts',
    );
    snapshot.content_version = 'learning-presets';
    snapshot.learning.controller = {
      source: 'preset weights',
      history: [
        {
          source: 'preset_weights',
          iteration: 10,
          iteration_before: 9,
          mode: 'explore',
          effective_mode: 'explore',
          adaptive: true,
          distribution: { base: 0.7, exploit: 0.2, explore: 0.1 },
          propensity: 0.1,
        },
        {
          source: 'preset_weights',
          iteration: null,
          iteration_before: 10,
          mode: 'base',
          effective_mode: null,
          adaptive: true,
          distribution: { base: 0.75, exploit: 0.15, explore: 0.1 },
          propensity: 0.75,
        },
      ],
      preset_weights: {
        available: true,
        iteration: 9,
        stale: true,
        updates: 8,
        learning_rate: 0.1,
        exploration: 0.1,
        max_importance_reward: 10,
        log_weights: { base: 0, exploit: -1.5, explore: -2, '<img src=x onerror=alert(1)>': -3 },
      },
    };
    streams.at(-1).snapshot(snapshot);
    assert.match(
      doc.querySelector('.learning-preset-state').textContent,
      /Checkpoint iteration 9 · earlier than the live journal/,
    );
    assert.match(doc.querySelector('.learning-preset-state').textContent, /Recorded updates: 8/);
    assert.match(
      doc.querySelector('.learning-preset-state').textContent,
      /Log weights are saved state, not probabilities/,
    );
    assert.match(doc.querySelector('.learning-preset-state').textContent, /-1\.500/);
    assert.equal(doc.querySelectorAll('.learning img').length, 0);
    assert.match(doc.querySelector('.learning-controller-decisions').textContent, /Preset weights/);
    assert.match(doc.querySelector('.learning-controller-decisions').textContent, /Not recorded/);
    assert.equal(doc.querySelectorAll('.learning-chart')[1].querySelectorAll('circle').length, 6);
    assert.match(
      doc.querySelectorAll('.learning-chart')[1].textContent,
      /explore · Recorded pre-step iteration 9 · 10\.00%/,
    );
    snapshot.content_version = 'learning-no-checkpoint';
    snapshot.learning.operator.checkpoint = { available: false, iteration: null, arms: [] };
    snapshot.learning.controller.preset_weights = { available: false };
    streams.at(-1).snapshot(snapshot);
    assert.match(doc.querySelector('.learning').textContent, /No saved operator bandit state yet/);
    assert.match(doc.querySelector('.learning').textContent, /No saved preset weights yet/);
    snapshot.content_version = 'learning-missing';
    snapshot.learning = null;
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelectorAll('.learning-chart').length, 0);
    assert.match(doc.getElementById('tab-content').textContent, /not recorded/);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('bootstrap attempts do not present the zero search counter as all evaluated programs', async () => {
  const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
  snapshot.content_version = 'bootstrap-counter-scope';
  snapshot.stats = { ...snapshot.stats, evaluations: 0, iterations: 0, attempts: 4 };
  snapshot.trials = snapshot.trials.slice(0, 4);
  snapshot.runtime = {
    available: true,
    active: true,
    stage: 'evaluating',
    parallel: {
      schema: 'sciel-parallel-runtime/1',
      wave: 2,
      phase: 'bootstrap',
      workers: 4,
      jobs: 4,
      pending_llm_calls: 0,
      pending_evaluations: 4,
    },
  };
  const before = JSON.stringify(snapshot.stats);
  const { dom, doc, errors } = await mounted({
    fetchOverride: (url) =>
      url.endsWith('/api/runs/' + fixtureRun.id)
        ? Promise.resolve({ ok: true, json: async () => snapshot })
        : null,
    ready: (doc) => doc.getElementById('evaluations').textContent === '0',
  });
  try {
    const counter = doc.getElementById('evaluations');
    assert.equal(counter.textContent, '0');
    assert.equal(
      counter.parentElement.querySelector('.metric-label').textContent,
      'Successful search evaluations',
    );
    assert.equal(
      doc.getElementById('evaluation-scope').textContent,
      'Excludes seed, bootstrap and failed evaluations.',
    );
    assert.match(counter.title, /including successful remeasurements/);
    assert.equal(doc.getElementById('trials-tab-count').textContent, '4');
    assert.match(
      doc.getElementById('chart-end').textContent,
      /0 iterations · 0 search evaluations/,
    );
    assert.match(
      doc.getElementById('chart-end').title,
      /Excludes seed, bootstrap and failed evaluations/,
    );
    assert.equal(
      JSON.stringify(snapshot.stats),
      before,
      'UI does not change scientific counter values',
    );
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('measured output repeats remain visible separately from admitted search evaluations', async () => {
  const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
  snapshot.stats = { ...snapshot.stats, evaluations: 0, measured_results: 4, repeated_outputs: 3 };
  const { dom, doc, errors } = await mounted({
    fetchOverride: (url) =>
      url.endsWith('/api/runs/' + fixtureRun.id)
        ? Promise.resolve({ ok: true, json: async () => snapshot })
        : null,
    ready: (doc) => doc.getElementById('evaluations').textContent === '0',
  });
  try {
    assert.match(
      doc.getElementById('attempts').textContent,
      /4 measured results · 3 exact output repeats/,
    );
    assert.match(doc.getElementById('attempts').title, /do not prove equivalent algorithms/);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});
