# Approximate a ratio inside a divisor-sum fiber

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-equal-divisor-sum-ratio-approximation`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> [a,b], positive Python integers <=10000000. Require sigma(a)=sigma(b), where sigma includes ALL positive divisors. Minimize |a/b-3/2|. Factorization and rational error are exact; the score is the binary64 serialization of that rational, with its exact numerator/denominator reported. Only the target 3/2 and inputs bounded by ten million are evaluated. A smaller exact rational error is a finite approximation, not a density proof for all positive real targets. Tiny error differences can round to the same floating score.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [a,b], positive Python integers <=10000000. Require sigma(a)=sigma(b), where sigma includes ALL positive divisors. Minimize |a/b-3/2|. Factorization and rational error are exact; the score is the binary64 serialization of that rational, with its exact numerator/denominator reported.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Paul Pollack (2015, Remarks on fibers of the sum-of-divisors function) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Remarks on fibers of the sum-of-divisors function](https://www.pollack-math.net/preimages-maier3.pdf), Paul Pollack (2015)

Parameters: `{"maximum": 10000000, "target": [3, 2]}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand which ratios occur between integers sharing a sum-of-divisors value.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Paul Pollack, Remarks on fibers of the sum-of-divisors function (2015)](https://www.pollack-math.net/preimages-maier3.pdf): Main research objective: Understand which ratios occur between integers sharing a sum-of-divisors value. Task connection: Only the target 3/2 and inputs bounded by ten million are evaluated. A smaller exact rational error is a finite approximation, not a density proof for all positive real targets. Tiny error differences can round to the same floating score.

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

- paper: https://www.pollack-math.net/preimages-maier3.pdf (Paul Pollack, Remarks on fibers of the sum-of-divisors function (2015). Abstract and Theorem 1: every positive real number can be approximated by m/n with equal sigma values.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000679 (JSP-000679; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- Only the target 3/2 and inputs bounded by ten million are evaluated. A smaller exact rational error is a finite approximation, not a density proof for all positive real targets. Tiny error differences can round to the same floating score.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
