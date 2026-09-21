# Task suite (SCiEL layout)

One directory per catalog task, laid out like a SCiEL/OpenEvolve example so
that any task can be handed to SCiEL directly:

```
suite/<task-id>/
  evaluator.py          evaluate(program_path) -> dict with combined_score, score, direction, valid, error
  initial_program.py    seed program; SCiEL evolves the code between the EVOLVE-BLOCK markers
  config.yaml           ready SCiEL configuration (system prompt = task description + interface)
  README.md             paper, task description, candidate interface, protocol, sources, requirements
  problem.json          machine-readable version of README.md (id, protocol, family, parameters, requires, origin hashes)
  task.json             the manifest read by run.py, the facade and the dashboard: sources, requirements, pinned upstream route, execution.suite
suite/_lib/
  autoresearch_suite/   shared evaluator library used by the generated evaluators (see below)
  openevolve/           verbatim shim of SCiEL's openevolve.evaluation_result for copied SCiEL evaluators
  vendor/               byte-hashed upstream code the original evaluators need (AlgoTune subset, CORAL ADRS taskdata, kernel_builder simulator)
suite/index.json        id -> protocol / family / direction / requirements / timeout for every task
```

Run any task without installing anything beyond NumPy/SciPy:

```sh
cd suite/alphaevolve-circle-packing-in-unit-square
python evaluator.py initial_program.py
# {"combined_score": 2.14, "score": 2.14, "direction": "maximize", "valid": true, "error": null, "published": 2.6358..., ...}
```

Copied SCiEL examples keep their upstream `evaluate()` entry point; run them
with `PYTHONPATH=suite/_lib` (plus `suite/_lib/vendor/algotune` for the
AlgoTune examples), which is what `scripts/test_suite.py` and `run.py evaluate`
do for you. `python3 run.py evaluate <id>` from the repository root runs any
task's evaluator in a fresh interpreter and returns the common result envelope.

## Protocols

| protocol | meaning |
|---|---|
| `original` | evaluator code copied verbatim from the pinned upstream source; `problem.json.origin` records repository, path and SHA-256 of every copied file (SCiEL examples, CORAL ADRS systems tasks, the Anthropic performance take-home simulator, AlgoTune subset) |
| `recreated_verified` | verifier reimplemented in `suite/_lib` from the paper/notebook and checked to reproduce the published values on the published constructions (`tests/test_suite.py`): AlphaEvolve geometry/analysis problems and the exact matrix-multiplication tensor checker |
| `recreated` | evaluator reimplemented from the paper's task description with locally generated, seeded instances (combinatorial heuristics, black-box optimisation, symbolic regression, numerical methods, HPO). Scores are comparable within the suite, not with the paper's tables |
| `unsupported` | the task needs a model API, accelerator hardware, a simulator, a proprietary system or an undistributed dataset; `evaluator.py` returns `unsupported: true` with the reason and the exact requirements, `README.md` documents the intended candidate |

## Shared library (`suite/_lib/autoresearch_suite`)

| module | families |
|---|---|
| `runtime` | program loading, deadlines, result envelopes (`success`, `failure`, `run`, `main`) |
| `geometry` | circle packings (square, perimeter-4 rectangle), Heilbronn triangle/convex, max-min distance ratio, kissing configurations, hexagon packing |
| `analysis` | autocorrelation inequalities (C1, C2, C3, signed), Erdős minimum overlap, sums/differences, uncertainty inequality (Hermite and Laguerre constructions) |
| `tensor` | exact rank verification of matrix-multiplication tensor decompositions |
| `combinatorial` | online/offline bin packing, TSP (constructive, GLS, ACO), CVRP, orienteering, multi-knapsack, knapsack, flow/job/open shop, RCPSP, assembly-line balancing, MIS, max-cut, cap sets, isosceles-free sets, admissible tuples, 3-D packing, facility location, EVRP-TW, box-constrained QPs, SAT, OneMax |
| `blackbox` | 24 BBOB functions with AOCC scoring, GP Bayesian optimisation with candidate acquisition functions (plain and cost-aware), ZDT/DTLZ/WFG/RE multi-objective problems with hypervolume |
| `numerics` | ODE integration, scalar/2-D root finding, feedback control |
| `regression` | LLM-SR benchmark data (embedded, MIT), Feynman and univariate synthetic targets, symbolic-regression algorithm contract |
| `hpo` | scikit-learn hyperparameter objectives on bundled datasets (FunBO HPO tasks, LLaMEA-BO Bayesmark suite) |
| `online` | non-stationary contextual bandit |
| `llm`, `llm_benchmarks` | cached, budgeted OpenRouter client; public benchmark registry and scorers for prompt/agent/workflow tasks |
| `arc` | ARC-AGI-1/2 program-synthesis scoring on the public data |
| `rl` | Gymnasium training loop for RL-algorithm candidates |
| `reward_design` | MetaWorld reward-function evaluation with a CEM-trained linear policy |

## Regenerating and testing

```sh
python3 scripts/build_suite.py --sciel /path/to/SCiEL     # rebuild every directory (SCiEL checkout pinned to da70706f)
python3 scripts/test_suite.py --python .cache/sciel-env/bin/python --workers 6 --allow-network
python3 -m unittest tests.test_suite
```

`scripts/test_suite.py` runs every evaluator on its own seed in a fresh
interpreter and writes `validation/suite-report.json` and
`docs/SUITE_REPORT.md`. Requirements are declared per task in `problem.json`
(`py:<module>`, `bin:<tool>`, `env:<VAR>`, `file:<path>`, `network:<resource>`,
plus unsatisfiable `service:`/`hardware:`/`dataset:` markers); the harness
skips tasks whose requirements are missing instead of failing them.
