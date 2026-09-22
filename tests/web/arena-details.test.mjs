// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  source,
  task,
  mount,
  referenceFixture,
  recordedOverview,
} from './helpers/arena-fixture.mjs';
test('catalog values stay text and unsafe provenance URLs never become links', async () => {
  const { dom, doc, w } = await mount({
    tasks: [
      task({
        id: 'odd/<id>',
        name: '<img src=x onerror=alert(1)>',
        description: '<script>alert(1)</script>',
        provenance: {
          sources: [
            'javascript:alert(1)',
            { url: 'data:text/html,danger' },
            { url: 'https://example.org/source' },
          ],
        },
      }),
    ],
  });
  try {
    assert.equal(doc.querySelector('#arena-results img'), null);
    assert.equal(doc.querySelector('#arena-results script'), null);
    doc.querySelector('.arena-task-link').click();
    assert.equal(new URL(w.location.href).searchParams.get('task'), 'odd/<id>');
    assert.match(doc.getElementById('arena-detail').textContent, /<script>alert\(1\)<\/script>/);
    assert.equal(doc.querySelector('#arena-detail script, #arena-detail img'), null);
    assert.equal(doc.querySelector('#arena-detail a[href^="javascript:"]'), null);
    assert.ok(doc.querySelector('#arena-detail a[href="https://example.org/source"]'));
    assert.equal(w.safeExternalURL('https://user:password@example.org'), null);
  } finally {
    dom.window.close();
  }
});

test('task details preserve the declared input/output contract with its pinned source', async () => {
  const contract =
    'Input: centers as an array.\nOutput: <candidate> JSON with radii.\n<script>alert(1)</script>';
  const sourceURL = 'https://github.com/example/tasks/blob/123abc/suite/circle/problem.json';
  const { dom, doc } = await mount({
    url: 'http://arena.test/?task=packing%2Fcircle',
    tasks: [
      task({
        contract,
        contract_source: {
          url: sourceURL,
          path: 'suite/circle/problem.json',
          sha256: 'a'.repeat(64),
        },
      }),
    ],
  });
  try {
    const section = doc.querySelector('[data-task-contract]');
    assert.equal(section.querySelector('.arena-contract-text').textContent, contract);
    assert.match(section.textContent, /runtime conformance has not been verified/);
    assert.match(section.textContent, /suite\/circle\/problem.json/);
    assert.match(section.textContent, new RegExp('a'.repeat(64)));
    assert.equal(section.querySelector('a').href, sourceURL);
    assert.equal(section.querySelector('a').rel, 'noopener noreferrer');
    assert.equal(section.querySelector('script, candidate'), null);
  } finally {
    dom.window.close();
  }
});

test('absent task contracts stay explicitly unrecorded without inventing a signature', async () => {
  const { dom, doc } = await mount({
    url: 'http://arena.test/?task=packing%2Fcircle',
    tasks: [
      task({
        contract: null,
        contract_source: {
          url: 'javascript:alert(1)',
          path: 'suite/circle/problem.json',
          sha256: 'b'.repeat(64),
        },
      }),
    ],
  });
  try {
    const section = doc.querySelector('[data-task-contract]');
    assert.equal(
      section.querySelector('.arena-contract-text').textContent,
      'Input/output contract not recorded in the task snapshot.',
    );
    assert.equal(section.querySelector('.arena-contract-note'), null);
    assert.equal(section.querySelector('a'), null);
    assert.match(section.textContent, /suite\/circle\/problem.json/);
  } finally {
    dom.window.close();
  }
});

test('task detail includes scientific context, precise metric, parameters and source evidence', async () => {
  const tasks = [task(), task({ id: 'model', name: 'Model task', family: 'ML' })];
  const { dom, doc } = await mount({
    tasks,
    references: referenceFixture(tasks),
    url: 'http://arena.test/?task=packing%2Fcircle',
  });
  try {
    assert.equal(doc.getElementById('arena-insights').hidden, true);
    assert.match(doc.querySelector('[data-task-science]').textContent, /Geometry scientific role/);
    const section = doc.querySelector('[data-task-references]');
    assert.match(section.textContent, /Sum of radii/);
    assert.match(section.textContent, /Task instance: n: 26/);
    assert.match(section.textContent, /Evaluation size: 10 cases \(configured default\)/);
    assert.match(section.textContent, /5 items \(historical smoke\)/);
    assert.match(section.textContent, /Use identical constraints/);
    assert.ok(section.querySelector('a[href="https://example.org/paper"]'));
    assert.ok(section.querySelector('a[href="https://example.org/receipt"]'));
    assert.match(section.textContent, /Neither alone establishes current SOTA/);
  } finally {
    dom.window.close();
  }
});

test('scientific direction cards retain exact corpus counts and open real chemistry contracts', async () => {
  const { catalog, insights, fetchJSON } = recordedOverview();
  const { dom, w, doc } = await mount({ fetchJSON });
  try {
    assert.equal(doc.querySelectorAll('[data-domain-card]').length, insights.domains.length);
    const composition = doc.querySelector('.insights-composition');
    assert.equal(composition.open, false);
    for (const domain of insights.domains) {
      const card = doc.querySelector(`[data-domain-card="${domain.id}"]`);
      assert.ok(card, `Missing direction ${domain.id}`);
      assert.equal(
        card.querySelector('.field-count').textContent,
        `${domain.total.toLocaleString('en-US')} tasks`,
      );
      assert.doesNotMatch(card.textContent, /%/);
      const bar = composition.querySelector(`[data-filter-value="${domain.id}"]`);
      assert.ok(bar, `Missing composition count ${domain.id}`);
      assert.match(
        bar.getAttribute('aria-label'),
        new RegExp(`${domain.total.toLocaleString('en-US')} tasks`),
      );
      assert.ok(bar.textContent.includes(`${domain.percentage.toFixed(1)}%`));
    }
    const awaitingEvaluator = catalog.tasks.filter((item) => item.protocol === 'unsupported').length;
    assert.equal(insights.summary.unsupported_count, awaitingEvaluator);
    assert.ok(
      composition
        .querySelector('[role="img"]')
        .getAttribute('aria-label')
        .includes(`Evaluator to be added: ${awaitingEvaluator.toLocaleString('en-US')}`),
    );
    composition.querySelector('summary').click();
    assert.equal(composition.open, true);
    const chemistry = doc.querySelector('[data-domain-card="chemistry-materials"]');
    chemistry.focus();
    chemistry.click();
    assert.equal(doc.querySelector('.insights-composition').open, true);
    assert.equal(doc.activeElement.id, 'arena-domain-preview-title');
    assert.equal(
      doc.querySelector('[data-domain-card="chemistry-materials"]').getAttribute('aria-expanded'),
      'true',
    );
    assert.equal(new URL(w.location).searchParams.get('domain'), null);
    assert.equal(doc.getElementById('arena-catalog-browser').open, false);
    doc.querySelector('.field-catalog-link').click();
    assert.equal(new URL(w.location).searchParams.get('domain'), 'chemistry-materials');
    const expected = catalog.tasks.filter(
      (item) => insights.task_annotations[item.id]?.domain_id === 'chemistry-materials',
    );
    assert.equal(
      doc.getElementById('arena-result-count').textContent,
      `${expected.length} of ${catalog.tasks.length.toLocaleString('en-US')} tasks`,
    );
    assert.deepEqual(
      [...doc.querySelectorAll('#arena-results .arena-task-id')]
        .map((node) => node.textContent)
        .sort(),
      expected.map((item) => item.id).sort(),
    );
    const example = doc.querySelector('[data-field-detail="chemistry-materials"] .field-example a');
    const id = new URL(example.href).searchParams.get('task'),
      record = catalog.tasks.find((item) => item.id === id);
    assert.ok(record.contract);
    example.click();
    assert.equal(
      doc.querySelector('[data-task-contract] .arena-contract-text').textContent,
      record.contract,
    );
    assert.equal(doc.getElementById('arena-insights').hidden, true);
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.querySelector('.insights-composition').open, true);
    doc.querySelector('.insights-composition summary').click();
    const beforeClose = w.location.href;
    doc.querySelector('.field-detail-close').click();
    assert.equal(doc.querySelector('.insights-composition').open, false);
    assert.equal(doc.activeElement.dataset.domainCard, 'chemistry-materials');
    assert.equal(doc.activeElement.getAttribute('aria-expanded'), 'false');
    assert.equal(w.location.href, beforeClose);
    doc.activeElement.click();
    assert.equal(doc.querySelector('.insights-composition').open, false);
    assert.equal(
      doc.querySelector('[data-domain-card="chemistry-materials"]').getAttribute('aria-expanded'),
      'true',
    );
    assert.equal(w.location.href, beforeClose);
  } finally {
    dom.window.close();
  }
});

test('all 24 scientific examples explain the task and research value with safe primary sources', async () => {
  const { catalog, insights, fetchJSON } = recordedOverview(),
    tasks = new Map(catalog.tasks.map((item) => [item.id, item]));
  const { dom, doc } = await mount({ fetchJSON });
  try {
    let executableExamples = 0,
      sourceOnlyExamples = 0;
    const contexts = new Map();
    for (const domain of insights.domains) {
      doc.querySelector(`[data-domain-card="${domain.id}"]`).click();
      const detail = doc.querySelector(`[data-field-detail="${domain.id}"]`);
      assert.ok(detail, `Missing selected context for ${domain.id}`);
      assert.ok(detail.textContent.includes(domain.why_it_matters));
      const examples = [...detail.querySelectorAll('.field-example')];
      assert.equal(examples.length, 2, `${domain.id} must offer two real examples`);
      for (const example of examples) {
        const id = new URL(example.querySelector('a[data-arena-route]').href).searchParams.get(
            'task',
          ),
          task = tasks.get(id);
        assert.ok(task, `${id} must exist in the catalog`);
        assert.equal(
          insights.task_annotations[id].domain_id,
          domain.id,
          `${id} must belong to the selected domain`,
        );
        const context = example.querySelector('.field-example-context');
        assert.ok(context, `${id} needs a task explanation, not a readiness label`);
        const summary = context.textContent.trim();
        assert.ok(
          summary.split(/\s+/).length >= 20,
          `${id} needs a substantial explanation of the task and research value`,
        );
        assert.doesNotMatch(
          summary,
          /Evaluation definition recorded|Source-only definition|awaiting an evaluator|runtime readiness/i,
        );
        assert.notEqual(
          summary,
          domain.why_it_matters,
          `${id} must describe this task, not repeat its domain card`,
        );
        assert.equal(context.querySelector('img,script,iframe'), null);
        const source = example.querySelector('.field-context-source');
        assert.ok(source, `${id} needs a source for its explanation`);
        const url = new URL(source.href);
        assert.equal(url.protocol, 'https:');
        assert.equal(url.username, '');
        assert.equal(url.password, '');
        assert.equal(source.target, '_blank');
        assert.match(source.rel, /noopener/);
        assert.match(source.rel, /noreferrer/);
        assert.equal(source.hasAttribute('data-arena-route'), false);
        assert.ok(source.textContent.trim());
        assert.equal(
          contexts.has(id),
          false,
          `${id} must not be reused as a different scientific example`,
        );
        contexts.set(id, summary);
        if (task.executable) executableExamples++;
        else sourceOnlyExamples++;
        if (['earth-environment', 'finance-economics'].includes(domain.id))
          assert.equal(task.executable, false);
      }
    }
    assert.equal(contexts.size, 24);
    assert.ok(executableExamples > 0);
    assert.ok(
      sourceOnlyExamples >= 4,
      'Source-only Earth and Finance examples must remain visible',
    );
    const matrix = contexts.get('alphaevolve-matrix-multiplication-4-4-4');
    assert.match(matrix, /4[×x]4/);
    assert.match(matrix, /49/);
    assert.match(matrix, /Strassen/);
    assert.match(matrix, /1969/);
    for (const [id, summary] of contexts) {
      if (id !== 'alphaevolve-matrix-multiplication-4-4-4')
        assert.doesNotMatch(
          summary,
          /Strassen|1969/,
          `${id} must not inherit matrix multiplication history`,
        );
    }
    const forest = contexts.get('loongflow-tabular-playground-series-dec-2021');
    assert.match(forest, /synthetic/i);
    assert.match(forest, /generat(?:ed|ion)|modeled on/i);
    assert.match(forest, /class(?:es|ification)/i);
    const packing = contexts.get('alphaevolve-circle-packing-in-unit-square');
    assert.match(packing, /26/);
    assert.match(packing, /lower bound/i);
    assert.match(packing, /(?:total|sum(?: of)?) radii/i);
    assert.doesNotMatch(
      packing,
      /proven optimal packing|optimal arrangement|globally optimal|best possible packing|solves the packing problem/i,
    );
  } finally {
    dom.window.close();
  }
});
