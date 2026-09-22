// Public, published relationships only. Layout distance is not a scientific metric.
const list = value => Array.isArray(value) ? value : [];
const text = value => typeof value === 'string' && value.length > 0 && value.length <= 512 && !/[\u0000-\u001f]/.test(value) ? value : null;
const finite = value => typeof value === 'number' && Number.isFinite(value);
const count = value => Number.isSafeInteger(value) && value >= 0;
const detail = value => typeof value === 'string' && value.length <= 16000 && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value) ? value : null;
const safeURL = value => {
  try { const url = new URL(value); return ['https:','http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; }
  catch { return null; }
};
const id = (kind, value) => `${kind}:${encodeURIComponent(value)}`;
const ordered = values => [...new Set(values)].sort();
const COUNTERS = ['cells_created', 'cell_revisions', 'tools_registered', 'tools_executed', 'tool_executions', 'shared_observation_deliveries'];
// These native task identities describe mathematical objectives; they are not
// aliases of catalog packages, and their evaluator protocols remain separate.
const NATIVE_DOMAINS = new Map([
  ['oe/circle_packing', 'mathematics'],
  ['oe/function_minimization_oracle', 'mathematics'],
  ['oe/heilbronn_triangle', 'mathematics'],
]);
// Display categorization of exact published native identities, not evaluator joins.
const NATIVE_RESULT_DOMAINS = new Map([['gsm8k','machine-learning'],['penguins-in-a-table','machine-learning'],
  ['oscillation_1','physics'],['circle-packing','mathematics'],['online-bin-packing','operations-research']]);
const DOMAIN_LABELS = new Map([['mathematics','Mathematics & optimization'],['machine-learning','Machine learning & language'],
  ['physics','Physics'],['operations-research','Operations research']]);
// Public SCiEL release registration and results UI identify this same system.
const SYSTEM_ALIASES = new Map([['sciel-release', 'sciel']]);
const emptyCounts = () => ({catalogTasks:0, literatureTasks:0, integrationRuns:0, researchRuns:0, nativeOutcomes:0,
  measured:0, improved:0, completed:0, active:0, failed:0, cancelled:0, unknown:0});

function stateKey(state) {
  if (state === 'completed') return 'completed';
  if (['queued', 'preparing', 'running'].includes(state)) return 'active';
  if (state === 'failed') return 'failed';
  if (state === 'cancelled') return 'cancelled';
  return 'unknown'; // Paused/stopped native runs are not completed or failed.
}

function improvement(row, direction, measured) {
  if (!measured || !finite(row.seed_score)) return false;
  return direction === 'maximize' ? row.best_score > row.seed_score : row.best_score < row.seed_score;
}

function selfImprovement(rows) {
  const totals = Object.fromEntries(COUNTERS.map(key => [key, null]));
  const overflow = new Set();
  let recordedRuns = 0, completeRuns = 0, partialRuns = 0;
  for (const row of rows) {
    const value = row?.self_improvement;
    if (value?.schema !== 'sciel-self-improvement/1' || value.scope !== 'recorded_run' ||
        !['complete', 'partial', 'not_recorded'].includes(value.coverage) ||
        COUNTERS.some(key => value[key] !== null && !count(value[key])) ||
        value.coverage === 'complete' && COUNTERS.some(key => value[key] === null) ||
        value.coverage === 'not_recorded' && COUNTERS.some(key => value[key] !== null) ||
        count(value.tools_executed) && count(value.tools_registered) && value.tools_executed > value.tools_registered ||
        count(value.tools_executed) && count(value.tool_executions) && value.tools_executed > value.tool_executions ||
        value.cells_created === 0 && count(value.tools_registered) && value.tools_registered > 0) continue;
    if (value.coverage === 'not_recorded') continue;
    recordedRuns++;
    if (value.coverage === 'complete') completeRuns++; else partialRuns++;
    for (const key of COUNTERS) if (count(value[key]) && !overflow.has(key)) {
      const sum = (totals[key] ?? 0) + value[key];
      totals[key] = Number.isSafeInteger(sum) ? sum : null;
      if (!Number.isSafeInteger(sum)) overflow.add(key);
    }
  }
  return {coverage:completeRuns === rows.length && rows.length && !overflow.size ? 'complete' : recordedRuns ? 'partial' : 'not_recorded',
    recordedRuns, completeRuns, partialRuns, totalRuns:rows.length, counts:totals,
    scope:'recorded_run_events', interpretation:'Counts can repeat across runs; partial coverage gives observed lower bounds, not unique inventions or demonstrated utility.'};
}

function paired(row) {
  const objectives = list(row?.objectives), population = list(row?.population_objectives);
  return row?.direction === null && objectives.length >= 2 && objectives.length <= 8 && population.length > 0 &&
    objectives.every(o=>text(o?.metric) && ['maximize','minimize'].includes(o.direction)) &&
    new Set(objectives.map(o=>o.metric)).size === objectives.length &&
    population.every(candidate=>candidate && objectives.every(o=>finite(candidate[o.metric])));
}

function measurement(group, rows) {
  const measuredRows = rows.filter(row => (finite(row.best_score) || group.scope === 'native_result' && paired(row)) &&
    (group.scope !== 'native_research' || row.measurement_status === 'measured'));
  const values = measuredRows.map(row => row.best_score).filter(finite);
  const seeds = measuredRows.map(row => row.seed_score).filter(finite);
  return {...group, runs:rows.length, measured:measuredRows.length,
    improved:measuredRows.filter(row => finite(row.best_score) && improvement(row, group.direction, true)).length,
    initialMin:seeds.length ? Math.min(...seeds) : null, initialMax:seeds.length ? Math.max(...seeds) : null,
    bestMin:values.length ? Math.min(...values) : null, bestMax:values.length ? Math.max(...values) : null,
    models:ordered(rows.flatMap(row => list(row.models).length ? row.models : [row.model]).filter(text)),
    systems:ordered(rows.map(row => row.system).filter(text))};
}

/** Pure graph, with separate integration/research scopes and no invented run IDs.
 * Callers verify catalog/insights revision binding before passing metadata.
 * Node labels are plain text; callers must render them with textContent.
 */
export function buildResearchMap({catalog, insights, participants, overview} = {}) {
  const nodes = new Map(), links = new Map(), tasks = new Map(), people = new Map(), domains = new Map();
  const literatureSets = new Map(), researchRows = new Map();
  const addNode = node => {
    if (!nodes.has(node.id)) nodes.set(node.id, {...node, counts:emptyCounts(), measurements:[]});
    return nodes.get(node.id);
  };
  const addLink = (source, target, kind, extra = {}) => {
    const key = JSON.stringify([source, target, kind, extra.sourceScope || '']);
    if (!links.has(key)) links.set(key, {id:id('edge',key), source, target, kind, count:0, ...extra});
    return links.get(key);
  };
  for (const domain of list(insights?.domains)) if (text(domain?.id) && text(domain.label)) {
    const node = addNode({id:id('domain',domain.id), kind:'domain', label:domain.label,
      domainId:domain.id, source:'taxonomy', description:detail(domain.description), why_it_matters:detail(domain.why_it_matters)});
    domains.set(domain.id, node);
  }
  const domainNode = domainId => {
    if (!domains.has(domainId)) {
      const node = addNode({id:id('domain',domainId), kind:'domain', label:DOMAIN_LABELS.get(domainId) || 'Mixed / unclassified',
        domainId, source:domainId !== 'unknown' ? 'native_task_classification' : 'unclassified'});
      domains.set(domainId, node);
    }
    return domains.get(domainId);
  };
  for (const task of list(catalog?.tasks)) if (text(task?.id) && !tasks.has(task.id)) {
    const recorded = insights?.task_annotations?.[task.id]?.domain_id;
    const domain = domainNode(domains.has(recorded) ? recorded : 'unknown');
    const node = addNode({id:id('task',task.id), kind:'task', label:text(task.name) || task.id,
      taskId:task.id, domainId:domain.domainId, source:'catalog', executable:task.executable === true,
      description:detail(task.description), paper_ids:ordered(list(task.paper_ids).filter(text)),
      declaredStatus:text(task.declared_status), protocol:text(task.protocol), runtimeReadiness:text(task.runtime_readiness)});
    node.counts.catalogTasks = 1; domain.counts.catalogTasks++;
    tasks.set(task.id, {node, task}); addLink(domain.id,node.id,'domain').count = 1;
  }
  const adapters = new Map(), papers = new Map();
  for (const participant of list(participants?.participants)) if (text(participant?.id) && !people.has(participant.id)) {
    const node = addNode({id:id('participant',participant.id), kind:'participant', label:text(participant.name) || participant.id,
      participantId:participant.id, domainId:null, source:'registry', recordKind:text(participant.record_kind),
      registrationStatus:text(participant.registration_status),description:detail(participant.description),
      attribution:{display:detail(participant.attribution?.display)},nativeAdapters:list(participant.native_adapters).length,
      papers:list(participant.papers).filter(paper=>text(paper?.id)).map(paper=>({id:paper.id,title:detail(paper.title),url:safeURL(paper.url)})).sort((a,b)=>a.id.localeCompare(b.id))});
    people.set(participant.id,node);
    for (const paper of list(participant.papers)) if (text(paper?.id)) {
      if (!papers.has(paper.id)) papers.set(paper.id,new Set()); papers.get(paper.id).add(node.id);
    }
    for (const adapter of list(participant.native_adapters)) if (text(adapter?.engine)) {
      if (!adapters.has(adapter.engine)) adapters.set(adapter.engine,new Set());
      adapters.get(adapter.engine).add(participant.id);
    }
  }
  for (const {node,task} of tasks.values()) for (const paperId of ordered(list(task.paper_ids).filter(text))) {
    for (const participantId of papers.get(paperId) || []) {
      const edge = addLink(node.id,participantId,'literature',{sourceScope:'paper_reference',paperIds:[]});
      edge.paperIds = ordered([...edge.paperIds,paperId]); edge.count = edge.paperIds.length;
      if (!literatureSets.has(participantId)) literatureSets.set(participantId,new Set());
      literatureSets.get(participantId).add(node.id);
    }
  }
  for (const [participantId,members] of literatureSets) nodes.get(participantId).counts.literatureTasks = members.size;
  const systemNode = system => {
    if (!text(system)) return null;
    if (people.has(system)) return people.get(system);
    const alias = SYSTEM_ALIASES.get(system);
    if (alias && people.has(alias)) return people.get(alias);
    const matches = adapters.get(system);
    if (matches?.size === 1) return people.get([...matches][0]);
    return addNode({id:id('system',system),kind:'participant',label:system,participantId:null,
      domainId:null,source:'published_system',system});
  };
  // Full system progress is independent of task-bound outcome evidence below:
  // a failed/queued run can have no published task measurement at all.
  const progressSeen = new Set();
  for (const system of list(overview?.systems)) if (text(system?.system) && !progressSeen.has(system.system)) {
    const keys = ['runs','completed','active','failed','cancelled','other'];
    if (keys.some(key=>!count(system[key])) || system.runs !== keys.slice(1).reduce((sum,key)=>sum+system[key],0)) continue;
    progressSeen.add(system.system);
    const node = systemNode(system.system);
    if (!node.integrationSummary) node.integrationSummary = {scope:'published_integration_runs',systems:[],runs:0,completed:0,active:0,failed:0,cancelled:0,other:0};
    for (const key of keys) node.integrationSummary[key] += system[key];
    node.integrationSummary.systems = ordered([...node.integrationSummary.systems,system.system]);
  }
  const applyRows = (targets, rows, group) => {
    const measured = measurement(group,rows);
    const scopeKey = group.scope === 'canonical' ? 'integrationRuns' : group.scope === 'native_research' ? 'researchRuns' : 'nativeOutcomes';
    for (const target of targets) {
      target.counts[scopeKey] += rows.length;
      target.counts.measured += measured.measured; target.counts.improved += measured.improved;
      for (const row of rows) target.counts[stateKey(row.state)]++;
      target.measurements.push(measured);
      if (group.scope === 'native_research') {
        if (!researchRows.has(target.id)) researchRows.set(target.id,[]);
        researchRows.get(target.id).push(...rows);
      }
    }
    return measured;
  };
  let unmatchedCanonical = 0;
  for (const cohort of list(overview?.cohorts)) {
    if (!text(cohort?.task_id) || !text(cohort.cohort) || !text(cohort.metric) || !['maximize','minimize'].includes(cohort.direction)) continue;
    const entry = tasks.get(cohort.task_id);
    const validRows = list(cohort.points).filter(row => row && text(row.system));
    if (!entry) { unmatchedCanonical += validRows.length; continue; }
    const grouped = new Map();
    for (const row of validRows) { if (!grouped.has(row.system)) grouped.set(row.system,[]); grouped.get(row.system).push(row); }
    for (const [system,rows] of grouped) {
      const participant = systemNode(system), node = entry.node;
      const m = applyRows([node,participant,domainNode(node.domainId)],rows,{scope:'canonical',protocol:cohort.cohort,
        taskId:cohort.task_id,metric:cohort.metric,direction:cohort.direction,units:null});
      const edge = addLink(node.id,participant.id,'measured',{sourceScope:'canonical',measurements:[]});
      edge.count += rows.length; edge.measurements.push(m);
    }
  }
  const observed = new Map();
  const observe = (row,scope,system,protocol) => {
    if (!row || !text(row.task_id) || !text(row.metric) || !(['maximize','minimize'].includes(row.direction) || scope === 'native_result' && paired(row)) || !text(protocol)) return;
    const objectives = paired(row) ? row.objectives.map(o=>({metric:o.metric,direction:o.direction})) : [];
    const key = JSON.stringify([scope,system,row.task_id,protocol,row.metric,row.direction,text(row.units),objectives]);
    if (!observed.has(key)) observed.set(key,{row,scope,system,protocol,rows:[]}); observed.get(key).rows.push(row);
  };
  for (const row of list(overview?.research?.runs)) observe(row,'native_research','sciel',row?.protocol);
  for (const row of list(overview?.native_results)) if (text(row?.system)) observe(row,'native_result',row.system,`system:${row.system}`);
  for (const [key,{row,scope,system,protocol,rows}] of observed) {
    const domainId = (scope === 'native_research' ? NATIVE_DOMAINS : NATIVE_RESULT_DOMAINS).get(row.task_id) || 'unknown';
    const domain = domainNode(domainId), participant = systemNode(system);
    const node = addNode({id:id('research',key),kind:'research',label:text(row.task_name) || row.task_id,
      taskId:row.task_id,domainId,source:scope,protocol,metric:row.metric,direction:row.direction,
      catalogEquivalent:false,protocolIdentity:scope === 'native_research' ? 'recorded_digest' : 'system_scoped_not_canonical'});
    addLink(domain.id,node.id,'domain').count = 1;
    const m = applyRows([node,participant,domain],rows,{scope,protocol,taskId:row.task_id,
      metric:row.metric,direction:row.direction,units:text(row.units),
      objectives:paired(row) ? row.objectives.map(o=>({metric:o.metric,direction:o.direction})) : []});
    const edge = addLink(node.id,participant.id,'measured',{sourceScope:scope,measurements:[]});
    edge.count += rows.length; edge.measurements.push(m);
  }
  for (const [nodeId,rows] of researchRows) nodes.get(nodeId).selfImprovement = selfImprovement(rows);
  const sortedNodes = [...nodes.values()].sort((a,b)=>a.id.localeCompare(b.id));
  const sortedLinks = [...links.values()].sort((a,b)=>a.id.localeCompare(b.id));
  for (const node of sortedNodes) node.measurements.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
  for (const link of sortedLinks) link.measurements?.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
  const research = list(overview?.research?.runs);
  return {nodes:sortedNodes,links:sortedLinks,domains:[...domains.values()].sort((a,b)=>a.id.localeCompare(b.id)),
    summary:{catalogTasks:tasks.size,domains:domains.size,participants:people.size,
      literatureLinks:sortedLinks.filter(link=>link.kind === 'literature').length,
      measuredLinks:sortedLinks.filter(link=>link.kind === 'measured').length,
      integrationRuns:count(overview?.summary?.runs) ? overview.summary.runs : null,
      researchRuns:count(overview?.research?.total) ? overview.research.total : null,
      nativeOutcomes:list(overview?.native_results).length,unmatchedCanonical,
      publishedAt:finite(overview?.generated_at) ? overview.generated_at : null,
      sourceGeneratedAt:finite(overview?.source_generated_at) ? overview.source_generated_at : null,
      researchSourceGeneratedAt:finite(overview?.research?.source_generated_at) ? overview.research.source_generated_at : null,
      truncated:typeof overview?.truncated === 'boolean' ? overview.truncated : null,
      selfImprovement:selfImprovement(research),
      availability:{catalog:Array.isArray(catalog?.tasks),insights:Array.isArray(insights?.domains),
        participants:Array.isArray(participants?.participants),results:overview?.schema === 'arena.results-overview/1'},
      scopeNote:'Integration runs and native research observations are separate collections, not a combined run total.'}};
}
