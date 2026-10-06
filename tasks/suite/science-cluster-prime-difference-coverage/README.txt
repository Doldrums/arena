# Cluster primes with complete even-difference coverage

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-cluster-prime-difference-coverage`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a prime p with 3<=p<=maximum=100000. Every positive even d<=p-3 must be a difference of two primes <=p. The evaluator independently checks all differences. Maximize p. Maximize a cluster prime at most 100000; every even difference through p-3 is checked using primes at most p. No density theorem or infinity claim follows. The optimum is 99991, the largest prime below 10^5, which is itself a cluster prime (OEIS A038134); this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a prime p with 3<=p<=maximum=100000. Every positive even d<=p-3 must be a difference of two primes <=p. The evaluator independently checks all differences. Maximize p.

## State of the art

99991, the largest prime below 10^5, is itself a cluster prime, so it is the maximum. OEIS A038134 lists all 1807 cluster primes up to 10^5, and the count was recomputed here. Whether infinitely many cluster primes exist is Erdős Problem #17. Blecksmith, Erdős and Selfridge proved that they have density zero among the primes.

Reference value: proven optimum `99991` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #17](https://www.erdosproblems.com/17), status: open.

- [OEIS A038134: Cluster primes](https://oeis.org/A038134)
- [Cluster Primes](https://doi.org/10.1080/00029890.1999.12005005), Richard Blecksmith, Paul Erdős, J. L. Selfridge (1999)
- [On cluster primes](https://www.impan.pl/shop/en/publication/transaction/download/product/81920), Christian Elsholtz (2003)

Parameters: `{"maximum": 100000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand how rare primes with complete smaller even prime-difference coverage are.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [On cluster primes](https://www.impan.pl/shop/en/publication/transaction/download/product/81920): Main research objective: Understand how rare primes with complete smaller even prime-difference coverage are. Task connection: Maximize a cluster prime at most 100000; every even difference through p-3 is checked using primes at most p. No density theorem or infinity claim follows.

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

- paper: https://www.impan.pl/shop/en/publication/transaction/download/product/81920 (Christian Elsholtz, On cluster primes. Acta Arithmetica 109.3 (2003), p.281 definition and abstract inspected. Original cluster-prime terminology is credited there to Blecksmith, Erdős and Selfridge.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000054 (JSP-000054; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Solved finite case: 99991, the largest prime below 10^5, is itself a cluster prime, so it is the maximum.
- Maximize a cluster prime at most 100000; every even difference through p-3 is checked using primes at most p. No density theorem or infinity claim follows.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
