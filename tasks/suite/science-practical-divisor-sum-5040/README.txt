# Short sums of distinct divisors of 5040

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-practical-divisor-sum-5040`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> at most 256 distinct positive divisors of n=5040 whose sum is target=4979. Minimize the number of selected divisors. Exact membership and sum checks; this is one finite practical-number instance. Represent 4979 as a sum of distinct divisors of 5040, minimizing the number of terms. This is one finite optimization instance, not Vose’s asymptotic theorem.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> at most 256 distinct positive divisors of n=5040 whose sum is target=4979. Minimize the number of selected divisors. Exact membership and sum checks; this is one finite practical-number instance.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Michael D. Vose (1985, Egyptian Fractions) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Egyptian Fractions](https://doi.org/10.1112/blms/17.1.21), Michael D. Vose (1985)

Parameters: `{"n": 5040, "target": 4979}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Minimize the number of distinct divisors needed to represent an integer below a practical number.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.


Vose’s paper identity is verified, but its specific minimum-term theorem was not checked in primary full text. A related practical-number definition does not by itself establish this exact objective as a primary research goal.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1112/blms/17.1.21 (Michael D. Vose, Egyptian Fractions. Publisher metadata verified: Bulletin of the London Mathematical Society 17 (1985), 21–24. Full text was not accessible in this review. Practical-number definition additionally checked in Weingartner, arXiv:1405.2585.)
- paper: https://arxiv.org/abs/1405.2585 (Andreas Weingartner, Practical numbers and the distribution of divisors: primary abstract confirms distinct-divisor-sum definition, but does not establish the local minimum-term objective.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000055 (JSP-000055; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Represent 4979 as a sum of distinct divisors of 5040, minimizing the number of terms. This is one finite optimization instance, not Vose’s asymptotic theorem.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
