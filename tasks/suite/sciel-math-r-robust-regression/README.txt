# SCiEL: Robust regression in R

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-r-robust-regression`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Evaluate an R main() function on four intended synthetic regression cases with outlier fractions 0, 0.1, 0.2 and 0.15. The pinned evaluator has broken CSV path interpolation.

Benchmark named in the paper: SCiEL source example r_robust_regression. Paper metric: score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `numerical_computing`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/r_robust_regression` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- Imports openevolve.evaluation_result; suite/_lib/openevolve is a verbatim shim of that module.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `bin:Rscript`
- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/r_robust_regression/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/r_robust_regression/initial_program.r (original baseline)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- A separately labeled repository adapter repairs original CSV transport. The original source is retained and verified before the repair is applied.
- The original score trusts candidate-provided metrics; no independent validity boolean exists.
