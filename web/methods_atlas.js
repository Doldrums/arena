// Read-only views of the methods registry. Positions describe ownership, not embeddings.
const populationViews = new WeakMap(), architectureViews = new WeakMap();
const SVG = 'http://www.w3.org/2000/svg';
const list = value => Array.isArray(value) ? value : [];
const short = value => String(value || '').slice(0, 10);
const validNumber = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const count = (methods, key, fallback) => validNumber(methods.summary?.[key]) ? Number(methods.summary[key]) : fallback;
const reusable = row => row.record_kind !== 'solution_execution_bundle' && row.protocol?.permanent_toolbox_method !== false;
const ids = values => list(values).map(row => typeof row === 'string' ? row : row?.id || row?.method_id).filter(Boolean);
const unique = values => [...new Set(values)];
const activeIds = lab => lab.revision_available === false ? [] : [...ids(lab.active_methods), ...ids(lab.active_adapters)];
function element(tag, className, content) { const node = document.createElement(tag); if (className) node.className = className; if (content !== undefined) node.textContent = String(content); return node; }
function svg(tag, attributes = {}, content) { const node = document.createElementNS(SVG, tag); for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value); if (content !== undefined) node.textContent = String(content); return node; }
function add(parent, ...children) { children.flat().filter(Boolean).forEach(child => parent.append(child)); return parent; }
function button(label, action, className = 'ma-link') { const node = element('button', className, label); node.type = 'button'; node.addEventListener('click', action); return node; }
function metric(solution) { const value = solution.native_metric ? solution.native_score : solution.score; return validNumber(value) ? Number(value).toFixed(6) + ' ' + (solution.native_metric || 'combined_score') : 'Task value not recorded'; }
function toolName(model, id) { return model.tools.find(tool => tool.id === id)?.name || short(id); }
function ordered(rows) { return rows.map((row, index) => ({...row, _order:index})).sort((a, b) => Number(a.registration_seq ?? a._order) - Number(b.registration_seq ?? b._order)); }
function populationModel(methods) {
  const tools = ordered(list(methods.tools).filter(reusable));
  const labs = list(methods.labs), solutions = ordered(list(methods.solutions));
  const groups = [{id:'__shared__', name:'Shared toolbox', kind:'shared', tools:[], solutions:[]}];
  for (const lab of labs) groups.push({id:lab.id, name:lab.id, kind:'lab', lab, tools:[], solutions:[]});
  const byId = new Map(groups.map(group => [group.id, group]));
  for (const tool of tools) {
    const owner = tool.provenance === 'common_toolbox' ? '__shared__' : tool.author_lab;
    let group = byId.get(owner);
    if (!group) {
      group = byId.get('__other__');
      if (!group) {group = {id:'__other__', name:'Other recorded owners', kind:'other', tools:[], solutions:[]}; groups.push(group); byId.set(group.id, group);}
    }
    group.tools.push({tool, owned:true, active:group.kind === 'lab' && activeIds(group.lab).includes(tool.id)});
    for (const lab of labs) {
      if (group.id !== lab.id && activeIds(lab).includes(tool.id)) byId.get(lab.id).tools.push({tool, owned:false, active:true});
    }
  }
  for (const solution of solutions) {
    const group = byId.get(solution.lab_id);
    if (group) group.solutions.push(solution);
  }
  const missing = labs.flatMap(activeIds).filter(id => !tools.some(tool => tool.id === id));
  return {tools, labs, solutions, groups, missing:unique(missing), methods};
}
function populationSignature(model) {
  return JSON.stringify([model.methods.summary, model.tools.map(t => [t.id,t.name,t.author_lab,t.provenance,t.status,t.parents,t.dependencies,t.active_in,t.adopted_by,t.invocations,t.registration_seq]),
    model.labs.map(l => [l.id,l.mode,l.status,l.current_stage,l.revision_id,l.revision_number,l.revision_available,l.active_methods,l.active_adapters]),
    model.solutions.map(s => [s.id,s.lab_id,s.method_id,s.experiment_id,s.score,s.native_metric,s.native_score,s.confirmed]), model.methods.storage]);
}
function membership(model, tool) {
  return model.labs.filter(lab => activeIds(lab).includes(tool.id)).map(lab => lab.id);
}
function selectionInfo(view, node) {
  if (!node) {
    view.detail.replaceChildren(element('strong', '', 'Explore the recorded population'), element('span', '', 'Hover or focus a cell to trace parents, dependencies and adoption. Select it to open its saved artifact.'));
    return;
  }
  const {record, kind, group} = node, name = kind === 'tool' ? record.name || short(record.id) : record.program_id || short(record.id);
  const heading = element('strong', '', name), facts = element('span', 'ma-inspect-facts');
  if (kind === 'solution') {
    facts.textContent = 'Evaluated program · ' + group.name + ' · ' + metric(record) + (record.confirmed === true ? ' · confirmed' : '');
    view.detail.replaceChildren(heading, facts, element('span', '', 'Saved program ' + short(record.id) + ' · separate from tool-state trials.'));
    return;
  }
  const active = membership(view.model, record);
  facts.textContent = short(record.id) + ' · ' + (record.status || 'State not recorded') + ' · ' + (record.invocations ?? 0) + ' actual invocations';
  const relations = element('div', 'ma-relations');
  for (const [label, references] of [['Parents', ids(record.parents)], ['Dependencies', ids(record.dependencies)]]) {
    const part = element('span', 'ma-relation'); part.append(element('span', '', label + ': '));
    if (!references.length) part.append(element('span', '', 'none recorded'));
    references.forEach((id, index) => {if (index) part.append(document.createTextNode(', ')); part.append(button(toolName(view.model, id), () => view.onSelect?.('tool', id)));});
    relations.append(part);
  }
  for (const [label, values] of [['Active in', active], ['Adopted by', unique(ids(record.adopted_by))]]) {
    const part = element('span', 'ma-relation'); part.append(element('span', '', label + ': '));
    const unknown = label === 'Active in' ? view.model.labs.filter(lab => lab.revision_available === false).map(lab => lab.id) : [];
    if (!values.length) part.append(element('span', '', unknown.length ? 'no verified current membership' : 'none recorded'));
    values.forEach((id, index) => {if (index) part.append(document.createTextNode(', ')); part.append(button(id, () => view.onSelect?.('lab', id)));});
    if (unknown.length) part.append(element('span', '', '; unknown for ' + unknown.join(', ')));
    relations.append(part);
  }
  view.detail.replaceChildren(heading, facts, relations);
}
function highlightPopulation(view, key) {
  const current = view.nodes.get(key), record = current?.record;
  const parents = new Set(ids(record?.parents)), dependencies = new Set(ids(record?.dependencies));
  const children = new Set(current?.kind === 'tool' ? view.model.tools.filter(t => ids(t.parents).includes(record.id)).map(t => t.id) : []);
  const dependants = new Set(current?.kind === 'tool' ? view.model.tools.filter(t => ids(t.dependencies).includes(record.id)).map(t => t.id) : []);
  const relatedLabs = new Set(current?.kind === 'tool' ? [...membership(view.model, record), ...ids(record.adopted_by)] : [current?.group.id]);
  for (const node of view.nodes.values()) {
    const same = current && node.kind === current.kind && node.record.id === record.id;
    const relation = same ? 'selected' : parents.has(node.record.id) ? 'parent' : dependencies.has(node.record.id) ? 'dependency' : children.has(node.record.id) ? 'child' : dependants.has(node.record.id) ? 'dependant' : '';
    node.element.dataset.relation = relation;
    node.element.classList.toggle('is-muted', Boolean(current && !relation));
    node.element.setAttribute('aria-pressed', String(node.key === view.selected));
  }
  for (const group of view.root.querySelectorAll('.ma-population-group')) group.classList.toggle('is-related', Boolean(current && relatedLabs.has(group.dataset.groupId)));
  selectionInfo(view, current);
}
function choosePopulation(view, key) {
  const node = view.nodes.get(key); if (!node) return;
  view.selected = key; highlightPopulation(view, key);
  if (node.kind === 'tool') view.onSelect?.('tool', node.record.id);
  else view.onSelect?.('solution', node.record.id);
}
function populationCell(view, group, kind, record, index, {owned = true, active = false} = {}) {
  const columns = group.columns, row = Math.floor(index / columns), column = index % columns;
  const x = (279 - (columns * 20 + 10)) / 2 + 10 + column * 20 + (row % 2 ? 10 : 0), y = 13 + row * 17;
  const key = JSON.stringify([group.id, kind, record.id]);
  const title = (kind === 'tool' ? record.name || short(record.id) : record.program_id || short(record.id)) + ' · ' + (kind === 'tool' ? (owned ? 'owned version' : 'active shared version') : 'evaluated program') + ' · ' + short(record.id);
  const node = svg('g', {'class':'ma-cell' + (kind === 'solution' ? ' ma-program' : '') + (active ? ' is-active' : '') + (!owned ? ' is-imported' : '') + (view.previousIds && !view.previousIds.has(record.id) ? ' is-new' : ''),
    transform:`translate(${x} ${y})`, tabindex:index === 0 ? 0 : -1, role:'button', 'aria-label':title, 'aria-pressed':'false', 'data-key':key, 'data-record-id':record.id, 'data-kind':kind});
  node.append(svg('title', {}, title));
  node.append(kind === 'solution' ? svg('circle', {r:9, class:'ma-cell-shape'}) : svg('polygon', {points:'0,-10 8.66,-5 8.66,5 0,10 -8.66,5 -8.66,-5', class:'ma-cell-shape'}));
  if (active) node.append(svg('circle', {r:2.6, class:'ma-active-dot'}));
  if (kind === 'solution' && record.confirmed === true) node.append(svg('circle', {r:5, class:'ma-confirmed-ring'}));
  const value = {key, element:node, kind, record, group}; view.nodes.set(key, value);
  node.addEventListener('pointerenter', () => highlightPopulation(view, key));
  node.addEventListener('pointerleave', () => highlightPopulation(view, view.selected));
  node.addEventListener('focus', () => highlightPopulation(view, key));
  node.addEventListener('blur', () => highlightPopulation(view, view.selected));
  node.addEventListener('click', () => choosePopulation(view, key));
  node.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); choosePopulation(view, key); return;}
    if (event.key === 'Escape') {event.preventDefault(); view.selected = null; highlightPopulation(view, null); return;}
    if (!['ArrowRight','ArrowLeft','ArrowDown','ArrowUp','Home','End'].includes(event.key)) return;
    event.preventDefault();
    const peers = [...view.nodes.values()].filter(item => item.group.id === group.id), at = peers.findIndex(item => item.key === key);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? peers.length - 1 : at + ({ArrowRight:1,ArrowLeft:-1,ArrowDown:columns,ArrowUp:-columns}[event.key]);
    const target = peers[Math.max(0, Math.min(peers.length - 1, next))];
    peers.forEach(item => item.element.setAttribute('tabindex', item === target ? '0' : '-1')); target?.element.focus();
  });
  return node;
}

export function renderMethodsPopulation(root, methods = {}, {onSelect} = {}) {
  let view = populationViews.get(root);
  if (!view) {view = {root, selected:null, nodes:new Map()}; populationViews.set(root, view);}
  view.onSelect = onSelect;
  const model = populationModel(methods), signature = populationSignature(model);
  if (signature === view.signature && root.classList.contains('ma-population')) return;
  const focused = root.contains(document.activeElement) ? document.activeElement.dataset.key : null;
  view.previousIds = view.model ? new Set([...view.model.tools, ...view.model.solutions].map(row => row.id)) : null;
  view.model = model; view.signature = signature; view.nodes = new Map(); root.classList.add('ma-atlas', 'ma-population');
  const heading = add(element('div', 'ma-heading'), element('div', '', 'Population'), element('span', '', count(methods, 'methods', model.tools.length) + ' reusable versions · ' + count(methods, 'solutions', model.solutions.length) + ' evaluated programs'));
  const note = element('p', 'ma-note', 'All laboratories · immutable content-addressed registry. Groups show recorded ownership and active membership. A shared version can appear in several labs.');
  const legend = add(element('div', 'ma-legend'), element('span', 'ma-legend-tool', 'Tool version'), element('span', 'ma-legend-active', 'Active in this lab'), element('span', 'ma-legend-program', 'Evaluated program'), element('span', 'ma-legend-parent', 'Parent / child'), element('span', 'ma-legend-dependency', 'Dependency'));
  const groups = element('div', 'ma-population-groups');
  model.groups.forEach((group, groupIndex) => {
    const section = element('section', 'ma-population-group'); section.dataset.groupId = group.id; section.style.setProperty('--ma-group-color', ['#8793a4','#778bd0','#8b80bc','#63a194','#b79a6c'][groupIndex % 5]);
    const header = element('div', 'ma-group-heading');
    header.append(group.lab ? button(group.name, () => view.onSelect?.('lab', group.id), 'ma-group-name') : element('strong', 'ma-group-name', group.name));
    const ownedCount = group.tools.filter(row => row.owned).length, activeCount = group.tools.filter(row => row.active).length;
    header.append(element('span', '', group.kind === 'lab' ? ownedCount + ' owned · ' + (group.lab.revision_available === false ? 'active unknown' : activeCount + ' active') + ' · ' + group.solutions.length + ' programs' : group.tools.length + ' versions'));
    section.append(header);
    const total = group.tools.length + group.solutions.length;
    group.columns = Math.min(12, Math.max(3, Math.ceil(Math.sqrt(total * 1.35))));
    const rows = Math.max(1, Math.ceil(total / group.columns));
    const field = svg('svg', {class:'ma-hex-field', viewBox:`0 0 279 ${Math.max(56, rows * 17 + 10)}`, width:279, height:Math.max(56, rows * 17 + 10), role:'group', 'aria-label':group.name + ' recorded versions'});
    let index = 0;
    for (const item of group.tools) field.append(populationCell(view, group, 'tool', item.tool, index++, item));
    for (const solution of group.solutions) field.append(populationCell(view, group, 'solution', solution, index++));
    section.append(field);
    if (!total) section.append(element('p', 'ma-group-empty', 'No recorded versions yet'));
    groups.append(section);
  });
  view.detail = element('div', 'ma-population-detail'); view.detail.setAttribute('aria-live', 'polite');
  const coverage = element('p', 'ma-note ma-coverage', 'Cells use an ordered hex layout. Position and distance do not encode score, niches or code similarity.');
  const knownTotal = count(methods, 'methods', model.tools.length);
  if (knownTotal > model.tools.length || model.missing.length) coverage.append(document.createTextNode(' Showing ' + model.tools.length + ' tool versions in this snapshot' + (model.missing.length ? '; ' + model.missing.length + ' active references are outside this view' : '') + '. Full history remains in the registry.'));
  root.replaceChildren(heading, note, legend, groups, view.detail, coverage);
  if (!view.nodes.has(view.selected)) view.selected = null;
  highlightPopulation(view, view.selected);
  if (focused && view.nodes.has(focused)) {view.nodes.get(focused).element.setAttribute('tabindex','0'); view.nodes.get(focused).element.focus();}
}

const stages = {generation:'Model proposal',generating:'Model proposal',execution:'Isolated trial',evaluation:'Isolated trial',evaluating:'Isolated trial',capacity_wait:'Waiting for a shared slot',retrieval:'Preparing context',adoption:'Updating lab revision',initial:'Ready',continued:'Step recorded',stopped:'Episode ended',refused:'Proposal refused'};
function currentStage(lab) {return stages[lab.current_stage] || String(lab.current_stage || lab.status || 'Not recorded').replaceAll('_',' ');}
function architectureModel(methods, live) {
  const labs = list(methods.labs), proposals = list(methods.proposals), experiments = list(methods.experiments), tools = list(methods.tools).filter(reusable), transfers = list(methods.transfers), claims = list(methods.claims);
  const rejected = proposals.filter(row => ['invalid','refused','rejected','failed'].includes(row.status)), replays = experiments.filter(row => row.purpose === 'replay'), adoptions = transfers.filter(row => row.kind !== 'solution_transfer');
  const waiting = labs.filter(lab => lab.current_stage === 'capacity_wait'), active = new Set();
  for (const lab of live ? labs : []) {
    if (lab.current_stage === 'capacity_wait') {active.add('queue'); continue;}
    if (['generation','generating'].includes(lab.current_stage)) active.add('proposal');
    if (['execution','evaluation','evaluating'].includes(lab.current_stage)) active.add('trial');
    if (['retrieval','adoption'].includes(lab.current_stage)) active.add('revision');
    if (lab.current_stage === 'replay') active.add('replay');
  }
  const last = rows => rows.at(-1), target = (kind, row) => row?.id ? {kind,id:row.id} : null;
  const steps = [
    {id:'revision',title:'Lab revision',note:labs.length+' labs · pinned tools + evidence',count:labs.length,target:target('lab',last(labs)),x:18,y:20},
    {id:'proposal',title:'Model proposal',note:count(methods,'proposals',proposals.length)+' recorded model calls',count:count(methods,'proposals',proposals.length),target:target('proposal',last(proposals)),x:257,y:20},
    {id:'validation',title:'Format & contract checks',note:rejected.length+' visible proposal refusals',count:rejected.length,target:target('proposal',last(rejected)),x:496,y:20},
    {id:'trial',title:'Isolated trial',note:count(methods,'experiments',experiments.length)+' experiments · '+count(methods,'invocations',0)+' calls',count:count(methods,'experiments',experiments.length),target:target('experiment',last(experiments)),x:496,y:150},
    {id:'evidence',title:'Scoped evidence',note:count(methods,'claims',claims.length)+' saved claims · outcomes retained',count:count(methods,'claims',claims.length),target:target('experiment',last(experiments)),x:257,y:150},
    {id:'feedback',title:'Next research context',note:'Recorded results + bounded memory',count:labs.length,target:target('lab',last(labs)),x:18,y:150},
    {id:'replay',title:'Independent replay',note:replays.length+' recorded replays',count:replays.length,target:target('experiment',last(replays)),x:18,y:295},
    {id:'release',title:'Release / publication',note:count(methods,'released',tools.filter(t=>t.status==='released').length)+' released tool versions',count:count(methods,'released',0),target:target('tool',last(tools.filter(t=>t.status==='released'))),x:257,y:295},
    {id:'adopt',title:'Adopt & use again',note:count(methods,'adoptions',adoptions.length)+' adoptions · '+adoptions.filter(t=>t.next_use_experiment_id).length+' with later use',count:count(methods,'adoptions',adoptions.length),target:target('transfer',last(adoptions)),x:496,y:295}
  ];
  const methodLabs = labs.some(lab => ['B','C'].includes(lab.mode));
  if (!methodLabs) for (const step of steps.slice(6)) {step.disabled = true; step.note = 'Not enabled in mode A';}
  else if (methods.identity?.library_policy === 'unreplayed') {steps[6].disabled = true; steps[6].note = 'Not required by library policy';}
  return {labs,proposals,experiments,tools,transfers,claims,rejected,replays,adoptions,waiting,active,steps,live};
}
function architectureSignature(model, methods) {
  const identity = methods.identity || {};
  return JSON.stringify([model.steps,model.labs.map(l=>[l.id,l.mode,l.status,l.current_stage,l.revision_id,l.revision_number,l.revision_available]),[...model.active],model.live,identity.library_policy,identity.transfer_policy,identity.executor,identity.generator,identity.procedure,identity.resources]);
}

export function renderMethodsArchitecture(root, methods = {}, {onSelect, live = false} = {}) {
  let view = architectureViews.get(root);
  if (!view) {view = {root}; architectureViews.set(root,view);}
  view.onSelect = onSelect;
  const model = architectureModel(methods, live === true), signature = architectureSignature(model,methods);
  if (view.signature === signature && root.classList.contains('ma-architecture')) return;
  const focused = root.contains(document.activeElement) ? document.activeElement.dataset.architectureStep : null;
  view.signature = signature;
  root.classList.add('ma-atlas','ma-architecture');
  const heading = add(element('div','ma-heading'),element('div','','Running architecture'),element('span','','All laboratories · '+model.labs.length+' labs'));
  const labs = element('div','ma-architecture-labs');
  for (const lab of model.labs) {
    const row = button('',()=>view.onSelect?.('lab',lab.id),'ma-architecture-lab');
    row.dataset.labId = lab.id;
    add(row,element('strong','',lab.id),element('span','',(model.live?'':'Recorded: ')+currentStage(lab)),element('small','','r'+(lab.revision_number??'—')+' · '+(lab.status||'Status not recorded'))); labs.append(row);
  }
  const scroller = element('div','ma-flow-scroll'); scroller.setAttribute('tabindex','0'); scroller.setAttribute('aria-label','Research process diagram; scroll horizontally on narrow screens');
  const flow = svg('svg',{class:'ma-flow',viewBox:'0 0 715 402',width:715,height:402,role:'group','aria-label':'Recorded laboratory research loop and method transfer branch'});
  const defs = svg('defs'), markerId = 'ma-arrow-' + Math.random().toString(36).slice(2,10);
  const marker = svg('marker',{id:markerId,viewBox:'0 0 6 6',refX:5,refY:3,markerWidth:5,markerHeight:5,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M0 0 L6 3 L0 6',fill:'#b1b8c2'}));defs.append(marker);flow.append(defs);
  const paths = [
    ['revision','proposal','M218 56 H254'],['proposal','validation','M457 56 H493'],['validation','trial','M596 92 V147'],
    ['trial','evidence','M496 186 H460'],['evidence','feedback','M257 186 H221'],['feedback','revision','M118 150 V95'],
    ['evidence','replay','M357 222 V259 H118 V292'],['replay','release','M218 331 H254'],['release','adopt','M457 331 H493'],
    ['adopt','revision','M596 367 V387 H6 V8 H118 V17']
  ];
  for (const [from,to,d] of paths) flow.append(svg('path',{d,class:'ma-flow-edge'+(model.active.has(to)?' is-active':''),'data-from':from,'data-to':to,'marker-end':`url(#${markerId})`}));
  flow.append(svg('text',{x:365,y:253,class:'ma-flow-annotation'},'Method evidence → optional transfer path'));
  const nodes = new Map();
  function highlight(id) {
    flow.querySelectorAll('.ma-flow-edge').forEach(edge=>edge.classList.toggle('is-highlighted',Boolean(id&&(edge.dataset.from===id||edge.dataset.to===id))));
    nodes.forEach((node,key)=>node.classList.toggle('is-highlighted',key===id));
  }
  for (const [index,step] of model.steps.entries()) {
    const node = svg('g',{class:'ma-flow-node'+(model.active.has(step.id)?' is-active':'')+(step.disabled?' is-disabled':''),transform:`translate(${step.x} ${step.y})`,'data-architecture-step':step.id,role:step.target?'button':'group',tabindex:step.target?0:-1,'aria-label':step.title+'. '+step.note+(model.active.has(step.id)?'. Active now.':'')});
    add(node,svg('rect',{width:200,height:72,rx:7}),svg('text',{x:13,y:20,class:'ma-flow-index'},String(index+1).padStart(2,'0')),
      svg('text',{x:35,y:21,class:'ma-flow-title'},step.title),svg('text',{x:13,y:45,class:'ma-flow-note'},step.note));
    if (model.active.has(step.id)) node.append(svg('text',{x:13,y:60,class:'ma-flow-live'},'Active now'));
    if (step.target) {
      node.addEventListener('click',()=>view.onSelect?.(step.target.kind,step.target.id));
      node.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();view.onSelect?.(step.target.kind,step.target.id);}});
    }
    node.addEventListener('pointerenter',()=>highlight(step.id));node.addEventListener('pointerleave',()=>highlight(null));node.addEventListener('focus',()=>highlight(step.id));node.addEventListener('blur',()=>highlight(null));
    nodes.set(step.id,node);flow.append(node);
  }
  scroller.append(flow);
  const queue = add(element('div','ma-queue'+(model.waiting.length&&model.live?' is-active':'')),element('strong','','Shared capacity'),element('span','',model.waiting.length?(model.live?'':'Last recorded queue: ')+model.waiting.map(l=>l.id).join(', ')+' waiting for a shared slot':model.live?'No lab is currently waiting for a shared slot':'No queue in the last recorded state'));
  const identity = methods.identity || {};
  const contract = element('div','ma-contract');
  const executor = identity.executor || {}, generator = identity.generator || {}, resources = identity.resources || {};
  for (const [label,value] of [['Model',generator.model || generator.kind || 'Not recorded'],['Executor',executor.docker_server?'Docker '+executor.docker_server+(executor.architecture?' · '+executor.architecture:''):executor.schema || 'Not recorded'],['Per-call wall',validNumber(resources.wall_seconds)?resources.wall_seconds+' s':'Not recorded'],['Per-call CPU',validNumber(resources.cpu_seconds)?resources.cpu_seconds+' s':'Not recorded'],['Memory',validNumber(resources.memory_bytes)?(Number(resources.memory_bytes)/1048576).toFixed(0)+' MiB':'Not recorded'],['Procedure',short(identity.procedure)||'Not recorded']]) contract.append(add(element('div'),element('span','',label),element('strong','',value)));
  const novelty = element('p','ma-note','Standalone programs also pass the solution novelty gate before evaluation. Reusable tools follow manifest, dependency and resource checks.');
  const policy = element('p','ma-note','Library policy: '+(identity.library_policy||'not recorded')+' · Transfer policy: '+(identity.transfer_policy||'not recorded')+'. Release and adoption do not establish a task gain.');
  const config = element('p','ma-config','Storage: immutable content-addressed registry. RL, bandits, MAP-Elites and VQ storage are not enabled in this runner.');
  root.replaceChildren(heading,labs,scroller,queue,contract,novelty,policy,config);
  if (focused && nodes.has(focused)) nodes.get(focused).focus();
}
