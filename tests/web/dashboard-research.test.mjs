// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { base, until, mounted, fixtureRun } from './helpers/dashboard-fixture.mjs';
test('Work Flow opens endpoint evidence and preserves the conversation on a dashboard refresh', async () => {
  const feed = await (
    await fetch(base + '/api/runs/' + fixtureRun.id + '/workflow?limit=60&actor=all')
  ).json();
  assert.ok(feed.items.length, 'fixture supplies workflow activity');
  const event = feed.items.find((item) => item.details_available !== false);
  assert.ok(event, 'fixture has inspectable evidence');
  const evidence = await (
    await fetch(base + '/api/runs/' + fixtureRun.id + '/workflow/' + encodeURIComponent(event.id))
  ).json();
  assert.ok(evidence.sections.length, 'the HTTP fixture returns inspectable sections');
  const { dom, doc, streams, errors } = await mounted();
  try {
    doc.querySelector('#tab-workflow').click();
    await until(() => doc.querySelectorAll('.wf-message').length > 0, 'workflow messages loaded');
    const message = [...doc.querySelectorAll('.wf-message')].find(
      (node) => node.dataset.eventId === event.id,
    );
    assert.ok(message, 'the saved event appears in the conversation');
    assert.equal(doc.querySelector('#tab-workflow').getAttribute('aria-selected'), 'true');
    assert.equal(message.querySelector('.wf-title').textContent, event.title);
    if (event.timestamp)
      assert.equal(message.querySelector('time').dateTime, new Date(event.timestamp).toISOString());
    const disclosure = message.querySelector('.wf-inspect');
    disclosure.open = true;
    await until(() => message.querySelector('.wf-section'), 'saved workflow evidence expanded');
    assert.equal(message.querySelector('.wf-section-name').textContent, evidence.sections[0].label);
    assert.equal(message.querySelector('.wf-raw').textContent, evidence.sections[0].text);
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.content_version = 'workflow-refresh-fixture';
    streams.at(-1).snapshot(snapshot);
    await until(
      () => doc.querySelector('.wf-refresh')?.disabled === false,
      'workflow refresh finished',
    );
    assert.equal(
      [...doc.querySelectorAll('.wf-message')].find((node) => node.dataset.eventId === event.id),
      message,
    );
    assert.equal(disclosure.open, true);
    doc.querySelector('#follow-button').click();
    assert.equal(doc.querySelector('.wf-connection').textContent, 'Updates paused');
    doc.querySelector('#tab-events').click();
    assert.equal(doc.querySelector('.workflow'), null);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('invalid conclusions and rejected reflections never appear as successful knowledge revisions', async () => {
  const { dom, doc, streams } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    // Matches live sciel-research/12 outcomes, including parsed JSON rejected by admission.
    const cases = [
      ['conclusion', { status: 'invalid', llm: null, accepted_lesson_ids: [], lesson_error: null }],
      [
        'reflection',
        {
          status: 'parsed',
          applied: null,
          changed: false,
          error: 'ValueError',
          error_detail: 'retirement requires a replacement preserving scope, polarity and evidence',
        },
      ],
      [
        'conclusion',
        {
          status: 'parsed',
          llm: { explanation: 'Measured outcome recorded' },
          verdict_matches_observation: true,
          accepted_lesson_ids: [],
          lesson_error: null,
        },
      ],
      [
        'reflection',
        {
          status: 'parsed',
          applied: { lesson_ids: ['l1'], retired_ids: [] },
          changed: true,
          error: null,
        },
      ],
      [
        'reflection',
        {
          status: 'parsed',
          applied: { lesson_ids: [], retired_ids: [] },
          changed: false,
          error: null,
        },
      ],
      [
        'conclusion',
        {
          status: 'parsed',
          llm: { explanation: 'Invalid lesson evidence' },
          accepted_lesson_ids: [],
          lesson_error: 'ValueError',
        },
      ],
      ['reflection', { status: 'invalid', applied: null, changed: false, error: null }],
    ];
    snapshot.events = cases.map(([phase, data], index) => ({
      event: 'research',
      phase,
      seq: index + 1,
      data,
    }));
    snapshot.stats.reflections = 4;
    streams.at(-1).snapshot(snapshot);
    const activity = (seq) => doc.querySelector('.activity-item[data-event-seq="' + seq + '"]');
    assert.match(doc.getElementById('hypotheses-count').textContent, /4 reflection attempts/);
    assert.doesNotMatch(doc.getElementById('hypotheses-count').textContent, /revisions/);
    for (const [seq, title] of [
      [1, 'Conclusion invalid'],
      [2, 'Reflection rejected'],
      [6, 'Conclusion rejected'],
      [7, 'Reflection invalid'],
    ]) {
      assert.equal(activity(seq).querySelector('.activity-title').textContent, title);
      assert.equal(activity(seq).querySelector('.activity-icon.green'), null);
      assert.equal(activity(seq).querySelector('.activity-icon').textContent, '!');
    }
    assert.equal(activity(4).querySelector('.activity-title').textContent, 'Knowledge revised');
    assert.equal(
      activity(5).querySelector('.activity-title').textContent,
      'Reflection accepted · no change',
    );
    assert.equal(doc.querySelectorAll('.activity-icon.green').length, 3);
    assert.match(
      activity(2).querySelector('.activity-subtitle').textContent,
      /retirement requires a replacement/,
    );
    doc.getElementById('tab-events').click();
    assert.equal(
      doc.querySelector('[data-seq="2"] .event-title').textContent,
      'Reflection rejected',
    );
    assert.equal(
      doc.querySelector('[data-seq="1"] .event-title').textContent,
      'Conclusion invalid',
    );
  } finally {
    dom.window.close();
  }
});

test('methods snapshots select a dedicated lab view and returning to an engine restores its metrics', async () => {
  const { dom, doc, streams, errors } = await mounted();
  try {
    const engine = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    streams
      .at(-1)
      .snapshot({
        kind: 'methods',
        content_version: 'methods-kind-switch',
        run: {
          id: fixtureRun.id,
          name: 'Research practices pilot',
          path: 'outputs/methods-pilot',
          kind: 'methods',
          status: 'running',
        },
        runtime: { active: true, stale_after_seconds: 30, heartbeat_age_seconds: 0 },
        timing: { session: { elapsed_seconds: 8 } },
        methods: {
          summary: { labs: 1, methods: 0, experiments: 0, proposals: 0, invocations: 0 },
          labs: [{ id: 'C-1', mode: 'C', active_methods: [], active_adapters: [], steps: 0 }],
          tools: [],
          experiments: [],
          proposals: [],
          transfers: [],
          events: [],
          budget: { spent: { dollars: 0 }, reserved: {}, limits: {} },
        },
      });
    assert.equal(doc.getElementById('dashboard').dataset.kind, 'methods');
    assert.equal(doc.getElementById('methods-dashboard').hidden, false);
    assert.match(doc.getElementById('methods-dashboard').textContent, /Research labs/);
    assert.match(doc.getElementById('run-title').textContent, /Research practices pilot/);
    assert.match(doc.querySelector('.methods-lab').textContent, /C-1/);
    streams
      .at(-1)
      .runtime({
        run: { id: fixtureRun.id, kind: 'methods', status: 'completed' },
        runtime: { active: false, elapsed_seconds: 12 },
        timing: { live: false, session: { elapsed_seconds: 12 } },
      });
    assert.match(doc.getElementById('run-status').textContent, /Completed/);
    assert.equal(doc.querySelector('[data-methods-elapsed]').textContent, '00:00:12');
    streams.at(-1).snapshot(engine);
    assert.equal(doc.getElementById('dashboard').dataset.kind, 'engine');
    assert.equal(doc.getElementById('methods-dashboard').hidden, true);
    assert.equal(doc.getElementById('best-score').textContent, 'Not measured');
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('native Tool library preserves original metrics and source while exposing recorded events and architecture', async () => {
  const tool = 'a'.repeat(64),
    paths = [];
  const { dom, doc, streams, errors } = await mounted({
    fetchOverride: (url) => {
      if (url.includes('/research-tools/')) {
        paths.push(url);
        return Promise.resolve({
          ok: true,
          json: async () => ({
            verified: true,
            files: { 'tool.py': 'def run(inputs):\n    return {"observed": 0}\n' },
            manifest: { name: 'Recorded helper' },
            parents: [],
          }),
        });
      }
    },
  });
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    const evaluations = doc.getElementById('evaluations').textContent;
    snapshot.content_version = 'tool-fixture-1';
    snapshot.research_tools = {
      available: true,
      configured: { enabled: true, share_between_islands: true },
      summary: {
        versions: 1,
        published: 1,
        actual_invocations: 0,
        foreign_invocations: 0,
        linked_programs: 0,
      },
      versions: [
        {
          id: tool,
          name: 'Recorded helper',
          author_island_id: 0,
          status: 'published',
          invocations: 0,
          foreign_invocations: 0,
          used_by: [],
        },
      ],
      events: [],
    };
    snapshot.events.push({
      event: 'research_tool',
      phase: 'published',
      seq: 999,
      data: { phase: 'published', tool_id: tool },
    });
    snapshot.architecture.graph.nodes.push(
      {
        id: 'tool_library',
        label: 'Shared tool library',
        kind: 'knowledge',
        detail: 'Published versions are available to islands; availability is not use.',
      },
      {
        id: 'tool_execution',
        label: 'Isolated tool calls',
        kind: 'rule',
        detail: 'Prepared Snapshot context does not prove prompt delivery.',
      },
    );
    snapshot.architecture.graph.edges.push(
      { from: 'tool_library', to: 'tool_execution', label: 'Explicit version invocation' },
      {
        from: 'tool_execution',
        to: 'generation',
        label: 'Prepared Snapshot context',
        kind: 'knowledge',
      },
    );
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-tools').click();
    assert.equal(doc.getElementById('evaluations').textContent, evaluations);
    assert.equal(doc.getElementById('tools-tab-count').textContent, '1');
    assert.match(doc.getElementById('activity-feed').textContent, /Tool published for sharing/);
    doc.querySelector('.tool-name button').click();
    await until(() => doc.querySelector('.tool-raw'));
    const source = doc.querySelector('.tool-raw');
    source.scrollTop = 21;
    source.focus();
    snapshot.content_version = 'tool-fixture-2';
    snapshot.research_tools.versions[0].invocations = 1;
    streams.at(-1).snapshot(snapshot);
    assert.strictEqual(doc.querySelector('.tool-raw'), source);
    assert.strictEqual(doc.activeElement, source);
    assert.equal(paths.length, 1);
    doc.getElementById('tab-architecture').click();
    doc.querySelector('[data-node="tool_execution"]').click();
    assert.match(
      doc.querySelector('.graph-inspector').textContent,
      /does not prove prompt delivery/,
    );
    doc.getElementById('tab-tools').click();
    assert.strictEqual(doc.querySelector('.tool-raw'), source);
    assert.equal(source.scrollTop, 21);
    assert.equal(errors.length, 0);
  } finally {
    dom.window.close();
  }
});

test('Research cells deep link distinguishes disabled configuration and retains ordinary search metrics', async () => {
  const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
  snapshot.research_tools = {
    configuration: { status: 'disabled', enabled: false },
    configured: { enabled: false },
    summary: { cells: 0, versions: 0 },
    cells: [],
  };
  const { dom, w, doc, errors } = await mounted({
    tab: 'research-cells',
    fetchOverride: (url) => {
      if (url === '/api/runs/' + fixtureRun.id) return Promise.resolve(Response.json(snapshot));
    },
  });
  try {
    assert.equal(doc.getElementById('tab-research-cells').getAttribute('aria-selected'), 'true');
    assert.equal(
      doc.getElementById('tab-research-cells').previousElementSibling.id,
      'tab-packings',
    );
    assert.match(doc.querySelector('.research-cells').textContent, /disabled for this run/);
    assert.match(doc.querySelector('.research-cells').textContent, /VQ/);
    assert.equal(doc.getElementById('cells-tab-count').textContent, '0');
    assert.equal(doc.getElementById('evaluations').textContent, '4');
    assert.ok(doc.getElementById('score-chart'));
    doc.getElementById('tab-events').click();
    assert.equal(new URL(w.location.href).searchParams.get('tab'), 'events');
    assert.equal(new URL(w.location.href).searchParams.get('run'), fixtureRun.id);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});
