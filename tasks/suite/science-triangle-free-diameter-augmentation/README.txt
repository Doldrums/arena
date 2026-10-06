# Triangle-free diameter-four augmentation

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-triangle-free-diameter-augmentation`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> list of added undirected edges [u,v] on vertices 0..23. Existing edges and duplicate edges are forbidden. The union with the pinned path must remain triangle-free, connected and have diameter at most four. Minimize the number of added edges. The host is a locally chosen 24-vertex path. Its h_4 upper bounds do not establish the maximum over all triangle-free hosts or the paper’s asymptotic claims.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of added undirected edges [u,v] on vertices 0..23. Existing edges and duplicate edges are forbidden. The union with the pinned path must remain triangle-free, connected and have diameter at most four. Minimize the number of added edges.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Paul Erdős, András Gyárfás and Miklós Ruszinkó (1998, How to decrease the diameter of triangle-free graphs) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [How to decrease the diameter of triangle-free graphs](https://users.renyi.hu/~gyarfas/Cikkek/90_howtodecrease.pdf), Paul Erdős, András Gyárfás and Miklós Ruszinkó (1998)

Parameters: `{"n": 24, "edges": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13], [13, 14], [14, 15], [15, 16], [16, 17], [17, 18], [18, 19], [19, 20], [20, 21], [21, 22], [22, 23]], "diameter": 4}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how few new edges can reduce distances while preserving triangle-freeness.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Paul Erdős, András Gyárfás and Miklós Ruszinkó, How to decrease the diameter of triangle-free graphs (1998)](https://users.renyi.hu/~gyarfas/Cikkek/90_howtodecrease.pdf): Main research objective: Determine how few new edges can reduce distances while preserving triangle-freeness. Task connection: The host is a locally chosen 24-vertex path. Its h_4 upper bounds do not establish the maximum over all triangle-free hosts or the paper’s asymptotic claims.

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

- paper: https://users.renyi.hu/~gyarfas/Cikkek/90_howtodecrease.pdf (Paul Erdős, András Gyárfás and Miklós Ruszinkó, How to decrease the diameter of triangle-free graphs (1998). Abstract and introduction: h_d(G) is the minimum number of added edges preserving triangle-freeness and reducing diameter to d; d=4 is explicitly discussed.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000501 (JSP-000501; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The host is a locally chosen 24-vertex path. Its h_4 upper bounds do not establish the maximum over all triangle-free hosts or the paper’s asymptotic claims.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
