// Public UI behavior only: no observer, credentials, control writes or research execution.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {JSDOM} from 'jsdom';
import {initResearchMap} from '../../web/research-map.js';
import {canonicalJSON} from '../../web/arena-model.js';

const read = name => readFileSync(new URL(`../../${name}`,import.meta.url),'utf8');
const html = read('web/results.html');
const clone = value => structuredClone(value);
const digest = catalog => createHash('sha256').update(canonicalJSON(catalog)).digest('hex');
const flush = async () => { for(let i=0;i<8;i++) await new Promise(resolve=>setImmediate(resolve)); };
const settle = async t => {
  if (t.root.getAttribute('aria-busy')==='true') await new Promise((resolve,reject)=>{
    const observer=new t.w.MutationObserver(()=>{
      if(t.root.getAttribute('aria-busy')!=='true'){clearTimeout(timer);observer.disconnect();resolve();}
    });
    const timer=setTimeout(()=>{observer.disconnect();reject(new Error('map did not finish loading'));},3000);
    observer.observe(t.root,{attributes:true,attributeFilter:['aria-busy']});
  });
  await flush();
};
const response = value => ({ok:true,json:async()=>clone(value)});
const activity = extra => ({schema:'sciel-self-improvement/1',scope:'recorded_run',coverage:'complete',
  cells_created:2,cell_revisions:3,tools_registered:1,tools_executed:1,tool_executions:4,shared_observation_deliveries:5,...extra});

function fixture() {
  const catalog={schema:'arena.catalog/1',tasks:[
    {id:'heat',name:'Heat equation',description:'Recover a physical heat model.',paper_ids:['paper-a'],executable:true,runtime_readiness:'not_verified'},
    {id:'cold',name:'Cold transport',paper_ids:['paper-a'],executable:false},
    {id:'packing',name:'Packing construction',paper_ids:['paper-b'],executable:true},
  ]};
  const insights={catalog_digest:digest(catalog),domains:[
    {id:'physics',label:'Physics',description:'Physical systems.',why_it_matters:'Explain heat transport.'},
    {id:'mathematics',label:'Mathematics'}],task_annotations:{heat:{domain_id:'physics'},cold:{domain_id:'physics'},packing:{domain_id:'mathematics'}}};
  const participants={participants:[
    {id:'sciel',name:'SCiEL',description:'Research cells and program search.',attribution:{display:'CPIL · MBZUAI'},papers:[{id:'paper-a',title:'Research paper',url:'https://example.com/paper'}]},
    {id:'baseline',name:'Baseline Work',registration_status:'literature',papers:[{id:'paper-b'}]},
  ]};
  const native={task_id:'oe/circle_packing',task_name:'Native circle experiment',protocol:'b'.repeat(64),metric:'sum_radii',direction:'maximize',
    units:'unit_square',models:['model-a'],state:'paused',measurement_status:'measured',seed_score:1,best_score:2};
  const overview={schema:'arena.results-overview/1',generated_at:1790007660,source_generated_at:1790007600,truncated:false,
    summary:{runs:2},systems:[{system:'sciel-release',runs:1,completed:1,active:0,failed:0,cancelled:0,other:0},
      {system:'baseline',runs:1,completed:0,active:0,failed:1,cancelled:0,other:0}],
    cohorts:[{cohort:'a'.repeat(64),task_id:'heat',metric:'error',direction:'minimize',
      points:[{system:'sciel-release',model:'model-a',state:'completed',seed_score:1,best_score:.25}]},
      {cohort:'c'.repeat(64),task_id:'packing',metric:'score',direction:'maximize',
        points:[{system:'baseline',model:'model-b',state:'failed',seed_score:0,best_score:null}]}],native_results:[],
    research:{total:2,source_generated_at:1790007300,runs:[{...native,self_improvement:activity()},
      {...native,self_improvement:activity({coverage:'partial',cells_created:1,tools_registered:null,tools_executed:null,tool_executions:null})}]}};
  return {catalog,insights,participants,'results-overview':overview};
}

function mount({data=fixture(),fetcher,verifyCatalog,timeoutMs=1000}={}) {
  const dom=new JSDOM(html,{url:'https://arena.test/results',pretendToBeVisual:true});
  const w=dom.window,doc=w.document,calls=[];
  w.sessionStorage.setItem('arena-control-key','not-for-public-map');
  const app=initResearchMap({doc,timeoutMs,...(verifyCatalog?{verifyCatalog}:{}),fetcher:async(path,options)=>{
    calls.push({path,options});
    return fetcher ? fetcher(path,options,calls.length) : response(data[path.slice(5)]);
  }});
  const node = label => [...doc.querySelectorAll('.map-node')].find(n=>n.querySelector('title')?.textContent===label);
  const click = element => {assert.ok(element,'expected a clickable element');element.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));};
  const change = (id,value,type='change') => {const n=doc.getElementById(id);n.value=value;n.dispatchEvent(new w.Event(type,{bubbles:true}));};
  return {dom,w,doc,calls,app,node,click,change,root:doc.getElementById('research-map'),
    close(){app.destroy();w.close();}};
}
const stat = (root,label) => [...root.querySelectorAll('dt')].find(n=>n.textContent===label)?.nextElementSibling?.textContent;
const visible = t => [...t.doc.querySelectorAll('.map-node')].filter(n=>n.style.display!=='none').map(n=>n.querySelector('title').textContent).sort();

test('initial loading has no fabricated counters; exactly four credential-free public GETs become a visible map',async()=>{
  const data=fixture(),waiters=[];
  const t=mount({fetcher:(path)=>new Promise(resolve=>waiters.push(()=>resolve(response(data[path.slice(5)]))))});
  try {
    assert.equal(t.root.getAttribute('aria-busy'),'true');
    assert.equal(t.doc.querySelectorAll('.map-node').length,0);
    assert.equal(t.doc.querySelectorAll('.map-summary-numbers strong').length,0);
    assert.match(t.doc.getElementById('map-status').textContent,/Loading/);
    await t.app.refresh();assert.equal(t.calls.length,4,'concurrent refresh is coalesced');
    waiters.forEach(done=>done());await settle(t);
    assert.equal(t.root.dataset.state,'ready');assert.equal(t.root.getAttribute('aria-busy'),'false');
    assert.equal(t.doc.getElementById('map-loading').hidden,true);
    assert.equal(t.doc.getElementById('map-canvas').hasAttribute('hidden'),false,'SVG needs attribute removal, not an expando hidden property');
    assert.deepEqual(t.calls.map(c=>c.path).sort(),['/api/catalog','/api/insights','/api/participants','/api/results-overview']);
    for(const {options} of t.calls){assert.ok(!options.method||options.method==='GET');assert.equal(options.headers,undefined);assert.equal(options.redirect,'error');assert.equal(options.cache,'no-store');}
    assert.ok(t.calls.every(c=>!c.path.includes('control')&&!c.path.includes('/runs')));
    assert.match(t.doc.getElementById('map-counts').textContent,/3 catalog tasks/);
    assert.match(t.doc.getElementById('map-status').textContent,/Published/);
    assert.equal(stat(t.doc.getElementById('map-inspector'),'Integration runs'),'2');
  } finally {t.close();}
});

test('actual catalog digest and real registry render every task and retain separate published collections',async()=>{
  const data=Object.fromEntries(['catalog','insights','participants','results-overview'].map(name=>[name,JSON.parse(read(`registry/${name}.json`))]));
  const t=mount({data});
  try {await settle(t);
    assert.equal(t.root.dataset.state,'ready');assert.equal(t.doc.querySelectorAll('.map-node.task').length,959);
    const inspector=t.doc.getElementById('map-inspector');
    assert.equal(stat(inspector,'Integration runs'),String(data['results-overview'].summary.runs));
    assert.equal(stat(inspector,'Research observations'),String(data['results-overview'].research.total));
    assert.match(inspector.textContent,/Separate published collections/);
    assert.equal(t.doc.querySelectorAll('#map-legend button').length,data.insights.domains.length);
    assert.ok(t.doc.querySelector('a[href="/experiments/results"]'));
  } finally {t.close();}
});

test('unavailable overview still shows catalog with explicit missing results rather than zero',async()=>{
  const data=fixture(),t=mount({fetcher:path=>path==='/api/results-overview'?{ok:false,status:503}:response(data[path.slice(5)])});
  try {await settle(t);assert.equal(t.root.dataset.state,'partial');
    assert.equal(t.doc.querySelectorAll('.map-node.task').length,3);
    assert.match(t.doc.getElementById('map-status').textContent,/Catalog visible · results unavailable/);
    const inspector=t.doc.getElementById('map-inspector');
    assert.equal(stat(inspector,'Integration runs'),'Not published');assert.equal(stat(inspector,'Research observations'),'Not published');
    assert.equal(t.doc.querySelectorAll('.map-edge.measured').length,0);
    t.click(t.doc.querySelector('[data-map-mode="recorded"]'));
    assert.equal(t.doc.getElementById('map-empty').hidden,false);
  } finally {t.close();}
});

test('taxonomy mismatch refuses a mixed snapshot; retry with matching metadata recovers',async()=>{
  const data=fixture();let mismatch=true;
  const t=mount({verifyCatalog:async value=>digest(value),fetcher:path=>response(path==='/api/insights'&&mismatch?{...data.insights,catalog_digest:'wrong'}:data[path.slice(5)])});
  try {await settle(t);assert.equal(t.root.dataset.state,'error');assert.equal(t.doc.querySelectorAll('.map-node').length,0);
    assert.match(t.doc.getElementById('map-counts').textContent,/catalog and its research taxonomy must load together/);
    mismatch=false;t.click(t.doc.querySelector('#map-loading button'));await settle(t);
    assert.equal(t.root.dataset.state,'ready');assert.equal(t.calls.length,8);
  } finally {t.close();}
});

test('refresh errors retain the last verified graph, selection and published values',async()=>{
  const data=fixture();let fail=false;
  const t=mount({fetcher:path=>response(path==='/api/insights'&&fail?{...data.insights,catalog_digest:'mismatch'}:data[path.slice(5)])});
  try {await settle(t);t.click(t.node('Heat equation'));
    const before=t.doc.getElementById('map-canvas').innerHTML;
    fail=true;await t.app.refresh();
    assert.equal(t.root.dataset.state,'error');assert.match(t.doc.getElementById('map-status').textContent,/previous map retained/);
    assert.equal(t.doc.getElementById('map-canvas').innerHTML,before);
    assert.equal(t.doc.querySelector('#map-inspector h2').textContent,'Heat equation');
    assert.equal(stat(t.doc.getElementById('map-inspector'),'error'),'0.25');
  } finally {t.close();}
});

test('timeout aborts pending fetches and offers retry without values or private fallback',async()=>{
  const t=mount({timeoutMs:5,fetcher:()=>new Promise(()=>{})});
  try {await new Promise(resolve=>setTimeout(resolve,20));await settle(t);
    assert.equal(t.root.dataset.state,'error');assert.equal(t.root.getAttribute('aria-busy'),'false');
    assert.ok(t.calls.every(c=>c.options.signal.aborted));assert.equal(t.calls.length,4);
    assert.ok(t.doc.querySelector('#map-loading button'));assert.equal(t.doc.querySelectorAll('.map-node').length,0);
  } finally {t.close();}
});

test('system selection exposes attribution, recorded process coverage, papers and real detail links',async()=>{
  const t=mount();try {await settle(t);t.click(t.node('SCiEL'));
    const inspector=t.doc.getElementById('map-inspector');
    assert.equal(inspector.querySelector('h2').textContent,'SCiEL');assert.match(inspector.textContent,/by CPIL · MBZUAI/);
    assert.equal(stat(inspector,'Research cells'),'3');assert.equal(stat(inspector,'Tool executions'),'4');
    assert.match(inspector.textContent,/Partial coverage.*lower bounds/);assert.match(inspector.textContent,/not unique inventions or evidence of causal improvement/);
    assert.equal(inspector.querySelector('a[href="https://example.com/paper"]').textContent,'Research paper');
    assert.ok(inspector.querySelector('a[href="/?view=participants&participant=sciel"]'));
    assert.ok(inspector.querySelector('a[href="/experiments/results"]'));
    assert.equal(t.node('SCiEL').getAttribute('aria-pressed'),'true');
    t.click(inspector.querySelector('[aria-label="Clear selection"]'));
    assert.match(inspector.textContent,/INSIDE THE ARENA/);assert.equal(t.node('SCiEL').getAttribute('aria-pressed'),'false');
  } finally {t.close();}
});

test('task inspector preserves metric direction and links; keyboard selection is accessible',async()=>{
  const t=mount();try {await settle(t);
    t.node('Heat equation').dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    const inspector=t.doc.getElementById('map-inspector');
    assert.equal(inspector.querySelector('h2').textContent,'Heat equation');assert.equal(stat(inspector,'error'),'0.25');
    assert.match(inspector.textContent,/Lower is better.*Evaluator aaaaaaaa/);
    assert.match(inspector.textContent,/Runtime readiness is verified separately/);
    assert.ok(inspector.querySelector('a[href="/?task=heat"]'));
    t.doc.getElementById('map-canvas').dispatchEvent(new t.w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    assert.match(inspector.textContent,/INSIDE THE ARENA/);
    t.click(t.node('Baseline Work'));assert.match(inspector.textContent,/citation link.*does not mean this system ran it/);
  } finally {t.close();}
});

test('directions, exact search and recorded layer filter nodes and links consistently',async()=>{
  const t=mount();try {await settle(t);
    t.change('map-domain','physics');assert.deepEqual(visible(t),['Cold transport','Heat equation','SCiEL']);
    assert.equal(t.doc.querySelector('#map-inspector h2').textContent,'Physics');
    assert.match(t.doc.getElementById('map-inspector').textContent,/Explain heat transport/);
    t.change('map-search','Heat','input');assert.deepEqual(visible(t),['Heat equation','SCiEL']);
    assert.equal(t.doc.querySelectorAll('#map-search-results button').length,1);
    t.click(t.doc.querySelector('#map-search-results button'));assert.equal(t.doc.getElementById('map-search-results').hidden,true);
    t.change('map-search','','input');t.change('map-domain','all');
    t.click(t.doc.querySelector('[data-map-mode="recorded"]'));
    assert.deepEqual(visible(t),['Heat equation','Native circle experiment','SCiEL']);
    assert.ok([...t.doc.querySelectorAll('.map-edge.literature')].every(edge=>edge.style.display==='none'));
    assert.equal(t.doc.querySelector('[data-map-mode="recorded"]').getAttribute('aria-pressed'),'true');
    t.click(t.doc.querySelector('[data-map-mode="landscape"]'));assert.ok(visible(t).includes('Packing construction'));
    t.click(t.doc.querySelector('#map-legend [data-domain="mathematics"]'));
    assert.equal(t.doc.getElementById('map-domain').value,'mathematics');
    assert.equal(t.doc.querySelector('#map-legend [data-domain="mathematics"]').getAttribute('aria-pressed'),'true');
  } finally {t.close();}
});

test('search suggestions do not offer nodes hidden by the active domain or recorded layer',async()=>{
  const t=mount();try {await settle(t);t.change('map-domain','physics');t.change('map-search','Packing','input');
    assert.equal(t.doc.getElementById('map-search-results').hidden,true);
    assert.equal(t.doc.querySelectorAll('#map-search-results button').length,0);
    assert.equal(t.doc.getElementById('map-empty').hidden,false);
    t.change('map-domain','all');t.click(t.doc.querySelector('[data-map-mode="recorded"]'));t.change('map-search','Baseline','input');
    assert.equal(t.doc.querySelectorAll('#map-search-results button').length,0);
  } finally {t.close();}
});

test('zoom is bounded, fit restores origin and destroy removes active controls',async()=>{
  const t=mount();try {await settle(t);
    for(let i=0;i<12;i++)t.click(t.doc.getElementById('map-zoom-in'));
    assert.equal(t.doc.getElementById('map-zoom-label').textContent,'300%');assert.equal(t.doc.getElementById('map-zoom-in').disabled,true);
    for(let i=0;i<20;i++)t.click(t.doc.getElementById('map-zoom-out'));
    assert.equal(t.doc.getElementById('map-zoom-label').textContent,'75%');assert.equal(t.doc.getElementById('map-zoom-out').disabled,true);
    t.click(t.doc.getElementById('map-fit'));assert.equal(t.doc.getElementById('map-zoom-label').textContent,'100%');
    assert.equal(t.doc.querySelector('#map-canvas > g').getAttribute('transform'),'translate(0 0) scale(1)');
    t.app.destroy();t.click(t.doc.getElementById('map-refresh'));t.click(t.doc.getElementById('map-zoom-in'));await settle(t);
    assert.equal(t.calls.length,4);assert.equal(t.doc.getElementById('map-zoom-label').textContent,'100%');
  } finally {t.close();}
});

test('labels remain text and unsafe publication URLs cannot become inspector links',async()=>{
  const data=fixture(),label='<img src=x onerror="alert(1)">';
  data.catalog.tasks[0].name=label;data.catalog.tasks[0].description='<script>danger()</script>';
  data.insights.catalog_digest=digest(data.catalog);
  data.participants.participants[0].papers[0].url='javascript:alert(1)';
  const t=mount({data});try {await settle(t);t.click(t.node(label));const inspector=t.doc.getElementById('map-inspector');
    assert.equal(inspector.querySelector('h2').textContent,label);assert.match(inspector.textContent,/<script>danger/);
    assert.equal(inspector.querySelectorAll('script,img').length,0);assert.equal(t.doc.querySelectorAll('#map-canvas img, #map-canvas script').length,0);
    t.click(t.node('SCiEL'));assert.equal(inspector.querySelectorAll('a[href^="javascript:"]').length,0);
  } finally {t.close();}
});

test('paired native objective records never acquire a scalar direction or invented best score',async()=>{
  const data=fixture();data['results-overview'].native_results=[{system:'meoh',task_id:'online-bin-packing',task_name:'Paired packing',metric:'native_two_objective_population',
    direction:null,seed_score:null,best_score:null,state:'completed',objectives:[{metric:'quality',direction:'maximize'},{metric:'latency',direction:'minimize'}],
    population_objectives:[{quality:2,latency:5},{quality:1,latency:3}]}];
  const t=mount({data});try {await settle(t);t.click(t.node('Paired packing'));
    const inspector=t.doc.getElementById('map-inspector');assert.doesNotMatch(inspector.textContent,/Higher is better|Lower is better/);
    assert.match(inspector.textContent,/Multiple objectives|Paired objectives/i);
    assert.doesNotMatch(inspector.textContent,/Improved on initial score0/);
  } finally {t.close();}
});

test('only measured outcomes receive measurement styling, including paired native objectives',async()=>{
  const data=fixture(),overview=data['results-overview'];
  overview.research.runs.push({...overview.research.runs[0],task_name:'Pending native experiment',protocol:'d'.repeat(64),
    state:'running',measurement_status:'unknown',seed_score:null,best_score:null,self_improvement:null});
  overview.research.total++;
  overview.native_results.push({system:'meoh',task_id:'online-bin-packing',task_name:'Measured paired population',metric:'paired_population',
    direction:null,seed_score:null,best_score:null,state:'completed',objectives:[{metric:'quality',direction:'maximize'},{metric:'latency',direction:'minimize'}],
    population_objectives:[{quality:2,latency:5},{quality:1,latency:3}]});
  const t=mount({data});try {await settle(t);
    for(const label of ['Pending native experiment','Packing construction','Baseline Work']){
      const node=t.node(label);assert.ok(node);assert.equal(node.classList.contains('has-measurement'),false,label);
      assert.equal(node.querySelector('.map-core,.map-recorded-ring'),null,label);
    }
    for(const label of ['Measured paired population','Native circle experiment','Heat equation']){
      const node=t.node(label);assert.equal(node.classList.contains('has-measurement'),true,label);
      assert.ok(node.querySelector('.map-core,.map-recorded-ring'),label);
    }
    assert.equal(t.doc.querySelectorAll('.map-edge.measured').length,3,'pending and failed-only edges must not be drawn as measurements');
    t.click(t.node('Baseline Work'));
    assert.ok(![...t.doc.querySelectorAll('#map-inspector h3')].some(n=>n.textContent==='Measured research'));
    assert.equal(stat(t.doc.getElementById('map-inspector'),'Failed'),'1','failed progress remains visible without a measurement claim');
    t.click(t.doc.querySelector('[data-map-mode="recorded"]'));
    assert.ok(!visible(t).includes('Pending native experiment'));assert.ok(visible(t).includes('Measured paired population'));
  } finally {t.close();}
});

test('landing navigation stays separate and the experiment results workspace retains its sidebar',()=>{
  const landing=new JSDOM(html),workspace=new JSDOM(read('web/experiment-results.html'));
  try {
    assert.ok(landing.window.document.querySelector('.arena-tabs a[href="/results"][aria-current="page"]'));
    assert.match(landing.window.document.body.textContent,/Follow the research behind the numbers/);
    const doc=workspace.window.document;
    assert.ok(doc.querySelector('aside.workspace-sidebar .workspace-nav'));
    for(const path of ['/experiments','/experiments/results','/experiments/queue'])assert.ok(doc.querySelector(`.workspace-nav a[href="${path}"]`));
    assert.ok(doc.querySelector('script[src="/arena-results.js"]'));assert.equal(doc.querySelector('.arena-tabs'),null);
    assert.equal(doc.querySelector('#research-map'),null);
  } finally {landing.window.close();workspace.window.close();}
});
