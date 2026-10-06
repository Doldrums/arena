# Large uniform families without singleton intersections

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-uniform-no-singleton-intersections`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..1000 distinct four-element subsets of 0..15. No two members may intersect in exactly one element. Maximize the number of members. The local parameters are n=16 and k=4. The optimum is binomial(14,2) = 91 (Keevash, Mubayi and Wilson determined the maximum for k = 4 and every n >= 9), so this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..1000 distinct four-element subsets of 0..15. No two members may intersect in exactly one element. Maximize the number of members.

## State of the art

Keevash, Mubayi and Wilson determined the maximum for 4-uniform families and every n. For n >= 9 it is binomial(n-2, 2), attained only by all 4-sets through two fixed points, so the maximum for n = 16 is 91. Frankl proved the bound binomial(n-2, k-2) for all k >= 4 and large n (Erdős Problem #702).

Reference value: proven optimum `91` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #702](https://www.erdosproblems.com/702), status: proved.

- [Set Systems with No Singleton Intersection](https://doi.org/10.1137/050647372), Peter Keevash, Dhruv Mubayi, Richard M. Wilson (2006)
- [On families of finite sets no two of which intersect in a singleton](https://doi.org/10.1017/S0004972700025521), Peter Frankl (1977)

Parameters: `{"n": 16, "r": 4}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal sizes of uniform families with a forbidden intersection size.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Peter Frankl, On families of finite sets no two of which intersect in a singleton (1977)](https://doi.org/10.1017/S0004972700025521): Main research objective: Determine extremal sizes of uniform families with a forbidden intersection size. Task connection: The local parameters are n=16 and k=4. The optimum is binomial(14,2) = 91 (Keevash, Mubayi and Wilson determined the maximum for k = 4 and every n >= 9), so this is a rediscovery task.

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

- paper: https://doi.org/10.1017/S0004972700025521 (Peter Frankl, On families of finite sets no two of which intersect in a singleton (1977). Publisher abstract: k-uniform families with no singleton intersection and the Erdős–Sós extremal conjecture for k>=4 and sufficiently large n.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000572 (JSP-000572; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Solved finite case: Keevash, Mubayi and Wilson determined the maximum for 4-uniform families and every n.
- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local parameters are n=16 and k=4. The optimum is binomial(14,2) = 91 (Keevash, Mubayi and Wilson determined the maximum for k = 4 and every n >= 9), so this is a rediscovery task.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
