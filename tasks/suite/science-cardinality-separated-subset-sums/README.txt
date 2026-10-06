# Large sets with cardinality-separated subset sums

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-cardinality-separated-subset-sums`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..60 distinct integers in 1..256. Whenever two subsets have different cardinalities their sums must differ. Repeated sums within the SAME cardinality are allowed. The empty subset is included. Maximize set size using exact cardinality-indexed subset-sum dynamic programming. N=256 with at most sixty output members is a bounded finite instance. This is weaker than requiring all subset sums distinct and is intentionally a different task. No optimality or infinite-density conclusion follows.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..60 distinct integers in 1..256. Whenever two subsets have different cardinalities their sums must differ. Repeated sums within the SAME cardinality are allowed. The empty subset is included. Maximize set size using exact cardinality-indexed subset-sum dynamic programming.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Paul Erdős, Jean-Louis Nicolas and András Sárközy (1991, Sommes de sous-ensembles) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Sommes de sous-ensembles](https://www.numdam.org/item/JTNB_1991__3_1_55_0/), Paul Erdős, Jean-Louis Nicolas and András Sárközy (1991)

Parameters: `{"n": 256, "maximum_size": 60}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximum size of an integer set whose subset sum identifies subset cardinality.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Paul Erdős, Jean-Louis Nicolas and András Sárközy, Sommes de sous-ensembles (1991)](https://www.numdam.org/item/JTNB_1991__3_1_55_0/): Main research objective: Determine the maximum size of an integer set whose subset sum identifies subset cardinality. Task connection: N=256 with at most sixty output members is a bounded finite instance. This is weaker than requiring all subset sums distinct and is intentionally a different task. No optimality or infinite-density conclusion follows.

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

- paper: https://www.numdam.org/item/JTNB_1991__3_1_55_0/ (Paul Erdős, Jean-Louis Nicolas and András Sárközy, Sommes de sous-ensembles (1991). Author abstract defines admissibility by distinct sums of subsets with different cardinalities and studies maximum size in [1,N].)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000725 (JSP-000725; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- N=256 with at most sixty output members is a bounded finite instance. This is weaker than requiring all subset sums distinct and is intentionally a different task. No optimality or infinite-density conclusion follows.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
