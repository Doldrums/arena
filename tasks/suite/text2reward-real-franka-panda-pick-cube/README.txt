# Real Franka Panda Pick Cube

**Paper:** Text2Reward: Reward Shaping with Language Models for Reinforcement Learning (https://arxiv.org/pdf/2309.11489)\
**Task id:** `text2reward-real-franka-panda-pick-cube`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Real Franka Panda Pick Cube: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Real Franka Panda Pick Cube. Paper metric: physical task success.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires a physics simulator or reinforcement-learning training loop (Real Franka Panda Pick Cube) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:Real Franka Panda Pick Cube`

## Sources

- paper: https://arxiv.org/pdf/2309.11489 (Real Robot Experiments)
- repository: https://github.com/xlang-ai/text2reward/tree/e7f57efcf76b22bbfb7c3eb9d67d98ff2765a926

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- MuJoCo installation is manual per README. Repository shell script lists handle-pull-v2 but corresponding released reward file is absent; it is not included as a paper task (paper lists ten MetaWorld tasks).
- No SPDX license identification verified for https://github.com/xlang-ai/text2reward.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
