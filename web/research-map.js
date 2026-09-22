import {catalogDigest} from './arena-model.js';
import {buildResearchMap} from './research-map-model.js';
import {DOMAIN_STYLE, layoutResearchMap, visibleResearchNodes, visibleResearchLinks} from './research-map-layout.js';
import {renderResearchInspector} from './research-map-inspector.js';

const SVG = 'http://www.w3.org/2000/svg';
function publicationLabel(timestamp) {
  if (typeof timestamp !== 'number' || !Number.isFinite(timestamp) || timestamp <= 0) return 'Publication time not recorded';
  const date = new Date(timestamp * 1000);
  return Number.isFinite(date.getTime())
    ? `Published ${date.toLocaleDateString('en-GB', {day:'numeric', month:'short', year:'numeric', timeZone:'UTC'})}`
    : 'Publication time not recorded';
}

export function initResearchMap({doc=document, fetcher=(...args)=>fetch(...args), verifyCatalog=catalogDigest, timeoutMs=20000} = {}) {
  const $ = id => doc.getElementById(id), win = doc.defaultView;
  const root = $('research-map'), svg = $('map-canvas');
  let model = null, positions = new Map(), nodeElements = new Map(), edgeElements = new Map();
  let labels = new Map(), domainLabels = new Map(), scene = null, selectedId = null, pending = null, disposed = false;
  let mode = 'landscape', domain = 'all', query = '', zoom = 1, offsetX = 0, offsetY = 0, drag = null;
  const listeners = [];
  const on = (node, type, callback, options) => {
    node.addEventListener(type, callback, options);
    listeners.push(() => node.removeEventListener(type, callback, options));
  };
  function element(tag, attributes={}, text) {
    const node = doc.createElementNS(SVG, tag);
    for (const [key,value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function button(text, callback) {
    const node = doc.createElement('button'); node.type = 'button'; node.textContent = text;
    node.addEventListener('click', callback); return node;
  }
  function select(id) {
    selectedId = positions.has(id) ? id : null;
    $('map-search-results').hidden = true;
    renderResearchInspector({doc, root:$('map-inspector'), model, selected:positions.get(selectedId), onSelect:select});
    updateView();
  }
  function transform() {
    scene?.setAttribute('transform', `translate(${offsetX} ${offsetY}) scale(${zoom})`);
    $('map-zoom-label').textContent = `${Math.round(zoom*100)}%`;
    $('map-zoom-in').disabled = zoom >= 3;
    $('map-zoom-out').disabled = zoom <= .75;
  }
  function changeZoom(next) {
    const previous = zoom; zoom = Math.max(.75, Math.min(3, next));
    offsetX = 550 - (550-offsetX)*zoom/previous;
    offsetY = 400 - (400-offsetY)*zoom/previous; transform();
  }
  function fit() { zoom=1; offsetX=0; offsetY=0; transform(); }
  function setDomain(next) {
    domain = next; $('map-domain').value = domain;
    select(domain === 'all' ? null : model.domains.find(item=>item.domainId === domain)?.id);
  }
  function draw() {
    svg.replaceChildren(element('title', {}, 'Research systems, tasks, and published measurements'),
      element('desc', {}, 'An editorial network layout grouped by research direction. Distance has no quantitative meaning. Use the direction selector and search to explore records.'));
    scene = element('g'); svg.append(scene);
    nodeElements = new Map(); edgeElements = new Map(); labels = new Map(); domainLabels = new Map();
    const edges = element('g', {'aria-hidden':'true'}); scene.append(edges);
    for (const link of model.links) {
      if (link.kind === 'domain') continue;
      if (link.kind === 'measured' && !link.measurements?.some(row=>row.measured>0)) continue;
      const a = positions.get(link.source), b = positions.get(link.target);
      if (!a || !b) continue;
      const bend = Math.min(35, Math.hypot(a.x-b.x, a.y-b.y)*.12);
      const path = element('path', {d:`M${a.x},${a.y} Q${(a.x+b.x)/2+bend},${(a.y+b.y)/2-bend} ${b.x},${b.y}`, class:`map-edge ${link.kind}`});
      edges.append(path); edgeElements.set(link.id, path);
    }
    const nodes = element('g'); scene.append(nodes);
    const ordered = [...positions.values()].filter(item=>item.kind !== 'domain').sort((a,b)=>a.radius-b.radius);
    for (const node of ordered) {
      const group = element('g', {class:`map-node ${node.kind}${node.counts.measured ? ' has-measurement' : ''}`, transform:`translate(${node.x} ${node.y})`,
        'data-node-id':node.id, role:'button', tabindex:node.kind === 'participant' ? '0' : '-1',
        'aria-label':`${node.label}. ${node.kind === 'participant' ? 'System or research work' : 'Task'}. ${node.counts.measured} measured outcomes.`});
      group.append(element('title', {}, node.label), element('circle', {r:Math.max(6,node.radius+3),class:'map-hit'}));
      group.append(element('circle', {r:node.radius, fill:node.color, stroke:node.color, class:'map-dot'}));
      if (node.kind === 'research' && node.counts.measured) group.append(element('circle', {r:1.8, class:'map-core'}));
      if (node.kind !== 'research' && node.counts.measured) group.append(element('circle', {r:node.radius+3.1, class:'map-recorded-ring'}));
      nodes.append(group); nodeElements.set(node.id, group);
    }
    const captions = element('g'); scene.append(captions);
    const prominent = ordered.filter(node=>node.kind === 'participant').sort((a,b)=>
      Number(b.participantId === 'sciel')-Number(a.participantId === 'sciel') || b.counts.literatureTasks-a.counts.literatureTasks).slice(0,8);
    for (const node of prominent) {
      const label = element('text', {x:node.x+node.radius+6,y:node.y+3,class:'map-system-label'}, node.label);
      captions.append(label); labels.set(node.id,label);
    }
    for (const node of model.domains) {
      const position = positions.get(node.id), style = DOMAIN_STYLE[node.domainId] || DOMAIN_STYLE.unknown;
      const group = element('g', {class:'map-domain-label','data-node-id':node.id,role:'button',tabindex:'0','aria-label':`${node.label}, ${node.counts.catalogTasks} catalog tasks`});
      const anchor = style.labelX > 860 ? 'end' : 'start';
      const endY = style.labelY < position.y ? style.labelY+24 : style.labelY-14;
      const endX = style.labelX + (anchor === 'end' ? -18 : 18);
      const sourceX = position.x+(endX-position.x)*.53, sourceY = position.y+(endY-position.y)*.53;
      group.append(element('path', {d:`M${sourceX},${sourceY} L${endX},${endY} L${style.labelX},${endY}`}),
        element('text',{x:style.labelX,y:style.labelY,'text-anchor':anchor},style.short),
        element('text',{x:style.labelX,y:style.labelY+15,'text-anchor':anchor,class:'map-domain-count'},`${node.counts.catalogTasks} tasks`));
      captions.append(group); domainLabels.set(node.id,group);
    }
    fit();
  }
  function updateView() {
    if (!model) return;
    const options = {domain,mode,query};
    const visible = visibleResearchNodes(model, options);
    const visibleEdges = new Set(visibleResearchLinks(model, options, visible).map(link=>link.id));
    const neighbors = new Set([selectedId]);
    for (const edge of model.links) {
      if (edge.source === selectedId) neighbors.add(edge.target);
      if (edge.target === selectedId) neighbors.add(edge.source);
    }
    const selected = positions.get(selectedId), focusDomain = selected?.kind === 'domain' ? selected.domainId : null;
    if (focusDomain) for (const node of model.nodes) if (node.domainId === focusDomain) neighbors.add(node.id);
    if (focusDomain) for (const edge of model.links) if (neighbors.has(edge.source)) neighbors.add(edge.target);
    for (const [id, node] of nodeElements) {
      node.style.display = visible.has(id) ? '' : 'none';
      node.classList.toggle('is-selected', id === selectedId);
      node.classList.toggle('is-dimmed', Boolean(selectedId) && !neighbors.has(id));
      node.setAttribute('aria-pressed', String(id === selectedId));
    }
    for (const edge of model.links) {
      const node = edgeElements.get(edge.id); if (!node) continue;
      node.style.display = visibleEdges.has(edge.id) ? '' : 'none';
      node.classList.toggle('is-selected', edge.source === selectedId || edge.target === selectedId);
      node.classList.toggle('is-dimmed', Boolean(selectedId) && !(neighbors.has(edge.source) && neighbors.has(edge.target)));
    }
    for (const [id,label] of labels) label.style.display = visible.has(id) && (!selectedId || neighbors.has(id)) ? '' : 'none';
    for (const [id,label] of domainLabels) {
      const item = positions.get(id);
      label.style.opacity = domain === 'all' || item.domainId === domain ? '1' : '.22';
    }
    for (const button of $('map-legend').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.domain === domain));
    $('map-empty').hidden = visible.size > 0;
    const taskCount = [...visible].filter(id=>positions.get(id)?.kind === 'task').length;
    $('map-counts').textContent = `${taskCount.toLocaleString('en')} catalog tasks in view · ${model.summary.participants} systems & works indexed · published evidence, not a live feed`;
  }
  function search() {
    query = $('map-search').value; selectedId = null;
    updateView(); renderResearchInspector({doc,root:$('map-inspector'),model,onSelect:select});
    const results = $('map-search-results'); results.replaceChildren();
    const normalized = query.trim().toLocaleLowerCase();
    const visible = visibleResearchNodes(model, {domain,mode,query});
    const matches = model.nodes.filter(node=>node.kind !== 'domain' && visible.has(node.id) &&
      `${node.label} ${node.taskId || ''} ${node.participantId || ''}`.toLocaleLowerCase().includes(normalized));
    for (const item of matches.slice(0,8)) {
      const row = button(item.label,()=>select(item.id)), tag = doc.createElement('small');
      tag.textContent = item.kind === 'participant' ? 'System / work' : 'Task'; row.append(tag); results.append(row);
    }
    results.hidden = !normalized || !matches.length;
  }
  async function refresh() {
    if (pending || disposed) return;
    const controller = new win.AbortController(); pending = controller;
    root.setAttribute('aria-busy','true'); $('map-refresh').disabled = true;
    $('map-status').textContent = model ? 'Updating published map…' : 'Loading the research map…';
    let timer;
    const timeout = new Promise((_,reject)=>{timer=win.setTimeout(()=>{controller.abort();reject(new Error('timeout'));},timeoutMs);});
    const names = ['catalog','insights','participants','results-overview'];
    try {
      const responses = await Promise.race([Promise.allSettled(names.map(async name=>{
        const response = await fetcher(`/api/${name}`, {cache:'no-store',credentials:'same-origin',redirect:'error',signal:controller.signal});
        if (!response.ok) throw new Error('unavailable');
        return response.json();
      })), timeout]);
      if (disposed) return;
      const [catalog,insights,participants,overview] = responses.map(result=>result.status === 'fulfilled' ? result.value : null);
      if (!Array.isArray(catalog?.tasks) || !Array.isArray(insights?.domains) || !Array.isArray(participants?.participants)) throw new Error('metadata');
      const digest = await Promise.race([verifyCatalog(catalog), timeout]);
      if (insights.catalog_digest !== digest) throw new Error('revision');
      if (disposed) return;
      const results = overview?.schema === 'arena.results-overview/1' ? overview : null;
      model = buildResearchMap({catalog,insights,participants,overview:results}); positions = layoutResearchMap(model);
      const selectDomain = $('map-domain'); selectDomain.replaceChildren(); $('map-legend').replaceChildren();
      const all = doc.createElement('option'); all.value='all'; all.textContent='All directions'; selectDomain.append(all);
      for (const item of model.domains) {
        const option=doc.createElement('option'); option.value=item.domainId; option.textContent=item.label; selectDomain.append(option);
        const control=button('',()=>setDomain(domain === item.domainId ? 'all' : item.domainId));
        control.dataset.domain=item.domainId; control.setAttribute('aria-pressed','false');
        const dot=doc.createElement('i'); dot.style.background=DOMAIN_STYLE[item.domainId]?.color || '#a4a9b0';
        control.append(dot,doc.createTextNode(DOMAIN_STYLE[item.domainId]?.short || item.label)); $('map-legend').append(control);
      }
      if (!model.domains.some(item=>item.domainId === domain)) domain='all'; selectDomain.value=domain;
      draw(); svg.removeAttribute('hidden'); $('map-loading').hidden=true; $('map-caption').hidden=false;
      root.dataset.state=results ? 'ready' : 'partial';
      $('map-status').textContent=results ? publicationLabel(model.summary.publishedAt) : 'Catalog visible · results unavailable';
      select(selectedId);
    } catch {
      if (disposed) return;
      root.dataset.state='error';
      $('map-status').textContent=model ? 'Update unavailable · previous map retained' : 'Map unavailable · retry to reconnect';
      if (!model) {
        $('map-loading').replaceChildren();
        const message=doc.createElement('p'); message.textContent='The research map could not be loaded.';
        $('map-loading').append(message,button('Retry loading', refresh));
        $('map-counts').textContent='The catalog and its research taxonomy must load together.';
      }
    } finally {
      win.clearTimeout(timer); pending=null;
      if (!disposed) {root.setAttribute('aria-busy','false'); $('map-refresh').disabled=false;}
    }
  }
  on($('map-refresh'),'click',refresh);
  on($('map-domain'),'change',()=>{if (model) setDomain($('map-domain').value);});
  on($('map-search'),'input',()=>{if (model) search();});
  on($('map-search'),'keydown',event=>{if (event.key === 'Escape') { $('map-search').value=''; if(model)search(); }});
  on($('map-zoom-in'),'click',()=>changeZoom(zoom*1.25));
  on($('map-zoom-out'),'click',()=>changeZoom(zoom/1.25)); on($('map-fit'),'click',fit);
  for (const control of doc.querySelectorAll('[data-map-mode]')) on(control,'click',()=>{
    mode=control.dataset.mapMode;
    for (const other of doc.querySelectorAll('[data-map-mode]')) other.setAttribute('aria-pressed',String(other===control));
    selectedId=null;
    if(model)select(null);
  });
  on(svg,'click',event=>{if(drag?.moved)return; const id=event.target.closest('[data-node-id]')?.dataset.nodeId;if(id)select(id);});
  on(svg,'keydown',event=>{
    if(['Enter',' '].includes(event.key)) {const id=event.target.closest('[data-node-id]')?.dataset.nodeId;if(id){event.preventDefault();select(id);}}
    if(event.key==='Escape')select(null);
  });
  on(svg,'pointerdown',event=>{
    if(event.button!==0)return;
    drag={x:event.clientX,y:event.clientY,offsetX,offsetY,moved:false};
  });
  on(svg,'pointermove',event=>{
    const node=event.target.closest('[data-node-id]'), tooltip=$('map-tooltip');
    if(drag && event.buttons) {
      const rect=svg.getBoundingClientRect(),scale=Math.min(rect.width/1100,rect.height/800)||1;
      const dx=(event.clientX-drag.x)/scale,dy=(event.clientY-drag.y)/scale;
      drag.moved ||= Math.hypot(dx,dy)>4;
      if(drag.moved)svg.setPointerCapture?.(event.pointerId);
      offsetX=Math.max(-2500,Math.min(1500,drag.offsetX+dx)); offsetY=Math.max(-1800,Math.min(1100,drag.offsetY+dy));
      transform();svg.classList.add('is-dragging');tooltip.hidden=true;return;
    }
    if(node){const box=$('map-viewport').getBoundingClientRect();tooltip.textContent=positions.get(node.dataset.nodeId)?.label || '';tooltip.style.left=`${Math.min(Math.max(8,event.clientX-box.left+12),Math.max(8,box.width-265))}px`;tooltip.style.top=`${Math.max(8,event.clientY-box.top-42)}px`;tooltip.hidden=false;}else tooltip.hidden=true;
  });
  on(svg,'pointerup',()=>{svg.classList.remove('is-dragging');});
  on(svg,'pointercancel',()=>{drag=null;svg.classList.remove('is-dragging');});
  on(svg,'pointerleave',()=>{$('map-tooltip').hidden=true;});
  on(svg,'wheel',event=>{if(event.ctrlKey||event.metaKey){event.preventDefault();changeZoom(zoom*(event.deltaY<0?1.12:1/1.12));}}, {passive:false});
  refresh();
  return {refresh,select,destroy(){disposed=true;pending?.abort();listeners.forEach(remove=>remove());}};
}

if (typeof document !== 'undefined' && document.body?.dataset.researchMap === 'true') initResearchMap();
