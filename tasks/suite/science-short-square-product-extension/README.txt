# Short intervals supplying a square-product extension

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-short-square-product-extension`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> 1..100 distinct integers strictly larger than 210 and at most 10210. Their product multiplied by 210 must be a perfect square. Minimize max(selected integers)-210. An arbitrary-precision integer square root verifies the exact condition. The task fixes n=210, a nonsquare, and bounds the certificate and following window. A certificate gives an upper bound on t_210; exact optimality and the distribution over n are not established.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..100 distinct integers strictly larger than 210 and at most 10210. Their product multiplied by 210 must be a perfect square. Minimize max(selected integers)-210. An arbitrary-precision integer square root verifies the exact condition.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Hung M. Bui, Kyle Pratt and Alexandru Zaharescu (2022, A problem of Erdős–Graham–Granville–Selfridge on integral points on hyperelliptic curves) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [A problem of Erdős–Graham–Granville–Selfridge on integral points on hyperelliptic curves](https://arxiv.org/abs/2211.12467), Hung M. Bui, Kyle Pratt and Alexandru Zaharescu (2022)

Parameters: `{"n": 210, "maximum_window": 10000, "maximum_size": 100}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand the size and distribution of square-product completion intervals.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Hung M. Bui, Kyle Pratt and Alexandru Zaharescu, A problem of Erdős–Graham–Granville–Selfridge on integral points on hyperelliptic curves (2022 preprint; 2024 publication)](https://arxiv.org/abs/2211.12467): Main research objective: Understand the size and distribution of square-product completion intervals. Task connection: The task fixes n=210, a nonsquare, and bounds the certificate and following window. A certificate gives an upper bound on t_210; exact optimality and the distribution over n are not established.

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

- paper: https://arxiv.org/abs/2211.12467 (Hung M. Bui, Kyle Pratt and Alexandru Zaharescu, A problem of Erdős–Graham–Granville–Selfridge on integral points on hyperelliptic curves (2022 preprint; 2024 publication). Abstract defines t_n as the least following-interval length whose selected members multiply with n to a square.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000697 (JSP-000697; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The task fixes n=210, a nonsquare, and bounds the certificate and following window. A certificate gives an upper bound on t_210; exact optimality and the distribution over n are not established.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
