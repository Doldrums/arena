import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {buildResearchMap} from '../../web/research-map-model.js';

const snapshot = overrides => ({schema:'arena.results-overview/1',generated_at:20,source_generated_at:10,
  summary:{runs:2},truncated:false,cohorts:[],native_results:[],research:{total:0,runs:[]},...overrides});
const fixture = () => ({
  catalog:{tasks:[{id:'heat',name:'Heat equation',description:'A physical model.',paper_ids:['paper-a'],executable:true,protocol:'recreated',runtime_readiness:'not_verified'},
    {id:'packing',name:'Packing',paper_ids:['paper-b'],executable:false}]},
  insights:{domains:[{id:'physics',label:'Physics',description:'Physical systems.',why_it_matters:'Understand behavior.'},
    {id:'mathematics',label:'Mathematics'}],task_annotations:{heat:{domain_id:'physics'},packing:{domain_id:'mathematics'}}},
  participants:{participants:[{id:'sciel',name:'SCiEL',papers:[{id:'paper-a',title:'Paper A',url:'https://example.com/a'}]},
    {id:'baseline',name:'Baseline',papers:[{id:'paper-b'}],native_adapters:[{engine:'baseline-v2'}]}]},
  overview:snapshot(),
});
const cohort = (points, extra={}) => ({cohort:'a'.repeat(64),task_id:'heat',metric:'error',direction:'minimize',points,...extra});
const point = extra => ({system:'sciel-release',model:'model-a',state:'completed',seed_score:10,best_score:8,...extra});
const research = extra => ({task_id:'oe/circle_packing',task_name:'Native circle packing',protocol:'b'.repeat(64),
  metric:'sum_radii',direction:'maximize',units:'length',models:['model-a'],state:'paused',measurement_status:'measured',seed_score:1,best_score:2,...extra});
const activity = extra => ({schema:'sciel-self-improvement/1',scope:'recorded_run',coverage:'complete',
  cells_created:1,cell_revisions:2,tools_registered:1,tools_executed:1,tool_executions:3,shared_observation_deliveries:4,...extra});
const find = (graph,kind,label) => graph.nodes.find(node=>node.kind===kind && node.label===label);

test('exact taxonomy partition and exact paper references do not imply execution',()=>{
  const data=fixture();data.participants.participants.push({id:'paper-a',name:'Coincidental ID',papers:[]});
  const graph=buildResearchMap(data),heat=find(graph,'task','Heat equation'),sciel=find(graph,'participant','SCiEL');
  assert.equal(heat.domainId,'physics');assert.equal(heat.runtimeReadiness,'not_verified');
  assert.equal(graph.links.filter(e=>e.kind==='domain').length,2);
  const edge=graph.links.find(e=>e.source===heat.id && e.target===sciel.id);
  assert.equal(edge.kind,'literature');assert.deepEqual(edge.paperIds,['paper-a']);
  assert.equal(graph.links.filter(e=>e.kind==='measured').length,0);
  assert.equal(sciel.counts.literatureTasks,1);assert.equal(sciel.counts.integrationRuns,0);
  assert.equal(find(graph,'participant','Coincidental ID').counts.literatureTasks,0);
  assert.equal(find(graph,'domain','Physics').why_it_matters,'Understand behavior.');
  assert.equal(sciel.papers[0].url,'https://example.com/a');
});

test('canonical evidence uses exact task IDs and explicit system identities only',()=>{
  const data=fixture();data.overview.cohorts=[cohort([point(),point({system:'baseline-v2'})]),
    cohort([point()],{task_id:'heat-copy'}),cohort([point({system:'sciel-made-up'})])];
  const graph=buildResearchMap(data),heat=find(graph,'task','Heat equation');
  assert.equal(heat.counts.integrationRuns,3);assert.equal(graph.summary.unmatchedCanonical,1);
  assert.equal(find(graph,'participant','SCiEL').counts.integrationRuns,1);
  assert.equal(find(graph,'participant','Baseline').counts.integrationRuns,1);
  assert.equal(find(graph,'participant','sciel-made-up').source,'published_system');
  assert.equal(graph.nodes.some(n=>n.taskId==='heat-copy'),false);
});

test('ambiguous adapter registry never picks an arbitrary participant',()=>{
  const data=fixture();data.participants.participants.push({id:'other',name:'Other',native_adapters:[{engine:'baseline-v2'}]});
  data.overview.cohorts=[cohort([point({system:'baseline-v2'})])];
  const graph=buildResearchMap(data);
  assert.equal(find(graph,'participant','baseline-v2').source,'published_system');
  assert.equal(find(graph,'participant','Baseline').counts.integrationRuns,0);
});

test('system run progress includes failed or queued runs without inventing task edges',()=>{
  const data=fixture();data.overview.systems=[{system:'sciel-release',runs:4,completed:1,active:2,failed:1,cancelled:0,other:0},
    {system:'unknown-system',runs:1,completed:0,active:0,failed:1,cancelled:0,other:0}];
  const graph=buildResearchMap(data),node=find(graph,'participant','SCiEL');
  assert.equal(node.integrationSummary.runs,4);assert.equal(node.integrationSummary.active,2);
  assert.equal(node.counts.integrationRuns,0);assert.equal(graph.links.some(e=>e.kind==='measured'),false);
  assert.equal(find(graph,'participant','unknown-system').integrationSummary.failed,1);
});

test('different evaluator cohorts stay separate, zero is measured, missing is not zero',()=>{
  const data=fixture();data.overview.cohorts=[cohort([point({seed_score:1,best_score:0}),point({best_score:null,state:'failed'})]),
    cohort([point({seed_score:1,best_score:5})],{cohort:'c'.repeat(64),direction:'maximize'})];
  const node=find(buildResearchMap(data),'task','Heat equation');
  assert.equal(node.counts.measured,2);assert.equal(node.counts.improved,2);assert.equal(node.counts.failed,1);
  assert.equal(node.measurements.length,2);assert.equal(node.measurements[0].bestMin,0);
  assert.equal('totalScore' in node,false);
});

test('native research remains separate from catalog and integration with protocol-specific nodes',()=>{
  const data=fixture();data.catalog.tasks.push({id:'oe/circle_packing',name:'Coincidental catalog name',paper_ids:[]});
  data.overview=snapshot({summary:{runs:196},research:{total:3,source_generated_at:12,runs:[research(),research(),research({protocol:'c'.repeat(64)})]}});
  const graph=buildResearchMap(data),observed=graph.nodes.filter(n=>n.source==='native_research');
  assert.equal(observed.length,2);assert.equal(observed.reduce((sum,n)=>sum+n.counts.researchRuns,0),3);
  assert.ok(observed.every(n=>n.domainId==='mathematics' && n.catalogEquivalent===false));
  assert.equal(find(graph,'task','Coincidental catalog name').counts.researchRuns,0);
  assert.equal(graph.summary.integrationRuns,196);assert.equal(graph.summary.researchRuns,3);
  assert.equal(graph.summary.researchSourceGeneratedAt,12);
  assert.ok(observed.every(n=>n.counts.completed===0 && n.counts.unknown>0));
  assert.equal('runId' in observed[0],false);
});

test('recorded RSI counts preserve coverage and do not count missing evidence as zero',()=>{
  const data=fixture();data.overview.research={total:3,runs:[research({self_improvement:activity()}),
    research({self_improvement:activity({coverage:'partial',tool_executions:null,tools_executed:null})}),research()]};
  const graph=buildResearchMap(data),rsi=graph.summary.selfImprovement;
  assert.equal(rsi.coverage,'partial');assert.equal(rsi.totalRuns,3);assert.equal(rsi.recordedRuns,2);
  assert.equal(rsi.completeRuns,1);assert.equal(rsi.partialRuns,1);assert.equal(rsi.counts.cells_created,2);
  assert.equal(rsi.counts.tool_executions,3);
  assert.deepEqual(find(graph,'participant','SCiEL').selfImprovement,rsi);
  assert.match(rsi.interpretation,/not unique inventions/);
  const empty=buildResearchMap({overview:snapshot({research:{total:1,runs:[research()]}})}).summary.selfImprovement;
  assert.equal(empty.coverage,'not_recorded');assert.equal(empty.counts.cells_created,null);
});

test('invalid activity, booleans and impossible invocation counts are excluded',()=>{
  const data=fixture();data.overview.research={total:3,runs:[research({self_improvement:activity({cells_created:true})}),
    research({self_improvement:activity({tools_executed:2})}),research({self_improvement:activity({coverage:'not_recorded'})})]};
  const rsi=buildResearchMap(data).summary.selfImprovement;
  assert.equal(rsi.recordedRuns,0);assert.equal(rsi.counts.tools_registered,null);
});

test('native results get explicit display categories without canonical equivalence',()=>{
  const data=fixture();data.overview.native_results=[point({system:'baseline-v2',task_id:'oscillation_1',task_name:'Oscillation',metric:'negative_mse',direction:'maximize'}),
    point({system:'baseline-v2',task_id:'invented-physics-prefix',task_name:'Unknown native task',metric:'score',direction:'maximize'})];
  const graph=buildResearchMap(data),node=find(graph,'research','Oscillation');
  assert.equal(node.domainId,'physics');assert.equal(node.catalogEquivalent,false);
  assert.equal(node.protocolIdentity,'system_scoped_not_canonical');assert.equal(node.counts.nativeOutcomes,1);
  assert.equal(find(graph,'research','Unknown native task').domainId,'unknown');
  assert.equal(node.counts.integrationRuns,0);
});

test('paired native objectives remain measured without inventing a scalar score',()=>{
  const data=fixture();data.overview.native_results=[{system:'meoh',task_id:'online-bin-packing',task_name:'Online packing',metric:'population',direction:null,
    state:'completed',seed_score:null,best_score:null,objectives:[{metric:'quality',direction:'maximize'},{metric:'time',direction:'minimize'}],
    population_objectives:[{quality:2,time:5},{quality:1,time:3}]}];
  const node=find(buildResearchMap(data),'research','Online packing');
  assert.equal(node.counts.measured,1);assert.equal(node.counts.improved,0);
  assert.equal(node.measurements[0].bestMax,null);assert.equal(node.measurements[0].objectives.length,2);
});

test('deterministic IDs and complete output survive reordered inputs without mutation',()=>{
  const data=fixture();data.overview.research={total:2,runs:[research(),research({models:['model-b'],best_score:3})]};
  data.overview.cohorts=[cohort([point(),point({system:'baseline-v2'})])];
  const before=JSON.stringify(data),a=buildResearchMap(data);
  assert.equal(JSON.stringify(data),before);
  const reversed=structuredClone(data);reversed.catalog.tasks.reverse();reversed.participants.participants.reverse();
  reversed.insights.domains.reverse();reversed.overview.research.runs.reverse();reversed.overview.cohorts[0].points.reverse();
  assert.deepEqual(buildResearchMap(reversed),a);
  assert.equal(new Set(a.nodes.map(n=>n.id)).size,a.nodes.length);
  const ids=new Set(a.nodes.map(n=>n.id));assert.ok(a.links.every(e=>ids.has(e.source)&&ids.has(e.target)));
});

test('missing data stays unavailable and inspector URLs reject active or credentialed schemes',()=>{
  const empty=buildResearchMap();assert.equal(empty.nodes.length,0);assert.equal(empty.summary.integrationRuns,null);
  assert.deepEqual(empty.summary.availability,{catalog:false,insights:false,participants:false,results:false});
  const data=fixture();data.participants.participants[0].papers=[{id:'a',title:'<script>text</script>',url:'javascript:alert(1)'},
    {id:'b',url:'https://user:password@example.com/'},{id:'c',url:'https://example.com/paper'}];
  const papers=find(buildResearchMap(data),'participant','SCiEL').papers;
  assert.equal(papers[0].title,'<script>text</script>');assert.equal(papers[0].url,null);assert.equal(papers[1].url,null);
  assert.equal(papers[2].url,'https://example.com/paper');
});

test('actual public registry joins all 1163 tasks and keeps integration and research collections separate',async()=>{
  const read=async name=>JSON.parse(await readFile(new URL(`../../registry/${name}.json`,import.meta.url),'utf8'));
  const [catalog,insights,participants,overview]=await Promise.all(['catalog','insights','participants','results-overview'].map(read));
  const graph=buildResearchMap({catalog,insights,participants,overview});
  assert.equal(graph.summary.catalogTasks,catalog.tasks.length);assert.equal(graph.summary.catalogTasks,1163);
  assert.equal(graph.nodes.filter(n=>n.kind==='task').length,1163);
  assert.equal(graph.domains.reduce((sum,d)=>sum+d.counts.catalogTasks,0),1163);
  assert.equal(graph.summary.participants,participants.participants.length);
  assert.equal(graph.nodes.filter(n=>n.source==='native_research').reduce((sum,n)=>sum+n.counts.researchRuns,0),overview.research.runs.length);
  assert.equal(graph.nodes.filter(n=>n.source==='native_result').reduce((sum,n)=>sum+n.counts.nativeOutcomes,0),overview.native_results.length);
  assert.equal(graph.nodes.filter(n=>n.kind==='task').reduce((sum,n)=>sum+n.counts.integrationRuns,0),overview.cohorts.reduce((sum,c)=>sum+c.points.length,0));
  const cantera=graph.nodes.find(n=>n.taskId==='science-materials-cantera-mechanism-reduction');
  assert.equal(cantera.domainId,'chemistry-materials');assert.equal(cantera.counts.integrationRuns,0);
  const ids=new Set(graph.nodes.map(n=>n.id));assert.ok(graph.links.every(e=>ids.has(e.source)&&ids.has(e.target)));
});
