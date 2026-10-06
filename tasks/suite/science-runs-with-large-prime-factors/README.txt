# Runs of consecutive integers each with a prime factor larger than the run length (start at most 10^4)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-runs-with-large-prime-factors`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'start': s, 'length': k} with 1 <= s <= 10^4 and 1 <= k <= 200. Each of s, ..., s + k - 1 must have a prime factor greater than k (exact factorization). Maximize k; the optimum is 30 (6961, ..., 6990). For runs starting at most 10^4 the maximum is 30, so the task recovers the run 6961..6990 or an equivalent.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'start': s, 'length': k} with 1 <= s <= 10^4 and 1 <= k <= 200. Each of s, ..., s + k - 1 must have a prime factor greater than k (exact factorization). Maximize k; the optimum is 30 (6961, ..., 6990).

## State of the art

The longest run starting at most 10^4 in which each term has a prime factor exceeding the run length has 30 terms (first 6961..6990); the first run of 31 starts at 10305 (OEIS A327909).

Reference value: proven optimum `30` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #962](https://www.erdosproblems.com/962), status: open.

- [OEIS A327909: Smallest start of a run of n or more integers having a prime factor greater than n](https://oeis.org/A327909)
- [An improved lower bound on Erdős problem #962](https://github.com/QuanyuTang/erdos-problem-962/blob/main/On_Erd%C5%91s_Problem_962.pdf), Quanyu Tang (2025)

Parameters: `{"bound": 10000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate k(n), the longest run up to n in which every term has a prime factor exceeding the run length (Erdős Problem #962).

Why it matters: The problem sharpens Sylvester-Schur type theorems on prime factors of consecutive integers and measures the distribution of smooth numbers in short intervals.

- [An improved lower bound on Erdős problem #962](https://github.com/QuanyuTang/erdos-problem-962/blob/main/On_Erd%C5%91s_Problem_962.pdf): Main research objective: Estimate k(n), the longest run up to n in which every term has a prime factor exceeding the run length (Erdős Problem #962). Task connection: For runs starting at most 10^4 the maximum is 30, so the task recovers the run 6961..6990 or an equivalent.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For runs starting at most 10^4 the maximum is 30, so the task recovers the run 6961..6990 or an equivalent. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://github.com/QuanyuTang/erdos-problem-962/blob/main/On_Erd%C5%91s_Problem_962.pdf (Quanyu Tang, An improved lower bound on Erdős problem #962 (2025). Research note linked from the Erdős Problems page inspected (proves log k(n) >= (1/sqrt 2 - o(1)) sqrt(log n log log n)). Erdős Problem #962 page inspected: k(n) is the largest k such that some m <= n has m+1, ..., m+k each divisible by a prime > k; Erdős had log k(n) >> (log n log log n)^(1/2) and Tao proved k(n) <= (1+o(1)) n^(1/2). OEIS A327909 inspected: the smallest start of a run of n or more integers each with a prime factor greater than n is 6961 for n = 30 and 10305 for n = 31 (the sequence is nondecreasing), so the longest run starting at most 10^4 has 30 terms. For runs starting at most 10^4 the maximum is 30, so the task recovers the run 6961..6990 or an equivalent.)
- archive: https://www.erdosproblems.com/962 (Erdős Problem #962 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000800 (JSP-000800; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS first-occurrence table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
