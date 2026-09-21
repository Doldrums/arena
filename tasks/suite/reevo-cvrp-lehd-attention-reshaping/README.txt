# CVRP LEHD attention reshaping

**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Task id:** `reevo-cvrp-lehd-attention-reshaping`\
**Protocol:** `original`\
**Direction:** minimize\

## Task

CVRP LEHD attention reshaping: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: CVRP LEHD attention reshaping. Paper metric: mean route length.

## Candidate interface

Original CPU protocol, bounded subset. POMO and DPP additionally check feasibility; BO/LEHD remain validity-unverified.

Parameters: `{"checkout": "{checkout}", "problem": "cvrp_lehd", "max_instances": 1}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Plan short delivery routes that serve customer demands without exceeding vehicle capacity.

Why it matters: This problem represents resource and distance constraints in distribution logistics. Research seeks better feasible delivery plans; local synthetic instances are a controlled subproblem rather than measured real-world savings.

- [Hybrid Genetic Search for the CVRP: Open-Source Implementation and SWAP* Neighborhood](https://arxiv.org/abs/2012.10384): Main research objective: Improve feasible low-cost solutions of the capacitated vehicle-routing problem. Task connection: Vidal develops and evaluates an algorithm specifically to solve capacitated vehicle routing. CVRP LEHD attention reshaping has a different candidate interface, but its distance objective and demand/capacity constraints pursue the same logistics problem.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

The paper's pinned evaluator, executed through the repository's upstream adapter (bounded_original_protocol_original_checkpoints). The pinned source is fetched by `python3 run.py setup reevo-cvrp-lehd-attention-reshaping`; data preparation is described in the notes.

- Bounded profile of the paper's evaluator (few instances, CPU); see the adapter kwargs in task.json.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `checkout:ai4co/reevo@6dce18257da5e11db2d138e417a2fffc5c72d05f`
- `py:torch`
- `py:matplotlib`
- `py:tqdm`
- `py:pytz`

## Sources

- paper: https://arxiv.org/pdf/2402.01145 (Sections 5.1–5.5)
- repository: https://github.com/ai4co/reevo/tree/6dce18257da5e11db2d138e417a2fffc5c72d05f (cfg/problem/cvrp_lehd.yaml)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
