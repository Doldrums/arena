# SCiEL: Heat-map-assisted TSP, 1,000 cities

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-tsp-tour-minimization`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Optimize a bundled Python/C++ heat-map and tour solver on eight generated Euclidean TSP instances of 1,000 cities, scoring tour length with a small runtime modifier.

Benchmark named in the paper: SCiEL source example tsp_tour_minimization. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize the length of a tour that visits each location once and returns to its start.

Why it matters: Shorter feasible tours address routing, inspection and manufacturing movement costs. The local instances are bounded algorithmic studies of that operations-research objective, not evidence of a deployed logistics improvement.

- [An effective implementation of the Lin–Kernighan traveling salesman heuristic](https://doi.org/10.1016/S0377-2217(99)00284-2): Main research objective: Compute optimal or near-optimal traveling-salesman tours efficiently. Task connection: Helsgaun develops a solver whose central goal is shorter symmetric TSP tours. SCiEL: Heat-map-assisted TSP, 1,000 cities uses its own construction, search, or attention interface and instance distribution while optimizing that same feasible-tour objective.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/tsp_tour_minimization` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- The candidate is the ten-file source bundle serialized by the upstream formatter (initial_program.txt); evaluation trains the heat-map model and compiles the C++ solver.
- Imports openevolve.evaluation_result; suite/_lib/openevolve is a verbatim shim of that module.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `bin:g++`
- `py:click`
- `py:numpy`
- `py:psutil`
- `py:torch`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/tsp_tour_minimization/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/tsp_tour_minimization/initial_program (original baseline)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The baseline is a directory of Python/C++ sources, not a directly importable candidate. It must be serialized using the pinned formatter before evaluation.
- The generated TSP data cache has no fixed random seed and is reused by path; results are not comparable unless the dataset file and its hash are retained.
- Some error branches omit combined_score; the strict common adapter reports an execution error rather than inventing a score.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
