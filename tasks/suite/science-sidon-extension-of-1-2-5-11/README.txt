# Extending the Sidon set {1, 2, 5, 11} inside [1, 284]

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-sidon-extension-of-1-2-5-11`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct integers in 1..284 containing 1, 2, 5 and 11 whose pairwise sums a + b (a <= b) are all distinct. Maximize the size; without the prescribed elements the maximum in [1, 284] is 20 (the optimal 20-mark Golomb ruler has length 283). Scores near 20 would show that the prescribed elements barely reduce the attainable size at this scale; no value for this seed is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 1..284 containing 1, 2, 5 and 11 whose pairwise sums a + b (a <= b) are all distinct. Maximize the size; without the prescribed elements the maximum in [1, 284] is 20 (the optimal 20-mark Golomb ruler has length 283).

## State of the art

No documented maximum with the prescribed elements; without them the maximum in [1, 284] is 20 (OEIS A003022).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #44](https://www.erdosproblems.com/44), status: open.

- [A Complete Annotated Bibliography of Work Related to Sidon Sequences](https://doi.org/10.37236/32), Kevin O'Bryant (2004)
- [OEIS A003022: Length of shortest (optimal) Golomb ruler with n marks](https://oeis.org/A003022)

Parameters: `{"n": 284, "seed": [1, 2, 5, 11]}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decide whether every finite Sidon set extends to a nearly optimal Sidon set (Erdős Problem #44).

Why it matters: Sidon sets are central to additive combinatorics; the extension question underlies the conjectured maximal density N^(1/2).

- [A Complete Annotated Bibliography of Work Related to Sidon Sequences](https://doi.org/10.37236/32): Main research objective: Decide whether every finite Sidon set extends to a nearly optimal Sidon set (Erdős Problem #44). Task connection: Scores near 20 would show that the prescribed elements barely reduce the attainable size at this scale; no value for this seed is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Scores near 20 would show that the prescribed elements barely reduce the attainable size at this scale; no value for this seed is documented. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.37236/32 (Kevin O'Bryant, A Complete Annotated Bibliography of Work Related to Sidon Sequences (2004). Crossref record inspected; Erdős Problem #44 page inspected (can every finite Sidon set be extended to a Sidon set of size (1-eps)M^(1/2) in [1, M]? A positive answer to #707 implies it, and it implies #329; Guy C9). OEIS A003022 inspected: the shortest 20-mark Golomb ruler has length 283. Scores near 20 would show that the prescribed elements barely reduce the attainable size at this scale; no value for this seed is documented.)
- archive: https://www.erdosproblems.com/44 (Erdős Problem #44 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000072 (JSP-000072; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for the seeded instance (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
