# Two-colourings of triples without red K4^(3) or blue K5^(3) (hypergraph Ramsey R(4,5;3))

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-hypergraph-ramsey-four-five`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'colors': [...]}: colour 0 (red) or 1 (blue) for every triple (a,b,c), a<b<c, of vertices 0..n-1 in lexicographic order, 1 <= n <= 40. No 4 vertices may have all four triples red and no 5 vertices may have all ten triples blue. Maximize n. A valid colouring on n points certifies R(4,5;3) > n; the published construction has 34 points.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'colors': [...]}: colour 0 (red) or 1 (blue) for every triple (a,b,c), a<b<c, of vertices 0..n-1 in lexicographic order, 1 <= n <= 40. No 4 vertices may have all four triples red and no 5 vertices may have all ten triples blue. Maximize n.

## State of the art

35 <= R(4,5;3) (Dybizbański 2018): the best known colouring has 34 points.

Reference value: best known value `34` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #562](https://www.erdosproblems.com/562), status: open.

- [A lower bound on the hypergraph Ramsey number R(4,5;3)](https://doi.org/10.55016/ojs/cdm.v13i2.62416), Janusz Dybizbański (2018)
- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski

Parameters: `{"red_clique": 4, "blue_clique": 5, "max_vertices": 40}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound classical Ramsey numbers of 3-uniform hypergraphs.

Why it matters: The tower growth of hypergraph Ramsey numbers is Erdős Problem #562 (Erdős-Hajnal-Rado); small values are known only from explicit constructions.

- [A lower bound on the hypergraph Ramsey number R(4,5;3)](https://doi.org/10.55016/ojs/cdm.v13i2.62416): Main research objective: Bound classical Ramsey numbers of 3-uniform hypergraphs. Task connection: A valid colouring on n points certifies R(4,5;3) > n; the published construction has 34 points.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid colouring on n points certifies R(4,5;3) > n; the published construction has 34 points. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.55016/ojs/cdm.v13i2.62416 (Janusz Dybizbański, A lower bound on the hypergraph Ramsey number R(4,5;3) (2018). Crossref record inspected; survey DS1.18 section 7.1 inspected: R(4,4;3) = 13 is the only known nontrivial classical hypergraph Ramsey number and 35 <= R(4,5;3) [Dyb2]. A valid colouring on n points certifies R(4,5;3) > n; the published construction has 34 points.)
- archive: https://www.erdosproblems.com/562 (Erdős Problem #562 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000454 (JSP-000454; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The divisibility starter has 9 points. No upper bound on R(4,5;3) is recorded in the survey.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
