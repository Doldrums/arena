# bo_caf

**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Task id:** `mcts-ahd-bo-caf`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

bo_caf task evaluated in Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design.

Benchmark named in the paper: bo_caf. Paper metric: mean absolute optimality gap.

## Candidate interface

acquisition(mu, sigma, f_best, cost) -> one score per candidate point; the loop stops when accumulated cost exceeds the budget (EvolCAF-style; cost(x) = 1 + mean normalized coordinate, a documented stand-in for the paper's cost functions). Score: mean simple regret

Parameters: `{"functions": ["ackley_2d", "rastrigin_2d", "levy_2d", "hartmann_3d"], "budget": 30}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `continuous_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/bo_caf/eval.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
