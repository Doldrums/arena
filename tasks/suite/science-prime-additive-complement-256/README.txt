# Small additive complements of the primes

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-prime-additive-complement-256`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> a nonempty subset B of [0,n=256] such that every integer in [256,512] is p+b for a prime p and b in B. Minimize |B|. All primes and target coverage are recomputed. Choose B in [0,256] so every integer in [256,512] is prime plus B, and minimize |B|. This only certifies finite coverage, not an asymptotic complement. The optimum is 10, established by an exact set-cover computation; this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty subset B of [0,n=256] such that every integer in [256,512] is p+b for a prime p and b in B. Minimize |B|. All primes and target coverage are recomputed.

## State of the art

The minimum is 10: {11, 16, 80, 117, 199, 204, 223, 225, 228, 242} covers [256,512]. Exact set-cover integer programmes show that 9 elements cannot. The programmes are split by parity, with every case of the prime 2 enumerated, and solved with HiGHS (scripts/check_state_of_the_art.py --slow). The asymptotic question is Erdős Problem #32.

Reference value: proven optimum `10` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #32](https://www.erdosproblems.com/32), status: open ($50).

- [The additive complements of primes and Goldbach's problem](https://doi.org/10.4064/aa162-3-1), Li-Xia Dai, Hao Pan (2014)

Parameters: `{"n": 256}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct sparse additive complements of the primes.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [The additive complements of primes and Goldbach’s problem](https://www.impan.pl/shop/en/publication/transaction/download/product/83028): Main research objective: Construct sparse additive complements of the primes. Task connection: Choose B in [0,256] so every integer in [256,512] is prime plus B, and minimize |B|. This only certifies finite coverage, not an asymptotic complement.

A problem-focused primary paper studies the same substantive mathematical construction or extremal quantity. No novelty claim is implied.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://www.impan.pl/shop/en/publication/transaction/download/product/83028 (Li-Xia Dai and Hao Pan, The additive complements of primes and Goldbach’s problem. Acta Arithmetica 162 (2014), 209–221, introduction inspected; DOI 10.4064/aa162-3-1.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000063 (JSP-000063; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Solved finite case: The minimum is 10: {11, 16, 80, 117, 199, 204, 223, 225, 228, 242} covers [256,512].
- Choose B in [0,256] so every integer in [256,512] is prime plus B, and minimize |B|. This only certifies finite coverage, not an asymptotic complement.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
