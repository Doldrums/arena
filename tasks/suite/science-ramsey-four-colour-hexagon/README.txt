# Four-colourings of complete graphs without monochromatic hexagons (R_4(C6))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-four-colour-hexagon`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'colors': [...]}: one colour in {0,1,2,3} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 20. No colour class may contain a six-cycle (exact search for not necessarily induced cycles). Maximize n. A valid 4-colouring of K_n certifies R_4(C6) > n. The best known colouring has 17 vertices; 18 or 19 vertices would be new.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'colors': [...]}: one colour in {0,1,2,3} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 20. No colour class may contain a six-cycle (exact search for not necessarily induced cycles). Maximize n.

## State of the art

18 <= R_4(C6) <= 20 (lower bound Sun, Yang, Jiang, Lin, Shi 2007; upper bound Zhang, Sun, Wu 2013), as listed in the survey.

Reference value: best known value `17` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #555](https://www.erdosproblems.com/555), status: open.

- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"colors": 4, "length": 6, "max_vertices": 20}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine multicolour Ramsey numbers of even cycles.

Why it matters: Erdős Problem #555 asks for R_k(C_2n); the survey lists R_4(C6) among the few small open multicolour cycle numbers.

- [Small Ramsey Numbers (Dynamic Survey DS1.18)](https://doi.org/10.37236/21): Main research objective: Determine multicolour Ramsey numbers of even cycles. Task connection: A valid 4-colouring of K_n certifies R_4(C6) > n. The best known colouring has 17 vertices; 18 or 19 vertices would be new.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid 4-colouring of K_n certifies R_4(C6) > n. The best known colouring has 17 vertices; 18 or 19 vertices would be new. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.37236/21 (Stanisław P. Radziszowski, Small Ramsey Numbers (Dynamic Survey DS1.18) (2026). Survey DS1.18 section 6.3.2 inspected (sur.pdf and ref.pdf downloaded 2026-09-24): 18 <= R_4(C6) <= 20 with lower bound [SunYJLS] (Sun, Yang, Jiang, Lin and Shi, Ars Combinatoria 84 (2007)) and upper bound [ZhaSW] (Ars Combinatoria 111 (2013)); neither article has a DOI. A valid 4-colouring of K_n certifies R_4(C6) > n. The best known colouring has 17 vertices; 18 or 19 vertices would be new.)
- archive: https://www.erdosproblems.com/555 (Erdős Problem #555 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000446 (JSP-000446; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The distance-class starter has 9 vertices. The primary articles have no DOI, so the survey is the inspected source.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
