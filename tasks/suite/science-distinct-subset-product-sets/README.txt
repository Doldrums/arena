# Large sets with distinct subset products

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-distinct-subset-product-sets`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..18 distinct integers in 2..40. All 2^k subset products, including the empty product one, must be distinct. Exact arbitrary-precision products are enumerated. Maximize number of selected integers. The local instance restricts N=40 and certificate cardinality to 18 to bound exhaustive verification. It supplies finite constructions, not the paper’s asymptotic theorem. Integer one is excluded because it collides with the empty product.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..18 distinct integers in 2..40. All 2^k subset products, including the empty product one, must be distinct. Exact arbitrary-precision products are enumerated. Maximize number of selected integers.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Rushil Raghavan (2025, Sharp Bounds for Sets with Distinct Subset Products) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Sharp Bounds for Sets with Distinct Subset Products](https://arxiv.org/abs/2501.02695), Rushil Raghavan (2025)

Parameters: `{"n": 40, "maximum_size": 18}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the extremal size of multiplicatively dissociated integer sets.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Rushil Raghavan, Sharp Bounds for Sets with Distinct Subset Products (2025; revised 2026)](https://arxiv.org/abs/2501.02695): Main research objective: Determine the extremal size of multiplicatively dissociated integer sets. Task connection: The local instance restricts N=40 and certificate cardinality to 18 to bound exhaustive verification. It supplies finite constructions, not the paper’s asymptotic theorem. Integer one is excluded because it collides with the empty product.

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

- paper: https://arxiv.org/abs/2501.02695 (Rushil Raghavan, Sharp Bounds for Sets with Distinct Subset Products (2025; revised 2026). Author abstract states the distinct-products condition for every pair of distinct subsets of A contained in [N].)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000653 (JSP-000653; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local instance restricts N=40 and certificate cardinality to 18 to bound exhaustive verification. It supplies finite constructions, not the paper’s asymptotic theorem. Integer one is excluded because it collides with the empty product.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
