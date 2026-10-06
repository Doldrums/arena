# Dense graphs on 16 vertices without the cube Q3

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-cube-free-graphs-16`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple graph on vertices 0..15 containing no subgraph isomorphic to the 3-cube Q3 (exact search). Maximize the number of edges. A Q3-free graph with m edges certifies ex(16;Q3) >= m; no exact value for n = 16 is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple graph on vertices 0..15 containing no subgraph isomorphic to the 3-cube Q3 (exact search). Maximize the number of edges.

## State of the art

No documented value of ex(16;Q3); asymptotically (1/2+o(1))n^(3/2) <= ex(n;Q3) << n^(8/5).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #576](https://www.erdosproblems.com/576), status: open.

- [On Graphs That Do Not Contain The Cube And Related Problems](https://doi.org/10.1007/s00493-005-0037-z), Rom Pinchasi, Micha Sharir (2005)
- [Erdős Problem #576](https://www.erdosproblems.com/576)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the Turán number of the cube Q3.

Why it matters: The exponent of ex(n;Q3) is a long-standing Erdős-Simonovits problem (Erdős Problem #576).

- [On Graphs That Do Not Contain The Cube And Related Problems](https://doi.org/10.1007/s00493-005-0037-z): Main research objective: Determine the Turán number of the cube Q3. Task connection: A Q3-free graph with m edges certifies ex(16;Q3) >= m; no exact value for n = 16 is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A Q3-free graph with m edges certifies ex(16;Q3) >= m; no exact value for n = 16 is documented. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/s00493-005-0037-z (Rom Pinchasi and Micha Sharir, On Graphs That Do Not Contain The Cube And Related Problems (2005). Crossref record inspected; Erdős Problem #576 page inspected: (1/2+o(1))n^(3/2) <= ex(n;Q3) << n^(8/5) (Erdős and Simonovits), with Erdős asking whether ex(n;Q3) is of order n^(8/5). A Q3-free graph with m edges certifies ex(16;Q3) >= m; no exact value for n = 16 is documented.)
- archive: https://www.erdosproblems.com/576 (Erdős Problem #576 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000466 (JSP-000466; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 16 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
