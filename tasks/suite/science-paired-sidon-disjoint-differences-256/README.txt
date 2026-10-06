# Two Sidon sets with disjoint difference sets

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-paired-sidon-disjoint-differences-256`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> [A,B], two nonempty Sidon subsets of [1,n=256], at most 64 elements each. Pair sums inside each set, including a+a, must be unique. Their nonzero difference sets must be disjoint. Maximize |A|+|B|; A and B need not themselves be disjoint. Two Sidon subsets of [1,256]; maximize combined size and require disjoint nonzero differences. Ordinary Sidon diagonals are included, and the two sets themselves may overlap.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [A,B], two nonempty Sidon subsets of [1,n=256], at most 64 elements each. Pair sums inside each set, including a+a, must be unique. Their nonzero difference sets must be disjoint. Maximize |A|+|B|; A and B need not themselves be disjoint.

## State of the art

No documented maximum of |A| + |B| for N = 256. Erdős's question (Problem #43) was answered negatively: one Sidon set can have the maximum size while the other grows without bound.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #43](https://www.erdosproblems.com/43), status: disproved (Lean).

- [Some problems on additive number theory](https://users.renyi.hu/~p_erdos/1982-34.pdf), Paul Erdős (1982)

Parameters: `{"n": 256}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Maximize combined cardinality of two Sidon sets whose nonzero differences are disjoint.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.


The exact problem statement is verified in a problem survey, but no paper primarily advancing this paired-set question was established.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://users.renyi.hu/~p_erdos/1982-34.pdf (Paul Erdős, Some problems on additive number theory. Annals of Discrete Mathematics 12 (1982), 113–116; p.114 explicitly poses the two-Sidon-set/disjoint-differences question.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000071 (JSP-000071; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Two Sidon subsets of [1,256]; maximize combined size and require disjoint nonzero differences. Ordinary Sidon diagonals are included, and the two sets themselves may overlap.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
