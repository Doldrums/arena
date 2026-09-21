# SCiEL: Tammes problem with 13 sphere points

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-tammes-problem`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Place 13 points on the unit sphere maximizing the smallest Euclidean separation.

Benchmark named in the paper: SCiEL source example tammes_problem. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Maximize the minimum pairwise separation of thirteen points on the sphere.

Why it matters: This is a precise extremal geometry problem about spherical packing. The research establishes an optimal arrangement, and the local task searches the same thirteen-point objective.

- [The strong thirteen spheres problem](https://arxiv.org/abs/1002.1439): Main research objective: Determine and prove the optimal arrangement of thirteen nonoverlapping spheres touching a central sphere. Task connection: The paper solves the Tammes problem for thirteen sphere points by a computer-assisted proof. The local task optimizes this same fixed-cardinality arrangement; it is a numerical construction task and does not itself reproduce the proof.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/alphaevolve_math_problems/tammes_problem` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/tammes_problem/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/tammes_problem/initial_program.py (original baseline)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
