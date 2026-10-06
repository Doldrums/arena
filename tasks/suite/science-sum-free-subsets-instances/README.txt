# Large sum-free subsets of three fixed sets of integers

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-sum-free-subsets-instances`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> three subsets, one per instance from sum_free_instance(size, seed) for (60,801), (120,802), (240,803) in the verifier (distinct nonzero integers in [-10000, 10000]). Each subset must be sum-free: no a + b = c with a, b, c in it (a = b allowed). Maximize the total size; every n-element set has a sum-free subset of size at least (n+2)/3 (Bourgain). The score totals sum-free subset sizes on three fixed random sets; it measures a search method, not the worst case in f(n).

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> three subsets, one per instance from sum_free_instance(size, seed) for (60,801), (120,802), (240,803) in the verifier (distinct nonzero integers in [-10000, 10000]). Each subset must be sum-free: no a + b = c with a, b, c in it (a = b allowed). Maximize the total size; every n-element set has a sum-free subset of size at least (n+2)/3 (Bourgain).

## State of the art

Instance-solving task; no reference value.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #792](https://www.erdosproblems.com/792), status: open.

- [Sets of integers with no large sum-free subset](https://doi.org/10.4007/annals.2014.180.2.5), Sean Eberhard, Ben Green, Freddie Manners (2014)
- [Erdős Problem #792](https://www.erdosproblems.com/792)

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate f(n), the size of the largest sum-free subset guaranteed in every n-element set of integers (Erdős Problem #792).

Why it matters: Sum-free subsets are a classical problem in additive combinatorics whose constant 1/3 was shown sharp only in 2014.

- [Sets of integers with no large sum-free subset](https://doi.org/10.4007/annals.2014.180.2.5): Main research objective: Estimate f(n), the size of the largest sum-free subset guaranteed in every n-element set of integers (Erdős Problem #792). Task connection: The score totals sum-free subset sizes on three fixed random sets; it measures a search method, not the worst case in f(n).

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The score totals sum-free subset sizes on three fixed random sets; it measures a search method, not the worst case in f(n). Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4007/annals.2014.180.2.5 (Sean Eberhard, Ben Green and Freddie Manners, Sets of integers with no large sum-free subset (2014). Crossref record inspected; Erdős Problem #792 page inspected (f(n) >= n/3 (Erdős), (n+2)/3 (Bourgain), n/3 + c log log n (Bedert 2025); f(n) <= n/3 + o(n) (Eberhard, Green and Manners); Problem 1 on Green's list). The score totals sum-free subset sizes on three fixed random sets; it measures a search method, not the worst case in f(n).)
- archive: https://www.erdosproblems.com/792 (Erdős Problem #792 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000651 (JSP-000651; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Instance-solving task on three fixed pseudo-random sets.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
