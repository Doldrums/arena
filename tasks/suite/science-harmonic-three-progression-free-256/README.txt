# Reciprocal weight of three-progression-free sets

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-harmonic-three-progression-free-256`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty subset of [1,n=256] without any nonconstant k=3 term arithmetic progression. Maximize the exact sum of reciprocals; score is its floating serialization with exact numerator/denominator in details. A bounded subset of [1,256] without three-term progressions, scored by reciprocal weight. It does not settle the general all-length divergent-reciprocal-sum question.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty subset of [1,n=256] without any nonconstant k=3 term arithmetic progression. Maximize the exact sum of reciprocals; score is its floating serialization with exact numerator/denominator in details.

## State of the art

No documented maximum of the reciprocal sum for subsets of [1,256] without three-term progressions. Bloom and Sisask proved that sets whose reciprocal sums diverge contain three-term progressions; the question for progressions of every length is Erdős Problem #3.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #3](https://www.erdosproblems.com/3), status: open ($5000).

- [Breaking the logarithmic barrier in Roth's theorem on arithmetic progressions](https://arxiv.org/abs/2007.03528), Thomas F. Bloom, Olof Sisask (2020)

Parameters: `{"n": 256, "k": 3}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound the size and harmonic weight of integer sets avoiding three-term arithmetic progressions.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Breaking the logarithmic barrier in Roth’s theorem on arithmetic progressions](https://arxiv.org/abs/2007.03528): Main research objective: Bound the size and harmonic weight of integer sets avoiding three-term arithmetic progressions. Task connection: A bounded subset of [1,256] without three-term progressions, scored by reciprocal weight. It does not settle the general all-length divergent-reciprocal-sum question.

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

- paper: https://arxiv.org/abs/2007.03528 (Thomas F. Bloom and Olof Sisask, Breaking the logarithmic barrier in Roth’s theorem on arithmetic progressions. Author abstract and introduction inspected; the paper proves a density bound strong enough for the three-term reciprocal-sum consequence.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000044 (JSP-000044; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- A bounded subset of [1,256] without three-term progressions, scored by reciprocal weight. It does not settle the general all-length divergent-reciprocal-sum question.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
