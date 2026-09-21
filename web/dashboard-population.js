import { $, empty, esc, format, scientificIdentity, state } from './dashboard-state.js';
import { destroyPopulationMap, renderPopulationMap } from './population.js';
import { renderStorageSpace } from './storage-view.js';
import {
  measuredValue,
  metricDisplay,
  metricHTML,
  metricLabel,
  metricText,
} from './dashboard-metrics.js';
import { renderPlot } from './dashboard-chart.js';
import { switchTab } from './dashboard-tabs.js';
import { renderPopulationPreview } from './population-preview.js';

export function destroyPopulation() {
  const mount = $('population-map');
  if (mount) destroyPopulationMap(mount);
}

export function historyLinks(ids) {
  return (Array.isArray(ids) ? ids : [])
    .slice(0, 12)
    .map(
      (id) =>
        '<button class="inline-link mono" data-candidate="' +
        esc(id) +
        '">' +
        esc(id) +
        ' ↗</button>',
    )
    .join(', ');
}

export function resultHistoryDetailHTML(history) {
  if (!history) return '';
  const facts = [];
  if (history.alias_kind)
    facts.push(
      '<p>' +
        esc(history.alias_kind === 'seed_copy' ? 'Shared seed measurement' : 'Migration copy') +
        ' · not a new evaluation.</p>',
    );
  if (history.source_match_count > 0)
    facts.push(
      '<p>Same source · ' +
        esc(history.source_match_count) +
        ' other program IDs: ' +
        historyLinks(history.source_matches) +
        '</p>',
    );
  if (history.ast_match_count > 0)
    facts.push(
      '<p>Same structural AST · ' +
        esc(history.ast_match_count) +
        ' other program IDs: ' +
        historyLinks(history.ast_matches) +
        '</p>',
    );
  if (history.output_match_count > 0)
    facts.push(
      '<p><strong>Same recorded output</strong> · ' +
        esc(history.output_match_count) +
        ' other evaluations: ' +
        historyLinks(history.output_matches) +
        '</p><p>Exact saved output match across the run, including other islands and former members. These measurements are unpaired; algorithm equivalence and runtime benefit are not established.</p>',
    );
  else
    facts.push(
      '<p>' +
        esc(
          history.output_status === 'unavailable'
            ? 'No comparable saved output is available.'
            : history.output_comparison_available === false || history.output_match_count == null
              ? 'Output comparison unavailable: evaluation identity is not recorded.'
              : 'No other evaluation with this exact saved output in the covered history.',
        ) +
        '</p>',
    );
  const coverage = state.snapshot?.result_history?.coverage;
  if (coverage)
    facts.push(
      '<p class="history-note">' +
        esc(
          'Saved history through iteration ' +
            (coverage.iteration ?? 'not recorded') +
            (coverage.stale ? ' · newer measurements are not covered yet.' : '.'),
        ) +
        '</p>',
    );
  facts.push(
    '<p class="history-note">Equal scores alone are not counted as repeated outputs. Listed links are capped at 12.</p>',
  );
  return (
    '<section class="result-history-detail" aria-label="Whole-run identity and output history"><h3>Across saved run history</h3>' +
    facts.join('') +
    '</section>'
  );
}

export function renderResultHistory() {
  const mount = $('population-history'),
    view = state.snapshot.result_history;
  if (!mount) return;
  if (!view) {
    mount.innerHTML = '';
    return;
  }
  const wasOpen = mount.querySelector('details')?.open === true,
    c = view.counts || {},
    coverage = view.coverage || {};
  const count = (value) => (Number.isInteger(value) ? String(value) : 'not recorded');
  const repeats = Object.entries(view.by_program || {}).filter(
    ([id, h]) => h.output_match_count > 0 && !h.alias_kind && h.first_output_program_id !== id,
  );
  mount.innerHTML =
    '<details class="result-history-summary"' +
    (wasOpen ? ' open' : '') +
    '><summary>Run-wide history <span>' +
    esc(count(c.unique_sources)) +
    ' source variants · ' +
    esc(count(c.repeated_outputs)) +
    ' repeated outputs · ' +
    esc(count(c.source_aliases)) +
    ' source copies</span></summary><div class="result-history-body"><p>All islands, including former members. Repeated outputs count separate measurements; seed and migration copies do not add evaluations.</p><p>' +
    esc(
      'Comparable saved outputs: ' +
        count(coverage.output_evaluations) +
        ' of ' +
        count(c.evaluations) +
        ' finished evaluations. Output history covers saved admitted programs; rejected candidates may have no output observation.',
    ) +
    '</p><p>' +
    esc(
      'Saved through iteration ' +
        (coverage.iteration ?? 'not recorded') +
        (coverage.stale ? ' · newer measurements are not covered yet.' : '.'),
    ) +
    '</p>' +
    repeats
      .slice(0, 12)
      .map(
        ([id, h]) =>
          '<p>' +
          historyLinks([id]) +
          ' has the same recorded output as ' +
          historyLinks([h.first_output_program_id || h.earliest_output_match].filter(Boolean)) +
          '</p>',
      )
      .join('') +
    (repeats.length > 12
      ? '<p>Showing 12 matching programs. Open individual source cards for their history.</p>'
      : '') +
    '<p class="history-note">Exact saved output does not establish algorithm equivalence. Score ties are not used as output fingerprints.</p></div></details>';
}

export function updatePopulationMap() {
  const mount = $('population-map');
  if (!mount || !state.snapshot?.population) return;
  renderPopulationMap(mount, state.snapshot.population, {
    runKey: scientificIdentity(state.snapshot),
    storageRenderer: renderStorageSpace,
    metricLabel: metricLabel(),
    metricValue: (row, field = 'metric_display', scoreKey = 'score') =>
      measuredValue(metricDisplay(row, field, scoreKey)),
    formatScore: (value, row, field = 'metric_display') =>
      row
        ? metricText(
            metricDisplay(row, field, field === 'best_metric_display' ? 'best_score' : 'score'),
            6,
          )
        : format(value, 6),
    live: state.snapshot.runtime?.active === true && state.timingConnected,
    follow: state.follow,
    onProgram: (id, { action } = {}) => {
      state.selected = id;
      state.detail = null;
      state.codeMode = action === 'source' ? 'code' : 'diff';
      renderPlot();
      switchTab('code');
    },
  });
}

export function updatePopulationPreview() {
  if (!state.snapshot || state.snapshot.kind === 'methods' || state.snapshot.run.kind === 'methods')
    return;
  renderPopulationPreview($('population-preview'), state.snapshot.population, {
    runKey: scientificIdentity(state.snapshot),
    metricLabel: metricLabel(),
    follow: state.follow,
    formatScore: (value, row) => metricText(metricDisplay(row), 6),
    onOpen: () => {
      switchTab('population');
      $('tab-content').scrollIntoView({
        behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
          ? 'instant'
          : 'smooth',
        block: 'start',
      });
    },
    onProgram: (id, { action } = {}) => {
      state.selected = id;
      state.detail = null;
      state.codeMode = action === 'source' ? 'code' : 'diff';
      renderPlot();
      switchTab('code');
    },
  });
}

export function renderPopulation() {
  const population = state.snapshot.population;
  if (!population?.available && !population?.dynamics?.islands?.length) {
    destroyPopulation();
    $('tab-content').innerHTML = empty(
      'Population not recorded',
      'Islands and archive members appear after the engine saves a population snapshot.',
    );
    return;
  }
  if (!$('population-map'))
    $('tab-content').innerHTML =
      '<div id="population-history"></div><div id="population-map"></div><details id="population-details" class="population-storage-details"><summary>Storage details <span>Descriptor cells, members &amp; global archive</span></summary><div id="population-details-body"></div></details>';
  renderResultHistory();
  updatePopulationMap();
  if (!population.available) {
    $('population-details-body').innerHTML = empty(
      'Storage snapshot pending',
      'Configured islands are shown above. Individual members appear when recorded.',
    );
    return;
  }
  renderPopulationDetails(population);
}

export function renderPopulationDetails(population) {
  const layout = population.layout || {},
    descriptor = population.descriptor || {};
  const name =
    {
      map_elites: 'MAP-Elites',
      vq: 'VQ niches',
      pool: 'Population pool',
      geometry: 'Geometry container',
      unknown: 'Recorded population',
    }[layout.kind] || 'Recorded population';
  const memberLink = (member) =>
    member.id && member.code_available
      ? '<button class="inline-link mono" data-candidate="' +
        esc(member.id) +
        '">' +
        esc(member.id) +
        ' ↗</button>'
      : '<span class="mono">' + esc(member.id || 'ID not recorded') + '</span>';
  const gridHTML = (island) => {
    if (!island.grid_available) return '<p class="population-muted">Grid not recorded.</p>';
    if (layout.kind === 'pool')
      return '<p class="population-muted">Members are retained in a pool.</p>';
    const bins = layout.grid_bins;
    if (
      !Number.isInteger(bins) ||
      bins < 1 ||
      bins > 32 ||
      !['map_elites', 'vq'].includes(layout.kind)
    )
      return (
        '<div class="population-sparse">' +
        island.grid
          .map(
            (cell) =>
              '<span>Cell ' +
              esc(cell.x) +
              ', ' +
              esc(cell.y) +
              ' · ' +
              esc(metricText(metricDisplay(cell))) +
              '</span>',
          )
          .join('') +
        '</div>'
      );
    const size = 220,
      step = size / bins;
    let svg =
      '<svg viewBox="0 0 250 255" role="img" aria-label="' +
      esc(name + ' grid, island ' + island.id) +
      '"><title>Recorded grid cells. Horizontal: ' +
      esc(layout.x_label) +
      '. Vertical: ' +
      esc(layout.y_label) +
      '.</title>';
    for (let x = 0; x < bins; x++)
      for (let y = 0; y < bins; y++)
        svg +=
          '<rect class="population-empty-cell" x="' +
          (20 + x * step) +
          '" y="' +
          (5 + (bins - 1 - y) * step) +
          '" width="' +
          (step - 2) +
          '" height="' +
          (step - 2) +
          '" rx="2"/>';
    for (const cell of island.grid) {
      if (
        !Number.isInteger(cell.x) ||
        !Number.isInteger(cell.y) ||
        cell.x < 0 ||
        cell.y < 0 ||
        cell.x >= bins ||
        cell.y >= bins
      )
        continue;
      const member = island.members.find((member) => member.id === cell.candidate_id);
      const open = member?.code_available
        ? ' data-candidate="' + esc(member.id) + '" tabindex="0" role="button"'
        : '';
      svg +=
        '<rect class="population-filled-cell"' +
        open +
        ' x="' +
        (20 + cell.x * step) +
        '" y="' +
        (5 + (bins - 1 - cell.y) * step) +
        '" width="' +
        (step - 2) +
        '" height="' +
        (step - 2) +
        '" rx="2"><title>' +
        esc(cell.candidate_id || 'Elite ID not recorded') +
        ' · ' +
        esc(metricLabel()) +
        ' ' +
        esc(metricText(metricDisplay(cell), 9)) +
        ' · cell ' +
        cell.x +
        ', ' +
        cell.y +
        '</title></rect>';
    }
    return (
      svg +
      '<text x="130" y="241" text-anchor="middle">' +
      esc(layout.x_label) +
      '</text><text x="10" y="115" text-anchor="middle" transform="rotate(-90 10 115)">' +
      esc(layout.y_label) +
      '</text></svg>'
    );
  };
  let html =
    '<div class="population"><div class="population-heading"><div><h2>Islands & storage</h2><p>' +
    esc(name) +
    ' · ' +
    esc(population.island_count ?? population.islands.length) +
    ' islands · snapshot at iteration ' +
    esc(population.iteration ?? '—') +
    ' · ' +
    esc(population.source) +
    '</p></div><span class="badge ' +
    (population.stale ? 'warning' : 'neutral') +
    '">' +
    (population.stale ? 'Earlier snapshot' : 'Latest recorded population') +
    '</span></div>';
  html +=
    '<div class="population-pipeline"><span>Program source & behavior</span><b>→</b><span>' +
    esc(descriptor.kind || 'Descriptor not recorded') +
    '</span><b>→</b><span>' +
    esc(name) +
    '</span><b>→</b><span>Island elites & global archive</span></div>';
  html +=
    '<p class="population-muted">Cells show recorded storage bins. Embeddings can define the descriptor used by MAP-Elites. Storage space shows saved prototype or program vectors when available; it does not reconstruct missing embeddings.</p>';
  html +=
    '<div class="population-islands">' +
    population.islands
      .map(
        (island) =>
          '<article class="population-island"><div class="population-island-heading"><h3>Island ' +
          esc(island.id) +
          '</h3><span>' +
          esc(island.member_count) +
          ' members · ' +
          esc(island.grid_cell_count) +
          ' cells</span></div><div class="population-best">Best ' +
          esc(metricLabel().toLowerCase()) +
          ' <strong>' +
          metricHTML(metricDisplay(island, 'best_metric_display', 'best_score'), 9) +
          '</strong></div>' +
          gridHTML(island) +
          '<div class="population-members"><table><thead><tr><th>Program</th><th>' +
          esc(metricLabel()) +
          '</th><th>Role</th></tr></thead><tbody>' +
          island.members
            .map(
              (member) =>
                '<tr><td>' +
                memberLink(member) +
                '</td><td class="number">' +
                metricHTML(metricDisplay(member)) +
                '</td><td>' +
                esc(
                  member.grid_elite === true
                    ? 'Cell elite'
                    : member.grid_elite === false
                      ? 'Member'
                      : 'Membership only',
                ) +
                (member.archive_member === true ? ' · archive' : '') +
                '</td></tr>',
            )
            .join('') +
          '</tbody></table></div>' +
          (!island.members_available
            ? '<p class="population-muted">Individual members not recorded.</p>'
            : '') +
          (island.members_truncated || island.grid_truncated
            ? '<p class="population-muted">Display capped; counts include the complete recorded population.</p>'
            : '') +
          '</article>',
      )
      .join('') +
    '</div>';
  const archive = population.archive || {};
  html +=
    '<section class="population-archive"><h3>Global archive <span class="count-pill">' +
    esc(archive.count ?? 0) +
    '</span></h3><p class="population-muted">Archive membership is separate from island membership and cell elites.</p><div class="archive-members">' +
    (archive.members || [])
      .map(
        (member) =>
          '<div>' +
          memberLink(member) +
          '<strong>' +
          metricHTML(metricDisplay(member), 9) +
          '</strong></div>',
      )
      .join('') +
    '</div>' +
    (archive.truncated
      ? '<p class="population-muted">Showing the first recorded archive members; display capped.</p>'
      : '') +
    '</section>';
  if (population.warnings?.length)
    html +=
      '<div class="architecture-notes">' +
      population.warnings.map((note) => '<p>' + esc(note) + '</p>').join('') +
      '</div>';
  $('population-details-body').innerHTML = html + '</div>';
}
