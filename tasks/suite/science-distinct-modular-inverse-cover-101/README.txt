# Short distinct-denominator inverse sums covering residues modulo 101

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-distinct-modular-inverse-cover-101`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> 101 nonempty lists, row r containing distinct denominators in 1..10 whose modular inverses sum to r modulo 101. Every residue must be represented. Minimize the largest row length. Denominators may recur across different rows, but never within one row. The local p=101, denominator-bound-ten problem is a concrete finite covering certificate; it does not reproduce the all-prime, arbitrary-epsilon theorem.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 101 nonempty lists, row r containing distinct denominators in 1..10 whose modular inverses sum to r modulo 101. Every residue must be represented. Minimize the largest row length. Denominators may recur across different rows, but never within one row.

## State of the art

Enumerating all 1023 nonempty subsets of {1, ..., 10} (scripts/check_state_of_the_art.py) shows that every residue modulo 101 is a sum of inverses of distinct denominators. One residue needs 5 terms, so the minimum possible longest row is 5. Shparlinski's theorem answers the asymptotic question (Erdős Problem #1180).

Reference value: proven optimum `5` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1180](https://www.erdosproblems.com/1180), status: proved.

- [On a question of Erdős and Graham](https://doi.org/10.1007/s00013-002-8269-2), Igor E. Shparlinski (2002)

Parameters: `{"p": 101, "interval": 10}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Represent every residue modulo a prime as a short sum of inverses of small distinct integers.

Why it matters: The representation constraint and maximum number of terms instantiate the number-theoretic covering question solved in the cited paper.

- [On a question of Erdos and Graham](https://doi.org/10.1007/s00013-002-8269-2): Main research objective: Represent every residue modulo a prime as a short sum of inverses of small distinct integers. Task connection: The local p=101, denominator-bound-ten problem is a concrete finite covering certificate; it does not reproduce the all-prime, arbitrary-epsilon theorem.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The local p=101, denominator-bound-ten problem is a concrete finite covering certificate; it does not reproduce the all-prime, arbitrary-epsilon theorem. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/s00013-002-8269-2 (Igor E. Shparlinski, On a question of Erdos and Graham (2002). Author's institutional abstract inspected. It explicitly requires pairwise distinct denominator integers; the feasibility proposal allowing repetitions was corrected. The local p=101, denominator-bound-ten problem is a concrete finite covering certificate; it does not reproduce the all-prime, arbitrary-epsilon theorem.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000985 (JSP-000985; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- Nonempty representations are required even for residue zero. A finite optimum does not establish a bound independent of the prime.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
