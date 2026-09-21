# Narrow admissible tuple

**Paper:** Generative Modeling for Mathematical Discovery (https://arxiv.org/pdf/2503.11061)\
**Paper:** Monte Carlo Tree Search for Comprehensive Exploration in LLM-Based Automatic Heuristic Design (https://arxiv.org/pdf/2501.08603)\
**Task id:** `funsearch-re-implementation-narrow-admissible-tuple`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Construct the largest admissible tuple within [0, 5000] by selecting a removed residue class for each prime. This is the fixed-diameter maximization formulation actually benchmarked in paper Table 2.

Benchmark named in the paper: Narrow admissible tuple. Paper metric: admissible_tuple_cardinality_at_fixed_diameter_bound.

## Candidate interface

construct() -> list of distinct integers in [0, n] forming an admissible tuple: for every prime p <= len(tuple) some residue class mod p is missed (FunSearch fixed-diameter formulation). Score: tuple size

Parameters: `{"n": 5000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate funsearch-re-implementation-narrow-admissible-tuple --route upstream --paper <paper>`.

- MCTS-AHD: asp_constructive (`mcts-ahd-asp-constructive`; asp_constructive, Pinned official training instances or exact official training generator; see docs/TASKS.md for subset and limits.)

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

- paper: https://arxiv.org/pdf/2503.11061 (Section 3, Tables 1-3)
- repository: https://github.com/kitft/funsearch/tree/cec37d84b474ea6bbd66f6defad8f5b5758449ff (examples/nat_spec.py)
- paper: https://arxiv.org/pdf/2501.08603 (Section 4; Appendices B-D and F)
- repository: https://github.com/zz1358m/MCTS-AHD-master/tree/ee9c4f424503c65a5fd2b899e6620ce86079fedb (problems/asp_constructive/eval.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
