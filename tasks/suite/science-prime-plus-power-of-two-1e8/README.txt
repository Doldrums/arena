# Integers up to 10^8 with many representations n = p + 2^k

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-prime-plus-power-of-two-1e8`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> an integer n with 3 <= n <= 10^8. The score is the number of k >= 0 with n - 2^k prime (deterministic Miller-Rabin). Maximize; the optimum is 19 (first at 53999715). For n <= 10^8 the maximum is 19, so the task recovers such an integer.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> an integer n with 3 <= n <= 10^8. The score is the number of k >= 0 with n - 2^k prime (deterministic Miller-Rabin). Maximize; the optimum is 19 (first at 53999715).

## State of the art

For n <= 10^8 at most 19 values n - 2^k are prime; first at 53999715 (OEIS A109926).

Reference value: proven optimum `19` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #236](https://www.erdosproblems.com/236), status: open.

- [OEIS A109926: Least k such that k - 2^r is prime for n values of r](https://oeis.org/A109926)
- [On integers of the form 2^k + p and some related problems](https://users.renyi.hu/~p_erdos/1950-07.pdf), Paul Erdős (1950)
- [Über einige Sätze der additiven Zahlentheorie](https://doi.org/10.1007/BF01449161), N. P. Romanoff (1934)

Parameters: `{"bound": 100000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how many representations n = p + 2^k an integer can have (Erdős Problem #236).

Why it matters: The problem grew out of Romanoff's theorem and led Erdős to covering congruences (odd numbers not of the form p + 2^k); f(n) = o(log n) is open.

- [On integers of the form 2^k + p and some related problems](https://users.renyi.hu/~p_erdos/1950-07.pdf): Main research objective: Determine how many representations n = p + 2^k an integer can have (Erdős Problem #236). Task connection: For n <= 10^8 the maximum is 19, so the task recovers such an integer.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n <= 10^8 the maximum is 19, so the task recovers such an integer. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://users.renyi.hu/~p_erdos/1950-07.pdf (Paul Erdős, On integers of the form 2^k + p and some related problems (1950). Paper located in the Rényi Institute archive (Summa Brasil. Math. 2 (1950)). Erdős Problem #236 page inspected (Erdős proved f(n) >> log log n infinitely often; whether f(n) = o(log n) is open; values are OEIS A109925). OEIS A109926 inspected: the least n with 19 representations is 53999715, with 20 it is 2282745465, and a(n) > 10^10 for n >= 21 (Donovan Johnson), so the maximum for n <= 10^8 is 19. For n <= 10^8 the maximum is 19, so the task recovers such an integer.)
- archive: https://www.erdosproblems.com/236 (Erdős Problem #236 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0201-0300.md#JSP-000209 (JSP-000209; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS first-occurrence table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
