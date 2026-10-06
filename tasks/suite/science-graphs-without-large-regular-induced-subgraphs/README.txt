# Large graphs with no regular induced subgraph on six vertices

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-graphs-without-large-regular-induced-subgraphs`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 22. No set of 6 or more vertices may induce a regular subgraph (every vertex subset is checked). Maximize n. A valid graph on n vertices certifies G(6) > n. Graphs with 20 vertices are known; a 21-vertex graph would show G(6) >= 22.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 22. No set of 6 or more vertices may induce a regular subgraph (every vertex subset is checked). Maximize n.

## State of the art

G(6) >= 21: graphs on 20 vertices with no regular induced subgraph of order 6 are known (Alexeev and McKay; OEIS A392636); the existence of such a graph on 21 vertices is open.

Reference value: best known value `20` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #82](https://www.erdosproblems.com/82), status: open.

- [Ramsey numbers for regular induced subgraphs](https://arxiv.org/abs/2604.08215), Paul W. Dyson, Brendan D. McKay (2026)
- [OEIS A392636](https://oeis.org/A392636)

Parameters: `{"size": 6, "max_vertices": 22}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how large a regular induced subgraph every graph on n vertices must contain.

Why it matters: Erdős, Fajtlowicz and Staton asked whether F(n)/log n -> infinity (Erdős Problem #82); these finite Ramsey-type numbers are the computational side of the question.

- [Ramsey numbers for regular induced subgraphs](https://arxiv.org/abs/2604.08215): Main research objective: Determine how large a regular induced subgraph every graph on n vertices must contain. Task connection: A valid graph on n vertices certifies G(6) > n. Graphs with 20 vertices are known; a 21-vertex graph would show G(6) >= 22.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid graph on n vertices certifies G(6) > n. Graphs with 20 vertices are known; a 21-vertex graph would show G(6) >= 22. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2604.08215 (Paul W. Dyson and Brendan D. McKay, Ramsey numbers for regular induced subgraphs (2026). arXiv record inspected; Erdős Problem #82 page inspected: G(5) = 17, G(6) >= 21 and G(7) >= 30 (Alexeev and McKay; Dyson and McKay), where G(k) is the least order forcing a regular induced subgraph on k vertices. OEIS A392636 inspected: graphs on 20 vertices without regular induced subgraphs of order 6 exist; whether any exist on 21 vertices is unknown. A valid graph on n vertices certifies G(6) > n. Graphs with 20 vertices are known; a 21-vertex graph would show G(6) >= 22.)
- archive: https://www.erdosproblems.com/82 (Erdős Problem #82 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000099 (JSP-000099; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The five-vertex starter is trivial. Verification enumerates all vertex subsets, so n is capped at 22.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
