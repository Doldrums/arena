# Graphs on 16 vertices with 65 edges whose triangles have small degree sums

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-triangle-degree-sums-above-turan-16`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'n': 16, 'edges': [[u, v], ...]}: a simple graph on 16 vertices with exactly 65 = floor(16^2/4) + 1 edges (so it has triangles). The score is the largest degree sum deg(u) + deg(v) + deg(w) over its triangles. Minimize. Scores below 24 would beat the published construction at n = 16; the conjectured asymptotic value is about 1.464n = 23.4.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': 16, 'edges': [[u, v], ...]}: a simple graph on 16 vertices with exactly 65 = floor(16^2/4) + 1 edges (so it has triangles). The score is the largest degree sum deg(u) + deg(v) + deg(w) over its triangles. Minimize.

## State of the art

No documented optimum for n = 16; the Erdős-Laskar/Fan construction gives 24 (evaluated locally) and 21n/16 <= h(n) asymptotically.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1033](https://www.erdosproblems.com/1033), status: open.

- [Degree sum for a triangle in a graph](https://doi.org/10.1002/jgt.3190120216), Genghua Fan (1988)
- [Erdős Problem #1033](https://www.erdosproblems.com/1033)

Parameters: `{"n": 16, "edges": 65}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate h(n), the largest triangle degree sum forced in graphs with more than n^2/4 edges (Erdős Problem #1033).

Why it matters: The problem refines Mantel's theorem by asking where the forced triangles sit in the degree sequence.

- [Degree sum for a triangle in a graph](https://doi.org/10.1002/jgt.3190120216): Main research objective: Estimate h(n), the largest triangle degree sum forced in graphs with more than n^2/4 edges (Erdős Problem #1033). Task connection: Scores below 24 would beat the published construction at n = 16; the conjectured asymptotic value is about 1.464n = 23.4.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Scores below 24 would beat the published construction at n = 16; the conjectured asymptotic value is about 1.464n = 23.4. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1002/jgt.3190120216 (Genghua Fan, Degree sum for a triangle in a graph (1988). Crossref record inspected; Erdős Problem #1033 page inspected (Bollobás-Erdős conjecture h(n) >= (2(sqrt 3 - 1) - o(1))n; known 21n/16 <= h(n) <= 2(sqrt 3 - 1)n + O(1) with the construction of Erdős and Laskar made explicit by Fan). Evaluated locally, that construction gives 24 for n = 16 (K_{10,6} plus a perfect matching on the 10-side); no finite optimum is documented. Scores below 24 would beat the published construction at n = 16; the conjectured asymptotic value is about 1.464n = 23.4.)
- archive: https://www.erdosproblems.com/1033 (Erdős Problem #1033 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000859 (JSP-000859; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 16 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
