# Covering an initial interval with one residue class for each of the first 30 primes

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-jacobsthal-covering-first-30-primes`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 30 residues r_1, ..., r_30 with 0 <= r_i < p_i for the first 30 primes 2, 3, ..., 113. The score is the largest L such that every integer 1..L is congruent to r_i modulo p_i for some i. Maximize; the optimum is 329 (Jacobsthal's function of the product of the first 30 primes is 330). For the first 30 primes the optimum is 329, so the task recovers an extremal covering.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 30 residues r_1, ..., r_30 with 0 <= r_i < p_i for the first 30 primes 2, 3, ..., 113. The score is the largest L such that every integer 1..L is congruent to r_i modulo p_i for some i. Maximize; the optimum is 329 (Jacobsthal's function of the product of the first 30 primes is 330).

## State of the art

Jacobsthal's function of the product of the first 30 primes is 330 (Hagedorn 2009; OEIS A048670), so at most 329 consecutive integers can be covered.

Reference value: proven optimum `329` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #687](https://www.erdosproblems.com/687), status: open ($1000).

- [OEIS A048670: Jacobsthal function applied to the product of the first n primes](https://oeis.org/A048670)
- [Computation of Jacobsthal's function h(n) for n < 50](https://doi.org/10.1090/S0025-5718-08-02166-2), Thomas Hagedorn (2009)
- [Long gaps between primes](https://doi.org/10.1090/jams/876), Kevin Ford, Ben Green, Sergei Konyagin, James Maynard, Terence Tao (2018)

Parameters: `{"count": 30}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate Y(x), the longest interval that can be covered by one residue class per prime up to x (Jacobsthal's function of primorials).

Why it matters: This covering function controls large gaps between consecutive primes; Erdős offered $1000 for estimates (Erdős Problem #687) and its growth rate remains open.

- [Computation of Jacobsthal's function h(n) for n < 50](https://doi.org/10.1090/S0025-5718-08-02166-2): Main research objective: Estimate Y(x), the longest interval that can be covered by one residue class per prime up to x (Jacobsthal's function of primorials). Task connection: For the first 30 primes the optimum is 329, so the task recovers an extremal covering.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For the first 30 primes the optimum is 329, so the task recovers an extremal covering. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1090/S0025-5718-08-02166-2 (Thomas Hagedorn, Computation of Jacobsthal's function h(n) for n < 50 (2009). Crossref record inspected; OEIS A048670 inspected: Jacobsthal's function of the product of the first n primes, a(30) = 330 (Hagedorn computed the values for n < 50). By the Chinese remainder theorem a run of L consecutive integers sharing a factor with the primorial is equivalent to covering 1..L with one class per prime, so the maximal covered length is 329. Erdős Problem #687 page inspected (Y(x) << x^2 by Iwaniec; lower bounds of Ford, Green, Konyagin, Maynard and Tao and later improvements). For the first 30 primes the optimum is 329, so the task recovers an extremal covering.)
- archive: https://www.erdosproblems.com/687 (Erdős Problem #687 (open ($1000)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000559 (JSP-000559; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case (published computation).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
