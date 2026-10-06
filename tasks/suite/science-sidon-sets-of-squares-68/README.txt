# Largest Sidon set among the first 68 squares

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-sidon-sets-of-squares-68`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct bases x in 1..68 whose squares form a Sidon set: all sums x^2 + y^2 with x <= y are distinct. Maximize the number of bases; the optimum is 32. For N = 68 the maximum is 32, so the task recovers an extremal set.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct bases x in 1..68 whose squares form a Sidon set: all sums x^2 + y^2 with x <= y are distinct. Maximize the number of bases; the optimum is 32.

## State of the art

The largest Sidon subset of {1^2, ..., 68^2} has 32 elements (OEIS A390813).

Reference value: proven optimum `32` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #773](https://www.erdosproblems.com/773), status: open.

- [OEIS A390813: Size of the largest Sidon subset of the first n positive perfect squares](https://oeis.org/A390813)
- [An Application of Graph Theory to Additive Number Theory](https://doi.org/10.1016/S0195-6698(85)80027-5), Noga Alon, Paul Erdős (1985)

Parameters: `{"m": 68}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the largest Sidon subset of {1, 4, ..., N^2} (Erdős Problem #773 asks whether it is N^(1-o(1))).

Why it matters: Sidon sets of squares link additive combinatorics with representations by sums of two squares; the exponent is open.

- [An Application of Graph Theory to Additive Number Theory](https://doi.org/10.1016/S0195-6698(85)80027-5): Main research objective: Determine the largest Sidon subset of {1, 4, ..., N^2} (Erdős Problem #773 asks whether it is N^(1-o(1))). Task connection: For N = 68 the maximum is 32, so the task recovers an extremal set.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For N = 68 the maximum is 32, so the task recovers an extremal set. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/S0195-6698(85)80027-5 (Noga Alon and Paul Erdős, An Application of Graph Theory to Additive Number Theory (1985). Crossref record inspected; Erdős Problem #773 page inspected (Alon and Erdős: N^(2/3-o(1)) from random subsets; Lefmann and Thiele: N^(2/3); upper bound N^(1-c/log log N) by Croot, Mao and Yip). OEIS A390813 inspected: the largest Sidon subset of the first 68 squares has 32 elements (computed by Sievers). For N = 68 the maximum is 32, so the task recovers an extremal set.)
- archive: https://www.erdosproblems.com/773 (Erdős Problem #773 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000634 (JSP-000634; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
