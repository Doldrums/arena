# Dense odd-order graphs avoiding equal-degree path endpoints

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-equal-degree-three-path-avoidance`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> simple undirected edges on vertices 0..14. Reject if any simple three-edge path has endpoints of equal degree in the FULL candidate graph. Extra chords are allowed: paths need not be induced. Maximize edge count. The local order fifteen lies outside the cited n>=600 theorem. Every length-three path is checked directly; no use of the asymptotic edge threshold to reject valid candidates is made.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> simple undirected edges on vertices 0..14. Reject if any simple three-edge path has endpoints of equal degree in the FULL candidate graph. Extra chords are allowed: paths need not be induced. Maximize edge count.

## State of the art

No documented maximum for 15 vertices. K_{7,8} has 56 edges and no such path, and Chen and Ma proved that this bound is sharp for 2n+1 vertices when n >= 600 (Erdős Problem #816).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #816](https://www.erdosproblems.com/816), status: proved.

- [A problem of Erdős and Hajnal on paths with equal-degree endpoints](https://arxiv.org/abs/2503.19569), Kaizhe Chen, Jie Ma (2025)

Parameters: `{"n": 15}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine edge thresholds forcing short paths whose endpoints have equal degrees.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Kaizhe Chen and Jie Ma, A problem of Erdős and Hajnal on paths with equal-degree endpoints (2025)](https://arxiv.org/abs/2503.19569): Main research objective: Determine edge thresholds forcing short paths whose endpoints have equal degrees. Task connection: The local order fifteen lies outside the cited n>=600 theorem. Every length-three path is checked directly; no use of the asymptotic edge threshold to reject valid candidates is made.

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

- paper: https://arxiv.org/abs/2503.19569 (Kaizhe Chen and Jie Ma, A problem of Erdős and Hajnal on paths with equal-degree endpoints (2025). Author abstract: every (2n+1)-vertex graph above an edge threshold has equal-degree vertices connected by a path of length three; theorem is stated for n>=600.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000673 (JSP-000673; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local order fifteen lies outside the cited n>=600 theorem. Every length-three path is checked directly; no use of the asymptotic edge threshold to reject valid candidates is made.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
