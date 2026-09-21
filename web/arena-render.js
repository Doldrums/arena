import { renderArenaAtlas } from './arena-atlas.js';
import { renderArenaInsights } from './arena-insights.js';
import { filterTasks, words } from './arena-model.js';
export function createArenaRender(context) {
  const { doc, $, state } = context;
  const locationState = (...args) => context.locationState(...args);
  const catalogDisclosure = (...args) => context.catalogDisclosure(...args);
  const summary = (...args) => context.summary(...args);
  const filterCatalog = (...args) => context.filterCatalog(...args);
  const navigate = (...args) => context.navigate(...args);
  const route = (...args) => context.route(...args);
  const exploreDomain = (...args) => context.exploreDomain(...args);
  const load = (...args) => context.load(...args);
  const element = (...args) => context.element(...args);
  const button = (...args) => context.button(...args);
  const empty = (...args) => context.empty(...args);
  const finishCatalogHashNavigation = (...args) => context.finishCatalogHashNavigation(...args);
  const taskDetail = (...args) => context.taskDetail(...args);
  const participantDetail = (...args) => context.participantDetail(...args);
  const taskResults = (...args) => context.taskResults(...args);
  const participantResults = (...args) => context.participantResults(...args);
  function render() {
    const current = locationState(),
      isTasks = current.view === 'tasks';
    const dataset = isTasks ? state.catalog : state.participants;
    const error = state.errors[isTasks ? 'catalog' : 'participants'];
    const selected = isTasks ? current.task : current.participant;
    const viewName = isTasks ? 'Tasks' : 'Participants';
    doc.title = `Empira · ${viewName}`;
    $('arena-title').textContent = viewName;
    $('arena-breadcrumb').textContent = viewName;
    $('arena-subtitle').textContent = isTasks
      ? 'Versioned scientific tasks and evaluation definitions.'
      : 'Research systems, their papers and the methods they build on.';
    $('arena-contribute').textContent = isTasks ? 'Submit a task +' : 'Submit a system +';
    $('arena-contribute').dataset.arenaContribution = isTasks ? 'task' : 'system';
    const showIntroduction = isTasks && !selected;
    for (const id of ['arena-intro', 'arena-positioning', 'arena-growth', 'arena-faq'])
      if ($(id)) $(id).hidden = !showIntroduction;
    $('arena-page-heading').hidden = showIntroduction;
    catalogDisclosure(current);
    for (const node of doc.querySelectorAll('[data-arena-view]')) {
      if (node.dataset.arenaView === current.view) node.setAttribute('aria-current', 'page');
      else node.removeAttribute('aria-current');
    }
    summary();
    $('arena-atlas').hidden = !isTasks || Boolean(selected);
    if (isTasks && !selected)
      renderArenaAtlas($('arena-atlas'), {
        catalog: state.catalog,
        insights: state.insights,
        searchFamilies: state.searchFamilies,
        current,
        errors: state.errors,
        loading: state.loading,
        onFilter: filterCatalog,
        onTask: (id) => navigate(route({ task: id }), { focus: true }),
        onModeChange: (mode) => navigate(route({ atlas: mode === 'methods' ? null : mode })),
      });
    $('arena-insights').hidden = !isTasks || Boolean(selected);
    $('arena-statistics').hidden = !isTasks || Boolean(selected);
    if (isTasks && !selected)
      renderArenaInsights($('arena-insights'), {
        insights: state.insights,
        references: state.references,
        catalog: state.catalog,
        current,
        analysisRoot: $('arena-analysis'),
        statisticsRoot: $('arena-statistics'),
        exploredDomain: state.fieldDomain,
        onExploreDomain: exploreDomain,
        matchingTasks: state.catalog ? filterTasks(state.catalog.tasks, current, state) : [],
        errors: state.errors,
        loading: state.loading,
        onFilter: filterCatalog,
        onRetry: load,
      });
    const chips = $('arena-active-filters');
    chips.replaceChildren();
    chips.hidden =
      !isTasks ||
      !(
        current.domain ||
        current.type ||
        current.reference ||
        current.search_family ||
        current.family
      );
    if (!chips.hidden) {
      chips.append(element('span', '', 'Selected filters'));
      for (const [key, value, labels, prefix] of [
        ['domain', current.domain, state.insights?.domains, 'Domain'],
        ['type', current.type, state.insights?.task_types, 'Type'],
        ['reference', current.reference, null, 'Reference'],
        ['search_family', current.search_family, state.searchFamilies?.groups, 'Search method'],
        ['family', current.family, null, 'Task family'],
      ]) {
        if (!value) continue;
        const label =
          labels?.find((item) => item.id === value)?.label ||
          {
            __unspecified__: 'Unspecified',
            published: 'Published reference',
            baseline: 'Seed baseline',
            missing: 'No numeric reference',
            numeric: 'Numeric reference',
          }[value] ||
          words(value);
        const chip = element('div', 'arena-filter-chip');
        chip.append(element('span', '', `${prefix}: ${label}`));
        const remove = button(
          '×',
          () => navigate(route({ [key]: null, page: null }), { catalog: true }),
          '',
        );
        remove.setAttribute('aria-label', `Remove ${prefix.toLowerCase()} filter: ${label}`);
        chip.append(remove);
        chips.append(chip);
      }
      if (
        ((current.domain || current.type) && !state.insights) ||
        (current.reference && !state.references) ||
        (current.search_family && !state.searchFamilies)
      )
        chips.append(
          element(
            'span',
            '',
            'Some filters await overview data; available catalog rows remain visible.',
          ),
        );
    }
    $('arena-scope').hidden = !dataset;
    $('arena-scope').textContent = isTasks
      ? 'Evaluation definitions and runtime integration are tracked separately. Original source declarations remain available in each task record.'
      : 'Research works identify methods and their original publications. Source-pinned registrations and framework integrations are tracked separately.';
    $('arena-error').hidden = !error;
    $('arena-error').replaceChildren();
    if (error) {
      $('arena-error').append(
        element(
          'p',
          'arena-error-message',
          `Could not load ${isTasks ? 'the task catalog' : 'participants'}. ${error}`,
        ),
        button('Try again', load),
      );
    }
    $('arena-detail').hidden = !selected || !dataset;
    $('arena-list-panel').hidden = Boolean(selected && dataset);
    $('arena-pagination').hidden = true;
    $('arena-search').placeholder = isTasks ? 'Search tasks' : 'Search systems, papers, labs';
    $('arena-search').setAttribute('aria-label', `Search ${current.view}`);
    if ($('arena-search').value !== current.query) $('arena-search').value = current.query;
    populateFamilies();
    $('arena-family').value = current.family;
    $('arena-protocol').value = current.protocol;
    $('family-filter-label').hidden = false;
    $('protocol-filter-label').hidden = !isTasks;
    $('arena-clear').hidden = !(
      current.query ||
      current.family ||
      current.protocol ||
      current.domain ||
      current.type ||
      current.reference ||
      current.search_family
    );
    $('arena-results-title').textContent = isTasks ? 'Task catalog' : 'Systems & research';
    $('arena-results').setAttribute('aria-busy', String(!dataset && !error));
    if (!dataset) {
      $('arena-result-count').textContent = error ? 'Unavailable' : 'Loading…';
      $('arena-results').replaceChildren();
      if (error)
        empty(
          $('arena-results'),
          'Registry unavailable',
          'Use Try again above to reload the registry.',
        );
      else
        $('arena-results').append(
          element('div', 'loading', `Loading ${isTasks ? 'task definitions' : 'participants'}…`),
        );
      finishCatalogHashNavigation();
      return;
    }
    if (selected) {
      if (isTasks) taskDetail(dataset.tasks.find((item) => item.id === selected));
      else participantDetail(dataset.participants.find((item) => item.id === selected));
    } else if (isTasks) taskResults(current);
    else participantResults(current);
    finishCatalogHashNavigation();
  }

  function populateFamilies() {
    const select = $('arena-family');
    select.replaceChildren();
    const all = element('option', '', 'All families');
    all.value = '';
    select.append(all);
    if (locationState().view === 'participants') {
      const families = new Map(
        (state.participants?.participants || [])
          .filter((item) => item.search_family)
          .map((item) => [item.search_family.id, item.search_family.label]),
      );
      for (const [id, label] of families) {
        const option = element('option', '', label);
        option.value = id;
        select.append(option);
      }
      return;
    }
    for (const family of [
      ...new Set((state.catalog?.tasks || []).map((task) => task.family).filter(Boolean)),
    ].sort()) {
      const option = element('option', '', family);
      option.value = family;
      select.append(option);
    }
    if (state.catalog?.tasks.some((task) => !task.family)) {
      const option = element('option', '', 'Unspecified');
      option.value = '__unspecified__';
      select.append(option);
    }
  }
  return { render, populateFamilies };
}
