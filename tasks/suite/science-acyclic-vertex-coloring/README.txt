# Few colors without any bicolored cycle

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-acyclic-vertex-coloring`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> fifty Python integer color labels in 0..49 for the pinned degree-four graph. Adjacent vertices must differ and the subgraph induced by any two colors must be a forest. Minimize number of distinct colors; union-find detects bicolored cycles exactly. A fixed 50-vertex degree-four circulant graph with steps 1 and 7 is colored. A lower score is a better finite coloring, not a new general maximum-degree bound.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> fifty Python integer color labels in 0..49 for the pinned degree-four graph. Adjacent vertices must differ and the subgraph induced by any two colors must be a forest. Minimize number of distinct colors; union-find detects bicolored cycles exactly.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Noga Alon, Colin McDiarmid and Bruce Reed (1991, Acyclic coloring of graphs) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Acyclic coloring of graphs](https://doi.org/10.1002/rsa.3240020303), Noga Alon, Colin McDiarmid and Bruce Reed (1991)

Parameters: `{"n": 50, "edges": [[0, 1], [0, 7], [0, 43], [0, 49], [1, 2], [1, 8], [1, 44], [2, 3], [2, 9], [2, 45], [3, 4], [3, 10], [3, 46], [4, 5], [4, 11], [4, 47], [5, 6], [5, 12], [5, 48], [6, 7], [6, 13], [6, 49], [7, 8], [7, 14], [8, 9], [8, 15], [9, 10], [9, 16], [10, 11], [10, 17], [11, 12], [11, 18], [12, 13], [12, 19], [13, 14], [13, 20], [14, 15], [14, 21], [15, 16], [15, 22], [16, 17], [16, 23], [17, 18], [17, 24], [18, 19], [18, 25], [19, 20], [19, 26], [20, 21], [20, 27], [21, 22], [21, 28], [22, 23], [22, 29], [23, 24], [23, 30], [24, 25], [24, 31], [25, 26], [25, 32], [26, 27], [26, 33], [27, 28], [27, 34], [28, 29], [28, 35], [29, 30], [29, 36], [30, 31], [30, 37], [31, 32], [31, 38], [32, 33], [32, 39], [33, 34], [33, 40], [34, 35], [34, 41], [35, 36], [35, 42], [36, 37], [36, 43], [37, 38], [37, 44], [38, 39], [38, 45], [39, 40], [39, 46], [40, 41], [40, 47], [41, 42], [41, 48], [42, 43], [42, 49], [43, 44], [44, 45], [45, 46], [46, 47], [47, 48], [48, 49]]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand the number of colors needed to prevent all bicolored graph cycles.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Noga Alon, Colin McDiarmid and Bruce Reed, Acyclic coloring of graphs (1991)](https://doi.org/10.1002/rsa.3240020303): Main research objective: Understand the number of colors needed to prevent all bicolored graph cycles. Task connection: A fixed 50-vertex degree-four circulant graph with steps 1 and 7 is colored. A lower score is a better finite coloring, not a new general maximum-degree bound.

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

- paper: https://doi.org/10.1002/rsa.3240020303 (Noga Alon, Colin McDiarmid and Bruce Reed, Acyclic coloring of graphs (1991). Publisher abstract defines proper acyclic colorings and the minimum color count A(G); studies its dependence on maximum degree.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000655 (JSP-000655; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- A fixed 50-vertex degree-four circulant graph with steps 1 and 7 is colored. A lower score is a better finite coloring, not a new general maximum-degree bound.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
