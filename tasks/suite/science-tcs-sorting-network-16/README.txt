# Size-efficient sorting networks on 16 wires

**Source collection:** [Theoretical computer science: source-based research tasks](../../papers/science-tcs.md)\
**Task id:** `science-tcs-sorting-network-16`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Construct a fixed compare-exchange network that sorts all 16-input sequences using as few comparators as possible. Correctness is certified by the zero-one principle over all 65,536 Boolean inputs. Parallel depth is reported separately. A verified 60-comparator construction is the reference; the initial odd-even transposition network uses 120 comparators.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> ordered list of integer pairs (i, j), 0 <= i < j < N. Each compare-exchange writes min to wire i and max to j. The network must sort every input. Score: comparator count, minimized; parallel depth is reported separately. Maximum 4096 comparators.

Parameters: `{"n": 16, "max_comparators": 4096, "reference": 60}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize comparators in a sorting network on 16 inputs.

Why it matters: Optimal-size sorting networks are the explicit combinatorial optimization target of the paper.

- [Greedy Best-First Search for the Optimal-Size Sorting Network Problem](https://doi.org/10.1016/j.procs.2019.09.199): Main research objective: Construct sorting networks with fewer comparators. Task connection: The local task restricts this problem to 16 wires and exhaustively checks binary inputs. Its reference size is not claimed as a current record.

The scientific target is the network construction itself, not an incidental test of a general agent.

## Evaluation protocol

Reimplemented in this repository and cross-checked against the paper's published constructions/values.

- Independent exact certificate verifier based on the zero-one principle. All 65,536 Boolean inputs are checked. The supplied seed has 120 comparators; the 60-comparator, depth-10 reference from Dobbelaere's author-maintained list is independently checked in tests/test_science_tcs.py. The reference is a feasible upper bound, not a proof of optimality. The evaluator recreates the construction objective, not the source paper's SAT search or optimality proofs.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/abs/1507.01428 (Codish et al., Sorting Networks: to the End and Back Again (2015/2016): comparator-network definitions, zero-one verification, and the optimal size/depth construction problem.)
- benchmark: https://bertdobbelaere.github.io/sorting_networks.html#N16L60D10 (Author-maintained sorting-network list, 16 inputs / 60 compare-exchanges / 10 layers; inspected 2026-09-20. Comparator topology is preserved as an independently verified test fixture.)

## Limitations

- This is an independently recreated construction benchmark, not a reproduction of the paper's SAT search, experimental budget, or optimality proof.
- The size objective is identical to the finite sorting-network problem. Depth is diagnostic only, and the 4096-comparator cap is a generous benchmark resource limit.
- The 60-comparator reference is a verified feasible upper bound. The inspected source lists size bounds 57..60; this package does not prove the minimum or promise that the online record will remain current.
- Improving the 120-comparator seed or recovering a published network is not a new research result. A claimed record requires a separately reviewed construction and comparison against current literature.
