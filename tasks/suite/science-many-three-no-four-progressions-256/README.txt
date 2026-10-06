# Many three-term progressions without four-term progressions

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-many-three-no-four-progressions-256`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty subset of [1,n=256], with no nonconstant four-term arithmetic progression. Maximize the number of distinct three-term arithmetic progressions (positive difference, counted once). Cardinality and ambient interval are both reported; finite-box restriction of the source extremal problem. Choose a subset of [1,256] with no four-term progression and maximize the number of three-term progressions. Unlike the paper, ambient height is fixed and cardinality varies; each result bounds f_{3,4}(|A|) from below.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty subset of [1,n=256], with no nonconstant four-term arithmetic progression. Maximize the number of distinct three-term arithmetic progressions (positive difference, counted once). Cardinality and ambient interval are both reported; finite-box restriction of the source extremal problem.

## State of the art

No documented maximum for subsets of [1,256]. Fox and Pohoata showed that sets without k-term progressions can contain N^(2-o(1)) shorter progressions, which answers Erdős Problem #179.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #179](https://www.erdosproblems.com/179), status: proved.

- [Sets without k-term progressions can have many shorter progressions](https://arxiv.org/abs/1908.09905), Jacob Fox, Cosmin Pohoata (2020)

Parameters: `{"n": 256}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Maximize the number of short progressions compatible with avoiding a longer progression.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Sets without k-term progressions can have many shorter progressions](https://arxiv.org/abs/1908.09905): Main research objective: Maximize the number of short progressions compatible with avoiding a longer progression. Task connection: Choose a subset of [1,256] with no four-term progression and maximize the number of three-term progressions. Unlike the paper, ambient height is fixed and cardinality varies; each result bounds f_{3,4}(|A|) from below.

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

- paper: https://arxiv.org/abs/1908.09905 (Jacob Fox and Cosmin Pohoata, Sets without k-term progressions can have many shorter progressions. Author abstract inspected; f_{s,k}(n) counts shorter progressions in n-element sets avoiding longer ones.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000173 (JSP-000173; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Choose a subset of [1,256] with no four-term progression and maximize the number of three-term progressions. Unlike the paper, ambient height is fixed and cardinality varies; each result bounds f_{3,4}(|A|) from below.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
