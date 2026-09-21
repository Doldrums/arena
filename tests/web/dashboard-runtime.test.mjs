// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  base,
  chart,
  architecture,
  measured,
  until,
  mounted,
  fixtureRun,
} from './helpers/dashboard-fixture.mjs';
test('parallel execution runtime updates preserve recorded architecture and pending queue semantics', async () => {
  const { dom, doc, streams, errors } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'parallel-ui-fixture';
    snapshot.runtime = {
      available: true,
      active: true,
      stage: 'generating',
      parallel: {
        schema: 'sciel-parallel-runtime/1',
        wave: 3,
        phase: 'generation',
        workers: 4,
        jobs: 4,
        pending_llm_calls: 2,
        pending_evaluations: 1,
      },
    };
    snapshot.architecture.sections = snapshot.architecture.sections.filter(
      (section) => section.id !== 'execution',
    );
    snapshot.architecture.sections.push({
      id: 'execution',
      title: 'Execution and shared resource limits',
      fields: [
        {
          key: 'parallel_search.workers',
          label: 'Concurrent jobs per run',
          value: 4,
          status: 'recorded',
        },
        {
          key: 'parallel_search.host_evaluator_slots',
          label: 'Shared host evaluator slots',
          value: 2,
          status: 'recorded',
        },
      ],
    });
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-architecture').click();
    assert.match(doc.querySelector('[data-field="parallel_search.workers"]').textContent, /4/);
    assert.match(
      doc.getElementById('runtime-bar').textContent,
      /Wave 3 · generation · 4 workers · pending LLM 2 \/ evaluation 1/,
    );
    const configuration = doc.querySelector('.architecture-configuration');
    configuration.open = true;
    streams
      .at(-1)
      .runtime({
        run: { id: fixtureRun.id, status: 'running' },
        runtime: {
          available: true,
          active: true,
          stage: 'research',
          parallel: {
            schema: 'sciel-parallel-runtime/1',
            wave: 3,
            phase: 'conclusion',
            workers: 4,
            jobs: 4,
            pending_llm_calls: 3,
            pending_evaluations: 0,
          },
        },
      });
    assert.equal(doc.querySelector('.architecture-configuration'), configuration);
    assert.equal(configuration.open, true);
    assert.match(
      doc.getElementById('runtime-bar').textContent,
      /Wave 3 · conclusion · 4 workers · pending LLM 3 \/ evaluation 0/,
    );
    assert.match(doc.querySelector('.runtime-parallel').title, /not measured executing/);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('session clocks tick only while live, freeze when paused and reset honestly on resume', async () => {
  let now = 0,
    tick;
  const { dom, doc, streams, errors } = await mounted({
    configure: (w) => {
      Object.defineProperty(w.performance, 'now', { value: () => now });
      const interval = w.setInterval.bind(w);
      w.setInterval = (fn, ms) => (ms === 1000 ? ((tick = fn), 1) : interval(fn, ms));
    },
  });
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'live-timing';
    snapshot.runtime = {
      available: true,
      active: true,
      stage: 'generating',
      heartbeat_age_seconds: 2,
      stale_after_seconds: 10,
    };
    snapshot.run.status = 'running';
    snapshot.timing = {
      live: true,
      session: { elapsed_seconds: 60 },
      last_hypothesis_age_seconds: 5,
      last_hypothesis_id: 'r1',
      intervals: { count: 1, last_seconds: 20, median_seconds: 20, source: 'recorded_monotonic' },
      hypotheses: [{ experiment_id: 'r1', source: 'recorded' }],
      coverage: { gaps: [] },
    };
    streams.at(-1).snapshot(snapshot);
    const plot = doc.querySelector('#score-chart svg');
    now = 2500;
    tick();
    assert.equal(doc.getElementById('run-elapsed').textContent, '00:01:02');
    assert.equal(doc.getElementById('hypothesis-age').textContent, '00:00:07');
    assert.equal(doc.querySelector('#score-chart svg'), plot, 'clock tick does not redraw plot');
    now = 20000;
    tick();
    assert.equal(
      doc.getElementById('run-elapsed').textContent,
      '00:01:08',
      'stale heartbeat bounds extrapolation',
    );
    streams
      .at(-1)
      .runtime({
        run: { id: fixtureRun.id, status: 'paused' },
        runtime: { available: true, active: false },
        timing: { live: false, session: { elapsed_seconds: 65 }, last_hypothesis_age_seconds: 10 },
      });
    now = 30000;
    tick();
    assert.equal(doc.getElementById('run-elapsed').textContent, '00:01:05');
    assert.equal(doc.getElementById('hypothesis-age').textContent, '00:00:10');
    assert.match(doc.getElementById('timing-note').textContent, /frozen/);
    streams
      .at(-1)
      .runtime({
        run: { id: fixtureRun.id, status: 'running' },
        runtime: snapshot.runtime,
        timing: {
          live: true,
          session: { elapsed_seconds: 2 },
          last_hypothesis_age_seconds: null,
          last_hypothesis_id: null,
          intervals: {
            count: 1,
            last_seconds: null,
            median_seconds: 20,
            source: 'recorded_monotonic',
          },
        },
      });
    assert.equal(
      doc.getElementById('last-hypothesis-id').textContent,
      'Not recorded in this session',
    );
    assert.equal(doc.getElementById('hypothesis-age').textContent, '—');
    assert.equal(doc.getElementById('hypothesis-interval').textContent, '—');
    now = 33000;
    tick();
    assert.equal(doc.getElementById('run-elapsed').textContent, '00:00:05');
    doc.getElementById('follow-button').click();
    now = 35000;
    tick();
    assert.equal(
      doc.getElementById('run-elapsed').textContent,
      '00:00:05',
      'pausing the view freezes its clock',
    );
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('stream updates are safe, pauseable, preserve selection, and do not execute research text', async () => {
  const { dom, w, doc, errors, streams } = await mounted();
  try {
    const id = new URL(w.location.href).searchParams.get('run');
    const snapshot = await (await fetch(base + '/api/runs/' + id)).json();
    doc.getElementById('tab-hypotheses').click();
    const injected = structuredClone(snapshot);
    injected.hypotheses[0].hypothesis.text = '<img src=x onerror="window.owned=true">';
    injected.stats.best_score = 0.94;
    injected.stats.best_metric_display = measured(0.94);
    streams.at(-1).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent, '0.940000');
    assert.equal(doc.querySelectorAll('.research-card img').length, 0);
    assert.match(doc.getElementById('tab-content').textContent, /<img src=x/);
    assert.equal(w.owned, undefined);
    assert.equal(doc.getElementById('tab-hypotheses').getAttribute('aria-selected'), 'true');
    doc.getElementById('follow-button').click();
    assert.equal(streams.at(-1).closed, true);
    assert.match(doc.getElementById('connection').textContent, /paused/);
    injected.stats.best_score = 0.95;
    injected.stats.best_metric_display = measured(0.95);
    streams.at(-1).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent, '0.940000');
    doc.getElementById('follow-button').click();
    assert.equal(streams.at(-1).closed, false);
    // A queued frame from a closed connection cannot overwrite newer state.
    streams.at(-2).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent, '0.940000');
    streams.at(-1).snapshot(injected);
    assert.equal(doc.getElementById('best-score').textContent, '0.950000');
    doc.querySelector('[data-axis="cost_total"]').click();
    assert.match(doc.querySelector('#chart-outcomes summary').textContent, /unavailable/);
    doc.getElementById('run-search').value = 'cards_off';
    doc.getElementById('run-search').dispatchEvent(new w.Event('input'));
    assert.equal(doc.querySelectorAll('[data-run]').length, 2);
    doc.querySelector('[data-run]').click();
    await until(() => doc.getElementById('run-title').textContent.includes('OFF'), 'run switched');
    await until(
      () => streams.at(-1).url.includes(new URL(w.location.href).searchParams.get('run')),
      'new run loaded',
    );
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('runtime-only heartbeats preserve the source view and scroll position', async () => {
  const { dom, doc, streams } = await mounted();
  try {
    doc.querySelector('[data-candidate="p3"]').click();
    await until(() => doc.querySelector('.code-view'), 'source view loaded');
    const view = doc.querySelector('.code-view');
    view.scrollTop = 90;
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.runtime = {
      available: true,
      status: 'running',
      stage: 'evaluating',
      active: true,
      heartbeat_age_seconds: 1,
      pid: 12345,
    };
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelector('.code-view'), view);
    assert.equal(doc.querySelector('.code-view').scrollTop, 90);
    assert.match(doc.getElementById('runtime-bar').textContent, /Evaluating a candidate/);
  } finally {
    dom.window.close();
  }
});

test('runtime events update status without replacing source, chart, or architecture nodes', async () => {
  const { dom, doc, streams } = await mounted();
  try {
    doc.querySelector('[data-candidate="p3"]').click();
    await until(() => doc.querySelector('.code-view'), 'source view loaded');
    const source = doc.querySelector('.code-view'),
      chart = doc.querySelector('#score-chart svg');
    source.scrollTop = 75;
    const update = {
      run: { id: fixtureRun.id, status: 'running', status_reason: null },
      runtime: { available: true, active: true, stage: 'evaluating', heartbeat_age_seconds: 1 },
    };
    streams.at(-1).runtime(update);
    assert.equal(doc.querySelector('.code-view'), source);
    assert.equal(source.scrollTop, 75);
    assert.equal(doc.querySelector('#score-chart svg'), chart);
    assert.match(doc.getElementById('run-status').textContent, /Running/);
    doc.getElementById('tab-architecture').click();
    const architecture = doc.querySelector('.architecture');
    update.runtime.stage = 'generating';
    streams.at(-1).runtime(update);
    assert.equal(doc.querySelector('.architecture'), architecture);
    assert.ok(doc.querySelector('.architecture-node[data-node="generation"].current'));
    update.run.status = 'stopped';
    update.runtime.active = false;
    update.runtime.stage = 'finished';
    streams.at(-1).runtime(update);
    assert.match(doc.getElementById('run-status').textContent, /Stopped/);
    assert.equal(doc.querySelector('.architecture-stage.current'), null);
    streams.at(-1).runtime({ ...update, run: { id: 'other-run', status: 'running' } });
    assert.match(doc.getElementById('run-status').textContent, /Stopped/);
  } finally {
    dom.window.close();
  }
});
