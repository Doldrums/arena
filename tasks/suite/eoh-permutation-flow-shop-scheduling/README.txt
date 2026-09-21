# Permutation flow shop scheduling

**Paper:** Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model (https://arxiv.org/pdf/2401.02051)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** DGA2D: Directed Graph-Guided Automated Algorithm Design with Large Language Models (https://arxiv.org/pdf/2608.00700)\
**Paper:** A2DEPT: Large Language Model-Driven Automated Algorithm Design via Evolutionary Program Trees (https://arxiv.org/pdf/2604.24043)\
**Task id:** `eoh-permutation-flow-shop-scheduling`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Permutation flow shop scheduling: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Permutation flow shop scheduling. Paper metric: mean makespan.

## Candidate interface

order_jobs(processing_times: np.ndarray[jobs, machines]) -> permutation of job indices. Score: mean makespan

Parameters: `{"n_instances": 5, "n_jobs": 50, "n_machines": 10, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate eoh-permutation-flow-shop-scheduling --route upstream --paper <paper>`.

- CodeEvolve: Flow shop guided local search (`codeevolve-flow-shop-guided-local-search`; EoH)
- DGA2D: Flow-Shop Scheduling (`dga2d-flow-shop-scheduling`)
- EoH, A2DEPT: Permutation flow-shop scheduling (`reference-flow-shop`; Generated locally with documented seed.)

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
- repository: https://github.com/FeiLiu36/EoH/tree/472545785c936dcfc863d2bc0d6109cf23c7ce62 (examples/fssp_gls/evaluation/runEval.py)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.2)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/eoh-problems/fssp_gls/input)
- paper: https://arxiv.org/pdf/2608.00700 (Section 4.1; Appendices E and F)
- paper: https://arxiv.org/pdf/2604.24043 (Problem family; original benchmark protocol is not claimed.)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
