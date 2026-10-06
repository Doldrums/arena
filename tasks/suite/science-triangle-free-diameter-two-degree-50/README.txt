# Triangle-free diameter-two graphs on 50 vertices with small maximum degree

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-triangle-free-diameter-two-degree-50`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> list of edges [u, v] of a simple graph on vertices 0..49 that is triangle-free and has diameter at most two (every pair adjacent or with a common neighbour). Minimize the maximum degree; the optimum is 7. The Moore bound forces maximum degree at least 7 on 50 vertices, and the Hoffman-Singleton graph attains it, so 7 is optimal.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple graph on vertices 0..49 that is triangle-free and has diameter at most two (every pair adjacent or with a common neighbour). Minimize the maximum degree; the optimum is 7.

## State of the art

Maximum degree 7 is optimal: n <= d^2+1 for diameter two, and the 7-regular Hoffman-Singleton graph has 50 vertices, girth 5 and diameter 2.

Reference value: proven optimum `7` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #133](https://www.erdosproblems.com/133), status: disproved (f(n)/sqrt(n) does not tend to infinity).

- [On Moore Graphs with Diameters 2 and 3](https://doi.org/10.1147/rd.45.0497), A. J. Hoffman, R. R. Singleton (1960)

Parameters: `{"n": 50}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find the least maximum degree of triangle-free graphs of diameter two on n vertices.

Why it matters: Erdős and Pach asked for the growth of this degree function (Erdős Problem #133); n = 50 is the Moore-graph case where the answer is exact.

- [On Moore Graphs with Diameters 2 and 3](https://doi.org/10.1147/rd.45.0497): Main research objective: Find the least maximum degree of triangle-free graphs of diameter two on n vertices. Task connection: The Moore bound forces maximum degree at least 7 on 50 vertices, and the Hoffman-Singleton graph attains it, so 7 is optimal.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The Moore bound forces maximum degree at least 7 on 50 vertices, and the Hoffman-Singleton graph attains it, so 7 is optimal. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1147/rd.45.0497 (Alan J. Hoffman and Robert R. Singleton, On Moore Graphs with Diameters 2 and 3 (1960). Crossref record inspected; Erdős Problem #133 page inspected: a diameter-two graph of maximum degree d has at most d^2+1 vertices, and constructions of Hanson-Seyffarth and Füredi-Seress bound the growth of the minimum maximum degree. The Moore bound forces maximum degree at least 7 on 50 vertices, and the Hoffman-Singleton graph attains it, so 7 is optimal.)
- archive: https://www.erdosproblems.com/133 (Erdős Problem #133 (disproved (f(n)/sqrt(n) does not tend to infinity)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000139 (JSP-000139; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; the extremal object is the unique Hoffman-Singleton graph.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
