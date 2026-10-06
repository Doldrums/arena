# Cochromatic partitions of a pinned random graph

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-cochromatic-homogeneous-partition`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> partition of vertices 0..13 into nonempty lists. Every part must induce a clique or an independent set, and vertices occur exactly once. Minimize number of parts. The evaluator independently reports the exact ordinary chromatic number by subset dynamic programming. One explicit G(14,1/2) sample, generated locally with random.Random(506), is optimized. The candidate score is a cochromatic upper bound, not an asymptotic random-graph result or a guaranteed optimal partition.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> partition of vertices 0..13 into nonempty lists. Every part must induce a clique or an independent set, and vertices occur exactly once. Minimize number of parts. The evaluator independently reports the exact ordinary chromatic number by subset dynamic programming.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Annika Heckel (2024, The difference between the chromatic and the cochromatic number of a random graph) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [The difference between the chromatic and the cochromatic number of a random graph](https://arxiv.org/abs/2409.17614), Annika Heckel (2024)

Parameters: `{"n": 14, "edges": [[0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 10], [0, 12], [1, 4], [1, 9], [1, 11], [2, 3], [2, 5], [2, 6], [2, 7], [2, 12], [2, 13], [3, 4], [3, 5], [3, 8], [3, 11], [3, 12], [3, 13], [4, 5], [4, 7], [4, 13], [5, 8], [5, 9], [5, 10], [5, 12], [5, 13], [6, 8], [6, 11], [6, 13], [7, 12], [8, 9], [8, 13], [9, 11], [9, 12], [11, 13]]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand the advantage of homogeneous partitions over ordinary graph coloring.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Annika Heckel, The difference between the chromatic and the cochromatic number of a random graph (2024; revised 2025)](https://arxiv.org/abs/2409.17614): Main research objective: Understand the advantage of homogeneous partitions over ordinary graph coloring. Task connection: One explicit G(14,1/2) sample, generated locally with random.Random(506), is optimized. The candidate score is a cochromatic upper bound, not an asymptotic random-graph result or a guaranteed optimal partition.

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

- paper: https://arxiv.org/abs/2409.17614 (Annika Heckel, The difference between the chromatic and the cochromatic number of a random graph (2024; revised 2025). Author abstract: defines cochromatic number by clique-or-independent color classes and studies its gap from chromatic number in G(n,1/2).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000506 (JSP-000506; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- One explicit G(14,1/2) sample, generated locally with random.Random(506), is optimized. The candidate score is a cochromatic upper bound, not an asymptotic random-graph result or a guaranteed optimal partition.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
