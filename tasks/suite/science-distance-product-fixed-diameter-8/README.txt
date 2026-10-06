# Eight planar points maximizing the product of distances at fixed diameter

**Source collection:** [Problem-bank constructions: discrete geometry and analysis: source-based research tasks](../../papers/science-prize_g.md)\
**Task id:** `science-distance-product-fixed-diameter-8`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 8 distinct points [x, y] (floats, |coordinate| < 10^6). The score is Delta/n^n, where Delta is the product over ordered pairs of distances after scaling the set to diameter 2; the regular octagon scores exactly 1. Maximize. Scores above 1 beat the regular octagon; the paper's constructions show this is possible, but no value for n = 8 is recorded here.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 8 distinct points [x, y] (floats, |coordinate| < 10^6). The score is Delta/n^n, where Delta is the product over ordered pairs of distances after scaling the set to diameter 2; the regular octagon scores exactly 1. Maximize.

## State of the art

No documented optimum for n = 8; regular octagon = 1 and improvements exist for all even n >= 4 (Hu-Tang; Cambie; Cambie, Decadt, Dong, Hu and Tang 2026).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1045](https://www.erdosproblems.com/1045), status: open.

- [On the maximum product of distances of diameter 2 point sets](https://arxiv.org/abs/2603.07088), S. Cambie, A. Decadt, Y. Dong, T. Hu, Q. Tang (2026)
- [Erdős Problem #1045](https://www.erdosproblems.com/1045)

Parameters: `{"n": 8}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximum product of pairwise distances of n planar points of diameter 2.

Why it matters: Erdős, Herzog and Piranian's problem (Erdős Problem #1045) links discriminants of polynomials with geometry; the even case was only recently shown to differ from regular polygons.

- [On the maximum product of distances of diameter 2 point sets](https://arxiv.org/abs/2603.07088): Main research objective: Determine the maximum product of pairwise distances of n planar points of diameter 2. Task connection: Scores above 1 beat the regular octagon; the paper's constructions show this is possible, but no value for n = 8 is recorded here.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Scores above 1 beat the regular octagon; the paper's constructions show this is possible, but no value for n = 8 is recorded here. Exact local certificates are not Lean proofs; floating-point scores are stated as such. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2603.07088 (Stijn Cambie, Aron Decadt, Yanting Dong, Tianchi Hu and Quanyu Tang, On the maximum product of distances of diameter 2 point sets (2026). arXiv abstract inspected (extremal sets are convex polygons; constructions drastically improve on regular n-gons for even n); Erdős Problem #1045 page inspected: the regular polygon gives Delta = n^n for even n and is not optimal for even n >= 4 (Hu and Tang; Cambie), and liminf max Delta/n^n >= 1.268 for even n. Scores above 1 beat the regular octagon; the paper's constructions show this is possible, but no value for n = 8 is recorded here.)
- archive: https://www.erdosproblems.com/1045 (Erdős Problem #1045 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000867 (JSP-000867; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Floating-point score (relative accuracy about 1e-12). No documented value for n = 8 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
