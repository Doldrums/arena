import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const source = readFileSync(new URL('../../web/methods_progress.js', import.meta.url), 'utf8').replace(/export function /g, 'function ');
function mount() {
  const dom = new JSDOM('<main id="progress"></main>', {runScripts: 'outside-only', pretendToBeVisual: true});
  dom.window.eval(source + '; window.renderMethodsProgress = renderMethodsProgress;');
  const root = dom.window.document.querySelector('main'), selections = [];
  return {dom, root, selections, render: data => dom.window.renderMethodsProgress(root, data, {onSelect: (kind, id) => selections.push([kind, id])})};
}
const choose = (root, mode) => root.querySelector('[data-progress-mode="' + mode + '"]').click();
const point = (root, id) => [...root.querySelectorAll('[data-progress-point]')].find(node => node.dataset.progressPoint === id);
const measurement = (value, valid = true) => ({status: 'ok', measurement: {valid, metrics: {combined_score: value / 3}, observables: {sum_radii: value}}});
function experiment(id, control = 2.5, treatment = 2.6, extra = {}) {
  return {id, at: '2026-09-19T14:00:00Z', lab_id: 'lab-a', purpose: 'local',
    display_metric: 'sum_radii', display_control_score: control, display_treatment_score: treatment,
    native_metric: 'sum_radii', native_control_score: control, native_treatment_score: treatment,
    control_score: control / 3, treatment_score: treatment / 3,
    control: ['common-tool'], treatment: ['new-tool'], valid_treatment: true, status: 'completed', passed: true,
    criterion: {metric: 'combined_score', direction: 'max', minimum_effect: .001},
    results: {control: [measurement(control)], treatment: [measurement(treatment)]}, ...extra};
}
function solution(id, value, extra = {}) {
  return {id, at: '2026-09-19T14:00:00Z', program_id: 'p-' + id, lab_id: 'lab-a',
    record_kind: 'solution', valid: true, native_metric: 'sum_radii', native_score: value, score: value / 3, ...extra};
}
function data(extra = {}) {return {summary: {history_complete: true}, quality: {direction: 'max'}, experiments: [], solutions: [], proposals: [], ...extra};}

test('tool comparisons default before solutions, use native values, and never draw a global best', () => {
  const {dom, root, render, selections} = mount();
  try {
    render(data({experiments: [experiment('first'), experiment('second', 100, 101, {lab_id: 'another-lab'})]}));
    assert.equal(root.querySelector('[data-progress-mode="experiments"]').getAttribute('aria-pressed'), 'true');
    assert.match(root.textContent, /No evaluated solutions yet/);
    assert.equal(root.querySelectorAll('.methods-progress-pair').length, 2);
    assert.equal(root.querySelector('[data-progress-best]'), null);
    assert.equal(point(root, 'first').querySelector('[data-arm="treatment"]').dataset.value, '2.6');
    assert.match(root.querySelector('.methods-progress-scope').textContent, /not a global improvement curve/);
    point(root, 'first').dispatchEvent(new dom.window.Event('pointerenter'));
    assert.match(root.querySelector('.methods-progress-tooltip').textContent, /Control2.5Treatment2.6/);
    assert.match(root.querySelector('.methods-progress-tooltip').textContent, /Combined evaluation score/);
    point(root, 'first').dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true}));
    assert.deepEqual(selections, [['experiment', 'first']]);
  } finally {dom.window.close();}
});

test('solution best curve includes only actual valid canonical Programs and excludes task trials', () => {
  const {dom, root, render, selections} = mount();
  try {
    render(data({experiments: [experiment('tool-trial', 999, 1000)], solutions: [
      solution('valid', 2.4, {at: 1}), solution('invalid', 999, {valid: false, at: 2}),
      solution('missing-program', 999, {program_id: null, at: 3}), solution('improved', 2.6, {at: 4}),
      solution('not-measured', null, {at: 5}), solution('not-valid', 999, {valid: undefined}),
    ]}));
    assert.equal(root.querySelector('[data-progress-mode="solutions"]').getAttribute('aria-pressed'), 'true');
    assert.deepEqual([...root.querySelectorAll('[data-progress-point]')].map(node => node.dataset.progressPoint), ['valid', 'improved']);
    const path = root.querySelector('[data-progress-best]'); assert.ok(path);
    assert.match(path.getAttribute('d'), /^M .* H .* V /);
    assert.equal(root.querySelector('.methods-progress-pair'), null);
    assert.doesNotMatch(root.textContent, /999|1000/);
    point(root, 'improved').dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
    assert.deepEqual(selections, [['solution', 'improved']]);
  } finally {dom.window.close();}
});

test('different native units require separate metric selection and known null display does not fall back', () => {
  const {dom, root, render} = mount();
  try {
    render(data({experiments: [experiment('radii'), experiment('time', 2, 1, {display_metric: 'runtime_seconds'}),
      experiment('missing', 5, 9, {display_control_score: null, display_treatment_score: null})]}));
    assert.ok(point(root, 'radii')); assert.equal(point(root, 'time'), undefined);
    assert.equal(point(root, 'missing').querySelector('circle'), null);
    assert.ok(point(root, 'missing').querySelector('.methods-progress-unmeasured'));
    const select = root.querySelector('select'); assert.equal(select.parentElement.hidden, false);
    select.value = 'runtime_seconds'; select.dispatchEvent(new dom.window.Event('change', {bubbles: true}));
    assert.equal(point(root, 'radii'), undefined); assert.ok(point(root, 'time'));
    assert.equal(root.querySelector('.methods-progress-metric').textContent, 'runtime_seconds');
    render(data({experiments: [experiment('radii'), experiment('time', 2, 1, {display_metric: 'runtime_seconds'})]}));
    assert.equal(root.querySelector('select').value, 'runtime_seconds');
  } finally {dom.window.close();}
});

test('invalid, missing and nonfinite tool results are never rendered as zero', () => {
  const {dom, root, render} = mount();
  try {
    render(data({experiments: [
      experiment('invalid', 0, 0, {valid_treatment: false, results: {control: [measurement(0, false)], treatment: [measurement(0, false)]}}),
      experiment('missing', null, null, {results: {control: [{status: 'failed', measurement: null}], treatment: [{status: 'unknown', measurement: null}]}}),
      experiment('nonfinite', Infinity, NaN), experiment('unknown-unit', 42, 47, {display_metric: null}),
    ]}));
    assert.equal(root.querySelector('circle'), null);
    assert.equal(root.querySelectorAll('.methods-progress-unmeasured').length, 4);
    assert.match(root.textContent, /No valid tool measurements yet/);
    assert.match(root.querySelector('.methods-progress-scope').textContent, /4 experiments have no valid measurement/);
    assert.doesNotMatch(root.querySelector('svg').outerHTML, /NaN|Infinity/);
  } finally {dom.window.close();}
});

test('zero is a valid measured value, but solution experiments are not mixed into tool comparisons', () => {
  const {dom, root, render} = mount();
  try {
    render(data({experiments: [experiment('zero', 0, 0), experiment('canonical', 2.5, 2.6, {purpose: 'solution'})]}));
    assert.equal(point(root, 'canonical'), undefined);
    assert.equal(point(root, 'zero').querySelector('[data-arm="treatment"]').dataset.value, '0');
    assert.equal(root.querySelector('.methods-progress-empty').hidden, true);
  } finally {dom.window.close();}
});

test('poll refresh preserves shell, tab choice, selected record, focus and current callback', () => {
  const {dom, root, render, selections} = mount();
  try {
    render(data({experiments: [experiment('first'), experiment('second')]}));
    const shell = root.querySelector('section'), mode = root.querySelector('[data-progress-mode="experiments"]');
    point(root, 'first').focus(); point(root, 'first').dispatchEvent(new dom.window.MouseEvent('click', {bubbles: true}));
    render(data({experiments: [experiment('first'), experiment('second')], solutions: [solution('new', 2.7)]}));
    assert.equal(root.querySelector('section'), shell); assert.equal(root.querySelector('[data-progress-mode="experiments"]'), mode);
    assert.equal(mode.getAttribute('aria-pressed'), 'true');
    assert.equal(dom.window.document.activeElement.dataset.progressPoint, 'first');
    assert.ok(point(root, 'first').classList.contains('is-selected'));
    assert.equal(root.querySelector('.methods-progress-tooltip').hidden, false);
    point(root, 'first').dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true}));
    assert.equal(dom.window.document.activeElement.dataset.progressPoint, 'second');
    point(root, 'second').dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: ' ', bubbles: true}));
    assert.deepEqual(selections, [['experiment', 'first'], ['experiment', 'second']]);
    point(root, 'second').dispatchEvent(new dom.window.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    assert.equal(root.querySelector('.methods-progress-tooltip').hidden, true);
    choose(root, 'solutions'); render(data({solutions: [solution('next', 2.8)], experiments: [experiment('third')]}));
    assert.equal(root.querySelector('[data-progress-mode="solutions"]').getAttribute('aria-pressed'), 'true');
  } finally {dom.window.close();}
});

test('chronological records and partial history are explicit; clipped solution line is not a lifetime best', () => {
  const {dom, root, render} = mount();
  try {
    render(data({summary: {solutions: 500, history_complete: false}, solutions: [solution('later', 2.6, {at: 30}), solution('earlier', 2.5, {at: 20})], quality: {direction: 'max', best_native_score: 999}}));
    assert.deepEqual([...root.querySelectorAll('[data-progress-point]')].map(node => node.dataset.progressPoint), ['earlier', 'later']);
    assert.match(root.querySelector('.methods-progress-scope').textContent, /Partial \/ bounded history/);
    assert.match(root.querySelector('.methods-progress-legend').textContent, /Best in displayed history/);
    assert.doesNotMatch(root.textContent, /999/);
    assert.match(root.querySelector('svg').textContent, /Solution order · displayed history/);
    render(data({experiments: Array.from({length: 230}, (_, index) => experiment('e' + index, 2.5, 2.6, {at: index}))}));
    choose(root, 'experiments');
    assert.equal(root.querySelectorAll('[data-progress-point]').length, 200);
    assert.equal(point(root, 'e0'), undefined); assert.ok(point(root, 'e30'));
    assert.match(root.querySelector('.methods-progress-scope').textContent, /Partial \/ bounded history/);
  } finally {dom.window.close();}
});

test('minimization best line respects direction; unknown direction does not invent one', () => {
  const {dom, root, render} = mount();
  try {
    const solutions = [solution('s1', 3, {at: 1}), solution('s2', 2, {at: 2}), solution('s3', 4, {at: 3})];
    render(data({quality: {direction: 'min'}, solutions}));
    const path = root.querySelector('[data-progress-best]').getAttribute('d');
    const levels = [...path.matchAll(/ V ([\d.]+)/g)].map(match => Number(match[1]));
    assert.equal(levels.length, 2); assert.equal(levels[0], levels[1]);
    assert.match(root.querySelector('.methods-progress-scope').textContent, /Lower is better/);
    render(data({quality: {}, solutions}));
    assert.equal(root.querySelector('[data-progress-best]'), null);
    assert.match(root.querySelector('.methods-progress-scope').textContent, /direction not recorded/);
  } finally {dom.window.close();}
});

test('empty solutions keep real call activity and known costs visible without treating unknown as free', () => {
  const {dom, root, render, selections} = mount();
  try {
    render(data({proposals: [{id: 'p2', at: 2, index: 1, lab_id: 'lab-a', cost: null, status: 'unknown'}, {id: 'p1', at: 1, index: 0, lab_id: 'lab-a', cost: .03, status: 'completed'}, {id: 'p3', at: 3, cost: 0, status: 'refused'}]}));
    choose(root, 'solutions');
    assert.match(root.textContent, /No evaluated solutions yet/);
    assert.match(root.querySelector('.methods-progress-activity').textContent, /3 model calls.*Known call spend \$0.0300 · 1 costs unknown/);
    assert.equal(root.querySelectorAll('.methods-progress-call').length, 3);
    assert.match(root.querySelector('[data-progress-proposal="p3"]').title, /\$0\.0000/);
    root.querySelector('[data-progress-proposal="p2"]').click();
    assert.deepEqual(selections, [['proposal', 'p2']]);
  } finally {dom.window.close();}
});

test('untrusted saved text cannot inject markup into hover cards or controls', () => {
  const {dom, root, render} = mount();
  try {
    const evil = '<img src=x onerror=alert(1)>';
    render(data({experiments: [experiment('safe', 2, 3, {question: evil, lab_id: evil, display_metric: evil})]}));
    point(root, 'safe').focus();
    assert.equal(root.querySelector('img'), null); assert.equal(root.querySelector('script'), null);
    assert.match(root.querySelector('.methods-progress-tooltip').textContent, /<img src=x/);
    assert.equal(root.querySelector('.methods-progress-metric').textContent, evil);
  } finally {dom.window.close();}
});

test('responsive Y ticks fit the margin while hover values keep complete measurement precision', () => {
  const {dom, root, render} = mount();
  try {
    const measured = 2.765761097432189;
    render(data({experiments: [experiment('precise', 2.72356182418851, measured)]}));
    const labels = [...root.querySelectorAll('[data-progress-y-tick]')].map(node => node.textContent);
    assert.equal(labels.length, 5);
    assert.ok(labels.every(text => text.length <= 8));
    assert.equal(new Set(labels).size, 5);
    assert.ok(labels.every(text => text.startsWith('2.')));
    point(root, 'precise').focus();
    assert.match(root.querySelector('.methods-progress-tooltip').textContent, /2\.765761097432189/);
    render(data({experiments: [experiment('narrow', 2.765761097432189, 2.765761097438189)]}));
    const deltas = [...root.querySelectorAll('[data-progress-y-tick]')].map(node => node.textContent);
    assert.ok(deltas.every(text => text.startsWith('Δ') && text.length <= 8));
    assert.equal(new Set(deltas).size, 5);
    assert.match(root.querySelector('.methods-progress-scope').textContent, /Y-axis Δ ticks are changes from 2\./);
    point(root, 'narrow').focus();
    assert.match(root.querySelector('.methods-progress-tooltip').textContent, /2\.765761097438189/);
  } finally {dom.window.close();}
});
