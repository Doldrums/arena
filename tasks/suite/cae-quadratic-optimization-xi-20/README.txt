# Quadratic optimization xi=20

**Paper:** From Understanding to Excelling: Template-Free Algorithm Design through Structural-Functional Co-Evolution (https://arxiv.org/pdf/2503.10721)\
**Task id:** `cae-quadratic-optimization-xi-20`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Quadratic optimization xi=20 task evaluated in From Understanding to Excelling: Template-Free Algorithm Design through Structural-Functional Co-Evolution.

Benchmark named in the paper: Quadratic optimization xi=20. Paper metric: relative objective error.

## Candidate interface

optimize(Q, c, bounds, objective) -> x in the box minimizing 0.5 x'Qx + c'x (Q symmetric, possibly indefinite); objective(x) counts evaluations. Score: mean objective value

Parameters: `{"n_instances": 5, "dim": 20, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2503.10721 (Section 4.3)

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
