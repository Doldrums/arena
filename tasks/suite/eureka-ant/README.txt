# Ant

**Paper:** Eureka: Human-Level Reward Design via Coding Large Language Models (https://arxiv.org/pdf/2310.12931)\
**Paper:** DrEureka: Language Model Guided Sim-To-Real Transfer (https://arxiv.org/pdf/2406.01967)\
**Paper:** HyperAgents (https://arxiv.org/pdf/2603.19461)\
**Paper:** Text2Reward: Reward Shaping with Language Models for Reinforcement Learning (https://arxiv.org/pdf/2309.11489)\
**Task id:** `eureka-ant`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Ant: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Isaac Gym. Paper metric: task-specific fitness and human-normalized score.

## Candidate interface

reward(observation, action, next_observation, info) -> float, the shaped reward used to train a policy on the Gymnasium environment named in the task (info carries the environment's step info such as x_velocity). The evaluator trains a linear Gaussian policy with the cross-entropy method (6 iterations x 16 candidates, 200-step episodes) under the candidate reward and reports the task's own fitness (see README) on 5 evaluation episodes. Higher is better.

Parameters: `{"task": "ant_forward", "seed": 0}`

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate eureka-ant --route upstream --paper <paper>`.

- DrEureka: Go1 forward locomotion (`dreureka-go1-forward-locomotion`; Go1 forward locomotion, Go1 forward locomotion)
- HyperAgents: Quadruped walk-forward reward design (`hyperagents-quadruped-walk-forward-reward-design`)
- Text2Reward: Ant Move Forward (`text2reward-ant-move-forward`; Gym MuJoCo, Gym MuJoCo)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Isaac Gym Ant replaced by Gymnasium Ant-v5; fitness is mean forward velocity (the Ant task's objective).
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

- paper: https://arxiv.org/pdf/2310.12931 (Appendix B task table)
- repository: https://github.com/eureka-research/Eureka/tree/9eee42808b52d8abc14845d1547bfde886403ccc (eureka/cfg/env/ant.yaml)
- paper: https://arxiv.org/pdf/2406.01967 (Sections 4–6)
- repository: https://github.com/eureka-research/DrEureka/tree/1d4e00700423170717654516f4ef4b24cb0f3a84 (forward_locomotion)
- paper: https://arxiv.org/pdf/2603.19461 (Section 4 and Appendix C)
- repository: https://github.com/facebookresearch/Hyperagents/tree/59a68f672dfb92c74aeb7e61535d776fb36e172d (domains/genesis)
- paper: https://arxiv.org/pdf/2309.11489 (Appendix B Table 6)
- repository: https://github.com/xlang-ai/text2reward/tree/e7f57efcf76b22bbfb7c3eb9d67d98ff2765a926 (code_generation/single_flow/classlike_prompt/AntPrompt.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Pinned cfg/config.yaml selects historical model gpt-4-0314 and the legacy OpenAI SDK. Configure a compatible available endpoint/model before execution; changing models changes reproduction conditions.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
