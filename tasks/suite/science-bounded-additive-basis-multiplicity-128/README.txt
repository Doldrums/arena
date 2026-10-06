# Additive bases with few representations

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-bounded-additive-basis-multiplicity-128`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> a nonempty subset A of [0,n=128]. Every integer in [128,256] must be a sum of two elements of A. Pair representations are unordered and permit equal summands. Minimize the largest representation multiplicity in that target interval. Choose A in [0,128] covering [128,256] by pair sums and minimize peak multiplicity. Local pairs are unordered and include equal summands; the paper’s ordered convention differs by symmetry.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty subset A of [0,n=128]. Every integer in [128,256] must be a sum of two elements of A. Pair representations are unordered and permit equal summands. Minimize the largest representation multiplicity in that target interval.

## State of the art

No documented minimum for this finite window. The Erdős-Turán conjecture that the representation function of an additive basis of order 2 is unbounded is Erdős Problem #28.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #28](https://www.erdosproblems.com/28), status: open ($500).

- [A note on a conjecture of Erdős-Turán](https://math.bme.hu/~csandor/Publications/ErdosTuran.pdf), Csaba Sándor

Parameters: `{"n": 128}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand growth of representation multiplicities in additive bases of order two.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [A note on a conjecture of Erdős–Turán](https://math.bme.hu/~csandor/Publications/ErdosTuran.pdf): Main research objective: Understand growth of representation multiplicities in additive bases of order two. Task connection: Choose A in [0,128] covering [128,256] by pair sums and minimize peak multiplicity. Local pairs are unordered and include equal summands; the paper’s ordered convention differs by symmetry.

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

- paper: https://math.bme.hu/~csandor/Publications/ErdosTuran.pdf (Csaba Sándor, A note on a conjecture of Erdős–Turán. Author-hosted full text, introduction and representation-function definition inspected.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000061 (JSP-000061; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Choose A in [0,128] covering [128,256] by pair sums and minimize peak multiplicity. Local pairs are unordered and include equal summands; the paper’s ordered convention differs by symmetry.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
