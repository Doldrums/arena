# No element dividing a sum of three others

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-nondividing-three-other-sums-192`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..maximum=48 distinct positive integers <=n=192. No selected integer may divide the sum of any k=3 DISTINCT OTHER selected integers. Maximize cardinality. This excludes the tested element from the summands. Follow the prize bank’s prescribed-number wording: k=3 distinct OTHER summands in [1,192], at most 48 elements. This relaxes the broader all-subsets condition in Erdős’s survey and is not attributed as his exact original statement.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..maximum=48 distinct positive integers <=n=192. No selected integer may divide the sum of any k=3 DISTINCT OTHER selected integers. Maximize cardinality. This excludes the tested element from the summands.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Paul Erdős (1975, Problems and results in combinatorial number theory) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Problems and results in combinatorial number theory](https://numdam.org/item/AST_1975__24-25__295_0.pdf), Paul Erdős (1975)

Parameters: `{"n": 192, "k": 3, "maximum": 48}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Study extremal divisibility restrictions between set elements and sums of other elements.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.


Primary survey attribution is related but its all-subsets condition is stronger than the bank’s prescribed-k wording. The explicit k=3 local adaptation is unreviewed for scientific importance, and no source-equivalence claim is made.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://numdam.org/item/AST_1975__24-25__295_0.pdf (Paul Erdős, Problems and results in combinatorial number theory. Astérisque 24–25 (1975), 295–310, p.309 inspected. The primary text studies divisibility by sums of other elements without fixing their number.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000137 (JSP-000137; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Follow the prize bank’s prescribed-number wording: k=3 distinct OTHER summands in [1,192], at most 48 elements. This relaxes the broader all-subsets condition in Erdős’s survey and is not attributed as his exact original statement.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
