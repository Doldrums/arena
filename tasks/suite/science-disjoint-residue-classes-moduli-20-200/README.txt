# Pairwise disjoint residue classes with distinct moduli in [20, 200] (largest reciprocal sum)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-disjoint-residue-classes-moduli-20-200`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> classes [[m, r], ...] with distinct moduli 20 <= m <= 200 and 0 <= r < m, pairwise disjoint (r_1 != r_2 modulo gcd(m_1, m_2)). The score is the sum of 1/m (exact rational, reported as a float). Maximize. With moduli restricted to [20, 200] every valid construction bounds epsilon_19 from below.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> classes [[m, r], ...] with distinct moduli 20 <= m <= 200 and 0 <= r < m, pairwise disjoint (r_1 != r_2 modulo gcd(m_1, m_2)). The score is the sum of 1/m (exact rational, reported as a float). Maximize.

## State of the art

No documented finite values; asymptotically epsilon_m = L(m)^(-1+o(1)).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1190](https://www.erdosproblems.com/1190), status: solved (Lean).

- [On non-intersecting arithmetic progressions](https://doi.org/10.4064/aa157-4-5), Régis de la Bretèche, Kevin Ford, Joseph Vandehey (2013)
- [Erdős Problem #1190](https://www.erdosproblems.com/1190)

Parameters: `{"low": 20, "high": 200}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate epsilon_m, the largest reciprocal sum of distinct moduli above m carrying pairwise disjoint residue classes (Erdős Problem #1190).

Why it matters: Disjoint arithmetic progressions are dual to covering systems and connect to Erdős's questions on exact covers.

- [On non-intersecting arithmetic progressions](https://doi.org/10.4064/aa157-4-5): Main research objective: Estimate epsilon_m, the largest reciprocal sum of distinct moduli above m carrying pairwise disjoint residue classes (Erdős Problem #1190). Task connection: With moduli restricted to [20, 200] every valid construction bounds epsilon_19 from below.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- With moduli restricted to [20, 200] every valid construction bounds epsilon_19 from below. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4064/aa157-4-5 (Régis de la Bretèche, Kevin Ford and Joseph Vandehey, On non-intersecting arithmetic progressions (2013). Crossref record inspected; Erdős Problem #1190 page inspected: epsilon_m, the largest sum 1/n_i over pairwise disjoint classes with moduli m < n_1 < ..., satisfies L(m)^(-1+o(1)) < epsilon_m < L(m)^(-sqrt(3)/2+o(1)) with L(m) = exp(sqrt(log m log log m)) (de la Bretèche, Ford and Vandehey), sharpened to epsilon_m = L(m)^(-1+o(1)) through the resolution of #202. No finite values are documented. With moduli restricted to [20, 200] every valid construction bounds epsilon_19 from below.)
- archive: https://www.erdosproblems.com/1190 (Erdős Problem #1190 (solved (Lean)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000995 (JSP-000995; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none); the cap at 200 makes the score a lower bound for epsilon_19.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
