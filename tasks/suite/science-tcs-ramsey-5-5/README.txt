# Ramsey graphs for R(5,5): large graphs with no K5 and no independent 5-set

**Source collection:** [Theoretical computer science: source-based research tasks](../../papers/science-tcs.md)\
**Task id:** `science-tcs-ramsey-5-5`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Construct a graph on as many vertices as possible with no clique of size 5 and no independent set of size 5. Every such graph on n vertices proves R(5,5) > n. The best known construction is Exoo's 42-vertex graph (R(5,5) >= 43) and Angeltveit and McKay proved R(5,5) <= 46, so the exact value is open. The seed is the Paley graph on 37 vertices, verified (5,5)-free by the evaluator.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> (n, edges): the number of vertices and a list of (i, j) pairs with 0 <= i < j < n. The graph must contain no clique of size CLIQUE and no independent set of size INDEPENDENT; n must be at most MAX_VERTICES. Score: n, maximized (each valid graph proves R(CLIQUE, INDEPENDENT) > n).

Parameters: `{"clique": 5, "independent": 5, "max_vertices": 45}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the diagonal Ramsey number R(5,5) through graphs avoiding both five-cliques and five-vertex independent sets.

Why it matters: Determining bounds on R(5,5) is the primary extremal graph-theory problem in the cited proof.

- [R(5,5) ≤ 46](https://arxiv.org/abs/2409.15709): Main research objective: Prove an improved upper bound on the diagonal Ramsey number R(5,5). Task connection: The local task constructs valid graphs to obtain lower bounds on the same number. It studies the complementary construction direction and cannot reproduce the paper's upper-bound proof or certify optimality from a valid submission alone.

The evidence concerns the same named mathematical quantity. The distinction between lower-bound constructions and an upper-bound theorem is explicit.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Exact bitset clique search over the graph and its complement. Exoo's 42-vertex construction is not embedded; a graph on 43 or more vertices would refute the conjecture R(5,5) = 43 and must be verified independently. Graphs on 46 or more vertices are rejected (R(5,5) <= 46).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/abs/2409.15709 (Angeltveit and McKay, R(5,5) <= 46: the current upper bound and a summary of the lower bound 43 (Exoo 1989).)
- benchmark: https://www.cs.rit.edu/~spr/ElJC/sur.pdf (Radziszowski, Small Ramsey Numbers (dynamic survey): R(5,5) bounds 43..46.)

## Limitations

- Exoo's 42-vertex graph is not embedded; the evaluator only certifies candidate graphs, so the reference label is none.
- A valid graph on 43 or more vertices would refute the conjecture R(5,5) = 43 and must be independently verified.
