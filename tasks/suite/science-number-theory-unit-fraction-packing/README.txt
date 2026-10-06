# Closest strict underpacking of one by supplied unit fractions

**Source collection:** [Problem-bank constructions: arithmetic and extremal sets: source-based research tasks](../../papers/science-prize_b.md)\
**Task id:** `science-number-theory-unit-fraction-packing`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Return nonempty distinct zero-based indices into denominators [2,3,...,48]; reciprocal sum must be STRICTLY BELOW 1. Minimize positive deficit 1-sum; exact rational value is reported. Fixed finite input collection whose reciprocal total exceeds one; minimizes the strict deficit rather than asserting a uniform bound for all collections. The source permits an exact-one subsum; the local protocol explicitly excludes it.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> candidate. Return nonempty distinct zero-based indices into denominators [2,3,...,48]; reciprocal sum must be STRICTLY BELOW 1. Minimize positive deficit 1-sum; exact rational value is reported.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Paul Erdős and Ronald L. Graham (1980, Old and New Problems and Results in Combinatorial Number Theory) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Old and New Problems and Results in Combinatorial Number Theory](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Paul Erdős and Ronald L. Graham (1980)

Parameters: `{"denominators": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


The original mathematical question is verified in the cited primary research monograph/survey, but no dedicated paper with this exact problem as a primary research goal was independently established in this review. Conservative metadata does not equate a prize listing or historical open status with important_to_science.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Fixed finite input collection whose reciprocal total exceeds one; minimizes the strict deficit rather than asserting a uniform bound for all collections. The source permits an exact-one subsum; the local protocol explicitly excludes it.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf (Paul Erdős and Ronald L. Graham (1980), Old and New Problems and Results in Combinatorial Number Theory. Printed p. 40. Fixed finite input collection whose reciprocal total exceeds one; minimizes the strict deficit rather than asserting a uniform bound for all collections. The source permits an exact-one subsum; the local protocol explicitly excludes it. Primary full text downloaded and inspected; the scanned monograph was OCRed locally and equation-sensitive passages checked against page images. No contemporary open/solved status is inferred from this historical publication.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0201-0300.md#JSP-000261 (JSP-000261; pinned Justin Sun Prize bank revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Discovery source only; mathematical authorship remains with the cited researchers. Independent paraphrase and implementation.)

## Limitations

- Independent finite adaptation, not a Lean proof, prize submission, full solution, optimality proof or claim of mathematical novelty.
- Published source supplies the mathematical question; all verifier and starter code was written locally, with no upstream implementation imported.
- Finite bounds and the public starter are development instances. An accepted candidate establishes only the reported local feasible value; no asymptotic inference follows.
- Candidate Python code is trusted; this runner is not a malicious-code sandbox.
- Fixed finite input collection whose reciprocal total exceeds one; minimizes the strict deficit rather than asserting a uniform bound for all collections. The source permits an exact-one subsum; the local protocol explicitly excludes it.
- Feasibility and rational objective are computed exactly; the standard score envelope converts the final rational to binary64, so exact numerator/denominator details should be used to resolve nearly tied scores.
