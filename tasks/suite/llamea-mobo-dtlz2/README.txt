# DTLZ2

**Paper:** LLM-Driven Evolutionary Generation of Multi-Objective Bayesian Optimization Algorithms (https://arxiv.org/pdf/2607.08791)\
**Task id:** `llamea-mobo-dtlz2`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

DTLZ2 task evaluated in LLM-Driven Evolutionary Generation of Multi-Objective Bayesian Optimization Algorithms.

Benchmark named in the paper: pymoo ZDT/DTLZ/WFG and RE engineering suites. Paper metric: normalized hypervolume.

## Candidate interface

class Optimizer: __init__(self, budget, dim, n_obj); __call__(self, problem, bounds) evaluates problem(x) -> objectives (minimize all) at most budget times. Score: hypervolume of the evaluated points normalized by the known Pareto front's hypervolume

Parameters: `{"problem": "dtlz2", "budget": 200}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `continuous_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/pdf/2607.08791 (Section IV.2 and Table 1)
- repository: https://github.com/glatq/LLaMEA-MOO/tree/18861aa47f17905c28aa33c5a9f33df3a893d191 (benchmark_best_codes.py)

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
