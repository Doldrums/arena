# Point sets without an empty convex hexagon (rediscovering 29 points)

**Source collection:** [Problem-bank constructions: discrete geometry and analysis: source-based research tasks](../../papers/science-prize_g.md)\
**Task id:** `science-point-sets-without-empty-hexagon`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of 1..30 distinct integer points [x, y] with |x|, |y| <= 10^6 and no three collinear. No six points may form a convex hexagon with no other point inside (exact search over all convex chains anchored at their lowest vertex). Maximize the number of points; the optimum is 29. Overmars found 29-point sets without empty hexagons and Heule and Scheucher proved every 30-point set has one, so 29 is optimal.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of 1..30 distinct integer points [x, y] with |x|, |y| <= 10^6 and no three collinear. No six points may form a convex hexagon with no other point inside (exact search over all convex chains anchored at their lowest vertex). Maximize the number of points; the optimum is 29.

## State of the art

The maximum is 29: Overmars (2003) found 29 points without an empty hexagon and Heule and Scheucher (2024) proved g(6) = 30.

Reference value: proven optimum `29` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #216](https://www.erdosproblems.com/216), status: disproved (no g(k) for k >= 7); g(6) = 30.

- [Happy Ending: An Empty Hexagon in Every Set of 30 Points](https://doi.org/10.1007/978-3-031-57246-3_5), Marijn J. H. Heule, Manfred Scheucher (2024)
- [Finding Sets of Points without Empty Convex 6-Gons](https://doi.org/10.1007/s00454-002-2829-x), Mark Overmars (2003)

Parameters: `{"max_points": 30, "bound": 1000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the smallest number of points in general position that forces an empty convex hexagon.

Why it matters: The empty-hexagon number was a long-standing Erdős-Szekeres type question (Erdős Problem #216), settled in 2024 by a SAT computation.

- [Happy Ending: An Empty Hexagon in Every Set of 30 Points](https://doi.org/10.1007/978-3-031-57246-3_5): Main research objective: Determine the smallest number of points in general position that forces an empty convex hexagon. Task connection: Overmars found 29-point sets without empty hexagons and Heule and Scheucher proved every 30-point set has one, so 29 is optimal.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Overmars found 29-point sets without empty hexagons and Heule and Scheucher proved every 30-point set has one, so 29 is optimal. Exact local certificates are not Lean proofs; floating-point scores are stated as such. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/978-3-031-57246-3_5 (Marijn J. H. Heule and Manfred Scheucher, Happy Ending: An Empty Hexagon in Every Set of 30 Points (2024). Crossref records inspected for Heule-Scheucher (TACAS 2024) and Overmars (Discrete Comput. Geom. 2003); Erdős Problem #216 page inspected: g(5) = 10 (Harborth), empty hexagons exist in large sets (Nicolás; Gerken), g(6) = 30 (Heule and Scheucher), and no g(k) for k >= 7 (Horton). Overmars found 29-point sets without empty hexagons and Heule and Scheucher proved every 30-point set has one, so 29 is optimal.)
- archive: https://www.erdosproblems.com/216 (Erdős Problem #216 (disproved (no g(k) for k >= 7); g(6) = 30); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000198 (JSP-000198; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; Overmars' 29-point sets are published and not copied. The randomized starter has 14 points.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
