# Clique partitions of three fixed split (chordal) graphs

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-chordal-clique-partition-instances`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> three lists of cliques (vertex lists), one per instance from split_graph(n, k, p, seed) for (30,10,0.7,301), (60,20,0.7,302), (90,30,0.7,303) in the verifier: a clique on the first k vertices, an independent set on the rest and each cross pair joined with probability p (split graphs are chordal). Every listed set must be a clique with at least two vertices and every edge must lie in exactly one listed clique. Minimize the total number of cliques; the Erdős-Ordman-Zalcstein question asks whether n^2/6 + O(n) always suffice, and split graphs need at most 3n^2/16 + O(n). The score totals clique partition sizes on three fixed random split graphs; it measures a partitioning method.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> three lists of cliques (vertex lists), one per instance from split_graph(n, k, p, seed) for (30,10,0.7,301), (60,20,0.7,302), (90,30,0.7,303) in the verifier: a clique on the first k vertices, an independent set on the rest and each cross pair joined with probability p (split graphs are chordal). Every listed set must be a clique with at least two vertices and every edge must lie in exactly one listed clique. Minimize the total number of cliques; the Erdős-Ordman-Zalcstein question asks whether n^2/6 + O(n) always suffice, and split graphs need at most 3n^2/16 + O(n).

## State of the art

Instance-solving task; no reference value.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #81](https://www.erdosproblems.com/81), status: open.

- [Clique Partitions of Chordal Graphs](https://doi.org/10.1017/S0963548300000808), Paul Erdős, Edward T. Ordman, Yechezkel Zalcstein (1993)
- [Erdős Problem #81](https://www.erdosproblems.com/81)

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether every chordal graph's edges split into n^2/6 + O(n) cliques (Erdős Problem #81).

Why it matters: Clique partitions measure the intersection-representation complexity of graphs (Erdős-Goodman-Pósa).

- [Clique Partitions of Chordal Graphs](https://doi.org/10.1017/S0963548300000808): Main research objective: Decide whether every chordal graph's edges split into n^2/6 + O(n) cliques (Erdős Problem #81). Task connection: The score totals clique partition sizes on three fixed random split graphs; it measures a partitioning method.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The score totals clique partition sizes on three fixed random split graphs; it measures a partitioning method. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1017/S0963548300000808 (Paul Erdős, Edward T. Ordman and Yechezkel Zalcstein, Clique Partitions of Chordal Graphs (1993). Crossref record inspected; Erdős Problem #81 page inspected (Erdős, Ordman and Zalcstein proved (1/4 - eps)n^2 cliques suffice and asked for n^2/6 + O(n); split graphs need at most 3n^2/16 + O(n) by Chen, Erdős and Ordman). The score totals clique partition sizes on three fixed random split graphs; it measures a partitioning method.)
- archive: https://www.erdosproblems.com/81 (Erdős Problem #81 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000098 (JSP-000098; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Instance-solving task on three fixed pseudo-random split graphs.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
