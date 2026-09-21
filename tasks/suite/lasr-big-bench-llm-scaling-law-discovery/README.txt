# BIG-Bench LLM scaling-law discovery

**Paper:** Symbolic Regression with a Learned Concept Library (https://arxiv.org/pdf/2409.09359)\
**Task id:** `lasr-big-bench-llm-scaling-law-discovery`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

BIG-Bench LLM scaling-law discovery: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: BIG-Bench LLM scaling-law discovery. Paper metric: exact symbolic recovery / MSE (symbolic regression); scaling-law predictive fit.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `discovery` (tier 1); artifact `equation`, domain `machine_learning`, data `real_measurements`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: BIG-Bench scaling-law discovery needs the BIG-Bench evaluation records.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:BIG-Bench`

## Sources

- paper: https://arxiv.org/pdf/2409.09359 (Sections 4.1–4.5 and Appendix A.4–A.6)
- repository: https://github.com/trishullab/LibraryAugmentedSymbolicRegression.jl/tree/776196e339191736e20d4eb6eed7c468aa6e4472

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
