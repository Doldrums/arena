# Orienteering ACO

**Paper:** ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution (https://arxiv.org/pdf/2402.01145)\
**Paper:** HSEvo: Elevating Automatic Heuristic Design with Diversity-Driven Harmony Search and Genetic Algorithm Using LLMs (https://arxiv.org/pdf/2412.14995)\
**Task id:** `reevo-orienteering-aco`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Orienteering ACO: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Orienteering ACO. Paper metric: mean collected prize.

## Candidate interface

heuristics(prizes, distance_matrix, max_len) -> matrix of edge attractiveness. Score: mean best collected prize

Parameters: `{"n_instances": 3, "n_nodes": 50, "n_ants": 20, "n_iterations": 30, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate reevo-orienteering-aco --route upstream --paper <paper>`.

- HSEvo: Orienteering ACO (`hsevo-orienteering-aco`; Orienteering ACO, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)

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
- repository: https://github.com/ai4co/reevo/tree/6dce18257da5e11db2d138e417a2fffc5c72d05f (cfg/problem/op_aco.yaml)
- paper: https://arxiv.org/pdf/2412.14995 (Section 5.1 and Appendix A)
- repository: https://github.com/datphamvn/HSEvo/tree/f3afffabc2b458fddf70a42a8678758039671297 (problems/op_aco)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
