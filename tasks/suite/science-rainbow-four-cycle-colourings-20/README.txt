# Dense graphs on 20 vertices edge-coloured with 20 colours so every 4-cycle is rainbow

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-rainbow-four-cycle-colourings-20`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> coloured edges [[u, v, c], ...] of a simple graph on vertices 0..19 with colours 0..19. Every 4-cycle (as a subgraph) must receive four distinct colours, checked over all 4-cycles. Maximize the number of edges. Dense valid colourings for n = 20 are finite evidence on the anti-Ramsey question.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> coloured edges [[u, v, c], ...] of a simple graph on vertices 0..19 with colours 0..19. Every 4-cycle (as a subgraph) must receive four distinct colours, checked over all 4-cycles. Maximize the number of edges.

## State of the art

No documented values.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #810](https://www.erdosproblems.com/810), status: open.

- [Maximal antiramsey graphs and the strong chromatic number](https://doi.org/10.1002/jgt.3190130302), S. A. Burr, P. Erdős, R. L. Graham, V. T. Sós (1989)
- [Erdős Problem #810](https://www.erdosproblems.com/810)

Parameters: `{"n": 20, "colours": 20}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether graphs with eps*n^2 edges can be n-coloured so that every 4-cycle is rainbow (Erdős Problem #810).

Why it matters: Anti-Ramsey problems for C4 are tied to the (7,4)-problem for 3-uniform hypergraphs and to Sidon-type constructions.

- [Maximal antiramsey graphs and the strong chromatic number](https://doi.org/10.1002/jgt.3190130302): Main research objective: Decide whether graphs with eps*n^2 edges can be n-coloured so that every 4-cycle is rainbow (Erdős Problem #810). Task connection: Dense valid colourings for n = 20 are finite evidence on the anti-Ramsey question.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Dense valid colourings for n = 20 are finite evidence on the anti-Ramsey question. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1002/jgt.3190130302 (S. A. Burr, P. Erdős, R. L. Graham and V. T. Sós, Maximal antiramsey graphs and the strong chromatic number (1989). Crossref record inspected; Erdős Problem #810 page inspected (Burr, Erdős, Graham and Sós believed no eps*n^2 edges admit an n-colouring with every C4 rainbow; open for C4, resolved for other connected bipartite graphs except complete bipartite ones by Sárközy and Selkow). No finite values are documented. Dense valid colourings for n = 20 are finite evidence on the anti-Ramsey question.)
- archive: https://www.erdosproblems.com/810 (Erdős Problem #810 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000667 (JSP-000667; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
