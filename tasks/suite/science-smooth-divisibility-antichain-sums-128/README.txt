# Divisibility-antichain representations by smooth numbers

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-smooth-divisibility-antichain-sums-128`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> 128 rows corresponding to targets 1..128. Every row must contain 1..30 distinct positive 2^a*3^b*5^c terms summing to its target; no chosen term may divide another. All targets require valid representations. Minimize the total number of summands over all targets, an explicit local refinement of finite d-completeness. Represent targets 1..128 by sums of distinct 2,3,5-smooth numbers forming a divisibility antichain. All targets require valid representations; minimizing the total term count is an explicit local efficiency refinement of finite d-completeness. The seed uses up to three terms and is not term-minimal.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 128 rows corresponding to targets 1..128. Every row must contain 1..30 distinct positive 2^a*3^b*5^c terms summing to its target; no chosen term may divide another. All targets require valid representations. Minimize the total number of summands over all targets, an explicit local refinement of finite d-completeness.

## State of the art

The minimum total is 220. Every target up to 128 needs at most three pairwise non-dividing 5-smooth summands, and an exhaustive search for each target (scripts/check_state_of_the_art.py) gives per-target minima that sum to 220. The d-completeness of such sequences was conjectured by Erdős and Lewin (Erdős Problem #123, now proved).

Reference value: proven optimum `220` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #123](https://www.erdosproblems.com/123), status: proved (Lean).

- [On d-complete sequences of integers](https://doi.org/10.1016/j.jnt.2015.12.003), Mi-Mi Ma, Yong-Gao Chen (2016)

Parameters: `{"maximum_terms": 30}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Study sequences that represent integers using sums whose summands do not divide one another.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.


The primary abstract confirms d-completeness but the precise 2,3,5 base restriction was not verified there. The local finite variant is independently checked; no importance claim is inferred from the broader definition.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://www.sciencedirect.com/science/article/pii/S0022314X16000342 (Mi-Mi Ma and Yong-Gao Chen, On d-complete sequences of integers. Publisher abstract inspected: divisibility-antichain sums and d-completeness. Journal of Number Theory 164 (2016), 1–12, DOI 10.1016/j.jnt.2015.12.003. Original d-complete terminology credited to Erdős and Mordechai Lewin, Mathematics of Computation 65 (1996), 837–840.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000130 (JSP-000130; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Represent targets 1..128 by sums of distinct 2,3,5-smooth numbers forming a divisibility antichain. All targets require valid representations; minimizing the total term count is an explicit local efficiency refinement of finite d-completeness. The seed uses up to three terms and is not term-minimal.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
