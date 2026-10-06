# Fewest triangles in graphs with 16 vertices and 68 edges

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-triangles-above-turan-16`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> exactly 68 distinct edges [u, v] on vertices 0..15. The score is the exact number of triangles. Minimize; the proven optimum is 32 = t * floor(n/2) with t = 68 - 64. With n = 16 and t = 4 the theorem gives at least 32 triangles, and K8,8 plus a 4-edge matching attains 32.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 68 distinct edges [u, v] on vertices 0..15. The score is the exact number of triangles. Minimize; the proven optimum is 32 = t * floor(n/2) with t = 68 - 64.

## State of the art

At least t*floor(n/2) = 32 triangles (Lovász-Simonovits theorem), attained by K8,8 plus a matching of four edges.

Reference value: proven optimum `32` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1010](https://www.erdosproblems.com/1010), status: proved (Lovász-Simonovits; Nikiforov-Khadzhiivanov).

- [On the number of complete subgraphs of a graph II](https://doi.org/10.1007/978-3-0348-5438-2_41), L. Lovász, M. Simonovits (1983)
- [Erdős Problem #1010](https://www.erdosproblems.com/1010)

Parameters: `{"n": 16, "edges": 68}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the minimum number of triangles in graphs with a given number of edges above the Turán threshold.

Why it matters: Supersaturation for triangles (Erdős Problem #1010) is a foundational result of extremal graph theory; this finite case is a calibrated rediscovery.

- [On the number of complete subgraphs of a graph II](https://doi.org/10.1007/978-3-0348-5438-2_41): Main research objective: Determine the minimum number of triangles in graphs with a given number of edges above the Turán threshold. Task connection: With n = 16 and t = 4 the theorem gives at least 32 triangles, and K8,8 plus a 4-edge matching attains 32.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- With n = 16 and t = 4 the theorem gives at least 32 triangles, and K8,8 plus a 4-edge matching attains 32. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/978-3-0348-5438-2_41 (László Lovász and Miklós Simonovits, On the number of complete subgraphs of a graph II (1983). Crossref record inspected; Erdős Problem #1010 page inspected: every graph with floor(n^2/4)+t edges, t < floor(n/2), has at least t*floor(n/2) triangles, proved independently by Lovász-Simonovits and Nikiforov-Khadzhiivanov. With n = 16 and t = 4 the theorem gives at least 32 triangles, and K8,8 plus a 4-edge matching attains 32.)
- archive: https://www.erdosproblems.com/1010 (Erdős Problem #1010 (proved (Lovász-Simonovits; Nikiforov-Khadzhiivanov)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000840 (JSP-000840; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case: the optimum 32 is proven and attained by a simple construction.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
