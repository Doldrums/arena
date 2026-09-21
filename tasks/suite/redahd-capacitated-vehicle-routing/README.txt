# Capacitated vehicle routing

**Paper:** RedAHD: Reduction-Based End-to-End Automatic Heuristic Design with Large Language Models (https://arxiv.org/pdf/2505.20242)\
**Paper:** A2DEPT: Large Language Model-Driven Automated Algorithm Design via Evolutionary Program Trees (https://arxiv.org/pdf/2604.24043)\
**Paper:** From Understanding to Excelling: Template-Free Algorithm Design through Structural-Functional Co-Evolution (https://arxiv.org/pdf/2503.10721)\
**Paper:** DGA2D: Directed Graph-Guided Automated Algorithm Design with Large Language Models (https://arxiv.org/pdf/2608.00700)\
**Paper:** EoH-S: Evolution of Heuristic Set using LLMs for Automated Heuristic Design (https://arxiv.org/pdf/2508.03082)\
**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Task id:** `redahd-capacitated-vehicle-routing`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Capacitated vehicle routing: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: MCTS-AHD evaluation datasets. Paper metric: objective value / gap to optimum (problem dependent).

## Candidate interface

select_next_node(current_node, depot, unvisited_nodes, rest_capacity, demands, distance_matrix) -> int; return 0 (depot) to close a route. Score: mean total route length

Parameters: `{"n_instances": 8, "n_customers": 50, "capacity": 50, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Plan short delivery routes that serve customer demands without exceeding vehicle capacity.

Why it matters: This problem represents resource and distance constraints in distribution logistics. Research seeks better feasible delivery plans; local synthetic instances are a controlled subproblem rather than measured real-world savings.

- [Hybrid Genetic Search for the CVRP: Open-Source Implementation and SWAP* Neighborhood](https://arxiv.org/abs/2012.10384): Main research objective: Improve feasible low-cost solutions of the capacitated vehicle-routing problem. Task connection: Vidal develops and evaluates an algorithm specifically to solve capacitated vehicle routing. Capacitated vehicle routing has a different candidate interface, but its distance objective and demand/capacity constraints pursue the same logistics problem.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate redahd-capacitated-vehicle-routing --route upstream --paper <paper>`.

- A2DEPT: Capacitated Vehicle Routing (`a2dept-capacitated-vehicle-routing`; FrontierCO and high-constraint extensions, CVRPLib Golden/Arnold; 20 instances, 200–483 customers)
- CAE: Capacitated Vehicle Routing Problem (`cae-capacitated-vehicle-routing-problem`; TSPLIB/CVRP instances)
- DGA2D: Capacitated Vehicle Routing (`dga2d-capacitated-vehicle-routing`)
- EoH-S: Capacitated Vehicle Routing Problem (`eoh-s-capacitated-vehicle-routing-problem`; BPPLib / TSPLIB / CVRPLIB)
- A2DEPT, ReEvo: Capacitated vehicle routing (`reference-cvrp`; Generated locally with documented seed.)

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
- paper: https://arxiv.org/pdf/2604.24043 (Section 4; Appendix D Table 5)
- paper: https://arxiv.org/pdf/2503.10721 (Section 4.1, Table 1)
- paper: https://arxiv.org/pdf/2608.00700 (Section 4.1; Appendices E and F)
- paper: https://arxiv.org/pdf/2508.03082 (Section 4, Tables 1-3)
- repository: https://github.com/FeiLiu36/EoH-S/tree/8310b056ab0d4ea83d194f1d9e8c7873c0a3b892
- paper: https://arxiv.org/pdf/2402.01145 (Problem family; original benchmark protocol is not claimed.)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
