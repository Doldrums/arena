# Many disjoint residue classes with distinct moduli

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-disjoint-congruence-classes-128`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty list of [residue,modulus] pairs with distinct moduli 2..maximum=128 and canonical residues 0<=r<m. Every two infinite residue classes must be disjoint; the verifier uses the exact gcd criterion. Maximize the number of classes. Choose pairwise disjoint infinite residue classes with distinct moduli between 2 and 128; maximize their number using the exact gcd/CRT criterion.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty list of [residue,modulus] pairs with distinct moduli 2..maximum=128 and canonical residues 0<=r<m. Every two infinite residue classes must be disjoint; the verifier uses the exact gcd criterion. Maximize the number of classes.

## State of the art

No documented value for moduli up to 128. Exact values are known for n <= 100 (OEIS A389975, a(100) = 20), so at least 20 classes are possible. The growth rate is Erdős Problem #202.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #202](https://www.erdosproblems.com/202), status: solved (Lean).

- [OEIS A389975: Maximum number of disjoint congruence classes with distinct moduli at most n](https://oeis.org/A389975)
- [On non-intersecting arithmetic progressions](https://arxiv.org/abs/math/0208236), Ernest S. Croot III (2003)

Parameters: `{"maximum": 128}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximum number of disjoint residue classes with distinct bounded moduli.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [On non-intersecting arithmetic progressions](https://arxiv.org/abs/math/0208236): Main research objective: Determine the maximum number of disjoint residue classes with distinct bounded moduli. Task connection: Choose pairwise disjoint infinite residue classes with distinct moduli between 2 and 128; maximize their number using the exact gcd/CRT criterion.

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

- paper: https://arxiv.org/abs/math/0208236 (Ernest S. Croot III, On non-intersecting arithmetic progressions. Author preprint and published first-page definition inspected; Acta Arithmetica 110.3 (2003), 233–238.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000189 (JSP-000189; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Choose pairwise disjoint infinite residue classes with distinct moduli between 2 and 128; maximize their number using the exact gcd/CRT criterion.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
