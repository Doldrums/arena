# Integers M <= 10^18 with many solutions of k*sigma(k) = M

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-many-solutions-k-sigma-k`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'M': M, 'k': [k_1, ...]} with M <= 10^18 and distinct k_i <= sqrt(M) satisfying k_i * sigma(k_i) = M (checked with exact factorization). The score is the number of listed solutions, a certified lower bound for f(M). Maximize. Values with many certified solutions are finite lower-bound constructions for f; no record values are documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'M': M, 'k': [k_1, ...]} with M <= 10^18 and distinct k_i <= sqrt(M) satisfying k_i * sigma(k_i) = M (checked with exact factorization). The score is the number of listed solutions, a certified lower bound for f(M). Maximize.

## State of the art

No documented record values.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1060](https://www.erdosproblems.com/1060), status: open.

- [Unsolved Problems in Number Theory](https://doi.org/10.1007/978-0-387-26677-0), Richard K. Guy (2004)
- [OEIS A337873: Numbers m such that m = k*sigma(k) has more than one solution](https://oeis.org/A337873)

Parameters: `{"bound": 1000000000000000000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound the number of solutions of k sigma(k) = n (Erdős Problem #1060).

Why it matters: Multiplicities of multiplicative functions such as k sigma(k) measure how far they are from injective, in the spirit of Ford's work on totient multiplicities.

- [Unsolved Problems in Number Theory](https://doi.org/10.1007/978-0-387-26677-0): Main research objective: Bound the number of solutions of k sigma(k) = n (Erdős Problem #1060). Task connection: Values with many certified solutions are finite lower-bound constructions for f; no record values are documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Values with many certified solutions are finite lower-bound constructions for f; no record values are documented. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/978-0-387-26677-0 (Richard K. Guy, Unsolved Problems in Number Theory (2004). Crossref record inspected (problem B11). Erdős Problem #1060 page inspected (is f(n) <= n^(o(1/log log n)), perhaps even (log n)^O(1)?). OEIS A327153 and A337873 inspected: values with several solutions such as 333312 = 336 sigma(336) = 372 sigma(372) = 434 sigma(434); no record over a range is documented. Values with many certified solutions are finite lower-bound constructions for f; no record values are documented.)
- archive: https://www.erdosproblems.com/1060 (Erdős Problem #1060 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000880 (JSP-000880; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none). Listed solutions certify a lower bound for f(M), not its exact value.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
