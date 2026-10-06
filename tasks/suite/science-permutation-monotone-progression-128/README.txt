# Permutations avoiding long monotone progressions

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-permutation-monotone-progression-128`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> a permutation of 1..n=128. Minimize the longest subsequence whose values form an increasing OR decreasing nonconstant arithmetic progression; subsequence positions need not be adjacent. A known finite construction attains 2, so this is a rediscovery task. Permute [1,128] and minimize the longest arithmetic-progression subsequence, allowing either sign of the common difference. The known finite optimum is 2; infinite-permutation questions are not recreated here.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a permutation of 1..n=128. Minimize the longest subsequence whose values form an increasing OR decreasing nonconstant arithmetic progression; subsequence positions need not be adjacent. A known finite construction attains 2, so this is a rediscovery task.

## State of the art

Davis, Entringer, Graham and Simmons showed that every interval [1,n] has a permutation without a monotone three-term progression (for example, evens before odds, recursively), so the minimum is 2.

Reference value: proven optimum `2` (reviewed 2026-09-24).

- [On permutations containing no long arithmetic progressions](https://fanchung.ucsd.edu/ron/papers/77_06_no_long_aps.pdf), James A. Davis, Roger C. Entringer, Ronald L. Graham, Gustavus J. Simmons (1977)

Parameters: `{"n": 128}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Analyze progression avoidance in finite and infinite permutations of integers.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [On permutations containing no long arithmetic progressions](https://fanchung.ucsd.edu/ron/papers/77_06_no_long_aps.pdf): Main research objective: Analyze progression avoidance in finite and infinite permutations of integers. Task connection: Permute [1,128] and minimize the longest arithmetic-progression subsequence, allowing either sign of the common difference. The known finite optimum is 2; infinite-permutation questions are not recreated here.

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

- paper: https://fanchung.ucsd.edu/ron/papers/77_06_no_long_aps.pdf (James A. Davis, Roger C. Entringer, Ronald L. Graham and Gustavus J. Simmons, On permutations containing no long arithmetic progressions. Acta Arithmetica XXXIV (1977), opening page visually inspected: finite permutations avoiding increasing and decreasing three-term progressions exist for every n, with the doubling construction proved explicitly.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000184 (JSP-000184; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Permute [1,128] and minimize the longest arithmetic-progression subsequence, allowing either sign of the common difference. The known finite optimum is 2; infinite-permutation questions are not recreated here.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
