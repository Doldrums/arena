# Distinct subset sums with a small largest element

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-distinct-subset-sums-12`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> exactly n=12 distinct positive Python integers <= maximum=1048576. Every subset, including the empty subset, must have a different sum. Minimize the largest integer. Exactly 12 positive integers with bounded largest entry; all 4096 subset sums checked. An improved feasible largest entry is only a finite upper bound.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly n=12 distinct positive Python integers <= maximum=1048576. Every subset, including the empty subset, must have a different sum. Minimize the largest integer.

## State of the art

The best known 12-element set with distinct subset sums has largest element 1157 (V. Popov, 2025, recorded in OEIS A276661), below the Conway-Guy value 1164 (OEIS A005318). Exact values are known only up to n = 10 (309), and the Dubroff-Fox-Xu bound gives at least binomial(12,6) = 924 for n = 12.

Reference value: best known value `1157` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1](https://www.erdosproblems.com/1), status: disproved (Lean).

- [OEIS A276661: Least k such that some n-subset of {1..k} has distinct subset sums](https://oeis.org/A276661)
- [OEIS A005318: Conway-Guy sequence](https://oeis.org/A005318)
- [A Note on the Erdős Distinct Subset Sums Problem](https://doi.org/10.1137/20m1385883), Quentin Dubroff, Jacob Fox, Max Wenqiang Xu (2021)
- [Some Remarks on the Erdős Distinct Subset Sums Problem](https://arxiv.org/abs/2208.12182), Stefan Steinerberger (2023)

Parameters: `{"n": 12, "maximum": 1048576}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate the smallest possible largest element of a set with all subset sums distinct.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Some Remarks on the Erdős Distinct Subset Sums Problem](https://arxiv.org/abs/2208.12182): Main research objective: Estimate the smallest possible largest element of a set with all subset sums distinct. Task connection: Exactly 12 positive integers with bounded largest entry; all 4096 subset sums checked. An improved feasible largest entry is only a finite upper bound.

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

- paper: https://arxiv.org/abs/2208.12182 (Stefan Steinerberger, Some Remarks on the Erdős Distinct Subset Sums Problem. Author abstract, 2022 preprint, revised 2023: distinct sums of all subsets and bounds on the largest element.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000043 (JSP-000043; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Exactly 12 positive integers with bounded largest entry; all 4096 subset sums checked. An improved feasible largest entry is only a finite upper bound.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
