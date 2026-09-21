# Multiple knapsack ACO

**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Paper:** RedAHD: Reduction-Based End-to-End Automatic Heuristic Design with Large Language Models (https://arxiv.org/pdf/2505.20242)\
**Task id:** `reevo-multiple-knapsack-aco`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Multiple knapsack ACO: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Multiple knapsack ACO. Paper metric: mean total prize.

## Candidate interface

heuristics(prizes, weights) -> one attractiveness score per item (weights has shape (constraints, items)). Score: mean best total prize

Parameters: `{"n_instances": 3, "n_items": 100, "n_constraints": 5, "n_ants": 20, "n_iterations": 30, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate reevo-multiple-knapsack-aco --route upstream --paper <paper>`.

- MCTS-AHD: mkp_aco (`mcts-ahd-mkp-aco`; mkp_aco, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- MCTS-AHD: mkp_aco_black_box (`mcts-ahd-mkp-aco-black-box`; mkp_aco_black_box, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- RedAHD: Multiple knapsack (`redahd-multiple-knapsack`; MCTS-AHD evaluation datasets, MCTS-AHD evaluation datasets)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2402.01145 (Sections 5.1–5.5)
- repository: https://github.com/ai4co/reevo/tree/6dce18257da5e11db2d138e417a2fffc5c72d05f (cfg/problem/mkp_aco.yaml)
- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/mkp_aco/eval.py)
- paper: https://arxiv.org/pdf/2505.20242 (Section 5.1 and Appendix C)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
