# Two-colourings of K11 with few edge-disjoint monochromatic triangles

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-edge-disjoint-monochromatic-triangles-11`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'n': 11, 'colors': [...]}: colour 0 or 1 for each of the 55 pairs (i,j), i<j, in lexicographic order. The score is the maximum number of edge-disjoint monochromatic triangles, computed exactly per colour by branch and bound. Minimize; the known optimum is 6. Any colouring gives an upper bound on the minimum; the tabulated value for n = 11 is 6.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': 11, 'colors': [...]}: colour 0 or 1 for each of the 55 pairs (i,j), i<j, in lexicographic order. The score is the maximum number of edge-disjoint monochromatic triangles, computed exactly per colour by branch and bound. Minimize; the known optimum is 6.

## State of the art

For n = 11 every 2-colouring has 6 edge-disjoint monochromatic triangles and some colouring has no more (OEIS A060407, from Erdős, Faudree, Gould, Jacobson and Lehel 2001).

Reference value: proven optimum `6` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #76](https://www.erdosproblems.com/76), status: proved (Gruslys and Letzter).

- [OEIS A060407](https://oeis.org/A060407)
- [Edge disjoint monochromatic triangles in 2-colored graphs](https://doi.org/10.1016/S0012-365X(00)00312-5), P. Erdős, R.J. Faudree, R.J. Gould, M.S. Jacobson, J. Lehel (2001)

Parameters: `{"n": 11}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how many edge-disjoint monochromatic triangles every 2-colouring of K_n must contain.

Why it matters: The asymptotic question (Erdős Problem #76, conjectured by Erdős, Faudree and Ordman) was proved by Gruslys and Letzter; exact small values come from this computation.

- [Edge disjoint monochromatic triangles in 2-colored graphs](https://doi.org/10.1016/S0012-365X(00)00312-5): Main research objective: Determine how many edge-disjoint monochromatic triangles every 2-colouring of K_n must contain. Task connection: Any colouring gives an upper bound on the minimum; the tabulated value for n = 11 is 6.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Any colouring gives an upper bound on the minimum; the tabulated value for n = 11 is 6. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/S0012-365X(00)00312-5 (Paul Erdős, Ralph J. Faudree, Ronald J. Gould, Michael S. Jacobson and Jenő Lehel, Edge disjoint monochromatic triangles in 2-colored graphs (2001). Crossref record inspected (publisher page returned HTTP 403). OEIS A060407 inspected: minimum over 2-colourings of K_n of the maximum number of edge-disjoint monochromatic triangles is 0,0,0,1,2,2,3,4,6 for n = 3..11, citing this paper. Erdős Problem #76 inspected (asymptotic n^2/12, proved by Gruslys and Letzter). Any colouring gives an upper bound on the minimum; the tabulated value for n = 11 is 6.)
- archive: https://www.erdosproblems.com/76 (Erdős Problem #76 (proved (Gruslys and Letzter)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000093 (JSP-000093; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case. The value 6 is taken from OEIS A060407, which cites the 2001 paper; the paper's full text was not accessible during review.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
