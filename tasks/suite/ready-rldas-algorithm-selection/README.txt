# RLDAS algorithm selection

**Paper:** READY: Reward Discovery for Meta-Black-Box Optimization (https://arxiv.org/pdf/2601.21847)\
**Task id:** `ready-rldas-algorithm-selection`\
**Protocol:** `unsupported`\
**Direction:** minimize\

## Task

RLDAS algorithm selection task evaluated in READY: Reward Discovery for Meta-Black-Box Optimization.

Benchmark named in the paper: BBOB. Paper metric: BBOB final objective cost.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `method` (tier 2); artifact `reward`, domain `continuous_optimisation`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires the BBOB data and training pipeline, which are not redistributed with the suite.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:BBOB`

## Sources

- paper: https://arxiv.org/pdf/2601.21847 (Sections 4.1 and 4.4)

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
