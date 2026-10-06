# Dense graphs with every edge essential for diameter two

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-diameter-two-edge-critical-graphs`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> simple undirected edges on vertices 0..15. The graph must have diameter exactly two. Deleting EACH individual edge must increase its diameter above two or disconnect it. Maximize edge count; the evaluator repeats exact all-pairs BFS for every edge deletion. Only sixteen vertices are searched; finite candidates provide lower constructions, not upper-bound proofs for every order. The star seed is an elementary complete bipartite example. No novelty or unresolved status of this small order is asserted.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> simple undirected edges on vertices 0..15. The graph must have diameter exactly two. Deleting EACH individual edge must increase its diameter above two or disconnect it. Maximize edge count; the evaluator repeats exact all-pairs BFS for every edge deletion.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Zoltán Füredi (1992, The maximum number of edges in a minimal graph of diameter 2) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [The maximum number of edges in a minimal graph of diameter 2](https://doi.org/10.1002/jgt.3190160110), Zoltán Füredi (1992)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the extremal number of edges in diameter-two-critical graphs.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Zoltán Füredi, The maximum number of edges in a minimal graph of diameter 2 (1992)](https://doi.org/10.1002/jgt.3190160110): Main research objective: Determine the extremal number of edges in diameter-two-critical graphs. Task connection: Only sixteen vertices are searched; finite candidates provide lower constructions, not upper-bound proofs for every order. The star seed is an elementary complete bipartite example. No novelty or unresolved status of this small order is asserted.

Supported by the inspected primary problem statement, rather than the prize listing or an agent benchmark. Finite progress is not automatically a novel scientific result.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Exact finite certificate validation; independently implemented from the cited mathematical definition. Resource bounds and source adaptation are recorded per task. No Lean verification or general theorem is claimed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1002/jgt.3190160110 (Zoltán Füredi, The maximum number of edges in a minimal graph of diameter 2 (1992). Publisher abstract defines edge-minimal diameter-two graphs and studies the Murty–Simon maximum-edge conjecture; Journal of Graph Theory 16, 81–98.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000610 (JSP-000610; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- Only sixteen vertices are searched; finite candidates provide lower constructions, not upper-bound proofs for every order. The star seed is an elementary complete bipartite example. No novelty or unresolved status of this small order is asserted.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
- The publisher HTML has a reversed inequality in its rendering of the size threshold. The local evaluator uses only the verified definition and does not apply the asymptotic theorem as a finite rejection rule.
