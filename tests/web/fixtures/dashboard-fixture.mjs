/**
 * Hand-authored HTTP data for browser interaction tests.
 * These records are synthetic UI fixtures, not archived research results.
 * Native journal parsing and HTTP integration are covered by tests/observer/.
 * No model transcripts, experiment code, private paths or paid-run logs are copied.
 */
export const fixtureRun = {
  id: 'synthetic-main', run_id: 'synthetic-research', name: 'Synthetic study',
  path: 'fixtures/synthetic-main', task: 'test/synthetic', status: 'completed',
  seed: 42, best_score: 0.9, last_modified: '2026-01-01T12:00:00Z', engineering_only: true,
};
export const runIndex = [fixtureRun, ...Array.from({length: 6}, (_, index) => ({
  ...fixtureRun, id: `synthetic-${index}`, run_id: `synthetic-research-${index}`,
  name: `Synthetic study ${index + 1}`, path: `fixtures/study-${index}/${index < 2 ? 'cards_off' : 'cards_on'}`,
}))];

function makeSnapshot(run) {
  const trials = Array.from({length: 7}, (_, index) => ({
    id: index === 2 ? 'r000002a1' : `synthetic-r${index + 1}`,
    candidate_id: `p${index + 1}`, parent_id: index ? `p${index}` : null,
    iteration: index + 1, score: 0.3 + index / 10, parent_score: 0.2 + index / 10,
    status: index < 4 ? 'evaluated' : 'eval_fail', code_available: true,
    operator: 'diff', forecast_verdict: 'INCONCLUSIVE',
    hypothesis: {text: `Synthetic hypothesis ${index + 1}`, reasoning: 'Hand-authored interaction fixture.',
      predicted_low: 0, predicted_high: 0.1, confidence: 0.5},
    conclusion: {explanation: 'Synthetic conclusion. No experiment was executed.'},
  }));
  return {
    kind: 'engine', run, stats: {best_score: 0.9, seed_score: 0.2, iterations: 7, attempts: 7,
      evaluations: 4, cost_total: 0.1157, cost_status: 'recorded', hypotheses: 7, lessons: 1, reflections: 1},
    metric_display: {label: 'Score', units: null, schema: 'sciel-metric-display/1'},
    trials, hypotheses: structuredClone(trials),
    lessons: [{id: 'synthetic-lesson', rule: 'A synthetic lesson for evidence navigation.', scope: 'global',
      polarity: 'negative', status: 'active', evidence_ids: ['r000002a1'], exposure_count: 2}],
    events: Array.from({length: 75}, (_, index) => ({seq: index + 1, event: index === 0 ? 'run_start' : 'research',
      phase: index === 0 ? 'run_start' : 'outcome', timestamp: `2026-01-01T12:${String(Math.floor(index / 60)).padStart(2, '0')}:${String(index % 60).padStart(2, '0')}Z`,
      data: {synthetic: true, message: `Synthetic event ${index + 1}`}})),
    curves: trials.slice(0, 4).map(row => ({...row, best_score: row.score, cost_total: row.iteration * 0.01})),
    programs: trials, warnings: [], runtime: {available: false, active: false},
    architecture: {recorded: true, source: 'synthetic fixture', summary: 'Synthetic configuration.',
      stages: [], sections: [], warnings: [], graph: {nodes: [
        {id: 'parent', label: 'Parent selection', kind: 'core', status: 'enabled'},
        {id: 'generation', label: 'Generate', kind: 'core', status: 'enabled'},
        {id: 'evaluation', label: 'Evaluate', kind: 'core', status: 'enabled'},
        {id: 'population', label: 'Population', kind: 'core', status: 'enabled'},
      ], edges: []}},
  };
}

const workflowItems = [{id: 'synthetic-workflow-1', actor: 'model', title: 'Synthetic proposal',
  summary: 'Synthetic evidence used only to test the disclosure UI.', timestamp: '2026-01-01T12:00:01Z',
  status: 'recorded', details_available: true, detail_version: 'fixture-v1', refs: {program_id: 'p3'}}];

export function dashboardFixtureResponse(rawURL) {
  const url = new URL(rawURL, 'http://fixture.test');
  const parts = url.pathname.split('/').filter(Boolean).map(decodeURIComponent);
  if (parts.join('/') === 'api/runs') return {runs: runIndex};
  if (parts[0] !== 'api' || parts[1] !== 'runs') return null;
  const run = runIndex.find(item => item.id === parts[2]);
  if (!run) return null;
  if (parts.length === 3) return makeSnapshot(run);
  if (parts[3] === 'program') return {id: parts[4], parent_id: 'p2', code_source: 'checkpoint',
    code: '# Synthetic browser fixture; never executed.\ndef construct_packing():\n    return [], [], 0\n',
    parent_code: '# Synthetic browser fixture; never executed.\ndef construct_packing():\n    return None\n',
    diff: '@@ -2,2 +2,2 @@\n def construct_packing():\n-    return None\n+    return [], [], 0\n',
    source_sha256: 'a'.repeat(64), parent_source_sha256: 'b'.repeat(64)};
  if (parts[3] === 'workflow' && parts.length === 4) return {items: workflowItems, total: workflowItems.length, has_more: false, next_before: null, warnings: []};
  if (parts[3] === 'workflow' && parts[4] === 'synthetic-workflow-1') return {id: parts[4], sections: [
    {label: 'Synthetic saved evidence', format: 'text', text: 'This is hand-authored test evidence, not a model response.'}], warnings: []};
  if (parts[3] === 'llm-calls') return {items: [], total: 0, has_more: false};
  return null;
}
