# Autonomous driving

**Paper:** REvolve: Reward Evolution with Large Language Models using Human Feedback (https://arxiv.org/pdf/2406.01309)\
**Task id:** `revolve-autonomous-driving`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Autonomous driving: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: AirSim. Paper metric: human preference Elo and task fitness.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires a physics simulator or reinforcement-learning training loop (AirSim) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:AirSim`

## Sources

- paper: https://arxiv.org/pdf/2406.01309 (Section 5.1, Table 1, Appendix A)
- repository: https://github.com/RishiHazra/Revolve/tree/eee636b5dba141bf00cf0ff47852c2a9125dc5d2 (main.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
