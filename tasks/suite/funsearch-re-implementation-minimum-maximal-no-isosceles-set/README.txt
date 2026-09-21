# Minimum maximal no-isosceles set

**Paper:** Generative Modeling for Mathematical Discovery (https://arxiv.org/pdf/2503.11061)\
**Task id:** `funsearch-re-implementation-minimum-maximal-no-isosceles-set`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Minimum maximal no-isosceles set task evaluated in Generative Modeling for Mathematical Discovery.

Benchmark named in the paper: Minimum maximal no-isosceles set. Paper metric: maximal set cardinality.

## Candidate interface

construct() -> list of (x, y) grid points in [0, n)^2 forming a maximal no-isosceles set (no further grid point can be added). Score: number of points (lower is better)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

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

- paper: https://arxiv.org/pdf/2503.11061 (Section 4, Figure 12)
- repository: https://github.com/kitft/funsearch/tree/cec37d84b474ea6bbd66f6defad8f5b5758449ff (examples/isosceles.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
