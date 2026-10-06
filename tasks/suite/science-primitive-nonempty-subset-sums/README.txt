# Large sets with divisibility-incomparable subset sums

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-primitive-nonempty-subset-sums`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..30 distinct integers in 1..256. Form every NONEMPTY subset sum; no two distinct resulting values may divide one another. Equal sum values are deduplicated (but any repeated subset representation also leads to a forbidden double after cancellation). Maximize set size. The local N=256 construction is checked by exact reachability and a multiples sieve. The empty sum is excluded, and no general asymptotic improvement or formal proof is claimed.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..30 distinct integers in 1..256. Form every NONEMPTY subset sum; no two distinct resulting values may divide one another. Equal sum values are deduplicated (but any repeated subset representation also leads to a forbidden double after cancellation). Maximize set size.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Konstantinos Gaitanas (2019, Two divisibility problems on subset sums) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Two divisibility problems on subset sums](https://arxiv.org/abs/1911.11097), Konstantinos Gaitanas (2019)

Parameters: `{"n": 256, "maximum_size": 30}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal sizes of integer sets whose nonempty subset sums are primitive under divisibility.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Konstantinos Gaitanas, Two divisibility problems on subset sums (2019)](https://arxiv.org/abs/1911.11097): Main research objective: Determine extremal sizes of integer sets whose nonempty subset sums are primitive under divisibility. Task connection: The local N=256 construction is checked by exact reachability and a multiples sieve. The empty sum is excluded, and no general asymptotic improvement or formal proof is claimed.

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

- paper: https://arxiv.org/abs/1911.11097 (Konstantinos Gaitanas, Two divisibility problems on subset sums (2019). Section 4, Problem two, defines property R: subset sums form a multiple-free sequence, and attributes the original extremal question to Erdős, Lev, Rauzy, Sándor and Sárközy (1999).)
- paper: https://doi.org/10.1016/S0012-365X(98)00385-9 (Paul Erdős, Vsevolod Lev, Gérard Rauzy, Csaba Sándor and András Sárközy, Greedy algorithm, arithmetic progressions, subset sums and divisibility (1999). Publisher metadata and abstract inspected; property R attribution independently confirmed by Gaitanas (2019), section 4. Original full text was not independently accessible.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000733 (JSP-000733; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local N=256 construction is checked by exact reachability and a multiples sieve. The empty sum is excluded, and no general asymptotic improvement or formal proof is claimed.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
