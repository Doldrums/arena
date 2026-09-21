# EoB-UAV surrogate benchmark synthesis

**Paper:** Evolution of Benchmark: Black-Box Optimization Benchmark Design through Large Language Model (https://arxiv.org/pdf/2601.21877)\
**Task id:** `eob-eob-uav-surrogate-benchmark-synthesis`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

EoB-UAV surrogate benchmark synthesis

Benchmark named in the paper: COCO-BBOB / MetaBox. Paper metric: landscape similarity and algorithm distinction capability.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `continuous_optimisation`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires the COCO-BBOB / MetaBox data and training pipeline, which are not redistributed with the suite.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:COCO-BBOB / MetaBox`

## Sources

- paper: https://arxiv.org/pdf/2601.21877 (Section 4.1–4.3)
- repository: https://github.com/MetaEvo/EoB/tree/5d9f30cb19a0231a74f58d17926cff828db6857f

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Paper-provided anonymous code URL https://anonymous.4open.science/r/EoB could not be read: web tool inaccessible; direct HTTPS connection reset. No downloadable artifact verified.
- Official EoB release pinned; the search needs a DeepSeek-compatible API key in config.py and PyTorch; the LSI/ADC scoring of evolved functions runs inside the search loop.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
