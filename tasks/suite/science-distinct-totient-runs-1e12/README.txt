# Long runs of consecutive integers with distinct totients (up to 10^12)

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-distinct-totient-runs-1e12`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'start': s, 'length': k} with s >= 1, 1 <= k <= 200 and s + k - 1 <= 10^12. The values phi(s), ..., phi(s + k - 1) must be pairwise distinct (exact factorization). Maximize k. Long runs below 10^12 are finite evidence; (log 10^12)^c is about 27.6^c.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'start': s, 'length': k} with s >= 1, 1 <= k <= 200 and s + k - 1 <= 10^12. The values phi(s), ..., phi(s + k - 1) must be pairwise distinct (exact factorization). Maximize k.

## State of the art

No documented values.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1004](https://www.erdosproblems.com/1004), status: open.

- [On Locally Repeated Values of Certain Arithmetic Functions. III](https://doi.org/10.2307/2046541), P. Erdős, C. Pomerance, A. Sárközy (1987)
- [Erdős Problem #1004](https://www.erdosproblems.com/1004)

Parameters: `{"bound": 1000000000000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether runs of length (log x)^c with distinct totients exist below x (Erdős Problem #1004).

Why it matters: Local distinctness of phi mirrors the Erdős-Mirsky divisor problem (#945) and measures the irregularity of multiplicative functions.

- [On Locally Repeated Values of Certain Arithmetic Functions. III](https://doi.org/10.2307/2046541): Main research objective: Decide whether runs of length (log x)^c with distinct totients exist below x (Erdős Problem #1004). Task connection: Long runs below 10^12 are finite evidence; (log 10^12)^c is about 27.6^c.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Long runs below 10^12 are finite evidence; (log 10^12)^c is about 27.6^c. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.2307/2046541 (Paul Erdős, Carl Pomerance and András Sárközy, On Locally Repeated Values of Certain Arithmetic Functions. III (1987). Crossref record inspected; Erdős Problem #1004 page inspected (does some n <= x have phi(n+1), ..., phi(n+K) distinct for K = (log x)^c? Erdős, Pomerance and Sárközy proved K <= n/exp(c(log n)^(1/3))). No finite values are documented. Long runs below 10^12 are finite evidence; (log 10^12)^c is about 27.6^c.)
- archive: https://www.erdosproblems.com/1004 (Erdős Problem #1004 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000836 (JSP-000836; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
