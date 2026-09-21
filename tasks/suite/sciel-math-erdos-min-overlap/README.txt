# SCiEL: Erdős minimum overlap

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-erdos-min-overlap`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Construct a discretized function and its reported overlap constant c5; minimize the original evaluator’s overlap bound.

Benchmark named in the paper: SCiEL source example erdos_min_overlap. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound Erdős' minimum-overlap constant for a set and translations of its complement.

Why it matters: Determining this extremal constant advances a named problem in combinatorial number theory and analysis. The task seeks explicit feasible constructions relevant to its upper bound.

- [Erdős' minimum overlap problem](https://arxiv.org/abs/2201.05704): Main research objective: Improve rigorous bounds on Erdős' minimum-overlap problem. Task connection: White develops a stronger lower bound for the same minimum-overlap constant. The local task instead searches bounded step-function constructions yielding upper bounds; both address the constant itself, and this paper is not claimed to supply the local construction.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/alphaevolve_math_problems/erdos_min_overlap` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:jax`
- `py:numpy`
- `py:optax`
- `py:tqdm`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/erdos_min_overlap/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/erdos_min_overlap/initial_program.py (original baseline)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
