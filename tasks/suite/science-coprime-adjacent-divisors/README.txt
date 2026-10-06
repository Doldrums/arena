# Integers up to 10^18 with many coprime adjacent divisors

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-coprime-adjacent-divisors`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> an integer n with 2 <= n <= 10^18. With the divisors of n in increasing order (exact factorization), the score tau_perp(n) is the number of adjacent pairs d_i < d_{i+1} with gcd 1. Maximize. Large values below 10^18 are finite lower-bound constructions for the maximal order of tau_perp.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> an integer n with 2 <= n <= 10^18. With the divisors of n in increasing order (exact factorization), the score tau_perp(n) is the number of adjacent pairs d_i < d_{i+1} with gcd 1. Maximize.

## State of the art

No documented record values.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1100](https://www.erdosproblems.com/1100), status: open.

- [On some unconventional problems on the divisors of integers](https://doi.org/10.1017/S1446788700021455), P. Erdős, R. R. Hall (1978)
- [Erdős Problem #1100](https://www.erdosproblems.com/1100)

Parameters: `{"bound": 1000000000000000000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the growth of tau_perp(n), the number of coprime adjacent divisor pairs (Erdős Problem #1100).

Why it matters: The problem probes the fine multiplicative structure of divisor sequences studied by Erdős, Hall and Tenenbaum.

- [On some unconventional problems on the divisors of integers](https://doi.org/10.1017/S1446788700021455): Main research objective: Determine the growth of tau_perp(n), the number of coprime adjacent divisor pairs (Erdős Problem #1100). Task connection: Large values below 10^18 are finite lower-bound constructions for the maximal order of tau_perp.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Large values below 10^18 are finite lower-bound constructions for the maximal order of tau_perp. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1017/S1446788700021455 (Paul Erdős and R. R. Hall, On some unconventional problems on the divisors of integers (1978). Crossref record inspected; Erdős Problem #1100 page inspected (Erdős and Hall: max_{n<x} tau_perp(n) > exp((log log x)^(2-eps)); is tau_perp(n) < exp((log n)^(o(1)))? Erdős and Simonovits: (2^(1/2)+o(1))^k < g(k) < (2-c)^k for squarefree n with k prime factors). No finite records are documented. Large values below 10^18 are finite lower-bound constructions for the maximal order of tau_perp.)
- archive: https://www.erdosproblems.com/1100 (Erdős Problem #1100 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000913 (JSP-000913; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
