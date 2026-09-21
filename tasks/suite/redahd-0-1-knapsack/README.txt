# 0/1 knapsack

**Paper:** RedAHD: Reduction-Based End-to-End Automatic Heuristic Design with Large Language Models (https://arxiv.org/pdf/2505.20242)\
**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Paper:** A2DEPT: Large Language Model-Driven Automated Algorithm Design via Evolutionary Program Trees (https://arxiv.org/pdf/2604.24043)\
**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Task id:** `redahd-0-1-knapsack`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

0/1 knapsack: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: MCTS-AHD evaluation datasets. Paper metric: objective value / gap to optimum (problem dependent).

## Candidate interface

select_next_item(remaining_capacity, remaining_weights, remaining_values) -> index into the remaining (feasible) arrays, or -1 to stop. Score: mean total value

Parameters: `{"n_instances": 8, "n_items": 100, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate redahd-0-1-knapsack --route upstream --paper <paper>`.

- MCTS-AHD: kp_constructive (`mcts-ahd-kp-constructive`; kp_constructive, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- A2DEPT, ReEvo: Zero-one knapsack (`reference-knapsack`; Generated locally with documented seed.)

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

- paper: https://arxiv.org/pdf/2505.20242 (Section 5.1 and Appendix C)
- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/kp_constructive/eval.py)
- paper: https://arxiv.org/pdf/2604.24043 (Problem family; original benchmark protocol is not claimed.)
- paper: https://arxiv.org/pdf/2402.01145 (Problem family; original benchmark protocol is not claimed.)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
