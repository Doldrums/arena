# Decap placement genetic algorithm

**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Task id:** `reevo-decap-placement-genetic-algorithm`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Decap placement genetic algorithm: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Decap placement genetic algorithm. Paper metric: mean physical circuit reward (model5).

## Candidate interface

Original CPU protocol, bounded subset. POMO and DPP additionally check feasibility; BO/LEHD remain validity-unverified.

Parameters: `{"checkout": "{checkout}", "max_instances": 1, "iterations": 1, "population_size": 20, "random_seed": 5678}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

The paper's pinned evaluator, executed through the repository's upstream adapter (bounded_original_solver_reconstructed_dataset_transport). The pinned source is fetched by `python3 run.py setup reevo-decap-placement-genetic-algorithm`; data preparation is described in the notes.

- Bounded profile of the paper's evaluator (few instances, CPU); see the adapter kwargs in task.json.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `checkout:ai4co/reevo@6dce18257da5e11db2d138e417a2fffc5c72d05f`
- `py:tqdm`
- `py:torch`

## Sources

- paper: https://arxiv.org/pdf/2402.01145 (Sections 5.1–5.5)
- repository: https://github.com/ai4co/reevo/tree/6dce18257da5e11db2d138e417a2fffc5c72d05f (cfg/problem/dpp_ga.yaml)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
