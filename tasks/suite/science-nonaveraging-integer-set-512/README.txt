# Large sets without subset averages

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-nonaveraging-integer-set-512`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 1..maximum=48 distinct positive integers <=n=512. No element may be the exact arithmetic mean of any subset of at least two OTHER elements. The verifier checks every possible subset cardinality by integer bitsets. Maximize cardinality. At most 48 integers in [1,512], with no element the mean of any subset of at least two distinct OTHER elements. Exact subset-sum dynamic programming verifies all subset sizes.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 1..maximum=48 distinct positive integers <=n=512. No element may be the exact arithmetic mean of any subset of at least two OTHER elements. The verifier checks every possible subset cardinality by integer bitsets. Maximize cardinality.

## State of the art

No documented maximum for N = 512. The growth rate is N^(1/4+o(1)): Bosznay proved the lower bound and Pham and Zakharov the upper bound (Erdős Problem #186).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #186](https://www.erdosproblems.com/186), status: solved.

- [Sharp bound for the Erdős-Straus non-averaging set problem](https://arxiv.org/abs/2410.14624), Huy Tuan Pham, Dmitrii Zakharov (2024)

Parameters: `{"n": 512, "maximum": 48}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the largest sets with no element equal to the average of other elements.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Sharp bound for the Erdős–Straus non-averaging set problem](https://arxiv.org/abs/2410.14624): Main research objective: Determine the largest sets with no element equal to the average of other elements. Task connection: At most 48 integers in [1,512], with no element the mean of any subset of at least two distinct OTHER elements. Exact subset-sum dynamic programming verifies all subset sizes.

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

- paper: https://arxiv.org/abs/2410.14624 (Huy Tuan Pham and Dmitrii Zakharov, Sharp bound for the Erdős–Straus non-averaging set problem. Author abstract inspected (2024 preprint, 2025 revision): non-averaging definition and sharp asymptotic exponent.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000179 (JSP-000179; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- At most 48 integers in [1,512], with no element the mean of any subset of at least two distinct OTHER elements. Exact subset-sum dynamic programming verifies all subset sizes.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
