# jigsaw-toxic-comment

**Paper:** EurekAgent: Agent Environment Engineering is All You Need For Autonomous Scientific Discovery (https://arxiv.org/pdf/2606.13662)\
**Task id:** `eurekagent-jigsaw-toxic-comment`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

jigsaw-toxic-comment

Benchmark named in the paper: MLE-Bench Lite. Paper metric: competition score and medal threshold.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `model`, domain `machine_learning`, data `undistributed`, verification `none`, reference `none`, resources `gpu, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: MLE-bench competitions require the Kaggle data and model training; neither is redistributed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:MLE-bench`
- `hardware:gpu`

## Sources

- paper: https://arxiv.org/pdf/2606.13662 (Appendix B)
- repository: https://github.com/THU-Team-Eureka/EurekAgent/tree/fb96df897dfb99797a77623aa0dd9ee178fe89d2

## Limitations

- Task appears in the paper MLE evaluation but no corresponding dataset wrapper, run config or evaluator package is present in the pinned public EurekAgent repository.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
