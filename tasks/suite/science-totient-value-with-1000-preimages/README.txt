# Smallest totient value with exactly 1000 preimages

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-totient-value-with-1000-preimages`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> an integer m with 1 <= m <= 10^8 such that phi(x) = m has exactly 1000 solutions x (counted exactly by recursion over the primes p with p - 1 dividing m). Minimize m; the optimum is 1360800. The least value with exactly 1000 preimages is 1360800, so the task recovers it.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> an integer m with 1 <= m <= 10^8 such that phi(x) = m has exactly 1000 solutions x (counted exactly by recursion over the primes p with p - 1 dividing m). Minimize m; the optimum is 1360800.

## State of the art

The least m with exactly 1000 solutions of phi(x) = m is 1360800 (OEIS A007374).

Reference value: proven optimum `1360800` (reviewed 2026-09-24).

- [OEIS A007374: Smallest k such that phi(x) = k has exactly n solutions](https://oeis.org/A007374)
- [The Number of Solutions of φ(x) = m](https://doi.org/10.2307/121103), Kevin Ford (1999)

Parameters: `{"k": 1000, "maximum": 100000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine which multiplicities the Euler totient function attains (Carmichael's and Sierpiński's conjectures).

Why it matters: Carmichael's totient conjecture (no value has exactly one preimage) is open; Ford's theorem on all other multiplicities is a landmark of multiplicative number theory.

- [The Number of Solutions of φ(x) = m](https://doi.org/10.2307/121103): Main research objective: Determine which multiplicities the Euler totient function attains (Carmichael's and Sierpiński's conjectures). Task connection: The least value with exactly 1000 preimages is 1360800, so the task recovers it.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The least value with exactly 1000 preimages is 1360800, so the task recovers it. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.2307/121103 (Kevin Ford, The Number of Solutions of φ(x) = m (1999). Crossref record inspected: Ford proved Sierpiński's conjecture that every multiplicity k >= 2 occurs. OEIS A007374 inspected (b-file by Noe, Johnson and McCranie): the smallest m with exactly 1000 totient preimages is 1360800; the count for 1360800 was reproduced locally. The least value with exactly 1000 preimages is 1360800, so the task recovers it.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000677 (JSP-000677; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table. No Erdős Problems page corresponds to this bank entry.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
