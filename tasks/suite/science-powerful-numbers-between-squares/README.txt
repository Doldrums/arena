# Many powerful numbers strictly between consecutive squares (k <= 10^9)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-powerful-numbers-between-squares`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> an integer k with 1 <= k <= 10^9. The score is the number of powerful integers (p | n implies p^2 | n) strictly between k^2 and (k+1)^2, counted exactly through the unique form a^2 b^3 with b squarefree. Maximize; the optimum is 11 (first at k = 472532614). For k <= 10^9 the maximum is 11. Erdős's h(n) counts [n^2, (n+1)^2) and so also includes the square n^2; the task counts the open interval as in OEIS A119241.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> an integer k with 1 <= k <= 10^9. The score is the number of powerful integers (p | n implies p^2 | n) strictly between k^2 and (k+1)^2, counted exactly through the unique form a^2 b^3 with b squarefree. Maximize; the optimum is 11 (first at k = 472532614).

## State of the art

For k <= 10^9 at most 11 powerful numbers lie strictly between k^2 and (k+1)^2; first at k = 472532614 (OEIS A119242).

Reference value: proven optimum `11` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #942](https://www.erdosproblems.com/942), status: open.

- [OEIS A119242: Least number k such that there are exactly n powerful numbers between k^2 and (k+1)^2](https://oeis.org/A119242)
- [On the number of square-full integers between successive squares](https://doi.org/10.1112/S0025579300010056), P. Shiu (1980)
- [Sur la proximité des nombres puissants](https://doi.org/10.4064/aa114-2-4), Jean-Marie De Koninck, Florian Luca (2004)

Parameters: `{"bound": 1000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate the largest number of powerful numbers between consecutive squares (Erdős Problem #942).

Why it matters: Powerful numbers are central to the abc conjecture and to questions on consecutive powerful numbers; the growth of h(n) is open.

- [On the number of square-full integers between successive squares](https://doi.org/10.1112/S0025579300010056): Main research objective: Estimate the largest number of powerful numbers between consecutive squares (Erdős Problem #942). Task connection: For k <= 10^9 the maximum is 11. Erdős's h(n) counts [n^2, (n+1)^2) and so also includes the square n^2; the task counts the open interval as in OEIS A119241.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For k <= 10^9 the maximum is 11. Erdős's h(n) counts [n^2, (n+1)^2) and so also includes the square n^2; the task counts the open interval as in OEIS A119241. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1112/S0025579300010056 (P. Shiu, On the number of square-full integers between successive squares (1980). Crossref record inspected; OEIS A119242 inspected: the least k with exactly 11 powerful numbers strictly between k^2 and (k+1)^2 is 472532614, the least with 12 is 78102676912, and a(n) > 10^11 for n >= 13 (Donovan Johnson), so 11 is the maximum for k <= 10^9. Erdős Problem #942 page inspected (Shiu proved every count occurs with positive density; De Koninck and Luca gave growth rates for large counts). For k <= 10^9 the maximum is 11. Erdős's h(n) counts [n^2, (n+1)^2) and so also includes the square n^2; the task counts the open interval as in OEIS A119241.)
- archive: https://www.erdosproblems.com/942 (Erdős Problem #942 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000783 (JSP-000783; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; the open interval is counted (Erdős's h(n) is one larger).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
