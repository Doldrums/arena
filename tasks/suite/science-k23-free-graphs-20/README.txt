# Dense graphs on 20 vertices without K2,3

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-k23-free-graphs-20`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple graph on vertices 0..19 in which no two vertices have three common neighbours (no K2,3). Maximize the number of edges. A K2,3-free graph with m edges certifies ex(20;K2,3) >= m; the exact value for n = 20 is not documented here.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple graph on vertices 0..19 in which no two vertices have three common neighbours (no K2,3). Maximize the number of edges.

## State of the art

No documented value of ex(20;K2,3) was found; asymptotically ex(n;K2,3) ~ (sqrt(2)/2) n^(3/2) (Füredi 1996).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #146](https://www.erdosproblems.com/146), status: disproved (Lean).

- [New Asymptotics for Bipartite Turán Numbers](https://doi.org/10.1006/jcta.1996.0067), Zoltán Füredi (1996)

Parameters: `{"n": 20, "s": 2, "t": 3}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine Turán numbers of complete bipartite graphs K2,t.

Why it matters: Turán numbers of bipartite graphs of bounded degeneracy are the subject of Erdős Problem #146; K2,3 is the smallest nontrivial K2,t case.

- [New Asymptotics for Bipartite Turán Numbers](https://doi.org/10.1006/jcta.1996.0067): Main research objective: Determine Turán numbers of complete bipartite graphs K2,t. Task connection: A K2,3-free graph with m edges certifies ex(20;K2,3) >= m; the exact value for n = 20 is not documented here.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A K2,3-free graph with m edges certifies ex(20;K2,3) >= m; the exact value for n = 20 is not documented here. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1006/jcta.1996.0067 (Zoltán Füredi, New Asymptotics for Bipartite Turán Numbers (1996). Crossref record inspected; Erdős Problem #146 page inspected: the Erdős-Simonovits conjecture for r-degenerate bipartite H was disproved (Lean) by a 2-degenerate construction; K2,3 is 2-degenerate and Füredi determined ex(n;K2,t+1) asymptotically. A K2,3-free graph with m edges certifies ex(20;K2,3) >= m; the exact value for n = 20 is not documented here.)
- archive: https://www.erdosproblems.com/146 (Erdős Problem #146 (disproved (Lean)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000147 (JSP-000147; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 20 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
