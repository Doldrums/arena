import { canonicalJSON, catalogDigest } from './arena-model.js';
export function createArenaLoader(context) {
  const { state, fetchJSON } = context;
  const render = (...args) => context.render(...args);
  const populateFamilies = (...args) => context.populateFamilies(...args);
  let loadRevision = 0;

  async function load() {
    const revision = ++loadRevision;
    state.loading = true;
    state.errors = {};
    // Metadata is promoted together after verifying the catalog revision.
    const metadata = {};
    state.insights = null;
    state.references = null;
    state.searchFamilies = null;
    render();
    await Promise.all(
      ['catalog', 'participants', 'insights', 'references', 'searchFamilies'].map(async (name) => {
        try {
          const data = await fetchJSON(
            `/api/${name === 'searchFamilies' ? 'search-families' : name}`,
          );
          if (name === 'searchFamilies') {
            if (
              !data ||
              !Array.isArray(data.groups) ||
              !data.task_annotations ||
              data.groups.some(
                (item) =>
                  typeof item.id !== 'string' ||
                  typeof item.label !== 'string' ||
                  !Array.isArray(item.task_ids),
              )
            )
              throw new Error('The server returned an invalid search-method map.');
          } else if (name === 'insights') {
            if (
              !data ||
              !Array.isArray(data.domains) ||
              !Array.isArray(data.task_types) ||
              !data.task_annotations ||
              typeof data.denominator?.task_count !== 'number' ||
              [...data.domains, ...data.task_types].some(
                (item) =>
                  typeof item.id !== 'string' ||
                  typeof item.label !== 'string' ||
                  typeof item.total !== 'number',
              )
            )
              throw new Error('The server returned an invalid scientific overview.');
          } else if (name === 'references') {
            if (
              !data ||
              !Array.isArray(data.tasks) ||
              data.tasks.some(
                (item) => !item || typeof item.task_id !== 'string' || !Array.isArray(item.anchors),
              )
            )
              throw new Error('The server returned invalid reference evidence.');
          } else {
            const field = name === 'catalog' ? 'tasks' : 'participants';
            if (
              !data ||
              !Array.isArray(data[field]) ||
              data[field].some((item) => !item || typeof item.id !== 'string')
            )
              throw new Error('The server returned an invalid registry.');
          }
          if (revision !== loadRevision) return;
          if (name === 'catalog' || name === 'participants') state[name] = data;
          else metadata[name] = data;
          if (name === 'catalog') populateFamilies();
        } catch (error) {
          if (revision !== loadRevision) return;
          state[name] = null;
          state.errors[name] =
            typeof error?.message === 'string' ? error.message : 'Request failed.';
        }
        if (revision === loadRevision) render();
      }),
    );
    if (revision !== loadRevision) return;
    let digest;
    if (state.catalog && Object.values(metadata).some((data) => data.catalog_digest)) {
      try {
        digest = await catalogDigest(state.catalog);
      } catch {
        /* Unverifiable metadata stays unavailable. */
      }
    }
    if (revision !== loadRevision) return;
    for (const [name, data] of Object.entries(metadata)) {
      const digestMismatch = data.catalog_digest && data.catalog_digest !== digest;
      const bindingMismatch =
        data.catalog_binding &&
        !state.catalog?.sources?.some(
          (source) => canonicalJSON(source) === canonicalJSON(data.catalog_binding),
        );
      if (!state.catalog || digestMismatch || bindingMismatch) {
        state[name] = null;
        state.errors[name] =
          'Metadata does not match the loaded catalog revision. Reload to fetch a consistent snapshot.';
      } else state[name] = data;
    }
    state.loading = false;
    render();
  }
  return { load };
}
