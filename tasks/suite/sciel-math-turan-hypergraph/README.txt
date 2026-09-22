# SCiEL: Tetrahedron-free three-uniform hypergraph

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-turan-hypergraph`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Construct a weighted three-uniform blow-up pattern with no tetrahedron and maximize its density.

Benchmark named in the paper: SCiEL source example turan_hypergraph. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/alphaevolve_math_problems/turan_hypergraph` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/turan_hypergraph/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/turan_hypergraph/initial_program.py (original baseline)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- Arena adds an explicit feasibility signal from exactly one trusted original verifier call during the same evaluation. Original scoring and normalization are retained in upstream_evaluator.py. Missing or ambiguous verifier observations remain unknown; this is not an optimum, theorem, or paper reproduction.

Arena adapter: _is_tetrahedron_free. Upstream evaluator SHA256: 3e2b6d700f18f5ec51ea0b5a6b79c3c3b755c0f2f3e44a9914bd40b0105b4993.
The Arena adaptation additionally requires a finite positive original weight total and a finite nonnegative normalized distribution summing to one. Finite raw weights whose sum overflows are rejected even if the original density score is finite.
