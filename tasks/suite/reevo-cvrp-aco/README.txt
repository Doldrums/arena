# CVRP ACO

**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Task id:** `reevo-cvrp-aco`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

CVRP ACO: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: CVRP ACO. Paper metric: mean route length.

## Candidate interface

heuristics(distance_matrix, coordinates, demands, capacity) -> matrix of edge attractiveness. Score: mean best CVRP cost found by ant colony optimization

Parameters: `{"n_instances": 3, "n_customers": 50, "capacity": 50, "n_ants": 20, "n_iterations": 30, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Plan short delivery routes that serve customer demands without exceeding vehicle capacity.

Why it matters: This problem represents resource and distance constraints in distribution logistics. Research seeks better feasible delivery plans; local synthetic instances are a controlled subproblem rather than measured real-world savings.

- [Hybrid Genetic Search for the CVRP: Open-Source Implementation and SWAP* Neighborhood](https://arxiv.org/abs/2012.10384): Main research objective: Improve feasible low-cost solutions of the capacitated vehicle-routing problem. Task connection: Vidal develops and evaluates an algorithm specifically to solve capacitated vehicle routing. CVRP ACO has a different candidate interface, but its distance objective and demand/capacity constraints pursue the same logistics problem.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate reevo-cvrp-aco --route upstream --paper <paper>`.

- MCTS-AHD: cvrp_aco (`mcts-ahd-cvrp-aco`; cvrp_aco, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- MCTS-AHD: cvrp_aco_black_box (`mcts-ahd-cvrp-aco-black-box`; cvrp_aco_black_box, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)

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
- repository: https://github.com/ai4co/reevo/tree/6dce18257da5e11db2d138e417a2fffc5c72d05f (cfg/problem/cvrp_aco.yaml)
- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/cvrp_aco/eval.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
