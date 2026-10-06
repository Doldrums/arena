# Few edges in 5-uniform hypergraphs without Property B (m(5))

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-five-uniform-hypergraphs-without-property-b`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'n': n, 'edges': [[v1, ..., v5], ...]}: distinct 5-element edges on vertices 0..n-1 with 5 <= n <= 26 and at most 200 edges. The hypergraph must have no proper 2-colouring (no colouring of the vertices leaves every edge with both colours), checked exactly by backtracking with unit propagation. Minimize the number of edges. A valid hypergraph with e edges certifies m(5) <= e; the best known construction has 51 edges and every 5-uniform hypergraph with at most 28 edges is 2-colourable.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[v1, ..., v5], ...]}: distinct 5-element edges on vertices 0..n-1 with 5 <= n <= 26 and at most 200 edges. The hypergraph must have no proper 2-colouring (no colouring of the vertices leaves every edge with both colours), checked exactly by backtracking with unit propagation. Minimize the number of edges.

## State of the art

29 <= m(5) <= 51: the upper bound is the Abbott-Hanson construction (Fano plane core, 51 edges on 17 vertices) and the lower bound is Aglave, Amarnath, Shannigrahi and Singh (2020).

Reference value: best known value `51` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #901](https://www.erdosproblems.com/901), status: open.

- [Improved bounds for uniform hypergraphs without property B](https://ajc.maths.uq.edu.au/pdf/76/ajc_v76_p073.pdf), S. Aglave, V. A. Amarnath, S. Shannigrahi, S. Singh (2020)
- [On A Combinatorial Problem of Erdös](https://doi.org/10.4153/CMB-1969-107-x), H. L. Abbott, D. Hanson (1969)
- [OEIS A392185](https://oeis.org/A392185)

Parameters: `{"uniformity": 5, "max_vertices": 26}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine m(n), the fewest edges of an n-uniform hypergraph without Property B (Erdős Problem #901).

Why it matters: Property B (2-colourability of hypergraphs) is a founding problem of probabilistic combinatorics (Erdős, Beck, Radhakrishnan-Srinivasan); m(5) is the smallest open case.

- [Improved bounds for uniform hypergraphs without property B](https://ajc.maths.uq.edu.au/pdf/76/ajc_v76_p073.pdf): Main research objective: Determine m(n), the fewest edges of an n-uniform hypergraph without Property B (Erdős Problem #901). Task connection: A valid hypergraph with e edges certifies m(5) <= e; the best known construction has 51 edges and every 5-uniform hypergraph with at most 28 edges is 2-colourable.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid hypergraph with e edges certifies m(5) <= e; the best known construction has 51 edges and every 5-uniform hypergraph with at most 28 edges is 2-colourable. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://ajc.maths.uq.edu.au/pdf/76/ajc_v76_p073.pdf (Sachin Aglave, V. A. Amarnath, Saswata Shannigrahi and Shwetank Singh, Improved bounds for uniform hypergraphs without property B (2020). Australasian Journal of Combinatorics article inspected: m(5) >= 29 (new lower bound) and m(5) <= 51 from the Abbott-Hanson construction on the Fano plane (16 + 5*7 edges); Table 1 lists m(2) = 3, m(3) = 7, m(4) = 23 (Seymour; Östergård). OEIS A392185 inspected (29 <= a(5) <= 51). Erdős Problem #901 page inspected (bounds sqrt(n/log n) 2^n << m(n) << n^2 2^n). The 51-edge construction was rebuilt locally on 17 vertices and verified non-2-colourable by exhaustive search. A valid hypergraph with e edges certifies m(5) <= e; the best known construction has 51 edges and every 5-uniform hypergraph with at most 28 edges is 2-colourable.)
- archive: https://www.erdosproblems.com/901 (Erdős Problem #901 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000749 (JSP-000749; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Constructions are limited to 26 vertices so that exhaustive non-colourability checks stay fast; the 51-edge construction uses 17.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
