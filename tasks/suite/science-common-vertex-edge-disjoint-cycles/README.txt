# Packing edge-disjoint cycles on one vertex set

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-common-vertex-edge-disjoint-cycles`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> nonempty list of simple cycles, each represented by a list of distinct vertices with the closing edge implicit. All cycles must use exactly the same vertex set of size at least three in the pinned 21-vertex host. No host edge may occur in two cycles. Maximize number of cycles. The local task maximizes witness multiplicity in the explicit circulant host with steps 1, 2 and 5. This measures the finite cycle-packing quantity and cannot prove a universal chromatic forcing statement.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> nonempty list of simple cycles, each represented by a list of distinct vertices with the closing edge implicit. All cycles must use exactly the same vertex set of size at least three in the pinned 21-vertex host. No host edge may occur in two cycles. Maximize number of cycles.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Barnabás Janzer, Raphael Steiner and Benny Sudakov (2024, Chromatic number and regular subgraphs) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Chromatic number and regular subgraphs](https://arxiv.org/abs/2410.02437), Barnabás Janzer, Raphael Steiner and Benny Sudakov (2024)

Parameters: `{"n": 21, "edges": [[0, 1], [0, 2], [0, 5], [0, 16], [0, 19], [0, 20], [1, 2], [1, 3], [1, 6], [1, 17], [1, 20], [2, 3], [2, 4], [2, 7], [2, 18], [3, 4], [3, 5], [3, 8], [3, 19], [4, 5], [4, 6], [4, 9], [4, 20], [5, 6], [5, 7], [5, 10], [6, 7], [6, 8], [6, 11], [7, 8], [7, 9], [7, 12], [8, 9], [8, 10], [8, 13], [9, 10], [9, 11], [9, 14], [10, 11], [10, 12], [10, 15], [11, 12], [11, 13], [11, 16], [12, 13], [12, 14], [12, 17], [13, 14], [13, 15], [13, 18], [14, 15], [14, 16], [14, 19], [15, 16], [15, 17], [15, 20], [16, 17], [16, 18], [17, 18], [17, 19], [18, 19], [18, 20], [19, 20]]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Study the connection between chromatic complexity and regular subgraph/cycle packing obstructions.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Barnabás Janzer, Raphael Steiner and Benny Sudakov, Chromatic number and regular subgraphs (2024)](https://arxiv.org/abs/2410.02437): Main research objective: Study the connection between chromatic complexity and regular subgraph/cycle packing obstructions. Task connection: The local task maximizes witness multiplicity in the explicit circulant host with steps 1, 2 and 5. This measures the finite cycle-packing quantity and cannot prove a universal chromatic forcing statement.

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

- paper: https://arxiv.org/abs/2410.02437 (Barnabás Janzer, Raphael Steiner and Benny Sudakov, Chromatic number and regular subgraphs (2024). Abstract: the original question asks for r edge-disjoint cycles on the same vertex set; the paper gives high-fractional-chromatic examples without even a 4-regular subgraph.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000521 (JSP-000521; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local task maximizes witness multiplicity in the explicit circulant host with steps 1, 2 and 5. This measures the finite cycle-packing quantity and cannot prove a universal chromatic forcing statement.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
- The cited paper DISPROVES existence of the proposed chromatic forcing function for r>=2. Its result is not described as a positive cycle-packing theorem. The local host is not claimed to reproduce its counterexamples.
