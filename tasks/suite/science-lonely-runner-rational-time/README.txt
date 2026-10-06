# Rational-time lonely-runner certificates

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-lonely-runner-rational-time`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> [p,q] of Python integers with 0<p<q<=1000000, representing time p/q. For relative speeds [1,3,4,7,11,18,29] from a stationary runner, maximize the minimum circular distance of (p/q)*v to an integer. Exact rational distances are retained in details; score is their floating serialization. One stationary runner and seven fixed relative integer speeds [1,3,4,7,11,18,29]; maximize the minimum distance at a rational time with denominator<=10^6. This lower-bound certificate does not optimize over all speed sets or prove a universal conjecture. The optimum is exactly 1/5, at t = 1/5; every breakpoint of the piecewise-linear objective has been checked, so this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [p,q] of Python integers with 0<p<q<=1000000, representing time p/q. For relative speeds [1,3,4,7,11,18,29] from a stationary runner, maximize the minimum circular distance of (p/q)*v to an integer. Exact rational distances are retained in details; score is their floating serialization.

## State of the art

For the speeds {1,3,4,7,11,18,29} the maximum over all times of the minimum distance is exactly 1/5, attained at t = 1/5 (no speed is a multiple of 5). The objective is piecewise linear with breakpoints at denominators dividing v_i + v_j or 2v_i. Checking every denominator up to 116 (scripts/check_state_of_the_art.py) therefore proves optimality. The lonely runner conjecture predicts only 1/8 for seven speeds.

Reference value: proven optimum `0.2` (reviewed 2026-09-24).

- [Barely lonely runners and very lonely runners](https://arxiv.org/abs/1912.06034), Noah Kravitz (2021)

Parameters: `{"maximum_denominator": 1000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand maximum simultaneous circular separation for integer speed sets.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Barely lonely runners and very lonely runners](https://arxiv.org/abs/1912.06034): Main research objective: Understand maximum simultaneous circular separation for integer speed sets. Task connection: One stationary runner and seven fixed relative integer speeds [1,3,4,7,11,18,29]; maximize the minimum distance at a rational time with denominator<=10^6. This lower-bound certificate does not optimize over all speed sets or prove a universal conjecture.

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

- paper: https://arxiv.org/abs/1912.06034 (Noah Kravitz, Barely lonely runners and very lonely runners. Author abstract inspected: maximum loneliness is max_t min_i distance(t*v_i,Z); paper studies the associated spectrum.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000017 (JSP-000017; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Solved finite case: For the speeds {1,3,4,7,11,18,29} the maximum over all times of the minimum distance is exactly 1/5, attained at t = 1/5 (no speed is a multiple of 5).
- One stationary runner and seven fixed relative integer speeds [1,3,4,7,11,18,29]; maximize the minimum distance at a rational time with denominator<=10^6. This lower-bound certificate does not optimize over all speed sets or prove a universal conjecture.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
