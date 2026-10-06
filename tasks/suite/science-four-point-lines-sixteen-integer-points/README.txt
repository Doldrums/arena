# Sixteen integer points with many four-point lines and no five collinear

**Source collection:** [Problem-bank constructions: discrete geometry and analysis: source-based research tasks](../../papers/science-prize_g.md)\
**Task id:** `science-four-point-lines-sixteen-integer-points`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> exactly 16 distinct integer points [x, y] with |x|, |y| <= 1000 and no five collinear. Maximize the number of lines containing exactly four of the points (exact). Integer configurations are a restriction of the real problem; the real value 15 for n = 16 is an upper reference, not a documented integer optimum.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 16 distinct integer points [x, y] with |x|, |y| <= 1000 and no five collinear. Maximize the number of lines containing exactly four of the points (exact).

## State of the art

No documented value for integer points; for real configurations OEIS A006065 lists 15 four-point lines for 16 points.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #101](https://www.erdosproblems.com/101), status: open ($100).

- [OEIS A006065](https://oeis.org/A006065)
- [Many Collinear k-Tuples with no k+1 Collinear Points](https://doi.org/10.1007/s00454-013-9526-9), József Solymosi, Miloš Stojaković (2013)

Parameters: `{"n": 16, "bound": 1000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how many four-point lines a set with no five collinear points can have.

Why it matters: Erdős offered $100 for the question whether such lines are o(n^2) (Erdős Problem #101), disproved in the stated form only by an intricate construction.

- [Many Collinear k-Tuples with no k+1 Collinear Points](https://doi.org/10.1007/s00454-013-9526-9): Main research objective: Determine how many four-point lines a set with no five collinear points can have. Task connection: Integer configurations are a restriction of the real problem; the real value 15 for n = 16 is an upper reference, not a documented integer optimum.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Integer configurations are a restriction of the real problem; the real value 15 for n = 16 is an upper reference, not a documented integer optimum. Exact local certificates are not Lean proofs; floating-point scores are stated as such. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/s00454-013-9526-9 (József Solymosi and Miloš Stojaković, Many Collinear k-Tuples with no k+1 Collinear Points (2013). Crossref record inspected; Erdős Problem #101 ($100) page inspected: sets with no five on a line can have n^(2-O(1/sqrt(log n))) four-point lines (Solymosi and Stojaković). OEIS A006065 lists maximal numbers of 4-point lines for real configurations (15 for n = 16). Integer configurations are a restriction of the real problem; the real value 15 for n = 16 is an upper reference, not a documented integer optimum.)
- archive: https://www.erdosproblems.com/101 (Erdős Problem #101 (open ($100)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000114 (JSP-000114; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented integer optimum (reference label none); OEIS A006065 gives real-plane values.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
