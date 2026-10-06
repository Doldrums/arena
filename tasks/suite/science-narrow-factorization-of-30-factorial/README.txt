# Narrowest factorization of 30! into increasing factors

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-narrow-factorization-of-30-factorial`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> strictly increasing positive integers a_1 < ... < a_t with 2 <= t <= 30 and product exactly 30!. Minimize a_t - a_1; the optimum is 27. For n = 30 the optimum span is 27, so the task recovers an optimal factorization.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> strictly increasing positive integers a_1 < ... < a_t with 2 <= t <= 30 and product exactly 30!. Minimize a_t - a_1; the optimum is 27.

## State of the art

f(30) = 27 (OEIS A388302).

Reference value: proven optimum `27` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #393](https://www.erdosproblems.com/393), status: open.

- [OEIS A388302: Smallest m >= 1 such that n! = b_1*...*b_t with b_1 < ... < b_t and m = b_t - b_1](https://oeis.org/A388302)
- [On the equation P(x) = n! and a question of Erdős](https://doi.org/10.1016/0022-314X(92)90020-P), Daniel Berend, Charles F. Osgood (1992)
- [Power savings for counting solutions to polynomial-factorial equations](https://doi.org/10.1016/j.aim.2023.109021), Hung M. Bui, Kyle Pratt, Alexandru Zaharescu (2023)

Parameters: `{"n": 30}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand how narrow an interval can contain a factorization of n! into distinct factors (Erdős Problem #393).

Why it matters: The problem links factorials with polynomial-factorial Diophantine equations such as Brocard's problem and with smooth numbers.

- [On the equation P(x) = n! and a question of Erdős](https://doi.org/10.1016/0022-314X(92)90020-P): Main research objective: Understand how narrow an interval can contain a factorization of n! into distinct factors (Erdős Problem #393). Task connection: For n = 30 the optimum span is 27, so the task recovers an optimal factorization.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 30 the optimum span is 27, so the task recovers an optimal factorization. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0022-314X(92)90020-P (Daniel Berend and Charles F. Osgood, On the equation P(x) = n! and a question of Erdős (1992). Crossref records inspected (Berend and Osgood 1992; Bui, Pratt and Zaharescu 2023). Erdős Problem #393 page inspected: f(n) is the least m with n! = a_1...a_t, a_1 < ... < a_t = a_1 + m; Erdős and Graham did not know whether f(n) = 1 infinitely often, and f(n) = m has o(N) solutions n <= N for each m. OEIS A388302 inspected: f(30) = 27. For n = 30 the optimum span is 27, so the task recovers an optimal factorization.)
- archive: https://www.erdosproblems.com/393 (Erdős Problem #393 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0301-0400.md#JSP-000324 (JSP-000324; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
