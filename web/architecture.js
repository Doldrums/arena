// Recorded mechanisms, grouped by the decision they affect. No policy replay.
const graphEscape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const graphIds = new Set(['scheduler','parent','operator','generation','novelty','evaluation','population','mode_policy','operator_bandit','refine','ideas','descriptor','memory','conclusion','reflection','reward','tool_library','tool_execution','research_cells','research_checks']);
const graphKinds={core:'Search step',rule:'Rule',online:'Online learning',frozen:'Frozen model',knowledge:'Research'};
const graphEdgeKinds={flow:'Program flow',control:'Controls a decision',reward:'Learning signal',knowledge:'Research feedback'};
const graphArray=value=>Array.isArray(value)?value:[];
const graphKind=value=>Object.hasOwn(graphKinds,value)?value:'core';
const graphEdgeKind=value=>Object.hasOwn(graphEdgeKinds,value)?value:'flow';

function graphData(graph) {
  const nodes=graphArray(graph?.nodes).filter(node=>node&&graphIds.has(node.id)).slice(0,20);
  const ids=new Set(nodes.map(node=>node.id));
  return {nodes,edges:graphArray(graph?.edges).filter(edge=>edge&&ids.has(edge.from)&&ids.has(edge.to)).slice(0,48)};
}

function graphTitle(node) {
  if(!node)return 'Not recorded';
  if(node.id==='mode_policy'){
    if(node.label==='Preset-weight bandit')return 'Adaptive presets';
    if(node.label==='Contextual mode bandit')return 'Mode bandit';
    if(node.label==='Static mode controller')return 'Parent selection rules';
  }
  if(node.id==='descriptor'&&node.label==='Learned descriptor')return 'Frozen embedding + PCA';
  return node.label;
}

function graphTag(node) {
  if(node.status==='unknown')return 'Not recorded';
  if(node.status==='shadow')return 'Overridden';
  if(node.kind==='online')return node.id==='descriptor'?'Adaptive niches':'Online RL';
  return node.kind==='core'?'':graphKinds[graphKind(node.kind)];
}

function graphButton(node,{title,description,variant='module'}={}) {
  if(!node)return '';
  const tag=variant==='core-action'&&node.status!=='unknown'?'':graphTag(node),kind=graphKind(node.kind);
  return '<button type="button" role="button" tabindex="0" class="architecture-node '+kind+' '+variant+(node.status==='unknown'?' unknown':'')+'" data-node="'+graphEscape(node.id)+'" data-stage="'+graphEscape(node.phase||node.id)+'" data-status-label="'+graphEscape(tag)+'" aria-pressed="false" aria-label="'+graphEscape((title||graphTitle(node))+(tag?' · '+tag:''))+'">'+
    '<span class="stage-status"'+(tag?'':' hidden')+'>'+graphEscape(tag)+'</span><span class="graph-node-label">'+graphEscape(title||graphTitle(node))+'</span>'+
    (description?'<span class="graph-node-subtitle">'+graphEscape(description)+'</span>':'')+'<span class="node-more" aria-hidden="true">↗</span></button>';
}

function graphModeCopy(node) {
  if(!node||node.status==='unknown')return 'The active parent policy was not recorded.';
  if(node.label==='Preset-weight bandit')return 'Learns the mix of parent-selection strategies.';
  if(node.label==='Contextual mode bandit')return 'Learns which parent-selection mode to use.';
  if(node.kind==='frozen')return 'A trained model guides parent choice. Its weights stay fixed.';
  return 'Uses a fixed mix of parent-selection modes, with any recorded plateau rules.';
}

export function architectureGraphHTML(graph) {
  const {nodes,edges}=graphData(graph),get=id=>nodes.find(node=>node.id===id);
  if(!nodes.length)return '<div class="graph-unavailable">Architecture was not recorded for this run.</div>';
  const mode=get('mode_policy'),operator=get('operator_bandit'),descriptor=get('descriptor');
  const learningEdges=edges.filter(edge=>edge.kind==='reward'&&edge.from==='reward');
  const learning=learningEdges.length>0,knowledge=Boolean(get('memory'));
  let html='<section class="architecture-map" aria-label="Architecture mechanism map">';
  html+='<div class="arch-profile">'+[
    ['Parent choice',mode?graphTitle(mode):get('parent')?.subtitle||'Not recorded'],
    ['Edits',operator?graphTitle(operator):get('operator')?.subtitle||'Not recorded'],
    ['Storage',descriptor?graphTitle(descriptor):get('population')?.label||'Not recorded']
  ].map(([label,value])=>'<div><span>'+graphEscape(label)+'</span><strong>'+graphEscape(value)+'</strong></div>').join('')+'</div>';
  const parallel=graph?.execution?.status==='enabled';
  html+='<div class="arch-loop-heading"><h3>'+(parallel?'Parallel wave':'One experiment')+'</h3><span>'+(parallel?graphEscape(graph.execution.workers??'Unknown')+' workers · '+graphEscape(graph.execution.feedback||'Research status unknown'):'Repeat with the updated population')+'</span></div><ol class="arch-pipeline" aria-label="Program evolution">';
  const steps=[
    {id:'select',number:1,title:'Select',node:get('parent'),description:'Choose a parent program and an edit.'},
    {id:'generate',number:2,title:'Generate',node:get('generation'),description:get('conclusion')?'Write a hypothesis and a candidate program.':'Ask the model for a candidate program.'},
    {id:'evaluate',number:3,title:'Evaluate',node:get('evaluation'),description:'Run the task. Check validity and measure the score.'},
    {id:'store',number:4,title:'Store',node:get('population'),description:'Keep useful programs for the next experiment.'}
  ];
  for(const step of steps){
    html+='<li class="arch-step" data-step="'+step.id+'"><div class="arch-step-heading"><span class="arch-step-number">'+step.number+'</span><h4>'+step.title+'</h4><span class="arch-step-arrow" aria-hidden="true">→</span></div>';
    html+='<div class="arch-step-body">'+(step.node?graphButton(step.node,{title:step.description,variant:'core-action'}):'<p class="arch-missing">Not recorded</p>');
    if(step.id==='select'){
      if(mode)html+=graphButton(mode,{description:graphModeCopy(mode)});
      if(operator)html+=graphButton(operator,{description:'Learns which edit strategy to use.'});
      const scheduling=get('scheduler'),features=graphArray(scheduling?.features);
      const schedulerTitle=features.includes('Portfolio starts')&&features.includes('Dynamic islands')?'Portfolio + dynamic islands':'Island scheduling';
      const operatorTitle=graphArray(get('operator')?.features).includes('Crossover available')?'Crossover & edit strategies':'Available edit strategies';
      html+='<div class="arch-support">'+graphButton(scheduling,{title:schedulerTitle,variant:'support'})+graphButton(get('operator'),{title:operatorTitle,variant:'support'})+'</div>';
    }else if(step.id==='generate'){
      html+='<p class="arch-model">'+graphEscape(step.node?.subtitle||'Model not recorded')+'</p>';
      if(get('ideas'))html+=graphButton(get('ideas'),{description:get('ideas').label==='Two-stage ideas'?'Strategy card → implementation.'+(graphArray(get('ideas').features).includes('Up to 1 card correction')?' Up to 1 card correction.':''):'Try a new strategy on the idea island.'});
      if(get('refine'))html+=graphButton(get('refine'),{description:'Push a strong program further after a stall.'});
      if(get('novelty'))html+=graphButton(get('novelty'),{description:'SHA256 → AST → code embedding. Check whole-run history before evaluation.'});
      if(get('research_cells'))html+=graphButton(get('research_cells'),{description:'Stagnation → a durable research question, separate from Programs.'});
      if(get('tool_library'))html+=graphButton(get('tool_library'),{description:'Retain executable versions; release follows the recorded checks.'});
      if(get('tool_execution'))html+=graphButton(get('tool_execution'),{description:'Run a version in isolation; retain exact inputs and outputs.'});
      if(get('research_checks'))html+=graphButton(get('research_checks'),{description:'Compact observations enter prepared context for ordinary G.'});
    }else if(step.id==='evaluate'){
      html+='<div class="arch-outputs"><span>Produces</span><ul><li>Valid or invalid outcome</li><li>Measured task score</li><li>Evidence for research</li></ul></div>';
    }else if(step.id==='store'){
      if(descriptor)html+=graphButton(descriptor,{description:descriptor.status==='unknown'?'Actual representation was not recorded.':descriptor.label==='VQ niches'?'Group programs into evolving niches. Embedding weights stay fixed.':descriptor.kind==='frozen'?'Use fixed embedding coordinates to preserve different solutions.':descriptor.subtitle});
      html+='<p class="arch-storage">'+graphEscape(step.node?.label||'Population storage')+'</p>';
    }
    html+='</div></li>';
  }
  html+='</ol><div class="arch-repeat"><span aria-hidden="true">↶</span> Updated population feeds the next selection</div>';
  if(learning){
    const targets=learningEdges.map(edge=>graphTitle(get(edge.to))).filter(Boolean);
    html+='<section class="arch-feedback learning-loop" data-feedback="learning"><div class="arch-feedback-heading"><span class="arch-loop-mark">RL</span><div><h3>Learn what to choose</h3><p>Results change the probabilities used in step 1.</p></div></div><div class="arch-feedback-flow">'+
      graphButton(get('reward'),{title:'Search results',description:'Record improvements become learning signals.',variant:'feedback-node'})+'<span class="arch-flow-arrow" aria-hidden="true">→</span><div class="arch-feedback-update"><strong>Update the chooser</strong><span>'+graphEscape(targets.join(' + '))+'</span></div><span class="arch-flow-arrow" aria-hidden="true">→</span><button type="button" class="arch-return" data-return-step="select"><span>Next selection</span><strong>1 · Select <span aria-hidden="true">↗</span></strong></button></div>';
    html+='<div class="arch-reward-notes">';
    if(learningEdges.some(edge=>edge.to==='mode_policy'))html+='<p><strong>Parent policy:</strong> '+graphEscape(mode?.label==='Preset-weight bandit'?'a new global record gives reward 1; otherwise 0.':'learns from improvement rewards, including zero-reward attempts.')+'</p>';
    if(learningEdges.some(edge=>edge.to==='operator_bandit'))html+='<p><strong>Edit policy:</strong> qualifying island records update its reward memory.</p>';
    html+='</div></section>';
  }else if(get('reward')){
    html+='<div class="arch-feedback no-learning">'+graphButton(get('reward'),{title:'Search feedback',description:'No active policy-update route was recorded.',variant:'feedback-node'})+'</div>';
  }
  if(knowledge){
    const delivered=edges.some(edge=>edge.from==='memory'&&edge.to==='generation');
    html+='<section class="arch-feedback knowledge-loop" data-feedback="knowledge"><div class="arch-feedback-heading"><span class="arch-loop-mark">GCR</span><div><h3>Learn what to try</h3><p>Experiments build research knowledge'+(delivered?' for the next prompt.':'; prompt injection is not active or not recorded.')+'</p></div></div><div class="arch-feedback-flow"><div class="arch-reviews">'+
      graphButton(get('conclusion'),{title:'C · Review this experiment',description:graphArray(get('conclusion')?.features).includes('Host-bound source references')?'Host-bound references'+(graphArray(get('conclusion').features).includes('Up to 1 format correction')?' · up to 1 correction.':'.'):undefined,variant:'feedback-node'})+graphButton(get('reflection'),{title:'R · Revisit past experiments',variant:'feedback-node'})+'</div><span class="arch-flow-arrow" aria-hidden="true">→</span>'+graphButton(get('memory'),{title:'Research memory',description:graphArray(get('memory').features).includes('Compact lesson memory')?'Compact decision cards · full evidence retained.':'Accepted lessons, evidence and fragments.',variant:'feedback-node'})+
      (delivered?'<span class="arch-flow-arrow" aria-hidden="true">→</span><button type="button" class="arch-return" data-return-step="generate"><span>Next prompt</span><strong>2 · Generate <span aria-hidden="true">↗</span></strong></button>':'')+'</div><p class="arch-research-note">C and R read recorded evidence. R can still learn when a conclusion is rejected.</p></section>';
  }
  html+='<div class="graph-inspector" hidden aria-live="polite"></div>';
  const inactive=graphArray(graph.inactive).slice(0,30);
  if(inactive.length)html+='<details class="graph-inactive"><summary>Disabled and overridden features <span>'+inactive.length+'</span></summary><div>'+inactive.map(item=>'<article><strong>'+graphEscape(item.label)+'</strong><span class="graph-inactive-status">'+graphEscape(item.status==='unknown'?'Not recorded':item.status==='shadow'?'Overridden / monitoring only':'Disabled')+'</span><p>'+graphEscape(item.detail)+'</p></article>').join('')+'</div></details>';
  const notes=[...graphArray(graph.summary),...graphArray(graph.notes)];
  if(notes.length)html+='<details class="graph-notes"><summary>Recorded architecture notes</summary><div>'+notes.map(note=>'<p>'+graphEscape(note)+'</p>').join('')+'</div></details>';
  return html+'</section>';
}

function graphInspector(node,nodes,edges) {
  const related=edges.filter(edge=>edge.from===node.id||edge.to===node.id),name=id=>graphTitle(nodes.find(item=>item.id===id));
  return '<div class="graph-inspector-heading"><div><span class="graph-kind-tag">'+graphEscape(graphTag(node))+'</span><h3>'+graphEscape(graphTitle(node))+'</h3></div><button type="button" class="graph-reset" aria-label="Close module details">Close ×</button></div><p class="graph-inspector-description">'+graphEscape(node.detail||node.subtitle||'No additional details recorded.')+'</p>'+
    (graphArray(node.features).length?'<ul class="graph-features">'+node.features.map(feature=>'<li>'+graphEscape(feature)+'</li>').join('')+'</ul>':'')+'<div class="graph-inspector-links">'+related.map(edge=>'<div class="graph-edge graph-connection-note related '+graphEdgeKind(edge.kind)+'" data-from="'+graphEscape(edge.from)+'" data-to="'+graphEscape(edge.to)+'"><strong>'+graphEscape(name(edge.from))+' → '+graphEscape(name(edge.to))+'</strong><p>'+graphEscape(edge.label||graphEdgeKinds[graphEdgeKind(edge.kind)])+'</p></div>').join('')+'</div>';
}

export function bindArchitectureGraph(root,graph,selectedId=null) {
  const container=root.querySelector('.architecture-map');if(!container)return;
  const {nodes,edges}=graphData(graph),inspector=container.querySelector('.graph-inspector');
  function select(id){
    const node=nodes.find(item=>item.id===id);container.dataset.selectedNode=node?.id||'';
    const adjacent=new Set(node?[node.id,...edges.filter(edge=>edge.from===id||edge.to===id).flatMap(edge=>[edge.from,edge.to])]:[]);
    container.querySelectorAll('.architecture-node').forEach(element=>{
      const selected=Boolean(node&&element.dataset.node===id);
      element.classList.toggle('selected',selected);element.classList.toggle('related',Boolean(node&&adjacent.has(element.dataset.node)));
      element.setAttribute('aria-pressed',String(selected));
    });
    inspector.hidden=!node;inspector.innerHTML=node?graphInspector(node,nodes,edges):'';
  }
  container.addEventListener('click',event=>{
    const target=event.target.closest('[data-node]');
    if(target&&container.contains(target))select(target.dataset.node);
    else if(event.target.closest('.graph-reset'))select(null);
    const back=event.target.closest('[data-return-step]');
    if(back){const step=container.querySelector('[data-step="'+back.dataset.returnStep+'"]');step?.scrollIntoView({block:'center',behavior:'smooth'});step?.querySelector('button')?.focus({preventScroll:true});}
  });
  container.addEventListener('keydown',event=>{
    const target=event.target.closest('[data-node]');
    if(target&&['Enter',' '].includes(event.key)){event.preventDefault();select(target.dataset.node);}
    if(event.key==='Escape'){event.preventDefault();select(null);}
  });
  if(selectedId&&nodes.some(node=>node.id===selectedId))select(selectedId);
}

export function updateArchitectureGraphPhase(root,runtime) {
  const current=runtime?.active===true?({generating:'generation',evaluating:'evaluation'}[runtime.stage]):null;
  root.querySelectorAll('.architecture-node').forEach(node=>{
    const phase=({generating:'generation',evaluating:'evaluation'}[node.dataset.stage])||node.dataset.stage,active=phase===current;
    node.classList.toggle('current',active);
    const status=node.querySelector('.stage-status');
    if(status){status.textContent=active?'Running now':node.dataset.statusLabel;status.hidden=!active&&!node.dataset.statusLabel;}
    const step=node.closest('.arch-step');if(node.classList.contains('core-action')&&step)step.classList.toggle('current',active);
  });
}
