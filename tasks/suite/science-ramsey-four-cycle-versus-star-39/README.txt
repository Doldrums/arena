# Four-cycle-free graphs of large minimum degree (Ramsey number R(C4,K1,39))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-four-cycle-versus-star-39`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 47, containing no C4, whose minimum degree is at least n - 39 (so the complement has no K1,39). Maximize n. A C4-free graph on n vertices with minimum degree at least n-39 certifies R(C4,K1,39) > n. The value is known to be 46 or 47, so 46 vertices would settle it.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 47, containing no C4, whose minimum degree is at least n - 39 (so the complement has no K1,39). Maximize n.

## State of the art

46 <= R(C4,K1,39) <= 47: Wu, Sun and Radziszowski (2015) gave the lower bound (a valid 45-vertex graph), Dybizbański and Dzido (2014) the upper bound; still open after Boza's determination of all n <= 38.

Reference value: best known value `45` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #552](https://www.erdosproblems.com/552), status: open ($100).

- [Wheel and star-critical Ramsey numbers for quadrilateral](https://doi.org/10.1016/j.dam.2015.01.003), Yali Wu, Yongqi Sun, Stanislaw P. Radziszowski (2015)
- [On Some Ramsey Numbers for Quadrilaterals Versus Wheels](https://doi.org/10.1007/s00373-013-1293-0), Janusz Dybizbański, Tomasz Dzido (2014)
- [Exact Values and Bounds for Ramsey Numbers of C4 Versus a Star Graph](https://arxiv.org/abs/2409.12770), Luis Boza (2024)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"star": 39, "max_vertices": 47}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the Ramsey numbers R(C4,K1,n) of the four-cycle versus stars.

Why it matters: Erdős Problem #552 asks to determine R(C4,S_n); n = 39 is the smallest case left open after Boza's 2024 computations.

- [Exact Values and Bounds for Ramsey Numbers of C4 Versus a Star Graph](https://arxiv.org/abs/2409.12770): Main research objective: Determine the Ramsey numbers R(C4,K1,n) of the four-cycle versus stars. Task connection: A C4-free graph on n vertices with minimum degree at least n-39 certifies R(C4,K1,39) > n. The value is known to be 46 or 47, so 46 vertices would settle it.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A C4-free graph on n vertices with minimum degree at least n-39 certifies R(C4,K1,39) > n. The value is known to be 46 or 47, so 46 vertices would settle it. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2409.12770 (Luis Boza, Exact Values and Bounds for Ramsey Numbers of C4 Versus a Star Graph (2024). arXiv abstract inspected (v2, 2026): all previously unknown values R(C4,K1,n) for n <= 38 are determined. Survey DS1.18 Table IVa inspected: R(C4,K1,39) is 46 or 47 (lower bound [WuSR], upper bound [DyDz2]). A C4-free graph on n vertices with minimum degree at least n-39 certifies R(C4,K1,39) > n. The value is known to be 46 or 47, so 46 vertices would settle it.)
- archive: https://www.erdosproblems.com/552 (Erdős Problem #552 (open ($100)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000443 (JSP-000443; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The empty-graph starter meets only the trivial bound 39.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
