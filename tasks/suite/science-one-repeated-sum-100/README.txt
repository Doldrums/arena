# Subsets of {1, ..., 100} in which at most one sum is repeated

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-one-repeated-sum-100`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct integers in 1..100 such that at most one integer has more than one representation a + b with a <= b in the set. Maximize the size; the optimum is 16. For N = 100 the maximum is 16, so the task recovers an extremal set.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 1..100 such that at most one integer has more than one representation a + b with a <= b in the set. Maximize the size; the optimum is 16.

## State of the art

The maximum for N = 100 is 16 (OEIS A389182).

Reference value: proven optimum `16` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #864](https://www.erdosproblems.com/864), status: open.

- [OEIS A389182: Maximum size of a subset of {1..n} in which all sums a+b (a <= b) are distinct except possibly one](https://oeis.org/A389182)
- [On sums of a Sidon-sequence](https://doi.org/10.1016/0022-314X(91)90083-N), P. Erdős, R. Freud (1991)

Parameters: `{"n": 100}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate the largest subset of {1..N} in which at most one sum has several representations (Erdős Problem #864).

Why it matters: A near-Sidon relaxation that measures how much one exceptional sum can enlarge Sidon sets; the constant 2/sqrt 3 is conjectured optimal.

- [On sums of a Sidon-sequence](https://doi.org/10.1016/0022-314X(91)90083-N): Main research objective: Estimate the largest subset of {1..N} in which at most one sum has several representations (Erdős Problem #864). Task connection: For N = 100 the maximum is 16, so the task recovers an extremal set.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For N = 100 the maximum is 16, so the task recovers an extremal set. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0022-314X(91)90083-N (P. Erdős and R. Freud, On sums of a Sidon-sequence (1991). Crossref record inspected; Erdős Problem #864 page inspected (Erdős and Freud: |A| >= (1+o(1))(2/sqrt 3)N^(1/2) by joining a Sidon set with its reflection; a matching upper bound is asked). OEIS A389182 inspected (b-file by Ferudun): the maximum for N = 100 is 16. For N = 100 the maximum is 16, so the task recovers an extremal set.)
- archive: https://www.erdosproblems.com/864 (Erdős Problem #864 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000716 (JSP-000716; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
