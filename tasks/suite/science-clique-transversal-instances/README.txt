# Small vertex sets meeting every maximal clique of three fixed random graphs

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-clique-transversal-instances`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> three vertex lists, one per instance from random_graph(n, p, seed) for (30,0.3,201), (35,0.25,202), (40,0.2,203) in the verifier. Each list must meet every maximal clique with at least two vertices (all maximal cliques enumerated by Bron-Kerbosch). Minimize the total size. The score totals transversal sizes on three fixed random graphs; it measures a covering method.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> three vertex lists, one per instance from random_graph(n, p, seed) for (30,0.3,201), (35,0.25,202), (40,0.2,203) in the verifier. Each list must meet every maximal clique with at least two vertices (all maximal cliques enumerated by Bron-Kerbosch). Minimize the total size.

## State of the art

Instance-solving task; no reference value.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #610](https://www.erdosproblems.com/610), status: proved (Lean).

- [Covering the cliques of a graph with vertices](https://doi.org/10.1016/0012-365X(92)90681-5), Paul Erdős, Tibor Gallai, Zsolt Tuza (1992)
- [Erdős Problem #610](https://www.erdosproblems.com/610)

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate the clique transversal number tau(G) (Erdős Problems #610, #611 and #151).

Why it matters: Clique transversals are a hitting-set problem on the clique hypergraph, related to independent sets in triangle-free graphs.

- [Covering the cliques of a graph with vertices](https://doi.org/10.1016/0012-365X(92)90681-5): Main research objective: Estimate the clique transversal number tau(G) (Erdős Problems #610, #611 and #151). Task connection: The score totals transversal sizes on three fixed random graphs; it measures a covering method.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The score totals transversal sizes on three fixed random graphs; it measures a covering method. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0012-365X(92)90681-5 (Paul Erdős, Tibor Gallai and Zsolt Tuza, Covering the cliques of a graph with vertices (1992). Crossref record inspected; Erdős Problem #610 page inspected (Erdős, Gallai and Tuza proved tau(G) <= n - sqrt(2n) + O(1); tau(G) <= n - c sqrt(n log n) follows from Joret, Micek, Reed and Smid) and related problems #151 and #611. The score totals transversal sizes on three fixed random graphs; it measures a covering method.)
- archive: https://www.erdosproblems.com/610 (Erdős Problem #610 (proved (Lean)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000150 (JSP-000150; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Instance-solving task on three fixed pseudo-random graphs.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
