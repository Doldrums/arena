# Large pairwise noncoprime sets containing the interval endpoint

**Source collection:** [Problem-bank constructions: arithmetic and extremal sets: source-based research tasks](../../papers/science-prize_b.md)\
**Task id:** `science-number-theory-noncoprime-forced`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Return a nonempty subset of [1,255] containing 255, with gcd(a,b)>1 for all distinct pairs. Maximize cardinality. Fixes n=255 in g(n), the source's exact forced-maximum-element formulation; no solution to a general coprime-family conjecture is claimed.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> candidate. Return a nonempty subset of [1,255] containing 255, with gcd(a,b)>1 for all distinct pairs. Maximize cardinality.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Rudolf Ahlswede and Levon H. Khachatrian (1996, Sets of integers with pairwise common divisor and a factor from a specified set of primes) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Sets of integers with pairwise common divisor and a factor from a specified set of primes](https://matwbn.icm.edu.pl/ksiazki/aa/aa75/aa7536.pdf), Rudolf Ahlswede and Levon H. Khachatrian (1996)

Parameters: `{"n": 255, "forced": 255}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine largest integer families with pairwise common divisors and prescribed prime factors.

Why it matters: Studies extremal intersection properties of arithmetic sets through shared prime factors.

- [Sets of integers with pairwise common divisor and a factor from a specified set of primes](https://matwbn.icm.edu.pl/ksiazki/aa/aa75/aa7536.pdf): Main research objective: Determine largest integer families with pairwise common divisors and prescribed prime factors. Task connection: Primary introduction p. 259 explicitly defines g(n) with a_k=n; local n=255 is that exact extremal problem. Fixes n=255 in g(n), the source's exact forced-maximum-element formulation; no solution to a general coprime-family conjecture is claimed.

A primary research paper directly studies the mathematical objective; local finite scope and restrictions are explicit. This does not certify novelty, importance of the baseline itself, or current open status.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Fixes n=255 in g(n), the source's exact forced-maximum-element formulation; no solution to a general coprime-family conjecture is claimed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://matwbn.icm.edu.pl/ksiazki/aa/aa75/aa7536.pdf (Rudolf Ahlswede and Levon H. Khachatrian (1996), Sets of integers with pairwise common divisor and a factor from a specified set of primes. Printed p. 259. Fixes n=255 in g(n), the source's exact forced-maximum-element formulation; no solution to a general coprime-family conjecture is claimed. Primary introduction inspected; author/publisher metadata independently verified. No source code reused.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000428 (JSP-000428; pinned Justin Sun Prize bank revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Discovery source only; mathematical authorship remains with the cited researchers. Independent paraphrase and implementation.)

## Limitations

- Independent finite adaptation, not a Lean proof, prize submission, full solution, optimality proof or claim of mathematical novelty.
- Published source supplies the mathematical question; all verifier and starter code was written locally, with no upstream implementation imported.
- Finite bounds and the public starter are development instances. An accepted candidate establishes only the reported local feasible value; no asymptotic inference follows.
- Candidate Python code is trusted; this runner is not a malicious-code sandbox.
- Fixes n=255 in g(n), the source's exact forced-maximum-element formulation; no solution to a general coprime-family conjecture is claimed.
