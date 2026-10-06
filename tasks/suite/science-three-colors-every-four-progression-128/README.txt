# Colorings with three colors in every four-term progression

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-three-colors-every-four-progression-128`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> n=128 integer color labels in 0..127. Every nonconstant four-term progression of positions must use AT LEAST three distinct colors. Minimize the number of labels actually used; labels need not be consecutive. Minimize colors on [1,128] with at least three colors on every four-term progression. The source’s largest forcing-color threshold is one below the least avoiding-color count; local score uses the latter convention.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> n=128 integer color labels in 0..127. Every nonconstant four-term progression of positions must use AT LEAST three distinct colors. Minimize the number of labels actually used; labels need not be consecutive.

## State of the art

No documented value of h(128), the least number of colours of [1,N] such that every four-term progression receives at least three colours (Erdős Problem #160).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #160](https://www.erdosproblems.com/160), status: open.

- [Some Problems and Results on Combinatorial Number Theory](https://users.renyi.hu/~p_erdos/1989-35.pdf), Paul Erdős (1989)

Parameters: `{"n": 128}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Understand thresholds for four-term progressions using at most two color classes.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.


The exact question is present in a problem survey. A primary problem-solving paper for this stronger every-progression constraint was not established; related ABBA-free-coloring papers are not treated as equivalent.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://users.renyi.hu/~p_erdos/1989-35.pdf (Paul Erdős, Some Problems and Results on Combinatorial Number Theory. Author-hosted 1989 paper, p.143, Freud–Erdős coloring question inspected.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000158 (JSP-000158; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Minimize colors on [1,128] with at least three colors on every four-term progression. The source’s largest forcing-color threshold is one below the least avoiding-color count; local score uses the latter convention.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
