import { PROTOCOL_LABELS, textValue, words } from './arena-model.js';
import { renderTaskReferences } from './arena-insights.js';
export function createArenaTaskDetail(context) {
  const { $, state } = context;
  const link = (...args) => context.link(...args);
  const route = (...args) => context.route(...args);
  const empty = (...args) => context.empty(...args);
  const element = (...args) => context.element(...args);
  const badge = (...args) => context.badge(...args);
  const fact = (...args) => context.fact(...args);
  const section = (...args) => context.section(...args);
  const externalLinks = (...args) => context.externalLinks(...args);
  const recordDetails = (...args) => context.recordDetails(...args);
  function taskDetail(task) {
    const holder = $('arena-detail');
    holder.replaceChildren();
    holder.append(link('← Back to task catalog', route({ task: null }), 'inline-link', true));
    if (!task) {
      empty(
        holder,
        'Task not found',
        'This task is not in the current catalog. Return to the catalog to choose an available definition.',
      );
      return;
    }
    const source = state.catalog.sources?.find(
      (item) => item.id === task.source_id || item.source_id === task.source_id,
    );
    const heading = element('div', 'arena-detail-top');
    const title = element('div');
    title.append(
      element('h2', 'arena-detail-title', task.name || task.id),
      element('span', 'arena-task-id', task.id),
    );
    heading.append(title, badge(PROTOCOL_LABELS[task.protocol] || words(task.protocol)));
    holder.append(
      heading,
      element('p', 'arena-detail-description', task.description || 'No description supplied.'),
    );
    const facts = element('dl', 'arena-detail-facts');
    fact(facts, 'Family', task.family);
    fact(facts, 'Metric', task.metric);
    fact(
      facts,
      'Direction',
      ['max', 'maximize'].includes(task.direction)
        ? 'Maximize'
        : ['min', 'minimize'].includes(task.direction)
          ? 'Minimize'
          : task.direction,
    );
    fact(facts, 'Executable definition', task.executable ? 'Present' : 'Evaluator to be added');
    fact(facts, 'Runtime availability', words(task.runtime_readiness));
    fact(facts, 'Source status', words(task.declared_status));
    holder.append(facts);
    if (source?.repository?.commit) fact(facts, 'Source revision', source.repository.commit);
    if (source?.kind === 'bundled') fact(facts, 'Task library SHA-256', source.manifest_sha256);
    const annotation = state.insights?.task_annotations?.[task.id];
    const domain = state.insights?.domains.find((item) => item.id === annotation?.domain_id);
    const taskType = state.insights?.task_types.find(
      (item) => item.id === annotation?.task_type_id,
    );
    const searchFamily = state.searchFamilies?.groups.find(
      (item) => item.id === state.searchFamilies.task_annotations[task.id]?.search_family_id,
    );
    if (searchFamily) fact(facts, 'Source method family', searchFamily.label);
    if (domain) fact(facts, 'Scientific domain', domain.label);
    if (taskType) fact(facts, 'Task type', taskType.label);
    if (domain || taskType) {
      const context = section(holder, 'Scientific context');
      context.dataset.taskScience = 'true';
      if (domain?.why_it_matters) context.append(element('p', '', domain.why_it_matters));
      if (taskType?.description) context.append(element('p', '', taskType.description));
      if (annotation?.rationale)
        context.append(
          element(
            'p',
            'arena-classification-note',
            `Arena classification: ${annotation.rationale}`,
          ),
        );
    }
    const contract = section(holder, 'Input / output');
    contract.dataset.taskContract = 'true';
    const hasContract = typeof task.contract === 'string' && task.contract.trim().length > 0;
    contract.append(
      element(
        'p',
        'arena-contract-text',
        hasContract ? task.contract : 'Input/output contract not recorded in the task snapshot.',
      ),
    );
    if (hasContract)
      contract.append(
        element(
          'p',
          'arena-contract-note',
          'Source declaration; runtime conformance has not been verified.',
        ),
      );
    if (task.contract_source) {
      externalLinks(contract, [[source?.kind === 'bundled' ? 'Task definition in Arena' : 'Pinned contract source', task.contract_source.url]]);
      const metadata = element('dl', 'arena-contract-source');
      if (task.contract_source.path) fact(metadata, 'Source file', task.contract_source.path);
      if (task.contract_source.sha256)
        fact(metadata, 'Source SHA-256', task.contract_source.sha256);
      if (metadata.childNodes.length) contract.append(metadata);
    }
    if (task.requirements?.length) {
      const requirements = section(holder, 'Requirements');
      const list = element('ul');
      for (const item of task.requirements) list.append(element('li', '', textValue(item)));
      requirements.append(list);
    }
    if (task.paper_ids?.length) {
      const papers = section(holder, 'Related papers');
      papers.append(element('p', '', task.paper_ids.map(textValue).join(' · ')));
    }
    renderTaskReferences(holder, {
      record: state.references?.tasks.find((item) => item.task_id === task.id),
      references: state.references,
      error: state.errors.references,
      loading: state.loading,
    });
    const provenance = section(holder, 'Source & provenance');
    provenance.append(
      element(
        'p',
        '',
        'The source contract describes the evaluation. An executable definition alone does not confirm that its dependencies or runtime are available in Arena.',
      ),
    );
    if (task.unsupported_reason) provenance.append(element('p', '', task.unsupported_reason));
    if (task.provenance?.validation_level)
      provenance.append(
        element('p', '', `Validation: ${words(task.provenance.validation_level)}.`),
      );
    if (task.provenance?.limitations?.length) {
      const list = element('ul');
      for (const limitation of task.provenance.limitations)
        list.append(element('li', '', textValue(limitation)));
      provenance.append(list);
    }
    const refs = [
      ['Repository', source?.repository?.url || source?.repository_url || source?.url],
      ['Task source', task.source_url || task.provenance?.source_url],
      ['Benchmark', task.benchmark?.url || task.provenance?.benchmark_url],
    ];
    const sources = task.provenance?.sources;
    if (Array.isArray(sources))
      for (const item of sources) refs.push(['Source', typeof item === 'string' ? item : item.url]);
    externalLinks(provenance, refs);
    recordDetails(holder, task);
  }
  return { taskDetail };
}
