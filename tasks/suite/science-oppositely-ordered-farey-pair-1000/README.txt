# Nearby oppositely ordered fractions in the Farey sequence

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-oppositely-ordered-farey-pair-1000`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> [[a,b],[c,d]], two reduced fractions in [0,1] with denominators <=1000, a/b<c/d, and (c-a)*(d-b)<0. Minimize their rank difference in the complete Farey sequence of order 1000, including 0/1 and 1/1. Every rank is recomputed exactly. The local finite search gives an upper certificate for the first possible ordering failure at order 1000. It corrects the feasibility draft's unrelated strictly monotone-run objective. The optimum is 252, found by scanning the complete Farey sequence of order 1000; this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [[a,b],[c,d]], two reduced fractions in [0,1] with denominators <=1000, a/b<c/d, and (c-a)*(d-b)<0. Minimize their rank difference in the complete Farey sequence of order 1000, including 0/1 and 1/1. Every rank is recomputed exactly.

## State of the art

The smallest rank difference between two oppositely ordered fractions in the Farey sequence of order 1000 is 252, i.e. f(1000) = 251 in the notation of Erdős Problem #1005. This comes from a full scan (scripts/check_state_of_the_art.py); OEIS A386893 tabulates f(n) for n <= 100, and the same scan agrees with it. Van Doorn proved (1/12 - o(1))n <= f(n) <= n/4 + O(1).

Reference value: proven optimum `252` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1005](https://www.erdosproblems.com/1005), status: solved.

- [OEIS A386893: Minimal number of Farey fractions between two fractions that are not similarly ordered](https://oeis.org/A386893)
- [Improved bounds for the Mayer-Erdős phenomenon on similarly ordered Farey fractions](https://arxiv.org/abs/2509.00121), Wouter van Doorn (2025)

Parameters: `{"order": 1000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the smallest Farey-index separation at which numerator and denominator changes can have opposite signs.

Why it matters: The pairwise rank-separation threshold is exactly the phenomenon bounded in the source paper.

- [Improved bounds for the Mayer-Erdős phenomenon on similarly ordered Farey fractions](https://arxiv.org/abs/2509.00121): Main research objective: Determine the smallest Farey-index separation at which numerator and denominator changes can have opposite signs. Task connection: The local finite search gives an upper certificate for the first possible ordering failure at order 1000. It corrects the feasibility draft's unrelated strictly monotone-run objective.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The local finite search gives an upper certificate for the first possible ordering failure at order 1000. It corrects the feasibility draft's unrelated strictly monotone-run objective. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2509.00121 (Wouter van Doorn, Improved bounds for the Mayer-Erdős phenomenon on similarly ordered Farey fractions (2025). Author abstract inspected. Similar ordering is the pairwise nonnegative product condition; the paper also constructs close pairs where that product is negative. The local finite search gives an upper certificate for the first possible ordering failure at order 1000. It corrects the feasibility draft's unrelated strictly monotone-run objective.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000837 (JSP-000837; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- Solved finite case: The smallest rank difference between two oppositely ordered fractions in the Farey sequence of order 1000 is 252, i.e.
- The bank's unrelated 2026 pairwise-sums citation is not used. No optimality or general all-order bound follows from an accepted pair.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
