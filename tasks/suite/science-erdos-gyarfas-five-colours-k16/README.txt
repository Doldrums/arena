# Edge-colourings of K16 in which every K4 sees five colours

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-erdos-gyarfas-five-colours-k16`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> 120 integer colours in 0..119 for the pairs (i,j), 0<=i<j<16, in lexicographic order. Every set of four vertices must span edges of at least five distinct colours. Minimize the number of colours used. A valid colouring certifies f(16) <= colours used. The general bounds give 13 <= f(16) <= 15; no exact value for n = 16 is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 120 integer colours in 0..119 for the pairs (i,j), 0<=i<j<16, in lexicographic order. Every set of four vertices must span edges of at least five distinct colours. Minimize the number of colours used.

## State of the art

No documented value for n = 16. General bounds: 5(n-1)/6 < f(n) < n (Erdős and Gyárfás 1997), so 13 <= f(16) <= 15; asymptotically f(n) ~ 5n/6 (Bennett, Cushman, Dudek and Prałat).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #136](https://www.erdosproblems.com/136), status: solved (f(n) ~ 5n/6).

- [A variant of the classical Ramsey problem](https://doi.org/10.1007/bf01195000), Paul Erdős, András Gyárfás (1997)
- [Erdős Problem #136](https://www.erdosproblems.com/136)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the least number of colours f(n) such that every K4 receives at least five colours.

Why it matters: This is the Erdős-Gyárfás generalized Ramsey function f(n,4,5) (Erdős Problem #136); its asymptotics were settled only in 2022.

- [A variant of the classical Ramsey problem](https://doi.org/10.1007/bf01195000): Main research objective: Determine the least number of colours f(n) such that every K4 receives at least five colours. Task connection: A valid colouring certifies f(16) <= colours used. The general bounds give 13 <= f(16) <= 15; no exact value for n = 16 is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid colouring certifies f(16) <= colours used. The general bounds give 13 <= f(16) <= 15; no exact value for n = 16 is documented. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/bf01195000 (Paul Erdős and András Gyárfás, A variant of the classical Ramsey problem (1997). Crossref record inspected; Erdős Problem #136 page inspected: Erdős and Gyárfás proved 5(n-1)/6 < f(n) < n and f(9) = 8; Bennett, Cushman, Dudek and Prałat proved f(n) ~ 5n/6. A valid colouring certifies f(16) <= colours used. The general bounds give 13 <= f(16) <= 15; no exact value for n = 16 is documented.)
- archive: https://www.erdosproblems.com/136 (Erdős Problem #136 (solved (f(n) ~ 5n/6)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000140 (JSP-000140; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No published value for n = 16 was found (reference label none); improvements are comparable across runs and with the bounds 13 <= f(16) <= 15, not with a recorded optimum.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
