# LunarLander-v3

**Paper:** Evolutionary Discovery of Reinforcement Learning Algorithms via Large Language Models (https://arxiv.org/pdf/2603.28416)\
**Task id:** `llm-evolved-rl-algorithms-lunarlander-v3`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

LunarLander-v3 task evaluated in Evolutionary Discovery of Reinforcement Learning Algorithms via Large Language Models.

Benchmark named in the paper: Gymnasium. Paper metric: mean maximum evaluation episodic return across five training seeds.

## Candidate interface

class Agent(observation_space, action_space, seed) with act(observation, explore) and observe(observation, action, reward, next_observation, terminated, truncated). Score: mean evaluation return after a fixed training budget on the Gymnasium task

Parameters: `{"task": "LunarLander-v3"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `machine_learning`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Small CPU training budgets (20k to 40k steps); the papers' multi-million-step runs are not reproduced. MuJoCo tasks need the mujoco package, LunarLander needs gymnasium[box2d].

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:gymnasium`
- `py:Box2D`

## Sources

- paper: https://arxiv.org/pdf/2603.28416 (Section 3; Tables 1, 3 and 4)
- repository: https://github.com/sygkounas/Designing-and-Evolving-New-Reinforcement-Learning-Algorithms-using-Large-Language-models/tree/b69c4edee1dd37a684c75a1c904190e9a66e1995

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- Official GECCO 2026 release pinned; packaging is incomplete (no requirements.txt or license at the pinned commit) and every evaluation is a full RL training run.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
