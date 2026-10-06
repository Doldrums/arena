# Large pairwise-coprime sumsets of two bounded integer sets

**Source collection:** [Problem-bank constructions: arithmetic and extremal sets: source-based research tasks](../../papers/science-prize_b.md)\
**Task id:** `science-number-theory-coprime-sumset`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Return two lists A,B, each containing exactly 3 distinct integers in [1,128]. All DISTINCT values in A+B must be pairwise coprime. Maximize the cardinality of A+B; repeated representations are allowed. Finite construction model for the Straus sumset-density question. Three elements per summand set and the bounding box are local; finite cardinality does not establish infinite density.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> candidate. Return two lists A,B, each containing exactly 3 distinct integers in [1,128]. All DISTINCT values in A+B must be pairwise coprime. Maximize the cardinality of A+B; repeated representations are allowed.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Paul Erdős and Ronald L. Graham (1980, Old and New Problems and Results in Combinatorial Number Theory) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Old and New Problems and Results in Combinatorial Number Theory](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Paul Erdős and Ronald L. Graham (1980)

Parameters: `{"n": 128, "size": 3}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


The original mathematical question is verified in the cited primary research monograph/survey, but no dedicated paper with this exact problem as a primary research goal was independently established in this review. Conservative metadata does not equate a prize listing or historical open status with important_to_science.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Finite construction model for the Straus sumset-density question. Three elements per summand set and the bounding box are local; finite cardinality does not establish infinite density.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf (Paul Erdős and Ronald L. Graham (1980), Old and New Problems and Results in Combinatorial Number Theory. Printed p. 85. Finite construction model for the Straus sumset-density question. Three elements per summand set and the bounding box are local; finite cardinality does not establish infinite density. Primary full text downloaded and inspected; the scanned monograph was OCRed locally and equation-sensitive passages checked against page images. No contemporary open/solved status is inferred from this historical publication.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0301-0400.md#JSP-000354 (JSP-000354; pinned Justin Sun Prize bank revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Discovery source only; mathematical authorship remains with the cited researchers. Independent paraphrase and implementation.)

## Limitations

- Independent finite adaptation, not a Lean proof, prize submission, full solution, optimality proof or claim of mathematical novelty.
- Published source supplies the mathematical question; all verifier and starter code was written locally, with no upstream implementation imported.
- Finite bounds and the public starter are development instances. An accepted candidate establishes only the reported local feasible value; no asymptotic inference follows.
- Candidate Python code is trusted; this runner is not a malicious-code sandbox.
- Finite construction model for the Straus sumset-density question. Three elements per summand set and the bounding box are local; finite cardinality does not establish infinite density.
