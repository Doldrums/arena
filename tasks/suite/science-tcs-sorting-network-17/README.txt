# Size-efficient sorting networks on 17 wires

**Source collection:** [Theoretical computer science: source-based research tasks](../../papers/science-tcs.md)\
**Task id:** `science-tcs-sorting-network-17`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Construct a compare-exchange network that sorts all 17-input sequences with as few comparators as possible; correctness is certified over all 131,072 Boolean inputs (zero-one principle). The best known network has 71 comparators (depth 12); the proven lower bound is 63, so the optimal size is open. The seed odd-even transposition network uses 136 comparators.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> ordered list of integer pairs (i, j), 0 <= i < j < N. Each compare-exchange writes min to wire i and max to j. The network must sort every input. Score: comparator count, minimized; parallel depth is reported separately. Maximum 4096 comparators.

Parameters: `{"n": 17, "max_comparators": 4096, "reference": 71}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize comparators in a sorting network on 17 inputs.

Why it matters: Optimal-size sorting networks are the explicit combinatorial optimization target of the paper.

- [Greedy Best-First Search for the Optimal-Size Sorting Network Problem](https://doi.org/10.1016/j.procs.2019.09.199): Main research objective: Construct sorting networks with fewer comparators. Task connection: The local task restricts this problem to 17 wires and exhaustively checks binary inputs. Its reference size is not claimed as a current record.

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

- paper: https://arxiv.org/abs/1507.01428 (Codish et al.: comparator networks, zero-one verification and the size/depth optimisation problem for 17 to 20 inputs.)
- benchmark: https://bertdobbelaere.github.io/sorting_networks.html#N17L71D12 (Author-maintained list, 17 inputs: best known 71 compare-exchanges (depth 12), size bounds 63..71, inspected 2026-09-20.)

## Limitations

- Independently recreated construction benchmark; the 71-comparator reference value is taken from the list and is not embedded as a verified fixture.
- Reaching 71 reproduces a known network; only fewer than 71 comparators would be a new bound and must be checked against current literature.
- Depth is diagnostic only.
