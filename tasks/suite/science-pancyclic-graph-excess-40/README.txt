# Sparse pancyclic graphs on 40 vertices

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-pancyclic-graph-excess-40`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'edges': undirected edge pairs on vertices 0..39, 'cycles': one vertex-list cycle of every length 3..40 in that order}. Edges are simple and distinct; cycle vertices are distinct and every required edge must exist. Minimize edge count minus 40. This is an independently implemented n=40 construction search with explicit cycle certificates. The seed is an elementary fan graph, not a copied minimal construction.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'edges': undirected edge pairs on vertices 0..39, 'cycles': one vertex-list cycle of every length 3..40 in that order}. Edges are simple and distinct; cycle vertices are distinct and every required edge must exist. Minimize edge count minus 40.

## State of the art

No documented value for n = 40. Griffin determined m(n) exactly for n <= 37 (m(37) = 42, an excess of 5). Bondy's counting bound gives an excess of at least 5 for n = 40, and the known five-chord constructions stop at 37 vertices.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1016](https://www.erdosproblems.com/1016), status: open.

- [Minimal Pancyclicity](https://arxiv.org/abs/1312.0274), Sean Griffin (2013)

Parameters: `{"n": 40}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize the number of edges needed for a graph to contain every cycle length.

Why it matters: Reducing the edge count supplies a certified finite upper bound for the extremal graph function investigated by the paper.

- [Minimal Pancyclicity](https://arxiv.org/abs/1312.0274): Main research objective: Minimize the number of edges needed for a graph to contain every cycle length. Task connection: This is an independently implemented n=40 construction search with explicit cycle certificates. The seed is an elementary fan graph, not a copied minimal construction.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- This is an independently implemented n=40 construction search with explicit cycle certificates. The seed is an elementary fan graph, not a copied minimal construction. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1312.0274 (Sean Griffin, Minimal Pancyclicity (2013). Author abstract inspected. It defines m(n), studies minimum-edge pancyclic graphs, and reports exact values through n=37. This is an independently implemented n=40 construction search with explicit cycle certificates. The seed is an elementary fan graph, not a copied minimal construction.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000846 (JSP-000846; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- No current optimal value or novelty threshold for n=40 is asserted. Feasibility proves an upper bound only, not global optimality or the general asymptotic law.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
