# Triple systems on 16 points without the complete 3-partite K(2,2,2)

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-triple-systems-without-k222-16`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of distinct triples [a, b, c] of distinct points in 0..15 such that no three disjoint pairs have all eight transversal triples present. Maximize the number of triples. A valid triple system with m triples certifies ex_3(16,K(2,2,2)) >= m; no finite value is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of distinct triples [a, b, c] of distinct points in 0..15 such that no three disjoint pairs have all eight transversal triples present. Maximize the number of triples.

## State of the art

No documented value for n = 16; ex_3(n,K(2,2,2)) << n^(11/4) by Erdős 1964.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1158](https://www.erdosproblems.com/1158), status: open.

- [On extremal problems of graphs and generalized graphs](https://doi.org/10.1007/bf02759942), P. Erdős (1964)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine Turán numbers of complete t-partite t-uniform hypergraphs.

Why it matters: Erdős's 1964 theorem introduced hypergraph Turán exponents; Erdős Problem #1158 asks whether his upper bound exponent is sharp.

- [On extremal problems of graphs and generalized graphs](https://doi.org/10.1007/bf02759942): Main research objective: Determine Turán numbers of complete t-partite t-uniform hypergraphs. Task connection: A valid triple system with m triples certifies ex_3(16,K(2,2,2)) >= m; no finite value is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid triple system with m triples certifies ex_3(16,K(2,2,2)) >= m; no finite value is documented. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/bf02759942 (Paul Erdős, On extremal problems of graphs and generalized graphs (1964). Crossref record inspected; Erdős Problem #1158 page inspected: n^(t-O(r^(1-t))) <= ex_t(n,K_t(r)) << n^(t-r^(1-t)) (Erdős 1964); the lower-bound exponent is known only for t = 2 and r <= 3. A valid triple system with m triples certifies ex_3(16,K(2,2,2)) >= m; no finite value is documented.)
- archive: https://www.erdosproblems.com/1158 (Erdős Problem #1158 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000963 (JSP-000963; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 16 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
