# Sparse squares of twelve-term integer polynomials

**Source collection:** [Problem-bank constructions: arithmetic and extremal sets: source-based research tasks](../../papers/science-prize_b.md)\
**Task id:** `science-algebra-sparse-polynomial-square`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Return coefficient list in ascending degree, length<=41, nonzero final coefficient, entries integers in [-64,64], exactly 12 nonzero terms. Minimize nonzero terms in the EXACT integer square. Restricts the characteristic-zero polynomial problem to bounded integer coefficients and degree; cancellation is exact and no general lower-bound theorem is claimed.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> candidate. Return coefficient list in ascending degree, length<=41, nonzero final coefficient, entries integers in [-64,64], exactly 12 nonzero terms. Minimize nonzero terms in the EXACT integer square.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Andrzej Schinzel and Umberto Zannier (2009, On the number of terms of a power of a polynomial) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [On the number of terms of a power of a polynomial](https://ems.press/content/serial-article-files/39657), Andrzej Schinzel and Umberto Zannier (2009)

Parameters: `{"terms": 12, "degree": 40, "coefficient_bound": 64}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Relate the nonzero coefficient counts of a polynomial and its powers and improve known bounds.

Why it matters: Explores algebraic cancellation and sparse polynomial structure, the research problem of the paper.

- [On the number of terms of a power of a polynomial](https://ems.press/content/serial-article-files/39657): Main research objective: Relate the nonzero coefficient counts of a polynomial and its powers and improve known bounds. Task connection: Introduction and Theorem 1, pp. 95–96; local exponent 2, 12 input terms, integer coefficients and bounded degree. Primary full text inspected. Restricts the characteristic-zero polynomial problem to bounded integer coefficients and degree; cancellation is exact and no general lower-bound theorem is claimed.

A primary research paper directly studies the mathematical objective; local finite scope and restrictions are explicit. This does not certify novelty, importance of the baseline itself, or current open status.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Restricts the characteristic-zero polynomial problem to bounded integer coefficients and degree; cancellation is exact and no general lower-bound theorem is claimed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://ems.press/content/serial-article-files/39657 (Andrzej Schinzel and Umberto Zannier (2009), On the number of terms of a power of a polynomial. Printed p. 95. Restricts the characteristic-zero polynomial problem to bounded integer coefficients and degree; cancellation is exact and no general lower-bound theorem is claimed. Primary full text inspected. DOI:10.4171/RLM/534.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0301-0400.md#JSP-000393 (JSP-000393; pinned Justin Sun Prize bank revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Discovery source only; mathematical authorship remains with the cited researchers. Independent paraphrase and implementation.)

## Limitations

- Independent finite adaptation, not a Lean proof, prize submission, full solution, optimality proof or claim of mathematical novelty.
- Published source supplies the mathematical question; all verifier and starter code was written locally, with no upstream implementation imported.
- Finite bounds and the public starter are development instances. An accepted candidate establishes only the reported local feasible value; no asymptotic inference follows.
- Candidate Python code is trusted; this runner is not a malicious-code sandbox.
- Restricts the characteristic-zero polynomial problem to bounded integer coefficients and degree; cancellation is exact and no general lower-bound theorem is claimed.
