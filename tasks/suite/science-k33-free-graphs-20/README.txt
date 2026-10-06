# Dense graphs on 20 vertices without K3,3

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-k33-free-graphs-20`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple graph on vertices 0..19 in which no three vertices have three common neighbours (no K3,3). Maximize the number of edges. A K3,3-free graph with m edges certifies ex(20;K3,3) >= m; no exact value for n = 20 is documented here.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple graph on vertices 0..19 in which no three vertices have three common neighbours (no K3,3). Maximize the number of edges.

## State of the art

No documented value of ex(20;K3,3) was found; ex(n;K3,3) = Theta(n^(5/3)) (Brown 1966; Kővári-Sós-Turán).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #714](https://www.erdosproblems.com/714), status: open.

- [On Graphs that do not Contain a Thomsen Graph](https://doi.org/10.4153/cmb-1966-036-2), W. G. Brown (1966)

Parameters: `{"n": 20, "s": 3, "t": 3}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the Turán numbers of complete bipartite graphs K_r,r.

Why it matters: Erdős Problem #714 asks for the order of ex(n;K_r,r); K3,3 is the case settled by Brown's construction.

- [On Graphs that do not Contain a Thomsen Graph](https://doi.org/10.4153/cmb-1966-036-2): Main research objective: Determine the Turán numbers of complete bipartite graphs K_r,r. Task connection: A K3,3-free graph with m edges certifies ex(20;K3,3) >= m; no exact value for n = 20 is documented here.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A K3,3-free graph with m edges certifies ex(20;K3,3) >= m; no exact value for n = 20 is documented here. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4153/cmb-1966-036-2 (W. G. Brown, On Graphs that do not Contain a Thomsen Graph (1966). Crossref record inspected; Erdős Problem #714 page inspected: ex(n;K_r,r) >> n^(2-1/r) is known for r = 2, 3 (Brown; Erdős, Rényi and Sós for r = 3) and open for r >= 4. A K3,3-free graph with m edges certifies ex(20;K3,3) >= m; no exact value for n = 20 is documented here.)
- archive: https://www.erdosproblems.com/714 (Erdős Problem #714 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000583 (JSP-000583; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 20 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
