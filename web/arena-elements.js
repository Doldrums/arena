import { safeExternalURL, textValue } from './arena-model.js';
export function createArenaElements(context) {
  const { doc, $, state } = context;
  const locationState = (...args) => context.locationState(...args);
  function element(tag, className, text) {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function link(text, href, className = 'inline-link', internal = false) {
    const node = element('a', className, text);
    node.href = href;
    if (internal) node.dataset.arenaRoute = 'true';
    else {
      node.target = '_blank';
      node.rel = 'noopener noreferrer';
    }
    return node;
  }

  function button(text, action, className = 'button') {
    const node = element('button', className, text);
    node.type = 'button';
    node.addEventListener('click', action);
    return node;
  }

  function badge(text, kind = 'neutral') {
    return element('span', `badge ${kind}`, text);
  }

  function fact(list, label, value) {
    const item = element('div');
    item.append(element('dt', '', label), element('dd', '', textValue(value)));
    list.append(item);
  }

  function section(container, title) {
    const item = element('section', 'arena-detail-section');
    item.append(element('h3', '', title));
    container.append(item);
    return item;
  }

  function empty(container, title, message) {
    const node = element('div', 'arena-empty');
    node.append(element('strong', '', title), element('p', '', message));
    container.append(node);
  }

  function recordDetails(container, record) {
    const details = element('details', 'arena-detail-section');
    details.append(
      element('summary', 'inline-link', 'View complete registry record'),
      element('pre', '', JSON.stringify(record, null, 2)),
    );
    container.append(details);
  }

  function externalLinks(container, candidates) {
    const holder = element('div', 'arena-detail-links');
    const seen = new Set();
    for (const [title, candidate] of candidates) {
      const url = safeExternalURL(candidate);
      if (url && !seen.has(url)) {
        holder.append(link(`${title} ↗`, url));
        seen.add(url);
      }
    }
    if (holder.childNodes.length) container.append(holder);
  }

  function summary() {
    const container = $('arena-summary');
    container.replaceChildren();
    const tasks = state.catalog?.tasks;
    const counts = tasks
      ? [tasks.length, tasks.filter((task) => task.executable).length]
      : ['—', '—'];
    const isTaskView = locationState().view === 'tasks';
    const metrics = isTaskView
      ? [
          [
            'Task packages',
            counts[0],
            `${typeof counts[1] === 'number' ? counts[1].toLocaleString('en-US') : '—'} with evaluation definitions`,
          ],
          [
            'Research domains',
            state.insights
              ? state.insights.domains.filter((item) => item.id !== 'unknown').length
              : '—',
            state.insights?.summary?.unknown_domain_count != null
              ? `${state.insights.summary.unknown_domain_count} packages unclassified`
              : 'Primary scientific context',
          ],
          [
            'Task families',
            tasks ? new Set(tasks.map((task) => task.family).filter(Boolean)).size : '—',
            'Packing, equations, algorithms & more',
          ],
          [
            'Research papers',
            state.insights?.summary?.corpus_paper_count ?? '—',
            state.insights?.summary?.source_group_count != null
              ? 'Plus the SCiEL task collection'
              : 'Excludes source supplements',
          ],
        ]
      : [
          [
            'Research works',
            state.participants?.summary?.research_work_count ??
              state.participants?.participants.filter((item) => item.papers?.length).length ??
              '—',
            'Papers, methods and source material',
          ],
          [
            'Method families',
            state.participants
              ? new Set(
                  state.participants.participants
                    .map((item) => item.search_family?.id)
                    .filter(Boolean),
                ).size
              : '—',
            'Explore related research approaches',
          ],
          [
            'Source-pinned systems',
            state.participants?.summary?.pinned_registration_count ??
              state.participants?.participants.filter((item) => item.repository?.commit).length ??
              '—',
            'Versioned framework registrations',
          ],
        ];
    container.classList.toggle('arena-task-metrics', isTaskView);
    for (const [index, [label, value, note]] of metrics.entries()) {
      const metric = element('article', 'metric');
      const caption = element('div', 'metric-label');
      const icon = element('span', 'arena-metric-icon');
      icon.setAttribute('aria-hidden', 'true');
      const svg = doc.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 24 24');
      const path = doc.createElementNS(svg.namespaceURI, 'path');
      path.setAttribute(
        'd',
        [
          'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z',
          'M12 3v18 M3 12h18 M5.6 5.6l12.8 12.8 M5.6 18.4 18.4 5.6',
          'M6 5h12 M6 12h12 M6 19h12 M12 5v14 M4 3h4v4H4z M16 10h4v4h-4z M4 17h4v4H4z',
          'M4 4h7l1 2 1-2h7v15h-7l-1 2-1-2H4z M12 6v13',
        ][index % 4],
      );
      svg.append(path);
      icon.append(svg);
      if (isTaskView) caption.append(icon, element('span', '', label));
      else caption.append(element('span', '', label), icon);
      const body = isTaskView ? element('div', 'arena-metric-body') : metric;
      metric.append(caption);
      body.append(
        element(
          'div',
          'metric-value',
          typeof value === 'number' ? value.toLocaleString('en-US') : value,
        ),
        element('div', 'metric-foot', note),
      );
      if (index === 0) {
        const glow = element('span', 'arena-curious-glow');
        glow.setAttribute('aria-hidden', 'true');
        glow.append(element('span', 'arena-curious-eye'), element('span', 'arena-curious-eye'));
        body.append(glow);
      }
      if (isTaskView) metric.append(body);
      container.append(metric);
    }
    $('nav-task-count').textContent = tasks?.length.toLocaleString('en-US') ?? '';
    $('nav-participant-count').textContent = state.participants?.participants.length ?? '';
    const registryError = state.errors.catalog || state.errors.participants;
    $('arena-connection').textContent = state.loading
      ? 'Loading registry…'
      : registryError
        ? 'Registry partly unavailable'
        : 'Registry loaded';
    $('arena-connection-dot').className =
      `connection-dot ${state.loading ? '' : registryError ? 'error' : 'connected'}`;
  }
  return {
    element,
    link,
    button,
    badge,
    fact,
    section,
    empty,
    recordDetails,
    externalLinks,
    summary,
  };
}
