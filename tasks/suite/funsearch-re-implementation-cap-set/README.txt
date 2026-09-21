# Cap set

**Paper:** Generative Modeling for Mathematical Discovery (https://arxiv.org/pdf/2503.11061)\
**Task id:** `funsearch-re-implementation-cap-set`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Cap set task evaluated in Generative Modeling for Mathematical Discovery.

Benchmark named in the paper: Cap set. Paper metric: cap set cardinality.

## Candidate interface

priority(vector: tuple, n: int) -> float; vectors of {0,1,2}^n are added greedily in descending priority when they keep the set a cap set (FunSearch contract). Score: cap set size

Parameters: `{"n": 8}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct large subsets of F₃ⁿ without nontrivial three-term arithmetic progressions.

Why it matters: Explicit cap sets establish lower bounds in additive combinatorics and clarify the possible density of progression-free sets. The local eight-dimensional construction contributes a finite instance of this mathematical question.

- [New Lower Bounds for Cap Sets](https://arxiv.org/abs/2209.10045): Main research objective: Improve lower bounds on the largest cap sets through new constructions. Task connection: Tyrrell constructs larger cap sets to improve mathematical lower bounds. This task searches F₃⁸ using a greedy priority rule; the finite dimension and search mechanism are local restrictions of the same cap-set construction objective.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate funsearch-re-implementation-cap-set --route upstream --paper <paper>`.

- FunSearch re-implementation: Cap set in F3^8 (`reference-cap-set-8`; Generated locally with documented seed.)

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
- repository: https://github.com/kitft/funsearch/tree/cec37d84b474ea6bbd66f6defad8f5b5758449ff (examples/cap_set_spec.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
