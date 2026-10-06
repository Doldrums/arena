# Graphs with 40 vertices and 401 edges whose largest book is small

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-small-books-above-turan-40`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> exactly 401 distinct edges [u, v] on vertices 0..39. The score is the largest book: the maximum over edges of the number of triangles containing that edge. Minimize; the theorem of Edwards and Khadzhiivanov-Nikiforov gives score >= 40/6. For n = 40 and one edge above n^2/4 the theorem gives a book of size at least 7; the least achievable value for this finite size is not documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 401 distinct edges [u, v] on vertices 0..39. The score is the largest book: the maximum over edges of the number of triangles containing that edge. Minimize; the theorem of Edwards and Khadzhiivanov-Nikiforov gives score >= 40/6.

## State of the art

No documented minimum for n = 40, m = 401; the book theorem gives at least ceil(40/6) = 7.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #905](https://www.erdosproblems.com/905), status: proved (Lean).

- [Books in graphs](https://doi.org/10.1016/j.ejc.2004.01.007), Béla Bollobás, Vladimir Nikiforov (2005)
- [Erdős Problem #905](https://www.erdosproblems.com/905)

Parameters: `{"n": 40, "edges": 401}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the largest book forced by a given number of edges.

Why it matters: The Bollobás-Erdős book conjecture (Erdős Problem #905) is a basic supersaturation statement; constructions near n/6 show its sharpness.

- [Books in graphs](https://doi.org/10.1016/j.ejc.2004.01.007): Main research objective: Determine the largest book forced by a given number of edges. Task connection: For n = 40 and one edge above n^2/4 the theorem gives a book of size at least 7; the least achievable value for this finite size is not documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 40 and one edge above n^2/4 the theorem gives a book of size at least 7; the least achievable value for this finite size is not documented. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/j.ejc.2004.01.007 (Béla Bollobás and Vladimir Nikiforov, Books in graphs (2005). Crossref record inspected; Erdős Problem #905 page inspected: every graph with more than n^2/4 edges has an edge in at least n/6 triangles (Edwards; Khadzhiivanov and Nikiforov). For n = 40 and one edge above n^2/4 the theorem gives a book of size at least 7; the least achievable value for this finite size is not documented.)
- archive: https://www.erdosproblems.com/905 (Erdős Problem #905 (proved (Lean)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000097 (JSP-000097; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented finite minimum (reference label none); the lower bound 7 follows from the theorem.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
