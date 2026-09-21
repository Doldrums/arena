export function createArenaNavigation(context) {
  const { doc, win, $, state } = context;
  const render = (...args) => context.render(...args);
  let pendingCatalogHash = null;

  let lastCatalogRoute = null;

  function locationState() {
    const params = new URL(win.location.href).searchParams;
    return {
      view: params.get('view') === 'participants' ? 'participants' : 'tasks',
      atlasMode: params.get('atlas') === 'families' ? 'families' : 'methods',
      search_family: params.get('search_family') || '',
      query: params.get('q') || '',
      family: params.get('family') || '',
      domain: params.get('domain') || '',
      type: params.get('type') || '',
      reference: params.get('reference') || '',
      protocol: params.get('protocol') || '',
      task: params.get('task'),
      participant: params.get('participant'),
      page: Math.max(1, Number.parseInt(params.get('page'), 10) || 1),
    };
  }

  function route(changes = {}) {
    const url = new URL(win.location.href);
    url.pathname = '/';
    url.hash = '';
    for (const [key, value] of Object.entries(changes)) {
      if (value == null || value === '') url.searchParams.delete(key);
      else url.searchParams.set(key, value);
    }
    return url.pathname + url.search;
  }

  function catalogHashTarget(url = new URL(win.location.href)) {
    const browser = $('arena-catalog-browser');
    if (!browser || !url.hash) return null;
    let target;
    try {
      target = $(decodeURIComponent(url.hash.slice(1)));
    } catch {
      return null;
    }
    return target && (target === browser || browser.contains(target)) ? target : null;
  }

  function revealCatalog({ scroll = false, focus = false, target = $('arena-list-panel') } = {}) {
    const current = locationState();
    if (current.view === 'tasks' ? current.task : current.participant) return;
    const browser = $('arena-catalog-browser');
    if (browser) browser.open = true;
    if (scroll) {
      const reducedMotion = win.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      target?.scrollIntoView?.({ behavior: reducedMotion ? 'instant' : 'smooth', block: 'start' });
    }
    if (focus) {
      const heading = target === $('arena-list-panel') ? $('arena-results-title') : target;
      heading?.setAttribute('tabindex', '-1');
      heading?.focus({ preventScroll: true });
    }
  }

  function catalogDisclosure(current) {
    const browser = $('arena-catalog-browser');
    if (!browser) return;
    const isTasks = current.view === 'tasks',
      selected = isTasks ? current.task : current.participant;
    browser.hidden = Boolean(selected);
    if ($('arena-catalog-toggle')) $('arena-catalog-toggle').hidden = !isTasks;
    if ($('arena-analysis')) $('arena-analysis').hidden = !isTasks || Boolean(selected);
    const url = new URL(win.location.href),
      hashTarget = catalogHashTarget(url);
    const filters = [
      current.query,
      current.family,
      current.protocol,
      current.domain,
      current.type,
      current.reference,
      current.search_family,
    ];
    const key = JSON.stringify([
      current.view,
      current.task,
      current.participant,
      ...filters,
      url.searchParams.get('page'),
      url.hash,
    ]);
    if (lastCatalogRoute?.key !== key)
      pendingCatalogHash = !selected && isTasks ? hashTarget?.id || null : null;
    if (!isTasks) browser.open = true;
    else if (lastCatalogRoute?.key !== key && !selected) {
      if (
        filters.some(Boolean) ||
        url.searchParams.has('page') ||
        hashTarget ||
        lastCatalogRoute?.task
      )
        browser.open = true;
      else if (lastCatalogRoute?.view === 'participants') browser.open = false;
    }
    lastCatalogRoute = { key, view: current.view, task: current.task };
  }

  function finishCatalogHashNavigation() {
    if (!pendingCatalogHash || state.loading) return;
    const target = $(pendingCatalogHash),
      browser = $('arena-catalog-browser');
    pendingCatalogHash = null;
    if (target && browser?.open && !browser.hidden) revealCatalog({ scroll: true, target });
  }

  function navigate(
    href,
    { replace = false, focus = false, catalog = false, scrollCatalog = false, target } = {},
  ) {
    win.history[replace ? 'replaceState' : 'pushState'](null, '', href);
    render();
    if (catalog) revealCatalog({ scroll: scrollCatalog, focus, target });
    else if (focus) $('main').focus({ preventScroll: true });
  }

  function exploreDomain(id) {
    const previous = state.fieldDomain === undefined ? locationState().domain : state.fieldDomain;
    state.fieldDomain = id;
    render();
    if (id) {
      const detail = $('arena-domain-preview');
      const reducedMotion = win.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      detail?.scrollIntoView?.({ behavior: reducedMotion ? 'instant' : 'smooth', block: 'center' });
      $('arena-domain-preview-title')?.focus({ preventScroll: true });
    } else {
      [...doc.querySelectorAll('[data-domain-card]')]
        .find((card) => card.dataset.domainCard === previous)
        ?.focus({ preventScroll: true });
    }
  }

  function filterCatalog(kind, value) {
    if (kind === 'domain') state.fieldDomain = value;
    navigate(route({ [kind]: value, page: null, task: null }), {
      catalog: true,
      scrollCatalog: true,
    });
  }
  return {
    locationState,
    route,
    catalogHashTarget,
    revealCatalog,
    catalogDisclosure,
    finishCatalogHashNavigation,
    navigate,
    exploreDomain,
    filterCatalog,
  };
}
