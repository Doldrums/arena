# Smallest triangle-free graph of chromatic number five (rediscovering 22 vertices)

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-smallest-triangle-free-five-chromatic`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple triangle-free graph on vertices 0..n-1 with 1 <= n <= 23 that is not 4-colourable (exact backtracking). Minimize n; the proven optimum is 22. Any valid graph certifies h_3(5) <= n; the optimum 22 was established by exhaustive computer search.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple triangle-free graph on vertices 0..n-1 with 1 <= n <= 23 that is not 4-colourable (exact backtracking). Minimize n; the proven optimum is 22.

## State of the art

The smallest triangle-free 5-chromatic graphs have 22 vertices (Jensen and Royle 1995); the Mycielski graph has 23.

Reference value: proven optimum `22` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1013](https://www.erdosproblems.com/1013), status: open.

- [Small graphs with chromatic number 5: A computer search](https://doi.org/10.1002/jgt.3190190111), Tommy R. Jensen, Gordon F. Royle (1995)
- [OEIS A292528](https://oeis.org/A292528)

Parameters: `{"max_vertices": 23}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find the minimum order of triangle-free graphs with given chromatic number.

Why it matters: The function h_3(k) is Erdős Problem #1013 (dual to #1104); small cases calibrate constructions such as Mycielski's.

- [Small graphs with chromatic number 5: A computer search](https://doi.org/10.1002/jgt.3190190111): Main research objective: Find the minimum order of triangle-free graphs with given chromatic number. Task connection: Any valid graph certifies h_3(5) <= n; the optimum 22 was established by exhaustive computer search.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Any valid graph certifies h_3(5) <= n; the optimum 22 was established by exhaustive computer search. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1002/jgt.3190190111 (Tommy R. Jensen and Gordon F. Royle, Small graphs with chromatic number 5: A computer search (1995). Crossref record inspected; OEIS A292528 inspected: 1, 2, 5, 11, 22 with Jensen and Royle proving a(5) = 22 and Goedgebeur proving 32 <= a(6) <= 40. Any valid graph certifies h_3(5) <= n; the optimum 22 was established by exhaustive computer search.)
- archive: https://www.erdosproblems.com/1013 (Erdős Problem #1013 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000843 (JSP-000843; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; the 22-vertex graphs are public and not copied.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
