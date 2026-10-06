# Long runs after p^2 with no prime factor exceeding p (p <= 10^9)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-smooth-runs-after-prime-squares`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'p': p, 'k': k} with p a prime at most 10^9 and 1 <= k <= 200; every integer p^2 + 1, ..., p^2 + k must have all prime factors at most p (exact factorization by trial division and Pollard-Brent with deterministic Miller-Rabin). Maximize k. Long runs for p <= 10^9 are finite evidence for the conjectured positive answer.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'p': p, 'k': k} with p a prime at most 10^9 and 1 <= k <= 200; every integer p^2 + 1, ..., p^2 + k must have all prime factors at most p (exact factorization by trial division and Pollard-Brent with deterministic Miller-Rabin). Maximize k.

## State of the art

No documented values.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #383](https://www.erdosproblems.com/383), status: open.

- [Old and new problems and results in combinatorial number theory](https://fanchung.ucsd.edu/ron/papers/80_11_number_theory.pdf), Paul Erdős, Ronald L. Graham (1980)
- [Erdős Problem #383](https://www.erdosproblems.com/383)

Parameters: `{"prime_bound": 1000000000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether for every k infinitely many primes p have p^2 + 1, ..., p^2 + k all free of prime factors larger than p (Erdős Problem #383).

Why it matters: The question probes smooth numbers in short intervals near squares, a regime central to sieve theory and factoring algorithms.

- [Old and new problems and results in combinatorial number theory](https://fanchung.ucsd.edu/ron/papers/80_11_number_theory.pdf): Main research objective: Decide whether for every k infinitely many primes p have p^2 + 1, ..., p^2 + k all free of prime factors larger than p (Erdős Problem #383). Task connection: Long runs for p <= 10^9 are finite evidence for the conjectured positive answer.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Long runs for p <= 10^9 are finite evidence for the conjectured positive answer. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://fanchung.ucsd.edu/ron/papers/80_11_number_theory.pdf (Paul Erdős and Ronald L. Graham, Old and new problems and results in combinatorial number theory (1980). Erdős-Graham monograph (L'Enseignement Mathématique, 1980; source of the problem) located. Erdős Problem #383 page inspected: heuristically n has no prime factor >= n^(1/2) with probability 1 - log 2, so a positive answer is expected; it would settle part of #382. No finite values are documented. Long runs for p <= 10^9 are finite evidence for the conjectured positive answer.)
- archive: https://www.erdosproblems.com/383 (Erdős Problem #383 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0301-0400.md#JSP-000317 (JSP-000317; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
