// Catalog evidence is rendered as recorded. No scores or scientific rankings are inferred here.
const sessions = new WeakMap();
const finite = value => typeof value === 'number' && Number.isFinite(value);
const number = value => finite(value) ? value.toLocaleString('en-US') : '—';
const percent = (total, denominator) => finite(total) && finite(denominator) && denominator > 0 ? total / denominator * 100 : null;
const percentText = value => finite(value) ? `${value.toFixed(1)}%` : 'Not recorded';
const safeURL = value => {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; }
  catch { return null; }
};
const text = value => value == null ? 'Not recorded' : typeof value === 'object' ? JSON.stringify(value) : String(value);

export function referenceMatches(record, filter) {
  const anchors = Array.isArray(record?.anchors) ? record.anchors : [];
  if (filter === 'published') return anchors.some(anchor => anchor.kind === 'published_reference');
  if (filter === 'baseline') return anchors.some(anchor => anchor.kind === 'recorded_seed_baseline');
  if (filter === 'numeric') return anchors.length > 0;
  if (filter === 'missing') return anchors.length === 0;
  return true;
}

function ui(root) {
  const doc = root.ownerDocument;
  const make = (tag, cls, value) => { const node = doc.createElement(tag); if (cls) node.className = cls; if (value != null) node.textContent = text(value); return node; };
  const link = (label, href, internal = false) => {
    const node = make('a', 'inline-link', label); node.href = href;
    if (internal) node.dataset.arenaRoute = 'true'; else { node.target = '_blank'; node.rel = 'noopener noreferrer'; }
    return node;
  };
  const panel = (title, description, cls = '') => {
    const node = make('section', `panel insights-panel ${cls}`); node.append(make('h3', '', title));
    if (description) node.append(make('p', 'insights-panel-description', description)); return node;
  };
  return {make, link, panel};
}

function unavailable(root, title, message, retry) {
  const {make} = ui(root), node = make('div', 'insights-unavailable');
  node.append(make('strong', '', title), make('p', '', message));
  if (retry) { const button = make('button', '', 'Retry overview'); button.type = 'button'; button.addEventListener('click', retry); node.append(button); }
  return node;
}

function distribution(root, items, {title, kind, selected, total, onFilter, expanded, onExpand}) {
  const {make, panel} = ui(root);
  const node = panel(title, `Share of all ${number(total)} task packages. Select a bar to filter the catalog.`, kind === 'type' ? 'insights-types' : '');
  const legend = make('div', 'insights-chart-legend');
  legend.append(make('span', 'insights-legend-executable', 'Executable definition'), make('span', 'insights-legend-unsupported', 'Evaluator to be added'));
  node.append(legend);
  const list = make('div', 'insights-bars'); list.setAttribute('role', 'group'); list.setAttribute('aria-label', `${title}, filter task catalog`);
  const sorted = [...items].sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
  const limit = kind === 'domain' ? items.length : 10;
  for (const item of sorted.slice(0, expanded ? undefined : limit)) {
    const share = finite(item.percentage) ? item.percentage : percent(item.total, total), button = make('button', 'insights-bar'); button.type = 'button';
    button.dataset.insightsAction = `${kind}:${item.id}`; button.dataset.filterKind = kind; button.dataset.filterValue = item.id;
    button.setAttribute('aria-pressed', String(selected === item.id));
    button.setAttribute('aria-label', `${item.label}: ${number(item.total)} tasks, ${percentText(share)} of all tasks; ${number(item.executable)} executable definitions, ${number(item.unsupported)} awaiting an evaluator. Filter catalog.`);
    button.title = item.description || item.label;
    const track = make('span', 'insights-bar-track'); track.setAttribute('aria-hidden', 'true');
    const fill = make('span', 'insights-bar-fill'); fill.style.width = `${Math.max(0, Math.min(100, share || 0))}%`;
    const executable = make('span', 'insights-bar-executable'), unsupported = make('span', 'insights-bar-unsupported');
    executable.style.width = `${Math.max(0, Math.min(100, percent(item.executable, item.total) || 0))}%`;
    unsupported.style.width = `${Math.max(0, Math.min(100, percent(item.unsupported, item.total) || 0))}%`;
    fill.append(executable, unsupported); track.append(fill);
    const value = make('span', 'insights-bar-value', number(item.total)); value.append(make('small', '', percentText(share)));
    button.append(make('span', 'insights-bar-label', item.label), track, value);
    button.addEventListener('click', () => onFilter(kind, selected === item.id ? null : item.id)); list.append(button);
  }
  node.append(list);
  if (items.length > limit) {
    const more = make('button', 'insights-list-toggle', expanded ? 'Show fewer' : `Show all ${items.length} ${kind === 'domain' ? 'domains' : 'task types'}`);
    more.type = 'button'; more.dataset.insightsAction = `expand:${kind}`; more.setAttribute('aria-expanded', String(expanded)); more.addEventListener('click', onExpand); node.append(more);
  }
  node.append(make('p', 'insights-chart-note', kind === 'domain' ? 'Domains describe scientific context. One package has one primary domain.' : 'Task types describe what the system must produce or optimize. They are a separate classification.'));
  return node;
}

function coverage(root, insights, catalog) {
  const {make, panel} = ui(root), total = insights.denominator.task_count;
  const node = panel('Evaluator & evidence coverage', 'Source protocol labels describe the available definitions. They are not Arena runtime verification.');
  const counts = catalog.tasks.reduce((all, task) => { all[task.protocol] = (all[task.protocol] || 0) + 1; return all; }, {});
  const protocols = [['original', 'Original', '#789b84'], ['recreated_verified', 'Recreated · verified at source', '#e1b52a'], ['recreated', 'Recreated', '#93a9c0'], ['unsupported', 'Evaluator to be added', '#d6dbe2']];
  const track = make('div', 'insights-coverage-track'); track.setAttribute('role', 'img');
  track.setAttribute('aria-label', protocols.map(([id, label]) => `${label}: ${number(counts[id] || 0)}`).join('; '));
  const list = make('div', 'insights-coverage-list');
  for (const [id, label, color] of protocols) {
    const count = counts[id] || 0, share = percent(count, total);
    const segment = make('span', 'insights-coverage-segment'); segment.style.flexBasis = `${share || 0}%`; segment.style.background = color; segment.style.flexShrink = '1'; track.append(segment);
    const row = make('div', 'insights-coverage-item'), labelNode = make('span'), swatch = make('i', 'insights-swatch'); swatch.style.background = color;
    labelNode.append(swatch, make('span', '', label)); const value = make('strong', '', `${number(count)} `); value.append(make('small', '', percentText(share)));
    row.append(labelNode, value); list.append(row);
  }
  node.append(track, list);
  const facts = make('dl', 'insights-small-facts');
  const coverageRows = Array.isArray(insights.coverage) ? insights.coverage : [];
  for (const [id, label] of [['executable', 'Executable definitions'], ['recorded_contract', 'Recorded input/output'], ['runtime_verified', 'Arena runtime verified']]) {
    const item = coverageRows.find(row => row.id === id), box = make('div');
    const value = make('dd', '', number(item?.total));
    if (item) value.append(make('small', '', `${percentText(percent(item.total, total))} of all tasks`));
    box.append(make('dt', '', label), value); if (item?.description) box.title = item.description; facts.append(box);
  }
  node.append(facts, make('p', 'insights-chart-note', 'Coverage counts can overlap. No recorded Arena verification means unverified availability, not a failed task.'));
  return node;
}

const FIELD_STORIES = {
  physics: {tone:'amber', symbol:'orbit', question:'Which equations capture physical behavior?', topics:'Oscillation · heat flow · dynamical systems', examples:['coevo-oscillation-1','a2dept-ode-integration-discretized-heat-equation-n-20']},
  'chemistry-materials': {tone:'lilac', symbol:'bonds', question:'How do reactions and materials behave?', topics:'Reaction kinetics · materials · stress & strain', examples:['a2dept-ode-integration-robertson-kinetics','coevo-stress-strain']},
  'biology-health': {tone:'green', symbol:'life', question:'How can we model living systems?', topics:'Growth · populations · biological data', examples:['coevo-e-coli-growth','dga2d-ode-solver-lotka-volterra']},
  mathematics: {tone:'blue', symbol:'construction', question:'Can a construction improve a bound?', topics:'Geometry · algebra · mathematical bounds', examples:['alphaevolve-circle-packing-in-unit-square','alphaevolve-matrix-multiplication-4-4-4']},
  'earth-environment': {tone:'green', symbol:'earth', question:'What can environmental observations predict?', topics:'Volcanic sensors · forest-cover observations', examples:['loongflow-predict-volcanic-eruptions-ingv-oe','loongflow-tabular-playground-series-dec-2021']},
  'robotics-control': {tone:'lilac', symbol:'control', question:'Which feedback makes a system behave reliably?', topics:'Controllers · rewards · learned movement', examples:['a2dept-feedback-control-cartpole-stabilization','text2reward-button-press-v2']},
  'operations-research': {tone:'amber', symbol:'routes', question:'How should limited resources be allocated?', topics:'Routing · packing · scheduling', examples:['a2dept-capacitated-electric-vehicle-routing-with-time-windows','reference-online-bin-packing']},
  'computer-systems': {tone:'blue', symbol:'systems', question:'Can the same workload use fewer resources?', topics:'Compute · placement · infrastructure', examples:['adaevolve-expert-placement-load-balancing','pairwise-validator-txn-scheduling']},
  'machine-learning': {tone:'lilac', symbol:'intelligence', question:'What improves reasoning and generalization?', topics:'Learning · prompts · reasoning · retrieval', examples:['adaevolve-arc-agi-2','promptbreeder-gsm8k']},
  'software-engineering': {tone:'green', symbol:'software', question:'Does generated software meet its contract?', topics:'Program synthesis · behavior · correctness', examples:['sciel-bench-kattis-alphabet','sciel-bench-web-scraper-api-docs']},
  'finance-economics': {tone:'blue', symbol:'decisions', question:'How do policies balance return and risk?', topics:'Allocation · trading policies · risk', examples:['ael-harness-d-full-portfolio-allocation','algoevolve-numin-intraday-equity-trading']},
  unknown: {tone:'neutral', symbol:'mixed', question:'Which scientific target does this task define?', topics:'Mixed suites · open classification', examples:['deliberate-evolution-lsr-transform','adaevolve-frontier-cs']},
};
// Editorial context for the exact task examples, checked against the primary sources below.
// Historical references describe source results, not an Arena result or a claim of optimality.
const TASK_CONTEXT = {
  "coevo-oscillation-1": {
    "summary": "Recover an equation for the acceleration of a driven, damped oscillator from its position and velocity. An explicit formula helps connect observed motion to a physical model that researchers can inspect and analyze.",
    "source_url": "https://github.com/pgg3/CoEvo/blob/dcad65e9799961cf67cf29865ff41dda2902a808/CoEvo/src/coevo/tasks/oscillation_1.py",
    "source_locator": "task_description and equation function skeleton",
    "evidence_note": "The pinned task explicitly specifies a damped nonlinear oscillator with a driving force, position and velocity inputs, and acceleration output. Scientific usefulness describes the equation-discovery objective, without claiming that recovered formulas identify the true physical law."
  },
  "a2dept-ode-integration-discretized-heat-equation-n-20": {
    "summary": "Design a numerical method to track heat spreading through a model with 20 coupled variables. The challenge is to keep the simulation accurate and stable while limiting calculations, a central trade-off in computational physics.",
    "source_url": "https://arxiv.org/pdf/2604.24043",
    "source_locator": "Appendix G.1, printed pp. 38–39, Experimental Setup and Table 17",
    "evidence_note": "Appendix G.1 specifies N=20, an accuracy–computation score and fixed-step stability challenges. Spatial geometry and boundary conditions are unspecified; no runnable reproduction is claimed."
  },
  "a2dept-ode-integration-robertson-kinetics": {
    "summary": "Develop a solver for a chemical reaction model with fast and slow changes occurring together. This stiffness can make time stepping unstable; the scientific challenge is accurate, stable simulation without excessive computation.",
    "source_url": "https://arxiv.org/pdf/2604.24043",
    "source_locator": "Appendix G.1, printed pp. 38–39, Robertson Kinetics and Table 17",
    "evidence_note": "Appendix G.1 identifies Robertson as stiff and balances accuracy against function evaluations. Standard equations cross-checked in SciML’s Robertson example: https://docs.sciml.ai/DiffEqDocs/v7.14/tutorials/faster_ode_example/."
  },
  "coevo-stress-strain": {
    "summary": "Find an equation linking an aluminium rod’s stress to deformation and temperature, covering both reversible stretching and permanent deformation. Such material models help explain how mechanical response changes across conditions and support simulations of loaded structures.",
    "source_url": "https://github.com/pgg3/CoEvo/blob/dcad65e9799961cf67cf29865ff41dda2902a808/CoEvo/src/coevo/tasks/stress_strain.py",
    "source_locator": "task_description and equation function skeleton",
    "evidence_note": "The pinned task specifies stress from strain and temperature in an aluminium rod across elastic and plastic regions. Reversible versus permanent deformation explains those regimes in plain language; downstream structural simulation is scientific motivation, not a demonstrated deployment."
  },
  "coevo-e-coli-growth": {
    "summary": "Find an equation describing how E. coli growth depends on population density, nutrients, temperature and acidity. The resulting formula makes these relationships explicit, helping researchers compare biological models across environmental conditions.",
    "source_url": "https://github.com/pgg3/CoEvo/blob/dcad65e9799961cf67cf29865ff41dda2902a808/CoEvo/src/coevo/tasks/bactgrow.py",
    "source_locator": "task_description and equation function skeleton",
    "evidence_note": "The source specifies growth rate from bacterial population density, substrate concentration, temperature and pH. 'Nutrients' and 'acidity' explain substrate and pH for a general reader. No new wet-lab result or causal identification is asserted."
  },
  "dga2d-ode-solver-lotka-volterra": {
    "summary": "Build a numerical solver for interacting predator and prey populations. Following their coupled changes accurately with few calculations helps study population dynamics while separating numerical error from behavior produced by the ecological model itself.",
    "source_url": "https://arxiv.org/html/2608.00700v1",
    "source_locator": "Appendix G.1, Numerical ODE Integration: problem families and accuracy–cost score",
    "evidence_note": "Appendix G.1 names Lotka–Volterra and scores final-state error against right-hand-side evaluations. The standard two-population equations were cross-checked in the official SciPy solve_ivp examples: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html. No species, field dataset, or conservation test is invented."
  },
  "alphaevolve-circle-packing-in-unit-square": {
    "summary": "Fit 26 nonoverlapping circles of varying sizes inside a unit square while maximizing their total radii. A better valid arrangement improves a mathematical lower bound, helping narrow the gap between what can be constructed and what can be proved optimal.",
    "source_url": "https://arxiv.org/pdf/2506.13131",
    "source_locator": "Appendix B.12, printed pp. 43–44; Figure 14, left",
    "evidence_note": "The paper explicitly maximizes the sum of radii and reports the n=26 construction as an improved bound. The summary makes no claim about a nineteenth-century origin, current record, or proven optimal packing."
  },
  "alphaevolve-matrix-multiplication-4-4-4": {
    "summary": "Find exact rules for multiplying two 4×4 matrices with fewer scalar products. The 49-product construction derived from Strassen’s 1969 algorithm provides a historical reference; reducing this count studies the arithmetic cost of a basic operation in scientific computing.",
    "source_url": "https://arxiv.org/pdf/2506.13131",
    "source_locator": "Section 3.1, printed pp. 9–10; Appendix A, Table 3; reference 95",
    "evidence_note": "Section 3.1 explicitly derives rank 49 by recursively applying Strassen; reference 95 dates it to 1969. AlphaEvolve's reported rank-48 construction uses complex arithmetic. The summary does not call rank 49 optimal or equate fewer scalar products with measured runtime gains."
  },
  "loongflow-predict-volcanic-eruptions-ingv-oe": {
    "summary": "Estimate the time remaining before a volcanic eruption from ten-minute recordings of ten seismic sensors. Finding useful precursors in these signals supports research on eruption forecasting, where warning time matters as well as prediction accuracy.",
    "source_url": "https://github.com/openai/mle-bench/blob/507f92e1138bb6e40dac5c6ee7a6758e6424bf97/mlebench/competitions/predict-volcanic-eruptions-ingv-oe/description.md",
    "source_locator": "Archived competition description, Overview and Dataset Description, lines 3–7 and 49–57",
    "evidence_note": "MLE-bench preserves the INGV/Kaggle task description, target time_to_eruption, and ten-minute, ten-sensor recordings. Forecasting motivation is explicit in the competition description; no operational warning system or field reliability is claimed."
  },
  "loongflow-tabular-playground-series-dec-2021": {
    "summary": "Predict forest-cover classes from synthetic data modeled on a real forest-cover benchmark. It provides a controlled setting for comparing how learning methods use terrain and soil features to distinguish vegetation classes.",
    "source_url": "https://github.com/openai/mle-bench/blob/507f92e1138bb6e40dac5c6ee7a6758e6424bf97/mlebench/competitions/tabular-playground-series-dec-2021/description.md",
    "source_locator": "Archived competition description, lines 12, 16–19 and Dataset Description, lines 41–48",
    "evidence_note": "The official competition text preserved by MLE-bench explicitly says the data were generated by a GAN trained on Forest Cover Type Prediction data, with relationships potentially differing from the original. Target Cover_Type and multiclass accuracy are recorded."
  },
  "a2dept-feedback-control-cartpole-stabilization": {
    "summary": "Design a feedback rule that moves a cart to keep an upright pole balanced. Maintaining stability over a long simulation while limiting tracking error and control effort studies a basic challenge shared by robots and other controlled machines.",
    "source_url": "https://arxiv.org/pdf/2604.24043",
    "source_locator": "Appendix G.3 and Table 19, printed p. 40",
    "evidence_note": "Appendix G.3 specifies unstable CartPole dynamics, 5,000 simulation steps, divergence penalties, tracking error and control action. Broader robotics relevance is motivation, not a deployment claim."
  },
  "text2reward-button-press-v2": {
    "summary": "Design a reward function that guides a simulated robot arm to reach and press a button. Turning a simple goal into useful step-by-step feedback helps study how robots learn precise manipulation through reinforcement learning.",
    "source_url": "https://arxiv.org/html/2309.11489v3",
    "source_locator": "Appendix B, Table 4, Button Press; reward-shaping method in Section 3",
    "evidence_note": "Table 4 specifies pressing a button along the y direction. The pinned implementation at https://github.com/xlang-ai/text2reward/blob/e7f57efcf76b22bbfb7c3eb9d67d98ff2765a926/run_metaworld/reward_code/button-press-v2/specific.py scores gripper distance, object state and actions. The summary describes reward design in simulation, not a deployed physical skill."
  },
  "a2dept-capacitated-electric-vehicle-routing-with-time-windows": {
    "summary": "Plan electric-vehicle delivery routes while respecting cargo limits, battery charge and customer time windows. The task tests whether a generated solver can reduce travel cost while satisfying several interacting constraints.",
    "source_url": "https://arxiv.org/pdf/2604.24043v1",
    "source_locator": "Appendix A.4.5, pp.21–22; Appendix D.1.2, Table 5",
    "evidence_note": "The formulation minimizes travel cost with cargo, battery, recharge and time-window constraints. The reported benchmark uses ESOGU-CEVRPTW instances. No historical open-problem claim is made."
  },
  "reference-online-bin-packing": {
    "summary": "Place incoming items into fixed-capacity bins without seeing future arrivals, using as few bins as possible. This isolates online heuristic design: each local placement changes the space available for later items.",
    "source_url": "https://github.com/IMRUNya/autoresearch-tasks/blob/995768fc462b8e327f90e6762846cc6ccb06cc2c/suite/reference-online-bin-packing/problem.json",
    "source_locator": "#/contract, #/parameters, #/protocol_description; sibling evaluator.py: task()",
    "evidence_note": "Verified in local checkout at the cited commit: generated fixed-seed instances, capacity 100, priority-based placement, and excess-bin scoring. This is the native recreated task, not a published experimental reproduction; unauthenticated source URL returned 404."
  },
  "adaevolve-expert-placement-load-balancing": {
    "summary": "Rearrange and replicate a mixture-of-experts model’s experts across GPUs to balance their workload. The benchmark evaluates both load balance and the speed of the placement algorithm, exposing the cost of computing a better assignment.",
    "source_url": "https://github.com/skydiscover-ai/skydiscover/blob/0d932b690670a7e544388ad362e9876c8bd256a0/benchmarks/ADRS/eplb/README.md",
    "source_locator": "Opening task definition and Files table",
    "evidence_note": "Fetched the pinned upstream README directly. It explicitly describes rearrangement and replication across GPUs, with evaluator scores for load-balance quality and execution speed; also corroborated by AdaEvolve Appendix B, Table 6."
  },
  "pairwise-validator-txn-scheduling": {
    "summary": "Order database transactions to shorten the time needed to finish a workload, accounting for conflicts between reads and writes. It tests scheduling heuristics whose choices affect how much work can proceed concurrently.",
    "source_url": "https://arxiv.org/pdf/2607.14408v1",
    "source_locator": "Section 5.4, Table 5; pp.24–27, ADRS code-evolution outputs: get_best_schedule",
    "evidence_note": "The paper identifies the ADRS txn_scheduling task and includes a candidate scheduler with read/write conflict checks, transaction durations and minimum-makespan objective. Purpose statement describes this scheduling problem, not a reproduced result."
  },
  "adaevolve-arc-agi-2": {
    "summary": "Infer a transformation from example pairs of colored grids and apply it to a new input. These tasks test how a solver combines visual relations, contextual rules and multiple reasoning steps from a small set of examples.",
    "source_url": "https://github.com/arcprize/ARC-AGI-2",
    "source_locator": "README: Task success criterion and Task file format; AdaEvolve Appendix C, Table 8",
    "evidence_note": "Official ARC-AGI-2 README defines demonstration pairs and exact output-grid prediction; the official benchmark page identifies compositional and contextual-rule tasks. AdaEvolve Appendix C identifies its 120-instance ARC-AGI-2 experiment and labels it exploratory."
  },
  "promptbreeder-gsm8k": {
    "summary": "Evolve prompts for solving grade-school mathematics word problems, then check the resulting numerical answers. This provides a concrete test of whether changes to instructions and worked examples improve multistep arithmetic reasoning.",
    "source_url": "https://arxiv.org/pdf/2309.16797v1",
    "source_locator": "Section 4; Appendix I.2 Arithmetic Reasoning; Appendix J.8 GSM8K",
    "evidence_note": "Promptbreeder explicitly evaluates GSM8K mathematical word problems and evolves instructions plus optional worked-example context. The summary states the optimization target and evaluation purpose, not an improvement achieved by Arena."
  },
  "sciel-bench-kattis-alphabet": {
    "summary": "Find the fewest letters to insert into a string so that the alphabet appears in order as a subsequence. This compact programming task tests sequence reasoning and exact correctness through an online judge.",
    "source_url": "https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/online_judge_programming/README.md",
    "source_locator": "Problem Description; copied as suite/sciel-bench-kattis-alphabet/README.upstream.md in pinned task snapshot",
    "evidence_note": "Verified the copied upstream problem statement in task checkout 995768fc462b8e327f90e6762846cc6ccb06cc2c: lowercase input and minimum insertions for a..z subsequence. The upstream URL returned 404; this is verification against its recorded source copy."
  },
  "sciel-bench-web-scraper-api-docs": {
    "summary": "Extract function names, signatures and parameters from three fixed HTML documentation layouts. The task tests parser changes against known outputs, measuring extraction accuracy, completeness and the number of pages processed without errors.",
    "source_url": "https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/web_scraper_optillm/evaluator.py",
    "source_locator": "evaluate(), get_test_cases(), evaluate_extraction(); copied as suite/sciel-bench-web-scraper-api-docs/evaluator.py in pinned task snapshot",
    "evidence_note": "Read copied evaluator at task commit 995768fc462b8e327f90e6762846cc6ccb06cc2c. It uses three embedded HTML cases, expected function/parameter data, and parsing-exception counts; no claim of broad web coverage. Upstream URL currently returned 404."
  },
  "ael-harness-d-full-portfolio-allocation": {
    "summary": "Allocate weights across ten equities and cash using a sequence of historical market observations. The benchmark studies how memory, tool use and decision procedures affect portfolio returns and risk across changing market conditions.",
    "source_url": "https://arxiv.org/pdf/2604.21725v2",
    "source_locator": "Section 4.1; Appendix L, Tables 17–18; experiments/run_portfolio.py at c95f5f961667e7df4bdddf750b22332158951bf2",
    "evidence_note": "Paper specifies ten equities plus cash, hourly observations and chronological train/validation/test episodes; runner allocates weights across tickers per bar. The summary describes a historical benchmark, without investment guidance or a future-performance claim."
  },
  "algoevolve-numin-intraday-equity-trading": {
    "summary": "Produce buy, sell or hold decisions from five-minute equity data in a paper-trading simulator. Returns, volatility and drawdown expose how evolved programs behave across historical trading windows, including the effects of transaction costs.",
    "source_url": "https://arxiv.org/pdf/2606.26173v1",
    "source_locator": "Section 5.1 Market Environment and Feature Representation, pp.4–5; Section 5.2",
    "evidence_note": "The source defines NUMIN as an anonymized multi-asset intraday paper-trading environment, with five-minute observations, buy/sell/hold outputs, fixed transaction/slippage cost and return/risk metrics. Section 5.1 is the actual setup locator in v1."
  },
  "deliberate-evolution-lsr-transform": {
    "summary": "Recover mathematical expressions from data generated by transformed benchmark equations. Changing familiar equation forms makes this a test of symbolic-regression search designed to challenge formula recall while measuring how closely candidate expressions fit the data.",
    "source_url": "https://arxiv.org/pdf/2606.04360v1",
    "source_locator": "Appendix E.1 Benchmark Details, Table 6; Section 4, Table 1",
    "evidence_note": "Appendix E.1 defines the transform subset by changing existing equation representations; Table 6 names LSR-Transform and Table 1 evaluates normalized MSE. The purpose is framed as benchmark design, not proof that memorization is eliminated; conflicting total dataset counts are omitted."
  },
  "adaevolve-frontier-cs": {
    "summary": "Generate executable solutions for a suite of 172 computer-science problems spanning algorithm design and systems optimization. This provides varied, task-specific feedback for studying program search where solution quality matters beyond whether code merely runs.",
    "source_url": "https://arxiv.org/pdf/2602.20133v1",
    "source_locator": "Section 4.4 Frontier-CS, Table 3",
    "evidence_note": "AdaEvolve explicitly evaluates 172 Frontier-CS problems spanning algorithmic optimization and systems tasks via executable programs. The number describes this paper’s benchmark evaluation; no claim that every problem is historically open is made."
  }
};

const FIELD_SYMBOLS = {
  orbit:'M20 48c0-14 56-14 56 0s-56 14-56 0 M34 24c12-7 40 41 28 48S22 31 34 24 M62 24c12 7-16 55-28 48s16-55 28-48',
  bonds:'M48 20 72 34v28L48 76 24 62V34z M48 20v18m24-4L56 44m16 18L56 52M48 76V58M24 62l16-10M24 34l16 10',
  life:'M31 18c43 13-9 46 34 60 M65 18C22 31 74 64 31 78 M37 24h22M40 39h16M40 57h16M37 72h22',
  construction:'M29 24h15v15H29z M52 24h15v15H52z M17 47h15v15H17z M40 47h15v15H40z M63 47h15v15H63z M29 70h15M52 70h15',
  earth:'M18 50c0-19 17-31 34-28s29 13 26 30-19 28-36 24S18 67 18 50z M28 46c4-13 22-18 33-8s-1 28-13 28-25-7-20-20z M40 45c6-6 17 3 10 9s-16-3-10-9',
  control:'M24 72h47 M34 72V51l21-20 16 10 M28 51a6 6 0 1 0 12 0 6 6 0 1 0-12 0 M49 29a6 6 0 1 0 12 0 6 6 0 1 0-12 0 M67 39l7 13 9-11',
  routes:'M22 68V27h24v42h27V27 M16 68a6 6 0 1 0 12 0 6 6 0 1 0-12 0 M67 27a6 6 0 1 0 12 0 6 6 0 1 0-12 0',
  systems:'M21 23h20v20H21z M55 23h20v20H55z M21 57h20v20H21z M55 57h20v20H55z M41 33h14M31 43v14M65 43v14M41 67h14',
  intelligence:'M24 31h1m23-9h1m23 9h1M17 49h1m29 0h1m29 0h1M24 67h1m23 9h1m23-9h1',
  software:'m34 28-18 20 18 20 M62 28l18 20-18 20 M53 23 43 73',
  decisions:'M20 48h56 M48 20v56 M27 28l42 42 M27 68l42-42',
  mixed:'M26 24h12v12H26z M57 24h12v12H57z M26 57h12v12H26z M57 57h12v12H57z',
};
function scientificFields(root, insights, catalog, current, onFilter, exploredDomain, onExploreDomain) {
  const {make,link} = ui(root), section = make('section','insights-fields');
  const selectedId = exploredDomain === undefined ? current.domain : exploredDomain;
  const explore = onExploreDomain || (id => onFilter('domain', id));
  section.setAttribute('aria-label','Explore scientific directions');
  const header = make('div','fields-heading');
  const intro=make('div');intro.append(make('span','fields-eyebrow','SCIENTIFIC CONTEXT'),make('h3','','Research domains'),
    make('p','','Problems, methods and example tasks across the scientific domains represented in the catalog.'));
  header.append(intro,make('span','fields-heading-note',`${number(insights.domains.filter(item=>item.id!=='unknown').length)} research directions`));section.append(header);
  const grid=make('div','fields-grid'); grid.setAttribute('role','group');grid.setAttribute('aria-label','Explore scientific directions');
  const order=Object.keys(FIELD_STORIES), domains=[...insights.domains].sort((a,b)=>(order.indexOf(a.id)<0?99:order.indexOf(a.id))-(order.indexOf(b.id)<0?99:order.indexOf(b.id)));
  for(const domain of domains){
    const story=FIELD_STORIES[domain.id] || {tone:'blue',symbol:'mixed',question:domain.description || domain.label,topics:'Explore the recorded scientific context'};
    const card=make('button','field-card');card.type='button';card.dataset.tone=story.tone;card.dataset.domainCard=domain.id;
    card.dataset.insightsAction=`field:${domain.id}`;card.dataset.filterKind='domain';card.dataset.filterValue=domain.id;
    card.setAttribute('aria-expanded',String(selectedId===domain.id));
    card.setAttribute('aria-controls','arena-domain-preview');
    card.setAttribute('aria-label',`${domain.label}: ${number(domain.total)} tasks; ${number(domain.executable)} executable definitions, ${number(domain.unsupported)} awaiting an evaluator. ${story.question} Explore research direction.`);
    const copy=make('span','field-copy'),meta=make('span','field-meta');
    meta.append(make('span','field-topics',story.topics),make('span','field-count',`${number(domain.total)} tasks`));
    copy.append(meta,make('span','field-title',domain.label),make('span','field-question',story.question));
    const visual=make('span','field-visual');visual.setAttribute('aria-hidden','true');
    const svg=root.ownerDocument.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 96 96');svg.setAttribute('class',`field-symbol field-symbol-${story.symbol}`);
    const path=root.ownerDocument.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',FIELD_SYMBOLS[story.symbol] || FIELD_SYMBOLS.mixed);svg.append(path);visual.append(svg);
    visual.append(make('span','field-explore',selectedId===domain.id?'Close direction':'Explore direction'),make('span','field-arrow',selectedId===domain.id?'−':'↗'));
    card.append(copy,visual);card.addEventListener('click',()=>explore(selectedId===domain.id?null:domain.id));grid.append(card);
  }
  section.append(grid);
  const selected=insights.domains.find(domain=>domain.id===selectedId);
  if(selected){
    const story=FIELD_STORIES[selected.id],detail=make('div','field-detail');detail.dataset.fieldDetail=selected.id;detail.id='arena-domain-preview';
    detail.setAttribute('role','region');detail.setAttribute('aria-labelledby','arena-domain-preview-title');
    const close=make('button','field-detail-close','×');close.type='button';close.setAttribute('aria-label','Close research direction');close.addEventListener('click',()=>explore(null));detail.append(close);
    const description=make('div');description.append(make('span','fields-eyebrow','INSIDE THIS DIRECTION'),Object.assign(make('h4','',selected.label),{id:'arena-domain-preview-title',tabIndex:-1}),make('p','',selected.why_it_matters || selected.description));
    const examples=make('div','field-examples');examples.append(make('span','fields-eyebrow','START WITH A TASK'));
    const tasks=new Map(catalog.tasks.map(task=>[task.id,task]));
    const ids=story?.examples || selected.representative_task_ids || [];
    for(const id of ids.slice(0,2)){
      const task=tasks.get(id);if(!task || insights.task_annotations?.[id]?.domain_id!==selected.id)continue;
      const row=make('div','field-example'),context=TASK_CONTEXT[id];
      row.append(link(`${task.name || id} ↗`,`/?task=${encodeURIComponent(id)}`,true));
      const explanation=make('p','field-example-context',context?.summary || task.description || selected.why_it_matters || selected.description);
      const source=safeURL(context?.source_url);
      if(source){
        const citation=link('Source ↗',source);citation.className='field-context-source';
        citation.title=context.source_locator;citation.setAttribute('aria-label',`Source for ${task.name || id}: ${context.source_locator}`);
        explanation.append(' ',citation);
      }
      row.append(explanation);examples.append(row);
    }
    const browse=make('a','field-catalog-link','Browse matching tasks ↓');browse.href=`/?domain=${encodeURIComponent(selected.id)}#arena-list-panel`;browse.addEventListener('click',event=>{if(event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)return;event.preventDefault();onFilter('domain',selected.id);});examples.append(browse);detail.append(description,examples);section.append(detail);
  }
  section.append(make('p','fields-footnote','Each direction gets its own space. Counts describe this task collection; variants of the same benchmark are counted separately.'));
  return section;
}

function parameterText(parameters) {
  return Object.entries(parameters || {}).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${Array.isArray(value) ? value.join(' × ') : text(value).replaceAll('_', ' ')}`).join(' · ');
}

function evaluationSize(evaluation, seed = false) {
  if (evaluation?.case_count == null) return null;
  const count = text(evaluation.case_count), kind = evaluation.case_count_kind;
  if (kind === 'candidate_construction') return `${count} construction${evaluation.case_count === 1 ? '' : 's'}`;
  if (kind === 'historical_smoke' || seed) return `${count} items (historical smoke)`;
  if (kind === 'test_id_rows') return `${count} rows (in-distribution test)`;
  if (kind === 'named_initial_value_problem') return `${count} named initial-value problem${evaluation.case_count === 1 ? '' : 's'}`;
  return `${count} cases${kind ? ` (${kind.replaceAll('_', ' ')})` : ' (scope not recorded)'}`;
}

function referenceTable(root, records, catalog, {detail = false} = {}) {
  const {make, link} = ui(root), names = new Map((catalog?.tasks || []).map(task => [task.id, task.name]));
  const wrapper = make('div', 'table-wrap'), table = make('table', 'insights-reference-table'), head = make('thead'), tr = make('tr');
  for (const label of [detail ? 'Reference' : 'Task / instance', 'Value & metric', 'Evidence', 'Source']) { const th = make('th', '', label); th.scope = 'col'; tr.append(th); }
  head.append(tr); table.append(head); const body = make('tbody');
  for (const record of records) {
    const anchors = [...(record.anchors || [])].sort((a, b) => Number(b.kind === 'published_reference') - Number(a.kind === 'published_reference'));
    const groups = detail ? anchors.map(anchor => [anchor]) : [anchors];
    for (const group of groups) {
      const row = make('tr'), label = make('td'), value = make('td', 'insights-reference-value'), evidence = make('td'), source = make('td');
      row.dataset.referenceTask = record.task_id;
      if (!detail) {
        label.append(link(names.get(record.task_id) || record.task_id, `/?task=${encodeURIComponent(record.task_id)}`, true));
        const parameters = parameterText(record.evaluation?.parameters);
        if (parameters) label.append(make('small', '', parameters));
      }
      for (const anchor of group) {
        const kind = anchor.kind === 'published_reference' ? 'Published reference' : 'Seed smoke';
        if (detail) {
          label.append(make('span', '', anchor.label || kind));
          if (anchor.scope) label.append(make('small', '', text(anchor.scope)));
          if (anchor.notes?.length) label.append(make('small', '', anchor.notes.map(text).join(' ')));
        }
        const valueBlock = make('div', 'insights-anchor-value');
        valueBlock.append(make('span', '', `${detail ? '' : `${kind}: `}${text(anchor.value)}`));
        value.append(valueBlock);
        const evidenceBlock = make('div', 'insights-anchor-evidence');
        evidenceBlock.append(make('span', '', anchor.kind === 'published_reference' ? 'Source-declared published value' : 'Historical seed smoke'));
        if (anchor.reproduction === 'recorded_upstream') evidenceBlock.append(make('small', '', 'Upstream artifact check recorded'));
        if (anchor.kind === 'recorded_seed_baseline') evidenceBlock.append(make('small', '', anchor.validity === true ? 'Source validity: true' : 'Validity not recorded'));
        const size = evaluationSize(anchor.evaluation, anchor.kind === 'recorded_seed_baseline');
        if (size) evidenceBlock.append(make('small', '', size));
        evidence.append(evidenceBlock);
        const url = safeURL(anchor.source?.url);
        const sourceBlock = make('div', 'insights-anchor-source');
        if (url) sourceBlock.append(link(`${detail ? 'Source' : kind} ↗`, url)); else sourceBlock.append(make('span', '', 'Not linked'));
        if (detail && anchor.source?.locator) sourceBlock.append(make('small', '', anchor.source.locator));
        if (detail) {
          for (const item of anchor.primary_sources || []) {
            const primaryURL = safeURL(item.url);
            if (primaryURL) sourceBlock.append(link(`${item.type === 'paper' ? 'Paper' : 'Primary source'} ↗`, primaryURL));
          }
          const receiptURL = safeURL(anchor.reproduction_source?.url);
          if (receiptURL) sourceBlock.append(link('Artifact check receipt ↗', receiptURL));
        }
        source.append(sourceBlock);
      }
      const first = group[0];
      value.append(make('small', '', `${first.metric_label || first.metric || record.metric || 'Metric not recorded'} · ${first.direction || record.direction || 'direction not recorded'}`));
      row.append(label, value, evidence, source); body.append(row);
    }
  }
  table.append(body); wrapper.append(table); return wrapper;
}

function referencesPanel(root, references, catalog, current, onFilter, matchingTasks) {
  const {make, panel} = ui(root), summary = references.summary || {};
  const node = panel('Published references & SOTA evidence', 'Coverage counts cover the full catalog; examples follow your filters. Published values and seed smoke scores retain separate scopes.');
  const buttons = make('div', 'insights-reference-summary');
  for (const [filter, label, key] of [['published', 'Published reference', 'tasks_with_published_reference'], ['baseline', 'Seed baseline', 'tasks_with_recorded_baseline'], ['missing', 'No numeric reference', 'tasks_without_numeric_reference']]) {
    const button = make('button', '', label); button.type = 'button'; button.append(make('strong', '', number(summary[key])));
    button.dataset.insightsAction = `reference:${filter}`; button.setAttribute('aria-pressed', String(current.reference === filter));
    button.setAttribute('aria-label', `${label}: ${number(summary[key])} tasks. Filter catalog.`);
    button.addEventListener('click', () => onFilter('reference', current.reference === filter ? null : filter)); buttons.append(button);
  }
  node.append(buttons);
  const eligible = new Set(matchingTasks.map(task => task.id));
  const candidates = references.tasks.filter(record => eligible.has(record.task_id) && record.anchors?.length && referenceMatches(record, current.reference));
  const highlighted = new Map((references.highlights || []).map((item, index) => [item.task_id, index]));
  candidates.sort((a, b) => (highlighted.get(a.task_id) ?? 1000) - (highlighted.get(b.task_id) ?? 1000) || Number(b.anchors.some(anchor => anchor.kind === 'published_reference')) - Number(a.anchors.some(anchor => anchor.kind === 'published_reference')) || a.task_id.localeCompare(b.task_id));
  if (candidates.length) {
    node.append(referenceTable(root, candidates.slice(0, 4), catalog));
    node.append(make('p', 'insights-chart-note', `Showing ${Math.min(4, candidates.length)} of ${number(candidates.length)} task records with values in this selection. Open a task for every reference and its scope.`));
  } else node.append(make('p', 'insights-chart-note', current.reference === 'missing' ? 'The catalog below is filtered to tasks without a numeric reference in this snapshot.' : 'No numeric references are recorded for the selected tasks in this snapshot.'));
  const sota = summary.current_sota_status === 'not_assessed' || summary.verified_current_sota === 0 ? 'Current SOTA has not been established by this catalog. Source-declared values remain references, not verified current records.' : `Current SOTA verification is recorded for ${number(summary.verified_current_sota)} tasks; consult each source and comparison scope.`;
  node.append(make('p', 'insights-chart-note', sota));
  if (references.as_of) node.append(make('p', 'insights-chart-note', `Reference snapshot: ${references.as_of}.`));
  return node;
}

export function renderTaskReferences(root, {record, references, error, loading}) {
  const {make} = ui(root), node = make('section', 'arena-detail-section insights-task-reference');
  node.dataset.taskReferences = 'true'; node.append(make('h3', '', 'References & comparison scope'));
  if (error) node.append(make('p', '', 'Reference data is unavailable. This does not establish that the task has no reference.'));
  else if (loading && !references) node.append(make('p', '', 'Loading recorded references…'));
  else if (!record?.anchors?.length) node.append(make('p', '', 'No numeric reference is recorded for this task in the reference snapshot.'));
  else {
    node.append(referenceTable(root, [record], null, {detail: true}));
    node.append(make('p', 'insights-chart-note', 'Published values are source-declared. Seed smoke scores describe earlier checks. Neither alone establishes current SOTA or a comparable new result.'));
    const evaluation = record.evaluation;
    const parameters = parameterText(evaluation?.parameters);
    if (parameters) node.append(make('p', 'insights-chart-note', `Task instance: ${parameters}.`));
    const size = evaluationSize(evaluation);
    if (size) node.append(make('p', 'insights-chart-note', `Evaluation size: ${size}.`));
    if (evaluation?.notes?.length) node.append(make('p', 'insights-chart-note', evaluation.notes.map(text).join(' ')));
  }
  root.append(node);
}

export function renderArenaInsights(root, options) {
  const {insights, references, catalog, current, analysisRoot, statisticsRoot, exploredDomain, onExploreDomain, matchingTasks = catalog?.tasks || [], errors = {}, loading, onFilter, onRetry} = options;
  const separateAnalysis = analysisRoot && analysisRoot !== root ? analysisRoot : null;
  const previous = sessions.get(root), key = [insights, references, catalog, separateAnalysis, statisticsRoot, exploredDomain, current.domain, current.type, current.reference, current.query, current.family, current.search_family, current.protocol, errors.insights, errors.references, loading];
  if (previous && key.every((value, index) => value === previous.key[index])) return;
  const active = root.ownerDocument.activeElement;
  const focusRoot = statisticsRoot?.contains(active) ? statisticsRoot : separateAnalysis?.contains(active) ? separateAnalysis : root;
  const focus = focusRoot.contains(active) ? active?.dataset.insightsAction : null;
  const compositionOpen = Boolean((statisticsRoot || separateAnalysis || root).querySelector('.insights-composition[open]'));
  const session = {key, expanded: previous?.expanded || {domain: false, type: false}}; sessions.set(root, session);
  const {make} = ui(root), container = make('div', 'arena-insights');
  const analysis = separateAnalysis ? make('div', 'arena-insights arena-analysis-content') : container;
  const heading = make('div', 'insights-heading'); heading.append(make('h2', '', 'Scientific overview'), make('p', '', 'Explore the problem mix, evaluation definitions and source evidence before choosing a task.'));
  const jump = make('a', 'insights-catalog-jump', `${number(matchingTasks.length)} matching tasks · View catalog ↓`); jump.href = '#arena-list-panel';
  heading.append(jump); container.append(heading);
  if (insights && catalog) {
    container.append(scientificFields(root,insights,catalog,current,onFilter,exploredDomain,onExploreDomain));
    const composition=make('details','insights-composition');composition.open=compositionOpen;
    const compositionSummary=make('summary');compositionSummary.append(make('span','','Catalog statistics'),make('small','',`${number(insights.denominator.task_count)} task packages · domain shares & evaluation coverage`));composition.append(compositionSummary);
    const grid=make('div','insights-grid');
    grid.append(distribution(root,insights.domains,{title:'Domain distribution in this corpus',kind:'domain',selected:current.domain,total:insights.denominator.task_count,onFilter,expanded:true}),coverage(root,insights,catalog));
    composition.append(grid);
    if (statisticsRoot) statisticsRoot.replaceChildren(composition); else analysis.append(composition);
    analysis.append(distribution(root,insights.task_types,{title:'What the tasks ask you to do',kind:'type',selected:current.type,total:insights.denominator.task_count,onFilter,
      expanded:session.expanded.type,onExpand:()=>{session.expanded.type=!session.expanded.type;session.key=[];renderArenaInsights(root,options);}}));
    const methodology = make('details', 'insights-methodology'); methodology.append(make('summary', '', 'How to read these counts'));
    methodology.append(make('p', '', insights.methodology?.unit || 'Each task package contributes once to its primary domain and once to its task type. Multiple packages can describe variants of the same scientific problem.'));
    methodology.append(make('p', '', insights.methodology?.classification_authority || 'Domain and task-type assignments are Arena editorial classifications, based on the pinned task metadata. They are not claims made by the source authors.'));
    methodology.append(make('p', '', insights.methodology?.percentages?.replace(/unsupported definitions/g, 'definitions awaiting an evaluator') || 'Percentages use the complete catalog, including definitions awaiting an evaluator.'));
    if (insights.methodology?.papers) methodology.append(make('p', '', insights.methodology.papers));
    analysis.append(methodology);
  } else {
    statisticsRoot?.replaceChildren();
    container.append(unavailable(root, loading && !errors.insights ? 'Loading scientific overview…' : 'Scientific overview unavailable', 'The task catalog remains available below. Domain and task-type counts require the recorded overview.', errors.insights ? onRetry : null));
  }
  if (references && catalog) analysis.append(referencesPanel(root, references, catalog, current, onFilter, matchingTasks));
  else analysis.append(unavailable(root, loading && !errors.references ? 'Loading reference evidence…' : 'Reference evidence unavailable', 'Missing reference data is not evidence that no baseline or SOTA exists.', errors.references ? onRetry : null));
  root.replaceChildren(container);
  if (separateAnalysis) separateAnalysis.replaceChildren(analysis);
  if (focus) [...focusRoot.querySelectorAll('[data-insights-action]')].find(node => node.dataset.insightsAction === focus)?.focus({preventScroll: true});
}
