# Feynman equations symbolic regression

**Paper:** Symbolic Regression with a Learned Concept Library (https://arxiv.org/pdf/2409.09359)\
**Task id:** `lasr-feynman-equations-symbolic-regression`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Feynman equations symbolic regression: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Feynman equations symbolic regression. Paper metric: exact symbolic recovery / MSE (symbolic regression); scaling-law predictive fit.

## Candidate interface

fit(X_train: np.ndarray[n, d], y_train) -> predict(X) callable; the candidate is a symbolic-regression algorithm run on every equation of the set. Score: mean held-out NMSE over the equations

Parameters: `{"targets": ["I.6.2a", "I.9.18", "I.12.1", "I.14.3", "I.25.13", "I.29.4", "I.34.27", "II.3.24", "I.27.6", "I.39.1"], "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

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

- paper: https://arxiv.org/pdf/2409.09359 (Sections 4.1–4.5 and Appendix A.4–A.6)
- repository: https://github.com/trishullab/LibraryAugmentedSymbolicRegression.jl/tree/776196e339191736e20d4eb6eed7c468aa6e4472

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
