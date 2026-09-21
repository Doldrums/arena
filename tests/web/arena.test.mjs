// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { task, participants, mount, input } from './helpers/arena-fixture.mjs';
test('overview keeps domains visible and technical data collapsed without undoing manual closure', async () => {
  const { dom, w, doc, app } = await mount();
  try {
    const browser = doc.getElementById('arena-catalog-browser');
    assert.equal(browser.open, false);
    assert.ok(doc.querySelector('#arena-insights [data-domain-card]'));
    assert.equal(doc.querySelector('#arena-insights .insights-composition'), null);
    assert.ok(doc.querySelector('#arena-statistics .insights-composition'));
    assert.equal(browser.contains(doc.getElementById('arena-statistics')), false);
    assert.equal(doc.getElementById('arena-statistics').hidden, false);
    assert.ok(browser.contains(doc.getElementById('arena-list-panel')));
    assert.equal(browser.contains(doc.getElementById('arena-detail')), false);
    doc.querySelector('[data-domain-card="geometry"]').click();
    doc.querySelector('.field-catalog-link').click();
    assert.equal(browser.open, true);
    browser.open = false;
    app.render();
    assert.equal(browser.open, false);
    await app.reload();
    assert.equal(browser.open, false);
    doc.querySelector('[data-atlas-mode="families"]').click();
    assert.equal(browser.open, false);
    input(w, doc.getElementById('arena-search'), 'circle');
    assert.equal(browser.open, true);
    doc.getElementById('arena-clear').click();
    assert.equal(browser.open, true);
  } finally {
    dom.window.close();
  }
});

test('catalog query and hash deep links reveal results while detail links stay outside the disclosure', async (t) => {
  for (const query of [
    'q=circle',
    'family=Geometry',
    'protocol=original',
    'domain=geometry',
    'type=construction',
    'reference=missing',
    'search_family=evolution',
    'page=1',
    '#arena-list-panel',
    '#arena-analysis',
  ]) {
    await t.test(query, async () => {
      const { dom, doc } = await mount({
        url: `http://arena.test/${query.startsWith('#') ? '' : '?'}${query}`,
      });
      try {
        assert.equal(doc.getElementById('arena-catalog-browser').open, true);
      } finally {
        dom.window.close();
      }
    });
  }
  const { dom, doc } = await mount({ url: 'http://arena.test/?task=packing%2Fcircle' });
  try {
    assert.equal(doc.getElementById('arena-catalog-browser').hidden, true);
    assert.equal(doc.getElementById('arena-detail').hidden, false);
    assert.equal(doc.getElementById('arena-faq').hidden, true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.getElementById('arena-catalog-browser').hidden, false);
    assert.equal(doc.getElementById('arena-catalog-browser').open, true);
    assert.equal(doc.activeElement.id, 'arena-results-title');
  } finally {
    dom.window.close();
  }
});

test('catalog anchors and history reveal the target before scrolling, including repeated hash links', async () => {
  const { dom, w, doc } = await mount();
  try {
    const browser = doc.getElementById('arena-catalog-browser'),
      panel = doc.getElementById('arena-list-panel'),
      scrolls = [];
    panel.scrollIntoView = () => scrolls.push(browser.open);
    doc.querySelector('.insights-catalog-jump').click();
    assert.equal(w.location.hash, '#arena-list-panel');
    assert.equal(browser.open, true);
    assert.equal(doc.activeElement.id, 'arena-results-title');
    assert.ok(scrolls.length);
    assert.ok(scrolls.every(Boolean));
    browser.open = false;
    doc.querySelector('.insights-catalog-jump').click();
    assert.equal(browser.open, true);
    browser.open = false;
    const faqLink = doc.querySelector('#arena-faq a[href="#arena-list-panel"]');
    faqLink.closest('details').open = true;
    faqLink.click();
    assert.equal(browser.open, true);
    assert.equal(doc.activeElement.id, 'arena-results-title');
    browser.open = false;
    w.history.replaceState(null, '', '/?domain=geometry');
    w.dispatchEvent(new w.PopStateEvent('popstate'));
    assert.equal(browser.open, true);
    browser.open = false;
    w.history.replaceState(null, '', '/#arena-analysis');
    w.dispatchEvent(new w.HashChangeEvent('hashchange'));
    assert.equal(browser.open, true);
  } finally {
    dom.window.close();
  }
});

test('initial catalog hash scroll waits for domain cards to establish the target position', async () => {
  const scrolls = [];
  const { dom } = await mount({
    url: 'http://arena.test/#arena-list-panel',
    prepare(w) {
      w.HTMLElement.prototype.scrollIntoView = function () {
        scrolls.push({
          id: this.id,
          domains: w.document.querySelectorAll('[data-domain-card]').length,
        });
      };
    },
  });
  try {
    assert.ok(scrolls.length);
    assert.ok(scrolls.every((item) => item.id === 'arena-list-panel' && item.domains > 0));
  } finally {
    dom.window.close();
  }
});

test('pagination and removing the last filter keep the catalog open and focus its results', async () => {
  const { dom, w, doc } = await mount({
    tasks: Array.from({ length: 31 }, (_, index) =>
      task({ id: `task-${index}`, name: `Task ${index}` }),
    ),
  });
  try {
    const browser = doc.getElementById('arena-catalog-browser');
    doc.querySelector('[data-domain-card="geometry"]').click();
    doc.querySelector('.field-catalog-link').click();
    browser.open = false;
    doc.querySelector('button[aria-label="Remove domain filter: Geometry"]').click();
    assert.equal(browser.open, true);
    [...doc.querySelectorAll('#arena-pagination button')]
      .find((node) => node.textContent === 'Next →')
      .click();
    assert.equal(browser.open, true);
    assert.equal(new URL(w.location).searchParams.get('page'), '2');
    assert.equal(doc.activeElement.id, 'arena-results-title');
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 6);
    doc.querySelector('.arena-task-link').click();
    assert.equal(browser.hidden, true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(browser.open, true);
    assert.match(doc.getElementById('arena-pagination').textContent, /Page 2 of 2/);
  } finally {
    dom.window.close();
  }
});

test('catalog searches real records, combines filters and restores deep-linked task details', async () => {
  const { dom, w, doc } = await mount({
    tasks: [
      task(),
      task({
        id: 'math/tensor',
        name: 'Tensor decomposition',
        description: 'Decompose a tensor.',
        family: 'Algebra',
        protocol: 'recreated',
        executable: false,
      }),
    ],
  });
  try {
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 2);
    input(w, doc.getElementById('arena-search'), 'circle square');
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 1);
    assert.equal(new URL(w.location.href).searchParams.get('q'), 'circle square');
    doc.querySelector('.arena-task-link').click();
    assert.equal(new URL(w.location.href).searchParams.get('task'), 'packing/circle');
    assert.match(
      doc.getElementById('arena-detail').textContent,
      /Runtime availabilitynot verified/,
    );
    assert.match(doc.getElementById('arena-detail').textContent, /Metric.*sum_radii/);
    assert.equal(doc.getElementById('arena-list-panel').hidden, true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.getElementById('arena-search').value, 'circle square');
    doc.getElementById('arena-clear').click();
    input(w, doc.getElementById('arena-family'), 'Algebra', 'change');
    input(w, doc.getElementById('arena-protocol'), 'original', 'change');
    assert.match(doc.getElementById('arena-results').textContent, /No tasks match/);
    doc.getElementById('arena-clear').click();
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 2);
  } finally {
    dom.window.close();
  }
});

test('independent API failures keep available registry usable and retry succeeds', async () => {
  let failed = true;
  const { dom, doc, app } = await mount({
    fetchJSON: async (path) => {
      if (path === '/api/catalog') {
        if (failed) throw new Error('Service unavailable');
        return { tasks: [task()] };
      }
      return participants;
    },
  });
  try {
    assert.match(doc.getElementById('arena-error').textContent, /Service unavailable/);
    doc.querySelector('[data-arena-view="participants"]').click();
    assert.equal(doc.getElementById('arena-error').hidden, true);
    assert.ok(doc.querySelector('.arena-participant'));
    failed = false;
    await app.reload();
    doc.querySelector('[data-arena-view="tasks"]').click();
    assert.equal(doc.getElementById('arena-error').hidden, true);
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 1);
  } finally {
    dom.window.close();
  }
});

test('empty registries, unknown links and pagination have explicit states', async () => {
  const empty = await mount({ tasks: [], url: 'http://arena.test/?task=missing' });
  try {
    assert.match(empty.doc.getElementById('arena-detail').textContent, /Task not found/);
  } finally {
    empty.dom.window.close();
  }
  const { dom, doc, w } = await mount({
    tasks: Array.from({ length: 31 }, (_, index) =>
      task({ id: `task-${index}`, name: `Task ${index}` }),
    ),
  });
  try {
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 25);
    assert.match(doc.getElementById('arena-pagination').textContent, /Page 1 of 2/);
    [...doc.querySelectorAll('#arena-pagination button')]
      .find((node) => node.textContent === 'Next →')
      .click();
    assert.equal(doc.querySelectorAll('.arena-table tbody tr').length, 6);
    assert.equal(new URL(w.location.href).searchParams.get('page'), '2');
    assert.equal(
      [...doc.querySelectorAll('#arena-pagination button')].find(
        (node) => node.textContent === 'Next →',
      ).disabled,
      true,
    );
  } finally {
    dom.window.close();
  }
});

test('malformed API payload is an error, not an empty catalog', async () => {
  const { dom, doc } = await mount({
    fetchJSON: async (path) =>
      path === '/api/catalog' ? { tasks: [{ name: 'Missing identity' }] } : participants,
  });
  try {
    assert.match(doc.getElementById('arena-error').textContent, /invalid registry/);
  } finally {
    dom.window.close();
  }
});
