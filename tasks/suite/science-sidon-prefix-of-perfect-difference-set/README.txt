# Sidon sets containing 0 whose differences include 1, ..., 30 (prefixes of perfect difference sets)

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-sidon-prefix-of-perfect-difference-set`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> at most 32 distinct integers in 0..10^6 including 0, with all positive differences distinct (a Sidon set) and every d in 1..30 occurring as a difference. Minimize the largest element. A Sidon set realizing all differences 1..30 is a truncated perfect difference set; its least possible diameter measures the growth cost at this scale.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> at most 32 distinct integers in 0..10^6 including 0, with all positive differences distinct (a Sidon set) and every d in 1..30 occurring as a difference. Minimize the largest element.

## State of the art

No documented minimum for this truncation.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1194](https://www.erdosproblems.com/1194), status: open.

- [Perfect difference sets constructed from Sidon sets](https://doi.org/10.1007/s00493-008-2339-4), Javier Cilleruelo, Melvyn B. Nathanson (2008)
- [Erdős Problem #1194](https://www.erdosproblems.com/1194)

Parameters: `{"covered": 30, "bound": 1000000, "maximum_size": 32}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how fast a set in which every positive integer is uniquely a difference must grow (Erdős Problem #1194).

Why it matters: Perfect difference sets connect Sidon sets, Singer difference sets and additive bases.

- [Perfect difference sets constructed from Sidon sets](https://doi.org/10.1007/s00493-008-2339-4): Main research objective: Determine how fast a set in which every positive integer is uniquely a difference must grow (Erdős Problem #1194). Task connection: A Sidon set realizing all differences 1..30 is a truncated perfect difference set; its least possible diameter measures the growth cost at this scale.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A Sidon set realizing all differences 1..30 is a truncated perfect difference set; its least possible diameter measures the growth cost at this scale. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/s00493-008-2339-4 (Javier Cilleruelo and Melvyn B. Nathanson, Perfect difference sets constructed from Sidon sets (2008). Crossref record inspected; Erdős Problem #1194 page inspected (a perfect difference set is Sidon; the greedy construction gives a_n << n^3; Erdős noted limsup a_n/n = infinity; a_n >> n^(2-o(1)) infinitely often was shown recently). No finite values of this truncation are documented. A Sidon set realizing all differences 1..30 is a truncated perfect difference set; its least possible diameter measures the growth cost at this scale.)
- archive: https://www.erdosproblems.com/1194 (Erdős Problem #1194 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000999 (JSP-000999; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value (reference label none); differences above 30 need not all occur.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
