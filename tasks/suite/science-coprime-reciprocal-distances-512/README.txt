# Pairwise coprime integers below 512 with large sum of 1/(512 - a)

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-coprime-reciprocal-distances-512`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct pairwise coprime integers a in 1..511. The score is sum 1/(512 - a) (exact rational, reported as a float); the report also gives sum over primes p < 512 of 1/p. Maximize. Large sums for n = 512 compared with the prime reciprocal sum are finite evidence on the conjectured bound.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct pairwise coprime integers a in 1..511. The score is sum 1/(512 - a) (exact rational, reported as a float); the report also gives sum over primes p < 512 of 1/p. Maximize.

## State of the art

No documented values.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1210](https://www.erdosproblems.com/1210), status: open.

- [A Survey of Problems in Combinatorial Number Theory](https://doi.org/10.1016/S0167-5060(08)70697-6), Paul Erdős (1980)
- [Erdős Problem #1210](https://www.erdosproblems.com/1210)

Parameters: `{"n": 512}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether pairwise coprime integers below n satisfy sum 1/(n - a) <= sum_{p<n} 1/p + O(1) (Erdős Problem #1210).

Why it matters: The question compares arbitrary coprime sets with the primes, the extremal coprime set, in a weighted sense.

- [A Survey of Problems in Combinatorial Number Theory](https://doi.org/10.1016/S0167-5060(08)70697-6): Main research objective: Decide whether pairwise coprime integers below n satisfy sum 1/(n - a) <= sum_{p<n} 1/p + O(1) (Erdős Problem #1210). Task connection: Large sums for n = 512 compared with the prime reciprocal sum are finite evidence on the conjectured bound.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Large sums for n = 512 compared with the prime reciprocal sum are finite evidence on the conjectured bound. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/S0167-5060(08)70697-6 (Paul Erdős, A Survey of Problems in Combinatorial Number Theory (1980). Crossref record inspected (the problem is on p. 112). Erdős Problem #1210 page inspected: is sum 1/(n - a) <= sum_{p < n} 1/p + O(1) for pairwise coprime A in [1, n)? No finite values are documented. Large sums for n = 512 compared with the prime reciprocal sum are finite evidence on the conjectured bound.)
- archive: https://www.erdosproblems.com/1210 (Erdős Problem #1210 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-1001-1022.md#JSP-001015 (JSP-001015; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
