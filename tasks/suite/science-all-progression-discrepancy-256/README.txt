# Low discrepancy on all arithmetic progressions

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-all-progression-discrepancy-256`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> exactly n=256 Python integer signs -1 or +1. Minimize the maximum absolute signed sum on ANY arithmetic progression contained in [1,256], any start, positive step and length including one. Assign 256 signs and minimize the maximum absolute sum on any arithmetic progression, including arbitrary starts and singletons. This differs from homogeneous-progression Erdős discrepancy.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly n=256 Python integer signs -1 or +1. Minimize the maximum absolute signed sum on ANY arithmetic progression contained in [1,256], any start, positive step and length including one.

## State of the art

No documented minimum for N = 256. The discrepancy of arithmetic progressions in [1,N] has order N^(1/4): Roth proved the lower bound and Matoušek and Spencer the matching upper bound.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Discrepancy in Arithmetic Progressions](https://cs.nyu.edu/~spencer/papers/matousek.pdf), Jiří Matoušek, Joel Spencer (1996)

Parameters: `{"n": 256}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound the discrepancy of the set system of arithmetic progressions.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Discrepancy in Arithmetic Progressions](https://cs.nyu.edu/~spencer/papers/matousek.pdf): Main research objective: Bound the discrepancy of the set system of arithmetic progressions. Task connection: Assign 256 signs and minimize the maximum absolute sum on any arithmetic progression, including arbitrary starts and singletons. This differs from homogeneous-progression Erdős discrepancy.

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

- paper: https://cs.nyu.edu/~spencer/papers/matousek.pdf (Jiří Matoušek and Joel Spencer, Discrepancy in Arithmetic Progressions. Author-hosted full text inspected, introduction and definition of discrepancy over every arithmetic progression in [1,n]. PDF pages are in reverse order.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000171 (JSP-000171; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Assign 256 signs and minimize the maximum absolute sum on any arithmetic progression, including arbitrary starts and singletons. This differs from homogeneous-progression Erdős discrepancy.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
