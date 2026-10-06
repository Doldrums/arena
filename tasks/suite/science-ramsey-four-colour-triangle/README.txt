# Four-colourings of complete graphs without monochromatic triangles (R(3,3,3,3))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-four-colour-triangle`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'colors': [...]}: one colour in {0,1,2,3} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 62. No colour class may contain a triangle. Maximize n. A valid 4-colouring of K_n certifies R_4(3) > n. Chung's 50-vertex colouring is the record; 51 vertices would be new.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'colors': [...]}: one colour in {0,1,2,3} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 62. No colour class may contain a triangle. Maximize n.

## State of the art

51 <= R(3,3,3,3) <= 62: Chung's 1973 construction on 50 vertices; upper bound by Fettes, Kramer and Radziszowski (2004).

Reference value: best known value `50` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #183](https://www.erdosproblems.com/183), status: solved (Lean): the limit of R(3;k)^(1/k) is infinite.

- [On the Ramsey numbers N(3,3,...,3;2)](https://doi.org/10.1016/0012-365x(73)90125-8), Fan R. K. Chung (1973)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"colors": 4, "max_vertices": 62}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the multicolour Ramsey numbers R_k(3) and their growth rate.

Why it matters: The exponential growth rate of R_k(3) is Erdős Problem #183 ($250); R(3,3,3,3) is the most studied open classical multicolour case.

- [On the Ramsey numbers N(3,3,...,3;2)](https://doi.org/10.1016/0012-365x(73)90125-8): Main research objective: Determine the multicolour Ramsey numbers R_k(3) and their growth rate. Task connection: A valid 4-colouring of K_n certifies R_4(3) > n. Chung's 50-vertex colouring is the record; 51 vertices would be new.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid 4-colouring of K_n certifies R_4(3) > n. Chung's 50-vertex colouring is the record; 51 vertices would be new. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0012-365x(73)90125-8 (Fan R. K. Chung, On the Ramsey numbers N(3,3,...,3;2) (1973). Crossref record inspected; survey DS1.18 section 6.1.1 inspected: 51 <= R_4(3) <= 62, lower bound [Chu1] (with a warning about a typo in the displayed matrix), upper bound [FeKR] (2004). A valid 4-colouring of K_n certifies R_4(3) > n. Chung's 50-vertex colouring is the record; 51 vertices would be new.)
- archive: https://www.erdosproblems.com/183 (Erdős Problem #183 (solved (Lean): the limit of R(3;k)^(1/k) is infinite); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000177 (JSP-000177; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The doubled Greenwood-Gleason starter has 32 vertices; Chung's construction is not copied.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
