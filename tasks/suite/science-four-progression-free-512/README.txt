# Large four-term-progression-free integer sets

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-four-progression-free-512`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty subset of [1,n=512] containing no nonconstant k=4 term arithmetic progression. Maximize cardinality. Maximize cardinality of a four-term-progression-free subset of [1,512]. A feasible construction supplies a finite lower bound, not an asymptotic theorem.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty subset of [1,n=512] containing no nonconstant k=4 term arithmetic progression. Maximize cardinality.

## State of the art

No documented value of r_4(512). Exact values of r_4(N) are tabulated only up to N = 142, where r_4(142) = 58 (OEIS A003003). Green and Tao proved a polylogarithmic-saving upper bound.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #142](https://www.erdosproblems.com/142), status: open ($10000).

- [OEIS A003003: Largest subset of [1..n] without a 4-term arithmetic progression](https://oeis.org/A003003)
- [New bounds for Szemerédi's theorem, III: A polylogarithmic bound for r_4(N)](https://arxiv.org/abs/1705.01703), Ben Green, Terence Tao (2017)

Parameters: `{"n": 512, "k": 4}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the extremal size of integer sets avoiding four-term arithmetic progressions.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [New bounds for Szemerédi’s theorem, III: A polylogarithmic bound for r_4(N)](https://arxiv.org/abs/1705.01703): Main research objective: Determine the extremal size of integer sets avoiding four-term arithmetic progressions. Task connection: Maximize cardinality of a four-term-progression-free subset of [1,512]. A feasible construction supplies a finite lower bound, not an asymptotic theorem.

A problem-focused primary paper studies the same substantive mathematical construction or extremal quantity. No novelty claim is implied.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1705.01703 (Ben Green and Terence Tao, New bounds for Szemerédi’s theorem, III: A polylogarithmic bound for r_4(N). Author abstract inspected; r_4(N) is exactly the largest four-term-progression-free subset of an interval.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000144 (JSP-000144; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Maximize cardinality of a four-term-progression-free subset of [1,512]. A feasible construction supplies a finite lower bound, not an asymptotic theorem.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
