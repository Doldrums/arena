# Hopper Front Flip

**Paper:** Text2Reward: Reward Shaping with Language Models for Reinforcement Learning (https://arxiv.org/pdf/2309.11489)\
**Task id:** `text2reward-hopper-front-flip`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Hopper Front Flip: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Gym MuJoCo. Paper metric: task success rate.

## Candidate interface

reward(observation, action, next_observation, info) -> float, the shaped reward used to train a policy on the Gymnasium environment named in the task (info carries the environment's step info such as x_velocity). The evaluator trains a linear Gaussian policy with the cross-entropy method (6 iterations x 16 candidates, 200-step episodes) under the candidate reward and reports the task's own fitness (see README) on 5 evaluation episodes. Higher is better.

Parameters: `{"task": "hopper_front_flip", "seed": 0}`

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Gymnasium Hopper-v5; fitness is torso rotations in the negative angle direction.
- The paper's simulator (Isaac Gym, Bi-DexHands, custom humanoids, ManiSkill2 or a real robot) is replaced by the closest Gymnasium MuJoCo environment and the RL training by a small CEM budget; the fitness definitions are local proxies of the papers' success criteria and scores are comparable within the suite only.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:gymnasium`
- `py:mujoco`

## Sources

- paper: https://arxiv.org/pdf/2309.11489 (Appendix B Table 6)
- repository: https://github.com/xlang-ai/text2reward/tree/e7f57efcf76b22bbfb7c3eb9d67d98ff2765a926 (code_generation/single_flow/classlike_prompt/HopperPrompt.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- MuJoCo installation is manual per README. Repository shell script lists handle-pull-v2 but corresponding released reward file is absent; it is not included as a paper task (paper lists ten MetaWorld tasks).
- No SPDX license identification verified for https://github.com/xlang-ai/text2reward.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
