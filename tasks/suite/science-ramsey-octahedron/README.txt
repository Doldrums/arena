# Two-colourings without a monochromatic octahedron K2,2,2 (R(K2,2,2))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-octahedron`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'colors': [...]}: colour 0 or 1 for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 31. Neither colour class may contain K2,2,2 as a (not necessarily induced) subgraph. Maximize n. A valid colouring of K_n certifies R(K2,2,2) > n. The record has 29 vertices; a 30-vertex colouring would prove R(K2,2,2) = 31.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'colors': [...]}: colour 0 or 1 for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 31. Neither colour class may contain K2,2,2 as a (not necessarily induced) subgraph. Maximize n.

## State of the art

30 <= R(K2,2,2,K2,2,2) <= 31: lower bound from Harborth and Krause's distance colourings, upper bound from Lidický and Pfender's semidefinite programming.

Reference value: best known value `29` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #163](https://www.erdosproblems.com/163), status: proved (Lee 2017).

- [Semidefinite Programming and Ramsey Numbers](https://doi.org/10.1137/18M1169473), Bernard Lidický, Florian Pfender (2021)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"max_vertices": 31}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine small graph Ramsey numbers, including the octahedron K2,2,2.

Why it matters: The octahedron is a small bounded-degeneracy graph; linear Ramsey bounds for such graphs are the Burr-Erdős conjecture (Erdős Problem #163, proved by Lee), while exact values need constructions.

- [Semidefinite Programming and Ramsey Numbers](https://doi.org/10.1137/18M1169473): Main research objective: Determine small graph Ramsey numbers, including the octahedron K2,2,2. Task connection: A valid colouring of K_n certifies R(K2,2,2) > n. The record has 29 vertices; a 30-vertex colouring would prove R(K2,2,2) = 31.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid colouring of K_n certifies R(K2,2,2) > n. The record has 29 vertices; a 30-vertex colouring would prove R(K2,2,2) = 31. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1137/18M1169473 (Bernard Lidický and Florian Pfender, Semidefinite Programming and Ramsey Numbers (2021). Crossref and arXiv records inspected; survey DS1.18 item 5.12 inspected: 30 <= R(K2,2,2,K2,2,2) <= 31 with the lower bound from Harborth and Krause's distance colourings and the upper bound from flag algebras [LidP]. A valid colouring of K_n certifies R(K2,2,2) > n. The record has 29 vertices; a 30-vertex colouring would prove R(K2,2,2) = 31.)
- archive: https://www.erdosproblems.com/163 (Erdős Problem #163 (proved (Lee 2017)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000161 (JSP-000161; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The Paley(17) starter is classical. Local checks found that the Paley colouring of K29 also avoids monochromatic octahedra, matching (not exceeding) the published bound.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
