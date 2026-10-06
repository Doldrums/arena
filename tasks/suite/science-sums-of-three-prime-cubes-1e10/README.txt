# Integers up to 10^10 with many representations as sums of three prime cubes

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-sums-of-three-prime-cubes-1e10`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'N': N, 'triples': [[p, q, r], ...]} with N <= 10^10 and distinct prime triples p <= q <= r (each at most 3000) with p^3 + q^3 + r^3 = N. Maximize the number of triples; the optimum is 4 (first at 999979163). For k = 3 and N <= 10^10 the maximum is 4, so the task recovers such an N.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'N': N, 'triples': [[p, q, r], ...]} with N <= 10^10 and distinct prime triples p <= q <= r (each at most 3000) with p^3 + q^3 + r^3 = N. Maximize the number of triples; the optimum is 4 (first at 999979163).

## State of the art

No N <= 10^10 is a sum of three prime cubes in more than 4 ways; the first with 4 is 999979163 (OEIS A385316; local enumeration).

Reference value: proven optimum `4` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #979](https://www.erdosproblems.com/979), status: open.

- [OEIS A385316: Smallest number that is the sum of 3 cubes of primes in exactly n ways](https://oeis.org/A385316)
- [On the Sum and Difference of Squares of Primes](https://doi.org/10.1112/jlms/s1-12.1.133), Paul Erdős (1937)

Parameters: `{"bound": 10000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether the number of representations n = p_1^k + ... + p_k^k by primes is unbounded (Erdős Problem #979).

Why it matters: Representation counts by prime powers probe the circle method in Waring-Goldbach problems; unboundedness for k >= 3 is open (Erdős's argument for k = 3 was never published).

- [On the Sum and Difference of Squares of Primes](https://doi.org/10.1112/jlms/s1-12.1.133): Main research objective: Decide whether the number of representations n = p_1^k + ... + p_k^k by primes is unbounded (Erdős Problem #979). Task connection: For k = 3 and N <= 10^10 the maximum is 4, so the task recovers such an N.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For k = 3 and N <= 10^10 the maximum is 4, so the task recovers such an N. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1112/jlms/s1-12.1.133 (Paul Erdős, On the Sum and Difference of Squares of Primes (1937). Crossref record inspected (Erdős proved the case k = 2: the number of representations n = p^2 + q^2 is unbounded). Erdős Problem #979 page inspected. OEIS A385316 inspected: the smallest numbers with exactly 1, ..., 5 representations as sums of three prime cubes are 24, 185527, 8627527, 999979163 and 10588881419. A local enumeration of all prime triples with cube sum at most 10^10 confirmed that no N <= 10^10 has more than 4. For k = 3 and N <= 10^10 the maximum is 4, so the task recovers such an N.)
- archive: https://www.erdosproblems.com/979 (Erdős Problem #979 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000812 (JSP-000812; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case (OEIS table and local enumeration).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
