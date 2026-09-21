# BBOB f1

**Paper:** LLaMEA-BO: A Large Language Model Evolutionary Algorithm for Automatically Generating Bayesian Optimization Algorithms (https://arxiv.org/pdf/2505.21034)\
**Task id:** `llamea-bo-bbob-f1`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

BBOB f1 task evaluated in LLaMEA-BO: A Large Language Model Evolutionary Algorithm for Automatically Generating Bayesian Optimization Algorithms.

Benchmark named in the paper: COCO BBOB. Paper metric: mean normalized area over log convergence curve.

## Candidate interface

class Optimizer: __init__(self, budget, dim); __call__(self, func) evaluates func(x) at most budget times within [-5, 5]^dim (LLaMEA contract). Score: mean area over the log convergence curve (AOCC) over instances

Parameters: `{"fid": 1, "dim": 5, "budget": 500}`

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

- paper: https://arxiv.org/pdf/2505.21034 (Section 4, generalization benchmarks)
- repository: https://github.com/Ewendawi/LLaMEA-BO/blob/938b4d780aa0cbf9f7c941ebab61dadfa9157185/llamevol/evaluator/evaluator_result.py (ConvergenceCurveAnalyzer.calculate_aoc; EvaluatorBasicResult.update_aoc)
- benchmark: https://pypi.org/project/ioh/0.3.18/ (Pinned IOH BBOB objective implementation)
- repository: https://github.com/Ewendawi/LLaMEA-BO/tree/938b4d780aa0cbf9f7c941ebab61dadfa9157185 (llamevol/evaluator/ioh_evaluator.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
