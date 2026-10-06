# Subsets of {1, ..., 44} in which no element divides two others

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-no-element-divides-two-others-44`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct integers in 1..44 such that no element divides two other elements. Maximize the size; the optimum is 30. For n = 44 the maximum is 30, so the task recovers an extremal set.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 1..44 such that no element divides two other elements. Maximize the size; the optimum is 30.

## State of the art

f(44) = 30 (OEIS A038372).

Reference value: proven optimum `30` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1062](https://www.erdosproblems.com/1062), status: open.

- [OEIS A038372: Largest subset of [1..n] such that no member divides two others](https://oeis.org/A038372)
- [A Divisibility Problem](https://doi.org/10.1002/sapm1977563291), Kenneth Lebensold (1977)

Parameters: `{"n": 44}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine f(n), the largest subset of {1..n} in which no element divides two others, and its limiting density.

Why it matters: A classical divisibility extremal problem related to primitive sets; the limiting constant is known only to lie in [0.6725, 0.6736].

- [A Divisibility Problem](https://doi.org/10.1002/sapm1977563291): Main research objective: Determine f(n), the largest subset of {1..n} in which no element divides two others, and its limiting density. Task connection: For n = 44 the maximum is 30, so the task recovers an extremal set.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 44 the maximum is 30, so the task recovers an extremal set. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1002/sapm1977563291 (Kenneth Lebensold, A Divisibility Problem (1977). Crossref record inspected; Erdős Problem #1062 page inspected (the interval [m+1, 3m+2] gives f(n) >= ceil(2n/3); Lebensold proved 0.6725n <= f(n) <= 0.6736n for large n; whether lim f(n)/n is irrational is open; Guy B24). OEIS A038372 inspected: f(44) = 30. For n = 44 the maximum is 30, so the task recovers an extremal set.)
- archive: https://www.erdosproblems.com/1062 (Erdős Problem #1062 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000882 (JSP-000882; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table; the simple interval construction [15, 44] already attains 30.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
