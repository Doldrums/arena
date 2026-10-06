# Subsets of {1, ..., 200} in which square products of four elements force ad = bc

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-square-products-condition-200`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct integers in 1..200 such that whenever a <= b <= c <= d are elements (repetition allowed) with abcd a perfect square, ad = bc (checked exactly through parity vectors of prime exponents). Maximize the size; the optimum is 102. For n = 200 the maximum is 102, so the task recovers an extremal set.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 1..200 such that whenever a <= b <= c <= d are elements (repetition allowed) with abcd a perfect square, ad = bc (checked exactly through parity vectors of prime exponents). Maximize the size; the optimum is 102.

## State of the art

The maximum for n = 200 is 102 (OEIS A387584).

Reference value: proven optimum `102` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #888](https://www.erdosproblems.com/888), status: solved (Lean).

- [OEIS A387584: Largest subset of {1..n} in which a square product abcd forces ad = bc](https://oeis.org/A387584)
- [Some of my new and almost new problems and results in combinatorial number theory](https://doi.org/10.1515/9783110809794.169), Paul Erdős (1998)

Parameters: `{"n": 200}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the largest A in {1..n} such that a square product abcd (a <= b <= c <= d) forces ad = bc (Erdős Problem #888).

Why it matters: A multiplicative analogue of Sidon-type conditions whose order of magnitude was settled only recently.

- [Some of my new and almost new problems and results in combinatorial number theory](https://doi.org/10.1515/9783110809794.169): Main research objective: Determine the largest A in {1..n} such that a square product abcd (a <= b <= c <= d) forces ad = bc (Erdős Problem #888). Task connection: For n = 200 the maximum is 102, so the task recovers an extremal set.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 200 the maximum is 102, so the task recovers an extremal set. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1515/9783110809794.169 (Paul Erdős, Some of my new and almost new problems and results in combinatorial number theory (1998). Crossref record inspected; Erdős Problem #888 page inspected (a question of Erdős, Sárközy and Sós; |A| = o(n); primes and semiprimes give (1+o(1)) n log log n/log n, and a matching upper bound was proved recently and verified in Lean). OEIS A387584 inspected (b-file by Sievers for n <= 203): the maximum for n = 200 is 102, attained by the primes together with the products of two distinct primes. For n = 200 the maximum is 102, so the task recovers an extremal set.)
- archive: https://www.erdosproblems.com/888 (Erdős Problem #888 (solved (Lean)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000739 (JSP-000739; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table; the independent tests confirm the repetition convention against the published small values.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
