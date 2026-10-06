# Large integer sets with unique triple sums

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-unique-triple-sum-b3-4096`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..80 distinct positive integers <=n=4096. Every unordered triple, allowing repetitions, must have a different sum. Maximize cardinality. At most 80 positive integers in [1,4096], with all unordered triples including repetitions having unique sums. This is B_3[1], not the g>=2 improvement in the cited paper.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..80 distinct positive integers <=n=4096. Every unordered triple, allowing repetitions, must have a different sum. Maximize cardinality.

## State of the art

No documented maximum for B_3 sets in [1,4096]; the greedy B_3 sequence (OEIS A096772) already has 16 terms up to 4048. Asymptotically the maximum is between (1+o(1))N^(1/3) (Bose and Chowla) and ((7/2)^(1/3)+o(1))N^(1/3) (Green), Erdős Problem #241.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #241](https://www.erdosproblems.com/241), status: open ($100).

- [Upper bounds for B_h[g]-sets with small h](https://arxiv.org/abs/1604.00661), Craig Timmons (2016)
- [OEIS A096772: Greedy B_3 sequence](https://oeis.org/A096772)

Parameters: `{"n": 4096, "maximum": 80}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Bound cardinalities of sets with limited higher-order additive representations.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.


The verified research results are for g>=2, while the local task uses g=1. The primary source establishes the general definition; exact objective-specific importance requires a matching g=1 paper.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1604.00661 (Craig Timmons, Upper bounds for B_h[g]-sets with small h. Author abstract and B_h[g] framework checked. The paper’s improved bounds focus on g>=2; local multiplicity is g=1.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000069 (JSP-000069; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- At most 80 positive integers in [1,4096], with all unordered triples including repetitions having unique sums. This is B_3[1], not the g>=2 improvement in the cited paper.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
