# Traveling salesman GLS

**Paper:** Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model (https://arxiv.org/pdf/2401.02051)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** HSEvo: Elevating Automatic Heuristic Design with Diversity-Driven Harmony Search and Genetic Algorithm Using LLMs (https://arxiv.org/pdf/2412.14995)\
**Paper:** In-the-loop Hyper-Parameter Optimization for LLM-Based Automated Design of Heuristics (https://arxiv.org/pdf/2410.16309)\
**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Task id:** `eoh-traveling-salesman-gls`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Traveling salesman GLS: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Traveling salesman GLS. Paper metric: mean optimality gap (%).

## Candidate interface

update_edge_distance(edge_distance, local_opt_tour, edge_n_used) -> np.ndarray: perturbed distance matrix that guides the next 2-opt pass (EoH tsp_gls contract). Score: mean best tour length

Parameters: `{"n_instances": 3, "n_nodes": 100, "iterations": 20, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize the length of a tour that visits each location once and returns to its start.

Why it matters: Shorter feasible tours address routing, inspection and manufacturing movement costs. The local instances are bounded algorithmic studies of that operations-research objective, not evidence of a deployed logistics improvement.

- [An effective implementation of the Lin–Kernighan traveling salesman heuristic](https://doi.org/10.1016/S0377-2217(99)00284-2): Main research objective: Compute optimal or near-optimal traveling-salesman tours efficiently. Task connection: Helsgaun develops a solver whose central goal is shorter symmetric TSP tours. Traveling salesman GLS uses its own construction, search, or attention interface and instance distribution while optimizing that same feasible-tour objective.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate eoh-traveling-salesman-gls --route upstream --paper <paper>`.

- CodeEvolve: Traveling salesman guided local search (`codeevolve-traveling-salesman-guided-local-search`; EoH)
- HSEvo: Traveling salesman GLS (`hsevo-traveling-salesman-gls`; Traveling salesman GLS, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- LLaMEA-HPO: Traveling salesman GLS (`llamea-hpo-traveling-salesman-gls`; Traveling salesman GLS, 64 TSP100 instances during search; paper final evaluation uses 1000 instances each of TSP20/TSP50/TSP100 plus Euclidean TSPLIB problems)
- MCTS-AHD: tsp_gls (`mcts-ahd-tsp-gls`; tsp_gls, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)
- ReEvo: TSP GLS (`reevo-tsp-gls`; TSP GLS, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)

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

- paper: https://arxiv.org/pdf/2401.02051 (Section 4 and Appendices B–D)
- repository: https://github.com/FeiLiu36/EoH/tree/472545785c936dcfc863d2bc0d6109cf23c7ce62 (examples/tsp_gls/evaluation/runEval.py)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.2)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/eoh-problems/tsp_gls/input)
- paper: https://arxiv.org/pdf/2412.14995 (Section 5.1 and Appendix A)
- repository: https://github.com/datphamvn/HSEvo/tree/f3afffabc2b458fddf70a42a8678758039671297 (problems/tsp_gls)
- paper: https://arxiv.org/pdf/2410.16309 (Sections 4.1–4.3)
- archive: https://zenodo.org/api/records/14917719/files/LLaMEA-HPO.zip/content (run_TSP_HPO.py)
- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/tsp_gls/eval.py)
- paper: https://arxiv.org/pdf/2402.01145 (Sections 5.1–5.5)
- repository: https://github.com/ai4co/reevo/tree/6dce18257da5e11db2d138e417a2fffc5c72d05f (cfg/problem/tsp_gls.yaml)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
