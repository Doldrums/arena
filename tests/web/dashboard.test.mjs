// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { base, until, mounted, fixtureRun, runIndex } from './helpers/dashboard-fixture.mjs';
test('an unavailable run list offers a retry and recovers to the actual experiment', async () => {
  let unavailable = true;
  const { dom, doc, errors } = await mounted({
    fetchOverride: (url) =>
      url === '/api/runs' && unavailable
        ? Promise.resolve(new Response('{}', { status: 503 }))
        : undefined,
    ready: (doc) => !doc.querySelector('#error-banner').hidden,
  });
  try {
    assert.equal(doc.querySelector('.footer-note').textContent, 'Run monitor');
    assert.match(doc.querySelector('#run-list').textContent, /Run list unavailable/);
    assert.doesNotMatch(doc.querySelector('#run-list').textContent, /Loading run logs/);
    assert.equal(doc.querySelector('#empty-state').hidden, false);
    assert.match(doc.querySelector('#empty-title').textContent, /temporarily unavailable/);
    assert.equal(doc.querySelector('#empty-help').hidden, true);
    assert.equal(doc.querySelector('#empty-retry').hidden, false);
    unavailable = false;
    doc.querySelector('#empty-retry').click();
    await until(
      () =>
        doc.querySelector('#evaluations').textContent === '4' &&
        doc.querySelector('#connection').textContent === 'Connected',
      'retry loads experiment',
    );
    assert.equal(doc.querySelector('#empty-state').hidden, true);
    assert.equal(doc.querySelector('#dashboard').hidden, false);
    assert.equal(doc.querySelector('#error-banner').hidden, true);
    assert.ok(doc.querySelectorAll('.run-item').length > 0);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('recovery to an empty run list restores the waiting state and clears the error', async () => {
  let unavailable = true;
  const { dom, doc, errors } = await mounted({
    fetchOverride: (url) =>
      url === '/api/runs'
        ? Promise.resolve(
            new Response(JSON.stringify(unavailable ? {} : { runs: [] }), {
              status: unavailable ? 503 : 200,
            }),
          )
        : undefined,
    ready: (doc) => !doc.querySelector('#error-banner').hidden,
  });
  try {
    unavailable = false;
    doc.querySelector('#empty-retry').click();
    await until(
      () => doc.querySelector('#connection').textContent === 'Waiting for a run',
      'empty list reconnects',
    );
    assert.equal(doc.querySelector('#empty-state').hidden, false);
    assert.equal(doc.querySelector('#empty-title').textContent, 'Watch your search unfold');
    assert.equal(doc.querySelector('#empty-help').hidden, false);
    assert.equal(doc.querySelector('#empty-retry').hidden, true);
    assert.equal(doc.querySelector('#error-banner').hidden, true);
    assert.match(doc.querySelector('#run-list').textContent, /No runs yet/);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('a later list failure preserves the displayed experiment and retry clears the stale error', async () => {
  let unavailable = false;
  const { dom, doc, errors } = await mounted({
    fetchOverride: (url) =>
      url === '/api/runs' && unavailable
        ? Promise.resolve(new Response('{}', { status: 503 }))
        : undefined,
  });
  try {
    await until(
      () => doc.querySelector('#connection').textContent === 'Connected',
      'initial stream connected',
    );
    // Pause so a successful SSE event cannot conceal the list error under test.
    doc.querySelector('#follow-button').click();
    const score = doc.querySelector('#best-score').textContent;
    const runCount = doc.querySelectorAll('.run-item').length;
    unavailable = true;
    doc.querySelector('#refresh-button').click();
    await until(
      () =>
        !doc.querySelector('#refresh-button').disabled &&
        !doc.querySelector('#error-banner').hidden,
      'later list failure',
    );
    assert.equal(doc.querySelector('#dashboard').hidden, false);
    assert.equal(doc.querySelector('#empty-state').hidden, true);
    assert.equal(doc.querySelector('#best-score').textContent, score);
    assert.equal(doc.querySelectorAll('.run-item').length, runCount);
    unavailable = false;
    doc.querySelector('#refresh-button').click();
    await until(
      () =>
        !doc.querySelector('#refresh-button').disabled && doc.querySelector('#error-banner').hidden,
      'retry clears list error',
    );
    assert.equal(doc.querySelector('#best-score').textContent, score);
    assert.equal(doc.querySelector('#connection').textContent, 'Updates paused');
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('failed run switch clears previous metrics, plot and runtime and ignores the closed stream', async () => {
  const { dom, w, doc, streams, errors } = await mounted();
  try {
    const oldStream = streams.at(-1);
    const target = runIndex.find((run) => run.id !== fixtureRun.id);
    w.fetch = (url) =>
      String(url) === '/api/runs/' + encodeURIComponent(target.id)
        ? Promise.resolve(new Response('', { status: 503 }))
        : fetch(new URL(url, base));
    doc.querySelector('[data-run="' + target.id + '"]').click();
    assert.equal(doc.getElementById('best-score').textContent, '—');
    assert.equal(doc.getElementById('cost').textContent, '—');
    assert.equal(doc.querySelector('#score-chart svg'), null);
    assert.equal(doc.getElementById('runtime-bar').hidden, true);
    await until(
      () => doc.getElementById('tab-content').textContent.includes('Unable to load this run'),
      'run error displayed',
    );
    assert.match(doc.getElementById('error-banner').textContent, /503/);
    oldStream.dispatchEvent(new w.Event('unavailable'));
    assert.match(doc.getElementById('error-banner').textContent, /503/);
    assert.doesNotMatch(doc.getElementById('error-banner').textContent, /no longer available/);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('default selection prefers a verified live run and then recent output, while explicit archives stay accessible', async () => {
  const original = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
  const active = {
    ...fixtureRun,
    id: 'live-test',
    name: 'Live experiment',
    path: 'outputs/live-test/run.jsonl',
    status: 'running',
    last_modified: '2026-09-19T12:00:00Z',
  };
  const recent = {
    ...fixtureRun,
    id: 'output-test',
    name: 'Latest experiment',
    path: 'outputs/latest/run.jsonl',
    status: 'completed',
    last_modified: '2026-09-19T13:00:00Z',
  };
  for (const includeLive of [true, false]) {
    const runs = [
      { ...fixtureRun, last_modified: '2026-09-19T14:00:00Z' },
      recent,
      ...(includeLive ? [active] : []),
    ];
    const { dom, w, doc, streams } = await mounted({
      runId: null,
      fetchOverride: (url) => {
        if (url === '/api/runs') return Promise.resolve(Response.json({ runs }));
        const chosen = runs.find((run) => url === '/api/runs/' + run.id);
        if (chosen)
          return Promise.resolve(Response.json({ ...structuredClone(original), run: chosen }));
      },
    });
    try {
      assert.equal(
        new URL(w.location.href).searchParams.get('run'),
        includeLive ? 'live-test' : 'output-test',
      );
      assert.equal(doc.querySelectorAll('[data-run]').length, runs.length);
      doc.querySelector('[data-run="' + fixtureRun.id + '"]').click();
      await until(
        () =>
          doc.getElementById('run-title').textContent.includes('Synthetic study') &&
          doc.getElementById('best-score').textContent === 'Not measured' &&
          streams.at(-1).url.includes(fixtureRun.id),
        'archive still selectable',
      );
      assert.equal(new URL(w.location.href).searchParams.get('run'), fixtureRun.id);
    } finally {
      dom.window.close();
    }
  }
});
