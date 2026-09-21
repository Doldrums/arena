# Snake-in-the-box in the 9-dimensional hypercube

**Source collection:** [Theoretical computer science: source-based research tasks](../../papers/science-tcs.md)\
**Task id:** `science-tcs-snake-in-the-box-9`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Construct the longest induced path (snake) in the hypercube Q_9: a sequence of distinct 9-bit vertices in which consecutive vertices differ in one bit and non-consecutive vertices differ in at least two bits. The exact maximum is known only up to dimension 8 (98 in Q_8); in dimension 9 the best known snakes had length 190 before 2026 and were improved in arXiv:2607.15270, so the problem is open. The seed is a greedy snake of length 104.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of distinct integers in [0, 2**N): the vertices of an induced path in the hypercube Q_N in order. Consecutive vertices differ in exactly one bit; non-consecutive vertices differ in at least two bits. Score: number of edges, maximized.

Parameters: `{"n": 9}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct the longest possible induced path in the nine-dimensional hypercube.

Why it matters: Extending induced hypercube paths, including dimension nine, is the direct mathematical construction goal of the paper.

- [A Census of New Snake-in-the-Box Records](https://arxiv.org/abs/2607.15270): Main research objective: Construct and verify longer induced paths in hypercubes across dimensions nine through thirteen. Task connection: The local task is the same dimension-nine induced-path problem with an exact verifier. Its stored baseline and evaluation budget are local choices and should not be interpreted as the latest record or a proof of optimality.

The reported scientific product is improved mathematical constructions, rather than simply an agent-performance comparison.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Exact verifier of the snake (induced path) property; no record construction is embedded. Reference lengths come from the literature: a(8) = 98 is exact, dimension 9 is open (at least 190 before 2026, improved by arXiv:2607.15270).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/abs/1603.05119 (Allison and Paulusma, New bounds for the snake-in-the-box problem: definitions, exact values up to dimension 8 (a(8)=98) and lower bounds.)
- paper: https://arxiv.org/abs/2607.15270 (A census of new snake-in-the-box records (2026): longer snakes in dimensions 9 to 13 than previously known.)
- benchmark: https://en.wikipedia.org/wiki/Snake-in-the-box (Summary of known snake and coil lengths by dimension, inspected 2026-09-20.)

## Limitations

- The evaluator checks the snake property exactly; it does not embed a record construction, so the reference label is none.
- A snake longer than the current published record would be a new result and must be compared with the 2026 census.
