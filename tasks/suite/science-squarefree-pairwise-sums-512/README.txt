# Large subsets of {1, ..., 512} whose pairwise sums are all squarefree

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-squarefree-pairwise-sums-512`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct integers in 1..512 such that every sum a + b with a <= b (including 2a) is squarefree. Maximize the size; the optimum is 24. For N = 512 the maximum is 24, so the task recovers an extremal set. The bank entry is the infinite question (#1103); this is its finite analogue (#1109).

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 1..512 such that every sum a + b with a <= b (including 2a) is squarefree. Maximize the size; the optimum is 24.

## State of the art

The largest subset of {1..512} with all pairwise sums squarefree has 24 elements (OEIS A392164).

Reference value: proven optimum `24` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1103](https://www.erdosproblems.com/1103), status: open.

- [OEIS A392164: Size of the largest subset S of {1..N} such that every element of S+S is squarefree](https://oeis.org/A392164)
- [Problems on the set of squarefree numbers](https://doi.org/10.4213/im486), Sergei V. Konyagin (2004)
- [Erdős Problem #1109 (finite version)](https://www.erdosproblems.com/1109)

Parameters: `{"n": 512}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how large a set can be when all pairwise sums are squarefree, and how fast an infinite such sequence must grow.

Why it matters: Squarefree sumsets test the interaction of additive structure with multiplicative sieves; the gap between polylogarithmic and power bounds is open.

- [Problems on the set of squarefree numbers](https://doi.org/10.4213/im486): Main research objective: Determine how large a set can be when all pairwise sums are squarefree, and how fast an infinite such sequence must grow. Task connection: For N = 512 the maximum is 24, so the task recovers an extremal set. The bank entry is the infinite question (#1103); this is its finite analogue (#1109).

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For N = 512 the maximum is 24, so the task recovers an extremal set. The bank entry is the infinite question (#1103); this is its finite analogue (#1109). Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4213/im486 (Sergei V. Konyagin, Problems on the set of squarefree numbers (2004). Crossref record inspected; Erdős Problems #1103 (infinite sequences) and #1109 (the finite version) inspected: Erdős and Sárközy proved log N << f(N) << N^(3/4) log N and Konyagin improved this to (log log N)(log N)^2 << f(N) << N^(11/15+o(1)); van Doorn and Tao bounded the growth of infinite sequences. OEIS A392164 inspected (exact branch and bound by Carney): f(512) = 24. For N = 512 the maximum is 24, so the task recovers an extremal set. The bank entry is the infinite question (#1103); this is its finite analogue (#1109).)
- archive: https://www.erdosproblems.com/1103 (Erdős Problem #1103 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000915 (JSP-000915; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table (finite analogue of the bank's infinite question).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
