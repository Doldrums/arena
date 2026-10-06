# Smallest Mahler measure above one in degree at most 12 (Lehmer's problem)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-lehmer-small-mahler-measure-degree-12`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> integer coefficients [c_0, ..., c_d] (constant term first) with 1 <= d <= 12, |c_i| <= 3 and c_d != 0. Polynomials equal to +-x^k times a product of cyclotomic polynomials (measure exactly one) are rejected by exact polynomial division. The score is the Mahler measure |c_d| * prod max(1, |z|) over all complex roots z (Aberth iteration, reported to 10 decimals). Minimize; the optimum is Lehmer's number 1.1762808183. Among integer polynomials of degree at most 12 the least measure above one is Lehmer's number, so the task recovers Lehmer's polynomial (up to sign, reversal and cyclotomic factors).

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> integer coefficients [c_0, ..., c_d] (constant term first) with 1 <= d <= 12, |c_i| <= 3 and c_d != 0. Polynomials equal to +-x^k times a product of cyclotomic polynomials (measure exactly one) are rejected by exact polynomial division. The score is the Mahler measure |c_d| * prod max(1, |z|) over all complex roots z (Aberth iteration, reported to 10 decimals). Minimize; the optimum is Lehmer's number 1.1762808183.

## State of the art

Lehmer's number 1.17628081826 (degree 10) is the least Mahler measure above one for integer polynomials of degree at most 54 (Mossinghoff, Rhin and Wu 2008 for even degrees; Smyth 1971 for nonreciprocal polynomials).

Reference value: proven optimum `1.1762808183` (reviewed 2026-09-24).

- [Minimal Mahler Measures](https://doi.org/10.1080/10586458.2008.10128872), Michael J. Mossinghoff, Georges Rhin, Qiang Wu (2008)
- [Factorization of Certain Cyclotomic Functions](https://doi.org/10.2307/1968172), D. H. Lehmer (1933)
- [On the Product of the Conjugates outside the unit circle of an Algebraic Integer](https://doi.org/10.1112/blms/3.2.169), C. J. Smyth (1971)

Parameters: `{"max_degree": 12, "max_coefficient": 3}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether Mahler measures of integer polynomials that exceed one are bounded away from one (Lehmer's problem).

Why it matters: Lehmer's problem is a central open question linking algebraic number theory, heights, the entropy of toral automorphisms and knot polynomials; exhaustive minima by degree are its main computational evidence.

- [Minimal Mahler Measures](https://doi.org/10.1080/10586458.2008.10128872): Main research objective: Decide whether Mahler measures of integer polynomials that exceed one are bounded away from one (Lehmer's problem). Task connection: Among integer polynomials of degree at most 12 the least measure above one is Lehmer's number, so the task recovers Lehmer's polynomial (up to sign, reversal and cyclotomic factors).

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Among integer polynomials of degree at most 12 the least measure above one is Lehmer's number, so the task recovers Lehmer's polynomial (up to sign, reversal and cyclotomic factors). Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1080/10586458.2008.10128872 (Michael J. Mossinghoff, Georges Rhin and Qiang Wu, Minimal Mahler Measures (2008). Crossref records inspected for Lehmer (Ann. of Math. 1933), Smyth (Bull. LMS 1971) and Mossinghoff, Rhin and Wu (Experimental Math. 2008). Lehmer's polynomial x^10 + x^9 - x^7 - x^6 - x^5 - x^4 - x^3 + x + 1 has measure 1.17628081826; Mossinghoff, Rhin and Wu determined the minimal measure of noncyclotomic irreducible polynomials of every even degree up to 54, none below Lehmer's number, and Smyth proved that nonreciprocal polynomials (which include every noncyclotomic irreducible polynomial of odd degree) have measure at least 1.3247. Measures multiply over factors, so no integer polynomial of degree at most 12 has measure in (1, 1.17628). Among integer polynomials of degree at most 12 the least measure above one is Lehmer's number, so the task recovers Lehmer's polynomial (up to sign, reversal and cyclotomic factors).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000025 (JSP-000025; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case. The measure is evaluated in floating point after an exact cyclotomic test (accuracy about 1e-10).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
