# Triangle-free graphs on 20 vertices whose every half is dense

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-triangle-free-dense-halves-20`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple triangle-free graph on vertices 0..19. The score is the minimum number of edges induced by any 10 of the vertices, computed over all 184756 subsets. Maximize; a score above 8 would disprove the Erdős-Rousseau conjecture for n = 20. For n = 20 the conjectured maximum of the score is 8, attained by the balanced C5 blow-up; a triangle-free graph with score 9 would be a counterexample.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple triangle-free graph on vertices 0..19. The score is the minimum number of edges induced by any 10 of the vertices, computed over all 184756 subsets. Maximize; a score above 8 would disprove the Erdős-Rousseau conjecture for n = 20.

## State of the art

Conjectured maximum n^2/50 = 8 for n = 20, attained by the balanced blow-up of C5; no triangle-free graph with a larger score is known.

Reference value: conjectured optimum `8` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #128](https://www.erdosproblems.com/128), status: open (falsifiable, $250).

- [More about sparse halves in triangle-free graphs](https://doi.org/10.1070/sm9615), A. A. Razborov (2022)
- [Erdős Problem #128](https://www.erdosproblems.com/128)

Parameters: `{"n": 20}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Show that every triangle-free graph has a set of n/2 vertices spanning at most n^2/50 edges.

Why it matters: The sparse-halves conjecture of Erdős and Rousseau is a $250 Erdős problem that is falsifiable by a single finite graph.

- [More about sparse halves in triangle-free graphs](https://doi.org/10.1070/sm9615): Main research objective: Show that every triangle-free graph has a set of n/2 vertices spanning at most n^2/50 edges. Task connection: For n = 20 the conjectured maximum of the score is 8, attained by the balanced C5 blow-up; a triangle-free graph with score 9 would be a counterexample.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 20 the conjectured maximum of the score is 8, attained by the balanced C5 blow-up; a triangle-free graph with score 9 would be a counterexample. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1070/sm9615 (Alexander A. Razborov, More about sparse halves in triangle-free graphs (2022). Crossref record inspected; Erdős Problem #128 ($250) page inspected: every n/2-set of a triangle-free graph is conjectured to span at most n^2/50 edges, tight for the C5 blow-up and the Petersen graph; proved with 1/50 replaced by 27/1024 by Razborov. For n = 20 the conjectured maximum of the score is 8, attained by the balanced C5 blow-up; a triangle-free graph with score 9 would be a counterexample.)
- archive: https://www.erdosproblems.com/128 (Erdős Problem #128 (open (falsifiable, $250)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000134 (JSP-000134; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The value 8 is a conjectured optimum, not a proven one; small cases have not been reported as verified. The 20-cycle starter scores 0.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
