import { referenceMatches } from './arena-insights.js';
export const REPOSITORY = 'https://github.com/Doldrums/arena';

export const PAGE_SIZE = 25;

export const PROTOCOL_LABELS = {
  original: 'Original',
  recreated_verified: 'Recreated · verified',
  recreated: 'Recreated',
  unsupported: 'Evaluator to be added',
};

export const textValue = (value) =>
  value == null || value === ''
    ? 'Not specified'
    : typeof value === 'object'
      ? JSON.stringify(value)
      : String(value);

export const words = (value) => textValue(value).replaceAll('_', ' ');

export const participantKind = (item) =>
  item.record_kind === 'research_work'
    ? 'Research work'
    : item.repository?.commit
      ? 'Source pinned'
      : words(item.registration_status);

export const linkedNativeAdapters = (item) =>
  (item.native_adapters || []).filter(
    (adapter) =>
      adapter.evaluation === 'native' &&
      adapter.runtime_readiness === 'not_verified' &&
      adapter.profiles?.length &&
      adapter.repository?.commit,
  );

export const adapterLabel = (item) =>
  linkedNativeAdapters(item).length
    ? 'Local adapter'
    : {
        not_implemented: 'Integration open',
        native_cli: 'Local adapter',
        planned: 'Integration planned',
        integrated: 'Adapter integrated',
      }[item.adapter_status] || words(item.adapter_status);

export function canonicalJSON(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJSON).join(',')}]`;
  if (value && typeof value === 'object')
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJSON(value[key])}`)
      .join(',')}}`;
  return JSON.stringify(value);
}

export async function catalogDigest(catalog) {
  const bytes = new TextEncoder().encode(canonicalJSON(catalog));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export function safeExternalURL(value) {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function filterTasks(
  tasks,
  {
    query = '',
    family = '',
    protocol = '',
    domain = '',
    type = '',
    reference = '',
    search_family = '',
  } = {},
  { insights, references, searchFamilies } = {},
) {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const referenceMap = new Map((references?.tasks || []).map((record) => [record.task_id, record]));
  return tasks.filter(
    (task) =>
      (!family || (family === '__unspecified__' ? !task.family : task.family === family)) &&
      (!search_family ||
        !searchFamilies ||
        (searchFamilies.task_annotations[task.id]?.search_family_id || 'unclassified') ===
          search_family) &&
      (!protocol || task.protocol === protocol) &&
      (!domain || !insights || insights.task_annotations[task.id]?.domain_id === domain) &&
      (!type || !insights || insights.task_annotations[task.id]?.task_type_id === type) &&
      (!reference || !references || referenceMatches(referenceMap.get(task.id), reference)) &&
      terms.every((term) =>
        [task.id, task.name, task.description, task.family, task.metric, ...(task.paper_ids || [])]
          .map(textValue)
          .join(' ')
          .toLocaleLowerCase()
          .includes(term),
      ),
  );
}
