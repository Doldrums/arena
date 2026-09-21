# Traveling salesman constructive heuristic

**Paper:** Algorithm Evolution Using Large Language Model (https://arxiv.org/pdf/2311.15249)\
**Paper:** From Understanding to Excelling: Template-Free Algorithm Design through Structural-Functional Co-Evolution (https://arxiv.org/pdf/2503.10721)\
**Paper:** DGA2D: Directed Graph-Guided Automated Algorithm Design with Large Language Models (https://arxiv.org/pdf/2608.00700)\
**Paper:** EoH-S: Evolution of Heuristic Set using LLMs for Automated Heuristic Design (https://arxiv.org/pdf/2508.03082)\
**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Paper:** Multi-objective Evolution of Heuristic Using Large Language Model (https://arxiv.org/pdf/2409.16867)\
**Paper:** RedAHD: Reduction-Based End-to-End Automatic Heuristic Design with Large Language Models (https://arxiv.org/pdf/2505.20242)\
**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Paper:** Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model (https://arxiv.org/pdf/2401.02051)\
**Task id:** `ael-traveling-salesman-constructive-heuristic`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Traveling salesman constructive heuristic: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Traveling salesman constructive heuristic. Paper metric: tour-length gap to optimum.

## Candidate interface

select_next_node(current_node, destination_node, unvisited_nodes: np.ndarray, distance_matrix: np.ndarray) -> int (EoH/LLM4AD contract). Score: mean tour length over generated Euclidean instances

Parameters: `{"n_instances": 8, "n_nodes": 50, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize the length of a tour that visits each location once and returns to its start.

Why it matters: Shorter feasible tours address routing, inspection and manufacturing movement costs. The local instances are bounded algorithmic studies of that operations-research objective, not evidence of a deployed logistics improvement.

- [An effective implementation of the Lin–Kernighan traveling salesman heuristic](https://doi.org/10.1016/S0377-2217(99)00284-2): Main research objective: Compute optimal or near-optimal traveling-salesman tours efficiently. Task connection: Helsgaun develops a solver whose central goal is shorter symmetric TSP tours. Traveling salesman constructive heuristic uses its own construction, search, or attention interface and instance distribution while optimizing that same feasible-tour objective.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate ael-traveling-salesman-constructive-heuristic --route upstream --paper <paper>`.

- CAE: Traveling Salesman Problem (`cae-traveling-salesman-problem`; TSPLIB/CVRP instances)
- DGA2D: Traveling Salesman (`dga2d-traveling-salesman`)
- EoH-S: Traveling Salesman Problem (`eoh-s-traveling-salesman-problem`; BPPLib / TSPLIB / CVRPLIB)
- MCTS-AHD: tsp_constructive (`mcts-ahd-tsp-constructive`; tsp_constructive, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- MEoH: Traveling Salesman Problem (`meoh-traveling-salesman-problem`; Traveling Salesman Problem)
- RedAHD: Traveling salesman problem (`redahd-traveling-salesman-problem`; MCTS-AHD evaluation datasets, MCTS-AHD evaluation datasets)
- ReEvo: TSP constructive heuristic (`reevo-tsp-constructive-heuristic`; TSP constructive heuristic, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- EoH, ReEvo, AEL, MEoH: Euclidean traveling salesperson (`reference-tsp`; Generated locally with documented seed.)

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

- paper: https://arxiv.org/pdf/2311.15249 (Experiments)
- paper: https://arxiv.org/pdf/2503.10721 (Section 4.1, Table 1)
- paper: https://arxiv.org/pdf/2608.00700 (Section 4.1; Appendices E and F)
- paper: https://arxiv.org/pdf/2508.03082 (Section 4, Tables 1-3)
- repository: https://github.com/FeiLiu36/EoH-S/tree/8310b056ab0d4ea83d194f1d9e8c7873c0a3b892
- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/tsp_constructive/eval.py)
- paper: https://arxiv.org/pdf/2409.16867 (Section 4)
- repository: https://github.com/Optima-CityU/LLM4AD/tree/ffb6acf64497be93932c98d25369352efd3865cf (llm4ad/task/optimization/tsp_construct/evaluation.py)
- paper: https://arxiv.org/pdf/2505.20242 (Section 5.1 and Appendix C)
- paper: https://arxiv.org/pdf/2402.01145 (Sections 5.1–5.5)
- repository: https://github.com/ai4co/reevo/tree/6dce18257da5e11db2d138e417a2fffc5c72d05f (cfg/problem/tsp_constructive.yaml)
- paper: https://arxiv.org/pdf/2401.02051 (Problem family; original benchmark protocol is not claimed.)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
