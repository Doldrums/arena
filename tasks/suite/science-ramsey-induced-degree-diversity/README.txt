# Many distinct induced degrees in a Ramsey host

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-ramsey-induced-degree-diversity`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct vertices of the pinned 17-vertex graph, selecting at least eight. Maximize the number of distinct vertex degrees in the induced subgraph. The evaluator checks that the host has no clique or independent set of size four. The input is the classical Paley graph of order 17, and at least eight vertices must be retained. The published theorem concerns growing hosts and unspecified constants; no asymptotic or optimality claim follows from this instance.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct vertices of the pinned 17-vertex graph, selecting at least eight. Maximize the number of distinct vertex degrees in the induced subgraph. The evaluator checks that the host has no clique or independent set of size four.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Boris Bukh and Benny Sudakov (2007, Induced subgraphs of Ramsey graphs with many distinct degrees) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Induced subgraphs of Ramsey graphs with many distinct degrees](https://www.borisbukh.org/distinct-degrees.pdf), Boris Bukh and Benny Sudakov (2007)

Parameters: `{"n": 17, "edges": [[0, 1], [0, 2], [0, 4], [0, 8], [0, 9], [0, 13], [0, 15], [0, 16], [1, 2], [1, 3], [1, 5], [1, 9], [1, 10], [1, 14], [1, 16], [2, 3], [2, 4], [2, 6], [2, 10], [2, 11], [2, 15], [3, 4], [3, 5], [3, 7], [3, 11], [3, 12], [3, 16], [4, 5], [4, 6], [4, 8], [4, 12], [4, 13], [5, 6], [5, 7], [5, 9], [5, 13], [5, 14], [6, 7], [6, 8], [6, 10], [6, 14], [6, 15], [7, 8], [7, 9], [7, 11], [7, 15], [7, 16], [8, 9], [8, 10], [8, 12], [8, 16], [9, 10], [9, 11], [9, 13], [10, 11], [10, 12], [10, 14], [11, 12], [11, 13], [11, 15], [12, 13], [12, 14], [12, 16], [13, 14], [13, 15], [14, 15], [14, 16], [15, 16]], "homogeneous_cap": 4, "minimum_vertices": 8}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand which induced degree patterns are forced by Ramsey behavior.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Boris Bukh and Benny Sudakov, Induced subgraphs of Ramsey graphs with many distinct degrees (2007)](https://www.borisbukh.org/distinct-degrees.pdf): Main research objective: Understand which induced degree patterns are forced by Ramsey behavior. Task connection: The input is the classical Paley graph of order 17, and at least eight vertices must be retained. The published theorem concerns growing hosts and unspecified constants; no asymptotic or optimality claim follows from this instance.

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

- paper: https://www.borisbukh.org/distinct-degrees.pdf (Boris Bukh and Benny Sudakov, Induced subgraphs of Ramsey graphs with many distinct degrees (2007). Abstract and Theorem 1.1: induced subgraphs with many different degrees in graphs whose largest homogeneous set has logarithmic order.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000518 (JSP-000518; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The input is the classical Paley graph of order 17, and at least eight vertices must be retained. The published theorem concerns growing hosts and unspecified constants; no asymptotic or optimality claim follows from this instance.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
