# Twenty points with no four collinear and small general-position subsets

**Source collection:** [Problem-bank constructions: discrete geometry and analysis: source-based research tasks](../../papers/science-prize_g.md)\
**Task id:** `science-no-four-collinear-general-position-20`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> exactly 20 distinct integer points [x, y] with |x|, |y| <= 100 and no four collinear. The score is the largest subset with no three collinear (exact branch and bound). Minimize. A valid configuration with score s certifies g(20) <= s; no exact value for n = 20 is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 20 distinct integer points [x, y] with |x|, |y| <= 100 and no four collinear. The score is the largest subset with no three collinear (exact branch and bound). Minimize.

## State of the art

No documented value for n = 20; asymptotically n^(1/2) log n << g(n) << n^(5/6+o(1)).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #589](https://www.erdosproblems.com/589), status: open.

- [On the number of points in general position in the plane](https://doi.org/10.19086/da.4438), József Balogh, József Solymosi (2018)

Parameters: `{"n": 20, "bound": 100}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate the largest subset with no three collinear guaranteed in sets with no four collinear.

Why it matters: Erdős Problem #589 connects incidence geometry with density Hales-Jewett type results.

- [On the number of points in general position in the plane](https://doi.org/10.19086/da.4438): Main research objective: Estimate the largest subset with no three collinear guaranteed in sets with no four collinear. Task connection: A valid configuration with score s certifies g(20) <= s; no exact value for n = 20 is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid configuration with score s certifies g(20) <= s; no exact value for n = 20 is documented. Exact local certificates are not Lean proofs; floating-point scores are stated as such. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.19086/da.4438 (József Balogh and József Solymosi, On the number of points in general position in the plane (2018). Crossref record inspected; Erdős Problem #589 page inspected: n^(1/2) log n << g(n) = o(n) (Füredi) and g(n) << n^(5/6+o(1)) (Balogh and Solymosi). A valid configuration with score s certifies g(20) <= s; no exact value for n = 20 is documented.)
- archive: https://www.erdosproblems.com/589 (Erdős Problem #589 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000478 (JSP-000478; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 20 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
