# Prime decompositions of even integers

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-goldbach-prime-decompositions`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 256 rows for even targets 1000000+2*i, i=0..255. Each row is None (unsolved) or a pair of primes summing to the target; equal primes are allowed. Maximize the fraction solved; every claimed pair is checked and any malformed claim invalidates the candidate. Construct prime pairs for 256 even targets from 1000000 to 1000510. These inputs are far within published verification ranges; maximizing coverage is a rediscovery exercise.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 256 rows for even targets 1000000+2*i, i=0..255. Each row is None (unsolved) or a pair of primes summing to the target; equal primes are allowed. Maximize the fraction solved; every claimed pair is checked and any malformed claim invalidates the candidate.

## State of the art

Every even number up to 4·10^18 is a sum of two primes (Oliveira e Silva, Herzog and Pardi), so all 256 targets are solvable and the maximum fraction is 1.

Reference value: proven optimum `1.0` (reviewed 2026-09-24).

- [Empirical verification of the even Goldbach conjecture and computation of prime gaps up to 4·10^18](https://doi.org/10.1090/S0025-5718-2013-02787-1), Tomás Oliveira e Silva, Siegfried Herzog, Silvio Pardi (2014)

Parameters: `{"start": 1000000, "count": 256}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Verify finite ranges of the even Goldbach conjecture using explicit prime decompositions.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Empirical verification of the even Goldbach conjecture and computation of prime gaps up to 4·10^18](https://doi.org/10.1090/S0025-5718-2013-02787-1): Main research objective: Verify finite ranges of the even Goldbach conjecture using explicit prime decompositions. Task connection: Construct prime pairs for 256 even targets from 1000000 to 1000510. These inputs are far within published verification ranges; maximizing coverage is a rediscovery exercise.

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

- paper: https://doi.org/10.1090/S0025-5718-2013-02787-1 (Tomás Oliveira e Silva, Siegfried Herzog and Silvio Pardi, Empirical verification of the even Goldbach conjecture and computation of prime gaps up to 4·10^18. Original author project https://sweet.ua.pt/tos/goldbach.html inspected: definitions, finite verification, and full 2014 paper citation (Mathematics of Computation 83, 2033–2060).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000008 (JSP-000008; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Construct prime pairs for 256 even targets from 1000000 to 1000510. These inputs are far within published verification ranges; maximizing coverage is a rediscovery exercise.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
