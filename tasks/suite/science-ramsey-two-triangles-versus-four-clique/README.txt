# Three-colourings avoiding two triangle colours and a K4 (rediscovering R(3,3,4) = 30)

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-two-triangles-versus-four-clique`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'colors': [...]}: one colour in {0,1,2} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 30. Colours 0 and 1 must be triangle-free and colour 2 must be K4-free. Maximize n; the proven optimum is 29. A valid colouring of K_n certifies R(3,3,4) > n; the optimum is 29 vertices.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'colors': [...]}: one colour in {0,1,2} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 30. Colours 0 and 1 must be triangle-free and colour 2 must be K4-free. Maximize n; the proven optimum is 29.

## State of the art

R(3,3,4) = 30 (lower bound Kalbfleisch 1966, upper bound Codish, Frank, Itzhakov and Miller 2016).

Reference value: proven optimum `29` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #553](https://www.erdosproblems.com/553), status: proved (Alon and Rödl).

- [Computing the Ramsey number R(4,3,3) using abstraction and symmetry breaking](https://doi.org/10.1007/s10601-016-9240-3), Michael Codish, Michael Frank, Avraham Itzhakov, Alice Miller (2016)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"clique": 4, "max_vertices": 30}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the three-colour Ramsey number R(3,3,4).

Why it matters: Erdős Problem #553 compares R(3,3,n) with R(3,n); R(3,3,4) = 30 was the long-open smallest case, settled by a large symmetry-broken computation.

- [Computing the Ramsey number R(4,3,3) using abstraction and symmetry breaking](https://doi.org/10.1007/s10601-016-9240-3): Main research objective: Determine the three-colour Ramsey number R(3,3,4). Task connection: A valid colouring of K_n certifies R(3,3,4) > n; the optimum is 29 vertices.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid colouring of K_n certifies R(3,3,4) > n; the optimum is 29 vertices. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/s10601-016-9240-3 (Michael Codish, Michael Frank, Avraham Itzhakov and Alice Miller, Computing the Ramsey number R(4,3,3) using abstraction and symmetry breaking (2016). Crossref record inspected; survey DS1.18 item 6.1.2.b inspected: Kalbfleisch (1966) proved 30 <= R(3,3,4) and Codish, Frank, Itzhakov and Miller (2016) completed R(3,3,4) = 30. A valid colouring of K_n certifies R(3,3,4) > n; the optimum is 29 vertices.)
- archive: https://www.erdosproblems.com/553 (Erdős Problem #553 (proved (Alon and Rödl)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000444 (JSP-000444; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; Kalbfleisch's 29-vertex colouring is published and not copied.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
