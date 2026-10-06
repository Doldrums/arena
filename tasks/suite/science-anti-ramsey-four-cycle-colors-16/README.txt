# Many edge colors without a rainbow four-cycle

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-anti-ramsey-four-cycle-colors-16`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 120 integer colors in 0..119 for the lexicographically ordered pairs (i,j), 0<=i<j<16. No four-cycle may have four distinct edge colors. Maximize the number of colors actually used; all three cycles on every four-vertex subset are checked. The n=16, cycle-length-four task searches extremal colorings for a solved finite specialization, using an independently written exhaustive verifier.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 120 integer colors in 0..119 for the lexicographically ordered pairs (i,j), 0<=i<j<16. No four-cycle may have four distinct edge colors. Maximize the number of colors actually used; all three cycles on every four-vertex subset are checked.

## State of the art

Alon proved that the maximum number of colours on K_n without a rainbow C_4 is floor(4n/3) - 1, which is 20 for n = 16. Montellano-Ballesteros and Neumann-Lara extended the exact result to all cycles. The formula was rechecked exhaustively for n <= 6 (scripts/check_state_of_the_art.py).

Reference value: proven optimum `20` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1105](https://www.erdosproblems.com/1105), status: proved.

- [On a conjecture of Erdős, Simonovits, and Sós concerning anti-Ramsey theorems](https://doi.org/10.1002/jgt.3190070112), Noga Alon (1983)
- [An Anti-Ramsey Theorem on Cycles](https://doi.org/10.1007/s00373-005-0619-y), J. J. Montellano-Ballesteros, V. Neumann-Lara (2005)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the edge-color threshold that forces a rainbow cycle of a prescribed length.

Why it matters: The local color-count objective directly instantiates the anti-Ramsey invariant solved in the cited paper.

- [An Anti-Ramsey Theorem on Cycles](https://doi.org/10.1007/s00373-005-0619-y): Main research objective: Determine the edge-color threshold that forces a rainbow cycle of a prescribed length. Task connection: The n=16, cycle-length-four task searches extremal colorings for a solved finite specialization, using an independently written exhaustive verifier.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The n=16, cycle-length-four task searches extremal colorings for a solved finite specialization, using an independently written exhaustive verifier. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/s00373-005-0619-y (Juan José Montellano-Ballesteros and Victor Neumann-Lara, An Anti-Ramsey Theorem on Cycles (2005). Authors' institutional publication abstract inspected. It defines the number of colors forcing a rainbow cycle and reports its determination for all n>=p>=3. The n=16, cycle-length-four task searches extremal colorings for a solved finite specialization, using an independently written exhaustive verifier.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000916 (JSP-000916; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- This is mathematical rediscovery, not an unsolved-conjecture task. No published coloring implementation or construction is imported.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
