# Longest run of consecutive integers with distinct divisor counts below 10^10

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-distinct-divisor-counts-run-1e10`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'start': s, 'length': k} with s >= 1, 1 <= k <= 40 and s + k - 1 <= 10^10. The divisor counts tau(s), ..., tau(s + k - 1) must be pairwise distinct (exact factorization). Maximize k; the optimum is 14 (first run at 1745175039). Runs ending below 10^10 have at most 14 terms (first at 1745175039), so the task recovers such a run.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'start': s, 'length': k} with s >= 1, 1 <= k <= 40 and s + k - 1 <= 10^10. The divisor counts tau(s), ..., tau(s + k - 1) must be pairwise distinct (exact factorization). Maximize k; the optimum is 14 (first run at 1745175039).

## State of the art

F(10^10) = 14: the first run of 14 integers with distinct divisor counts starts at 1745175039 and the first run of 15 at 31287652672 (OEIS A048892).

Reference value: proven optimum `14` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #945](https://www.erdosproblems.com/945), status: open.

- [OEIS A048892: Start of n consecutive integers with distinct number of divisors](https://oeis.org/A048892)
- [The Distribution of Values of the Divisor Function d(n)](https://doi.org/10.1112/plms/s3-2.1.257), P. Erdős, L. Mirsky (1952)

Parameters: `{"bound": 10000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate F(x), the longest run of consecutive integers up to x with pairwise distinct numbers of divisors.

Why it matters: Erdős and Mirsky's problem (Erdős Problem #945) measures how irregular the divisor function is on short intervals; whether F(x) is polylogarithmic is open.

- [The Distribution of Values of the Divisor Function d(n)](https://doi.org/10.1112/plms/s3-2.1.257): Main research objective: Estimate F(x), the longest run of consecutive integers up to x with pairwise distinct numbers of divisors. Task connection: Runs ending below 10^10 have at most 14 terms (first at 1745175039), so the task recovers such a run.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Runs ending below 10^10 have at most 14 terms (first at 1745175039), so the task recovers such a run. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1112/plms/s3-2.1.257 (P. Erdős and L. Mirsky, The Distribution of Values of the Divisor Function d(n) (1952). Crossref record inspected; Erdős Problem #945 page inspected (Erdős and Mirsky proved (log x)^(1/2)/log log x << F(x) << exp(O((log x)^(1/2)/log log x)); Beker improved the upper bound; Guy B18). OEIS A048892 inspected: the first run of 14 consecutive integers with distinct divisor counts starts at 1745175039 and the first run of 15 at 31287652672 > 10^10, so F(10^10) = 14. Runs ending below 10^10 have at most 14 terms (first at 1745175039), so the task recovers such a run.)
- archive: https://www.erdosproblems.com/945 (Erdős Problem #945 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000786 (JSP-000786; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS first-occurrence table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
