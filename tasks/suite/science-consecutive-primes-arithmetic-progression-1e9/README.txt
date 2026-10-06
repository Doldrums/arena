# Consecutive primes in arithmetic progression below 10^9

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-consecutive-primes-arithmetic-progression-1e9`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> [p, d, k] describing p, p + d, ..., p + (k-1)d with 2 <= k <= 64, 1 <= d <= 5000 and last term at most 10^9. Every term must be prime (deterministic Miller-Rabin) and no prime may lie strictly between consecutive terms. Maximize k; the optimum below 10^9 is 6. Below 10^9 the longest such progressions have six terms (the first starts at 121174811), so the task recovers a six-term progression.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [p, d, k] describing p, p + d, ..., p + (k-1)d with 2 <= k <= 64, 1 <= d <= 5000 and last term at most 10^9. Every term must be prime (deterministic Miller-Rabin) and no prime may lie strictly between consecutive terms. Maximize k; the optimum below 10^9 is 6.

## State of the art

The longest progressions of consecutive primes below 10^9 have 6 terms, first 121174811 + 30j (Lander and Parkin 1967; OEIS A006560; local scan).

Reference value: proven optimum `6` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #141](https://www.erdosproblems.com/141), status: open.

- [OEIS A006560: Smallest starting prime for n consecutive primes in arithmetic progression](https://oeis.org/A006560)
- [Consecutive primes in arithmetic progression](https://doi.org/10.1090/S0025-5718-67-99657-3), L. J. Lander, T. R. Parkin (1967)
- [Ten consecutive primes in arithmetic progression](https://doi.org/10.1090/S0025-5718-01-01374-6), H. Dubner, T. Forbes, N. Lygeros, M. Mizony, H. Nelson, P. Zimmermann (2002)

Parameters: `{"bound": 1000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether there are arbitrarily long arithmetic progressions of consecutive primes.

Why it matters: Erdős Problem #141, called 'completely hopeless' by Erdős, is open even for infinitely many three-term progressions; the Green-Tao theorem gives progressions of primes that need not be consecutive.

- [Consecutive primes in arithmetic progression](https://doi.org/10.1090/S0025-5718-67-99657-3): Main research objective: Decide whether there are arbitrarily long arithmetic progressions of consecutive primes. Task connection: Below 10^9 the longest such progressions have six terms (the first starts at 121174811), so the task recovers a six-term progression.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Below 10^9 the longest such progressions have six terms (the first starts at 121174811), so the task recovers a six-term progression. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1090/S0025-5718-67-99657-3 (L. J. Lander and T. R. Parkin, Consecutive primes in arithmetic progression (1967). Crossref records inspected (Lander and Parkin 1967; Dubner, Forbes, Lygeros, Mizony, Nelson and Zimmermann 2002). OEIS A006560 inspected: the smallest six consecutive primes in arithmetic progression start at 121174811 with difference 30 (Lander and Parkin), and seven terms need a difference of at least 210. A local segmented sieve over all 50,847,534 primes below 10^9 confirmed that no seven consecutive primes below 10^9 form an arithmetic progression. Erdős Problem #141 page inspected. Below 10^9 the longest such progressions have six terms (the first starts at 121174811), so the task recovers a six-term progression.)
- archive: https://www.erdosproblems.com/141 (Erdős Problem #141 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000143 (JSP-000143; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; the bound 10^9 rests on a local exhaustive scan that agrees with OEIS A006560.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
