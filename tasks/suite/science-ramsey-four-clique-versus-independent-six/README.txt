# K4-free graphs without independent 6-sets (Ramsey number R(4,6))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-four-clique-versus-independent-six`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 40. It must contain no K4 and no independent set of 6 vertices, checked exactly. Maximize n. A valid graph on n vertices certifies R(4,6) > n. Exoo's 35-vertex graph is the published record; 36 vertices would be a new lower bound.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 40. It must contain no K4 and no independent set of 6 vertices, checked exactly. Maximize n.

## State of the art

Best known (4,6)-graph has 35 vertices (Exoo 2012), so R(4,6) >= 36; the upper bound R(4,6) <= 40 is from computations of Angeltveit and McKay reported in the survey.

Reference value: best known value `35` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #166](https://www.erdosproblems.com/166), status: proved (R(4,k) >> k^3/(log k)^O(1), Mattheus and Verstraete).

- [On the Ramsey Number R(4,6)](https://doi.org/10.37236/2102), Geoffrey Exoo (2012)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"clique": 4, "independent": 6, "max_vertices": 40}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the classical Ramsey number R(4,6).

Why it matters: R(4,k) growth was Erdős Problem #166 (now proved); R(4,6) is one of the smallest unknown classical Ramsey numbers and lower bounds come only from explicit constructions like this one.

- [On the Ramsey Number R(4,6)](https://doi.org/10.37236/2102): Main research objective: Determine the classical Ramsey number R(4,6). Task connection: A valid graph on n vertices certifies R(4,6) > n. Exoo's 35-vertex graph is the published record; 36 vertices would be a new lower bound.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid graph on n vertices certifies R(4,6) > n. Exoo's 35-vertex graph is the published record; 36 vertices would be a new lower bound. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.37236/2102 (Geoffrey Exoo, On the Ramsey Number R(4,6) (2012). Crossref record inspected; survey DS1.18 Tables Ia/Ib inspected: 36 <= R(4,6) <= 40, lower bound [Ex19], upper bound by Angeltveit and McKay. A valid graph on n vertices certifies R(4,6) > n. Exoo's 35-vertex graph is the published record; 36 vertices would be a new lower bound.)
- archive: https://www.erdosproblems.com/166 (Erdős Problem #166 (proved (R(4,k) >> k^3/(log k)^O(1), Mattheus and Verstraete)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000163 (JSP-000163; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The Paley(17) starter is a classical 17-vertex graph, not a record construction.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
