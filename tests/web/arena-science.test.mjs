// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  task,
  participants,
  insightsFixture,
  mount,
  input,
  referenceFixture,
} from './helpers/arena-fixture.mjs';
test('scientific cards expose a keyboard-accessible preview without opening or filtering the catalog', async () => {
  const tasks = [
    task(),
    task({ id: 'second', name: 'Second construction' }),
    task({ id: 'other', name: 'Other task', family: 'Physics' }),
  ];
  const scrolls = [];
  const { dom, w, doc, app } = await mount({
    tasks,
    prepare(w) {
      w.HTMLElement.prototype.scrollIntoView = function () {
        scrolls.push(this.id);
      };
    },
  });
  try {
    const browser = doc.getElementById('arena-catalog-browser'),
      before = w.location.href,
      historyLength = w.history.length;
    const card = doc.querySelector('[data-domain-card="geometry"]');
    assert.equal(card.tagName, 'BUTTON');
    assert.equal(card.type, 'button');
    assert.equal(card.tabIndex, 0);
    assert.equal(card.getAttribute('aria-expanded'), 'false');
    assert.equal(card.getAttribute('aria-controls'), 'arena-domain-preview');
    card.focus();
    // Native keyboard activation produces a zero-detail click; JSDOM does not synthesize it from keydown.
    card.dispatchEvent(new w.MouseEvent('click', { bubbles: true, detail: 0 }));
    const preview = doc.getElementById('arena-domain-preview');
    assert.ok(preview);
    assert.equal(preview.getAttribute('role'), 'region');
    assert.equal(preview.getAttribute('aria-labelledby'), 'arena-domain-preview-title');
    assert.equal(doc.activeElement.id, 'arena-domain-preview-title');
    assert.equal(
      doc.querySelector('[data-domain-card="geometry"]').getAttribute('aria-expanded'),
      'true',
    );
    assert.match(preview.textContent, /Geometry scientific role/);
    assert.equal(preview.querySelectorAll('.field-example').length, 2);
    assert.equal(browser.open, false);
    assert.equal(w.location.href, before);
    assert.equal(w.history.length, historyLength);
    assert.equal(doc.getElementById('arena-result-count').textContent, '3 of 3 tasks');
    assert.equal(doc.getElementById('arena-active-filters').hidden, true);
    assert.ok(
      !scrolls.some((id) =>
        ['arena-list-panel', 'arena-analysis', 'arena-catalog-browser'].includes(id),
      ),
    );
    app.render();
    await app.reload();
    assert.equal(browser.open, false);
    assert.equal(w.location.href, before);
    assert.equal(
      doc.querySelector('[data-domain-card="geometry"]').getAttribute('aria-expanded'),
      'true',
    );
    doc.querySelector('.field-detail-close').focus();
    doc.querySelector('.field-detail-close').click();
    assert.equal(doc.querySelector('[data-field-detail]'), null);
    assert.equal(doc.activeElement.dataset.domainCard, 'geometry');
    assert.equal(doc.activeElement.getAttribute('aria-expanded'), 'false');
    assert.equal(browser.open, false);
    assert.equal(w.location.href, before);
    assert.equal(w.history.length, historyLength);
  } finally {
    dom.window.close();
  }
});

test('domain previews preserve deep-link filters and both manually open and closed catalog states', async () => {
  const tasks = [
    task(),
    task({ id: 'unsupported', executable: false }),
    task({ id: 'other', name: 'Other task', family: 'Physics' }),
  ];
  const { dom, w, doc, app } = await mount({
    tasks,
    url: 'http://arena.test/?domain=geometry&type=construction',
  });
  try {
    const browser = doc.getElementById('arena-catalog-browser'),
      before = w.location.href;
    assert.equal(browser.open, true);
    assert.equal(doc.querySelector('[data-field-detail]').dataset.fieldDetail, 'geometry');
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 3 tasks');
    doc.querySelector('[data-domain-card="other"]').click();
    assert.equal(browser.open, true);
    assert.equal(w.location.href, before);
    assert.equal(doc.querySelector('[data-field-detail]').dataset.fieldDetail, 'other');
    assert.equal(
      doc.querySelector('[data-domain-card="geometry"]').getAttribute('aria-expanded'),
      'false',
    );
    assert.equal(
      doc.querySelector('[data-domain-card="other"]').getAttribute('aria-expanded'),
      'true',
    );
    assert.equal(
      doc
        .querySelector('.insights-composition [data-filter-value="geometry"]')
        .getAttribute('aria-pressed'),
      'true',
    );
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 3 tasks');
    doc.querySelector('.field-detail-close').click();
    assert.equal(doc.activeElement.dataset.domainCard, 'other');
    assert.equal(doc.querySelector('[data-field-detail]'), null);
    assert.equal(browser.open, true);
    assert.equal(w.location.href, before);
    browser.open = false;
    app.render();
    doc.querySelector('[data-domain-card="geometry"]').click();
    assert.equal(browser.open, false);
    assert.equal(w.location.href, before);
    doc.querySelector('.field-catalog-link').click();
    assert.equal(browser.open, true);
    assert.equal(new URL(w.location).searchParams.get('domain'), 'geometry');
    assert.equal(new URL(w.location).searchParams.get('type'), 'construction');
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 3 tasks');
  } finally {
    dom.window.close();
  }
});

test('a scientific preview example opens task detail without applying a domain filter first', async () => {
  const { dom, w, doc } = await mount();
  try {
    const browser = doc.getElementById('arena-catalog-browser');
    doc.querySelector('[data-domain-card="geometry"]').click();
    assert.equal(browser.open, false);
    doc.querySelector('#arena-domain-preview .field-example a').click();
    assert.equal(new URL(w.location).searchParams.get('task'), 'packing/circle');
    assert.equal(new URL(w.location).searchParams.get('domain'), null);
    assert.equal(doc.getElementById('arena-detail').hidden, false);
    assert.equal(doc.getElementById('arena-insights').hidden, true);
    assert.equal(browser.hidden, true);
    assert.equal(browser.open, false);
    assert.match(doc.getElementById('arena-detail').textContent, /Circle packing/);
  } finally {
    dom.window.close();
  }
});

test('standalone scientific overview retains combined charts and references without an analysis root', async () => {
  const tasks = [task(), task({ id: 'model' })],
    { dom, w, doc } = await mount({ tasks });
  try {
    const root = doc.createElement('div');
    doc.body.append(root);
    w.renderArenaInsights(root, {
      catalog: { tasks },
      insights: insightsFixture(tasks),
      references: referenceFixture(tasks),
      current: {},
      onFilter: () => {},
    });
    assert.ok(root.querySelector('[data-domain-card]'));
    assert.ok(root.querySelector('.insights-composition'));
    assert.ok(root.querySelector('[data-reference-task]'));
  } finally {
    dom.window.close();
  }
});

test('domain and task-type charts combine URL filters and preserve keyboard focus', async () => {
  const tasks = [
    task(),
    task({ id: 'packing/unsupported', executable: false }),
    task({ id: 'other', name: 'Other task', family: 'Physics' }),
  ];
  const insights = insightsFixture(tasks);
  insights.domains[0].percentage = 66.6;
  const { dom, w, doc } = await mount({ tasks, insights });
  try {
    const domain = doc.querySelector(
      '.insights-composition [data-filter-kind="domain"][data-filter-value="geometry"]',
    );
    assert.match(domain.textContent, /66\.6%/);
    assert.match(doc.querySelector('.insights-composition').textContent, /66\.6%/);
    assert.equal(doc.querySelector('.insights-composition').open, false);
    assert.match(
      domain.getAttribute('aria-label'),
      /1 executable definitions, 1 awaiting an evaluator/,
    );
    domain.focus();
    domain.click();
    assert.equal(doc.activeElement.dataset.filterValue, 'geometry');
    assert.equal(doc.activeElement.getAttribute('aria-pressed'), 'true');
    assert.equal(new URL(w.location).searchParams.get('domain'), 'geometry');
    assert.equal(doc.getElementById('arena-result-count').textContent, '2 of 3 tasks');
    const taskType = doc.querySelector(
      '[data-filter-kind="type"][data-filter-value="construction"]',
    );
    taskType.focus();
    taskType.click();
    assert.equal(doc.activeElement.dataset.insightsAction, 'type:construction');
    assert.equal(doc.getElementById('arena-analysis').contains(doc.activeElement), true);
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 3 tasks');
    assert.match(doc.querySelector('.insights-catalog-jump').textContent, /1 matching tasks/);
    doc.querySelector('button[aria-label="Remove domain filter: Geometry"]').click();
    assert.equal(doc.getElementById('arena-result-count').textContent, '2 of 3 tasks');
    assert.equal(new URL(w.location).searchParams.get('domain'), null);
    w.history.replaceState(null, '', '/?domain=geometry&type=analysis');
    w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(doc.querySelector('.arena-task-link').textContent, 'Circle packing');
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 3 tasks');
    doc.getElementById('arena-clear').click();
    assert.equal(doc.getElementById('arena-result-count').textContent, '3 of 3 tasks');
  } finally {
    dom.window.close();
  }
});

test('all scientific domains are visible while the independent task-type chart expands', async () => {
  const tasks = [task()],
    insights = insightsFixture(tasks);
  insights.domains = Array.from({ length: 12 }, (_, i) => ({
    id: `domain-${i}`,
    label: `Domain ${i}`,
    total: 1,
    executable: 1,
    unsupported: 0,
  }));
  insights.task_types = Array.from({ length: 18 }, (_, i) => ({
    id: `type-${i}`,
    label: `Type ${i}`,
    total: 1,
    executable: 1,
    unsupported: 0,
  }));
  const { dom, doc } = await mount({ tasks, insights });
  try {
    assert.equal(doc.querySelectorAll('[data-domain-card]').length, 12);
    assert.equal(
      doc.querySelectorAll('.insights-composition [data-filter-kind="domain"]').length,
      12,
    );
    assert.equal(doc.querySelectorAll('[data-filter-kind="type"]').length, 10);
    doc.querySelector('[data-insights-action="expand:type"]').click();
    assert.equal(doc.querySelectorAll('[data-filter-kind="type"]').length, 18);
    assert.equal(
      doc.querySelector('[data-insights-action="expand:type"]').getAttribute('aria-expanded'),
      'true',
    );
  } finally {
    dom.window.close();
  }
});

test('reference examples follow every filter and distinguish published values from seed smoke', async () => {
  const tasks = [
    task(),
    task({ id: 'model', name: 'Model task', family: 'ML' }),
    task({ id: 'no-reference', name: 'Missing reference', family: 'ML' }),
  ];
  const { dom, w, doc } = await mount({ tasks, references: referenceFixture(tasks) });
  try {
    let rows = doc.querySelectorAll('#arena-analysis [data-reference-task]');
    assert.equal(rows.length, 2);
    assert.equal(rows[0].dataset.referenceTask, 'model');
    assert.match(rows[0].textContent, /Validity not recorded/);
    assert.match(rows[0].textContent, /5 items \(historical smoke\)/);
    assert.match(rows[1].textContent, /Published reference: 2.63/);
    assert.match(rows[1].textContent, /Seed smoke: 2.14/);
    assert.match(rows[1].textContent, /n: 26/);
    assert.match(rows[1].textContent, /1 construction/);
    assert.doesNotMatch(rows[1].textContent, /Cases: 1/);
    doc.querySelector('[data-domain-card="geometry"]').click();
    doc.querySelector('.field-catalog-link').click();
    rows = doc.querySelectorAll('#arena-analysis [data-reference-task]');
    assert.equal(rows.length, 1);
    assert.equal(rows[0].dataset.referenceTask, 'packing/circle');
    input(w, doc.getElementById('arena-search'), 'missing query');
    assert.equal(doc.querySelectorAll('#arena-analysis [data-reference-task]').length, 0);
    assert.match(
      doc.getElementById('arena-analysis').textContent,
      /No numeric references are recorded for the selected tasks/,
    );
    doc.getElementById('arena-clear').click();
    doc.querySelector('[data-insights-action="reference:missing"]').click();
    assert.equal(new URL(w.location).searchParams.get('reference'), 'missing');
    assert.equal(doc.querySelector('.arena-task-link').textContent, 'Missing reference');
  } finally {
    dom.window.close();
  }
});

test('overview API outages keep task search usable and do not invent zero evidence', async () => {
  const { dom, w, doc } = await mount({
    url: 'http://arena.test/?domain=geometry',
    fetchJSON: async (path) => {
      if (path === '/api/catalog') return { tasks: [task()] };
      if (path === '/api/participants') return participants;
      throw new Error('Offline');
    },
  });
  try {
    assert.equal(doc.getElementById('arena-error').hidden, true);
    assert.match(
      doc.getElementById('arena-insights').textContent,
      /Scientific overview unavailable/,
    );
    assert.match(
      doc.getElementById('arena-analysis').textContent,
      /Reference evidence unavailable/,
    );
    assert.match(
      doc.getElementById('arena-active-filters').textContent,
      /Some filters await overview data/,
    );
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 1 tasks');
    input(w, doc.getElementById('arena-search'), 'circle');
    assert.equal(doc.getElementById('arena-result-count').textContent, '1 of 1 tasks');
    doc.querySelector('.arena-task-link').click();
    assert.match(
      doc.querySelector('[data-task-references]').textContent,
      /does not establish that the task has no reference/,
    );
    assert.doesNotMatch(
      doc.querySelector('[data-task-references]').textContent,
      /No numeric reference is recorded/,
    );
  } finally {
    dom.window.close();
  }
});

test('scientific and reference metadata remain text and external links reject active content', async () => {
  const tasks = [task(), task({ id: 'second' })],
    insights = insightsFixture(tasks),
    references = referenceFixture(tasks);
  insights.domains[0].label = '<img src=x onerror=alert(1)>';
  insights.domains[0].why_it_matters = '<script>alert(1)</script>';
  references.tasks[0].anchors[0].value = '<img src=x>';
  references.tasks[0].anchors[0].source.url = 'javascript:alert(1)';
  references.tasks[0].anchors[0].primary_sources = [{ url: 'data:text/html,bad' }];
  const { dom, doc } = await mount({ tasks, insights, references });
  try {
    assert.match(
      doc.getElementById('arena-insights').textContent,
      /<img src=x onerror=alert\(1\)>/,
    );
    assert.equal(
      doc.querySelector(
        '#arena-insights img, #arena-insights script, #arena-insights a[href^="javascript:"], #arena-analysis img, #arena-analysis script, #arena-analysis a[href^="javascript:"]',
      ),
      null,
    );
    doc.querySelector('.arena-task-link').click();
    assert.equal(
      doc.querySelector('#arena-detail img, #arena-detail script, #arena-detail a[href^="data:"]'),
      null,
    );
  } finally {
    dom.window.close();
  }
});
