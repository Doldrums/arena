# Thirty-two integers with many distinct 3-term progression differences

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-three-progression-differences-32`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> exactly 32 distinct integers in 1..512. The score is the number of distinct d > 0 such that a, a + d, a + 2d all lie in the set for some a. Maximize. A 32-element set with many progression differences is a finite construction for this extremal function.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 32 distinct integers in 1..512. The score is the number of distinct d > 0 such that a, a + d, a + 2d all lie in the set for some a. Maximize.

## State of the art

No documented values for n = 32; asymptotically the exponent lies in [1.77898, 11/6].

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1097](https://www.erdosproblems.com/1097), status: open.

- [New counterexamples for sums-differences](https://doi.org/10.1090/S0002-9939-2015-12603-2), Marius Lemm (2015)
- [Bounds on arithmetic projections, and applications to the Kakeya conjecture](https://doi.org/10.4310/MRL.1999.v6.n6.a3), Nets Hawk Katz, Terence Tao (1999)

Parameters: `{"size": 32, "bound": 512}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how many distinct common differences 3-term progressions in an n-element set can have (Erdős Problem #1097).

Why it matters: Through Bourgain's arithmetic formulation the problem bears on the Kakeya conjecture.

- [New counterexamples for sums-differences](https://doi.org/10.1090/S0002-9939-2015-12603-2): Main research objective: Determine how many distinct common differences 3-term progressions in an n-element set can have (Erdős Problem #1097). Task connection: A 32-element set with many progression differences is a finite construction for this extremal function.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A 32-element set with many progression differences is a finite construction for this extremal function. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1090/S0002-9939-2015-12603-2 (Marius Lemm, New counterexamples for sums-differences (2015). Crossref records inspected (Lemm 2015; Katz and Tao 1999). Erdős Problem #1097 page inspected: the question is equivalent to Bourgain's sums-differences problem; the optimal exponent lies in [1.77898..., 11/6] (Lemm, with a small improvement by AlphaEvolve; Katz and Tao), so the O(n^(3/2)) guess is false. No finite values are documented. A 32-element set with many progression differences is a finite construction for this extremal function.)
- archive: https://www.erdosproblems.com/1097 (Erdős Problem #1097 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000911 (JSP-000911; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
