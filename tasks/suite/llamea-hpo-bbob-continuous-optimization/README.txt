# BBOB continuous optimization

**Paper:** In-the-loop Hyper-Parameter Optimization for LLM-Based Automated Design of Heuristics (https://arxiv.org/pdf/2410.16309)\
**Task id:** `llamea-hpo-bbob-continuous-optimization`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

BBOB continuous optimization: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: BBOB continuous optimization. Paper metric: normalized AOCC.

## Candidate interface

class Optimizer: __init__(self, budget, dim); __call__(self, func) evaluates func(x) at most budget times within [-5, 5]^dim (LLaMEA contract). Score: mean area over the log convergence curve (AOCC) over instances

Parameters: `{"fids": [1, 3, 8, 15, 21], "dim": 5, "budget": 300}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `continuous_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- LLaMEA-HPO aggregates over all 24 BBOB functions; this suite uses a five-function subset for tractable evaluation.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/pdf/2410.16309 (Sections 4.1–4.3)
- archive: https://zenodo.org/api/records/14917719/files/LLaMEA-HPO.zip/content (run_BBOB_HPO.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Exact paper archive, three entrypoint scripts and lockfile were inspected; API-funded searches and benchmark outcomes were not executed or reproduced.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
