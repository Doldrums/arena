// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { task, insightsFixture, mount, input, referenceFixture } from './helpers/arena-fixture.mjs';
test('atlas mode persists while separate source-method and evaluator-family filters combine', async () => {
  const tasks = [
    task(),
    task({ id: 'unsupported', family: null, executable: false }),
    task({ id: 'algebra', family: 'Algebra' }),
  ];
  const searchFamilies = {
    groups: [
      { id: 'evo', label: 'Evolutionary search', task_ids: ['packing/circle', 'unsupported'] },
      { id: 'prompt', label: 'Prompt optimization', task_ids: ['algebra'] },
    ],
    task_annotations: {
      'packing/circle': { search_family_id: 'evo' },
      unsupported: { search_family_id: 'evo' },
      algebra: { search_family_id: 'prompt' },
    },
  };
  const { dom, w, doc } = await mount({
    tasks,
    searchFamilies,
    url: 'http://arena.test/?search_family=evo',
  });
  try {
    assert.equal(doc.getElementById('arena-result-count').textContent, '2 of 3 tasks');
    assert.equal(doc.querySelectorAll('#arena-atlas circle[data-task-id]').length, 3);
    doc.querySelector('[data-atlas-mode="families"]').click();
    assert.equal(new URL(w.location).searchParams.get('atlas'), 'families');
    input(w, doc.getElementById('arena-family'), '__unspecified__', 'change');
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 3 tasks');
    assert.match(
      doc.getElementById('arena-active-filters').textContent,
      /Task family: Unspecified/,
    );
    assert.match(
      doc.getElementById('arena-active-filters').textContent,
      /Search method: Evolutionary search/,
    );
    doc
      .querySelector('button[aria-label="Remove search method filter: Evolutionary search"]')
      .click();
    assert.equal(new URL(w.location).searchParams.get('search_family'), null);
    doc.getElementById('arena-clear').click();
    assert.equal(doc.getElementById('arena-result-count').textContent, '3 of 3 tasks');
    assert.equal(
      doc.querySelector('[data-atlas-mode="families"]').getAttribute('aria-pressed'),
      'true',
    );
    doc.querySelector('#arena-results .arena-task-link').click();
    assert.equal(doc.getElementById('arena-atlas').hidden, true);
  } finally {
    dom.window.close();
  }
});

test('Task families atlas browses the same Physics tasks and scientific detail as its domain card', async () => {
  const tasks = [
    task(),
    task({ id: 'physical-model', name: 'Physical model', family: 'Algebra' }),
    task({ id: 'biology-model', name: 'Biology model', family: 'Geometry' }),
  ];
  const insights = insightsFixture(tasks);
  insights.task_annotations['packing/circle'].domain_id = 'physics';
  insights.task_annotations['physical-model'].domain_id = 'physics';
  insights.task_annotations['biology-model'].domain_id = 'biology-health';
  insights.domains = [
    {
      id: 'physics',
      label: 'Physics',
      total: 2,
      executable: 2,
      unsupported: 0,
      description: 'Physical systems.',
      why_it_matters: 'Understand physical behavior.',
      representative_task_ids: ['physical-model', 'packing/circle'],
    },
    {
      id: 'biology-health',
      label: 'Biology & health',
      total: 1,
      executable: 1,
      unsupported: 0,
      description: 'Living systems.',
      why_it_matters: 'Understand biological behavior.',
      representative_task_ids: ['biology-model'],
    },
  ];
  const { dom, w, doc } = await mount({ tasks, insights });
  const resultIds = () =>
    [...doc.querySelectorAll('#arena-results .arena-task-id')]
      .map((node) => node.textContent)
      .sort();
  try {
    doc.querySelector('[data-domain-card="physics"]').click();
    doc.querySelector('.field-catalog-link').click();
    const cardTaskIds = resultIds();
    assert.deepEqual(cardTaskIds, ['packing/circle', 'physical-model']);
    assert.equal(new URL(w.location).searchParams.get('domain'), 'physics');
    doc.querySelector('.field-detail-close').click();
    doc.getElementById('arena-clear').click();
    assert.equal(doc.querySelector('[data-field-detail]'), null);
    doc.querySelector('[data-atlas-mode="families"]').click();
    assert.equal(new URL(w.location).searchParams.get('atlas'), 'families');
    const physics = doc.querySelector('#arena-atlas [data-atlas-cluster="physics"]');
    assert.ok(physics);
    assert.equal(physics.querySelectorAll('[data-task-id]').length, 2);
    assert.ok(doc.querySelector('#arena-atlas [data-atlas-cluster="biology-health"]'));
    assert.equal(doc.querySelector('#arena-atlas [data-atlas-cluster="Geometry"]'), null);
    physics.dispatchEvent(new w.Event('click'));
    assert.equal(new URL(w.location).searchParams.get('domain'), null);
    assert.equal(doc.querySelector('#arena-atlas .atlas-details h3').textContent, 'Physics');
    doc.querySelector('#arena-atlas .atlas-browse').click();
    assert.equal(new URL(w.location).searchParams.get('domain'), 'physics');
    assert.equal(new URL(w.location).searchParams.get('family'), null);
    assert.equal(doc.getElementById('arena-catalog-browser').open, true);
    assert.deepEqual(resultIds(), cardTaskIds);
    assert.equal(doc.getElementById('arena-result-count').textContent, '2 of 3 tasks');
    assert.equal(doc.querySelector('[data-field-detail]').dataset.fieldDetail, 'physics');
    assert.equal(
      doc.querySelector('[data-domain-card="physics"]').getAttribute('aria-expanded'),
      'true',
    );
    assert.match(doc.getElementById('arena-active-filters').textContent, /Domain: Physics/);
    input(w, doc.getElementById('arena-family'), 'Geometry', 'change');
    assert.equal(new URL(w.location).searchParams.get('domain'), 'physics');
    assert.equal(new URL(w.location).searchParams.get('family'), 'Geometry');
    assert.deepEqual(resultIds(), ['packing/circle']);
    w.history.replaceState(null, '', '/?atlas=families&domain=physics');
    w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.deepEqual(resultIds(), cardTaskIds);
    assert.equal(
      doc.querySelector('#arena-atlas [data-atlas-cluster="physics"]').getAttribute('aria-pressed'),
      'true',
    );
  } finally {
    dom.window.close();
  }
});

test('method filters also update published reference examples', async () => {
  const tasks = [task(), task({ id: 'model', family: 'ML' })];
  const searchFamilies = {
    groups: [
      { id: 'evo', label: 'Evolution', task_ids: ['packing/circle'] },
      { id: 'prompt', label: 'Prompt', task_ids: ['model'] },
    ],
    task_annotations: {
      'packing/circle': { search_family_id: 'evo' },
      model: { search_family_id: 'prompt' },
    },
  };
  const { dom, w, doc } = await mount({
    tasks,
    searchFamilies,
    references: referenceFixture(tasks),
  });
  try {
    w.history.replaceState(null, '', '/?search_family=evo');
    w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(doc.querySelectorAll('#arena-analysis [data-reference-task]').length, 1);
    assert.equal(
      doc.querySelector('#arena-analysis [data-reference-task]').dataset.referenceTask,
      'packing/circle',
    );
    w.history.replaceState(null, '', '/?search_family=prompt');
    w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(
      doc.querySelector('#arena-analysis [data-reference-task]').dataset.referenceTask,
      'model',
    );
  } finally {
    dom.window.close();
  }
});

test('unmapped method cluster filters tasks with missing source assignments', async () => {
  const tasks = [task(), task({ id: 'unmapped' })];
  const searchFamilies = {
    groups: [{ id: 'evo', label: 'Evolution', task_ids: ['packing/circle'] }],
    task_annotations: { 'packing/circle': { search_family_id: 'evo' } },
  };
  const { dom, doc } = await mount({
    tasks,
    searchFamilies,
    url: 'http://arena.test/?search_family=unclassified',
  });
  try {
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 2 tasks');
    assert.equal(doc.querySelector('#arena-results .arena-task-id').textContent, 'unmapped');
  } finally {
    dom.window.close();
  }
});

test('metadata from a different catalog revision is unavailable while task search stays usable', async () => {
  const tasks = [task()],
    insights = insightsFixture(tasks);
  insights.catalog_digest = '0'.repeat(64);
  const searchFamilies = {
    catalog_digest: '0'.repeat(64),
    groups: [{ id: 'evo', label: 'Evolution', task_ids: ['packing/circle'] }],
    task_annotations: { 'packing/circle': { search_family_id: 'evo' } },
  };
  const { dom, doc } = await mount({ tasks, insights, searchFamilies });
  try {
    assert.match(
      doc.getElementById('arena-insights').textContent,
      /Scientific overview unavailable/,
    );
    assert.match(doc.getElementById('arena-atlas').textContent, /unavailable/i);
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 1 tasks');
  } finally {
    dom.window.close();
  }
});
