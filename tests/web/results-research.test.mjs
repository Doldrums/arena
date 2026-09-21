import {test} from 'node:test';
import assert from 'node:assert/strict';
import {researchSummary} from '../../web/results-research.js';

const row = (id, score, seconds, extra = {}) => ({
  id, task_id: 'recorded/task', protocol: 'exact-protocol', metric: 'quality',
  direction: 'maximize', units: 'dimensionless', models: ['model-a'],
  measurement_status: 'measured', best_score: score, seed_score: 0,
  to_best_wall_seconds: seconds, state: 'paused', tokens: null, ...extra,
});
const ids = rows => rows.map(value => value.id);

test('summaries retain paused, stopped and failed-process observations without rewriting their evidence', () => {
  const records = [
    row('paused', 4, 20, {seed_score: 2}),
    row('stopped', 8, 30, {state: 'stopped', seed_score: 5}),
    row('failed-process', 6, 10, {state: 'failed', seed_score: 7, tokens: 12}),
    row('unknown-score', 999, 1, {measurement_status: 'unknown'}),
    row('unmeasured-zero', 0, 0, {measurement_status: 'invalid_penalty'}),
    row('missing-measurement-status', 100, 2, {measurement_status: undefined}),
  ];
  const before = structuredClone(records);
  for (const record of records) { Object.freeze(record.models); Object.freeze(record); }
  Object.freeze(records);
  const result = researchSummary(records);
  assert.equal(result.recorded, 6);
  assert.equal(result.measured, 3);
  assert.equal(result.paired, 3);
  assert.equal(result.improved, 2);
  assert.equal(result.timed, 3);
  assert.strictEqual(result.best, records[1]);
  assert.equal(result.best.seed_score, 5, 'the winning row keeps its own seed');
  assert.equal(result.groups[0].median, 6);
  assert.deepEqual(records, before);
  assert.ok(!('usd' in result), 'token values never become a currency estimate');
});

test('minimization reverses quality comparisons while retaining measured zero and missing seeds', () => {
  const records = [
    row('high', 9, 5, {direction: 'minimize', seed_score: 10}),
    row('zero', 0, 10, {direction: 'minimize', seed_score: 4}),
    row('unpaired', -1, null, {direction: 'minimize', seed_score: null}),
    row('worse', 8, 12, {direction: 'minimize', seed_score: 7}),
    row('nan', NaN, 1, {direction: 'minimize'}),
    row('infinite', Infinity, 1, {direction: 'minimize'}),
  ];
  const result = researchSummary(records, {budgetSeconds: 10});
  assert.equal(result.measured, 4);
  assert.equal(result.paired, 3);
  assert.equal(result.improved, 2);
  assert.strictEqual(result.best, records[2]);
  assert.strictEqual(result.bestWithinBudget, records[1]);
  assert.deepEqual(ids(result.frontier), ['high', 'zero']);
  assert.equal(result.groups[0].median, 4);
});

test('equal quality prefers the least recorded elapsed time and never interprets a missing time as zero', () => {
  const records = [row('unknown-time', 8, null), row('slower', 8, 50), row('fastest', 8, 0),
    row('negative-time', 8, -1), row('infinite-time', 8, Infinity)];
  const result = researchSummary(records, {budgetSeconds: 0});
  assert.strictEqual(result.best, records[2]);
  assert.strictEqual(result.bestWithinBudget, records[2]);
  assert.equal(result.timed, 2);
  assert.deepEqual(ids(result.frontier), ['fastest']);
  assert.equal(researchSummary([records[0], records[3]]).bestWithinBudget, null);
});

test('budget selection is a recorded endpoint inside the bound, not an interpolated threshold time', () => {
  const records = [row('within', 5, 899), row('boundary', 7, 900), row('later-best', 9, 901)];
  const result = researchSummary(records);
  assert.strictEqual(result.best, records[2]);
  assert.strictEqual(result.bestWithinBudget, records[1]);
  assert.strictEqual(researchSummary(records, {budgetSeconds: 899}).bestWithinBudget, records[0]);
  assert.equal(researchSummary(records, {budgetSeconds: 1}).bestWithinBudget, null);
  assert.deepEqual(ids(result.frontier), ['within', 'boundary', 'later-best']);
});

test('frontier retains exact duplicate endpoints and removes strictly dominated observations', () => {
  const records = [row('same-a', 4, 10), row('same-b', 4, 10), row('slower-same', 4, 20),
    row('worse-same-time', 3, 10), row('higher-later', 8, 30), row('untimed-high', 10, null)];
  const result = researchSummary(records);
  assert.deepEqual(ids(result.frontier), ['same-a', 'same-b', 'higher-later']);
  assert.strictEqual(result.best, records[5]);
  assert.strictEqual(result.bestWithinBudget, records[4]);
});

test('model groups retain all rows and denominators, with measured-only medians and original best rows', () => {
  const records = [row('b1', 4, 1, {models: ['b', 'helper']}), row('a1', 2, 2),
    row('a2', 6, 4), row('b-unknown', null, null, {models: ['b', 'helper'], measurement_status: 'unknown'}),
    row('unattributed', 1, 1, {models: []})];
  const result = researchSummary(records);
  assert.equal(result.modelCount, 2, 'missing attribution does not invent a model configuration');
  const a = result.groups.find(group => group.model === 'model-a');
  const b = result.groups.find(group => group.model === 'b + helper');
  assert.deepEqual(ids(a.rows), ['a1', 'a2']);
  assert.equal(a.median, 4);
  assert.strictEqual(a.best, records[2]);
  assert.equal(b.rows.length, 2);
  assert.equal(b.measured, 1);
  assert.equal(b.paired, 1);
  assert.equal(b.improved, 1);
  assert.equal(b.median, 4);
  assert.equal(result.groups.find(group => group.model === 'Model not recorded').rows.length, 1);
});

test('comparisons reject any mixed evaluator identity, including units and score direction', () => {
  for (const [field, value] of [['task_id', 'other/task'], ['protocol', 'other-protocol'],
    ['metric', 'other-metric'], ['direction', 'minimize'], ['units', 'millimetres']]) {
    assert.throws(() => researchSummary([row('a', 1, 1), row('b', 2, 2, {[field]: value})]),
      /one exact evaluator cohort/, field);
  }
  assert.throws(() => researchSummary([row('missing', 1, 1, {protocol: null})]), /complete evaluator contract/);
  assert.throws(() => researchSummary([row('bad-direction', 1, 1, {direction: 'unknown'})]), /complete evaluator contract/);
});

test('empty or unmeasured cohorts return explicit empty summaries and reject invalid budgets', () => {
  assert.deepEqual(researchSummary([]), {
    recorded: 0, measured: 0, paired: 0, improved: 0, modelCount: 0,
    best: null, bestWithinBudget: null, timed: 0, groups: [], frontier: [],
  });
  const result = researchSummary([row('unknown', null, null, {measurement_status: 'unknown'})]);
  assert.equal(result.recorded, 1);
  assert.equal(result.measured, 0);
  assert.equal(result.best, null);
  assert.equal(result.groups[0].median, null);
  for (const budgetSeconds of [-1, NaN, Infinity, '900']) {
    assert.throws(() => researchSummary([], {budgetSeconds}), /finite and nonnegative/);
  }
});
