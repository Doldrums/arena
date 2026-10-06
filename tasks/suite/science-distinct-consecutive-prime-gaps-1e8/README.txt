# Longest string of pairwise distinct consecutive prime gaps below 10^8

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-distinct-consecutive-prime-gaps-1e8`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'start': p, 'length': k} with p prime, 1 <= k <= 200, and the k + 1 consecutive primes beginning at p all at most 10^8. The k gaps between them must be pairwise distinct. Maximize k; the optimum below 10^8 is 21. Among primes below 10^8 the longest string has 21 distinct gaps, so the task recovers it.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'start': p, 'length': k} with p prime, 1 <= k <= 200, and the k + 1 consecutive primes beginning at p all at most 10^8. The k gaps between them must be pairwise distinct. Maximize k; the optimum below 10^8 is 21.

## State of the art

The longest string of pairwise distinct consecutive gaps among primes below 10^8 has 21 gaps, starting at 69931991 (record positions OEIS A078515; recomputed locally).

Reference value: proven optimum `21` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #852](https://www.erdosproblems.com/852), status: open.

- [OEIS A078515: Numbers n such that A053597(n) sets a new record](https://oeis.org/A078515)
- [OEIS A053597: Number of distinct values among consecutive prime gaps before the first duplicate](https://oeis.org/A053597)
- [Consecutive primes in tuples](https://doi.org/10.4064/aa167-3-4), William D. Banks, Tristan Freiberg, Caroline L. Turnage-Butterbaugh (2015)

Parameters: `{"bound": 100000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate h(x), the longest string of consecutive prime gaps that are pairwise distinct (Erdős Problem #852).

Why it matters: Erdős asked whether h(x) exceeds a power of log x yet is o(log x); the question probes the fine structure of prime gaps and Hardy-Littlewood type heuristics.

- [Consecutive primes in tuples](https://doi.org/10.4064/aa167-3-4): Main research objective: Estimate h(x), the longest string of consecutive prime gaps that are pairwise distinct (Erdős Problem #852). Task connection: Among primes below 10^8 the longest string has 21 distinct gaps, so the task recovers it.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Among primes below 10^8 the longest string has 21 distinct gaps, so the task recovers it. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4064/aa167-3-4 (William D. Banks, Tristan Freiberg and Caroline L. Turnage-Butterbaugh, Consecutive primes in tuples (2015). Crossref record inspected (the paper produces arbitrarily long strings of consecutive primes with strictly increasing gaps, answering a question of Erdős and Turán). Erdős Problem #852 page inspected (Brun's sieve gives h(x) -> infinity). OEIS A053597 and its record positions A078515 inspected; the longest string of distinct gaps among primes below 10^8 was recomputed locally with a complete sieve: 21 gaps, starting at the prime 69931991, consistent with the OEIS records. Among primes below 10^8 the longest string has 21 distinct gaps, so the task recovers it.)
- archive: https://www.erdosproblems.com/852 (Erdős Problem #852 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000705 (JSP-000705; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case recomputed locally from a complete sieve and consistent with OEIS A053597/A078515.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
