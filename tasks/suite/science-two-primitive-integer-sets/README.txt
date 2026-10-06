# Large integer sets with no two-other-product divisibility

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-two-primitive-integer-sets`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> nonempty distinct integers in 2..256. For every THREE DISTINCT members a,b,c, require that a does not divide b*c. Maximize cardinality. In particular b and c cannot denote the same member; this convention is part of the finite contract. Only the interval up to 256 is searched. The verifier uses three distinct members, and it does not claim a sharp asymptotic error term or optimal cardinality.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> nonempty distinct integers in 2..256. For every THREE DISTINCT members a,b,c, require that a does not divide b*c. Maximize cardinality. In particular b and c cannot denote the same member; this convention is part of the finite contract.

## State of the art

No documented value for n = 256. Erdős proved F(n) = pi(n) + Theta(n^(2/3)/(log n)^2), and the asymptotic constant asked for in Erdős Problem #793 has been established.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #793](https://www.erdosproblems.com/793), status: proved (Lean).

- [On sequences of integers no one of which divides the product of two others and on some related problems](https://www.renyi.hu/~p_erdos/1938-07.pdf), Paul Erdős (1938)

Parameters: `{"n": 256}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand the maximum density of multiplicative divisibility-avoiding sets.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Paul Erdős, On sequences of integers no one of which divides the product of two others and on some related problems (1938)](https://www.renyi.hu/~p_erdos/1938-07.pdf): Main research objective: Understand the maximum density of multiplicative divisibility-avoiding sets. Task connection: Only the interval up to 256 is searched. The verifier uses three distinct members, and it does not claim a sharp asymptotic error term or optimal cardinality.

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

- paper: https://www.renyi.hu/~p_erdos/1938-07.pdf (Paul Erdős, On sequences of integers no one of which divides the product of two others and on some related problems (1938). Introduction and section 1 study A-sequences in which no member divides the product of two other members; the sequence of primes is an explicit example.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000652 (JSP-000652; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- Only the interval up to 256 is searched. The verifier uses three distinct members, and it does not claim a sharp asymptotic error term or optimal cardinality.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
