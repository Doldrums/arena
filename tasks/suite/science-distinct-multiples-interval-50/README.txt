# Shortest interval above 50 containing distinct multiples of 1, ..., 50

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-distinct-multiples-interval-50`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> integers b_1, ..., b_50 with 50 < b_i <= 5000, i | b_i and all b_i distinct. The score is max(b) - 50 + 1, the least k with every b_i in the open interval (50, 50 + k). Minimize; the optimum is 77. For n = 50 the optimum is 77, so the task recovers an optimal matching.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> integers b_1, ..., b_50 with 50 < b_i <= 5000, i | b_i and all b_i distinct. The score is max(b) - 50 + 1, the least k with every b_i in the open interval (50, 50 + k). Minimize; the optimum is 77.

## State of the art

f(50) = 77 (OEIS A390246).

Reference value: proven optimum `77` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #710](https://www.erdosproblems.com/710), status: open.

- [OEIS A390246: Least k such that distinct b_1..b_n with n < b_i < n+k and i | b_i exist](https://oeis.org/A390246)
- [Matching the natural numbers up to n with distinct multiples in another interval](https://doi.org/10.1016/1385-7258(80)90018-9), Paul Erdős, Carl Pomerance (1980)

Parameters: `{"n": 50}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find an asymptotic formula for f(n), the length of the shortest interval (n, n + f(n)) containing distinct multiples of 1, ..., n (Erdős Problem #710).

Why it matters: A matching problem between integers and their multiples, tied to smooth numbers and Hall-type arguments; the asymptotic formula is open.

- [Matching the natural numbers up to n with distinct multiples in another interval](https://doi.org/10.1016/1385-7258(80)90018-9): Main research objective: Find an asymptotic formula for f(n), the length of the shortest interval (n, n + f(n)) containing distinct multiples of 1, ..., n (Erdős Problem #710). Task connection: For n = 50 the optimum is 77, so the task recovers an optimal matching.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 50 the optimum is 77, so the task recovers an optimal matching. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/1385-7258(80)90018-9 (Paul Erdős and Carl Pomerance, Matching the natural numbers up to n with distinct multiples in another interval (1980). Crossref record inspected; Erdős Problem #710 page inspected (Erdős and Pomerance: (2/sqrt e + o(1)) n (log n/log log n)^(1/2) <= f(n) <= (1.7398...+o(1)) n (log n)^(1/2); Erdős offered 2000 rupees for an asymptotic formula). OEIS A390246 inspected (b-file by Kesarwani): f(50) = 77. For n = 50 the optimum is 77, so the task recovers an optimal matching.)
- archive: https://www.erdosproblems.com/710 (Erdős Problem #710 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000579 (JSP-000579; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
