// Descriptive summaries of saved measurements within one evaluator contract.
// Elapsed-to-best is a recorded endpoint, never a reconstructed search curve.
const finite = value => typeof value === 'number' && Number.isFinite(value);
const measured = row => row.measurement_status === 'measured' && finite(row.best_score);
const elapsed = row => finite(row.to_best_wall_seconds) && row.to_best_wall_seconds >= 0
  ? row.to_best_wall_seconds : null;
const identityFields = ['task_id', 'protocol', 'metric', 'direction', 'units'];
const modelName = row => Array.isArray(row.models)
  ? row.models.filter(value => typeof value === 'string' && value.trim()).join(' + ') : '';

/**
 * Input must already be filtered to one exact task/evaluator/metric contract.
 * Counts include every process state; only explicit measured outcomes qualify.
 * Returned rows retain their own seed, status and resources, without mutation.
 */
export function researchSummary(rows, {budgetSeconds = 900} = {}) {
  if (!Array.isArray(rows)) throw new TypeError('Research rows must be an array.');
  if (!finite(budgetSeconds) || budgetSeconds < 0) {
    throw new RangeError('The elapsed-time budget must be finite and nonnegative.');
  }
  let identity = null;
  for (const row of rows) {
    if (!row || identityFields.some(field => typeof row[field] !== 'string' || !row[field].trim()) ||
        !['maximize', 'minimize'].includes(row.direction)) {
      throw new TypeError('Research rows require a complete evaluator contract.');
    }
    const next = JSON.stringify(identityFields.map(field => row[field]));
    if (identity !== null && next !== identity) {
      throw new RangeError('Research comparisons require one exact evaluator cohort.');
    }
    identity = next;
  }
  const sign = rows[0]?.direction === 'minimize' ? -1 : 1;
  const compare = (a, b) => sign * (b.best_score - a.best_score) ||
    (elapsed(a) ?? Infinity) - (elapsed(b) ?? Infinity);
  const bestOf = records => records.length ? [...records].sort(compare)[0] : null;
  const medianOf = records => {
    if (!records.length) return null;
    const values = records.map(row => row.best_score).sort((a, b) => a - b);
    const middle = Math.floor(values.length / 2);
    return values.length % 2 ? values[middle] : values[middle - 1] / 2 + values[middle] / 2;
  };
  const summarize = records => {
    const observations = records.filter(measured);
    const paired = observations.filter(row => finite(row.seed_score));
    return {
      measured: observations.length,
      paired: paired.length,
      improved: paired.filter(row => sign * (row.best_score - row.seed_score) > 0).length,
      best: bestOf(observations),
      median: medianOf(observations),
    };
  };
  const observations = rows.filter(measured);
  const timed = observations.filter(row => elapsed(row) !== null);
  const buckets = new Map();
  for (const row of rows) {
    const model = modelName(row);
    if (!buckets.has(model)) buckets.set(model, []);
    buckets.get(model).push(row);
  }
  const groups = [...buckets].sort(([a], [b]) => a.localeCompare(b)).map(([model, records]) => ({
    model: model || 'Model not recorded', rows: records, ...summarize(records),
  }));
  // Strict dominance retains duplicate observed endpoints. Missing times never
  // stand for zero; equal-time points with a worse score are dominated.
  const frontier = timed.filter(row => !timed.some(other =>
    elapsed(other) <= elapsed(row) && sign * (other.best_score - row.best_score) >= 0 &&
    (elapsed(other) < elapsed(row) || sign * (other.best_score - row.best_score) > 0)
  )).sort((a, b) => elapsed(a) - elapsed(b) || compare(a, b));
  const summary = summarize(rows);
  return {
    recorded: rows.length,
    measured: summary.measured,
    paired: summary.paired,
    improved: summary.improved,
    modelCount: [...buckets.keys()].filter(Boolean).length,
    best: summary.best,
    bestWithinBudget: bestOf(timed.filter(row => elapsed(row) <= budgetSeconds)),
    timed: timed.length,
    groups,
    frontier,
  };
}
