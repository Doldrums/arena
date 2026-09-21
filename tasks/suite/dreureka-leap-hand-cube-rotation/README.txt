# LEAP Hand cube rotation

**Paper:** DrEureka: Language Model Guided Sim-To-Real Transfer (https://arxiv.org/pdf/2406.01967)\
**Task id:** `dreureka-leap-hand-cube-rotation`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

LEAP Hand cube rotation: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: LEAP Hand cube rotation. Paper metric: forward velocity/distance, cube rotations, or balance duration.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires a physics simulator or reinforcement-learning training loop (LEAP Hand cube rotation) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:LEAP Hand cube rotation`

## Sources

- paper: https://arxiv.org/pdf/2406.01967 (Sections 4–6)
- repository: https://github.com/eureka-research/DrEureka/tree/1d4e00700423170717654516f4ef4b24cb0f3a84

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
