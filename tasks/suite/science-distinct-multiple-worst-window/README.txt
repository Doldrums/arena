# Worst interval starts for distinct-multiple matching

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-distinct-multiple-worst-window`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> Python integer m in 0..1000000. The evaluator computes f(12,m), the LEAST positive L such that (m,m+L] contains distinct b_1,...,b_12 with i dividing b_i. Maximize this independently computed L. Exact bipartite matching plus monotone binary search evaluates every proposal. The task fixes n=12 and bounds m by one million; it optimizes the exact finite f(n,m). It neither searches arbitrary integer sets as in JSP-000578 nor establishes asymptotic worst-case growth.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> Python integer m in 0..1000000. The evaluator computes f(12,m), the LEAST positive L such that (m,m+L] contains distinct b_1,...,b_12 with i dividing b_i. Maximize this independently computed L. Exact bipartite matching plus monotone binary search evaluates every proposal.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Wouter van Doorn (2026, On the length of an interval that contains distinct multiples of the first n positive integers) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [On the length of an interval that contains distinct multiples of the first n positive integers](https://math.colgate.edu/~integers/aa7/aa7.pdf), Wouter van Doorn (2026)

Parameters: `{"n": 12, "maximum_start": 1000000}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal interval lengths needed to match each small divisor to a distinct multiple.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Wouter van Doorn, On the length of an interval that contains distinct multiples of the first n positive integers (2026)](https://math.colgate.edu/~integers/aa7/aa7.pdf): Main research objective: Determine extremal interval lengths needed to match each small divisor to a distinct multiple. Task connection: The task fixes n=12 and bounds m by one million; it optimizes the exact finite f(n,m). It neither searches arbitrary integer sets as in JSP-000578 nor establishes asymptotic worst-case growth.

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

- paper: https://math.colgate.edu/~integers/aa7/aa7.pdf (Wouter van Doorn, On the length of an interval that contains distinct multiples of the first n positive integers (2026). Section 1 defines f(n,m) with the half-open interval (m,m+f(n,m)] and studies max_m f(n,m)-f(n,n).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000580 (JSP-000580; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The task fixes n=12 and bounds m by one million; it optimizes the exact finite f(n,m). It neither searches arbitrary integer sets as in JSP-000578 nor establishes asymptotic worst-case growth.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
