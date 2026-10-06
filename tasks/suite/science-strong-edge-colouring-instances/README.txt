# Strong edge colourings of three fixed bounded-degree graphs

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-strong-edge-colouring-instances`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> three lists of edge colours, one per instance from bounded_degree_graph(n, d, seed) for (40,4,101), (60,5,102), (80,6,103) in the verifier; colours follow the sorted edge order. Each colour class must be an induced matching (no two edges share a vertex or are joined by an edge). Minimize the total number of colours used; the Erdős-Nešetřil conjecture predicts at most 5d^2/4 per instance (20 + 31 + 45). The score totals colours on three fixed graphs of maximum degree 4, 5 and 6; it measures a colouring method, not the conjecture.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> three lists of edge colours, one per instance from bounded_degree_graph(n, d, seed) for (40,4,101), (60,5,102), (80,6,103) in the verifier; colours follow the sorted edge order. Each colour class must be an induced matching (no two edges share a vertex or are joined by an edge). Minimize the total number of colours used; the Erdős-Nešetřil conjecture predicts at most 5d^2/4 per instance (20 + 31 + 45).

## State of the art

Instance-solving task; the conjectured bound 5 Delta^2/4 per instance is a reference line, not a documented optimum.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #149](https://www.erdosproblems.com/149), status: open.

- [A Bound on the Strong Chromatic Index of a Graph](https://doi.org/10.1006/jctb.1997.1724), Michael Molloy, Bruce Reed (1997)
- [An improved procedure for colouring graphs of bounded local density](https://doi.org/10.19086/aic.2022.7), Eoin Hurley, Rémi de Joannis de Verclos, Ross J. Kang (2022)

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Prove the Erdős-Nešetřil bound 5 Delta^2/4 on the strong chromatic index.

Why it matters: Strong edge colouring models interference-free channel assignment and is a benchmark problem for probabilistic colouring methods.

- [A Bound on the Strong Chromatic Index of a Graph](https://doi.org/10.1006/jctb.1997.1724): Main research objective: Prove the Erdős-Nešetřil bound 5 Delta^2/4 on the strong chromatic index. Task connection: The score totals colours on three fixed graphs of maximum degree 4, 5 and 6; it measures a colouring method, not the conjecture.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The score totals colours on three fixed graphs of maximum degree 4, 5 and 6; it measures a colouring method, not the conjecture. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1006/jctb.1997.1724 (Michael Molloy and Bruce Reed, A Bound on the Strong Chromatic Index of a Graph (1997). Crossref records inspected (Molloy and Reed 1997; Hurley, de Joannis de Verclos and Kang 2022). Erdős Problem #149 page inspected: the Erdős-Nešetřil conjecture sq(G) <= 5 Delta^2/4 is open; the best general bound is 1.772 Delta^2 (Hurley, de Joannis de Verclos and Kang). The score totals colours on three fixed graphs of maximum degree 4, 5 and 6; it measures a colouring method, not the conjecture.)
- archive: https://www.erdosproblems.com/149 (Erdős Problem #149 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000149 (JSP-000149; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Instance-solving task on three fixed pseudo-random graphs; results are not claims about the conjecture.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
