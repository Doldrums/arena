# Four-cycle-free edge sets of the 7-dimensional hypercube

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-hypercube-q7-four-cycle-free`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of Q7 (vertices 0..127, endpoints differing in one bit). No 2-dimensional face may have all four edges selected. Maximize the number of edges (Q7 has 448). An edge set with m edges certifies ex(Q7,C4) >= m; 304 is the best known and 308 the best upper bound.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of Q7 (vertices 0..127, endpoints differing in one bit). No 2-dimensional face may have all four edges selected. Maximize the number of edges (Q7 has 448).

## State of the art

304 <= ex(Q7,C4) <= 308: 304-edge C4-free subgraphs are known (Minamoto 2026 certificates); the upper bound is recorded in OEIS A245762.

Reference value: best known value `304` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #86](https://www.erdosproblems.com/86), status: open ($100).

- [C4-Free Subgraphs of the Hypercubes Q6, Q7, and Q8](https://arxiv.org/abs/2603.29127), Minamo Minamoto (2026)
- [OEIS A245762](https://oeis.org/A245762)
- [On the maximum number of edges in a C4-free subgraph of Qn](https://doi.org/10.1002/jgt.3190190104), Peter Brass, Heiko Harborth, Hauke Nienborg (1995)

Parameters: `{"dimension": 7}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the largest C4-free subgraphs of hypercubes.

Why it matters: Erdős offered $100 (Problem #86) for whether (1/2+o(1)) n 2^(n-1) edges suffice; small cubes are the only exact data.

- [C4-Free Subgraphs of the Hypercubes Q6, Q7, and Q8: Odd Squares, Fully Frustrated Models, and Computational Structure](https://arxiv.org/abs/2603.29127): Main research objective: Determine the largest C4-free subgraphs of hypercubes. Task connection: An edge set with m edges certifies ex(Q7,C4) >= m; 304 is the best known and 308 the best upper bound.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- An edge set with m edges certifies ex(Q7,C4) >= m; 304 is the best known and 308 the best upper bound. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2603.29127 (Minamo Minamoto, C4-Free Subgraphs of the Hypercubes Q6, Q7, and Q8: Odd Squares, Fully Frustrated Models, and Computational Structure (2026). arXiv abstract inspected: ex(Q7,C4) >= 304 with certificates, 19,866 previously released 304-edge C4-free subgraphs of Q7 classified. OEIS A245762 inspected (a(6) = 132 by Harborth and Nienborg; 304 <= a(7) <= 308). Erdős Problem #86 page inspected. An edge set with m edges certifies ex(Q7,C4) >= m; 304 is the best known and 308 the best upper bound.)
- archive: https://www.erdosproblems.com/86 (Erdős Problem #86 (open ($100)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000102 (JSP-000102; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The greedy starter is locally computed and is not a published construction.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
