// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { base, until, mounted, fixtureRun, runIndex } from './helpers/dashboard-fixture.mjs';
test('architecture shows recorded options, zero values, unknowns and verified runtime without executing text', async () => {
  const { dom, doc, streams, errors } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    snapshot.architecture = {
      schema: 'sciel-architecture/1',
      source: 'run_start.config',
      recorded: true,
      summary: 'Actual configuration of the selected run.',
      stages: [
        {
          id: 'selection',
          label: 'Select parent',
          status: 'enabled',
          description: 'Sample from the population',
        },
        {
          id: 'generation',
          label: 'Generate program',
          status: 'enabled',
          description: 'Use the recorded model',
        },
        {
          id: 'evaluation',
          label: 'Evaluate',
          status: 'enabled',
          description: 'Measure the candidate',
        },
        {
          id: 'admission',
          label: 'Update population',
          status: 'enabled',
          description: 'Retain eligible candidates',
        },
        ...['conclusion', 'reflection', 'retrieval'].map((id) => ({
          id,
          label: id,
          status: 'disabled',
          description: 'Optional research stage',
        })),
      ],
      edges: [{ from: 'generation', to: 'evaluation', label: 'candidate' }],
      sections: [
        {
          id: 'population',
          title: 'Population',
          fields: [
            {
              key: 'capacity',
              label: 'Capacity',
              value: 0,
              status: 'recorded',
              source: 'run_start.config',
            },
            { key: 'dynamic', label: 'Dynamic islands', value: false, status: 'recorded' },
            { key: 'unknown', label: 'Unrecorded option', value: null, status: 'unknown' },
            ...['budget', 'max_iterations', 'research.max_aux_calls'].map((key) => ({
              key,
              label: key,
              value: null,
              status: 'recorded',
            })),
            { key: 'research.model', label: 'Dedicated model', value: null, status: 'recorded' },
            {
              key: 'unsafe',
              label: 'Recorded model',
              value: '<img src=x onerror="window.owned=true">',
              status: 'recorded',
            },
          ],
        },
      ],
      warnings: ['Only recorded values are shown.'],
    };
    snapshot.runtime = {
      available: true,
      status: 'running',
      stage: 'generating',
      active: true,
      heartbeat_at: new Date().toISOString(),
      heartbeat_age_seconds: 2,
      pid: 12345,
      reason: 'Verified local engine process',
    };
    snapshot.run.status = 'running';
    snapshot.stats.cost_status = 'estimated';
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-architecture').click();
    assert.equal(doc.querySelectorAll('.architecture-stage').length, 7);
    assert.equal(doc.querySelectorAll('.architecture-stage.disabled').length, 3);
    assert.ok(doc.querySelector('[data-stage="generation"].current'));
    assert.equal(doc.querySelector('[data-field="capacity"] dd').textContent, '0');
    assert.equal(doc.querySelector('[data-field="dynamic"] dd').textContent, 'Disabled');
    assert.equal(doc.querySelector('[data-field="unknown"] dd').textContent, 'Not recorded');
    for (const key of ['budget', 'max_iterations', 'research.max_aux_calls'])
      assert.equal(doc.querySelector('[data-field="' + key + '"] dd').textContent, 'Unlimited');
    assert.equal(doc.querySelector('[data-field="research.model"] dd').textContent, 'Not set');
    assert.equal(doc.querySelectorAll('.architecture img').length, 0);
    assert.match(doc.querySelector('[data-field="unsafe"]').textContent, /<img src=x/);
    assert.match(doc.getElementById('runtime-bar').textContent, /Generating a candidate/);
    assert.match(doc.getElementById('runtime-bar').textContent, /Heartbeat 2s ago/);
    assert.match(doc.getElementById('cost-note').textContent, /Estimated/);
    snapshot.runtime.active = false;
    snapshot.runtime.stage = 'finished';
    snapshot.run.status = 'completed';
    streams.at(-1).snapshot(snapshot);
    assert.equal(doc.querySelector('.architecture-stage.current'), null);
    assert.equal(doc.querySelector('.runtime-indicator.live'), null);
    assert.match(doc.getElementById('runtime-bar').textContent, /Run finished/);
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});

test('architecture graph traces recorded run mechanisms with keyboard selection and stable runtime phases', async () => {
  const { dom, w, doc, streams, errors } = await mounted();
  try {
    const snapshot = await (await fetch(base + '/api/runs/' + fixtureRun.id)).json();
    const unsafe = '<img src=x onerror="window.owned=true">';
    const node = (id, label, kind = 'core', extra = {}) => ({
      id,
      label,
      subtitle: 'Recorded ' + id,
      kind,
      status: 'enabled',
      detail: label + ' role for this run.',
      features: [],
      ...extra,
    });
    const graph = {
      nodes: [
        node('parent', 'Novelty-chain parent', 'rule'),
        node('operator', 'Choose operator'),
        node('operator_bandit', 'Adaptive operator bandit', 'online', {
          features: ['Window max reward', unsafe],
        }),
        node('generation', 'Generate with model A', 'core', {
          phase: 'generating',
          subtitle: 'Provider / model A',
          detail: 'Recorded model A. ' + unsafe,
        }),
        node('evaluation', 'Evaluate the candidate', 'core', { phase: 'evaluating' }),
        node('population', 'Population archive'),
        node('reward', 'Improvement reward', 'core'),
        node('conclusion', 'Conclusion', 'knowledge', { phase: 'research' }),
        node('reflection', 'Reflection', 'knowledge', { phase: 'research' }),
        node('memory', 'Research memory', 'knowledge'),
        node('descriptor', unsafe, 'frozen', { subtitle: unsafe, detail: unsafe }),
      ],
      edges: [
        { from: 'parent', to: 'operator', label: 'Parent identity', kind: 'flow' },
        {
          from: 'operator_bandit',
          to: 'operator',
          label: 'Operator sampling weights',
          kind: 'control',
        },
        { from: 'operator', to: 'generation', label: 'Selected generation operator', kind: 'flow' },
        { from: 'generation', to: 'evaluation', label: 'Candidate source', kind: 'flow' },
        { from: 'evaluation', to: 'population', label: 'Measured score', kind: 'flow' },
        { from: 'evaluation', to: 'reward', label: 'Measured improvement', kind: 'reward' },
        {
          from: 'reward',
          to: 'operator_bandit',
          label: 'Eligible island improvement',
          kind: 'reward',
        },
        { from: 'evaluation', to: 'conclusion', label: 'Observed evidence', kind: 'knowledge' },
        { from: 'conclusion', to: 'reflection', label: 'Tested conclusions', kind: 'knowledge' },
        { from: 'reflection', to: 'memory', label: unsafe, kind: 'knowledge' },
        { from: 'memory', to: 'generation', label: 'Retrieved lessons', kind: 'knowledge' },
      ],
      inactive: [{ id: 'mode_mlp', label: 'Mode MLP', status: 'disabled', detail: unsafe }],
      summary: ['Model A · recorded selection policy', unsafe],
      notes: [unsafe],
    };
    snapshot.content_version = 'architecture-graph-a';
    snapshot.architecture = {
      schema: 'sciel-architecture/2',
      source: 'run_start.config',
      recorded: true,
      summary: 'Mechanisms recorded for this run.',
      graph,
      stages: [],
      edges: [],
      sections: [],
      warnings: [],
    };
    snapshot.run.status = 'running';
    snapshot.runtime = {
      available: true,
      active: true,
      status: 'running',
      stage: 'generating',
      heartbeat_age_seconds: 1,
    };
    streams.at(-1).snapshot(snapshot);
    doc.getElementById('tab-architecture').click();
    const map = doc.querySelector('.architecture-map');
    const getNode = (id) => doc.querySelector('.architecture-node[data-node="' + id + '"]');
    assert.ok(map);
    assert.equal(doc.querySelectorAll('.architecture-node').length, graph.nodes.length);
    assert.deepEqual(
      [...map.querySelectorAll('.arch-pipeline > .arch-step .arch-step-heading h4')].map(
        (el) => el.textContent,
      ),
      ['Select', 'Generate', 'Evaluate', 'Store'],
    );
    assert.equal(
      getNode('operator_bandit').closest('.arch-step').dataset.step,
      'select',
      'learning controls sit at the choice they affect',
    );
    assert.equal(getNode('generation').closest('.arch-step').dataset.step, 'generate');
    assert.equal(getNode('descriptor').closest('.arch-step').dataset.step, 'store');
    assert.match(map.querySelector('.arch-model').textContent, /Provider \/ model A/);
    assert.equal(map.querySelectorAll('.arch-feedback[data-feedback]').length, 2);
    assert.match(
      map.querySelector('[data-feedback="learning"] [data-return-step="select"]').textContent,
      /1 · Select/,
    );
    assert.match(
      map.querySelector('[data-feedback="knowledge"] [data-return-step="generate"]').textContent,
      /2 · Generate/,
    );
    assert.equal(getNode('generation').tagName, 'BUTTON');
    assert.equal(getNode('generation').tabIndex, 0);
    assert.equal(getNode('generation').classList.contains('current'), true);
    assert.equal(getNode('mode_mlp'), null, 'disabled mechanism belongs outside the active graph');
    assert.match(doc.querySelector('.graph-inactive').textContent, /Mode MLP/);
    assert.equal(
      doc.querySelector('.graph-inspector').hidden,
      true,
      'details stay collapsed until a mechanism is selected',
    );
    getNode('generation').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
    assert.equal(map.dataset.selectedNode, 'generation');
    assert.equal(getNode('generation').getAttribute('aria-pressed'), 'true');
    assert.equal(getNode('evaluation').classList.contains('related'), true);
    assert.equal(getNode('reflection').classList.contains('related'), false);
    assert.equal(doc.querySelector('.graph-inspector').hidden, false);
    assert.match(doc.querySelector('.graph-inspector').textContent, /Recorded model A/);
    assert.match(doc.querySelector('.graph-inspector').textContent, /Candidate source/);
    assert.match(doc.querySelector('.graph-inspector').textContent, /Selected generation operator/);
    assert.match(doc.querySelector('.graph-inspector').textContent, /Retrieved lessons/);
    assert.doesNotMatch(
      doc.querySelector('.graph-inspector').textContent,
      /Observed evidence|Tested conclusions/,
    );
    const enter = new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true });
    getNode('operator_bandit').focus();
    getNode('operator_bandit').dispatchEvent(enter);
    assert.equal(enter.defaultPrevented, true);
    assert.equal(map.dataset.selectedNode, 'operator_bandit');
    assert.match(doc.querySelector('.graph-inspector').textContent, /Window max reward/);
    const space = new w.KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true });
    getNode('memory').focus();
    getNode('memory').dispatchEvent(space);
    assert.equal(space.defaultPrevented, true);
    assert.equal(map.dataset.selectedNode, 'memory');
    assert.equal(getNode('operator_bandit').getAttribute('aria-pressed'), 'false');
    assert.equal(getNode('memory').getAttribute('aria-pressed'), 'true');
    const selectedNode = getNode('memory'),
      inspector = doc.querySelector('.graph-inspector'),
      inspectorHTML = inspector.innerHTML;
    const update = {
      run: { id: fixtureRun.id, status: 'running' },
      runtime: {
        available: true,
        active: true,
        status: 'running',
        stage: 'evaluating',
        heartbeat_age_seconds: 2,
      },
    };
    streams.at(-1).runtime(update);
    assert.equal(doc.querySelector('.architecture-map'), map);
    assert.equal(
      getNode('memory'),
      selectedNode,
      'heartbeat preserves the selected keyboard target',
    );
    assert.equal(doc.activeElement, selectedNode, 'heartbeat preserves keyboard focus');
    assert.equal(doc.querySelector('.graph-inspector'), inspector);
    assert.equal(inspector.innerHTML, inspectorHTML);
    assert.equal(map.dataset.selectedNode, 'memory');
    assert.equal(getNode('memory').getAttribute('aria-pressed'), 'true');
    assert.equal(getNode('evaluation').classList.contains('current'), true);
    assert.equal(getNode('generation').classList.contains('current'), false);
    update.runtime.stage = 'research';
    streams.at(-1).runtime(update);
    assert.equal(
      doc.querySelector('.architecture-node.current'),
      null,
      'generic research heartbeat does not identify conclusion or reflection',
    );
    assert.equal(map.dataset.selectedNode, 'memory');
    assert.equal(inspector.innerHTML, inspectorHTML);
    assert.equal(doc.querySelectorAll('.architecture img').length, 0);
    assert.equal(w.owned, undefined);
    assert.match(map.textContent, /<img src=x/, 'untrusted text remains visible as literal text');
    getNode('memory').dispatchEvent(
      new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }),
    );
    assert.equal(map.dataset.selectedNode, '');
    assert.equal(doc.querySelector('.architecture-node.selected'), null);
    assert.equal(inspector.hidden, true, 'Escape collapses details again');
    map.querySelector('[data-return-step="select"]').click();
    assert.equal(
      doc.activeElement,
      getNode('parent'),
      'reward feedback returns keyboard focus to selection',
    );
    map.querySelector('[data-return-step="generate"]').click();
    assert.equal(
      doc.activeElement,
      getNode('generation'),
      'knowledge feedback returns keyboard focus to generation',
    );
    const target = runIndex.find((run) => run.id !== fixtureRun.id);
    const other = JSON.parse(JSON.stringify(snapshot));
    other.run = { ...snapshot.run, ...target };
    other.content_version = 'architecture-graph-b';
    other.runtime = null;
    other.architecture.graph = {
      nodes: [
        node('generation', 'Generate with model B', 'core', { subtitle: 'Provider / model B' }),
        node('evaluation', 'Second evaluator'),
        node('population', 'Single archive'),
      ],
      edges: [
        { from: 'generation', to: 'evaluation', label: 'Second-run candidate', kind: 'flow' },
      ],
      inactive: [],
      summary: ['Model B'],
      notes: [],
    };
    w.fetch = (url) =>
      String(url) === '/api/runs/' + encodeURIComponent(target.id)
        ? Promise.resolve(
            new Response(JSON.stringify(other), {
              headers: { 'Content-Type': 'application/json' },
            }),
          )
        : fetch(new URL(url, base));
    doc.querySelector('[data-run="' + target.id + '"]').click();
    await until(
      () => doc.querySelector('.arch-model')?.textContent.includes('Provider / model B'),
      'new run architecture loaded',
    );
    assert.equal(doc.querySelectorAll('.architecture-node').length, 3);
    assert.equal(getNode('operator_bandit'), null);
    assert.equal(getNode('memory'), null);
    assert.doesNotMatch(
      doc.querySelector('.architecture-map').textContent,
      /model A|Adaptive operator bandit/,
    );
    assert.deepEqual(errors, []);
  } finally {
    dom.window.close();
  }
});
