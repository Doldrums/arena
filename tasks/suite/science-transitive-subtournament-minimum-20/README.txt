# Tournaments with small largest transitive subtournaments

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-transitive-subtournament-minimum-20`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> 190 integer bits, one for each pair (i,j), i<j, in lexicographic order on 20 vertices. Bit 0 orients i to j and bit 1 orients j to i. Minimize the exact largest transitive induced subtournament, computed by source-vertex subset recursion. The local n=20 task minimizes the largest transitive subset rather than reproducing the larger R(7) computation. This small order is labelled rediscovery, with no new-bound claim.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 190 integer bits, one for each pair (i,j), i<j, in lexicographic order on 20 vertices. Bit 0 orients i to j and bit 1 orients j to i. Minimize the exact largest transitive induced subtournament, computed by source-vertex subset recursion.

## State of the art

Every tournament on n vertices contains a transitive subtournament on floor(log2 n) + 1 vertices (Stearns), which is 5 for n = 20. The Paley tournament on 23 vertices restricted to 20 vertices has no transitive subtournament on 6 (scripts/check_state_of_the_art.py). The largest tournament without one has 27 vertices (Sanchez-Flores; confirmed by Neiman, Mackey and Heule). Erdős Problem #1216 was answered negatively by Reid and Parker.

Reference value: proven optimum `5` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1216](https://www.erdosproblems.com/1216), status: disproved.

- [The Voting Problem](https://doi.org/10.1080/00029890.1959.11989405), Richard Stearns (1959)
- [Tighter Bounds on Directed Ramsey Number R(7)](https://doi.org/10.1007/s00373-022-02560-5), David Neiman, John Mackey, Marijn Heule (2022)
- [Disproof of a conjecture of Erdős and Moser on tournaments](https://doi.org/10.1016/s0021-9800(70)80061-8), K. B. Reid, E. T. Parker (1970)

Parameters: `{"n": 20}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how large a tournament can be while avoiding a prescribed transitive subtournament.

Why it matters: The finite exact search studies directed Ramsey obstructions, the same substantive combinatorial problem as the cited research.

- [Tighter Bounds on Directed Ramsey Number R(7)](https://doi.org/10.1007/s00373-022-02560-5): Main research objective: Determine how large a tournament can be while avoiding a prescribed transitive subtournament. Task connection: The local n=20 task minimizes the largest transitive subset rather than reproducing the larger R(7) computation. This small order is labelled rediscovery, with no new-bound claim.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The local n=20 task minimizes the largest transitive subset rather than reproducing the larger R(7) computation. This small order is labelled rediscovery, with no new-bound claim. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/s00373-022-02560-5 (David Neiman, John Mackey, and Marijn Heule, Tighter Bounds on Directed Ramsey Number R(7) (2022). Publisher abstract inspected. It defines directed Ramsey numbers and describes exact computer-assisted work on tournaments avoiding transitive subtournaments. The local n=20 task minimizes the largest transitive subset rather than reproducing the larger R(7) computation. This small order is labelled rediscovery, with no new-bound claim.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-1001-1022.md#JSP-001021 (JSP-001021; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- The 20-vertex case is a bounded rediscovery task, not a new solution to the all-order problem or the paper's R(7) result. No SAT solver, published tournament, or upstream implementation is copied.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
