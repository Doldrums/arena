# Large gaps between sums of two squares

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-consecutive-two-square-gap`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> [a,b], positive endpoints a<b<=maximum=10000000, b-a<=10000, both sums of two integer squares (zero is permitted). No interior integer may be a sum of two squares. Maximize b-a. Positive consecutive representable endpoints at most 10000000 and distance at most 10000, with zero allowed as one of the two squared integers. Every interior integer is checked. The optimum is 50 (9565544 to 9565594; OEIS A297350); this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [a,b], positive endpoints a<b<=maximum=10000000, b-a<=10000, both sums of two integer squares (zero is permitted). No interior integer may be a sum of two squares. Maximize b-a.

## State of the art

The largest gap between consecutive sums of two squares up to 10^7 is 50, from 9565544 to 9565594. The next record gap starts at 13305524 (OEIS A297350), and a sieve up to 10^7 recomputes the value.

Reference value: proven optimum `50` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #222](https://www.erdosproblems.com/222), status: open.

- [OEIS A297350: Start of record gaps between sums of two squares](https://oeis.org/A297350)
- [Large gaps between sums of two squares](https://arxiv.org/abs/1906.09100), A. B. Kalmynin, S. V. Konyagin (2019)

Parameters: `{"maximum": 10000000, "maximum_gap": 10000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find lower bounds for gaps in integers representable as sums of two squares.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Large gaps between sums of two squares](https://arxiv.org/abs/1906.09100): Main research objective: Find lower bounds for gaps in integers representable as sums of two squares. Task connection: Positive consecutive representable endpoints at most 10000000 and distance at most 10000, with zero allowed as one of the two squared integers. Every interior integer is checked.

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

- paper: https://arxiv.org/abs/1906.09100 (A. B. Kalmynin and S. V. Konyagin, Large gaps between sums of two squares. Author abstract inspected: g(X) is the largest difference between consecutive sums of two squares up to X. This is a preprint; v2 notes a later expanded joint manuscript.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0201-0300.md#JSP-000201 (JSP-000201; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Solved finite case: The largest gap between consecutive sums of two squares up to 10^7 is 50, from 9565544 to 9565594.
- Positive consecutive representable endpoints at most 10000000 and distance at most 10000, with zero allowed as one of the two squared integers. Every interior integer is checked.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
