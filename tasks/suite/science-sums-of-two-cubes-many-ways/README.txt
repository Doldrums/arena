# Integers up to 5*10^16 with many representations as sums of two positive cubes

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-sums-of-two-cubes-many-ways`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'m': m, 'pairs': [[a, b], ...]} with 2 <= m <= 5*10^16 and distinct pairs of positive integers a <= b with a^3 + b^3 = m (checked exactly). Maximize the number of pairs; the optimum is 5, attained only by the fifth taxicab number 48988659276962496. Below 5*10^16 the maximum is 5, attained only by the fifth taxicab number, so the task is a calibrated rediscovery of Ta(5).

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'m': m, 'pairs': [[a, b], ...]} with 2 <= m <= 5*10^16 and distinct pairs of positive integers a <= b with a^3 + b^3 = m (checked exactly). Maximize the number of pairs; the optimum is 5, attained only by the fifth taxicab number 48988659276962496.

## State of the art

No integer below 5*10^16 is a sum of two positive cubes in six ways, and 48988659276962496 is the only one with five (Wilson 1999, exhaustive search).

Reference value: proven optimum `5` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #829](https://www.erdosproblems.com/829), status: open.

- [The Fifth Taxicab Number is 48988659276962496](https://cs.uwaterloo.ca/journals/JIS/wilson10.html), David W. Wilson (1999)
- [OEIS A011541: Taxicab numbers](https://oeis.org/A011541)
- [Cubic Thue Equations with Many Solutions](https://doi.org/10.1093/imrn/rnn040), C. L. Stewart (2008)

Parameters: `{"bound": 50000000000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how many representations an integer can have as a sum of two cubes (Erdős Problem #829 asks whether the count is at most polylogarithmic).

Why it matters: Representation counts of binary cubic forms are tied to Thue equations and ranks of elliptic curves; Erdős asked for polylogarithmic upper bounds.

- [The Fifth Taxicab Number is 48988659276962496](https://cs.uwaterloo.ca/journals/JIS/wilson10.html): Main research objective: Determine how many representations an integer can have as a sum of two cubes (Erdős Problem #829 asks whether the count is at most polylogarithmic). Task connection: Below 5*10^16 the maximum is 5, attained only by the fifth taxicab number, so the task is a calibrated rediscovery of Ta(5).

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Below 5*10^16 the maximum is 5, attained only by the fifth taxicab number, so the task is a calibrated rediscovery of Ta(5). Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://cs.uwaterloo.ca/journals/JIS/wilson10.html (David W. Wilson, The Fifth Taxicab Number is 48988659276962496 (1999). Journal of Integer Sequences article inspected: Wilson's exhaustive search listed every 3-, 4- and 5-way sum of two positive cubes below 5*10^16, and the only 5-way sum found was Ta(5) = 48988659276962496, so no integer below 5*10^16 has six representations. Erdős Problem #829 page inspected (Mordell: unbounded; Mahler: more than (log n)^(1/4) representations infinitely often; Stewart: (log n)^(11/13)). OEIS A011541 inspected. Below 5*10^16 the maximum is 5, attained only by the fifth taxicab number, so the task is a calibrated rediscovery of Ta(5).)
- archive: https://www.erdosproblems.com/829 (Erdős Problem #829 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000685 (JSP-000685; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; unordered representations by positive cubes (the taxicab convention).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
