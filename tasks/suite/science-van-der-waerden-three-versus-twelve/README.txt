# Two-colourings avoiding a red 3-term and a blue 12-term progression (w(3,12) = 135)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-van-der-waerden-three-versus-twelve`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> colours c_1, ..., c_N in {0, 1} with 1 <= N <= 135. Colour 0 may contain no 3-term and colour 1 no 12-term arithmetic progression (exhaustive check). Maximize N; the optimum is 134 because w(3,12) = 135. Since w(3,12) = 135, the longest valid colouring has 134 terms; the task recovers an extremal colouring.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> colours c_1, ..., c_N in {0, 1} with 1 <= N <= 135. Colour 0 may contain no 3-term and colour 1 no 12-term arithmetic progression (exhaustive check). Maximize N; the optimum is 134 because w(3,12) = 135.

## State of the art

w(3,12) = 135, so 134 is the longest valid colouring (Ahmed, Kullmann and Snevily 2014; OEIS A171081).

Reference value: proven optimum `134` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #721](https://www.erdosproblems.com/721), status: solved (bounds of Green, Hunter and Schoen).

- [OEIS A171081: Van der Waerden numbers w(3,n)](https://oeis.org/A171081)
- [On the van der Waerden numbers w(2;3,t)](https://doi.org/10.1016/j.dam.2014.05.007), Tanbir Ahmed, Oliver Kullmann, Hunter Snevily (2014)
- [New lower bounds for van der Waerden numbers](https://doi.org/10.1017/fmp.2022.12), Ben Green (2022)

Parameters: `{"long_length": 12, "maximum": 135}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the growth of the off-diagonal van der Waerden numbers w(3,k).

Why it matters: Off-diagonal van der Waerden numbers connect Ramsey theory with bounds for sets without 3-term progressions; Graham's conjectured quadratic growth was disproved by Green.

- [On the van der Waerden numbers w(2;3,t)](https://doi.org/10.1016/j.dam.2014.05.007): Main research objective: Determine the growth of the off-diagonal van der Waerden numbers w(3,k). Task connection: Since w(3,12) = 135, the longest valid colouring has 134 terms; the task recovers an extremal colouring.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Since w(3,12) = 135, the longest valid colouring has 134 terms; the task recovers an extremal colouring. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/j.dam.2014.05.007 (Tanbir Ahmed, Oliver Kullmann and Hunter Snevily, On the van der Waerden numbers w(2;3,t) (2014). Crossref records inspected (Ahmed, Kullmann and Snevily 2014; Green 2022). OEIS A171081 inspected: w(3,12) = 135. Erdős Problem #721 page inspected (Green's superpolynomial lower bound, Hunter's improvement and Schoen's upper bound meet Erdős's stated challenges). Since w(3,12) = 135, the longest valid colouring has 134 terms; the task recovers an extremal colouring.)
- archive: https://www.erdosproblems.com/721 (Erdős Problem #721 (solved (bounds of Green, Hunter and Schoen)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000589 (JSP-000589; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case (published SAT computations).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
