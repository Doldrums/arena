# Triangle-free graphs without independent 10-sets (Ramsey number R(3,10))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-triangle-versus-independent-ten`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 41. It must contain no triangle and no independent set of 10 vertices; both conditions are checked by exact branch and bound. Maximize n. A valid graph on n vertices certifies R(3,10) > n. The survey records 39 as the largest known order, and R(3,10) <= 41 limits any valid graph to 40 vertices.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 41. It must contain no triangle and no independent set of 10 vertices; both conditions are checked by exact branch and bound. Maximize n.

## State of the art

Largest known triangle-free graph with no independent 10-set has 39 vertices (Exoo 1989), so 40 <= R(3,10); Angeltveit (2025) proved R(3,10) <= 41. A 40-vertex graph would prove R(3,10) = 41.

Reference value: best known value `39` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #165](https://www.erdosproblems.com/165), status: open (asymptotics of R(3,k)).

- [On Two Classical Ramsey Numbers of the Form R(3,n)](https://doi.org/10.1137/0402043), Geoffrey Exoo (1989)
- [R(3,10) <= 41](https://doi.org/10.37236/12936), Vigleik Angeltveit (2025)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"clique": 3, "independent": 10, "max_vertices": 41}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the Ramsey number R(3,10), the least n forcing a triangle or an independent 10-set.

Why it matters: R(3,k) is the central off-diagonal Ramsey function (Erdős Problem #165), and R(3,10) is the smallest classical two-colour case with an unknown value; a 40-vertex graph would settle it.

- [R(3,10) <= 41](https://doi.org/10.37236/12936): Main research objective: Determine the Ramsey number R(3,10), the least n forcing a triangle or an independent 10-set. Task connection: A valid graph on n vertices certifies R(3,10) > n. The survey records 39 as the largest known order, and R(3,10) <= 41 limits any valid graph to 40 vertices.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid graph on n vertices certifies R(3,10) > n. The survey records 39 as the largest known order, and R(3,10) <= 41 limits any valid graph to 40 vertices. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.37236/12936 (Vigleik Angeltveit, R(3,10) <= 41 (2025). Crossref record for the Electronic Journal of Combinatorics article inspected; Radziszowski's survey DS1.18 (Table Ia, item 2.1.d) inspected: 40 <= R(3,10) <= 41, lower bound from Exoo (1989), at least 43 million (3,10)-graphs on 39 vertices known. A valid graph on n vertices certifies R(3,10) > n. The survey records 39 as the largest known order, and R(3,10) <= 41 limits any valid graph to 40 vertices.)
- archive: https://www.erdosproblems.com/165 (Erdős Problem #165 (open (asymptotics of R(3,k))); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000162 (JSP-000162; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The Andrásfai starter has 26 vertices and is far below the published 39-vertex constructions, which are not copied.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
