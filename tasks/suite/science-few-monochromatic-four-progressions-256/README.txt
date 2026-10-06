# Two-colourings of [1,256] with few monochromatic four-term progressions

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-few-monochromatic-four-progressions-256`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> 256 colours in {0,1} for the integers 1..256. Minimize the exact number of monochromatic 4-term arithmetic progressions a, a+d, a+2d, a+3d with d >= 1 inside 1..256. The finite count for n = 256 and k = 4 upper-bounds the minimum for this n; no exact finite value is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 256 colours in {0,1} for the integers 1..256. Minimize the exact number of monochromatic 4-term arithmetic progressions a, a+d, a+2d, a+3d with d >= 1 inside 1..256.

## State of the art

No documented minimum for n = 256, k = 4. The asymptotic density delta_4 is unknown; the random colouring gives delta_k <= 1/((k-1)2^k).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1186](https://www.erdosproblems.com/1186), status: open.

- [Erdős Problem #1186](https://www.erdosproblems.com/1186)

Parameters: `{"n": 256, "length": 4}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the minimum number of monochromatic k-term progressions in 2-colourings of [n].

Why it matters: Erdős Problem #1186 asks for the asymptotic density delta_k; Graham offered $100 for delta_3.

- [On the asymptotic minimum number of monochromatic 3-term arithmetic progressions](https://doi.org/10.1016/j.jcta.2007.03.006): Main research objective: Determine the minimum number of monochromatic k-term progressions in 2-colourings of [n]. Task connection: The finite count for n = 256 and k = 4 upper-bounds the minimum for this n; no exact finite value is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The finite count for n = 256 and k = 4 upper-bounds the minimum for this n; no exact finite value is documented. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/j.jcta.2007.03.006 (Pablo A. Parrilo, Aaron Robertson and Dan Saracino, On the asymptotic minimum number of monochromatic 3-term arithmetic progressions (2008). Erdős Problem #1186 page inspected: the constant delta_k with (delta_k + o(1))n^2 monochromatic k-APs is open; Parrilo, Robertson and Saracino bound delta_3; Wolf and Lu-Peng bound the finite-field analogue for k = 4. Crossref record for the 2008 paper inspected. The finite count for n = 256 and k = 4 upper-bounds the minimum for this n; no exact finite value is documented.)
- archive: https://www.erdosproblems.com/1186 (Erdős Problem #1186 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000991 (JSP-000991; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented finite reference value (reference label none); the count is exact but only comparable across runs and with asymptotic densities.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
