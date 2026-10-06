# Covering an initial interval twice with one residue class per prime up to 1000

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-double-cover-primes-to-1000`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 168 residues, one for each prime p <= 1000 in increasing order, with 0 <= r_p < p. The score is the largest L such that every integer 1..L satisfies at least two of the congruences x = r_p (mod p) (exact count, capped at 10^5). Maximize; L >= 1000 would realize the property asked in Erdős Problem #689 at n = 1000. Scores are doubly covered lengths for n = 1000; reaching 1000 would exhibit the property at this size.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 168 residues, one for each prime p <= 1000 in increasing order, with 0 <= r_p < p. The score is the largest L such that every integer 1..L satisfies at least two of the congruences x = r_p (mod p) (exact count, capped at 10^5). Maximize; L >= 1000 would realize the property asked in Erdős Problem #689 at n = 1000.

## State of the art

No documented values for finite n.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #689](https://www.erdosproblems.com/689), status: open.

- [A Survey of Problems in Combinatorial Number Theory](https://doi.org/10.1016/S0167-5060(08)70697-6), Paul Erdős (1980)
- [Erdős Problem #689](https://www.erdosproblems.com/689)

Parameters: `{"largest_prime": 1000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether, for large n, one residue class per prime p <= n can cover every integer in [1, n] at least twice.

Why it matters: Double covers by prime residues quantify sieve limits beyond Jacobsthal's single-cover problem (Erdős Problem #687).

- [A Survey of Problems in Combinatorial Number Theory](https://doi.org/10.1016/S0167-5060(08)70697-6): Main research objective: Decide whether, for large n, one residue class per prime p <= n can cover every integer in [1, n] at least twice. Task connection: Scores are doubly covered lengths for n = 1000; reaching 1000 would exhibit the property at this size.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Scores are doubly covered lengths for n = 1000; reaching 1000 would exhibit the property at this size. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/S0167-5060(08)70697-6 (Paul Erdős, A Survey of Problems in Combinatorial Number Theory (1980). Crossref record inspected; Erdős Problem #689 page inspected (asked in 1979-1980; the variant with ten covers instead of two is Problem 45 on Green's list of open problems). No finite values are documented. Scores are doubly covered lengths for n = 1000; reaching 1000 would exhibit the property at this size.)
- archive: https://www.erdosproblems.com/689 (Erdős Problem #689 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000561 (JSP-000561; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
