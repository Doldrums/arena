# Smallest set whose pairwise sums cover 0..212

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-additive-two-basis-212`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> distinct integers in 0..212 such that every integer 0..212 equals a + b for some a <= b in the set (a = b allowed). Minimize the size; the optimum is 25. For n = 212 the minimum is 25, so the task recovers an extremal basis.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 0..212 such that every integer 0..212 equals a + b for some a <= b in the set (a = b allowed). Minimize the size; the optimum is 25.

## State of the art

The least 2-basis of {0..212} has 25 elements (OEIS A066063; two-stamp range 212 needs 24 denominations, A001212).

Reference value: proven optimum `25` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #791](https://www.erdosproblems.com/791), status: open.

- [OEIS A066063: Size of the smallest subset S of {0..n} such that each element is the sum of two elements of S](https://oeis.org/A066063)
- [Some Extremal Postage Stamp Bases](https://cs.uwaterloo.ca/journals/JIS/VOL13/Challis/challis6.html), Michael F. Challis, John P. Robinson (2010)
- [An improved lower bound for finite additive 2-bases](https://doi.org/10.1016/j.jnt.2016.11.011), Jukka Kohonen (2017)

Parameters: `{"n": 212}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate g(n), the smallest additive 2-basis of {0..n} (Rohrbach's problem, Erdős Problem #791).

Why it matters: Finite additive bases (the postage stamp problem) are classical in additive number theory; the asymptotic constant is open.

- [Some Extremal Postage Stamp Bases](https://cs.uwaterloo.ca/journals/JIS/VOL13/Challis/challis6.html): Main research objective: Estimate g(n), the smallest additive 2-basis of {0..n} (Rohrbach's problem, Erdős Problem #791). Task connection: For n = 212 the minimum is 25, so the task recovers an extremal basis.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 212 the minimum is 25, so the task recovers an extremal basis. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://cs.uwaterloo.ca/journals/JIS/VOL13/Challis/challis6.html (Michael F. Challis and John P. Robinson, Some Extremal Postage Stamp Bases (2010). Journal of Integer Sequences article and OEIS A066063/A001212 inspected: the two-stamp postage problem has optimal range 212 with 24 denominations and 196 with 23, and a basis of {0..n} is 0 together with a set of denominations, so the minimum size for n = 212 is 25. Erdős Problem #791 page inspected (Rohrbach's problem; (2.181+o(1))n <= g(n)^2 <= (3.458+o(1))n by Yu and Kohonen). For n = 212 the minimum is 25, so the task recovers an extremal basis.)
- archive: https://www.erdosproblems.com/791 (Erdős Problem #791 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000650 (JSP-000650; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from published exhaustive postage-stamp computations.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
