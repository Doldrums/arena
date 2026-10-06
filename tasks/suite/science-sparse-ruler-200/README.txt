# Sparse ruler of length 200 with the fewest marks

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-sparse-ruler-200`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> distinct integer marks in 0..200 such that every distance 1..200 is a difference of two marks. Minimize the number of marks; the optimum is 25. For N = 200 the minimum is 25, so the task recovers an optimal ruler.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integer marks in 0..200 such that every distance 1..200 is a difference of two marks. Minimize the number of marks; the optimum is 25.

## State of the art

A sparse ruler of length 200 needs 25 marks (OEIS A046693).

Reference value: proven optimum `25` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #170](https://www.erdosproblems.com/170), status: open.

- [OEIS A046693: Minimal number of marks of a sparse ruler of length n](https://oeis.org/A046693)
- [On the Representation of 1, 2, …, n by Differences](https://doi.org/10.1112/jlms/s1-31.2.160), John Leech (1956)

Parameters: `{"n": 200}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the minimal number of marks of a sparse ruler of length N and the limit of F(N)/N^(1/2) (Erdős Problem #170).

Why it matters: Sparse rulers are extremal difference bases with applications to minimum-redundancy antenna arrays; the limiting constant is open.

- [On the Representation of 1, 2, …, n by Differences](https://doi.org/10.1112/jlms/s1-31.2.160): Main research objective: Determine the minimal number of marks of a sparse ruler of length N and the limit of F(N)/N^(1/2) (Erdős Problem #170). Task connection: For N = 200 the minimum is 25, so the task recovers an optimal ruler.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For N = 200 the minimum is 25, so the task recovers an optimal ruler. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1112/jlms/s1-31.2.160 (John Leech, On the Representation of 1, 2, …, n by Differences (1956). Crossref record inspected; Erdős Problem #170 page inspected (Erdős and Gál proved that lim F(N)/N^(1/2) exists; it lies in [1.56, sqrt 3] by Leech and Wichmann). OEIS A046693 inspected (b-file by Pegg for lengths 0..213): the minimal number of marks for length 200 is 25. For N = 200 the minimum is 25, so the task recovers an optimal ruler.)
- archive: https://www.erdosproblems.com/170 (Erdős Problem #170 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000167 (JSP-000167; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
