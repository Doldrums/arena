# Few prime factors across pairwise sums

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-pair-sum-prime-diversity-12`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> n=12 distinct positive integers <=maximum=10000. Factor every sum of two DISTINCT elements, union all prime factors and minimize the number of distinct primes. Choose 12 distinct positive integers at most 10000; minimize the number of distinct primes dividing sums of distinct-index pairs. Equal-index sums are excluded.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> n=12 distinct positive integers <=maximum=10000. Factor every sum of two DISTINCT elements, union all prime factors and minimize the number of distinct primes.

## State of the art

No documented minimum for 12-element sets. Erdős and Turán proved that the number of distinct primes dividing the product of pairwise sums grows at least like log n; Erdős Problem #126, whether it grows faster, has been answered affirmatively.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #126](https://www.erdosproblems.com/126), status: proved (Lean).

- [On a Problem in the Elementary Theory of Numbers](https://users.renyi.hu/~p_erdos/1934-03.pdf), Paul Erdős, Paul Turán (1934)

Parameters: `{"n": 12, "maximum": 10000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Relate the size of an integer set to the number of primes dividing its pairwise sums.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [On a Problem in the Elementary Theory of Numbers](https://users.renyi.hu/~p_erdos/1934-03.pdf): Main research objective: Relate the size of an integer set to the number of primes dividing its pairwise sums. Task connection: Choose 12 distinct positive integers at most 10000; minimize the number of distinct primes dividing sums of distinct-index pairs. Equal-index sums are excluded.

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

- paper: https://users.renyi.hu/~p_erdos/1934-03.pdf (Paul Erdős and Paul Turán, On a Problem in the Elementary Theory of Numbers. American Mathematical Monthly 41 (1934), 608–611; full text, initial pair-sum prime-divisor problem inspected. The opening credits its original oral proposal to G. Grünwald and D. Lázár.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000133 (JSP-000133; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Choose 12 distinct positive integers at most 10000; minimize the number of distinct primes dividing sums of distinct-index pairs. Equal-index sums are excluded.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
