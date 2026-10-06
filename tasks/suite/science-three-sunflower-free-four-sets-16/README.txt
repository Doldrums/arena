# Large four-uniform families without three sunflowers

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-three-sunflower-free-four-sets-16`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..maximum=250 distinct k=4 element subsets of [1,n=16]. No three distinct sets may have all three pairwise intersections equal, including an empty common core. Maximize family cardinality. Maximize a family of four-element subsets of [1,16], with at most 250 members, excluding three-petal sunflowers including the empty-core case.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..maximum=250 distinct k=4 element subsets of [1,n=16]. No three distinct sets may have all three pairwise intersections equal, including an empty common core. Maximize family cardinality.

## State of the art

No documented maximum for families of 4-subsets of a 16-element set without a three-petal sunflower (empty cores included). The exponential sunflower bound is Erdős Problem #20; Alweiss, Lovett, Wu and Zhang improved the general upper bound.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #20](https://www.erdosproblems.com/20), status: open ($1000).

- [Improved bounds for the sunflower lemma](https://arxiv.org/abs/1908.08483), Ryan Alweiss, Shachar Lovett, Kewen Wu, Jiapeng Zhang (2019)

Parameters: `{"n": 16, "k": 4, "petals": 3, "maximum": 250}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how large a uniform set family can be before a sunflower is forced.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Improved bounds for the sunflower lemma](https://arxiv.org/abs/1908.08483): Main research objective: Determine how large a uniform set family can be before a sunflower is forced. Task connection: Maximize a family of four-element subsets of [1,16], with at most 250 members, excluding three-petal sunflowers including the empty-core case.

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

- paper: https://arxiv.org/abs/1908.08483 (Ryan Alweiss, Shachar Lovett, Kewen Wu and Jiapeng Zhang, Improved bounds for the sunflower lemma. Author abstract inspected: three sets form a sunflower when all pairwise intersections agree.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000057 (JSP-000057; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Maximize a family of four-element subsets of [1,16], with at most 250 members, excluding three-petal sunflowers including the empty-core case.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
