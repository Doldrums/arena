# OneMax binary strings

**Paper:** Language Model Crossover: Variation through Few-Shot Prompting (https://arxiv.org/pdf/2302.12170)\
**Task id:** `lmx-onemax-binary-strings`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

OneMax binary strings: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: OneMax binary strings. Paper metric: domain-specific fitness / QD score.

## Candidate interface

construct() -> binary string of length n. Score: number of ones (LMX OneMax genotype task)

Parameters: `{"n": 100}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

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

## Sources

- paper: https://arxiv.org/pdf/2302.12170 (Sections 4.1–4.5)
- repository: https://github.com/jal278/lmx/tree/b8fec5dd16451cf7afb6e02ac621b71d5bdfee7f (scripts/binary_strings.ipynb)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
