// A deterministic editorial layout. Coordinates encode no scientific distance.
export const MAP_WIDTH = 1100;
export const MAP_HEIGHT = 800;
export const DOMAIN_STYLE = {
  mathematics: {color:'#e37861', x:660, y:350, labelX:735, labelY:78, short:'Mathematics'},
  'machine-learning': {color:'#629bc4', x:389, y:419, labelX:91, labelY:329, short:'Machine learning'},
  'computer-systems': {color:'#8684b9', x:467, y:201, labelX:421, labelY:59, short:'Computer systems'},
  'operations-research': {color:'#d3a34e', x:826, y:451, labelX:859, labelY:384, short:'Operations research'},
  'robotics-control': {color:'#ae76a0', x:269, y:214, labelX:170, labelY:91, short:'Robotics & control'},
  physics: {color:'#dfb23e', x:751, y:180, labelX:818, labelY:132, short:'Physics'},
  'chemistry-materials': {color:'#bc88b8', x:888, y:272, labelX:906, labelY:218, short:'Chemistry & materials'},
  'biology-health': {color:'#65ad8b', x:181, y:494, labelX:38, labelY:541, short:'Biology & health'},
  'earth-environment': {color:'#a0b75f', x:269, y:648, labelX:150, labelY:734, short:'Earth & environment'},
  'software-engineering': {color:'#55a7aa', x:521, y:651, labelX:449, labelY:744, short:'Software engineering'},
  'finance-economics': {color:'#bc965b', x:813, y:628, labelX:829, labelY:710, short:'Finance & economics'},
  unknown: {color:'#a4a9b0', x:953, y:543, labelX:883, labelY:612, short:'Mixed / unclassified'},
};

function hash(value) {
  let result = 2166136261;
  for (const character of value) result = Math.imul(result ^ character.charCodeAt(0), 16777619);
  return result >>> 0;
}

export function layoutResearchMap(model) {
  const groups = new Map(), positions = new Map();
  const orderedNodes = [...model.nodes].sort((a,b) => a.id.localeCompare(b.id));
  for (const node of orderedNodes) {
    if (node.kind === 'participant' || node.kind === 'domain') continue;
    if (!groups.has(node.domainId)) groups.set(node.domainId, []);
    groups.get(node.domainId).push(node);
  }
  for (const [domainId, members] of groups) {
    const style = DOMAIN_STYLE[domainId] || DOMAIN_STYLE.unknown;
    const spread = 13 + Math.sqrt(members.length) * 7.6;
    // Golden-angle packing, softly deformed to make neighboring fields meet.
    [...members].sort((a,b) => hash(a.id) - hash(b.id) || a.id.localeCompare(b.id)).forEach((node,index) => {
      const seed = hash(node.id), angle = index * 2.39996323;
      const distance = Math.sqrt((index + .6) / members.length);
      const radius = spread * distance * (1 + .13 * Math.sin(angle * 3) + .09 * Math.cos(angle * 5));
      const x = style.x + radius * Math.cos(angle) * 1.11 + ((seed % 11) - 5) * .3;
      const y = style.y + radius * Math.sin(angle) * .84;
      positions.set(node.id, {...node, x, y, color:style.color,
        radius:node.kind === 'research' ? 5.5 : node.counts.measured ? 4.5 : 2.4 + (seed % 3) * .3});
    });
  }
  const related = new Map();
  for (const edge of [...model.links].sort((a,b) => a.id.localeCompare(b.id))) {
    if (edge.kind === 'domain') continue;
    const task = positions.get(edge.source);
    if (!task) continue;
    if (!related.has(edge.target)) related.set(edge.target, []);
    related.get(edge.target).push(task);
  }
  const systems = orderedNodes.filter(node => node.kind === 'participant');
  systems.forEach((node,index) => {
    const members = related.get(node.id) || [], seed = hash(node.id);
    const counts = new Map();
    for (const member of members) counts.set(member.domainId, (counts.get(member.domainId) || 0) + 1);
    const dominant = [...counts].sort((a,b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0];
    const style = DOMAIN_STYLE[dominant] || DOMAIN_STYLE.unknown;
    const mean = axis => members.reduce((sum,item) => sum + item[axis], 0) / members.length;
    const x = members.length ? mean('x') + ((seed % 31) - 15) * 2.5 : 525 + Math.cos(index * 2.4) * 78;
    const y = members.length ? mean('y') + ((seed % 43) - 21) * 1.9 : 470 + Math.sin(index * 2.4) * 75;
    positions.set(node.id, {...node, x, y, color:node.participantId === 'sciel' ? '#f0b53d' : style.color,
      dominantDomain:dominant, radius:5 + Math.min(7, Math.sqrt(members.length) * .65)});
  });
  // Resolve circle collisions locally without applying a force-based meaning to edges.
  const points = [...positions.values()];
  for (let iteration=0; iteration<12; iteration++) {
    const grid = new Map();
    for (const point of points) {
      const col = Math.floor(point.x / 28), row = Math.floor(point.y / 28);
      for (let dx=-1; dx<=1; dx++) for (let dy=-1; dy<=1; dy++) {
        for (const other of grid.get(`${col+dx}:${row+dy}`) || []) {
          const x = point.x-other.x, y = point.y-other.y, distance = Math.hypot(x,y) || .01;
          const minimum = point.radius + other.radius + 1.3;
          if (distance >= minimum) continue;
          const push = (minimum-distance) / distance * .36;
          point.x += x*push; point.y += y*push; other.x -= x*push; other.y -= y*push;
        }
      }
      const key = `${col}:${row}`;
      if (!grid.has(key)) grid.set(key, []);
      grid.get(key).push(point);
      point.x = Math.max(50, Math.min(1040, point.x));
      point.y = Math.max(105, Math.min(700, point.y));
    }
  }
  // A later pair can nudge an already-visited point past its earlier clamp.
  for (const point of points) {
    point.x = Math.max(50, Math.min(1040, point.x));
    point.y = Math.max(105, Math.min(700, point.y));
  }
  for (const node of [...model.domains].sort((a,b) => a.id.localeCompare(b.id))) {
    const style = DOMAIN_STYLE[node.domainId] || DOMAIN_STYLE.unknown;
    positions.set(node.id, {...node, ...style, radius:0});
  }
  return positions;
}

const measured = node => Number.isFinite(node.counts?.measured) && node.counts.measured > 0;
const matches = (node, query) => `${node.label} ${node.taskId || ''} ${node.participantId || ''}`.toLocaleLowerCase().includes(query);
const filters = ({domain='all', mode='landscape', query=''} = {}) => ({domain, mode, query:query.trim().toLocaleLowerCase()});
const eligible = (node, {domain, mode}) => node && node.kind !== 'domain' && node.kind !== 'participant' &&
  (domain === 'all' || node.domainId === domain) && (mode !== 'recorded' || measured(node));

function eligibleLinks(model, options) {
  const nodes = new Map(model.nodes.map(node => [node.id, node]));
  return model.links.filter(edge => {
    const source = nodes.get(edge.source), target = nodes.get(edge.target);
    if (!['literature','measured'].includes(edge.kind) || !eligible(source, options) || target?.kind !== 'participant') return false;
    // A published run edge can exist without a measured outcome (e.g. failed).
    if (options.mode === 'recorded' && (edge.kind !== 'measured' ||
        !edge.measurements?.some(row => Number.isFinite(row.measured) && row.measured > 0))) return false;
    return !options.query || matches(source, options.query) || matches(target, options.query);
  });
}

export function visibleResearchNodes(model, options = {}) {
  const selected = filters(options), visible = new Set(), searchedSystems = new Set();
  for (const node of model.nodes) {
    if (node.kind === 'domain') continue;
    if (node.kind === 'participant') {
      if (selected.query && matches(node, selected.query)) searchedSystems.add(node.id);
      if (selected.domain === 'all' && (selected.mode !== 'recorded' || measured(node)) &&
          (!selected.query || matches(node, selected.query))) visible.add(node.id);
    } else if (eligible(node, selected) && (!selected.query || matches(node, selected.query))) visible.add(node.id);
  }
  // Only an explicitly searched system expands its neighborhood. Systems added
  // as context for a matching task must not reveal unrelated sibling tasks.
  for (const edge of eligibleLinks(model, selected)) {
    if (visible.has(edge.source) || searchedSystems.has(edge.target)) {
      visible.add(edge.source);
      visible.add(edge.target);
    }
  }
  return visible;
}

export function visibleResearchLinks(model, options = {}, visible = visibleResearchNodes(model, options)) {
  return eligibleLinks(model, filters(options)).filter(edge => visible.has(edge.source) && visible.has(edge.target));
}
