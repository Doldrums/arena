// Read-only DOM behavior with synthetic fixtures; no research execution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { source, mount, input } from './helpers/arena-fixture.mjs';
test('participants remain visible without the task disclosure or scientific analysis', async () => {
  const { dom, doc } = await mount({ url: 'http://arena.test/?view=participants' });
  try {
    const browser = doc.getElementById('arena-catalog-browser');
    assert.equal(browser.open, true);
    assert.equal(browser.hidden, false);
    assert.equal(doc.getElementById('arena-catalog-toggle').hidden, true);
    assert.equal(doc.getElementById('arena-analysis').hidden, true);
    assert.equal(doc.getElementById('arena-faq').hidden, true);
    assert.ok(doc.querySelector('.arena-participant'));
    doc.querySelector('[data-arena-view="tasks"]').click();
    assert.equal(browser.open, false);
    assert.equal(doc.getElementById('arena-catalog-toggle').hidden, false);
    assert.equal(doc.getElementById('arena-analysis').hidden, false);
  } finally {
    dom.window.close();
  }
});

test('participants show planned capabilities without execution controls', async () => {
  const { dom, doc, w } = await mount({ url: 'http://arena.test/?view=participants' });
  try {
    assert.equal(doc.getElementById('arena-title').textContent, 'Participants');
    assert.match(doc.getElementById('arena-results').textContent, /Source pinned/);
    assert.match(doc.getElementById('arena-results').textContent, /Integration open/);
    doc.querySelector('.arena-participant .arena-task-link').click();
    assert.equal(new URL(w.location.href).searchParams.get('participant'), 'sciel');
    assert.match(
      doc.getElementById('arena-detail').textContent,
      /Native executionIntegration pending/,
    );
    assert.match(
      doc.getElementById('arena-detail').textContent,
      /Canonical evaluationIntegration pending/,
    );
    assert.equal(
      [...doc.querySelectorAll('button')].some((node) =>
        /^(Run|Start|Pause|Resume)$/.test(node.textContent),
      ),
      false,
    );
    assert.ok(doc.querySelector('a[href="/experiments"]'));
  } finally {
    dom.window.close();
  }
});

test('research works expose paper provenance and safe source links without implying execution support', async () => {
  const record = {
    id: 'method-x',
    name: 'Method X',
    record_kind: 'research_work',
    registration_status: 'literature',
    adapter_status: 'not_implemented',
    description: 'Evolves search procedures.',
    search_family: { id: 'evolution', label: 'Evolutionary methods' },
    papers: [
      {
        id: 'paper-x',
        title: 'Research <script>literal</script>',
        url: 'https://arxiv.org/abs/1234.56789',
        year: 2025,
        venue: 'Research venue',
      },
    ],
    code_links: [
      { label: 'Result notebook', url: 'https://example.org/results' },
      { label: 'Unsafe', url: 'javascript:alert(1)' },
    ],
    provenance: { filename: 'research-corpus.md', line_start: 12, line_end: 30 },
    capabilities: { native_run: false },
  };
  const { dom, doc } = await mount({
    url: 'http://arena.test/?view=participants',
    participantRecords: {
      participants: [record],
      summary: { research_work_count: 1, pinned_registration_count: 0 },
    },
  });
  try {
    const card = doc.querySelector('.arena-participant');
    assert.match(card.textContent, /Research work/);
    assert.match(card.textContent, /2025 · Research venue/);
    assert.equal(card.querySelector('script'), null);
    const paper = card.querySelector('.arena-paper-title');
    assert.equal(paper.getAttribute('href'), 'https://arxiv.org/abs/1234.56789');
    assert.equal(paper.target, '_blank');
    assert.match(paper.rel, /noopener/);
    assert.ok([...card.querySelectorAll('a')].some((a) => a.textContent === 'Result notebook ↗'));
    assert.equal(card.querySelector('a[href^="javascript:"]'), null);
    card.querySelector('.arena-task-link').click();
    const detail = doc.getElementById('arena-detail');
    assert.ok(detail.querySelector('.arena-participant-papers.is-detail'));
    assert.match(detail.textContent, /research-corpus.md, lines 12–30/);
    assert.doesNotMatch(detail.textContent, /Native executionAvailable/);
  } finally {
    dom.window.close();
  }
});

test('research adapter links show native engines and exact pins without granting registration capabilities', async () => {
  const record = {
    id: 'method-x',
    name: 'Method X',
    record_kind: 'research_work',
    registration_status: 'literature',
    repository: null,
    adapter_status: 'not_implemented',
    capabilities: { native_run: false, canonical_evaluation: false, pause: false, resume: false },
    native_adapters: [
      {
        engine: 'method-engine',
        name: 'Native <script>literal</script>',
        repository: { url: 'https://github.com/example/method', commit: 'a'.repeat(40) },
        profiles: ['native-search', 'native-evaluate'],
        evaluation: 'native',
        runtime_readiness: 'not_verified',
      },
    ],
  };
  const { dom, doc } = await mount({
    url: 'http://arena.test/?view=participants',
    participantRecords: { participants: [record] },
  });
  try {
    const card = doc.querySelector('.arena-participant');
    assert.match(card.textContent, /Research work/);
    assert.match(card.textContent, /Local adapter/);
    assert.doesNotMatch(card.textContent, /Source pinned|Adapter integrated/);
    card.querySelector('.arena-task-link').click();
    const detail = doc.getElementById('arena-detail');
    assert.match(
      detail.textContent,
      /Source and fixture checks · native environment to be verified/,
    );
    assert.match(detail.textContent, /method-engine/);
    assert.match(detail.textContent, /native-search, native-evaluate/);
    assert.match(detail.textContent, /native evaluation/);
    assert.match(
      detail.textContent,
      /do not establish canonical task compatibility or a verified runtime/,
    );
    assert.doesNotMatch(
      detail.textContent,
      /Native executionAvailable|Canonical evaluationAvailable/,
    );
    assert.equal(detail.querySelector('script'), null);
    const source = detail.querySelector(
      `a[href="https://github.com/example/method/tree/${'a'.repeat(40)}"]`,
    );
    assert.ok(source);
    assert.equal(source.target, '_blank');
    assert.match(source.rel, /noopener/);
    assert.equal(record.registration_status, 'literature');
    assert.equal(record.capabilities.native_run, false);
  } finally {
    dom.window.close();
  }
});

test('blocked and artifact-only works do not acquire runnable badges from the current snapshot', async () => {
  const snapshot = JSON.parse(
    readFileSync(new URL('../../registry/participants.json', import.meta.url), 'utf8'),
  );
  const records = snapshot.participants.filter((item) =>
    ['meta-harness', 'evoflow', 'aevo', 'adas'].includes(item.id),
  );
  assert.equal(records.length, 4);
  const { dom, doc } = await mount({
    url: 'http://arena.test/?view=participants',
    participantRecords: { participants: records },
  });
  try {
    for (const id of ['meta-harness', 'evoflow', 'aevo']) {
      const card = doc.querySelector(`[data-participant="${id}"].arena-participant`);
      assert.match(card.textContent, /Integration open/);
      assert.doesNotMatch(card.textContent, /Local adapter/);
    }
    assert.match(
      doc.querySelector('[data-participant="adas"].arena-participant').textContent,
      /Local adapter/,
    );
  } finally {
    dom.window.close();
  }
});

test('participant search includes bibliography and family filters with pagination and history', async () => {
  const records = Array.from({ length: 31 }, (_, i) => ({
    id: `work-${i}`,
    name: `Work ${i}`,
    record_kind: 'research_work',
    adapter_status: 'not_implemented',
    search_family: {
      id: i < 27 ? 'search' : 'prompts',
      label: i < 27 ? 'Search methods' : 'Prompt methods',
    },
    papers: [
      {
        title: i === 29 ? 'Distinctive research title' : `Publication ${i}`,
        url: `https://example.org/paper/${i}`,
        year: 2025,
        venue: 'Conference',
      },
    ],
  }));
  const { dom, doc, w } = await mount({
    url: 'http://arena.test/?view=participants',
    participantRecords: { participants: records },
  });
  try {
    assert.equal(doc.querySelectorAll('.arena-participant').length, 25);
    assert.match(doc.getElementById('arena-result-count').textContent, /31 of 31/);
    [...doc.querySelectorAll('#arena-pagination button')]
      .find((b) => b.textContent === 'Next →')
      .click();
    assert.equal(doc.querySelectorAll('.arena-participant').length, 6);
    assert.equal(new URL(w.location.href).searchParams.get('page'), '2');
    doc.querySelector('.arena-participant .arena-task-link').click();
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    assert.equal(doc.querySelectorAll('.arena-participant').length, 6);
    input(w, doc.getElementById('arena-family'), 'prompts', 'change');
    assert.equal(doc.querySelectorAll('.arena-participant').length, 4);
    assert.equal(new URL(w.location.href).searchParams.has('page'), false);
    input(w, doc.getElementById('arena-search'), 'Distinctive');
    assert.equal(doc.querySelectorAll('.arena-participant').length, 1);
    assert.equal(doc.querySelector('.arena-participant').dataset.participant, 'work-29');
    doc.getElementById('arena-clear').click();
    assert.match(doc.getElementById('arena-result-count').textContent, /31 of 31/);
  } finally {
    dom.window.close();
  }
});

test('participant bylines credit primary research sources and search full institutions', async () => {
  const records = [
    {
      id: 'lab-method',
      name: 'Lab method',
      record_kind: 'research_work',
      attribution: {
        kind: 'organizations',
        display: 'Sakana AI · UBC',
        organizations: ['Sakana AI', 'University of British Columbia'],
        authors: [],
        source_url: 'https://arxiv.org/pdf/2505.22954v3',
        source_locator: 'p. 1 author affiliations',
        evidence_note: 'Work-done affiliations.',
      },
    },
    {
      id: 'author-method',
      name: 'Author method',
      record_kind: 'research_work',
      attribution: {
        kind: 'authors',
        display: 'A <script>literal</script>',
        organizations: [],
        authors: ['A Researcher'],
        source_url: 'javascript:alert(1)',
      },
    },
  ];
  const { dom, doc, w } = await mount({
    url: 'http://arena.test/?view=participants',
    participantRecords: { participants: records },
  });
  try {
    const byline = doc.querySelector('[data-participant="lab-method"] .arena-participant-byline');
    assert.equal(byline.textContent, 'by Sakana AI · UBC');
    const source = byline.querySelector('a');
    assert.equal(source.href, 'https://arxiv.org/pdf/2505.22954v3');
    assert.equal(source.target, '_blank');
    assert.match(source.rel, /noopener/);
    const author = doc.querySelector(
      '[data-participant="author-method"] .arena-participant-byline',
    );
    assert.equal(author.querySelector('a'), null);
    assert.equal(author.querySelector('script'), null);
    assert.equal(author.textContent, 'by A <script>literal</script>');
    input(w, doc.getElementById('arena-search'), 'British Columbia');
    assert.equal(doc.querySelectorAll('.arena-participant').length, 1);
    doc.querySelector('.arena-participant .arena-task-link').click();
    const detail = doc.getElementById('arena-detail');
    assert.equal(
      detail.querySelector('.arena-participant-byline').textContent,
      'by Sakana AI · UBC',
    );
    assert.match(
      detail.querySelector('.arena-attribution-context').textContent,
      /University of British Columbia/,
    );
    assert.match(
      detail.querySelector('.arena-attribution-context').textContent,
      /Work-done affiliations/,
    );
    doc.querySelector('#arena-detail a[data-arena-route]').click();
    input(w, doc.getElementById('arena-search'), 'A Researcher');
    assert.equal(doc.querySelectorAll('.arena-participant').length, 1);
    assert.equal(doc.querySelector('.arena-participant').dataset.participant, 'author-method');
  } finally {
    dom.window.close();
  }
});
