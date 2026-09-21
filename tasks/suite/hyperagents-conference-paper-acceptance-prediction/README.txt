# Conference paper acceptance prediction

**Paper:** HyperAgents (https://arxiv.org/pdf/2603.19461)\
**Task id:** `hyperagents-conference-paper-acceptance-prediction`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Conference paper acceptance prediction

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `model`, domain `machine_learning`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires the Conference paper acceptance prediction data and training pipeline, which are not redistributed with the suite.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:Conference paper acceptance prediction`

## Sources

- paper: https://arxiv.org/pdf/2603.19461 (Section 4 and Appendix C)
- repository: https://github.com/facebookresearch/Hyperagents/tree/59a68f672dfb92c74aeb7e61535d776fb36e172d (domains/paper_review)

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
