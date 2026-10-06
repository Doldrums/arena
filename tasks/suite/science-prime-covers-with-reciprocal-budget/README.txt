# Covering 1..L by prime residue classes with reciprocal budget 1 (primes up to 1000)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-prime-covers-with-reciprocal-budget`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> classes [[p, r], ...] with distinct primes p <= 1000, 0 <= r < p and sum of 1/p at most 1 (exact rationals). The score is the largest L such that every integer 1..L lies in some class (exact, capped at 10^5). Maximize; L >= 999 would realize the Erdős-Ruzsa covering statement at x = 1000 with C = 1. Covered lengths for x = 1000 and C = 1 are finite evidence for the conjecture; reaching 999 would realize it at this size.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> classes [[p, r], ...] with distinct primes p <= 1000, 0 <= r < p and sum of 1/p at most 1 (exact rationals). The score is the largest L such that every integer 1..L lies in some class (exact, capped at 10^5). Maximize; L >= 999 would realize the Erdős-Ruzsa covering statement at x = 1000 with C = 1.

## State of the art

No documented values.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1200](https://www.erdosproblems.com/1200), status: open.

- [On the small sieve. I. Sifting by primes](https://doi.org/10.1016/0022-314X(80)90032-3), P. Erdős, I. Z. Ruzsa (1980)
- [Erdős Problem #1200](https://www.erdosproblems.com/1200)

Parameters: `{"largest_prime": 1000, "budget": 1}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether prime residue classes of bounded reciprocal mass can cover [1, x) for all large x (Erdős Problem #1200).

Why it matters: The conjecture concerns the limits of the small sieve and connects to Jacobsthal-type covering problems.

- [On the small sieve. I. Sifting by primes](https://doi.org/10.1016/0022-314X(80)90032-3): Main research objective: Decide whether prime residue classes of bounded reciprocal mass can cover [1, x) for all large x (Erdős Problem #1200). Task connection: Covered lengths for x = 1000 and C = 1 are finite evidence for the conjecture; reaching 999 would realize it at this size.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Covered lengths for x = 1000 and C = 1 are finite evidence for the conjecture; reaching 999 would realize it at this size. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0022-314X(80)90032-3 (P. Erdős and I. Z. Ruzsa, On the small sieve. I. Sifting by primes (1980). Crossref record inspected; Erdős Problem #1200 page inspected (the Erdős-Ruzsa conjecture that primes p < x with sum 1/p < C admit classes covering every n < x, called 'surprising' by Erdős; related to #688). No finite values are documented. Covered lengths for x = 1000 and C = 1 are finite evidence for the conjecture; reaching 999 would realize it at this size.)
- archive: https://www.erdosproblems.com/1200 (Erdős Problem #1200 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-1001-1022.md#JSP-001005 (JSP-001005; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
