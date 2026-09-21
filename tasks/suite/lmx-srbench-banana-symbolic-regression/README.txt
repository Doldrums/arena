# SRBench banana symbolic regression

**Paper:** Language Model Crossover: Variation through Few-Shot Prompting (https://arxiv.org/pdf/2302.12170)\
**Task id:** `lmx-srbench-banana-symbolic-regression`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

SRBench banana symbolic regression: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: SRBench banana symbolic regression. Paper metric: domain-specific fitness / QD score.

## Candidate interface

equation(<inputs>, params: np.ndarray[10]) -> np.ndarray prediction; parameters fitted by BFGS on generated training data. Score: NMSE on generated test data

Parameters: `{"target": "srbench_banana", "seed": 0}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `equation`, domain `natural_science`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

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

- paper: https://arxiv.org/pdf/2302.12170 (Sections 4.1–4.5)
- repository: https://github.com/jal278/lmx/tree/b8fec5dd16451cf7afb6e02ac621b71d5bdfee7f (scripts/symbolic_regression.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
