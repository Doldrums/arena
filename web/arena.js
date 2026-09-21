import { createArenaElements } from './arena-elements.js';
import { createArenaNavigation } from './arena-navigation.js';
import { createArenaTaskDetail } from './arena-task-detail.js';
import { createArenaParticipantDetail } from './arena-participant-detail.js';
import { createArenaLists } from './arena-lists.js';
import { createArenaRender } from './arena-render.js';
import { createArenaLoader } from './arena-loader.js';
export { filterTasks, safeExternalURL } from './arena-model.js';
export function createArenaApp({
  document: doc = document,
  window: win = window,
  fetchJSON = async (path) => {
    const response = await fetch(path, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  },
} = {}) {
  const $ = (id) => doc.getElementById(id);
  const state = {
    catalog: null,
    participants: null,
    insights: null,
    references: null,
    searchFamilies: null,
    errors: {},
    loading: true,
  };
  const context = { doc, win, $, state, fetchJSON };
  Object.assign(context, createArenaElements(context));
  Object.assign(context, createArenaNavigation(context));
  Object.assign(context, createArenaTaskDetail(context));
  Object.assign(context, createArenaParticipantDetail(context));
  Object.assign(context, createArenaLists(context));
  Object.assign(context, createArenaRender(context));
  Object.assign(context, createArenaLoader(context));
  const { locationState, navigate, route, catalogHashTarget, render, revealCatalog, load } =
    context;
  function updateFilters() {
    const current = locationState();
    navigate(
      route({
        q: $('arena-search').value,
        family: $('arena-family').value,
        protocol: current.view === 'tasks' ? $('arena-protocol').value : null,
        page: null,
        task: null,
        participant: null,
      }),
      { replace: true, catalog: true },
    );
  }

  $('arena-search').addEventListener('input', updateFilters);

  $('arena-family').addEventListener('change', updateFilters);

  $('arena-protocol').addEventListener('change', updateFilters);

  $('arena-filters').addEventListener('submit', (event) => {
    event.preventDefault();
    updateFilters();
  });

  $('arena-clear').addEventListener('click', () =>
    navigate(
      route({
        q: null,
        family: null,
        protocol: null,
        domain: null,
        type: null,
        reference: null,
        search_family: null,
        page: null,
      }),
      { replace: true, catalog: true },
    ),
  );

  doc.addEventListener('click', (event) => {
    const anchor = event.target.closest?.('a[href]');
    if (
      event.defaultPrevented ||
      !anchor ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    const url = new URL(anchor.href),
      currentURL = new URL(win.location.href);
    const hashTarget =
      url.origin === currentURL.origin &&
      url.pathname === currentURL.pathname &&
      url.search === currentURL.search
        ? catalogHashTarget(url)
        : null;
    if (hashTarget) {
      event.preventDefault();
      navigate(anchor.href, {
        catalog: true,
        scrollCatalog: true,
        focus: true,
        target: hashTarget,
      });
    } else if (anchor.matches('a[data-arena-route], a[data-arena-view]')) {
      const current = locationState();
      const backToCatalog =
        current.view === 'tasks' &&
        current.task &&
        url.searchParams.get('view') !== 'participants' &&
        !url.searchParams.has('task');
      event.preventDefault();
      navigate(anchor.href, {
        focus: true,
        catalog: Boolean(backToCatalog),
        scrollCatalog: Boolean(backToCatalog),
      });
    }
  });

  win.addEventListener('popstate', render);

  win.addEventListener('hashchange', () => {
    render();
    const target = catalogHashTarget();
    if (target) revealCatalog({ scroll: true, target });
  });

  const ready = load();

  return { ready, reload: load, render };
}
if (typeof document !== 'undefined' && document.body.dataset.arenaApp === 'true') createArenaApp();
