import { badge, esc, format, key, numeric, state, toleranceLabel } from './dashboard-state.js';

export function metricLabel() {
  const label =
    state.snapshot?.benchmark?.metric || state.snapshot?.metric_display?.label || 'Score';
  // Keep recorded identifiers untouched; captions turn generic case keys into
  // readable labels without rewriting acronyms or assigning task semantics.
  const words = String(label).replace(/_/g, ' ').trim();
  return words ? words[0].toUpperCase() + words.slice(1) : 'Score';
}

export function metricDisplay(row, field = 'metric_display', scoreKey = 'score') {
  const view = row?.[field];
  if (view?.schema === 'sciel-metric-display/1') {
    if (numeric(row?.[scoreKey]) && numeric(view.raw_score) && row[scoreKey] !== view.raw_score)
      return {
        ...view,
        status: 'unknown',
        value: null,
        reason: 'Score and measurement binding differ',
      };
    return view;
  }
  // An older response may expose only controller scores. Never reinterpret
  // those as a physical measurement just because a benchmark is configured.
  const raw = row?.[scoreKey];
  const rawOnly = !state.snapshot?.metric_display && !state.snapshot?.benchmark;
  return {
    status: rawOnly && numeric(raw) ? 'measured' : 'unknown',
    value: rawOnly && numeric(raw) ? raw : null,
    label: rawOnly ? 'Score' : metricLabel(),
    raw_score: numeric(raw) ? raw : null,
    metric_sha256: rawOnly ? 'legacy-raw-score' : null,
    reason: 'Measurement metadata not recorded',
  };
}

export function measuredValue(view) {
  return view?.status === 'measured' && numeric(view.value) ? view.value : null;
}

export function metricStatus(view) {
  return (
    { invalid_penalty: 'Invalid result', failed: 'Evaluation failed', unknown: 'Not measured' }[
      view?.status
    ] || 'Measured'
  );
}

export function metricText(view, digits = 6) {
  if (measuredValue(view) !== null) return format(view.value, digits);
  const raw = numeric(view?.raw_score)
    ? ' (' +
      (view.status === 'invalid_penalty' ? 'penalty score ' : 'raw score ') +
      format(view.raw_score, digits) +
      ')'
    : '';
  return metricStatus(view) + raw;
}

export function metricHTML(view, digits = 6) {
  if (measuredValue(view) !== null) return esc(format(view.value, digits));
  const raw = numeric(view?.raw_score)
    ? '<small>' +
      (view.status === 'invalid_penalty' ? 'Penalty score ' : 'Raw score ') +
      esc(format(view.raw_score, digits)) +
      '</small>'
    : '';
  return (
    '<span class="metric-outcome ' +
    (view?.status === 'invalid_penalty' || view?.status === 'failed' ? 'negative-text' : '') +
    '" title="' +
    esc(view?.reason || '') +
    '">' +
    esc(metricStatus(view)) +
    raw +
    '</span>'
  );
}

export function metricDifference(child, parent) {
  return measuredValue(child) !== null &&
    measuredValue(parent) !== null &&
    child.metric_sha256 &&
    child.metric_sha256 === parent.metric_sha256
    ? child.value - parent.value
    : null;
}

export function trialDifference(row) {
  return metricDifference(
    metricDisplay(row),
    metricDisplay(row, 'parent_metric_display', 'parent_score'),
  );
}

export function metricBadge(row) {
  const view = metricDisplay(row);
  return view.status === 'invalid_penalty'
    ? '<span class="badge negative">Invalid result · penalty</span>'
    : view.status === 'failed'
      ? badge('eval_fail')
      : view.status === 'unknown' && row.status === 'evaluated'
        ? '<span class="badge neutral">Measurement unavailable</span>'
        : badge(row.status);
}

export function referenceGapText(gap) {
  if (gap === 0) return 'equal';
  const magnitude = Math.abs(gap),
    digits = magnitude < 0.01 ? 6 : magnitude < 1 ? 4 : 2;
  return (
    (magnitude < 0.000001 ? '<0.000001' : magnitude.toFixed(digits)) +
    '% ' +
    (gap > 0 ? 'below' : 'above')
  );
}

export function referenceComparisonsHTML(reference, value) {
  if (!reference || !numeric(value) || reference.current_value !== value) return '';
  const legacy = {
    status: 'known',
    label: 'Best known',
    value: reference.value,
    current_value: reference.current_value,
    tolerance: reference.reference_tolerance,
    name: reference.source_label,
    source_url: reference.source_url,
  };
  return [
    ['best-known', reference.best_known || legacy, 'Best known'],
    ['ai-search', reference.best_ai_method, 'Best AI search'],
  ]
    .map(([key, item, label]) => {
      label = item?.label || label;
      const comparable =
        item?.status === 'known' &&
        numeric(item.value) &&
        item.value > 0 &&
        item.current_value === value &&
        numeric(reference.run_tolerance) &&
        item.tolerance === reference.run_tolerance;
      const text = comparable
        ? (item.value === value
            ? 'matches'
            : referenceGapText(((item.value - value) / item.value) * 100)) +
          ' ' +
          label.toLowerCase()
        : label + ': not available';
      const title = comparable
        ? (item.name || label) +
          ' · ' +
          (item.value_label || item.value) +
          ' · ' +
          toleranceLabel(item.tolerance) +
          ' · gap ' +
          (((item.value - value) / item.value) * 100).toPrecision(8) +
          '% · ' +
          (item.source_url || '') +
          ' · ' +
          (reference.note || '')
        : item?.reason ||
          'A comparable reference with a recorded method classification is not available.';
      return (
        '<span class="benchmark-reference-gap" data-reference-comparison="' +
        key +
        '" title="' +
        esc(title) +
        '">| ' +
        esc(text) +
        '</span>'
      );
    })
    .join(' ');
}
