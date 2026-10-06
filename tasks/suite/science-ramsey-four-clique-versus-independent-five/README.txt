# K4-free graphs without independent 5-sets (rediscovering R(4,5) = 25)

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-four-clique-versus-independent-five`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 25. It must contain no K4 and no independent set of 5 vertices, checked exactly. Maximize n; the proven optimum is 24. Finding a 24-vertex (4,5)-graph recovers Kalbfleisch's lower bound; no 25-vertex graph exists.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 25. It must contain no K4 and no independent set of 5 vertices, checked exactly. Maximize n; the proven optimum is 24.

## State of the art

R(4,5) = 25 (McKay and Radziszowski 1995), so 24 vertices is optimal; Kalbfleisch (1965) gave the first 24-vertex construction.

Reference value: proven optimum `24` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #986](https://www.erdosproblems.com/986), status: proved (Bradač 2026 for general s; Mattheus and Verstraete for s = 4).

- [R(4,5) = 25](https://doi.org/10.1002/jgt.3190190304), Brendan D. McKay, Stanislaw P. Radziszowski (1995)
- [Construction of Special Edge-Chromatic Graphs](https://doi.org/10.4153/cmb-1965-041-7), J. G. Kalbfleisch (1965)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"clique": 4, "independent": 5, "max_vertices": 25}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the Ramsey number R(4,5).

Why it matters: The off-diagonal numbers R(s,k) with s fixed are the subject of Erdős Problem #986; R(4,5) = 25 was a landmark computer-assisted determination.

- [R(4,5) = 25](https://doi.org/10.1002/jgt.3190190304): Main research objective: Determine the Ramsey number R(4,5). Task connection: Finding a 24-vertex (4,5)-graph recovers Kalbfleisch's lower bound; no 25-vertex graph exists.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Finding a 24-vertex (4,5)-graph recovers Kalbfleisch's lower bound; no 25-vertex graph exists. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1002/jgt.3190190304 (Brendan D. McKay and Stanisław P. Radziszowski, R(4,5) = 25 (1995). Crossref record inspected; survey DS1.18 item 2.1.d inspected: R(4,5) = 25 and exactly 352366 critical graphs on 24 vertices; lower bound by Kalbfleisch (1965). Finding a 24-vertex (4,5)-graph recovers Kalbfleisch's lower bound; no 25-vertex graph exists.)
- archive: https://www.erdosproblems.com/986 (Erdős Problem #986 (proved (Bradač 2026 for general s; Mattheus and Verstraete for s = 4)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000819 (JSP-000819; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case: the optimum 24 is known and many extremal graphs are public.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
