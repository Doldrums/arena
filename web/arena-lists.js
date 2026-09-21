import {
  PAGE_SIZE,
  PROTOCOL_LABELS,
  adapterLabel,
  filterTasks,
  participantKind,
  words,
} from './arena-model.js';
export function createArenaLists(context) {
  const { $, state } = context;
  const empty = (...args) => context.empty(...args);
  const element = (...args) => context.element(...args);
  const link = (...args) => context.link(...args);
  const route = (...args) => context.route(...args);
  const badge = (...args) => context.badge(...args);
  const button = (...args) => context.button(...args);
  const navigate = (...args) => context.navigate(...args);
  const participantAttribution = (...args) => context.participantAttribution(...args);
  const participantPapers = (...args) => context.participantPapers(...args);
  const externalLinks = (...args) => context.externalLinks(...args);
  const participantSourceLinks = (...args) => context.participantSourceLinks(...args);
  function taskResults(current) {
    const tasks = filterTasks(state.catalog.tasks, current, state);
    const results = $('arena-results');
    results.replaceChildren();
    $('arena-result-count').textContent =
      `${tasks.length.toLocaleString('en-US')} of ${state.catalog.tasks.length.toLocaleString('en-US')} tasks`;
    if (!tasks.length) {
      empty(
        results,
        state.catalog.tasks.length ? 'No tasks match these filters' : 'No tasks in the catalog',
        state.catalog.tasks.length
          ? 'Try another search or clear the filters to show all tasks.'
          : 'Task definitions can be proposed through a pull request.',
      );
      return;
    }
    const pages = Math.ceil(tasks.length / PAGE_SIZE),
      page = Math.min(current.page, pages);
    const table = element('table', 'arena-table');
    const head = element('thead');
    const header = element('tr');
    for (const label of ['Task', 'Family', 'Protocol', 'Definition']) {
      const th = element('th', '', label);
      th.scope = 'col';
      header.append(th);
    }
    head.append(header);
    table.append(head);
    const body = element('tbody');
    for (const task of tasks.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)) {
      const row = element('tr');
      const title = element('td');
      title.append(
        link(task.name || task.id, route({ task: task.id }), 'arena-task-link', true),
        element('span', 'arena-task-id', task.id),
      );
      if (task.description) title.append(element('p', 'arena-task-description', task.description));
      const protocol = element('td');
      protocol.append(badge(PROTOCOL_LABELS[task.protocol] || words(task.protocol)));
      row.append(
        title,
        element('td', 'muted', task.family || 'Unspecified'),
        protocol,
        element(
          'td',
          'arena-definition',
          task.executable ? 'Executable source' : 'Evaluator to be added',
        ),
      );
      body.append(row);
    }
    table.append(body);
    const wrapper = element('div', 'table-wrap');
    wrapper.append(table);
    results.append(wrapper);
    const pagination = $('arena-pagination');
    pagination.replaceChildren();
    pagination.hidden = pages <= 1;
    pagination.append(element('span', '', `Page ${page} of ${pages}`));
    const controls = element('div');
    const previous = button('← Previous', () =>
      navigate(route({ page: page - 1 }), { focus: true, catalog: true, scrollCatalog: true }),
    );
    previous.disabled = page === 1;
    const next = button('Next →', () =>
      navigate(route({ page: page + 1 }), { focus: true, catalog: true, scrollCatalog: true }),
    );
    next.disabled = page === pages;
    controls.append(previous, next);
    pagination.append(controls);
  }

  function participantResults(current) {
    const terms = current.query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    const all = state.participants.participants;
    const participants = all.filter(
      (item) =>
        (!current.family || item.search_family?.id === current.family) &&
        terms.every((term) =>
          [
            item.id,
            item.name,
            item.description,
            item.search_family?.label,
            item.attribution?.display,
            ...(item.attribution?.organizations || []),
            ...(item.attribution?.authors || []),
            ...(item.papers || []).flatMap((paper) => [paper.title, paper.year, paper.venue]),
          ]
            .join(' ')
            .toLocaleLowerCase()
            .includes(term),
        ),
    );
    $('arena-result-count').textContent = `${participants.length} of ${all.length} participants`;
    const results = $('arena-results');
    results.replaceChildren();
    if (!participants.length) {
      empty(
        results,
        all.length ? 'No participants match your search' : 'No participants registered',
        all.length
          ? 'Try another name or clear the search.'
          : 'Propose a participant through a pull request.',
      );
      return;
    }
    const grid = element('div', 'arena-participants');
    const pages = Math.ceil(participants.length / PAGE_SIZE),
      page = Math.min(current.page, pages);
    for (const item of participants.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)) {
      const card = element('article', 'arena-participant');
      card.dataset.participant = item.id;
      const title = element('h3');
      title.append(
        link(item.name || item.id, route({ participant: item.id }), 'arena-task-link', true),
      );
      const status = element('div', 'arena-participant-status');
      status.append(badge(participantKind(item)), badge(adapterLabel(item)));
      const art = element('div', 'arena-participant-art');
      art.dataset.participant = item.id;
      art.setAttribute('aria-hidden', 'true');
      art.append(element('span', 'arena-participant-glyph'));
      const heading = element('div', 'arena-participant-heading'),
        identity = element('div');
      identity.append(title);
      participantAttribution(identity, item);
      identity.append(
        element('span', 'arena-participant-family', item.search_family?.label || 'Research system'),
      );
      heading.append(art, identity);
      card.append(
        heading,
        element(
          'p',
          'arena-participant-description',
          item.description || 'Research system registration.',
        ),
      );
      participantPapers(card, item);
      const footer = element('div', 'arena-participant-footer');
      externalLinks(footer, [
        ...(item.papers || []).map((paper) => [
          paper.kind === 'technical_report' ? 'Report' : 'Paper',
          paper.url,
        ]),
        ...participantSourceLinks(item),
      ]);
      footer.append(link('Details →', route({ participant: item.id }), 'inline-link', true));
      card.append(status, footer);
      grid.append(card);
    }
    results.append(grid);
    const pagination = $('arena-pagination');
    pagination.replaceChildren();
    pagination.hidden = pages <= 1;
    if (pages > 1) {
      pagination.append(element('span', '', `Page ${page} of ${pages}`));
      const controls = element('div');
      const previous = button('← Previous', () =>
        navigate(route({ page: page - 1 }), { focus: true, catalog: true, scrollCatalog: true }),
      );
      previous.disabled = page === 1;
      const next = button('Next →', () =>
        navigate(route({ page: page + 1 }), { focus: true, catalog: true, scrollCatalog: true }),
      );
      next.disabled = page === pages;
      controls.append(previous, next);
      pagination.append(controls);
    }
  }
  return { taskResults, participantResults };
}
