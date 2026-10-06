# Large sets avoiding x, 2x, 3x

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-multiplicative-triple-free-4096`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty subset of [1,n=4096] containing no triple {x,2x,3x}. Maximize cardinality; density is recorded as an exact fraction. Maximize the size of a subset of [1,4096] avoiding {x,2x,3x}. This yields a finite construction, not the exact limiting density or its irrationality. The optimum is 3281, computed exactly on the independent 3-smooth grids (OEIS A157282); this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty subset of [1,n=4096] containing no triple {x,2x,3x}. Maximize cardinality; density is recorded as an exact fraction.

## State of the art

The maximum is 3281 (density 3281/4096). The problem splits into independent grids {2^a 3^b m : gcd(m,6) = 1} (the decomposition behind OEIS A157282). An exact dynamic programme over every grid (scripts/check_state_of_the_art.py) gives 3281. The limiting density is Erdős Problem #168.

Reference value: proven optimum `3281` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #168](https://www.erdosproblems.com/168), status: open.

- [OEIS A157282: Maximum cardinality of a weakly triple-free subset of {1..n}](https://oeis.org/A157282)
- [On Extremal Density Theorems for Linear Forms](https://fanchung.ucsd.edu/ron/papers/77_05_extremal_density.pdf), Ronald L. Graham, Hans S. Witsenhausen, Joel H. Spencer (1977)

Parameters: `{"n": 4096}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal densities of sets avoiding fixed multiplicative patterns.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [On Extremal Density Theorems for Linear Forms](https://fanchung.ucsd.edu/ron/papers/77_05_extremal_density.pdf): Main research objective: Determine extremal densities of sets avoiding fixed multiplicative patterns. Task connection: Maximize the size of a subset of [1,4096] avoiding {x,2x,3x}. This yields a finite construction, not the exact limiting density or its irrationality.

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

- paper: https://fanchung.ucsd.edu/ron/papers/77_05_extremal_density.pdf (Ronald L. Graham, Hans S. Witsenhausen and Joel H. Spencer, On Extremal Density Theorems for Linear Forms. Author-hosted full text visually inspected: Number Theory and Algebra (1977), 103–109; pp.107–108 explicitly analyze the pattern {x,2x,3x} and maximal subsets.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000165 (JSP-000165; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Solved finite case: The maximum is 3281 (density 3281/4096).
- Maximize the size of a subset of [1,4096] avoiding {x,2x,3x}. This yields a finite construction, not the exact limiting density or its irrationality.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
