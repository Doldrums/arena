# Two-colourings without a monochromatic 3-cube (rediscovering R(Q3,Q3) = 13)

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-cube-graph`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'colors': [...]}: colour 0 or 1 for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 13. Neither colour class may contain the 8-vertex cube graph Q3 as a subgraph. Maximize n; the proven optimum is 12. Recovering a 12-vertex colouring with no monochromatic Q3 rediscovers the extremal lower bound.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'colors': [...]}: colour 0 or 1 for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 13. Neither colour class may contain the 8-vertex cube graph Q3 as a subgraph. Maximize n; the proven optimum is 12.

## State of the art

R(Q3,Q3) = 13 (Harborth and Krause lower bound; Lidický and Pfender upper bound).

Reference value: proven optimum `12` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #181](https://www.erdosproblems.com/181), status: open.

- [Semidefinite Programming and Ramsey Numbers](https://doi.org/10.1137/18M1169473), Bernard Lidický, Florian Pfender (2021)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"max_vertices": 13}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine Ramsey numbers of hypercubes and other small graphs.

Why it matters: Whether R(Q_n) = O(2^n) is Erdős Problem #181; R(Q3,Q3) = 13 is the only nontrivial exactly known hypercube case.

- [Semidefinite Programming and Ramsey Numbers](https://doi.org/10.1137/18M1169473): Main research objective: Determine Ramsey numbers of hypercubes and other small graphs. Task connection: Recovering a 12-vertex colouring with no monochromatic Q3 rediscovers the extremal lower bound.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Recovering a 12-vertex colouring with no monochromatic Q3 rediscovers the extremal lower bound. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1137/18M1169473 (Bernard Lidický and Florian Pfender, Semidefinite Programming and Ramsey Numbers (2021). Crossref and arXiv records inspected; survey DS1.18 items 5.13 and 5.17.n inspected: R(Q3,Q3) = 13, lower bound construction by Harborth and Krause, upper bound by Lidický and Pfender. Recovering a 12-vertex colouring with no monochromatic Q3 rediscovers the extremal lower bound.)
- archive: https://www.erdosproblems.com/181 (Erdős Problem #181 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000175 (JSP-000175; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; the published construction is not copied.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
