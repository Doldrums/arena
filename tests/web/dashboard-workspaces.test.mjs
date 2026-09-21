// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  base,
  preview,
  measured,
  until,
  mounted,
  fixtureRun,
} from './helpers/dashboard-fixture.mjs';
test('long histories have bounded chart and event DOM while retaining selected samples and searchable history', async () => {
  const { dom, w, doc, streams } = await mounted();
  try {
    const points = Array.from({ length: 130000 }, (_, iteration) => ({
      iteration,
      score: iteration === 50001 ? -3 : iteration === 129999 ? 5 : 0.5,
      best_score: iteration === 129999 ? 5 : 0.5,
    }));
    let selected;
    const shown = w.renderChart(
      doc.getElementById('score-chart'),
      points,
      'iteration',
      42000,
      (p) => (selected = p),
    );
    assert.equal(shown.total, 130000);
    assert.ok(shown.displayed <= 600);
    assert.ok(doc.querySelectorAll('.chart-dot').length <= 600);
    doc.querySelector('.chart-dot.selected').dispatchEvent(new w.Event('click'));
    assert.equal(selected.iteration, 42000);
    assert.match(doc.getElementById('score-chart').textContent, /Iteration 50001/);
    assert.match(doc.getElementById('score-chart').textContent, /Iteration 129999/);
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'bounded-event-fixture';
    snapshot.events = Array.from({ length: 650 }, (_, i) => ({
      seq: i + 1,
      event: 'decision',
      data: { text: i === 0 ? 'older-search-marker' : 'Recorded event' },
    }));
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-events').click();
    for (let i = 0; i < 9; i++) doc.querySelector('[data-more]')?.click();
    assert.equal(doc.querySelectorAll('.event-row').length, 600);
    assert.equal(doc.querySelector('[data-more]'), null);
    assert.match(doc.querySelector('.display-limit').textContent, /650/);
    assert.ok([...doc.querySelectorAll('.event-data')].every((node) => !node.textContent));
    doc.querySelector('.event-row').open = true;
    await until(
      () => doc.querySelector('.event-data').textContent.includes('Recorded event'),
      'lazy event data',
    );
    const input = doc.getElementById('content-search');
    input.value = 'older-search-marker';
    input.dispatchEvent(new w.Event('input', { bubbles: true }));
    assert.equal(doc.querySelectorAll('.event-row').length, 1);
    assert.equal(doc.querySelector('.event-row').dataset.seq, '1');
  } finally {
    dom.window.close();
  }
});

test('Research cells receives background-only updates and retains its workspace across tab switches', async () => {
  const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
  const cell = 'c'.repeat(64),
    calls = [];
  const detail = {
    kind: 'cell',
    id: cell,
    verified: true,
    genesis: { question: 'Which method should be tested next?' },
    revision_history: [],
    related: { jobs: [] },
    related_coverage: {},
  };
  snapshot.research_tools = {
    configuration: { status: 'enabled', enabled: true },
    summary: { cells: 1, versions: 0 },
    cells: [
      {
        id: cell,
        question: detail.genesis.question,
        stage: 'research',
        scheduled: true,
        detail_version: 'same-checkpoint',
        affinities: [0],
      },
    ],
    jobs: { version: 'initial', items: [] },
  };
  const { dom, doc, streams, errors } = await mounted({
    tab: 'research-cells',
    fetchOverride: (url) => {
      if (url === '/api/runs/' + fixtureRun.id) return Promise.resolve(Response.json(snapshot));
      if (url.includes('/research-cells/')) {
        calls.push(url);
        return Promise.resolve(Response.json(detail));
      }
    },
  });
  try {
    await until(
      () => doc.querySelector('.rc-detail')?.textContent.includes('No background job'),
      'cell details loaded',
    );
    assert.equal(doc.getElementById('cells-tab-count').textContent, '1');
    const workspace = doc.querySelector('.research-cells'),
      pane = doc.querySelector('.rc-detail');
    const job = {
      id: 'j'.repeat(64),
      cell_id: cell,
      status: 'queued',
      requested: { cpu_seconds: 60, wall_seconds: 90 },
    };
    detail.related.jobs = [job];
    streams
      .at(-1)
      .runtime({
        run: { id: fixtureRun.id, status: 'running' },
        research_tool_jobs: { version: 'new-job', items: [job] },
      });
    await until(
      () => doc.querySelector('[data-section="jobs"]')?.textContent.includes('Queued'),
      'runtime-only jobs delivered to research cells',
    );
    assert.ok(
      calls.length >= 2,
      'mutable job status refreshes details without a checkpoint change',
    );
    assert.equal(doc.querySelector('.rc-detail'), pane);
    doc.getElementById('tab-events').click();
    doc.getElementById('tab-research-cells').click();
    assert.equal(doc.querySelector('.research-cells'), workspace);
    assert.equal(doc.querySelector('.rc-detail'), pane);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('Packings deep link loads only active geometry, survives polling, and opens the saved program', async () => {
  const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
  snapshot.content_version = 'packings-v1';
  const program = snapshot.trials.find((row) => row.code_available),
    programId = String(program.candidate_id || program.id),
    requests = [];
  const layout = {
    id: 'saved-invocation',
    program_id: programId,
    evaluation_id: 'evaluation-fixture',
    island_id: 0,
    iteration: 1,
    timestamp: '2026-09-20T09:00:00Z',
    valid: true,
    score: 0.2,
    source_sha256: 'a'.repeat(64),
    centers: [
      [0.2, 0.3],
      [0.7, 0.8],
    ],
    radii: [0.1, 0.1],
  };
  const { dom, w, doc, streams, errors } = await mounted({
    tab: 'packings',
    fetchOverride: (url) => {
      if (url === '/api/runs/' + fixtureRun.id) return Promise.resolve(Response.json(snapshot));
      if (url.includes('/packings?')) {
        requests.push(url);
        return Promise.resolve(
          Response.json({
            schema: 'sciel-packings/1',
            supported: true,
            total: 1,
            available: 1,
            unavailable: 0,
            offset: 0,
            limit: 120,
            has_more: false,
            content_version: snapshot.content_version,
            islands: [0],
            items: [layout],
          }),
        );
      }
    },
  });
  try {
    await until(() => doc.querySelector('.pg-tile'), 'deep-linked gallery loaded');
    assert.equal(doc.getElementById('tab-packings').getAttribute('aria-selected'), 'true');
    assert.equal(new URL(w.location.href).searchParams.get('tab'), 'packings');
    assert.equal(requests.length, 1);
    const tile = doc.querySelector('.pg-tile'),
      search = doc.querySelector('.pg-search');
    streams
      .at(-1)
      .runtime({
        run: { id: fixtureRun.id, status: 'running' },
        runtime: { active: true, stage: 'generating' },
      });
    await new Promise((r) => setTimeout(r, 30));
    assert.equal(requests.length, 1, 'runtime updates do not fetch geometry');
    snapshot.content_version = 'packings-v2';
    streams.at(-1).snapshot(snapshot);
    await until(() => requests.length === 2);
    assert.strictEqual(doc.querySelector('.pg-tile'), tile);
    assert.strictEqual(doc.querySelector('.pg-search'), search);
    doc.getElementById('tab-events').click();
    snapshot.content_version = 'packings-v3';
    streams.at(-1).snapshot(snapshot);
    await new Promise((r) => setTimeout(r, 30));
    assert.equal(requests.length, 2, 'inactive tab never fetches geometry');
    doc.getElementById('tab-packings').click();
    await until(() => requests.length === 3);
    doc.querySelector('.pg-tile').click();
    assert.equal(doc.querySelector('.pg-dialog').open, true);
    doc.querySelector('.pg-code').click();
    await until(
      () =>
        doc.getElementById('code-select')?.value === programId &&
        doc.querySelector('#code-body .code-meta'),
    );
    assert.equal(doc.getElementById('tab-code').getAttribute('aria-selected'), 'true');
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('overview Population stays beside search markup and opens existing full population and source views', async () => {
  const { dom, doc, streams, errors } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'population-preview-fixture';
    snapshot.population = {
      available: true,
      source: 'checkpoint',
      iteration: 5,
      island_count: 1,
      layout: { kind: 'map_elites', grid_bins: 10 },
      descriptor: { kind: 'code_length' },
      islands: [
        {
          id: 0,
          member_count: 1,
          members_available: true,
          grid_available: true,
          grid_cell_count: 1,
          members: [{ id: 'p3', score: 0.9, code_available: true }],
          grid: [
            {
              x: 2,
              y: 3,
              candidate_id: 'p3',
              score: 0.9,
              metric_display: measured(2.7, 0.9, 'Sum of radii'),
            },
          ],
        },
      ],
      archive: { count: 0, members: [] },
      storage: {
        schema: 'sciel-population-storage/1',
        kind: 'map_elites',
        label: 'MAP-Elites',
        iteration: 5,
        bins: { x: 10, y: 10 },
        projection: { available: false },
      },
    };
    streams.at(-1).snapshot(snapshot);
    assert.equal(
      doc.querySelector('.chart-panel').nextElementSibling.className,
      'panel population-preview-panel',
    );
    assert.equal(
      doc
        .querySelector('.overview-grid')
        .nextElementSibling.classList.contains('overview-activity'),
      true,
    );
    const preview = doc.querySelector('#population-preview .population-preview'),
      mark = preview.querySelector('.preview-mark');
    assert.ok(mark);
    assert.equal(mark.dataset.change, '');
    mark.dispatchEvent(new dom.window.Event('pointerenter', { bubbles: true }));
    assert.match(preview.querySelector('.preview-inspector').textContent, /2.700000/);
    preview.querySelector('.preview-full').click();
    assert.equal(doc.getElementById('tab-population').getAttribute('aria-selected'), 'true');
    assert.ok(
      doc.getElementById('population-map'),
      'complete population workspace remains available',
    );
    assert.equal(doc.querySelector('#population-preview .population-preview'), preview);
    preview.querySelector('.preview-program').click();
    await until(() => doc.querySelector('.code-view'), 'saved program source opens');
    assert.equal(doc.getElementById('tab-code').getAttribute('aria-selected'), 'true');
    assert.equal(doc.querySelector('#population-preview .preview-mark'), mark);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('headline separates known and AI search references without stale or mismatched gaps', async () => {
  const { dom, doc, streams } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    const update = (value) => {
      snapshot.stats.best_score = value / 2.635;
      snapshot.stats.best_metric_display = measured(
        value,
        snapshot.stats.best_score,
        'Sum of radii',
      );
      snapshot.benchmark.current_value = value;
      snapshot.benchmark.best_known.current_value = value;
      snapshot.benchmark.best_ai_method.current_value = value;
    };
    snapshot.benchmark = {
      metric: 'Sum of radii',
      value: 2.64,
      current_value: 2.62,
      run_tolerance: 1e-6,
      reference_tolerance: 1e-6,
      references: [],
      best_known: {
        status: 'known',
        label: 'Best known',
        name: 'Published witness',
        value: 2.64,
        tolerance: 1e-6,
        current_value: 2.62,
        source_url: 'https://example.org/known',
      },
      best_ai_method: {
        status: 'known',
        label: 'Best AI search',
        name: 'AI <script>method</script>',
        value: 2.63,
        tolerance: 1e-6,
        current_value: 2.62,
        source_url: 'https://example.org/ai',
      },
    };
    update(2.62);
    streams.at(-1).snapshot(snapshot);
    const headline = doc.getElementById('best-score-comparison');
    assert.equal(
      headline.querySelector('[data-reference-comparison="best-known"]').textContent,
      '| 0.7576% below best known',
    );
    assert.equal(
      headline.querySelector('[data-reference-comparison="ai-search"]').textContent,
      '| 0.3802% below best ai search',
    );
    assert.match(headline.lastElementChild.title, /https:\/\/example.org\/ai/);
    assert.equal(headline.querySelector('script'), null);
    update(2.65);
    streams.at(-1).snapshot(snapshot);
    assert.match(headline.textContent, /above best known.*above best ai search/);
    update(2.63);
    streams.at(-1).snapshot(snapshot);
    assert.match(headline.textContent, /matches best ai search/);
    update(2.63 - 1e-12);
    streams.at(-1).snapshot(snapshot);
    assert.match(headline.textContent, /<0\.000001% below best ai search/);
    snapshot.benchmark.best_ai_method.tolerance = 0;
    streams.at(-1).snapshot(snapshot);
    assert.match(headline.lastElementChild.textContent, /not available/);
    snapshot.benchmark.best_ai_method = {
      status: 'unavailable',
      reason: 'Method provenance not recorded',
    };
    streams.at(-1).snapshot(snapshot);
    assert.match(headline.lastElementChild.title, /Method provenance not recorded/);
    snapshot.benchmark.current_value = 1;
    streams.at(-1).snapshot(snapshot);
    assert.equal(headline.hidden, true);
    assert.equal(headline.textContent, '');
  } finally {
    dom.window.close();
  }
});
