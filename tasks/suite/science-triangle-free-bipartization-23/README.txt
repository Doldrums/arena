# Triangle-free graphs on 23 vertices that are far from bipartite

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-triangle-free-bipartization-23`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple triangle-free graph on vertices 0..22. The score is the least number of edges whose deletion leaves a bipartite graph, computed exactly as edges minus the maximum cut over all 2^22 bipartitions. Maximize; the known optimum is 20. The finite maximum over triangle-free graphs on 23 vertices is 20 (below the conjectured bound 21.16); recovering it tests constructions near the extremal C5 blow-ups.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple triangle-free graph on vertices 0..22. The score is the least number of edges whose deletion leaves a bipartite graph, computed exactly as edges minus the maximum cut over all 2^22 bipartitions. Maximize; the known optimum is 20.

## State of the art

Exhaustive computations (SeqFan 2025; B. McKay) give the maximum 20 for n = 23 (OEIS A389646); the conjectured bound n^2/25 is 21.16.

Reference value: proven optimum `20` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #23](https://www.erdosproblems.com/23), status: open (falsifiable by a finite counterexample).

- [OEIS A389646](https://oeis.org/A389646)
- [Max Cuts in Triangle-free Graphs](https://arxiv.org/abs/2103.14179), József Balogh, Felix Christian Clemen, Bernard Lidický (2021)

Parameters: `{"n": 23}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether every triangle-free graph on n vertices can be made bipartite by deleting n^2/25 edges.

Why it matters: Erdős Problem #23 is falsifiable by a finite counterexample; exact small values calibrate the n^2/25 conjecture and the flag-algebra bounds.

- [Max Cuts in Triangle-free Graphs](https://arxiv.org/abs/2103.14179): Main research objective: Decide whether every triangle-free graph on n vertices can be made bipartite by deleting n^2/25 edges. Task connection: The finite maximum over triangle-free graphs on 23 vertices is 20 (below the conjectured bound 21.16); recovering it tests constructions near the extremal C5 blow-ups.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The finite maximum over triangle-free graphs on 23 vertices is 20 (below the conjectured bound 21.16); recovering it tests constructions near the extremal C5 blow-ups. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2103.14179 (József Balogh, Felix Christian Clemen and Bernard Lidický, Max Cuts in Triangle-free Graphs (2021). arXiv record inspected; Erdős Problem #23 page inspected (best general bound 1.064 n^2/25 deletions, Balogh-Clemen-Lidický). OEIS A389646 inspected: exact values through n = 23 with a(23) = 20, attained by the blow-up of C5 with class sizes 4,5,4,5,5 and five of its subgraphs (comment by B. McKay, 2025). The finite maximum over triangle-free graphs on 23 vertices is 20 (below the conjectured bound 21.16); recovering it tests constructions near the extremal C5 blow-ups.)
- archive: https://www.erdosproblems.com/23 (Erdős Problem #23 (open (falsifiable by a finite counterexample)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000058 (JSP-000058; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; exceeding 20 is impossible. The conjecture itself concerns n = 5k and all larger n.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
