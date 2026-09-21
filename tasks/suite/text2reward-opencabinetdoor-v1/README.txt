# OpenCabinetDoor-v1

**Paper:** Text2Reward: Reward Shaping with Language Models for Reinforcement Learning (https://arxiv.org/pdf/2309.11489)\
**Task id:** `text2reward-opencabinetdoor-v1`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

OpenCabinetDoor-v1: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: ManiSkill2. Paper metric: success rate.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires a physics simulator or reinforcement-learning training loop (ManiSkill2) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:ManiSkill2`

## Sources

- paper: https://arxiv.org/pdf/2309.11489 (Appendix B Table 5)
- repository: https://github.com/xlang-ai/text2reward/tree/e7f57efcf76b22bbfb7c3eb9d67d98ff2765a926 (run_maniskill/reward_code/zero-shot/OpenCabinetDoor-v1/specific.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- MuJoCo installation is manual per README. Repository shell script lists handle-pull-v2 but corresponding released reward file is absent; it is not included as a paper task (paper lists ten MetaWorld tasks).
- No SPDX license identification verified for https://github.com/xlang-ai/text2reward.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
