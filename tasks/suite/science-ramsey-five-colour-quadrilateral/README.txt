# Five-colourings of complete graphs without monochromatic four-cycles (R_5(K2,2))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-ramsey-five-colour-quadrilateral`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'colors': [...]}: one colour in {0,...,4} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 29. No colour class may contain a four-cycle (no two vertices with two common neighbours in one colour). Maximize n. A valid 5-colouring of K_n certifies R_5(C4) > n. The algebraic construction of Lazebnik and Woldar gives 26 vertices; 27 or 28 would be new.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'colors': [...]}: one colour in {0,...,4} for each pair (i,j), i<j, of vertices 0..n-1 in lexicographic order, 1 <= n <= 29. No colour class may contain a four-cycle (no two vertices with two common neighbours in one colour). Maximize n.

## State of the art

27 <= R_5(C4) <= 29 (Lazebnik and Woldar 2000).

Reference value: best known value `26` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #558](https://www.erdosproblems.com/558), status: open.

- [New Lower Bounds on the Multicolor Ramsey Numbers r_k(C4)](https://doi.org/10.1006/jctb.2000.1954), Felix Lazebnik, Andrew J. Woldar (2000)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"colors": 5, "length": 4, "max_vertices": 29}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine multicolour Ramsey numbers of the four-cycle K2,2.

Why it matters: Erdős Problem #558 asks for R_k(K_{s,t}); for K2,2 the growth (1+o(1))k^2 is known but small values remain open.

- [New Lower Bounds on the Multicolor Ramsey Numbers r_k(C4)](https://doi.org/10.1006/jctb.2000.1954): Main research objective: Determine multicolour Ramsey numbers of the four-cycle K2,2. Task connection: A valid 5-colouring of K_n certifies R_5(C4) > n. The algebraic construction of Lazebnik and Woldar gives 26 vertices; 27 or 28 would be new.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid 5-colouring of K_n certifies R_5(C4) > n. The algebraic construction of Lazebnik and Woldar gives 26 vertices; 27 or 28 would be new. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1006/jctb.2000.1954 (Felix Lazebnik and Andrew J. Woldar, New Lower Bounds on the Multicolor Ramsey Numbers r_k(C4) (2000). Crossref record inspected; survey DS1.18 section 6.3.2 inspected: 27 <= R_5(C4) <= 29 [LaWo1] and R_k(C4) >= k^2+2 for odd prime powers k. A valid 5-colouring of K_n certifies R_5(C4) > n. The algebraic construction of Lazebnik and Woldar gives 26 vertices; 27 or 28 would be new.)
- archive: https://www.erdosproblems.com/558 (Erdős Problem #558 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000449 (JSP-000449; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The distance-class starter has 11 vertices; the algebraic record construction is not copied.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
