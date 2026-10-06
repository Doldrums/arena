# Large subsets of {1, ..., 134} with no subset sum a perfect square

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-no-square-subset-sums-134`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct integers in 1..134 such that no nonempty subset sums to a perfect square (exact subset-sum bitset). Maximize the size; the optimum is 13. For N = 134 the maximum is 13, so the task recovers an extremal set.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 1..134 such that no nonempty subset sums to a perfect square (exact subset-sum bitset). Maximize the size; the optimum is 13.

## State of the art

The largest subset of {1..134} without square subset sums has 13 elements (OEIS A372040: a(13) = 134).

Reference value: proven optimum `13` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #587](https://www.erdosproblems.com/587), status: solved (up to logarithmic factors).

- [OEIS A372040: Smallest k such that some n-element subset of {1..k} has no subset summing to a square](https://oeis.org/A372040)
- [Squares In Sumsets](https://doi.org/10.1007/978-3-642-14444-8_14), Hoi H. Nguyen, Van H. Vu (2010)

Parameters: `{"n": 134}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the largest subset of {1..N} none of whose nonempty subset sums is a square (Erdős Problem #587).

Why it matters: A model problem for squares in sumsets (asked by Erdős of a young Terence Tao), resolved up to logarithmic factors by Nguyen and Vu.

- [Squares In Sumsets](https://doi.org/10.1007/978-3-642-14444-8_14): Main research objective: Determine the largest subset of {1..N} none of whose nonempty subset sums is a square (Erdős Problem #587). Task connection: For N = 134 the maximum is 13, so the task recovers an extremal set.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For N = 134 the maximum is 13, so the task recovers an extremal set. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/978-3-642-14444-8_14 (Hoi H. Nguyen and Van H. Vu, Squares In Sumsets (2010). Crossref record inspected; Erdős Problem #587 page inspected (Erdős: |A| >> N^(1/3) from multiples of a prime; Nguyen and Vu: |A| << N^(1/3)(log N)^O(1)). OEIS A372040 inspected: the least k admitting a 13-element subset of {1..k} without square subset sums is 134. A 14-element example in {1..134} would leave a 13-element one inside {1..133}, so the maximum for N = 134 is 13. For N = 134 the maximum is 13, so the task recovers an extremal set.)
- archive: https://www.erdosproblems.com/587 (Erdős Problem #587 (solved (up to logarithmic factors)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000476 (JSP-000476; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
