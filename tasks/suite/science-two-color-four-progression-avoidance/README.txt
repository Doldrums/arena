# Long binary colorings without four-term progressions

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-two-color-four-progression-avoidance`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a list of integer colors 0 or 1, length between k=4 and maximum=512. No nonconstant four-term arithmetic progression of positions may be monochromatic. Maximize length. Maximize binary-coloring length up to 512 with no monochromatic four-term arithmetic progression. The paper determines the six-term case; this smaller four-term instance is a known finite rediscovery exercise.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a list of integer colors 0 or 1, length between k=4 and maximum=512. No nonconstant four-term arithmetic progression of positions may be monochromatic. Maximize length.

## State of the art

W(2,4) = 35 (Chvátal 1970; OEIS A005346), so the longest 2-colouring without a monochromatic four-term progression has length 34. An exhaustive search (scripts/check_state_of_the_art.py) reproduces both the length-34 colouring and the impossibility at 35.

Reference value: proven optimum `34` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #138](https://www.erdosproblems.com/138), status: open ($500).

- [OEIS A005346: Van der Waerden numbers W(2,n)](https://oeis.org/A005346)
- [The van der Waerden Number W(2,6) Is 1132](https://www.cs.umd.edu/users/gasarch/TOPICS/vdw/1132.pdf), Michal Kouril, Jerome L. Paul (2008)

Parameters: `{"k": 4, "maximum": 512}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the threshold at which two-colorings force monochromatic arithmetic progressions.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [The van der Waerden Number W(2,6) Is 1132](https://www.cs.umd.edu/users/gasarch/TOPICS/vdw/1132.pdf): Main research objective: Determine the threshold at which two-colorings force monochromatic arithmetic progressions. Task connection: Maximize binary-coloring length up to 512 with no monochromatic four-term arithmetic progression. The paper determines the six-term case; this smaller four-term instance is a known finite rediscovery exercise.

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

- paper: https://www.cs.umd.edu/users/gasarch/TOPICS/vdw/1132.pdf (Michal Kouril and Jerome L. Paul, The van der Waerden Number W(2,6) Is 1132. Primary paper PDF and initial definition of W(r,k) inspected. Experimental Mathematics (2008).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000142 (JSP-000142; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Maximize binary-coloring length up to 512 with no monochromatic four-term arithmetic progression. The paper determines the six-term case; this smaller four-term instance is a known finite rediscovery exercise.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
