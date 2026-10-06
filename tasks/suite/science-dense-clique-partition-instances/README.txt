# Clique partitions of two fixed dense random graphs

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-dense-clique-partition-instances`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> two lists of cliques (vertex lists), one per instance from random_graph(n, p, seed) for (32,0.6,601) and (64,0.55,602) in the verifier (both with more than n^2/4 edges). Every listed set must be a clique with at least two vertices and every edge must lie in exactly one listed clique. Minimize the total number of cliques. The score totals clique partition sizes on two fixed dense graphs; it measures a partitioning method.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> two lists of cliques (vertex lists), one per instance from random_graph(n, p, seed) for (32,0.6,601) and (64,0.55,602) in the verifier (both with more than n^2/4 edges). Every listed set must be a clique with at least two vertices and every edge must lie in exactly one listed clique. Minimize the total number of cliques.

## State of the art

Instance-solving task; no reference value.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1017](https://www.erdosproblems.com/1017), status: open.

- [The Representation of a Graph by Set Intersections](https://doi.org/10.4153/CJM-1966-014-3), Paul Erdős, A. W. Goodman, Louis Pósa (1966)
- [On the Number of Edge-Disjoint Triangles in K4-Free Graphs](https://doi.org/10.1007/s00493-016-3500-0), Ervin Győri, Balázs Keszegh (2017)

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate the clique partition number f(n,k) of graphs with k > n^2/4 edges (Erdős Problem #1017).

Why it matters: Clique partition numbers measure intersection representations of graphs and appear in design theory.

- [The Representation of a Graph by Set Intersections](https://doi.org/10.4153/CJM-1966-014-3): Main research objective: Estimate the clique partition number f(n,k) of graphs with k > n^2/4 edges (Erdős Problem #1017). Task connection: The score totals clique partition sizes on two fixed dense graphs; it measures a partitioning method.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The score totals clique partition sizes on two fixed dense graphs; it measures a partitioning method. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4153/CJM-1966-014-3 (Paul Erdős, A. W. Goodman and Louis Pósa, The Representation of a Graph by Set Intersections (1966). Crossref records inspected (Erdős, Goodman and Pósa 1966; Győri and Keszegh 2017). Erdős Problem #1017 page inspected: every graph has an edge partition into at most n^2/4 edges and triangles; Erdős asked for sharpening when there are more than n^2/4 edges; Győri and Keszegh settled the K4-free case. The score totals clique partition sizes on two fixed dense graphs; it measures a partitioning method.)
- archive: https://www.erdosproblems.com/1017 (Erdős Problem #1017 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000847 (JSP-000847; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Instance-solving task on two fixed pseudo-random graphs.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
